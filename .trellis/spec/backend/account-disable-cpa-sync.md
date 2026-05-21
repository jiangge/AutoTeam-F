# Account Disable and CPA Sync Contract

## Scenario: local account disable controls

### 1. Scope / Trigger

- Trigger: an operator needs to keep an account record and auth file locally while excluding that account from automated checks, rotation, reuse, and CPA publication.
- Applies to: `src/autoteam/accounts.py`, `src/autoteam/api.py`, `src/autoteam/cpa_sync.py`, and Dashboard account operations.

### 2. Signatures

- Account row field: `disabled: bool`.
- Helper: `is_account_disabled(acc: dict | None) -> bool`.
- API:
  - `POST /api/accounts/{email}/disable`
  - `POST /api/accounts/{email}/enable`
  - `POST /api/accounts/bulk/disable` with body `{ "emails": string[] }`
  - `POST /api/accounts/bulk/enable` with body `{ "emails": string[] }`
- Status response account fields:
  - `status`: display status, `disabled` for disabled non-main accounts.
  - `raw_status`: persisted lifecycle status such as `active`, `standby`, or `personal`.

### 3. Contracts

- `load_accounts()` and `save_accounts()` must normalize legacy rows so missing `disabled` becomes `false`.
- Main account rows must not be disabled or enabled through these endpoints.
- Disabled non-main accounts remain visible in `/api/status`, but quota probing must skip them.
- Disabled rows must be excluded from `get_active_accounts()` and `get_standby_accounts()`.
- Auto-check and rotation candidate selection must treat disabled rows as unavailable.
- `sync_to_cpa()` must not upload disabled accounts.
- `STATUS_DEGRADED_GRACE` accounts are non-publishable for remote sync: full CPA sync must not upload them, and single-credential sync must return `account_not_active` instead of uploading to CPA/Sub2API. Existing remote CPA copies may be removed only through the normal remote-delete guard when the active pool is stable.
- A disabled account's local auth file is still protected from accidental CPA remote deletion by the existing same-file delete guard.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Empty or invalid email | `400` with a business message |
| Main account email | `400`, never mutate `disabled` |
| Unknown email | `404` for single toggle; `missing_emails` entry for bulk |
| Already target state | No mutation; include in `unchanged_emails` for bulk |
| Mixed bulk payload | Deduplicate, skip main, report missing, mutate valid rows |
| Disabled row in status | Return `status="disabled"` and preserve `raw_status` |

### 5. Good/Base/Bad Cases

- Good: disabling an `active` account keeps the row and auth file, hides it from quota checks, and surfaces `raw_status="active"` plus `status="disabled"`.
- Base: enabling a disabled standby account restores `status="standby"` in the display status.
- Bad: deleting or moving auth files when an account is merely disabled.

### 6. Tests Required

- `tests/unit/test_accounts.py`
  - Normalizes missing `disabled`.
  - Excludes disabled active/standby rows from active/reuse helpers.
- `tests/unit/test_api_status.py`
  - Single disable/enable.
  - Bulk disable/enable with missing, unchanged, duplicate, and main-account rows.
  - `/api/status` skips disabled quota checks and counts disabled rows.
- `tests/unit/test_cpa_sync.py`
  - Disabled account is skipped for CPA upload.
  - `STATUS_DEGRADED_GRACE` account is skipped for CPA upload.
  - Matching remote auth file is retained by delete guard.
- `tests/unit/test_sync_targets.py`
  - `STATUS_DEGRADED_GRACE` single-credential sync skips CPA/Sub2API upload with `account_not_active`.

### 7. Wrong vs Correct

#### Wrong

```python
active = [a for a in load_accounts() if a["status"] == STATUS_ACTIVE]
```

This lets a locally disabled account re-enter auto-check, rotation, or CPA sync.

#### Correct

```python
active = [
    a for a in load_accounts()
    if a["status"] == STATUS_ACTIVE and not is_account_disabled(a)
]
```

## Scenario: CPA list failure handling

### 1. Scope / Trigger

- Trigger: CPA may be unreachable, return a 5xx page, return non-JSON, or return a malformed JSON shape.
- Applies to `list_cpa_files()` and all call sites that depend on CPA truth.

### 2. Signatures

- `list_cpa_files() -> list[dict]`.
- Raises `RuntimeError` on request, HTTP, JSON, or schema failure.

### 3. Contracts

- Do not convert CPA failure into `[]`.
- Do not treat remote failure as "remote has no files".
- Callers performing sync or cleanup should fail loudly or surface the error rather than deleting based on false emptiness.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| `requests.get` raises | `RuntimeError("[CPA] auth-files list request failed: ...")` |
| HTTP status is not `200` | `RuntimeError("[CPA] auth-files list failed: HTTP ...")` |
| Body is non-JSON | `RuntimeError("[CPA] auth-files list returned non-JSON response")` |
| JSON `files` is missing or not a list | `RuntimeError("[CPA] auth-files list response missing files list")` |

### 5. Good/Base/Bad Cases

- Good: CPA returns `{"files": [...]}` and the sync proceeds.
- Base: CPA has zero files and explicitly returns `{"files": []}`.
- Bad: CPA returns a `503` HTML page and the app interprets that as an empty CPA file set.

### 6. Tests Required

- `tests/unit/test_cpa_sync.py::test_list_cpa_files_raises_on_non_200`.
- `tests/unit/test_cpa_sync.py::test_list_cpa_files_raises_on_non_json`.

### 7. Wrong vs Correct

#### Wrong

```python
if resp.status_code != 200:
    return []
```

#### Correct

```python
if resp.status_code != 200:
    raise RuntimeError(f"[CPA] auth-files list failed: HTTP {resp.status_code}")
```

## Scenario: Managed-account deletion and Team state parsing

### 1. Scope / Trigger

- Trigger: deleting a locally managed account, rendering `/api/team/members`, or reconciling local rows against ChatGPT Team member/invite responses.
- Applies to `src/autoteam/account_ops.py`, `src/autoteam/api.py`, and any caller that consumes `fetch_team_state()`.
- Goal: tolerate known ChatGPT Team API response-shape drift without deleting protected local credentials or mutating the wrong remote target.

### 2. Signatures

- `fetch_team_state(chatgpt_api) -> tuple[list, list]`.
- `extract_team_members(payload) -> list`.
- `extract_team_invites(payload) -> list`.
- `team_member_email(member) -> str`.
- `team_member_user_id(member) -> str | None`.
- `team_member_role(member) -> str | None`.
- `team_invite_email(invite) -> str`.
- `delete_team_invite(chatgpt_api, account_id: str, invite: dict | None = None, *, invite_id=None, email: str | None = None) -> dict`.
- `delete_managed_account(email, *, remove_remote=True, remove_cloudmail=True, sync_cpa_after=True, chatgpt_api=None, mail_client=None, remote_state=None) -> dict`.
- `GET /api/team/members` response rows must contain `email`, `role`, `user_id`, `is_local`, and `type`.

### 3. Contracts

- Team member responses may be a list or a dict containing `items`, `users`, `members`, or `account_users`.
- Team invite responses may be a list or a dict containing `items`, `invites`, or `account_invites`.
- Member identity fields may live at the top level, under `user`, or under `account_user`.
- Invite email fields may live at the top level, under `user`, or under `account_user`.
- Team API `401` / `403` and HTML/non-JSON responses must raise a readable `RuntimeError` that tells the operator to redo administrator login.
- Invite cancellation must first try `DELETE /backend-api/accounts/{account_id}/invites/{invite_id}` when an id exists, then fall back to collection delete with `{"email_address": email}`.
- Deleting an account must call `delete_account_from_configured_targets(..., include_disabled=True)` so CPA and Sub2API cleanup use the shared configured-target router.
- Local auth paths may be stored as absolute paths, `/app/...` container paths, `data/auths/...`, or `auths/...`; deletion must resolve known candidates without string-only assumptions.
- Non-main local credential seats with an auth file and no mail binding are protected from destructive deletion; the cleanup result must expose `protected_local_credential=true`.
- Mail-provider deletion must prefer `mail_account_id` and fall back to legacy `cloudmail_account_id`.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Team users/invites return known list-wrapper shapes | Return extracted records without dropping nested identity fields |
| Team users endpoint returns HTML/login/challenge page | Raise `RuntimeError` containing `接口返回了非 JSON 内容` and redo-login guidance |
| Team users endpoint returns `401` or `403` | Raise `RuntimeError` containing redo-login guidance |
| Invite-id delete returns non-success and email is known | Retry collection delete with `email_address` |
| Account auth file uses a container `/app/...` path | Resolve the corresponding project-local candidate before deletion |
| Account has local auth and no mail binding | Return cleanup with `protected_local_credential=true`; do not delete local row, auth file, CPA, or Sub2API |
| Account has `mail_account_id` | Delete that provider account id, even when `cloudmail_account_id` is missing |
| Configured target cleanup returns CPA/Sub2API deletions | Surface them as `cleanup["cpa_files"]` and `cleanup["sub2api_accounts"]` |

### 5. Good/Base/Bad Cases

- Good: `/api/team/members` receives `{"items": [{"user": {"email": "...", "id": "...", "account_role": "admin"}}]}` and returns normalized row fields for the frontend.
- Good: deleting a provider-backed account removes the Team member/invite, local auth file, local row, configured remote targets, and provider mailbox id once.
- Base: a personal or auth-invalid row still skips Team remote fetch, but local and configured-target cleanup remains available.
- Bad: assuming `member["email"]` and `member["user_id"]` are always top-level fields; this silently hides nested Team rows from cleanup and UI.
- Bad: calling CPA-only cleanup directly from `delete_managed_account()`; this bypasses Sub2API and configured-target availability rules.
- Bad: deleting a manually imported credential row simply because it has an auth file but no provider mailbox binding.

### 6. Tests Required

- `tests/unit/test_account_ops.py`
  - `fetch_team_state()` parses member/invite wrapper variants and nested identity fields.
  - Team API HTML/auth failures raise readable redo-login errors.
  - `delete_team_invite()` falls back from invite-id delete to collection delete.
  - `delete_managed_account()` uses `mail_account_id`, configured-target deletion, and local credential protection.
  - `/api/team/members` renders normalized nested Team rows and still stops `ChatGPTTeamAPI`.
- Regression suites:
  - `tests/unit/test_round6_patches.py`
  - `tests/unit/test_spec2_lifecycle.py`
  - `tests/unit/test_cpa_sync.py`
  - `tests/unit/test_sub2api_sync.py`

### 7. Wrong vs Correct

#### Wrong

```python
email = (member.get("email") or "").lower()
user_id = member.get("user_id") or member.get("id")
```

This misses nested `user` / `account_user` shapes and can leave real Team seats undeleted.

#### Correct

```python
email = team_member_email(member)
user_id = team_member_user_id(member)
```

Use the shared shape helpers wherever Team state is parsed, including cleanup and `/api/team/members`.

## Scenario: active CPA publish preflight

### 1. Scope / Trigger

- Trigger: `sync_to_cpa()` is about to publish a local `STATUS_ACTIVE` auth file or decide whether an existing CPA copy should be deleted.
- Applies to `src/autoteam/cpa_sync.py` and the unit tests that cover active credential publish branches.
- Goal: make publish/delete decisions from live quota truth, not from the local status string alone.

### 2. Signatures

- `_active_auth_publish_decision(acc: dict, path: Path) -> str`
- `sync_to_cpa() -> dict`
- `check_codex_quota(access_token, timeout=8) -> tuple[str, dict | None]`

### 3. Contracts

- `quota_status == "ok"` means the active credential may be published.
- `quota_status == "network_error"` means the remote copy stays in place and the local row waits for a later round.
- Any other non-`ok` quota status means the existing remote copy should follow the delete path used for stale active files.
- A successful live `ok` check may refresh the local auth bundle's `proxy_url` before upload.
- `sync_to_cpa()` should surface active-publish counters so operators can see why a file was uploaded, kept, or deleted.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Active quota check returns `ok` | Upload the local auth file and refresh proxy metadata when available |
| Active quota check returns `network_error` | Keep the remote copy and do not delete or upload that file |
| Active quota check returns `exhausted` or another terminal failure | Delete the remote copy through the existing delete path |
| Active quota probe raises | Log the failure and keep the remote copy for the next round |

### 5. Good/Base/Bad Cases

- Good: a live `ok` credential is republished with fresh proxy metadata.
- Base: a transient network error leaves the remote CPA copy untouched.
- Bad: deleting or uploading active CPA files purely because the local row still says `active`.

### 6. Tests Required

- `tests/unit/test_cpa_sync.py::test_sync_to_cpa_skips_exhausted_active_credential_before_upload`
- `tests/unit/test_cpa_sync.py::test_sync_to_cpa_keeps_remote_on_active_quota_network_error`
- `tests/unit/test_cpa_sync.py::test_sync_to_cpa_refreshes_proxy_url_before_upload`

### 7. Wrong vs Correct

#### Wrong

```python
if acc.get("status") == STATUS_ACTIVE:
    upload_to_cpa(path)
```

#### Correct

```python
quota_status, _info = check_codex_quota(access_token, timeout=8)
if quota_status == "ok":
    upload_to_cpa(path)
elif quota_status == "network_error":
    keep_remote_copy()
else:
    delete_from_cpa(path.name)
```

Live quota must decide the publish branch before the remote copy is touched.
