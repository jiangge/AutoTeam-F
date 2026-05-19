# Current vs autoteam-1 seat rotation migration notes

Date: 2026-05-19

## Scope

This note re-checks the current `D:\Desktop\AutoTeam` tree against the target `D:\Desktop\autoteam-1\AutoTeam` tree for the user's requested migration around seat rotation and related hardening. Older Trellis audit files are useful history but some of their conclusions are stale because current `main` has since absorbed IPv6 pool, CLIProxy health, runtime resources, multi-master scaffolding, and other features.

## Re-verified current baseline

* Current repo recent commits include `ead7e93 feat: add multi-master Team fill scheduler`, `5aff1af fix: 对齐注册轮转链路和 CloudMail 配置提示`, `8543971 feat: add ipv6 proxy pool and status surface`, and `a011d67 fix: harden Playwright and HTTP transport cleanup`.
* Target repo recent commits include `276ed0b fix: harden quota blocker rotation`, `f120570 fix rotate post sync and cliproxy health`, `6f4d106 fix invite blank page recovery`, `15e50d6 Improve registration credential sync and diagnostics`, `d952ce6 fix rotation cooldown safety boundary`, `2fb3031 fix rotation validation and ipv6 pool status`, and `7d46b46 fix autoteam seat rotation runtime hardening`.
* `git diff --no-index --stat` still shows large divergence in `api.py`, `manager.py`, `cpa_sync.py`, and `tests/unit/test_api_status.py`, so broad copying would be unsafe.
* GitNexus does not currently index either AutoTeam tree. Serena MCP returned parameter errors in this session. Code evidence here comes from local read-only searches and targeted file reads.

## Already absorbed in current repo

* 3-seat clamp exists: current `src/autoteam/config.py` clamps `AUTO_CHECK_TARGET_SEATS` to `1..3`; current `manager.py` has `TEAM_SEATS_MAX = 3` semantics via `_clamp_team_target_seats`.
* Runtime validation and status exposure exist: current `api.py` has `_log_task_runtime_validation`, `_rotation_validation_cooldown`, `/api/status.runtime_resources`, `/api/status.ipv6_pool`, and `/api/status.cliproxy`.
* IPv6 pool/proxy exists in current repo: `src/autoteam/ipv6_pool.py`, `src/autoteam/ipv6_proxy.py`, `manager._ensure_account_ipv6_proxy`, `chatgpt_api` integration, `cpa_sync` proxy refresh, `tests/unit/test_ipv6_pool.py`.
* CLIProxyAPI read-only health exists: `src/autoteam/cliproxy_health.py`, `tests/unit/test_cliproxy_health.py`, and `web/src/components/PoolPage.vue` references `status.cliproxy`.
* Docker/runtime hardening has a completed local audit under `.trellis/tasks/05-15-autoteam1-hardening-docker-apply/completion-audit-2026-05-15.md`.
* Multi-master scaffolding exists in current repo: `src/autoteam/multi_master.py`, `tests/unit/test_multi_master.py`, and a dry-run API path. It groups owners and budgets owner workers, but it does not by itself solve the single-owner rotate blocker semantics below.

## Remaining target behaviors not fully applied

### 1. Default skip-reuse / new-account replacement policy

Target repo has `ROTATE_SKIP_REUSE=true` in config and uses it throughout `manager.cmd_rotate`, `cmd_check`, and `create_new_account` to avoid reusing old/disabled/retired child accounts. Current repo does not define `ROTATE_SKIP_REUSE`; current `cmd_rotate` still prioritizes standby reuse and describes itself as "尽量少创建新账号". This is a real policy difference.

Migration risk: current repo also has Round 12 provider fallback and `RegisterPathRotator`. A target-style skip-reuse policy should be added as an opt-in/defaulted config and threaded through current reuse paths rather than replacing the current manager wholesale.

### 2. Replaceable pool blocker semantics

Target repo has:

* `manager._account_auth_state_blocks_pool_use`
* `manager._is_pool_active_account_usable`
* `manager._replaceable_pool_blocker_reason`
* `manager._is_replaceable_pool_blocker`
* `api._collect_auto_check_state` that classifies active/auth-pending/missing-auth/auth-error/low-quota candidates before choosing rotate, auth repair, cleanup, or no-op.

Current repo search found no equivalent symbols. Current auto-check mostly counts `STATUS_ACTIVE` rows with existing auth files, handles basic cooldown, and triggers `auto-fill`; it does not classify local occupied-but-unusable Team seats as replaceable blockers.

Migration value: this is likely the most important remaining target improvement for rotation accuracy. It prevents "Team full but local usable pool short" from being treated as healthy.

### 3. Remove-before-create replacement under full Team

Target `cmd_rotate` contains `attempt_remove_then_create(...)`, `_wait_for_remote_capacity_after_removal(...)`, and managed-account post-create validation. When the Team is already full and a child must be replaced, it removes a concrete old child, waits for remote capacity, then creates the replacement. Current `cmd_rotate` removes exhausted rows before creating, but lacks target's explicit full-Team remove-first transaction for local blockers and confirmed unusable low-quota seats.

Migration value: aligns with the hard 3-seat cap and avoids create-before-remove behavior. This also matches external SaaS lifecycle guidance: deprovision/confirm capacity before provisioning replacements, keep operations idempotent, and record audit outcomes.

### 4. Managed account operational validation

Target repo has `manager._validate_managed_account_operational(...)` and tests requiring a new managed child to be present remotely and have usable Codex auth/quota. Current repo has post-task validation in `api.py`, but current `cmd_rotate` does not validate each replacement child before treating the vacancy as filled.

Migration value: catches degraded successes earlier and allows immediate release/discard of a newly created but unusable child.

### 5. More nuanced auto-check actions

Target auto-check can trigger:

* `auto-rotate` for real seat shortage, confirmed low/exhausted blockers, or local_pool_blocker.
* `auto-auth-repair` when remote Team is full but local auth is missing/invalid and retry is not throttled.
* `auto-cleanup` when remote Team exceeds target.
* Cooldown bypass for real Team shortage or confirmed exhausted remote blocker, but cooldown delay for low-quota churn when capacity is otherwise healthy.

Current tests cover only two cooldown cases around real shortage vs full Team. Target `tests/unit/test_api_status.py` has many more cases around degraded cooldown, unknown probes, auth repair, cleanup, and blocker rotation.

Migration value: improves both efficiency and accuracy without changing the 3-seat contract.

### 6. Task progress heartbeat and rotate duration fuse

Target `api.py` exposes `bump_task_progress(...)`, and target `cmd_rotate` uses `ROTATE_MAX_DURATION` plus `_deadline_exceeded(...)`. Current repo search found no `bump_task_progress`, `ROTATE_MAX_DURATION`, or deadline helper.

Migration value: long registration/rotation jobs can show healthy forward progress to watchdog-style observers and stop before colliding with the next recovery loop.

### 7. Direct registration race is still not wired into single-owner registration

Current `.env.example` contains `DIRECT_REGISTER_PARALLEL=1`, and `multi_master.resolve_worker_budget(...)` budgets `direct_register_parallel`, but current `manager.py` does not contain target's `_direct_register_parallel_size`, `_cap_direct_register_parallel`, or `_race_chatgpt_signup`. The current multi-master worker passes the direct-parallel value in result metadata but calls `cmd_fill(...)` without passing it into actual account creation.

Migration value: if the project wants target's direct signup race, it must be wired into current `create_account_direct` / `cmd_fill` path while preserving `RegisterPathRotator`, provider fallback, SignupProfile reuse, Playwright cleanup, and global browser budget.

## Areas that should not be blindly overwritten

* Current repo uses `STATUS_AUTH_INVALID = "auth_invalid"` and an account-state machine where AUTH_PENDING maps to auth invalid semantics. Target repo uses `STATUS_AUTH_PENDING = "auth_pending"`. Migration must map concepts, not copy constants.
* Current repo has newer `RegisterPathRotator`, multi-provider mail fallback, multi-master scaffolding, frontend status display, and stronger CPA live quota decision logic. Target `manager.py`, `api.py`, or `cpa_sync.py` should not be copied wholesale.
* CPA sync in current repo already has a local `_active_auth_publish_decision` with live quota checks, disabled-account skip, personal credential handling, IPv6 proxy refresh, and delete guard. Target ideas should be compared at behavior level only.

## External practice check

Grok Search query on SaaS seat rotation and lifecycle automation returned consistent general guidance:

* Deprovision or deactivate the old user/seat first, confirm capacity, then provision the replacement.
* Preflight current seat count and quota before adding.
* Make operations retry-safe and idempotent.
* Use background jobs plus full/incremental reconciliation, with audit logs and failure alerts.

These are compatible with the target repo's remove-before-create and validation direction, but current implementation details must still be governed by local code.

## Recommended migration slices

### Slice A: Safe rotation core (recommended MVP)

Implement target-equivalent blocker classification, remove-before-create, child validation, cooldown semantics, rotate heartbeat, and duration fuse in current code. Preserve current registration provider/fallback stack and multi-master scaffolding.

### Slice B: Direct signup race integration

After Slice A, wire target direct registration race into current `create_account_direct` / `RegisterPathRotator` path and multi-master browser budget. This has higher Playwright resource risk.

### Slice C: Broad target parity

Attempt to converge all target repo rotation/registration behaviors in one larger implementation. This is highest risk because current repo has newer divergent architecture and many active Trellis tasks.
