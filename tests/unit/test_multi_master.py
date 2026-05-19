import threading

from autoteam import admin_state, api, multi_master
from autoteam.workspace_pool import SCHEMA_VERSION, TIER_ACTIVE, TIER_WARM, WorkspacePool

UUID_A = "00000000-0000-0000-0000-0000000000aa"
UUID_B = "00000000-0000-0000-0000-0000000000bb"


def _disable_admin_seed(monkeypatch):
    monkeypatch.setattr(
        WorkspacePool,
        "_seed_from_admin_state",
        lambda self: {"schema_version": SCHEMA_VERSION, "active": None, "workspaces": []},
    )


def test_temporary_admin_state_overrides_thread_local_state(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(admin_state, "STATE_FILE", state_file)
    admin_state.save_admin_state({
        "email": "owner-a@example.com",
        "session_token": "token-a",
        "account_id": UUID_A,
        "workspace_name": "Team A",
    })

    with admin_state.temporary_admin_state(
        email="owner-b@example.com",
        session_token="token-b",
        account_id=UUID_B,
        workspace_name="Team B",
    ):
        assert admin_state.get_admin_email() == "owner-b@example.com"
        assert admin_state.get_admin_session_token() == "token-b"
        assert admin_state.get_chatgpt_account_id() == UUID_B
        assert admin_state.get_chatgpt_workspace_name() == "Team B"

    assert admin_state.load_admin_state()["email"] == "owner-a@example.com"
    assert admin_state.get_admin_session_token() == "token-a"


def test_workspace_pool_upsert_persists_parallel_owner_metadata(tmp_path, monkeypatch):
    _disable_admin_seed(monkeypatch)
    pool = WorkspacePool(path=tmp_path / "workspaces.json")

    snap = pool.upsert(
        "ws-a",
        "owner-a@example.com",
        UUID_A,
        workspace_name="Team A",
        session_token="secret-a",
        enabled=True,
        parallel=True,
    )

    assert snap["tier"] == TIER_ACTIVE
    assert snap["workspace_name"] == "Team A"
    assert snap["session_token"] == "secret-a"
    assert snap["parallel"] is True

    updated = pool.upsert(
        "ws-a",
        "owner-a2@example.com",
        UUID_A,
        workspace_name="Team A2",
        session_token="secret-a2",
        enabled=False,
        parallel=False,
    )

    assert updated["admin_email"] == "owner-a2@example.com"
    assert updated["session_token"] == "secret-a2"
    assert updated["enabled"] is False
    assert updated["parallel"] is False
    assert any(row["reason"] == "upsert_update" for row in updated["transition_log"])


def test_multi_master_status_groups_accounts_without_leaking_tokens(tmp_path, monkeypatch):
    _disable_admin_seed(monkeypatch)
    pool = WorkspacePool(path=tmp_path / "workspaces.json")
    pool.upsert("ws-a", "owner-a@example.com", UUID_A, workspace_name="Team A", session_token="secret-a", parallel=True)
    pool.upsert("ws-b", "owner-b@example.com", UUID_B, tier=TIER_WARM, workspace_name="Team B", parallel=True)
    accounts = [
        {"email": "a1@example.com", "status": "active", "workspace_account_id": UUID_A},
        {"email": "a2@example.com", "status": "auth_invalid", "workspace_account_id": UUID_A},
        {"email": "b1@example.com", "status": "standby", "workspace_account_id": UUID_B, "disabled": True},
        {"email": "other@example.com", "status": "active", "workspace_account_id": "other"},
    ]

    status = multi_master.build_multi_master_status(accounts=accounts, pool=pool)

    assert status["enabled"] is True
    assert status["owner_count"] == 2
    assert status["parallel_owner_count"] == 2
    owner_a = next(owner for owner in status["owners"] if owner["workspace_id"] == "ws-a")
    owner_b = next(owner for owner in status["owners"] if owner["workspace_id"] == "ws-b")
    assert "session_token" not in owner_a
    assert owner_a["session_present"] is True
    assert owner_a["managed_team_seats"] == 2
    assert owner_a["counts"]["active"] == 1
    assert owner_a["counts"]["auth_invalid"] == 1
    assert owner_b["counts"]["disabled"] == 1
    assert status["aggregate"]["managed_team_seats"] == 2


def test_resolve_worker_budget_downgrades_on_high_memory(monkeypatch):
    monkeypatch.setattr(multi_master, "MULTI_MASTER_MAX_OWNER_WORKERS", 4)
    monkeypatch.setattr(multi_master, "MULTI_MASTER_BROWSER_BUDGET", 8)
    monkeypatch.setattr(multi_master, "MULTI_MASTER_MEMORY_DOWNGRADE_RATIO", 0.85)
    monkeypatch.setattr(multi_master, "DIRECT_REGISTER_PARALLEL", 3)

    budget = multi_master.resolve_worker_budget(
        4,
        runtime_snapshot={"cgroup_memory_usage_ratio": 0.9},
    )

    assert budget["owner_workers"] == 1
    assert budget["direct_register_parallel"] == 1
    assert budget["downgraded"] is True
    assert budget["reason"] == "memory_high"


def test_run_multi_master_fill_isolates_owner_failures(tmp_path, monkeypatch):
    _disable_admin_seed(monkeypatch)
    pool = WorkspacePool(path=tmp_path / "workspaces.json")
    pool.upsert("ws-a", "owner-a@example.com", UUID_A, workspace_name="Team A", session_token="secret-a", parallel=True)
    pool.upsert("ws-b", "owner-b@example.com", UUID_B, tier=TIER_WARM, workspace_name="Team B", session_token="secret-b", parallel=True)
    seen = []
    lock = threading.Lock()

    def fake_cmd_fill(target, leave_workspace=False, post_sync=True, print_status=True, direct_parallel=None):
        with lock:
            seen.append(
                (
                    admin_state.get_admin_email(),
                    admin_state.get_chatgpt_account_id(),
                    target,
                    leave_workspace,
                    post_sync,
                    print_status,
                    direct_parallel,
                )
            )
        if admin_state.get_admin_email() == "owner-b@example.com":
            raise RuntimeError("boom-b")

    monkeypatch.setattr("autoteam.manager.cmd_fill", fake_cmd_fill)
    monkeypatch.setattr(multi_master, "collect_runtime_resource_snapshot", lambda: {"cgroup_memory_usage_ratio": 0.1})

    result = multi_master.run_multi_master_fill(
        target_seats=3,
        owner_workers=2,
        direct_parallel=1,
        pool=pool,
        post_sync=False,
    )

    assert result["status"] == "partial_failed"
    assert {row[0] for row in seen} == {"owner-a@example.com", "owner-b@example.com"}
    assert ("owner-a@example.com", UUID_A, 3, False, False, False, 1) in seen
    assert ("owner-b@example.com", UUID_B, 3, False, False, False, 1) in seen
    assert result["post_sync"] == {"skipped": True}
    owner_b = next(owner for owner in result["owners"] if owner["admin_email"] == "owner-b@example.com")
    assert owner_b["status"] == "failed"
    assert "boom-b" in owner_b["error"]
    assert pool.get("ws-b")["last_error"] == "boom-b"
    assert pool.get("ws-a")["last_error"] == ""


def test_post_multi_master_fill_dry_run_returns_plan(monkeypatch):
    called = []

    def fake_run(**kwargs):
        called.append(kwargs)
        return {"status": "planned", "owners": []}

    monkeypatch.setattr(multi_master, "run_multi_master_fill", fake_run)

    result = api.post_multi_master_fill(api.MultiMasterFillParams(target=3, owner_workers=2, dry_run=True))

    assert result["command"] == "multi-master-fill"
    assert result["status"] == "completed"
    assert result["result"]["status"] == "planned"
    assert called == [{
        "target_seats": 3,
        "owner_workers": 2,
        "direct_parallel": None,
        "workspace_ids": None,
        "dry_run": True,
    }]
