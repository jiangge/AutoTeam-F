# Free Registration Hardening

## Scenario: Fill-Personal Safety Boundary

### 1. Scope / Trigger

- Trigger: any change to `POST /api/tasks/fill`, `cmd_fill(..., leave_workspace=True)`, `_cmd_fill_personal()`, `create_account_direct(..., leave_workspace=True)`, `_run_post_register_oauth(..., leave_workspace=True)`, or `SignupProfile`.
- Goal: make the free-account registration flow safer and more diagnosable without changing the successful-path semantics.
- Safety boundary: do not add bypasses for captcha, human verification, platform restrictions, rate limits, or anti-abuse systems. Hardening means consistency, early rejection, cleanup, and auditability.

### 2. Signatures

- `TaskParams.leave_workspace: bool = False`
- `TaskParams.target: int = 3`
- `post_fill(params: TaskParams = TaskParams())`
- `cmd_fill(target=3, leave_workspace=False, *, post_sync=True, print_status=True, direct_parallel=None)`
- `_cmd_fill_personal(count)`
- `create_new_account(chatgpt_api, mail_client=None, *, leave_workspace=False, out_outcome=None, acc=None, path_rotator=None, parallel=None)`
- `create_account_direct(mail_client=None, *, leave_workspace=False, out_outcome=None, acc=None, path_rotator=None, parallel=None)`
- `_run_post_register_oauth(email, password, mail_client, leave_workspace=False, out_outcome=None, chatgpt_session_token=None, signup_profile=None)`
- `generate_signup_profile(*, today: date | None = None, rng: random.Random | random.SystemRandom | None = None) -> SignupProfile`

### 3. Contracts

- API command mapping must remain:
  - `leave_workspace=True` -> `"fill-personal"`
  - `leave_workspace=False` -> `"fill"`
- The free path must remain:
  - register into Team
  - remove from Team with master authority
  - run Personal OAuth
  - accept only `plan_type == "free"`
  - persist `STATUS_PERSONAL`
- API-level fill-personal preflight must use the same local Team-seat definition as `manager._count_local_team_seat_accounts()`.
- Local Team-seat statuses are `STATUS_ACTIVE`, `STATUS_EXHAUSTED`, and `STATUS_AUTH_INVALID`; `STATUS_PERSONAL` is not a Team seat.
- Current Team-seat target contract is `3 = 1 owner + 2 managed children`. Team-target inputs for rotate/fill/auto-check must be clamped to `1..3`; the child-account hard cap is `2`.
- `SignupProfile` must be a single immutable snapshot passed through registration and OAuth. Its nested `birthday` mapping must reject in-place mutation and must be defensively copied from constructor input. Generated birthday and age must also be self-consistent.
- Registration, direct registration, Team OAuth, and Personal OAuth must not use hardcoded fallback identities such as `User`, `1995-06-15`, or age `25` when a `SignupProfile` is available.
- OAuth about-you must consume the same `SignupProfile`, try the profile's supported birthday field orders, and return failure if the page still remains on about-you after all supported orders. The caller must treat that failure as `bundle=None` so the existing retry/failure-classification policy can handle it.
- `CHATGPT_API_TRANSPORT` defaults to `auto` for Team backend API reads, matching `D:\Desktop\autoteam-1\AutoTeam`; free registration and Personal OAuth still require a real browser context and must not rely on HTTP-only transport.
- Direct free-registration setup may use Team backend HTTP transport only before the protected browser/OAuth boundary. The registration page, Team kick, Personal OAuth, about-you, and plan validation path must remain browser-backed or explicitly `require_browser=True`.
- Direct registration must extract the ChatGPT session token before cleanup on the success path, then pass that token plus the same `SignupProfile` into `_run_post_register_oauth(..., leave_workspace=True)`.
- Legacy `autoteam.cloudflare_temp_email` imports may remain available as a compatibility facade, but the source of truth stays in `autoteam.mail.cf_temp_email`. AI-extract metadata on mail payloads should be preferred before falling back to subject/body parsing.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| local Team seats >= `TEAM_SUB_ACCOUNT_HARD_CAP` before fill-personal | API returns 409 and does not start a background task |
| local Team seats include `STATUS_AUTH_INVALID` | Count them as occupied seats |
| generated birthday implies age outside allowed range | raise `ValueError` during profile generation |
| caller mutates `profile.birthday["year"]` or updates the birthday mapping | raise `TypeError`; profile remains unchanged |
| OAuth about-you appears after registration | Fill it from the same `SignupProfile` used for registration |
| OAuth about-you submit stays on profile page after one birthday order | retry the next supported order from `SignupProfile.positional_birthday_orders()` |
| OAuth about-you stays on profile page after all supported orders | return `None`/failure to the caller; do not continue into consent loop as if profile succeeded |
| Personal OAuth gets `plan_type != "free"` or no bundle | retry up to the existing 5-attempt policy, then record plan drift and fail fast |
| `remove_from_team` fails before Personal OAuth | mark/keep safe local state, record `kick_failed`, and do not run Personal OAuth |
| `RegisterBlocked` phone/add-phone | terminal failure, record category, delete or quarantine according to existing manager logic |
| direct registration page/navigation fails before a normal result | release Playwright page/context/browser and return/raise through the existing retry classifier without losing the local `SignupProfile` contract |

### 5. Good/Base/Bad Cases

- Good: API rejects fill-personal when the local child-seat set already reaches the hard cap, for example `{active, auth_invalid}`.
- Base: a normal `leave_workspace=False` fill does not use the free-path preflight.
- Bad: counting only `active/exhausted` at API level while manager counts `auth_invalid` as a seat, because that starts a task that should have been rejected before browser/mail work.

### 6. Tests Required

- Profile consistency:
  - `tests/unit/test_round12_s3_cherry_pick.py`
  - assert `profile.age == calculate_age(profile.birth_date, today)`
  - assert injected RNG makes `generate_signup_profile(today=..., rng=...)` deterministic
  - assert nested `profile.birthday` mutation raises `TypeError`
  - assert constructor input is copied so later caller-side dict mutation cannot alter the profile
- Registration/OAuth profile propagation:
  - `tests/unit/test_free_registration_hardening.py`
  - assert OAuth about-you consumes the provided `SignupProfile`
  - assert OAuth about-you retries birthday orders and reports failure if no order exits the profile page
  - assert direct registration passes the same `SignupProfile` into `_run_post_register_oauth()`
- API preflight:
  - `tests/unit/test_free_registration_hardening.py`
  - assert `auth_invalid` contributes to Team-seat hard-cap rejection
- Main free registration regression:
  - `tests/unit/test_round11_personal_oauth_retry.py`
  - `tests/unit/test_round11_session_token_injection.py`
  - `tests/unit/test_round12_s4_register_dual_path.py`
  - `tests/unit/test_manager_fill.py`
  - `tests/unit/test_cloudmail.py`

### 7. Wrong vs Correct

#### Wrong

```python
in_team_local = sum(
    1 for a in load_accounts()
    if a.get("status") in (STATUS_ACTIVE, STATUS_EXHAUSTED)
)
```

This misses `STATUS_AUTH_INVALID`, which the manager treats as a Team-seat occupant.

#### Correct

```python
in_team_local = _count_local_team_seat_accounts(load_accounts())
```

Keep the API entrypoint and manager entrypoint aligned so unsafe fill-personal work is rejected before starting browser or mail-provider operations.

## Scenario: Direct Signup Race and Managed Child Validation

### 1. Scope / Trigger

- Trigger: any change to direct signup, `DIRECT_REGISTER_PARALLEL`, multi-master owner fill budgets, Team fill/rotate child creation, or auto-check decisions when local usable children are below target.
- Goal: improve throughput without breaking the `1 owner + 2 managed children = 3 seats` contract or accepting a newly created child before remote/auth/quota validation.

### 2. Signatures

- `DIRECT_REGISTER_PARALLEL: int`, clamped to `1..4`.
- `AUTOTEAM_REGISTER_PARALLEL_MEMORY_WARN_RATIO`, default `0.72`.
- `AUTOTEAM_REGISTER_PARALLEL_MAX_BROWSER_LIVE`, default `4`.
- `_direct_register_parallel_size() -> int`.
- `_cap_direct_register_parallel(requested: int) -> int`.
- `_attempt_chatgpt_signup_only(mail_client, *, acc=None, out_outcome=None) -> dict`.
- `_race_chatgpt_signup(mail_client_factory, *, parallel: int, acc=None, out_outcome=None) -> dict`.
- `create_account_direct(..., parallel=None)`.
- `create_new_account(..., parallel=None)`.
- `cmd_fill(..., direct_parallel=None)`.
- `_wait_for_direct_code_target(page, timeout=_DIRECT_CODE_RENDER_TIMEOUT) -> dict`.
- `_submit_direct_verification_code(page, code_target, verification_code) -> str`.
- `_wait_for_invite_code_target(page, timeout=INVITE_CODE_RENDER_TIMEOUT) -> dict`.
- `_submit_invite_verification_code(page, code_target, verification_code) -> str`.
- `_validate_managed_account_operational(email, *, threshold: int, stage_label="[轮转验收]", chatgpt_api=None) -> bool`.

### 3. Contracts

- `parallel=None` means read `DIRECT_REGISTER_PARALLEL` and then apply local runtime downgrades.
- Direct signup race must run independent signup-only workers. Only the winner is persisted with `add_account()` and passed into `_run_post_register_oauth()`.
- Loser workers that successfully reached Team must be removed from Team, have their temporary mailbox discarded, and have account-scoped IPv6 proxy state released.
- The same `SignupProfile` used by a winning signup worker must be passed into post-registration OAuth.
- `SignupProfile`'s public shape is the current immutable mapping snapshot:
  `SignupProfile(full_name, birthday, age=...)`. Do not add the target repo's
  older positional `SignupProfile("Name", year, month, day, age)` constructor
  back into current code just to satisfy target-only test shape; it weakens the
  immutable birthday contract and obscures browser-form string fields.
- Direct and invite email-verification pages must support both delayed
  single-character split inputs and ordinary single code inputs. Wait helpers
  should return structured modes (`split`, `single`, `advanced`, `timeout`) so
  callers can distinguish "input not rendered yet" from "page already advanced".
- `cmd_fill(..., direct_parallel=N)` must pass `N` into `create_new_account(..., parallel=N)`. Multi-master worker budgets must not remain display-only metadata.
- New managed children created by fill/rotate must pass remote member presence, local auth file, and Codex quota checks before counting as filled.
- If a new child fails validation, release the remote Team seat and mark the local row back to standby with a diagnostic reason.
- `ROTATE_SKIP_REUSE=true` means pending invites and standby reuse are skipped for automated fill/rotate; replacement must be remove-before-create under full Team.
- Auto-check cooldown/full-Team logic must still trigger `auto-fill` when local usable active children are below target and replaceable blockers are present.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| `DIRECT_REGISTER_PARALLEL <= 1` | Run the existing serial direct signup path |
| Runtime memory ratio exceeds warn threshold | Downgrade direct signup race to `1` |
| Browser process count exceeds max live threshold | Downgrade direct signup race to `1` |
| A race worker fails registration | Clean up its temporary mailbox through the existing failure path |
| A non-winning race worker succeeds | Remove it from Team, delete its mailbox, and release its proxy |
| Email verification renders six one-character inputs after a delay | Wait until the split inputs are visible/editable, fill one character per input, then wait for the step to advance |
| Invite verification remains on a code URL but no code input appears | Log `code_input_timeout` with URL, step, page excerpt, and visible input summary, then stop that registration attempt |
| Winning child lacks local auth file | Do not count it as filled; release/mark standby |
| Winning child is absent from remote Team member list | Do not count it as filled; release/mark standby |
| Winning child quota is below threshold or auth fails | Do not count it as filled; release/mark standby |
| Team is full and a replaceable blocker exists | Remove the blocker first, wait for observed capacity, then create the replacement |
| Team is full and no blocker exists | Do not create before remove |

### 5. Good/Base/Bad Cases

- Good: `DIRECT_REGISTER_PARALLEL=3` starts three signup-only attempts, persists one winner, and reports race counts in `out_outcome`.
- Good: multi-master owner fill computes a direct parallel budget and the worker calls `cmd_fill(..., direct_parallel=budget)`.
- Base: serial `parallel=1` keeps the previous duplicate-swap and add-phone behavior.
- Bad: creating a second child before removing an unusable full-Team blocker.
- Bad: counting a newly created child as successful before remote/auth/quota validation.
- Bad: only displaying `direct_register_parallel` in task metadata while `create_account_direct()` still runs serially.

### 6. Tests Required

- `tests/unit/test_free_registration_hardening.py`
  - direct signup race starts multiple signup workers and persists only the winner.
  - high memory or high browser-live runtime snapshots downgrade parallel to `1`.
- `tests/unit/test_workspace_oauth_parity.py`
  - delayed split-code helpers return a `split` target for direct and invite flows.
  - direct split-code submit fills one character per input and waits for the page
    step to advance.
- `tests/unit/test_multi_master.py`
  - owner worker passes `direct_parallel` into `cmd_fill`.
- `tests/unit/test_manager_fill.py`
  - `cmd_fill` passes direct parallel into `create_new_account` and releases a child that fails validation.
- `tests/unit/test_manager_rotate.py`
  - replaceable blocker reasons are concrete.
  - full-Team replacement removes the blocker before creating a child.
- `tests/unit/test_api_status.py`
  - auto-check cooldown/full-Team logic still starts `auto-fill` when replaceable blockers exist.

### 7. Wrong vs Correct

#### Wrong

```python
result = create_new_account(chatgpt, mail_client)
if result:
    current_count += 1
```

This treats "created" as "operational" and can leave a dead child occupying one of the two managed seats.

#### Correct

```python
created_email = create_new_account(chatgpt, mail_client, parallel=direct_parallel)
if created_email and _validate_managed_account_operational(created_email, threshold=threshold, chatgpt_api=chatgpt):
    current_count += 1
else:
    remove_from_team(chatgpt, created_email, return_status=True)
```

Creation, Team membership, local auth, and quota are separate facts. A child becomes usable only after all are validated.

## Scenario: Rotation New Account Strategy and Invite Fallback

### 1. Scope / Trigger

- Trigger: any change to `create_new_account(...)`, `create_account_via_invite(...)`, pending invite cleanup, or the setup/runtime keys `ROTATE_NEW_ACCOUNT_MODE`, `AUTOTEAM_AUTO_JOIN_DOMAINS`, and `ROTATE_DOMAIN_AUTO_JOIN_FALLBACK_INVITE`.
- Goal: prefer verified-domain automatic workspace join when it is safe, while preserving the explicit invite-link registration path for workspaces that cannot auto-join.

### 2. Signatures

- `ROTATE_NEW_ACCOUNT_MODE: domain_auto_join_first | invite_first | direct_first`.
- `AUTOTEAM_AUTO_JOIN_DOMAINS: auto | * | <comma-separated domains>`.
- `ROTATE_DOMAIN_AUTO_JOIN_FALLBACK_INVITE: bool`, default `true`.
- `create_new_account(chatgpt_api, mail_client=None, *, leave_workspace=False, out_outcome=None, acc=None, path_rotator=None, parallel=None)`.
- `create_account_via_invite(chatgpt_api, mail_client=None, *, leave_workspace=False, out_outcome=None, acc=None)`.
- `_prepare_remote_capacity_for_new_seat(chatgpt_api, *, stage_label="[创建]") -> bool`.
- `_cancel_stale_pending_invites_for_capacity(chatgpt_api, *, stage_label="[Team]", mail_client=None) -> list[str]`.

### 3. Contracts

- Valid `ROTATE_NEW_ACCOUNT_MODE` values are:
  - `domain_auto_join_first` (default): direct signup first only when the current mail domain is in `AUTOTEAM_AUTO_JOIN_DOMAINS`.
  - `invite_first`: use explicit Team invite and invitation-link registration first.
  - `direct_first`: force direct signup first without domain allowlist gating.
- `AUTOTEAM_AUTO_JOIN_DOMAINS=auto` means the current mail provider domain set, including runtime `register_domain`, `CLOUDMAIL_DOMAIN`, `MAILLAB_DOMAIN`, and supported provider-specific domain envs.
- `AUTOTEAM_AUTO_JOIN_DOMAINS=*` allows direct-first behavior for all provider domains, but should only be used after verified-domain auto-join has been confirmed.
- Direct signup may run only after remote capacity is checked. If Team members plus pending invites occupy the hard 3-seat cap, cancel only AutoTeam-owned stale pending invites; never cancel main-account, protected-auth, or external/manual invites.
- Direct signup success is not enough to count a child as usable. Fill/rotate must still validate remote Team member presence, local auth file, and Codex quota before incrementing active capacity.
- If `domain_auto_join_first` direct signup fails and `ROTATE_DOMAIN_AUTO_JOIN_FALLBACK_INVITE=true`, the next path is invite-link registration. If that invite fallback also fails, do not retry direct in the same cycle.
- If the mail domain is not allowed for `domain_auto_join_first`, skip direct signup and use the invite path. This keeps non-verified domains from producing free/personal accounts that never join the Team.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| `ROTATE_NEW_ACCOUNT_MODE` is missing or invalid at runtime | Warn and fall back to `domain_auto_join_first` |
| setup save receives invalid `ROTATE_NEW_ACCOUNT_MODE` | return HTTP 400 and do not persist the invalid value |
| setup save receives non-boolean `ROTATE_DOMAIN_AUTO_JOIN_FALLBACK_INVITE` | return HTTP 400 and do not persist the invalid value |
| `AUTOTEAM_AUTO_JOIN_DOMAINS=auto` | derive the allowlist from the configured mail provider domains |
| `AUTOTEAM_AUTO_JOIN_DOMAINS=*` | allow direct-first auto-join for all domains |
| `domain_auto_join_first` with unlisted mail domain | skip direct signup and use invite-link registration |
| direct auto-join fails and invite fallback is enabled | try invite-link registration once |
| direct auto-join fails and invite fallback is disabled | stop the cycle without inviting |
| invite fallback fails after direct already ran | stop the cycle without retrying direct |
| remote members plus pending invites reach the 3-seat cap | cancel only AutoTeam-owned stale pending invites before any new account creation |
| pending invite belongs to main/protected/external account | keep it and do not free capacity by deleting it |

### 5. Good/Base/Bad Cases

- Good: `AUTOTEAM_AUTO_JOIN_DOMAINS=auto` with a verified CloudMail domain runs direct signup before invite, then the created child must still pass remote/auth/quota validation.
- Good: a full remote Team with one stale AutoTeam-owned pending invite cancels that invite first, waits for capacity, and only then creates a replacement.
- Base: `invite_first` preserves the explicit invite-link flow for workspaces where verified-domain auto-join is not available.
- Bad: creating a direct-signup child for an unlisted domain, because it can become a free/personal account outside the Team.
- Bad: deleting pending invites that belong to the main account, protected local auth, or manually-created external users.
- Bad: retrying direct signup again after an invite fallback failure in the same cycle.

### 6. Tests Required

- `tests/unit/test_manager_rotate.py`
  - domain auto-join allowlist runs direct before invite.
  - `invite_first` preserves invite-link registration order.
  - failed domain auto-join falls back to invite when enabled.
  - invite fallback failure does not retry direct again.
  - unlisted mail domain skips direct and uses invite.
- `tests/unit/test_api_status.py`
  - setup save normalizes the three rotation strategy fields.
  - invalid mode/bool values are rejected before writing `.env`.

### 7. Wrong vs Correct

#### Wrong

```python
created = create_account_direct(mail_client)
if not created:
    created = create_account_via_invite(chatgpt_api, mail_client)
if not created:
    created = create_account_direct(mail_client)
```

This ignores the verified-domain allowlist, can create non-Team free accounts for unsupported domains, and retries direct after invite fallback has already failed.

#### Correct

```python
if mode == "domain_auto_join_first" and _mail_domain_auto_join_allowed(mail_client):
    created = create_account_direct(mail_client, parallel=parallel)
    if created or not _domain_auto_join_fallback_invite_enabled():
        return created
    return create_account_via_invite(chatgpt_api, mail_client)
return create_account_via_invite(chatgpt_api, mail_client)
```

Gate direct signup on the configured domain policy, preserve invite-first behavior, and keep each registration path to one attempt per cycle.
