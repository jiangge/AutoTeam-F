# Runtime and Docker Hardening

## Scenario: Docker-Bounded Playwright Runtime

### 1. Scope / Trigger

- Trigger: any change that touches Docker runtime settings, Playwright lifecycle management, runtime resource probes, background browser probes, `CHATGPT_API_TRANSPORT`, or per-account IPv6 proxy isolation.
- Goal: keep browser automation bounded and observable without changing the free-account registration main flow.
- Applies to:
  - `docker-compose.yml`
  - `Dockerfile.fast`
  - `docker-entrypoint.sh`
  - `src/autoteam/runtime_resources.py`
  - `src/autoteam/playwright_lifecycle.py`
  - `src/autoteam/playwright_probe.py`
  - `src/autoteam/ipv6_pool.py`
  - `src/autoteam/ipv6_proxy.py`
  - `src/autoteam/chatgpt_transport.py`
  - `src/autoteam/chatgpt_api.py`
  - `src/autoteam/cpa_sync.py`
  - `src/autoteam/api.py`

### 2. Signatures

- `collect_runtime_resource_snapshot() -> dict[str, Any]`
- `log_runtime_resource_snapshot(logger: Any, *, label: str = "runtime") -> dict[str, Any]`
- `GET /api/status?fast=true`
- `bump_task_progress(stage: str = "") -> None`
- `_record_task_progress(task: dict, stage: str, now: float | None = None) -> None`
- `close_playwright_objects(page=None, context=None, browser=None, playwright=None, *, logger=None, label="playwright") -> None`
- `python -m autoteam.playwright_probe team-member-count`
- `_TeamMemberCount(int)` with `.invites` and `.occupancy`
- `_team_member_invite_count(team_count) -> int`
- `_team_member_occupancy(team_count) -> int`
- `ChatGPTTeamAPI.start_with_session(session_token, account_id, workspace_name="", require_browser=False)`
- `ChatGPTTeamAPI.stop() -> None`
- `MainCodexLoginFlow.complete() -> dict`
- `MainCodexSyncFlow.complete() -> dict`
- `_workspace_candidate_kind(text: str | None) -> str | None`
- `ChatGPTTeamAPI._wait_for_post_workspace_ready(timeout=12) -> bool`
- `_select_existing_api_organization(page) -> bool`
- `_select_choose_account(page, email: str | None) -> bool`
- `_classify_oauth_failure(url: str, body_excerpt: str) -> tuple[str, str, bool]`
- `_recover_oauth_timeout_page(page) -> bool`
- `_recover_oauth_no_valid_organizations_page(page) -> bool`
- `_complete_oauth_login_challenge(page, email, password, mail_client, min_email_id, used_email_ids) -> bool`
- `_fetch_team_session_bundle_from_context(context, email: str, account_id: str | None, *, stage_label: str, attempts: int = 3) -> dict | None`
- `login_codex_via_browser(..., pre_signed_in_cookies: list | None = None, return_result: bool = False)`
- `build_chatgpt_transport(session_token: str, account_id: str = "", oai_device_id: str = "", proxy_url: str | None = None)`
- `get_chatgpt_http_proxy_url(proxy_url: str | None = None) -> str`
- `get_cliproxy_health() -> dict[str, Any]`
- `_collect_cpa_credential_gate() -> dict[str, Any]`
- `_cpa_provider_auth_below_pool_target(gate: dict | None, pool_target: int) -> bool`
- `_auth_repair_error_label(error_type: str | None) -> str`
- `_oauth_retry_delay_seconds(error_type: str | None) -> int`
- `_login_codex_with_result(email, password, *, mail_client=None, max_attempts=3, signup_profile=None, pre_signed_in_cookies=None, playwright_proxy_url=None) -> dict`
- `cmd_check(include_standby=False, *, force_auth_repair=False, preserve_low_active=False, preserved_low_accounts=None) -> list`
- `_historical_low_quota_info(acc, threshold, now=None) -> dict | None`
- `_record_auth_repair_failure(email, error_type=None, error_detail=None, *, chatgpt_api=None) -> dict`
- `_can_replace_protected_managed_auth_failure(acc, *, error_type=None, reason=None, missing_auth=False) -> bool`
- `_should_aggressively_release_auth_failure(error_type, *, discard_failed_repair) -> bool`
- `_discard_auth_repair_failed_account_record(email, reason, *, status=STATUS_STANDBY, now=None) -> None`
- `cmd_rotate(target_seats=3, force_auth_repair=False, background_post_sync=False)`
- `IPv6Pool.start(active_emails: Iterable[str] | None = None) -> None`
- `IPv6Pool.ensure_proxy_for_account(email: str) -> tuple[str, str]`
- `IPv6Pool.release_proxy_for_account(email: str) -> None`
- `IPv6Pool.status() -> dict[str, Any]`

### 3. Contracts

- Docker Compose must keep:
  - `services.autoteam.init: true`
  - `services.autoteam.shm_size` at least `1gb`
  - `services.autoteam.mem_limit` and `memswap_limit`
  - `services.autoteam.pids_limit`
  - healthcheck using `curl -fsS http://127.0.0.1:8787/api/version`
  - build args `GIT_SHA` and `BUILD_TIME`
- Runtime env keys:
  - `AUTOTEAM_MEMORY_WARN_RATIO`, default `0.85`
  - `AUTOTEAM_ZOMBIE_WARN_THRESHOLD`, default `20` in code; compose may use a stricter value
  - `CHATGPT_API_TRANSPORT`, default `auto` to match `D:\Desktop\autoteam-1\AutoTeam`
  - `CHATGPT_API_HTTP_TIMEOUT`, default `60`
  - `CHATGPT_API_IMPERSONATE`, default `chrome136`
  - `AUTOTEAM_IPV6_POOL_ENABLED`, default `false`
  - `AUTOTEAM_IPV6_POOL_REQUIRED`, default `false`
  - `IPV6_PREFIX` and `IPV6_IFACE`, required only when the IPv6 pool is enabled
  - `IPV6_PROXY_*` keys for local listen, public auth URL, allowed IPs, port range, TTL, and pool persistence
- `CHATGPT_API_TRANSPORT=curl_cffi` or `auto` is allowed only for backend API reads. It must not be used for free registration, Personal OAuth, captcha/challenge flows, or workspace UI selection; those call sites must force `require_browser=True` or launch their own Playwright context.
- `/api/status` may include `runtime_resources`, but resource collection must never block or fail the status response.
- `/api/status?fast=true` is the polling-safe status path. It must skip live Codex quota checks, keep the ordinary account/status summary shape, use a bounded CLIProxy health read, and return `status_mode.fast=true` with `live_quota=false`.
- Background Team member count probes must run in a killable subprocess and return unknown (`-1`) on timeout/failure.
- `python -m autoteam.playwright_probe team-member-count` must return `count`, `invites`, and `occupancy=count+invites` when Team state is readable. `_auto_check_team_member_count()` must preserve `int` compatibility while carrying invite/occupancy metadata through `_TeamMemberCount`.
- Auto-check must treat pending Team invites as remote seat occupancy. If `members + invites > target_seats`, it should trigger `auto-cleanup` with diagnostic params `team_count`, `invite_count`, and `team_occupancy`; it must not treat unknown pending invites as safe-delete evidence.
- Auto-check remains a single-main flow: `target_seats` is the total Team cap for one owner/main plus managed children, and provider-auth low-watermark targets only the managed-child pool (`target_seats - 1`). This contract must not enable or depend on multi-owner scheduling.
- `ChatGPTTeamAPI.start_with_session()` must call `stop()` if the browser fallback path fails after partial initialization, not only when `_launch_browser()` itself fails.
- `ChatGPTTeamAPI.start_with_session()` must also call `stop()` when HTTP transport startup succeeds but later workspace detection or admin-state persistence fails.
- Direct HTTP API fetches must close and clear the bad `http_transport` before browser fallback when the transport raises, returns HTML/challenge, or fails again after a 401-triggered token refresh retry.
- Registration and OAuth Playwright call sites must use `close_playwright_objects()` rather than raw `browser.close()`, `context.close()`, or `page.close()`. Direct registration paths need a `try/finally` guard so unexpected page/navigation errors still release page, context, and browser.
- `SessionCodexAuthFlow.start()` must stop its `ChatGPTTeamAPI` instance if page creation, cookie injection, navigation, or the first `_advance()` fails after `start_with_session(require_browser=True)`.
- Workspace selection helpers must filter page headings, legal links, one-time-code actions, and generic organization setup cards out of selectable workspace labels. Personal/free/new-organization options may be exposed only as fallback candidates, never as preferred Team workspaces.
- `codex_auth.py` may expose compatibility wrappers for shared `oauth_workspace.py` detectors/selectors, but the implementation source of truth stays in `oauth_workspace.py`.
- After a ChatGPT workspace option is selected, `ChatGPTTeamAPI.select_workspace_option()` must wait briefly for post-selection readiness and treat a stable `chatgpt.com` home page as `completed`, even if no session cookie was newly extracted.
- Codex OAuth lightweight helpers may improve organization/account-choice pages, trace filtering, retryable error classification, timeout/no-valid-organization recovery, and login-challenge completion, but they must not alter the higher-level `login_codex_via_browser()` return contract or session-bundle extraction policy without a separate behavior review.
- OTP rejection caching must hash the rejected OTP value and retain bounded recent metadata. Do not persist raw OTP codes in the rejection cache.
- OTP submit result detection may treat OAuth progress URLs such as consent, organization, choose-account, about-you, and OAuth authorize/continue pages as accepted progress, not as rejection.
- `pre_signed_in_cookies` is an explicit `login_codex_via_browser()` opt-in. When provided for Team auth, the function may attempt `_fetch_team_session_bundle_from_context()` before the full OAuth challenge flow. Default callers must keep receiving the legacy bundle/`None` return shape.
- `return_result=True` is an explicit compatibility wrapper for callers that need `{ok, bundle, error_type, error_detail, retryable}`. Do not change existing default callers to expect that wrapper object.
- `_login_codex_with_result()` is the manager-side normalization wrapper for auth-repair callers. It may call `login_codex_via_browser(..., return_result=True)` and must return a dict containing `ok`, `bundle`, `error_type`, `error_detail`, `retryable`, and `attempts`. It must reject non-Team bundles as `error_type="non_team_plan"` and must not change `cmd_check` or Team-seat release policy merely by existing.
- Auth-repair single-attempt failure types such as `add_phone`, `human_verification`, `email_verification`, `login_state_lost`, `account_selection`, and `no_valid_organizations` must not be retried repeatedly inside the same `_login_codex_with_result()` call. Let the surrounding auth-repair state machine handle cooldown, pause, or release decisions.
- `cmd_check()` must keep `include_standby` as the first positional argument and expose auth-repair controls only as keyword-only arguments: `force_auth_repair`, `preserve_low_active`, and `preserved_low_accounts`.
- `cmd_check()` must scan both active rows and auth-repair-pending rows. Current persisted auth-repair-pending rows use `STATUS_AUTH_INVALID` (`"auth_invalid"`); target-style `"auth_pending"` may be accepted as legacy input but must not replace the current persisted state literal.
- `force_auth_repair=True` bypasses `auth_retry_after` and `auth_retry_paused` skip checks for eligible rows. Default `False` must continue respecting cooldown and pause metadata.
- Auth-repair login from `cmd_check()` must route mail through the account's configured provider (`mail_provider`, `mail_account_id`, or `cloudmail_account_id`) rather than blindly using the global default provider.
- When the live quota call returns `network_error`, `_historical_low_quota_info()` may use saved `last_quota` only if the relevant reset window has not elapsed. It must ignore stale historical low quota after reset time.
- With `preserve_low_active=True`, active low-quota rows discovered from live quota or historical quota should be appended to `preserved_low_accounts` and not marked `STATUS_EXHAUSTED` in that check pass. Default mode may still mark historical-low rows exhausted.
- `_record_auth_repair_failure()` must preserve current state-machine semantics: final auth-pending state is persisted as `STATUS_AUTH_INVALID`, and status writes may include `_reason` for transition logging.
- `_record_auth_repair_failure()` may release a Team blocker after repeated `email_verification` exhausts the retry budget, and may release missing-auth `login_state_lost` / organization-selection blockers when they occupy a Team seat.
- Protected local credential seats (`protect_team_seat=True` or a non-provider local auth file) must not be released by `login_state_lost`; they should pause repair and stay in the current auth-pending state.
- Protected AutoTeam-managed child seats with a mail binding (`mail_account_id` or `cloudmail_account_id`) are different from manual/local credential seats. If concrete auth-failure evidence exists (`auth_error_discard`, `missing_auth_file`, `auth_retry_paused`, `auth_retry_after`, `non_team_plan`, `oauth_timeout`, `login_failed`, etc.), `_can_replace_protected_managed_auth_failure()` may override stale protection flags so rotation can release/retire the child and restore capacity.
- When an auth-repair failure successfully releases a Team seat and `ROTATE_SKIP_REUSE=true`, the local row should be retained for evidence but marked `disabled=True`, `reuse_disabled=True`, and `retired_reason="auth_repair_failed:<type>"` so automated standby reuse cannot select it.
- When add-phone soft retry is disabled, current capacity-first behavior treats `add_phone` as a hard managed-child blocker that may release the Team seat. Do not migrate target's pause-without-release behavior unless the operator policy is explicitly changed.
- Target assertions that require persisted `"auth_pending"` or exact `update_account(email, {"status": ...})` calls are incompatible with the current account-state lifecycle and are not migration requirements.
- Session fallback bundles may be built from `/api/auth/session.accessToken` only after the browser context is loaded against the intended Team workspace. JWT claims should be accepted when they already show `plan_type=team`; stale JWT workspace claims may be accepted only when a browser-context quota probe verifies the intended Team account.
- Auth-repair diagnostics should map transient OAuth/organization errors such as `oauth_timeout`, `unsupported_region`, `account_selection`, and `no_valid_organizations` to readable labels and bounded same-round retry delays. This is diagnostic/retry pacing only; it must not change hard Team-seat cap behavior.
- `POST /api/main-codex/login` is the local-only main-Codex path: it may save the main auth file but must not call CPA/Sub2API sync or delete helpers.
- `POST /api/main-codex/start` is the remote-sync path: it must require at least one fully configured enabled sync target before starting browser work or syncing an existing local main auth file.
- `POST /api/main-codex/delete-remote-files` and legacy `POST /api/main-codex/delete-cpa` are explicit remote deletion actions. They must use `delete_main_codex_from_configured_targets()` through the configured target router and summarize the deleted CPA/Sub2API filenames.
- API-driven `rotate`, `auto-fill`, and `auto-rotate` must not block task completion on CPA/CLIProxyAPI remote sync. Use `background_post_sync=True` so `cmd_rotate()` schedules final sync after the Playwright-bound operation releases task state.
- Long-running background tasks must maintain `last_progress_at`, `progress`, and bounded `progress_history` stage timings. Preserve the existing cancellation ordering: reset the cancellation signal before exposing `_current_task_id`, then allow `bump_task_progress()` to update the active task.
- Auto-check must not run expensive probes while a Playwright-bound task is active. If `_playwright_lock` is locked or `_current_task_id` is set after the interval wait, skip that round before loading accounts, reading CLIProxy health, or launching Team-member probes.
- IPv6 proxy isolation is opt-in. Disabled-by-default installs must not create local proxy processes, mutate network state, or require IPv6 kernel configuration.
- When `AUTOTEAM_IPV6_POOL_REQUIRED=true`, allocation/preflight failure is a hard business/runtime error. Do not silently fall back to direct network access.
- Account-scoped browser and HTTP transport paths must propagate the allocated local proxy URL into Playwright launch options and `curl_cffi` transport construction. Persisted auth bundles should store the public/auth proxy URL only when one was allocated.
- Temporary registration proxies must be released when registration, duplicate-email retry, phone/add-phone terminal failure, or post-registration OAuth fails before the account becomes usable.
- API startup may pre-warm the IPv6 pool only for non-main, non-disabled active accounts. Shutdown must stop pool proxies after Playwright executor cleanup.
- `/api/status` may include `ipv6_pool`, but IPv6 status collection must never block or fail the status response. Return a diagnostic `ipv6_pool.error` instead of raising a 500.
- `/api/status` may include `cliproxy` and `rotation_validation`. These fields are additive and must not remove or rename existing status fields.
- `cliproxy` health must stay read-only. It may read CLIProxyAPI management metadata (`/v0/management/auth-files`) and provider availability counts, but must never call sync/upload/delete/refresh endpoints.
- Auto-check may use CLIProxyAPI provider-auth metadata only as a read-only CPA credential gate. The gate is enabled only when CPA sync is configured/enabled, must call `get_cliproxy_health(..., force_refresh=True)` without sync/upload/delete side effects, and may treat provider auth as zero only when `management_ok=true` and `available <= 0`.
- Provider-auth low-watermark is a proactive signal, not only a zero-credential signal. When the gate is enabled, `safe_read_only=true`, `management_ok=true`, and `provider_auth.available < pool_active_target`, auto-check may trigger `auto-rotate` / sync with params `provider_auth_below_target`, `provider_auth_available`, and `provider_auth_target`; post-task runtime validation should degrade with `provider_auth_available=<available>/<target>`.
- When Team is full but local active child count is below the target and the CPA credential gate reports zero available credentials, auto-check may trigger the normal `auto-fill` / `cmd_rotate(..., background_post_sync=True)` path. This is a replacement/fill decision, not a remote CPA mutation.
- `zero_available` and provider-auth low-watermark must require `safe_read_only=true`. A management failure, malformed response, or non-read-only health check is unknown and must not trigger replacement.
- Remote capacity preflight for direct registration may use `members+invites` only after `ChatGPTTeamAPI` is actually ready. Dynamic mock/duck attributes must not be allowed to spoof readiness; if `start()` returns without a ready browser/http transport, skip the remote preflight rather than calling Team APIs on an unusable session.
- `rotation_validation` must distinguish `ok`, `degraded`, and hard `failed` results. Hard post-task validation failure may convert a superficially completed mutation task into `failed`; degraded results keep operation success visible and expose cooldown/follow-up metadata.
- `sync_to_cpa()` must refresh `proxy_url` in auth JSON for active/personal, non-disabled local accounts before upload. In required mode refresh failure must fail the sync; in non-required mode it may warn and upload the existing file.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| `/proc` or cgroup files missing | Resource snapshot fields become `None`; no exception escapes |
| `ps` unavailable or times out | Browser process counts become zero; no exception escapes |
| cgroup memory ratio >= threshold | Log a warning and run best-effort `gc.collect()` |
| browser zombie count >= threshold | Log a warning that init/reaper should be enabled |
| Playwright page/context/browser/stop raises during cleanup | Log debug when logger exists; continue cleanup and do not re-raise |
| `_launch_browser()` partially initializes then fails | Call `stop()` and re-raise the original exception |
| `start_with_session(..., require_browser=True)` or browser fallback starts Playwright then fails during navigation/token/workspace setup | Call `stop()` and re-raise the original exception |
| probe subprocess timeout | Kill the process group/tree and treat count as unknown |
| Team probe returns members and pending invites | Preserve `count`, `invites`, and `occupancy`; use occupancy for over-target cleanup |
| Team probe returns `count=3, invites=1, occupancy=4` for target 3 | Trigger `auto-cleanup` and include `invite_count=1`, `team_occupancy=4` in task params |
| `curl_cffi` missing or transport init fails | Return `None`; continue with Playwright |
| transport returns HTML/challenge/401 token missing | Fall back to Playwright API fetch |
| `ChatGPTTeamAPI.start()` succeeds via HTTP transport only | Cleanup and reuse checks must use `is_started()` / `_chatgpt_session_ready()`, not `browser` alone |
| `http_transport.request()` raises before or after token refresh retry | Close/clear the transport, then fall back to Playwright using the saved `session_token` |
| invite/direct registration or Codex OAuth opens a Playwright page then raises before a normal return | Cleanup must still close page, context, and browser in dependency order |
| `SessionCodexAuthFlow.start()` fails after creating a `ChatGPTTeamAPI` | Call `stop()` and clear `chatgpt` / `page` fields |
| Main-Codex login action completes | Return `message="主号 Codex 已登录"` and clear `action` from status |
| Main-Codex sync action is requested with no enabled target | Return HTTP `400` before browser work or remote mutation |
| Main-Codex remote deletion is requested | Require an enabled target, delete only via the configured target router, and expose per-target results |
| `cmd_check(force_auth_repair=False)` sees a cooled-down auth-pending row | Skip repair and log the cooldown/pause reason |
| `cmd_check(force_auth_repair=True)` sees a cooled-down auth-pending row | Attempt auth repair through the account-routed mail provider |
| live quota returns `network_error` and saved `last_quota` is low but not reset | Default mode may mark exhausted; preserve-low-active mode records the row as a rotation candidate without changing status |
| live quota returns `network_error` and saved `last_quota` reset time has passed | Ignore historical-low decision and preserve current credential/seat state |
| repeated `email_verification` exhausts auth-repair retry budget | Pause repair, release the Team seat when present, and retire/disable the released local row under skip-reuse mode |
| `login_state_lost` has no usable local auth file and blocks Team capacity | Pause repair, release the Team seat when present, and retire/disable the released local row under skip-reuse mode |
| `login_state_lost` has a protected local credential auth file | Pause repair without releasing the Team seat or disabling the row |
| `auth_error_discard` or another concrete auth failure hits a protected AutoTeam-managed child with a mail binding | Allow the protected replacement override, release the Team seat when present, and retire/disable the row under skip-reuse mode |
| `auth_retry_paused` / `auth_retry_after` is present on a protected AutoTeam-managed child | Treat it as a replaceable pool blocker; do not let stale `protect_team_seat` block rotation |
| the same auth-failure signal hits a protected manual/local credential row without mail binding | Preserve the seat; do not release or retire the row automatically |
| `collect_runtime_resource_snapshot()` unexpectedly raises inside `/api/status` | Return a status response with a diagnostic `runtime_resources.error`; do not raise a 500 |
| `/api/status?fast=true` is called while rotate/fill is running | Return account/resource snapshot without live quota probes and with bounded CLIProxy health metadata |
| background task calls `bump_task_progress("stage")` repeatedly | Update task heartbeat and append/refresh a bounded stage history |
| auto-check wakes while `_playwright_lock` or `_current_task_id` indicates an active task | Log a skip message and do not load accounts, query CPA gate, or launch Team-member probes |
| CLIProxyAPI health config is missing or unreachable | Return `cliproxy.ok=false`, `safe_read_only=true`, and a reason; do not raise a 500 |
| CLIProxyAPI auth-file payload is malformed | Return provider/management diagnostic fields; do not treat it as an empty healthy provider set |
| CPA sync target is disabled | `_collect_cpa_credential_gate()` returns `enabled=false`; auto-check behavior is unchanged |
| CPA sync target is enabled and CLIProxyAPI management reports `available=0` with `management_ok=true` | Gate returns `zero_available=true`; a full Team with too few local active children may trigger `auto-fill` |
| CPA sync target is enabled and CLIProxyAPI management reports `available=1` while `pool_active_target=2` | Gate remains non-zero but below target; auto-check may trigger preventive `auto-rotate` / sync and runtime validation degrades |
| CLIProxyAPI management check fails | Gate returns `management_ok=false`, `zero_available=false`; do not interpret this as no credentials |
| CLIProxyAPI health is not confirmed read-only | Do not treat `available=0` or below-target as actionable rotation evidence |
| `ChatGPTTeamAPI.start()` returns but no browser/http transport is ready | Do not fetch Team members/invites; keep direct registration fallback behavior |
| post-task remote sync fails after API-driven rotate | Log a warning, keep the local rotation result, and leave task completion unblocked |
| post-task runtime validation is degraded | Keep the task completed, record reasons and cooldown/follow-up metadata |
| post-task runtime validation is a hard failure | Convert the task to `failed` with a business reason |
| IPv6 pool is disabled | Do not start proxies; status should report disabled/no allocations |
| IPv6 allocation fails while required mode is true | Raise a clear error and do not continue direct |
| IPv6 allocation fails while required mode is false | Log a warning and continue only through the existing direct-path fallback |
| IPv6 status collection raises inside `/api/status` | Return a status response with a diagnostic `ipv6_pool.error`; do not raise a 500 |
| CPA proxy refresh fails while required mode is true | Raise and stop the sync rather than uploading stale direct auth |

### 5. Good/Base/Bad Cases

- Good: `docker compose config` shows init, shm, memory, PID, healthcheck, and build args; `docker run --rm autoteam:fast-0515 status` passes self-check.
- Base: local non-Docker startup still uses the same Python modules and defaults to `auto`, while browser-dependent flows force Playwright explicitly.
- Bad: letting `auto` leak into OAuth/UI flows, swallowing Playwright init failures without cleanup, or running periodic Team count checks in the long-lived API process.
- Bad: guarding `stop()` with `if api.browser` after `auto` transport is enabled; HTTP-only sessions would leak.
- Bad: keeping a failed `http_transport` after browser fallback; the next `_api_fetch()` would retry the same known-bad transport instead of using the live browser session.
- Bad: replacing direct registration's final `browser.close()` but leaving unexpected navigation errors outside a `finally` cleanup guard.
- Bad: adding a proxy URL to saved auth bundles without actually launching browser/API requests through the same account proxy.
- Bad: treating required-mode IPv6 failures as warnings; this hides pool exhaustion and defeats isolation.
- Bad: using `/api/sync`, `upload_to_cpa()`, or `delete_from_cpa()` as part of the CPA credential gate. The gate is diagnostic/read-only and must not mutate remote credentials.
- Bad: treating a failed CLIProxyAPI management request as `available=0`; this would trigger unnecessary rotation on unreliable evidence.
- Bad: using full `/api/status` as a high-frequency frontend polling endpoint during rotation; it can spend real quota-probe time and interfere with Playwright-bound work.
- Bad: running auto-check's Team-member/CPA/account probes while another task already holds the Playwright lock.

### 6. Tests Required

- Docker contract: `tests/integration/test_docker_guard.py`
- Resource probe: `tests/unit/test_runtime_resources.py`
- Playwright cleanup and subprocess probe behavior: `tests/unit/test_api_playwright_cleanup.py`
- API status resource-snapshot boundary: `tests/unit/test_api_status.py`
- HTTP transport auto/fallback: `tests/unit/test_chatgpt_transport.py`
- Direct registration and OAuth cleanup source/exception guards:
  - `tests/unit/test_api_playwright_cleanup.py`
  - `tests/unit/test_round11_session_token_injection.py`
- Main-Codex login/sync/delete target boundaries:
  - `tests/unit/test_api_main_codex_after_admin.py`
  - `tests/unit/test_round10_master_codex_session.py`
- Workspace/OAuth helper parity:
  - `tests/unit/test_workspace_oauth_parity.py`
  - `tests/unit/test_round11_oauth_workspace_consent.py`
  - target-only comparison runs may include `D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_chatgpt_workspace.py` and `D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_codex_auth_session.py`.
  - selected target `test_signup_flow_profiles.py` assertions may be used for lightweight OAuth helper parity, split-code target waits, session-bundle extraction, and explicit browser-login result wrapping. Full-file target parity is not required when the only failures are the rejected old positional `SignupProfile` constructor shape.
  - selected target `test_manager_auth_repair.py` assertions may be used for `_login_codex_with_result()` result-wrapper parity, `cmd_check(...force_auth_repair...)`, historical-low-quota network-error handling, and protected/released Team blocker behavior. Full-file target parity is not required while remaining failures describe target-only `"auth_pending"` persisted literals, exact `update_account()` call shape, or the rejected add-phone retry-disabled no-release policy.
  - current `tests/unit/test_round12_s3_cherry_pick.py::TestCmdCheckAuthRepairEntry` and `::TestRecordAuthRepairFailure` must cover the adapted current behavior.
  - `tests/unit/test_round12_s3_cherry_pick.py::TestRecordAuthRepairFailure` must cover protected managed-child release and manual protected credential preservation.
  - `tests/unit/test_manager_rotate.py::test_replaceable_pool_blocker_reason_reports_concrete_evidence` must cover protected managed-child blocker classification and manual protected credential exclusion.
- Status endpoint integration: `tests/unit/test_api_status.py`
  - fast status skips live quota probes and uses bounded CLIProxy health reads.
  - active tasks record progress history from `bump_task_progress()`.
- CLIProxyAPI read-only health: `tests/unit/test_cliproxy_health.py`
- CPA credential gate for auto-check: `tests/unit/test_api_status.py`
  - Auto-check skips expensive probes while a task is active.
  - Full Team + local active shortage + `management_ok=true` + `available=0` triggers `auto-fill` without sync/upload/delete.
  - Management failure with `available=0` does not trigger replacement.
  - Provider-auth `available < pool_active_target` triggers preventive `auto-rotate` / sync with provider-auth task params.
  - Runtime validation degrades when provider-auth is below target.
  - Non-read-only CLIProxy health does not produce `zero_available` or below-target action.
  - Pending invites count toward remote occupancy and over-target occupancy triggers `auto-cleanup`.
  - `_auto_check_team_member_count()` preserves `int` compatibility while carrying invite/occupancy metadata.
- Rotate deferred post-sync and validation plumbing: `tests/unit/test_manager_rotate.py` and `tests/unit/test_api_status.py`
- IPv6 pool/proxy persistence and strict required-mode behavior: `tests/unit/test_ipv6_pool.py`
- IPv6 status and status-failure boundary: `tests/unit/test_api_status.py`
- CPA auth proxy refresh before upload: `tests/unit/test_cpa_sync.py`
- Free registration regression:
  - `tests/unit/test_round11_personal_oauth_retry.py`
  - `tests/unit/test_round11_session_token_injection.py`
  - `tests/unit/test_round12_s4_register_dual_path.py`
  - `tests/unit/test_manager_fill.py`

### 7. Wrong vs Correct

#### Wrong

```python
def start_with_session(self, session_token, account_id):
    self.http_transport = build_chatgpt_transport(...)
    # This silently changes all callers to HTTP-first behavior, including flows
    # that require a real browser context.
```

#### Correct

```python
def start_with_session(self, session_token, account_id, workspace_name="", require_browser=False):
    if not require_browser and self._start_transport_session(session_token):
        ...
    self._start_browser_session(session_token)
```

Use `require_browser=True` for any path that depends on a real browser context. Keep the default environment value aligned with `autoteam-1` as `auto`, and keep `curl_cffi` isolated to backend API reads/writes plus browser fallback.

## Scenario: Multi-Master Owner Fill Scheduling

### 1. Scope / Trigger

- Trigger: any change to multi-Team owner scheduling, `/api/tasks/multi-master/fill`, `/api/status.multi_master`, workspace-pool owner metadata, or owner/direct-registration concurrency budgets.
- Goal: allow several imported Team owners to fill their own managed children inside one observable API task while preserving the single-Team `1 owner + 2 managed children = 3 seats` cap.
- Applies to:
  - `src/autoteam/multi_master.py`
  - `src/autoteam/workspace_pool.py`
  - `src/autoteam/admin_state.py`
  - `src/autoteam/api.py`
  - `src/autoteam/manager.py::cmd_fill`

### 2. Signatures

- `WorkspacePool.upsert(workspace_id, admin_email, account_id, tier=TIER_WARM, *, workspace_name="", session_token="", enabled=True, parallel=False) -> dict`
- `WorkspacePool.record_run_result(workspace_id, *, last_error="", last_run_ts=None) -> dict`
- `temporary_admin_state(**kwargs) -> contextmanager`
- `build_multi_master_status(accounts=None, pool=None) -> dict`
- `resolve_worker_budget(owner_count, *, requested_owner_workers=None, requested_direct_parallel=None, runtime_snapshot=None) -> dict`
- `run_multi_master_fill(target_seats=3, *, owner_workers=None, direct_parallel=None, workspace_ids=None, dry_run=False, post_sync=True, pool=None, worker=None) -> dict`
- `cmd_fill(target=3, leave_workspace=False, *, post_sync=True, print_status=True, direct_parallel=None)`
- `POST /api/tasks/multi-master/fill`

### 3. Contracts

- A multi-master task is one API mutation task. Do not open independent untracked API mutation tasks for each owner.
- `target_seats_per_owner` must stay clamped to `1..3`; `child_cap_per_owner` is `2`.
- Eligible owner rows come from `WorkspacePool` rows with `enabled != false`, `parallel == true`, `admin_email`, and `account_id`. If none are marked parallel, read-only planning/status may fall back to the active workspace for backwards compatibility.
- Per-owner workers must use `temporary_admin_state(...)` so `ChatGPTTeamAPI.start()` reads the owner-local session/account/workspace data without mutating global `state.json`.
- Owner worker failures are isolated. One failed owner becomes one failed result row and must not prevent other submitted owners from completing.
- `session_token` may be persisted in the local workspace pool for imported owners, but API status and task results must expose only `session_present`, never the raw token.
- `MULTI_MASTER_MAX_OWNER_WORKERS`, `MULTI_MASTER_BROWSER_BUDGET`, `MULTI_MASTER_MEMORY_DOWNGRADE_RATIO`, and `DIRECT_REGISTER_PARALLEL` are the scheduling budget inputs. `run_multi_master_fill()` must pass the resolved `direct_register_parallel` into `cmd_fill(..., direct_parallel=...)`, and `cmd_fill()` must pass it into `create_new_account(..., parallel=...)`.
- When owner workers call `cmd_fill`, they must set `post_sync=False`, `print_status=False`, and the budgeted `direct_parallel` value. The parent multi-master task may run CPA sync once after all owners finish; a post-sync failure should be reported in `post_sync` without converting completed owner work into failed owner work.
- `/api/status.multi_master` is additive. It must not remove or rename existing status fields and must not raise a 500 if multi-master diagnostics fail.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| No eligible owners | Return `status="no_owners"` and `owner_workers=0`; do not start owner work |
| `dry_run=true` | Return a completed plan without creating a background task |
| Owner row has no session token | Mark it non-runnable in status; execution may fail only that owner |
| Runtime memory ratio >= `MULTI_MASTER_MEMORY_DOWNGRADE_RATIO` | Force `owner_workers=1` and `direct_register_parallel=1` with reason `memory_high` |
| `owner_workers * direct_register_parallel` exceeds `MULTI_MASTER_BROWSER_BUDGET` | Clip both values to stay within the global browser budget |
| Owner worker starts `cmd_fill` | Pass the resolved `direct_parallel`; do not leave it as display-only metadata |
| One owner worker raises | Record `last_error` for that workspace and return overall `partial_failed` when other owners complete |
| All owner workers raise | Return overall `failed` |
| Parent post-sync raises | Return `post_sync.ok=false`; keep per-owner results intact |
| `/api/status.multi_master` builder raises | Return an error diagnostic block instead of failing `/api/status` |

### 5. Good/Base/Bad Cases

- Good: two imported owners marked `parallel=true` are filled inside one `multi-master-fill` task, each owner uses its own temporary admin state, and final `post_sync` runs once.
- Good: a multi-master dry-run/result reports the same `direct_register_parallel` that execution passes into `cmd_fill`.
- Base: a single-owner install with no parallel rows still reports compatible status and can dry-run against the active workspace.
- Bad: increasing `target` above `3` to gain throughput, because this breaks the Team-seat contract.
- Bad: calling `cmd_fill()` concurrently with its default `post_sync=True`, because each worker would race remote CPA sync and make delete-guard behavior harder to reason about.
- Bad: returning `session_token` in `/api/status.multi_master.owners` or task result rows.

### 6. Tests Required

- `tests/unit/test_multi_master.py`
  - `temporary_admin_state` overrides owner state without mutating disk.
  - `WorkspacePool.upsert` persists owner metadata and keeps the active-workspace invariant.
  - `build_multi_master_status` groups accounts by `workspace_account_id` and omits session tokens.
  - `resolve_worker_budget` downgrades on high memory and clips by browser budget.
  - `run_multi_master_fill` isolates owner failures, records `last_error`, suppresses worker-local sync/status, passes `direct_parallel` into `cmd_fill`, and reports parent `post_sync`.
  - API dry-run returns a plan and passes request parameters through.
- Existing single-owner regressions must still pass:
  - `tests/unit/test_round12_s7_workspace_pool.py`
  - `tests/unit/test_api_status.py`
  - `tests/unit/test_manager_fill.py`
  - `tests/unit/test_manager_rotate.py`

### 7. Wrong vs Correct

#### Wrong

```python
# Starts several independent mutation tasks; each task owns its own view of
# Playwright/resource state and may race the global task lock.
for owner in owners:
    post_fill(TaskParams(target=3))
```

#### Correct

```python
run_multi_master_fill(
    target_seats=3,
    owner_workers=2,
    direct_parallel=1,
)
```

Keep multi-owner work inside one parent task, and make owner-local state explicit with `temporary_admin_state(...)`.
