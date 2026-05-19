"""Multi-master Team owner scheduler.

This module keeps the first multi-master slice deliberately narrow:
several imported Team owners can be planned and run inside one API task, while
each owner keeps the existing single-Team `1 owner + 2 children` contract.
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
from collections.abc import Callable, Iterable
from typing import Any

from autoteam.accounts import (
    STATUS_ACTIVE,
    STATUS_AUTH_INVALID,
    STATUS_EXHAUSTED,
    STATUS_ORPHAN,
    STATUS_PENDING,
    STATUS_PERSONAL,
    STATUS_STANDBY,
    is_account_disabled,
    load_accounts,
)
from autoteam.admin_state import load_admin_state, temporary_admin_state
from autoteam.config import (
    DIRECT_REGISTER_PARALLEL,
    MULTI_MASTER_BROWSER_BUDGET,
    MULTI_MASTER_MAX_OWNER_WORKERS,
    MULTI_MASTER_MEMORY_DOWNGRADE_RATIO,
)
from autoteam.runtime_resources import collect_runtime_resource_snapshot
from autoteam.workspace_pool import STATUS_UNHEALTHY, WorkspacePool, default_pool

logger = logging.getLogger(__name__)

_OWNER_STATUS_KEYS = (
    STATUS_ACTIVE,
    STATUS_STANDBY,
    STATUS_EXHAUSTED,
    STATUS_PENDING,
    STATUS_PERSONAL,
    STATUS_AUTH_INVALID,
    STATUS_ORPHAN,
    "disabled",
)
_TEAM_SEAT_STATUSES = {STATUS_ACTIVE, STATUS_EXHAUSTED, STATUS_AUTH_INVALID, STATUS_ORPHAN}


def list_parallel_owners(
    *,
    pool: WorkspacePool | None = None,
    workspace_ids: Iterable[str] | None = None,
    include_active_fallback: bool = True,
) -> list[dict[str, Any]]:
    """Return owner rows eligible for multi-master work.

    Rows marked ``parallel=true`` are the real multi-master set. If none exist,
    the active workspace is returned as a compatibility fallback so dry-runs and
    status still work on a single-owner install.
    """
    pool = pool or default_pool
    wanted = {str(item) for item in workspace_ids or [] if item}
    rows = [row for row in pool.list_all() if _owner_matches(row, wanted)]
    eligible = [row for row in rows if _owner_enabled(row) and row.get("admin_email") and row.get("account_id")]
    parallel = [row for row in eligible if row.get("parallel")]
    if parallel:
        return parallel
    if not include_active_fallback:
        return []
    active = pool.get_active()
    if active and _owner_matches(active, wanted) and _owner_enabled(active):
        return [active]
    return []


def build_multi_master_status(*, accounts: list[dict] | None = None, pool: WorkspacePool | None = None) -> dict:
    """Build a read-only multi-master status block for `/api/status`."""
    pool = pool or default_pool
    accounts = load_accounts() if accounts is None else accounts
    rows = pool.list_all()
    owners = [_owner_summary(row, accounts) for row in rows if row.get("admin_email") and row.get("account_id")]
    aggregate = {key: sum(owner["counts"].get(key, 0) for owner in owners) for key in _OWNER_STATUS_KEYS}
    aggregate["managed_team_seats"] = sum(owner["managed_team_seats"] for owner in owners)
    aggregate["runnable_owner_count"] = sum(1 for owner in owners if owner["runnable"])
    parallel_count = sum(1 for owner in owners if owner["parallel"])
    return {
        "enabled": parallel_count > 0,
        "owner_count": len(owners),
        "parallel_owner_count": parallel_count,
        "target_seats_per_owner": 3,
        "child_cap_per_owner": 2,
        "aggregate": aggregate,
        "owners": owners,
    }


def resolve_worker_budget(
    owner_count: int,
    *,
    requested_owner_workers: int | None = None,
    requested_direct_parallel: int | None = None,
    runtime_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Clip owner workers and direct-signup race by one global browser budget."""
    if owner_count <= 0:
        return {
            "owner_workers": 0,
            "direct_register_parallel": 0,
            "browser_budget": MULTI_MASTER_BROWSER_BUDGET,
            "downgraded": False,
            "reason": "no_owners",
        }

    owner_workers = _clamp_int(requested_owner_workers, MULTI_MASTER_MAX_OWNER_WORKERS, 1, 8)
    direct_parallel = _clamp_int(requested_direct_parallel, DIRECT_REGISTER_PARALLEL, 1, 4)
    browser_budget = max(1, int(MULTI_MASTER_BROWSER_BUDGET))
    downgraded = False
    reason = ""

    ratio = (runtime_snapshot or {}).get("cgroup_memory_usage_ratio")
    if ratio is not None and MULTI_MASTER_MEMORY_DOWNGRADE_RATIO > 0 and ratio >= MULTI_MASTER_MEMORY_DOWNGRADE_RATIO:
        owner_workers = 1
        direct_parallel = 1
        downgraded = True
        reason = "memory_high"

    owner_workers = min(owner_count, owner_workers)
    owner_workers = max(1, min(owner_workers, max(1, browser_budget // max(1, direct_parallel))))
    direct_parallel = max(1, min(direct_parallel, max(1, browser_budget // max(1, owner_workers))))

    return {
        "owner_workers": owner_workers,
        "direct_register_parallel": direct_parallel,
        "browser_budget": browser_budget,
        "downgraded": downgraded,
        "reason": reason,
    }


def run_multi_master_fill(
    target_seats: int = 3,
    *,
    owner_workers: int | None = None,
    direct_parallel: int | None = None,
    workspace_ids: Iterable[str] | None = None,
    dry_run: bool = False,
    post_sync: bool = True,
    pool: WorkspacePool | None = None,
    worker: Callable[[dict[str, Any], int, int], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run or plan a multi-owner fill operation with per-owner failure isolation."""
    pool = pool or default_pool
    owners = list_parallel_owners(pool=pool, workspace_ids=workspace_ids)
    target = _clamp_target_seats(target_seats)
    child_target = max(0, target - 1)
    runtime = _safe_runtime_snapshot()
    budget = resolve_worker_budget(
        len(owners),
        requested_owner_workers=owner_workers,
        requested_direct_parallel=direct_parallel,
        runtime_snapshot=runtime,
    )
    base = {
        "target_seats_per_owner": target,
        "child_target_per_owner": child_target,
        "owner_count": len(owners),
        "budget": budget,
        "dry_run": dry_run,
        "owners": [],
    }
    if not owners:
        return dict(base, status="no_owners")
    if dry_run:
        return dict(
            base,
            status="planned",
            owners=[_planned_owner(owner, target, child_target, budget) for owner in owners],
        )

    worker = worker or _run_fill_for_owner
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, budget["owner_workers"]),
        thread_name_prefix="multi-master",
    ) as executor:
        future_map = {}
        started_map = {}
        for owner in owners:
            future = executor.submit(worker, owner, target, budget["direct_register_parallel"])
            future_map[future] = owner
            started_map[future] = time.time()
        for future in concurrent.futures.as_completed(future_map):
            owner = future_map[future]
            started = started_map.get(future, time.time())
            try:
                result = future.result()
                result.setdefault("status", "completed")
                pool.record_run_result(owner["id"], last_error="", last_run_ts=time.time())
            except Exception as exc:
                logger.exception("[multi-master] owner %s failed: %s", owner.get("admin_email"), exc)
                result = {
                    "workspace_id": owner.get("id"),
                    "admin_email": owner.get("admin_email"),
                    "account_id": owner.get("account_id"),
                    "workspace_name": owner.get("workspace_name") or "",
                    "status": "failed",
                    "error": str(exc),
                    "elapsed_seconds": round(time.time() - started, 3),
                }
                try:
                    pool.record_run_result(owner["id"], last_error=str(exc), last_run_ts=time.time())
                except Exception:
                    logger.debug("[multi-master] cannot persist run failure for %s", owner.get("id"), exc_info=True)
            results.append(_strip_sensitive_owner_result(result))

    post_sync_result = _run_post_sync_once(results) if post_sync else {"skipped": True}
    failed = sum(1 for item in results if item.get("status") == "failed")
    status = "completed" if failed == 0 else "failed" if failed == len(results) else "partial_failed"
    return dict(
        base,
        status=status,
        owners=sorted(results, key=lambda item: item.get("admin_email") or ""),
        post_sync=post_sync_result,
    )


def _run_fill_for_owner(owner: dict[str, Any], target_seats: int, direct_parallel: int) -> dict[str, Any]:
    session_token = _owner_session_token(owner)
    if not session_token:
        raise RuntimeError("owner session_token missing")
    started = time.time()
    from autoteam.manager import cmd_fill

    with temporary_admin_state(
        email=owner.get("admin_email") or "",
        session_token=session_token,
        account_id=owner.get("account_id") or "",
        workspace_name=owner.get("workspace_name") or "",
    ):
        cmd_fill(
            target_seats,
            leave_workspace=False,
            post_sync=False,
            print_status=False,
            direct_parallel=direct_parallel,
        )
    return {
        "workspace_id": owner.get("id"),
        "admin_email": owner.get("admin_email"),
        "account_id": owner.get("account_id"),
        "workspace_name": owner.get("workspace_name") or "",
        "status": "completed",
        "target_seats": target_seats,
        "direct_register_parallel": direct_parallel,
        "elapsed_seconds": round(time.time() - started, 3),
    }


def _planned_owner(owner: dict[str, Any], target: int, child_target: int, budget: dict[str, Any]) -> dict[str, Any]:
    return {
        "workspace_id": owner.get("id"),
        "admin_email": owner.get("admin_email"),
        "account_id": owner.get("account_id"),
        "workspace_name": owner.get("workspace_name") or "",
        "status": "planned",
        "runnable": _owner_runnable(owner),
        "target_seats": target,
        "child_target": child_target,
        "direct_register_parallel": budget["direct_register_parallel"],
    }


def _owner_summary(owner: dict[str, Any], accounts: list[dict]) -> dict[str, Any]:
    account_id = owner.get("account_id") or ""
    owner_accounts = [acc for acc in accounts if (acc.get("workspace_account_id") or "") == account_id]
    counts = {key: 0 for key in _OWNER_STATUS_KEYS}
    managed_team_seats = 0
    for acc in owner_accounts:
        disabled = is_account_disabled(acc)
        status = "disabled" if disabled else (acc.get("status") or "")
        if status in counts:
            counts[status] += 1
        if not disabled and (acc.get("status") or "") in _TEAM_SEAT_STATUSES:
            managed_team_seats += 1
    return {
        "workspace_id": owner.get("id"),
        "admin_email": owner.get("admin_email"),
        "account_id": account_id,
        "workspace_name": owner.get("workspace_name") or "",
        "tier": owner.get("tier"),
        "health_status": owner.get("status"),
        "enabled": _owner_enabled(owner),
        "parallel": bool(owner.get("parallel")),
        "session_present": bool(_owner_session_token(owner)),
        "runnable": _owner_runnable(owner),
        "managed_team_seats": managed_team_seats,
        "counts": counts,
        "last_error": owner.get("last_error") or "",
        "last_run_ts": owner.get("last_run_ts"),
    }


def _owner_session_token(owner: dict[str, Any]) -> str:
    token = str(owner.get("session_token") or "").strip()
    if token:
        return token
    state = load_admin_state()
    if (state.get("account_id") and state.get("account_id") == owner.get("account_id")) or (
        state.get("email") and state.get("email") == owner.get("admin_email")
    ):
        return str(state.get("session_token") or "").strip()
    return ""


def _owner_runnable(owner: dict[str, Any]) -> bool:
    return (
        _owner_enabled(owner)
        and owner.get("status") != STATUS_UNHEALTHY
        and bool(owner.get("admin_email"))
        and bool(owner.get("account_id"))
        and bool(_owner_session_token(owner))
    )


def _owner_enabled(owner: dict[str, Any]) -> bool:
    return owner.get("enabled") is not False


def _owner_matches(owner: dict[str, Any], wanted: set[str]) -> bool:
    if not wanted:
        return True
    values = {
        str(owner.get("id") or ""),
        str(owner.get("account_id") or ""),
        str(owner.get("admin_email") or ""),
    }
    return bool(values & wanted)


def _strip_sensitive_owner_result(result: dict[str, Any]) -> dict[str, Any]:
    clean = dict(result)
    clean.pop("session_token", None)
    return clean


def _run_post_sync_once(results: list[dict[str, Any]]) -> dict[str, Any]:
    if not any(item.get("status") == "completed" for item in results):
        return {"skipped": True, "reason": "no_completed_owners"}
    try:
        from autoteam.cpa_sync import sync_to_cpa

        sync_to_cpa()
        return {"ok": True}
    except Exception as exc:
        logger.warning("[multi-master] post-fill CPA sync failed: %s", exc)
        return {"ok": False, "error": str(exc)}


def _safe_runtime_snapshot() -> dict[str, Any]:
    try:
        return collect_runtime_resource_snapshot()
    except Exception as exc:
        logger.debug("[multi-master] runtime snapshot unavailable: %s", exc)
        return {"error": "runtime_snapshot_unavailable"}


def _clamp_target_seats(value: int) -> int:
    try:
        from autoteam.manager import _clamp_team_target_seats

        return _clamp_team_target_seats(value)
    except Exception:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = 3
        return max(1, min(3, parsed))


def _clamp_int(value: int | None, default: int, low: int, high: int) -> int:
    try:
        parsed = int(default if value is None else value)
    except (TypeError, ValueError):
        parsed = default
    return max(low, min(high, parsed))


__all__ = [
    "build_multi_master_status",
    "list_parallel_owners",
    "resolve_worker_budget",
    "run_multi_master_fill",
]
