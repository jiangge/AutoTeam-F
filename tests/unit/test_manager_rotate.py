from autoteam import manager


class _FakeChatGPT:
    def __init__(self):
        self.browser = True
        self.started = 0
        self.stopped = 0

    def start(self):
        self.browser = True
        self.started += 1

    def stop(self):
        self.browser = False
        self.stopped += 1


class _FakeMailClient:
    def login(self):
        return None


def test_cmd_rotate_skips_google_accounts_during_auto_reuse(monkeypatch):
    import autoteam.config as config

    chatgpt = _FakeChatGPT()
    count_values = iter([2, 3])
    events = []

    monkeypatch.setattr(config, "ROTATE_SKIP_REUSE", False)
    monkeypatch.setattr(manager, "sync_account_states", lambda: events.append(("sync_account_states", None)))
    monkeypatch.setattr(manager, "cmd_check", lambda: events.append(("cmd_check", None)))
    monkeypatch.setattr(manager, "ChatGPTTeamAPI", lambda: chatgpt)
    monkeypatch.setattr(manager, "CloudMailClient", lambda: _FakeMailClient())
    monkeypatch.setattr(manager, "load_accounts", lambda: [])
    monkeypatch.setattr(manager, "get_team_member_count", lambda _chatgpt: next(count_values))
    monkeypatch.setattr(
        manager,
        "get_standby_accounts",
        lambda: [
            {"email": "bubblehuntr@gmail.com"},
            {"email": "old-2@example.com"},
        ],
    )
    monkeypatch.setattr(
        manager,
        "reinvite_account",
        lambda _chatgpt, _mail, acc: events.append(("reinvite", acc["email"])) or True,
    )
    monkeypatch.setattr(
        manager,
        "create_new_account",
        lambda _chatgpt, _mail: events.append(("create", None)) or True,
    )
    monkeypatch.setattr(manager, "sync_to_cpa", lambda: events.append(("sync_to_cpa", None)))

    manager.cmd_rotate(target_seats=3)

    assert events == [
        ("sync_account_states", None),
        ("cmd_check", None),
        ("reinvite", "old-2@example.com"),
        ("sync_to_cpa", None),
    ]
    assert chatgpt.stopped == 1


def test_cmd_rotate_can_defer_final_sync_when_running_as_api_task(monkeypatch):
    chatgpt = _FakeChatGPT()
    events = []

    monkeypatch.setattr(manager, "sync_account_states", lambda: events.append(("sync_account_states", None)))
    monkeypatch.setattr(manager, "cmd_check", lambda: events.append(("cmd_check", None)))
    monkeypatch.setattr(manager, "ChatGPTTeamAPI", lambda: chatgpt)
    monkeypatch.setattr(manager, "CloudMailClient", lambda: _FakeMailClient())
    monkeypatch.setattr(manager, "load_accounts", lambda: [])
    monkeypatch.setattr(manager, "get_team_member_count", lambda _chatgpt: 3)
    monkeypatch.setattr(manager, "_count_pool_active_accounts", lambda *args, **kwargs: 2)
    monkeypatch.setattr(manager, "get_standby_accounts", lambda: [])
    monkeypatch.setattr(
        manager,
        "create_new_account",
        lambda _chatgpt, _mail: (_ for _ in ()).throw(AssertionError("should not create when member count is full")),
    )
    monkeypatch.setattr(
        manager,
        "sync_to_cpa",
        lambda: (_ for _ in ()).throw(AssertionError("final sync should be scheduled, not run inline")),
    )
    monkeypatch.setattr(
        manager,
        "_schedule_post_task_sync",
        lambda stage_label: events.append(("schedule_post_sync", stage_label)),
    )

    manager.cmd_rotate(target_seats=3, background_post_sync=True)

    assert events == [
        ("sync_account_states", None),
        ("cmd_check", None),
        ("schedule_post_sync", "[轮转]"),
    ]


def test_replaceable_pool_blocker_reason_reports_concrete_evidence(tmp_path):
    auth_file = tmp_path / "codex-auth.json"
    auth_file.write_text("{}", encoding="utf-8")
    assert (
        manager._replaceable_pool_blocker_reason(
            {"email": "missing@example.com", "status": manager.STATUS_ACTIVE, "auth_file": ""}
        )
        == "missing_auth"
    )
    assert (
        manager._replaceable_pool_blocker_reason(
            {"email": "invalid@example.com", "status": manager.STATUS_AUTH_INVALID}
        )
        == "auth_invalid"
    )
    assert (
        manager._replaceable_pool_blocker_reason(
            {"email": "exhausted@example.com", "status": manager.STATUS_EXHAUSTED}
        )
        == "quota_exhausted"
    )
    assert (
        manager._replaceable_pool_blocker_reason(
            {
                "email": "managed-protected@example.com",
                "status": manager.STATUS_ACTIVE,
                "auth_file": str(auth_file),
                "mail_account_id": 1,
                "auth_retry_paused": True,
                "protect_team_seat": True,
            }
        )
        == "auth_retry_paused"
    )
    assert (
        manager._replaceable_pool_blocker_reason(
            {
                "email": "manual-protected@example.com",
                "status": manager.STATUS_ACTIVE,
                "auth_file": str(auth_file),
                "auth_retry_paused": True,
                "protect_team_seat": True,
            }
        )
        is None
    )


def test_create_new_account_uses_domain_auto_join_before_invite(monkeypatch):
    chatgpt = _FakeChatGPT()
    events = []

    monkeypatch.setenv("ROTATE_NEW_ACCOUNT_MODE", "domain_auto_join_first")
    monkeypatch.setenv("AUTOTEAM_AUTO_JOIN_DOMAINS", "example.com")
    monkeypatch.setattr(manager, "get_mail_domain", lambda: "@example.com")
    monkeypatch.setattr(manager, "_prepare_remote_capacity_for_new_seat", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        manager,
        "create_account_via_invite",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("invite should not run for auto-join domain")),
    )
    monkeypatch.setattr(manager, "create_account_direct", lambda *_args, **_kwargs: events.append("direct") or "new@example.com")

    result = manager.create_new_account(chatgpt, _FakeMailClient())

    assert result == "new@example.com"
    assert events == ["direct"]
    assert chatgpt.stopped == 1


def test_create_new_account_invite_first_mode_preserves_invite_order(monkeypatch):
    chatgpt = _FakeChatGPT()
    events = []

    monkeypatch.setenv("ROTATE_NEW_ACCOUNT_MODE", "invite_first")
    monkeypatch.setattr(manager, "create_account_via_invite", lambda *_args, **_kwargs: events.append("invite") or "new@example.com")
    monkeypatch.setattr(
        manager,
        "create_account_direct",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("direct should not run when invite succeeds")),
    )

    result = manager.create_new_account(chatgpt, _FakeMailClient())

    assert result == "new@example.com"
    assert events == ["invite"]


def test_create_new_account_domain_auto_join_falls_back_to_invite(monkeypatch):
    chatgpt = _FakeChatGPT()
    events = []

    monkeypatch.setenv("ROTATE_NEW_ACCOUNT_MODE", "domain_auto_join_first")
    monkeypatch.setenv("AUTOTEAM_AUTO_JOIN_DOMAINS", "example.com")
    monkeypatch.setenv("ROTATE_DOMAIN_AUTO_JOIN_FALLBACK_INVITE", "true")
    monkeypatch.setattr(manager, "get_mail_domain", lambda: "@example.com")
    monkeypatch.setattr(manager, "_prepare_remote_capacity_for_new_seat", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(manager, "create_account_direct", lambda *_args, **_kwargs: events.append("direct") or None)
    monkeypatch.setattr(manager, "create_account_via_invite", lambda *_args, **_kwargs: events.append("invite") or "new@example.com")

    result = manager.create_new_account(chatgpt, _FakeMailClient())

    assert result == "new@example.com"
    assert events == ["direct", "invite"]


def test_create_new_account_does_not_retry_direct_after_invite_fallback_failure(monkeypatch):
    chatgpt = _FakeChatGPT()
    events = []

    monkeypatch.setenv("ROTATE_NEW_ACCOUNT_MODE", "domain_auto_join_first")
    monkeypatch.setenv("AUTOTEAM_AUTO_JOIN_DOMAINS", "example.com")
    monkeypatch.setattr(manager, "get_mail_domain", lambda: "@example.com")
    monkeypatch.setattr(manager, "_prepare_remote_capacity_for_new_seat", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(manager, "create_account_direct", lambda *_args, **_kwargs: events.append("direct") or None)
    monkeypatch.setattr(manager, "create_account_via_invite", lambda *_args, **_kwargs: events.append("invite") or None)

    assert manager.create_new_account(chatgpt, _FakeMailClient()) is None
    assert events == ["direct", "invite"]


def test_create_new_account_domain_auto_join_respects_allowlist(monkeypatch):
    chatgpt = _FakeChatGPT()
    events = []

    monkeypatch.setenv("ROTATE_NEW_ACCOUNT_MODE", "domain_auto_join_first")
    monkeypatch.setenv("AUTOTEAM_AUTO_JOIN_DOMAINS", "other.example")
    monkeypatch.setattr(manager, "get_mail_domain", lambda: "@example.com")
    monkeypatch.setattr(
        manager,
        "create_account_direct",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("direct should not run for unlisted domain")),
    )
    monkeypatch.setattr(manager, "create_account_via_invite", lambda *_args, **_kwargs: events.append("invite") or "new@example.com")

    result = manager.create_new_account(chatgpt, _FakeMailClient())

    assert result == "new@example.com"
    assert events == ["invite"]


def test_cmd_rotate_removes_replaceable_blocker_before_creating_replacement(monkeypatch):
    import autoteam.config as config

    chatgpt = _FakeChatGPT()
    accounts = [{"email": "blocked@example.com", "status": manager.STATUS_ACTIVE, "auth_file": ""}]
    counts = iter([3, 2, 2, 3])
    events = []

    monkeypatch.setattr(config, "ROTATE_SKIP_REUSE", True)
    monkeypatch.setattr(manager, "sync_account_states", lambda: events.append(("sync_account_states", None)))
    monkeypatch.setattr(manager, "cmd_check", lambda: events.append(("cmd_check", None)))
    monkeypatch.setattr(manager, "ChatGPTTeamAPI", lambda: chatgpt)
    monkeypatch.setattr(manager, "CloudMailClient", lambda: _FakeMailClient())
    monkeypatch.setattr(manager, "load_accounts", lambda: accounts)
    monkeypatch.setattr(manager, "get_team_member_count", lambda _chatgpt: next(counts))
    monkeypatch.setattr(manager, "get_standby_accounts", lambda: [])
    monkeypatch.setattr(manager, "time", manager.time)
    monkeypatch.setattr(manager.time, "sleep", lambda *_args, **_kwargs: None)

    def fake_update(email, **kwargs):
        events.append(("update", email, kwargs.get("status"), kwargs.get("_reason")))
        for acc in accounts:
            if acc["email"] == email:
                acc.update(kwargs)

    def fake_remove(_chatgpt, email, *, return_status=False, **_kwargs):
        events.append(("remove", email))
        return "removed" if return_status else True

    def fake_create(_chatgpt, _mail):
        events.append(("create", None))
        accounts.append(
            {
                "email": "new@example.com",
                "status": manager.STATUS_ACTIVE,
                "auth_file": "auth.json",
            }
        )
        return "new@example.com"

    monkeypatch.setattr(manager, "update_account", fake_update)
    monkeypatch.setattr(manager, "remove_from_team", fake_remove)
    monkeypatch.setattr(manager, "create_new_account", fake_create)
    monkeypatch.setattr(manager, "_validate_managed_account_operational", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(manager, "sync_to_cpa", lambda: events.append(("sync_to_cpa", None)))

    manager.cmd_rotate(target_seats=3)

    assert events.index(("remove", "blocked@example.com")) < events.index(("create", None))
    assert ("update", "blocked@example.com", manager.STATUS_STANDBY, "missing_auth") in events


def test_cmd_rotate_target2_refills_after_exhausted_removal_despite_transient_overcount(tmp_path, monkeypatch):
    import autoteam.config as config

    chatgpt = _FakeChatGPT()
    old_auth = tmp_path / "old.json"
    standby_auth = tmp_path / "standby.json"
    old_auth.write_text('{"access_token": "old-token"}', encoding="utf-8")
    standby_auth.write_text('{"access_token": "standby-token"}', encoding="utf-8")

    state = {
        "team_count": 2,
        "accounts": [
            {
                "email": "old@example.com",
                "status": manager.STATUS_EXHAUSTED,
                "auth_file": str(old_auth),
                "last_quota": {"primary_pct": 100, "primary_resets_at": 1_700_001_000},
            },
            {
                "email": "standby@example.com",
                "status": manager.STATUS_STANDBY,
                "auth_file": str(standby_auth),
                "last_quota": {"primary_pct": 10, "primary_resets_at": 1_700_000_000},
            },
        ],
    }
    counts = iter([2, 3, 2])
    events = []

    def fake_load_accounts():
        return [dict(acc) for acc in state["accounts"]]

    def fake_update(email, **kwargs):
        events.append(("update", email, kwargs.get("status"), kwargs.get("_reason")))
        for acc in state["accounts"]:
            if acc["email"] == email:
                acc.update(kwargs)
                return

    def fake_count(_chatgpt):
        count = next(counts)
        events.append(("count", count))
        return count

    def fake_wait(_chatgpt, **kwargs):
        events.append(("wait_capacity", kwargs["removed_email"], kwargs["target"]))
        return 3, False

    def fake_remove(_chatgpt, email, *, return_status=False, **_kwargs):
        events.append(("remove", email, return_status))
        state["team_count"] -= 1
        return "removed" if return_status else True

    def fake_quota(token, *args, **kwargs):
        events.append(("quota", token))
        if token == "old-token":
            return (
                "exhausted",
                {"quota_info": {"primary_pct": 100, "weekly_pct": 100}, "resets_at": 1_700_001_000},
            )
        return "ok", {"primary_pct": 10, "weekly_pct": 10}

    def fake_reinvite(_chatgpt, _mail, acc):
        events.append(("reinvite", acc["email"]))
        state["team_count"] += 1
        fake_update(acc["email"], status=manager.STATUS_ACTIVE, last_active_at=1_700_000_000)
        return True

    monkeypatch.setattr(config, "ROTATE_SKIP_REUSE", False)
    monkeypatch.setattr(manager, "sync_account_states", lambda: events.append(("sync_account_states", None)))
    monkeypatch.setattr(manager, "cmd_check", lambda: events.append(("cmd_check", None)))
    monkeypatch.setattr(manager, "ChatGPTTeamAPI", lambda: chatgpt)
    monkeypatch.setattr(manager, "CloudMailClient", lambda: _FakeMailClient())
    monkeypatch.setattr(manager, "load_accounts", fake_load_accounts)
    monkeypatch.setattr(manager, "update_account", fake_update)
    monkeypatch.setattr(manager, "get_team_member_count", fake_count)
    monkeypatch.setattr(manager, "_wait_for_remote_capacity_after_removal", fake_wait)
    monkeypatch.setattr(
        manager,
        "get_standby_accounts",
        lambda: [dict(acc) for acc in state["accounts"] if acc["status"] == manager.STATUS_STANDBY],
    )
    monkeypatch.setattr(manager, "check_codex_quota", fake_quota)
    monkeypatch.setattr(manager, "reinvite_account", fake_reinvite)
    monkeypatch.setattr(
        manager,
        "create_new_account",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("should reuse standby after removing exhausted blocker, not create before remove")
        ),
    )
    monkeypatch.setattr(manager, "remove_from_team", fake_remove)
    monkeypatch.setattr(manager, "sync_to_cpa", lambda: events.append(("sync_to_cpa", None)))

    manager.cmd_rotate(target_seats=2)

    assert events.index(("remove", "old@example.com", True)) < events.index(("reinvite", "standby@example.com"))
    assert ("count", 3) in events
    assert events.count(("remove", "old@example.com", True)) == 1
    assert state["team_count"] == 2
    assert next(acc for acc in state["accounts"] if acc["email"] == "old@example.com")["status"] == manager.STATUS_STANDBY
    assert next(acc for acc in state["accounts"] if acc["email"] == "standby@example.com")[
        "status"
    ] == manager.STATUS_ACTIVE
