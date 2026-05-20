# autoteam-1 full parity matrix

Date: 2026-05-19

## Objective Restatement

User objective: absorb all good points from `D:\Desktop\autoteam-1\AutoTeam` into
the current repo `D:\Desktop\AutoTeam`.

Concrete success criteria:

1. Every recent target-repo improvement is mapped to current code, tests, specs, or
   an explicit migration decision.
2. Existing current-repo superior/incompatible implementations are preserved.
3. Remaining gaps become small implementation slices, not whole-file overwrites.
4. The final completion decision must be based on real artifacts and test/runtime
   evidence, not on commit count or broad similarity.

## Target Recent Commit Matrix

Target recent commits inspected with `git -C D:/Desktop/autoteam-1/AutoTeam show --stat --oneline`:

| Target commit | Capability | Current evidence | Status | Notes |
| --- | --- | --- | --- | --- |
| `c93d246 fix: prefer domain auto-join for rotation account creation` | rotation new-account creation should prefer verified-domain auto-join, expose invite/direct mode switches, and keep invite-link registration as fallback | `src/autoteam/manager.py` has `ROTATE_NEW_ACCOUNT_MODE` strategy helpers, domain allowlist helpers, `create_account_via_invite`, and direct->invite fallback; `src/autoteam/config.py`, `src/autoteam/api.py`, `.env.example`, `docs/configuration.md`, and tests cover the config surface | Absorbed by adapted design | Current repo keeps its richer `create_new_account(... leave_workspace/out_outcome/acc/path_rotator/parallel ...)` signature, direct signup race, multi-provider routing, IPv6 proxy handling, and remove-before-create validation; target `ConfigPage.vue` was not copied verbatim. |
| `8f17448 fix: add CPA credential gate to auto-check` | auto-check should consider read-only CPA provider-auth availability when Team is full but local active children are short | `src/autoteam/api.py::_collect_cpa_credential_gate`, auto-fill branch, `tests/unit/test_api_status.py::test_auto_check_uses_read_only_cpa_gate_when_team_full_and_no_credentials`, `test_auto_check_cpa_gate_does_not_treat_management_failure_as_zero_credentials` | Absorbed by adapted design | Current repo keeps command `auto-fill` / `cmd_rotate(..., background_post_sync=True)` rather than target's larger auto-check restructuring. Gate is read-only and does not call CPA sync/upload/delete, and the same live provider-auth truth now also drives active CPA publish routing in `src/autoteam/cpa_sync.py`. |
| `276ed0b fix: harden quota blocker rotation` | quota blocker replacement, auto-check action semantics | `src/autoteam/manager.py` has `_replaceable_pool_blocker_reason`, `_wait_for_remote_capacity_after_removal`, `_validate_managed_account_operational`; tests in `tests/unit/test_manager_rotate.py` and `tests/unit/test_api_status.py` | Absorbed in `05bf6da` | Need no whole-file copy. |
| `f120570 fix rotate post sync and cliproxy health` | deferred rotate post-sync and read-only CLIProxy health | `src/autoteam/cliproxy_health.py`, `/api/status.cliproxy`, `tests/unit/test_cliproxy_health.py`, `tests/unit/test_manager_rotate.py` | Absorbed | Current repo keeps read-only health and CPA delete guard. |
| `6f4d106 fix invite blank page recovery` | recover post-auth blank registration pages | `src/autoteam/invite.py` has `_recover_blank_invite_page`; tests in `tests/unit/test_invite_blank_page_recovery.py` | Absorbed | Current tests are split from target `test_signup_flow_profiles.py`, but cover the same blank-page recovery behavior. |
| `15e50d6 Improve registration credential sync and diagnostics` | sync newly ready credential once, improve CPA/Sub2API diagnostics | `src/autoteam/manager.py` has `_sync_ready_credential_to_targets`; `src/autoteam/sync_targets.py` has `sync_account_to_configured_targets`; tests in `test_sync_targets.py`, `test_cpa_sync.py`, `test_sub2api_sync.py` | Mostly absorbed | Further audit should compare target invite diagnostics line-by-line before declaring final completion. |
| `d952ce6 fix rotation cooldown safety boundary` | cooldown must not block real shortage | `tests/unit/test_api_status.py` includes shortage/cooldown and blocker replacement cases | Absorbed | Strengthened in `05bf6da`. |
| `2fb3031 fix rotation validation and ipv6 pool status` | `/api/status` runtime/IPv6/rotation validation fields | current `api.py`, `ipv6_pool.py`, `tests/unit/test_api_status.py`, `tests/unit/test_ipv6_pool.py` | Absorbed | Current repo also has richer IPv6 proxy isolation task artifacts. |
| `7d46b46 fix autoteam seat rotation runtime hardening` | runtime resources, Playwright cleanup, Docker bounds, rotation contract, safer Team/account cleanup helpers | current prior commits and specs: `runtime-docker-hardening.md`, `free-registration-hardening.md`; `src/autoteam/account_ops.py`, `/api/team/members`, `tests/unit/test_account_ops.py` | Absorbed core plus account-ops slice | Docker live deployment was intentionally not restarted in current repo. |
| `dafa32f fix: preswitch exhausted accounts in seat-2 rotation` | pre-switch exhausted child before replacement | current `cmd_rotate` intentionally uses safer remove-before-create for replaceable blockers; `tests/unit/test_manager_rotate.py::test_cmd_rotate_target2_refills_after_exhausted_removal_despite_transient_overcount` covers exhausted target-2 refill order | Absorbed by adapted design | Do not copy target preswitch because it can temporarily exceed the Team cap. Current regression asserts remove before replacement. |
| `89932b2 Fix seat-2 preswitch transient overcount cleanup` | cleanup overcount after preswitch | current `cmd_rotate` uses conservative `min(api_count, initial_api_count - removed_now)` after removal; regression test injects stale `api_count=3` and still refills from standby | Absorbed by adapted design | Target overcount risk is covered without creating a transient over-cap state. |
| `123e80f Add configurable auto-check seats and seat-2 preswitch` | target seat config, settings UI, preswitch | current `.env.example` and API clamp target seats to 1..3; `Settings.vue` has auto-check target controls | Mostly absorbed | Preswitch exactness remains the only uncertain part. |
| `a0c852f fix-add-phone-auth-retry` | add-phone auth retry backoff | current `AUTO_CHECK_RETRY_ADD_PHONE`, `AUTO_CHECK_ADD_PHONE_MAX_RETRIES`, auth repair tests | Absorbed | Current account-state work appears richer. |
| `e9d614f feat: add account disable and bulk toggle controls` | disable/bulk enable UI/API and sync exclusion | current `accounts.is_account_disabled`, `/api/accounts/*/disable`, bulk endpoints, `Dashboard.vue`, tests in `test_accounts.py`, `test_api_status.py`, `test_cpa_sync.py`, `test_sub2api_sync.py` | Absorbed | Current frontend style is different but functionality exists. |
| `6fa85a5 Update main codex remote deletion targets` | Main-Codex local-only login path, sync-target preflight, and remote deletion across CPA/Sub2API | `src/autoteam/codex_auth.py::MainCodexLoginFlow`, `src/autoteam/api.py` routes `/api/main-codex/login`, `/api/main-codex/delete-remote-files`, `/api/main-codex/delete-cpa`, tests in `tests/unit/test_api_main_codex_after_admin.py` and `tests/unit/test_round10_master_codex_session.py` | Absorbed by adapted design | Current repo uses `sync_targets.py` configured-target router and keeps admin-login local auth refresh without remote sync. |
| `66249a9 feat: add dashboard quota reset action` | Reset local quota recovery metadata and recover exhausted rows to checkable local states | `manager.cmd_reset_quota_recovery`, CLI `reset-quota`, API `POST /api/tasks/reset-quota`, `tests/unit/test_manager_reset_quota.py`, `tests/unit/test_api_status.py` | Absorbed | Current behavior is local-only: no Team/CPA/Sub2API mutation. |
| `563e8bc Randomize signup profile details` | randomized signup profile consistency | current `SignupProfile` and profile-propagation tests in `test_round12_s3_cherry_pick.py`, `test_free_registration_hardening.py` | Partially absorbed / needs assertion audit | Target's public dataclass shape differs; do not change current immutable profile contract without auditing all free-registration callers. |
| `5782586 fix: harden codex team workspace selection` | workspace selection, signup-flow helper, and session Codex auth hardening | current `oauth_workspace.py`, `SessionCodexAuthFlow`, `chatgpt_api._workspace_candidate_kind`, `ChatGPTTeamAPI._wait_for_post_workspace_ready`, `codex_auth` compatibility wrappers/lightweight OAuth helpers/session fallback, direct/invite split-code helpers, `tests/unit/test_workspace_oauth_parity.py` | Absorbed by adapted design | Target `test_chatgpt_workspace.py`, `test_codex_auth_session.py`, and all non-profile-shape assertions from target `test_signup_flow_profiles.py` now pass against current. Remaining target signup-flow failures are the rejected old positional `SignupProfile` constructor shape only. |

## Target-only Files And Migration Decisions

Target-only files from `git ls-files` comparison:

| Target-only artifact | Current equivalent | Decision |
| --- | --- | --- |
| `src/autoteam/cloudflare_temp_email.py` | `src/autoteam/cloudflare_temp_email.py` facade plus `src/autoteam/mail/cf_temp_email.py` and `MAIL_PROVIDER` / `MAIL_PROVIDER_CHAIN` | Absorbed as compatibility facade; source of truth remains provider package | Current implementation supports cf_temp_email under a provider package and adds maillab/addy/simplelogin fallback. The top-level module is a legacy import shim only, not a move back to target's simpler architecture. |
| `src/autoteam/mail_provider.py` | `src/autoteam/mail/__init__.py`, `mail/base.py`, `mail/fallback.py`, provider modules | Superseded. Target helper is simpler; current abstraction is stronger. |
| `src/autoteam/cloudflare_dns.py` | `src/autoteam/dns_diagnostics.py`, `/api/setup/dns/check`, `tests/unit/test_dns_diagnostics.py` | Read-only portion migrated. The mutating `upsert_record` / `ensure_admin_dns` path remains rejected unless the user explicitly asks for DNS automation. |
| `web/src/components/ConfigPage.vue` | current `SetupPage.vue`, `Settings.vue`, `MailProviderCard.vue` | UX grouping useful, exact component not migrated | Target's unified runtime/source configuration grouping is useful, especially category tabs and `.env` source editing. The exact file is dark, emoji-heavy, and depends on `/api/config/runtime` plus `/api/config/source`; migrate only after a separate current-style safety/design pass. |
| `web/src/components/ThemeToggle.vue`, `web/src/theme.js` | no direct current equivalent | Reject for now. Target implementation reintroduces dark gradient/emoji styling that conflicts with current UI direction. |
| `tests/unit/test_account_ops.py` | `tests/unit/test_account_ops.py` | Migrated. Current tests cover target assertions plus current `/api/team/members` normalized rendering. Target test file also passes against current code. |
| `web/pnpm-lock.yaml`, `web/public/favicon.svg`, `src/autoteam/web/dist/assets/*`, `src/autoteam/web/dist/favicon.svg` | current web build pipeline, `web/package-lock.json`, regenerated `src/autoteam/web/dist/*` | Superseded as build artifacts | These are target build outputs or lockfile assets, not feature-source truth. Current repo regenerates its own web build artifacts and keeps `web/package-lock.json`; do not copy target build outputs verbatim. |
| `test_signup_profile.py` | `test_round12_s3_cherry_pick.py`, `test_free_registration_hardening.py`, `src/autoteam/signup_profile.py` | Superseded by current shape | Target file fails against current immutable snapshot interface because current repo intentionally keeps `SignupProfile(full_name, birthday, age="...")` plus `birthday_text` / `age_text`; the underlying behavior (deterministic generation, immutability, positional birthday ordering, RNG injection) is already covered in current tests. |
| `test_chatgpt_workspace.py` | `tests/unit/test_workspace_oauth_parity.py`, `src/autoteam/chatgpt_api.py` | Migrated | Target file now passes against current repo. Current coverage keeps workspace noise filtering, fallback classification, post-selection readiness, and completed ChatGPT home shortcut behavior. |
| `test_codex_auth_session.py` | `tests/unit/test_workspace_oauth_parity.py`, `tests/unit/test_round11_oauth_workspace_consent.py`, `src/autoteam/oauth_workspace.py`, `src/autoteam/codex_auth.py` | Migrated core workspace/session assertions | Target file now passes against current repo. Current repo keeps shared implementation in `oauth_workspace.py` and exposes thin compatibility wrappers from `codex_auth.py`. |
| `test_signup_flow_profiles.py` | `test_free_registration_hardening.py`, `test_round12_s3_cherry_pick.py`, `test_workspace_oauth_parity.py`, `src/autoteam/codex_auth.py`, `src/autoteam/invite.py`, `src/autoteam/manager.py` | Absorbed except rejected old profile constructor shape | Current repo covers snapshot propagation, about-you retries, workspace/OAuth selection, split-code target waits, direct/invite code submit helpers, OAuth lightweight recovery, OTP rejection cache, session-bundle extraction, and `login_codex_via_browser(return_result=..., pre_signed_in_cookies=...)`. Full target file now reaches `24 passed, 11 failed`; every remaining failure is the old positional `SignupProfile("Name", year, month, day, age)` API, which current repo intentionally rejects in favor of the immutable mapping snapshot contract. |
| `test_manager_auth_repair.py` | `tests/unit/test_manager_auth_paths.py`, auth-repair related tests in `tests/unit/test_round12_s3_cherry_pick.py` and `tests/unit/test_api_status.py` | Safe auth-path/result-helper/cmd-check/release-policy subsets migrated; exact target status literal remains rejected | Current now resolves host, container, project-relative, and bare auth-file paths, protects Team seats when a real local auth exists, exposes `_login_codex_with_result()` with target-compatible retry/result behavior, lets `cmd_check(...force_auth_repair...)` ignore cooldown, preserves historical low-quota candidates on network errors, releases repeated email-verification and missing-auth `login_state_lost` blockers, retires released failed repairs, and preserves protected local credentials. The full target file still has incompatible expectations around the target-only `"auth_pending"` persisted literal, exact `update_account()` call shape without `_reason`, and add-phone retry-disabled no-release behavior. Those are rejected for current's state machine and capacity-first hard-cap policy. |
| `test_cloudflare_temp_email.py` | `src/autoteam/cloudflare_temp_email.py`, `src/autoteam/mail/base.py`, `src/autoteam/mail/cf_temp_email.py`, current `tests/unit/test_cloudmail.py` | Absorbed as compatibility facade + metadata-preferred extraction | Current repo now keeps the provider-package source of truth, but exposes a target-compatible top-level compatibility module, strips `/admin` from the base URL, and prefers `metadata.ai_extract` before subject/body parsing for OTP and invite extraction. |

## Current-only Strengths To Preserve

* `src/autoteam/mail/` package with provider fallback chain and richer provider options.
* Account-state lifecycle tests and reconciliation anomaly tests.
* Multi-master workspace pool and direct-parallel budget propagation.
* Frontend component system (`AtButton`, status/health components, composables) and cleaner UI direction.
* CPA delete guard and disabled-account exclusion.
* `1 owner + 2 managed children = 3 seats` hard cap.

## Recommended Next Slice

Slice P1: seat-2 preswitch transient-overcount coverage audit and regression tests. **Completed in this task.**

Reason:

* It is close to the just-landed rotation work and still marked partially absorbed.
* It can be verified entirely with unit tests.
* It avoids high-risk live operations and avoids touching frontend style.

Slice P2: Cloudflare DNS read-only diagnostics. **Completed in this task.**

Reason:

* It is the clearest target-only useful source helper.
* Current docs still instruct manual DNS setup.
* Only read-only `check_admin_dns` should be migrated first; mutating `ensure_admin_dns` should remain out of scope until the user explicitly wants DNS automation.

Slice P3: account cleanup and Team response shape hardening. **Completed in this task.**

Reason:

* Target `tests/unit/test_account_ops.py` exposed a useful safety surface that was not
  covered in current repo before this slice.
* The migration is backend-only and does not touch live remote services.
* Current repo keeps its stronger `src/autoteam/mail/` provider package and
  `sync_targets.py` router instead of copying target top-level `mail_provider.py`.

Implemented current evidence:

* `src/autoteam/account_ops.py` now parses Team member/invite wrapper variants,
  nested `user` / `account_user` fields, readable auth/HTML failures, invite delete
  fallback, local credential seat protection, configured CPA/Sub2API deletion, and
  generic `mail_account_id` / legacy `cloudmail_account_id` deletion.
* `src/autoteam/api.py` `/api/team/members` now renders normalized nested Team rows
  using the same helpers rather than assuming top-level fields.
* `.trellis/spec/backend/account-disable-cpa-sync.md` records the executable
  contract for deletion and Team state parsing.

Slice P4: CPA credential gate for auto-check. **Completed in this task.**

Reason:

* Target commit `8f17448` was newer than the previous matrix and exposed a real
  remaining runtime-decision gap.
* Current repo already has read-only CLIProxyAPI health, so the useful value is the
  gate decision, not new remote mutation behavior.
* It can be tested without touching live CPA/Sub2API/Team.

Implemented current evidence:

* `src/autoteam/api.py::_collect_cpa_credential_gate()` checks only configured CPA
  enablement plus read-only `get_cliproxy_health(cache_ttl=0.0, force_refresh=True)`.
* `src/autoteam/api.py::_auto_check_loop()` now lets zero available CPA provider
  credentials trigger the existing `auto-fill` path when Team is full but local
  active children are below target.
* Management failure returns `zero_available=false`; it is not treated as no
  credentials.
* `.trellis/spec/backend/runtime-docker-hardening.md` records the read-only gate
  contract.

Slice P5: reset-quota local recovery. **Completed in this task.**

Reason:

* Target commit `66249a9` exposed a useful operator recovery action after quota
  reset windows or stale exhausted metadata.
* The current migration is local-only and does not mutate Team, CPA, Sub2API, or
  browser sessions.

Implemented current evidence:

* `src/autoteam/accounts.py` defines `STATUS_AUTH_PENDING` as an alias for the
  persisted `auth_invalid` lifecycle state.
* `src/autoteam/manager.py::cmd_reset_quota_recovery()` clears local quota reset
  metadata for non-main accounts and restores exhausted rows to either `active`
  when an auth file exists or `auth_pending`/`auth_invalid` when it does not.
* `src/autoteam/api.py` exposes `POST /api/tasks/reset-quota`.
* `tests/unit/test_manager_reset_quota.py` covers local-only state transitions.

Slice P6: main-Codex local login and remote deletion target router. **Completed in this task.**

Reason:

* Target commit `6fa85a5` and target-only
  `tests/unit/test_api_main_codex_after_admin.py` exposed a useful split between
  local main-Codex login and explicit remote sync/delete actions.
* The migration is safe when adapted to current `sync_targets.py`: sync and delete
  remain explicit operator actions, while admin-login local refresh does not upload
  or delete CPA/Sub2API files.

Implemented current evidence:

* `src/autoteam/codex_auth.py::MainCodexLoginFlow` saves a main auth file without
  remote sync; `MainCodexSyncFlow` extends it and still syncs only on the sync path.
* `src/autoteam/api.py` now tracks `main_codex.action`, exposes
  `POST /api/main-codex/login`, requires enabled sync targets before
  `POST /api/main-codex/start`, and adds explicit remote deletion routes
  `/api/main-codex/delete-remote-files` plus legacy `/api/main-codex/delete-cpa`.
* `web/src/api.js` exposes client helpers for the new routes without adding a new
  UI surface yet.
* `.trellis/spec/backend/runtime-docker-hardening.md` records the local-login,
  sync-target preflight, and explicit-delete contracts.

Slice P7: manager auth-path resolution and protected Team credential recovery.

Reason:

* Target `test_manager_auth_repair.py` exposed a low-risk current gap: manager
  code did not consistently resolve auth paths persisted as container paths,
  project-relative paths, or bare filenames.
* The migration is local-file and reconciliation only. It does not mutate Team,
  CPA, Sub2API, or browser sessions.
* It strengthens the current account-state lifecycle without copying target's
  larger auth-repair command shape.

Implemented current evidence:

* `src/autoteam/manager.py::_resolve_auth_file_path()` handles host absolute
  paths, `/app/...` container paths, `data/auths/...`, `auths/...`, and bare
  names searched under current auth dirs.
* `src/autoteam/manager.py::_find_team_auth_file()` now searches the current
  auth search dirs instead of only one path convention.
* `sync_account_states()` now preserves Team seats for standby/auth-pending rows
  with real local auth files and restores recovered Team rows with
  `protect_team_seat=True` plus `workspace_account_id`.
* `tests/unit/test_manager_auth_paths.py` covers the adapted behavior.

Remaining target auth-repair audit:

* Full target `test_manager_auth_repair.py` still fails against current because
  several assertions describe target-only helper names or behavior policies, not
  simple path handling.
* Do not migrate those as a batch. Each remaining category needs a separate
  behavior decision against current account-state and hard Team-cap contracts.

Slice P8: OAuth/auth-repair transient error labels and retry-delay helper. **Completed in this task.**

Reason:

* Target `test_manager_auth_repair.py::test_auth_repair_error_label_handles_oauth_timeout`
  exposed a small diagnostic gap with no remote mutation risk.
* Current repo already has auth-repair retry metadata; richer labels make cooldown
  and pause messages more actionable without changing the state machine.

Implemented current evidence:

* `src/autoteam/manager.py::_auth_repair_error_label()` now labels
  `oauth_timeout`, `unsupported_region`, `account_selection`,
  `missing_auth_file`, and `auth_error_discard`.
* `src/autoteam/manager.py::_oauth_retry_delay_seconds()` records the short
  same-round delays target uses for transient organization/region pages.
* `tests/unit/test_round12_s3_cherry_pick.py` covers the adapted label and delay
  contract.

Slice P9: workspace selection and session Codex helper parity. **Completed in this task.**

Reason:

* Target `test_chatgpt_workspace.py` and `test_codex_auth_session.py` exposed a
  behavior gap: current had the stronger shared `oauth_workspace.py` helpers but
  did not expose target-compatible wrappers from `codex_auth.py`, and
  `ChatGPTTeamAPI.select_workspace_option()` did not wait for post-selection
  ChatGPT readiness before reclassifying the login step.
* The migration is pure helper/UI-flow hardening and is unit-testable without
  live browser or remote services.

Implemented current evidence:

* `src/autoteam/chatgpt_api.py` now classifies workspace labels through
  `_workspace_candidate_kind()`, filters page heading/legal-link noise, marks
  personal/free/new-org options as fallback, waits for post-workspace readiness,
  and returns completed when the page has already landed on ChatGPT home.
* `src/autoteam/codex_auth.py` exposes compatibility wrappers around the shared
  `oauth_workspace.py` detector/candidate/selector functions.
* `tests/unit/test_workspace_oauth_parity.py` keeps current regression coverage.
* Target `test_chatgpt_workspace.py` and `test_codex_auth_session.py` pass against
  current repo after this migration.

Slice P10: target ConfigPage UX audit.

Reason:

* Target's grouping of runtime config into mail, sync, security, admin,
  auto-check, source, and proxy categories is useful.
* Current repo already has a stronger `SetupPage` / `Settings` /
  `MailProviderCard` split and a cleaner restrained UI direction.
* The exact target component should not be copied: it uses dark glass cards,
  emoji category icons, gradient accents, and depends on target-only
  `/api/config/runtime` plus `/api/config/source` endpoints.
* Future migration, if desired, should be a current-style runtime configuration
  pass with explicit source-editor safety review, not a whole-file copy.
* Source check on 2026-05-19 confirmed target frontend clients call
  `/api/config/runtime` and `/api/config/source`, and target backend implements
  those endpoints as runtime config read/write plus raw `.env` source read/write.
  Current repo intentionally exposes narrower setup/runtime endpoints such as
  `/api/config/register-domain`, `/api/config/preferred-seat-type`,
  `/api/config/sync-probe`, and `/api/config/auto-check`, and `web/src/api.js`
  has no runtime/source config client. Exact target UI/API migration would
  therefore be a new source-editor safety feature, not a parity patch.

Slice P11: Codex OAuth lightweight challenge/recovery helpers. **Completed in this task.**

Reason:

* Target `test_signup_flow_profiles.py` exposed a safe helper subset that improves
  Codex OAuth robustness without changing live browser-login orchestration or
  session-bundle extraction policy.
* The migration is DOM/trace/cache helper hardening only: organization dropdown
  selection, choose-account selection, OAuth trace filtering, retryable error
  classification, timeout/no-valid-organization retry-page recovery, login
  challenge completion, OTP rejection cache hashing, and OTP submit acceptance of
  OAuth progress URLs.
* Higher-risk target helpers remain out of this slice: split verification-code
  target waits, `_fetch_team_session_bundle_from_context`,
  `login_codex_via_browser(return_result=..., pre_signed_in_cookies=...)`, and
  the rejected old `SignupProfile` constructor shape.

Implemented current evidence:

* `src/autoteam/codex_auth.py` now contains the lightweight OAuth helpers and
  bounded trace/cache constants.
* `tests/unit/test_workspace_oauth_parity.py` covers the current-adapted helper
  behavior with Playwright-like fake locators whose empty `.first` is not visible.
* The selected target subset from `test_signup_flow_profiles.py` passes against
  current repo (`13 passed`).

Slice P12: direct/invite split-code verification helpers. **Completed in this task.**

Reason:

* Target `test_signup_flow_profiles.py` exposed a real registration robustness
  gap: OpenAI email verification can render delayed six-box inputs, and current
  invite registration previously logged only a generic missing-input warning.
* The migration is DOM-bound helper hardening. It does not alter seat caps,
  remote sync, CPA/Sub2API behavior, or browser-login policy.

Implemented current evidence:

* `src/autoteam/manager.py` now exposes `_DIRECT_MULTI_CODE_SELECTOR`,
  `_wait_for_direct_code_target()`, and `_submit_direct_verification_code()`.
  The direct flow waits for delayed split/single code inputs before submitting.
* `src/autoteam/invite.py` now exposes `INVITE_CODE_SELECTORS`,
  `INVITE_MULTI_CODE_SELECTOR`, `_wait_for_invite_code_target()`,
  `_submit_invite_verification_code()`, and structured input diagnostics for
  timeout/advanced-step cases.
* `tests/unit/test_workspace_oauth_parity.py` covers delayed split-code helper
  behavior in the current repo.
* Selected target split-code assertions from `test_signup_flow_profiles.py` pass
  against current repo (`5 passed`).

Slice P13: Codex session fallback from pre-signed ChatGPT cookies. **Completed in this task.**

Reason:

* Target `test_signup_flow_profiles.py` showed a useful safe path for newly
  registered accounts: if a valid ChatGPT Team session already exists in the
  browser context, fetch `/api/auth/session` and use that Team access token
  before entering the full OAuth challenge path.
* The migration is opt-in and backwards-compatible: existing callers still get
  the old bundle/`None` return shape unless they explicitly pass
  `return_result=True`; session fallback is attempted only when
  `pre_signed_in_cookies` is provided.

Implemented current evidence:

* `src/autoteam/codex_auth.py::_fetch_team_session_bundle_from_context()` injects
  Team account cookies, opens `https://chatgpt.com/admin/workspace/<account_id>`,
  extracts `/api/auth/session.accessToken`, validates Team JWT claims, and can
  accept a quota-verified session token whose JWT workspace claim is stale.
* `login_codex_via_browser(..., pre_signed_in_cookies=..., return_result=True)`
  returns the target-compatible `{ok, bundle, error_type, error_detail,
  retryable}` shape on the explicit session-fallback path while preserving the
  default return contract.
* `tests/unit/test_workspace_oauth_parity.py` covers pre-signed session fallback
  in the current repo.
* Selected target session fallback assertions from `test_signup_flow_profiles.py`
  pass against current repo (`4 passed`).

Slice P14: Codex auth-repair result wrapper helper. **Completed in this task.**

Reason:

* Target `test_manager_auth_repair.py` exposed one safe auth-repair helper that can
  be migrated without changing `cmd_check`, account-state lifecycle, or Team-seat
  release decisions.
* `_login_codex_with_result()` is a local normalization wrapper around the already
  migrated `login_codex_via_browser(..., return_result=True)` contract. It can be
  tested with pure monkeypatched unit tests and does not touch live browser,
  Team, CPA, Sub2API, or Cloudflare state.
* Higher-risk target auth-repair behavior remains outside this slice:
  `cmd_check(...force_auth_repair...)`, historical low-quota network-error
  replacement policy, retry-disabled add-phone no-release behavior,
  `auth_pending` literal expectations, repeated email-verification release, and
  local-credential `login_state_lost` pause/release policy.

Implemented current evidence:

* `src/autoteam/manager.py::_login_codex_with_result()` now normalizes explicit
  `{ok, bundle, error_type, error_detail, retryable}` results, legacy
  bundle/`None` results, thrown exceptions, and non-Team bundles into one result
  shape with `attempts`.
* `AUTH_REPAIR_SINGLE_ATTEMPT_FAILURE_TYPES` prevents same-round retries for
  failures that should be handled by the surrounding auth-repair state machine,
  while retryable `auth_code_missing` can retry within the same call.
* `tests/unit/test_round12_s3_cherry_pick.py::TestLoginCodexWithResult` covers
  retryable same-round success, single-attempt terminal categories, and non-Team
  bundle rejection.
* The selected target `_login_codex_with_result` assertions from
  `test_manager_auth_repair.py` pass against current repo (`5 passed`).
* After P14, full target `test_manager_auth_repair.py` reached
  `14 passed, 13 failed`; the remaining failures were the higher-risk policy
  categories listed above and were intentionally split into later slices.

Slice P15: `cmd_check` auth-repair entry and historical-low-quota handling. **Completed in this task.**

Reason:

* Target `test_manager_auth_repair.py` exposed useful `cmd_check` behavior that
  is safe when adapted to current state aliases and mail-provider routing:
  force-auth-repair should ignore cooldown, auth-pending rows should be scanned,
  and low historical quota should be usable when the live quota endpoint returns
  a temporary network error.
* The migration is local decision logic only. It does not change Team-seat release
  policy, CPA/Sub2API sync, live Docker state, or the hard `1 owner + 2 managed
  children` cap.

Implemented current evidence:

* `src/autoteam/manager.py::cmd_check()` now accepts
  `force_auth_repair=False`, `preserve_low_active=False`, and
  `preserved_low_accounts=None` while preserving the legacy positional
  `include_standby` parameter.
* `_is_auth_repair_pending_status()` accepts both current persisted
  `STATUS_AUTH_INVALID` and the target legacy `"auth_pending"` literal as input.
  Output still uses current `STATUS_AUTH_INVALID`.
* `_historical_low_quota_info()` derives a bounded low-quota decision from saved
  `last_quota` only when the reset window has not elapsed.
* `preserve_low_active=True` records low active accounts in
  `preserved_low_accounts` instead of immediately marking them exhausted; default
  mode can still mark historical-low accounts exhausted.
* `force_auth_repair=True` bypasses retry cooldown/paused skips, uses
  `_get_account_mail_client()` for per-account mail-provider routing, and calls
  `_login_codex_with_result()` without passing empty proxy kwargs to old
  monkeypatch/test doubles.
* Selected target `cmd_check` auth-repair assertions now pass against current repo
  (`6 passed`).

Slice P16: `_record_auth_repair_failure` safe release-policy subset. **Completed in this task.**

Reason:

* Target auth-repair work contains one useful seat-rotation safety improvement:
  when a repair failure has actually released a Team seat, the local row should
  not silently re-enter standby reuse.
* Current repo already has protected local credential rules. Target's
  `login_state_lost` guard was adapted to preserve those local credentials rather
  than releasing them.
* The migration deliberately does not adopt target's persisted `"auth_pending"`
  literal or exact `update_account()` call shape because current account-state
  transition logging relies on `STATUS_AUTH_INVALID` plus `_reason`.

Implemented current evidence:

* `src/autoteam/manager.py` now defines release-after-retry and Team-blocker
  classifications for auth repair.
* Repeated `email_verification` can pause and release after the retry budget is
  exhausted.
* Missing-auth `login_state_lost` can release the Team blocker; protected local
  credential seats cancel release and remain in current auth-pending state.
* Released repair failures are marked `disabled=True`, `reuse_disabled=True`, and
  `retired_reason="auth_repair_failed:<type>"`, then account IPv6 proxy state is
  released best-effort.
* Current `TestRecordAuthRepairFailure`, `TestLoginCodexWithResult`,
  `TestCmdCheckAuthRepairEntry`, `test_api_status`, and `test_round12_wireup`
  suites pass.
* Full target `test_manager_auth_repair.py` now reaches `20 passed, 7 failed`.
  Remaining failures are the intentionally rejected `"auth_pending"` persisted
  literal, exact update-call shape, and add-phone retry-disabled no-release
  policy. Current keeps capacity-first release for unrepairable managed children.

Slice P17: Cloudflare temp-email compatibility facade and metadata-preferred extraction. **Completed in this task.**

Reason:

* Target `test_cloudflare_temp_email.py` exposed a small compatibility gap:
  the current project already had a stronger `src/autoteam/mail/` provider package,
  but not the legacy top-level import path or the target's `/admin` base URL
  normalization behavior.
* The useful part of the target behavior is not the top-level architecture; it is
  the provider parsing improvement. Metadata-derived `ai_extract` results should
  win over subject/body fallback parsing because they are more direct and less
  brittle.

Implemented current evidence:

* `src/autoteam/cloudflare_temp_email.py` now exposes a target-compatible
  `CloudflareTempEmailClient` wrapper while keeping `src/autoteam/mail/cf_temp_email.py`
  as the source of truth.
* `normalize_cloudflare_temp_email_base_url()` strips `/admin` and trailing
  slashes from target-style inputs.
* `src/autoteam/mail/base.py` now prefers `metadata.ai_extract.result` for both
  verification code and invite-link extraction before falling back to text/body
  parsing.
* Current `tests/unit/test_cloudmail.py` covers the compatibility facade and
  metadata-preferred extraction behavior.
* Target `tests/unit/test_cloudflare_temp_email.py` now passes against current
  repo (`6 passed`), and the combined current cloudmail/mail sniff suite still
  passes.

Slice P18: active CPA credential publish preflight. **Completed in this task.**

Reason:

* Target `8f17448` made CPA provider-auth availability a real-time decision input
  for auto-check. The same principle must also hold when current repo publishes
  active auth files to CPA: local `STATUS_ACTIVE` is not enough evidence that a
  credential should be uploaded or that its remote copy should be removed.
* The current migration is adapted to existing CPA delete guards. A quota network
  failure is treated as "unknown, keep remote", not "zero usable" and not
  "delete remote".

Implemented current evidence:

* `src/autoteam/cpa_sync.py::_active_auth_publish_decision()` reads each active
  auth file and calls `check_codex_quota(access_token, timeout=8)` immediately
  before publish.
* `sync_to_cpa()` uploads only `ok` active credentials, preserves remote files on
  `network_error` / quota exceptions, and routes exhausted or terminal failures to
  the existing remote-delete path.
* `sync_to_cpa()` now returns `active_publish.skipped_unknown`,
  `active_publish.kept_remote`, and `active_publish.delete_remote` counters so
  operators can see why active files were not uploaded.
* `tests/unit/test_cpa_sync.py` covers exhausted active credentials deleting the
  matching remote file, network-error active credentials preserving the remote
  copy, disabled-account preservation, and proxy refresh before upload.

## Commands/Evidence Collected

* `git -C D:/Desktop/autoteam-1/AutoTeam log --oneline -12`
* `git log --oneline -12`
* `git -C D:/Desktop/autoteam-1/AutoTeam show --stat --oneline ...`
* `diff -qr --exclude=.git --exclude=__pycache__ --exclude=node_modules --exclude=dist ... src/autoteam`
* `diff -qr --exclude=.git --exclude=__pycache__ --exclude=node_modules --exclude=dist ... web/src`
* `rg` searches for blank-page recovery, blocker rotation, disable/bulk controls, sync diagnostics, and Cloudflare DNS/Temp Email.
* `python -m ruff check src/autoteam/manager.py tests/unit/test_manager_rotate.py tests/unit/test_api_status.py`
* `python -m pytest -q tests/unit/test_manager_rotate.py tests/unit/test_api_status.py` -> `21 passed, 1 warning`
* `python -m ruff check src/autoteam/dns_diagnostics.py src/autoteam/api.py tests/unit/test_dns_diagnostics.py tests/unit/test_manager_rotate.py tests/unit/test_api_status.py`
* `python -m py_compile src/autoteam/dns_diagnostics.py src/autoteam/api.py src/autoteam/manager.py`
* `python -m pytest -q tests/unit/test_dns_diagnostics.py tests/unit/test_manager_rotate.py tests/unit/test_api_status.py` -> `27 passed, 1 warning`
* `python -m pytest -q tests/unit/test_dns_diagnostics.py tests/unit/test_mail_provider_probe.py tests/unit/test_manager_rotate.py tests/unit/test_api_status.py` -> `38 passed, 1 warning`
* `python -m ruff check src/autoteam/account_ops.py src/autoteam/api.py tests/unit/test_account_ops.py` -> pass
* `python -m pytest -q tests/unit/test_account_ops.py` -> `8 passed, 1 warning`
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_account_ops.py` -> `7 passed`
* `python -m pytest -q tests/unit/test_round6_patches.py tests/unit/test_spec2_lifecycle.py tests/unit/test_cpa_sync.py tests/unit/test_sub2api_sync.py` -> `66 passed, 1 warning`
* `python -m pytest -q tests/unit/test_account_ops.py tests/unit/test_api_playwright_cleanup.py tests/unit/test_api_status.py tests/unit/test_manager_rotate.py` -> `43 passed, 1 warning`
* `python -m ruff check src/autoteam/account_ops.py src/autoteam/api.py tests/unit/test_account_ops.py tests/unit/test_api_playwright_cleanup.py tests/unit/test_api_status.py tests/unit/test_manager_rotate.py tests/unit/test_round6_patches.py tests/unit/test_spec2_lifecycle.py tests/unit/test_cpa_sync.py tests/unit/test_sub2api_sync.py` -> pass
* `python -m py_compile src/autoteam/account_ops.py src/autoteam/api.py` -> pass
* `python -m ruff check src/autoteam/api.py tests/unit/test_api_status.py` -> pass
* `python -m pytest -q tests/unit/test_api_status.py::test_auto_check_cooldown_does_not_delay_real_team_shortage tests/unit/test_api_status.py::test_auto_check_cooldown_keeps_full_team_from_refilling tests/unit/test_api_status.py::test_auto_check_cooldown_allows_full_team_blocker_replacement tests/unit/test_api_status.py::test_auto_check_uses_read_only_cpa_gate_when_team_full_and_no_credentials tests/unit/test_api_status.py::test_auto_check_cpa_gate_does_not_treat_management_failure_as_zero_credentials` -> `5 passed, 1 warning`
* `python -m pytest -q tests/unit/test_api_status.py` -> `18 passed, 1 warning`
* `python -m ruff check src/autoteam/accounts.py src/autoteam/manager.py src/autoteam/api.py tests/unit/test_manager_reset_quota.py tests/unit/test_api_status.py` -> pass
* `python -m pytest -q tests/unit/test_manager_reset_quota.py tests/unit/test_api_status.py` -> `19 passed, 1 warning`
* `python -m ruff check src/autoteam/api.py src/autoteam/codex_auth.py tests/unit/test_api_main_codex_after_admin.py tests/unit/test_round10_master_codex_session.py` -> pass
* `python -m pytest -q tests/unit/test_api_main_codex_after_admin.py tests/unit/test_round10_master_codex_session.py` -> `14 passed, 1 warning`
* `python -m ruff check src/autoteam/api.py src/autoteam/codex_auth.py src/autoteam/accounts.py src/autoteam/manager.py tests/unit/test_api_main_codex_after_admin.py tests/unit/test_round10_master_codex_session.py tests/unit/test_manager_reset_quota.py tests/unit/test_api_status.py` -> pass
* `python -m pytest -q tests/unit/test_api_main_codex_after_admin.py tests/unit/test_round10_master_codex_session.py tests/unit/test_manager_reset_quota.py tests/unit/test_api_status.py tests/unit/test_sync_targets.py` -> `38 passed, 1 warning`
* `npm run build` from `web/` -> Vite build succeeded; refreshed `src/autoteam/web/dist`.
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_api_main_codex_after_admin.py` -> `5 passed, 1 failed, 1 warning`. The failure is the target's exact `_finish_admin_login` expectation: current repo deliberately refreshes the local main auth file after admin login and records `main_auth` / `main_auth_error`; adapted current test asserts no remote sync instead.
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_profile.py` -> `2 passed, 2 failed`. The failures are the target's older public shape (`age` as `int` and positional `SignupProfile(name, year, month, day, age)`), while current repo intentionally uses an immutable birthday mapping plus `age_text` for browser form consumers.
* `python -m ruff check src/autoteam/manager.py tests/unit/test_manager_auth_paths.py` -> pass.
* `python -m pytest -q tests/unit/test_manager_auth_paths.py` -> `4 passed`.
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_has_auth_file_resolves_container_data_auth_path D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_find_team_auth_file_searches_auth_dirs D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_sync_account_states_recovers_team_auth_file_as_protected D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_sync_account_states_promotes_auth_pending_remote_member_with_auth` -> `4 passed`.
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py` -> `8 passed, 19 failed, 1 warning`. Remaining failures are categorized above and should not be copied wholesale into current repo without separate behavior review.
* `python -m ruff check src/autoteam/manager.py tests/unit/test_round12_s3_cherry_pick.py` -> pass.
* `python -m pytest -q tests/unit/test_round12_s3_cherry_pick.py D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_auth_repair_error_label_handles_oauth_timeout` -> `49 passed, 1 warning`.
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_chatgpt_workspace.py D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_codex_auth_session.py` before migration -> `3 passed, 9 failed`; failures were missing workspace helpers/wrappers.
* `python -m ruff check src/autoteam/chatgpt_api.py src/autoteam/codex_auth.py tests/unit/test_workspace_oauth_parity.py` -> pass.
* `python -m pytest -q tests/unit/test_workspace_oauth_parity.py D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_chatgpt_workspace.py D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_codex_auth_session.py tests/unit/test_round11_oauth_workspace_consent.py tests/unit/test_oauth_workspace_select.py` -> `45 passed`.
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py` -> `3 passed, 32 failed`. Remaining failures are split between rejected old `SignupProfile` constructor shape and separate OAuth challenge/session-bundle helper gaps.
* `python -m ruff check src/autoteam/codex_auth.py tests/unit/test_workspace_oauth_parity.py` -> pass.
* `python -m pytest -q tests/unit/test_workspace_oauth_parity.py` -> `6 passed`.
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_select_existing_api_organization_prefers_non_new_option D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_select_choose_account_prefers_matching_email D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_oauth_trace_filters_and_trims_relevant_urls D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_oauth_trace_detects_login_challenge_redirect D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_oauth_login_challenge_page_detects_log_in_url D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_complete_oauth_login_challenge_password_path D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_classify_oauth_failure_handles_no_valid_organizations D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_classify_oauth_failure_handles_timeout D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_recover_oauth_timeout_page_clicks_try_again D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_recover_oauth_no_valid_organizations_page_clicks_try_again D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_wait_for_otp_submit_result_accepts_oauth_progress_url D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_otp_rejection_cache_hashes_code_and_loads_recent D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_classify_oauth_failure_handles_unsupported_region` -> `13 passed`.
* `python -m pytest -q tests/unit/test_workspace_oauth_parity.py tests/unit/test_round11_oauth_workspace_consent.py tests/unit/test_oauth_workspace_select.py tests/unit/test_round12_s3_cherry_pick.py D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_chatgpt_workspace.py D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_codex_auth_session.py` -> `95 passed, 1 warning`.
* `python -m ruff check src/autoteam/manager.py src/autoteam/invite.py` -> pass.
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_wait_for_direct_code_target_handles_delayed_split_inputs D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_wait_for_invite_code_target_handles_delayed_split_inputs D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_wait_for_invite_code_target_reports_advanced_step D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_register_with_invite_logs_code_input_diagnostics D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_submit_direct_verification_code_supports_split_inputs` -> `5 passed`.
* `python -m pytest -q tests/unit/test_round12_s3_cherry_pick.py tests/unit/test_free_registration_hardening.py tests/unit/test_api_playwright_cleanup.py tests/unit/test_manager_fill.py` -> `74 passed, 1 warning`.
* `python -m ruff check src/autoteam/codex_auth.py` -> pass.
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_fetch_team_session_bundle_from_context_returns_team_token D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_fetch_team_session_bundle_rejects_non_team_token D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_fetch_team_session_bundle_accepts_quota_verified_session_token D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py::test_login_codex_via_browser_uses_session_fallback_before_oauth` -> `4 passed`.
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_signup_flow_profiles.py` -> `24 passed, 11 failed`. Remaining failures are all target's older positional `SignupProfile("Name", year, month, day, age)` API. Current repo intentionally keeps immutable `SignupProfile(full_name, birthday, age=...)` and already covers equivalent behavior in current tests.
* `python -m ruff check src/autoteam/codex_auth.py src/autoteam/manager.py src/autoteam/invite.py tests/unit/test_workspace_oauth_parity.py` -> pass.
* `python -m pytest -q tests/unit/test_workspace_oauth_parity.py` -> `8 passed`.
* `python -m pytest -q tests/unit/test_workspace_oauth_parity.py tests/unit/test_round11_oauth_workspace_consent.py tests/unit/test_oauth_workspace_select.py tests/unit/test_round12_s3_cherry_pick.py tests/unit/test_free_registration_hardening.py tests/unit/test_api_playwright_cleanup.py tests/unit/test_manager_fill.py tests/unit/test_round11_session_token_injection.py` -> `126 passed, 1 warning`.
* `python -m pytest -q tests/unit/test_round12_s3_cherry_pick.py::TestLoginCodexWithResult` -> `5 passed`.
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_login_codex_with_result_retries_retryable_failures_within_same_round D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_login_codex_with_result_stops_immediately_on_hard_failure D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_login_codex_with_result_single_attempts_email_verification D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_login_codex_with_result_single_attempts_login_state_lost D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_login_codex_with_result_rejects_non_team_bundle` -> `5 passed`.
* `python -m ruff check src/autoteam/manager.py tests/unit/test_round12_s3_cherry_pick.py` -> pass.
* `python -m pytest -q tests/unit/test_round12_s3_cherry_pick.py tests/unit/test_workspace_oauth_parity.py tests/unit/test_api_status.py` -> `79 passed, 1 warning`.
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py` -> `14 passed, 13 failed, 1 warning`. Remaining failures are `cmd_check` signature/force-auth-repair/historical-low-quota behavior and `_record_auth_repair_failure` release/status policy differences, not the result-wrapper helper.
* `python -m py_compile tests/unit/test_round12_s3_cherry_pick.py` -> pass.
* `python -m pytest -q tests/unit/test_round12_s3_cherry_pick.py::TestCmdCheckAuthRepairEntry` -> `2 passed, 1 warning`.
* `python -m ruff check src/autoteam/manager.py tests/unit/test_round12_s3_cherry_pick.py` -> pass.
* `python -m pytest -q tests/unit/test_round12_s3_cherry_pick.py::TestLoginCodexWithResult tests/unit/test_round12_s3_cherry_pick.py::TestCmdCheckAuthRepairEntry tests/unit/test_api_status.py` -> `25 passed, 1 warning`.
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_cmd_check_preserves_active_credential_on_network_error D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_cmd_check_uses_historical_low_quota_on_network_error_for_remove_first D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_cmd_check_marks_historical_low_quota_exhausted_on_network_error D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_cmd_check_skips_cooled_down_auth_pending_account D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_cmd_check_force_auth_repair_ignores_cooldown D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_cmd_check_preserves_low_active_for_seat2_remove_first` -> `6 passed, 1 warning`.
* `python -m py_compile src/autoteam/manager.py tests/unit/test_round12_s3_cherry_pick.py` -> pass.
* `python -m ruff check src/autoteam/manager.py tests/unit/test_round12_s3_cherry_pick.py` -> pass.
* `python -m pytest -q tests/unit/test_round12_s3_cherry_pick.py::TestRecordAuthRepairFailure` -> `8 passed, 1 warning`.
* `python -m pytest -q tests/unit/test_round12_s3_cherry_pick.py::TestLoginCodexWithResult tests/unit/test_round12_s3_cherry_pick.py::TestCmdCheckAuthRepairEntry tests/unit/test_round12_s3_cherry_pick.py::TestRecordAuthRepairFailure tests/unit/test_api_status.py` -> `33 passed, 1 warning`.
* `python -m pytest -q tests/unit/test_round12_wireup.py` -> `18 passed, 1 warning`.
* `python -m ruff check src/autoteam/cloudflare_temp_email.py src/autoteam/mail/base.py src/autoteam/mail/cf_temp_email.py tests/unit/test_cloudmail.py` -> pass.
* `python -m pytest -q tests/unit/test_cloudmail.py tests/unit/test_mail_cf_temp_email_sniff.py D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_cloudflare_temp_email.py` -> `27 passed in 0.16s`.
* `python -m pytest -q tests/unit/test_cloudmail.py tests/unit/test_mail_cf_temp_email_sniff.py tests/unit/test_round12_s3_cherry_pick.py::TestRecordAuthRepairFailure tests/unit/test_round12_s3_cherry_pick.py::TestLoginCodexWithResult tests/unit/test_round12_s3_cherry_pick.py::TestCmdCheckAuthRepairEntry` -> `36 passed, 1 warning`.
* `python -m pytest -q tests/unit/test_api_status.py tests/unit/test_round12_wireup.py tests/unit/test_manager_auth_paths.py tests/unit/test_manager_reset_quota.py` -> `41 passed, 1 warning`.
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_cloudflare_temp_email.py D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_cmd_check_preserves_active_credential_on_network_error D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_cmd_check_force_auth_repair_ignores_cooldown D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py::test_cmd_check_uses_historical_low_quota_on_network_error_for_remove_first` -> `9 passed, 1 warning`.
* `python -m pytest -q D:/Desktop/autoteam-1/AutoTeam/tests/unit/test_manager_auth_repair.py` -> `20 passed, 7 failed, 1 warning`. Remaining failures are target-only `"auth_pending"` literal assertions, exact `update_account()` call-shape differences caused by current `_reason` state-machine logging, and the rejected add-phone retry-disabled no-release policy.
* `python -m ruff check src/autoteam/codex_auth.py src/autoteam/cpa_sync.py src/autoteam/accounts.py src/autoteam/mail/__init__.py src/autoteam/manager.py tests/unit/test_cpa_sync.py tests/unit/test_free_registration_hardening.py tests/unit/test_round10_master_codex_session.py` -> pass.
* `python -m pytest -q tests/unit/test_cpa_sync.py tests/unit/test_free_registration_hardening.py tests/unit/test_round10_master_codex_session.py tests/unit/test_api_status.py tests/unit/test_api_main_codex_after_admin.py tests/unit/test_manager_reinvite.py tests/unit/test_round12_wireup.py tests/unit/test_round11_oauth_failure_backoff.py tests/unit/test_round11_oauth_failure_kick_ws.py tests/unit/test_round11_session_token_injection.py tests/unit/test_round11_fresh_relogin_fallback.py tests/unit/test_round11_oauth_workspace_consent.py tests/unit/test_round11_personal_oauth_retry.py` -> `132 passed, 1 warning`.
* `python -m ruff check src/autoteam/account_ops.py src/autoteam/api.py src/autoteam/chatgpt_api.py src/autoteam/invite.py src/autoteam/mail/base.py src/autoteam/mail/cf_temp_email.py src/autoteam/cloudflare_temp_email.py src/autoteam/dns_diagnostics.py tests/unit/test_account_ops.py tests/unit/test_api_status.py tests/unit/test_api_main_codex_after_admin.py tests/unit/test_cloudmail.py tests/unit/test_dns_diagnostics.py tests/unit/test_manager_auth_paths.py tests/unit/test_manager_reset_quota.py tests/unit/test_manager_rotate.py tests/unit/test_round12_s3_cherry_pick.py tests/unit/test_workspace_oauth_parity.py` -> pass.
* `python -m pytest -q tests/unit/test_account_ops.py tests/unit/test_api_status.py tests/unit/test_api_main_codex_after_admin.py tests/unit/test_cloudmail.py tests/unit/test_dns_diagnostics.py tests/unit/test_manager_auth_paths.py tests/unit/test_manager_reset_quota.py tests/unit/test_manager_rotate.py tests/unit/test_round12_s3_cherry_pick.py tests/unit/test_workspace_oauth_parity.py tests/unit/test_cpa_sync.py tests/unit/test_free_registration_hardening.py tests/unit/test_round10_master_codex_session.py tests/unit/test_round12_wireup.py` -> `173 passed, 1 warning`.

## Completion Audit Checklist

| Objective item | Evidence inspected | Result |
| --- | --- | --- |
| Map every recent target commit to current code/tests/spec or a decision | `Target Recent Commit Matrix` covers the latest target commits from `8f17448` through `5782586` and current commits from `efad4b5` backward | Complete |
| Classify target-only source/UI/test files | `Target-only Files And Migration Decisions` covers source helpers, UI components, target-only test files, lockfile/favicon/build artifacts | Complete |
| Absorb safe seat-rotation and account-state improvements | P1, P3, P4, P5, P7, P15, P16, P18 plus current tests and selected target tests | Complete |
| Preserve current stronger architecture | Current-only strengths section keeps mail provider package/fallback, account-state machine, multi-master pool, CPA delete guard, cleaner UI, and hard 3-seat cap | Complete |
| Avoid whole-file target copies | All slices are adapted helpers/tests/spec updates; target `ConfigPage.vue`, `ThemeToggle.vue`, old `SignupProfile` shape, and raw build artifacts are rejected | Complete |
| Avoid unsafe live mutations | No `/api/sync`, Docker restart, CPA/Sub2API/Cloudflare/OpenAI Team mutation, or remote deletion smoke test was used in this audit | Complete |
| Verify implementation with real commands | Commands/Evidence section records `ruff`, current pytest suites, and selected target pytest runs | Complete |
| Identify unresolved or rejected target assertions | Remaining target auth-repair failures are explicitly rejected as incompatible status literal/update-call/capacity-policy expectations | Complete |

## Completion Finding

The global objective for this audit pass is complete: every inspected target
recent commit and target-only artifact is now either absorbed in current shape or
explicitly rejected as not suitable for this project. The broad seat-rotation core,
preswitch/transient-overcount risk, target-only DNS helper value, account cleanup
/ Team response-shape hardening, CPA credential gate logic, active CPA publish
preflight, reset-quota recovery, main-Codex local-login / remote-deletion behavior,
auth-path credential recovery subset, OAuth diagnostic labels, workspace/session
helper parity, `cmd_check` auth-repair entry behavior, historical-low-quota
recovery, the safe `_record_auth_repair_failure` release-policy subset, and
Cloudflare temp-email compatibility/metadata extraction now have adapted
current-repo implementations and tests. Target `ConfigPage.vue` is classified as
"do not exact-copy; replan as a separate current-style config safety feature if
desired." Target
`test_signup_flow_profiles.py` is fully dispositioned: all
non-profile-shape behavior is absorbed, and the old positional `SignupProfile`
constructor API is intentionally rejected. Remaining target auth-repair failures
are not incomplete work: target's `"auth_pending"` persisted literal is rejected,
exact `update_account()` call-shape assertions conflict with current
state-machine logging, and add-phone retry-disabled no-release behavior is
rejected because it can leave an unrepairable child occupying scarce Team
capacity under the current hard cap.
