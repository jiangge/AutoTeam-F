import pytest

from autoteam import accounts as accounts_mod
from autoteam import api, codex_auth
from autoteam import manager as manager_mod
from autoteam.signup_profile import SignupProfile


def test_post_fill_personal_preflight_counts_auth_invalid_as_team_seat(monkeypatch):
    accounts = [
        {"email": "active-1@example.com", "status": accounts_mod.STATUS_ACTIVE},
        {"email": "exhausted-1@example.com", "status": accounts_mod.STATUS_EXHAUSTED},
        {"email": "auth-invalid-1@example.com", "status": accounts_mod.STATUS_AUTH_INVALID},
        {"email": "auth-invalid-2@example.com", "status": accounts_mod.STATUS_AUTH_INVALID},
    ]

    monkeypatch.setattr(accounts_mod, "load_accounts", lambda: accounts)
    monkeypatch.setattr(api, "_start_task", lambda *args, **kwargs: pytest.fail("_start_task should not run"))

    with pytest.raises(api.HTTPException) as exc:
        api.post_fill(api.TaskParams(target=1, leave_workspace=True))

    assert exc.value.status_code == 409
    assert f"Team 子号已满 4/{manager_mod.TEAM_SUB_ACCOUNT_HARD_CAP}" in str(exc.value.detail)


class _FakeElement:
    def __init__(self, page=None, *, visible=True):
        self.page = page
        self.visible = visible
        self.filled = []
        self.typed = []
        self.clicked = 0

    def is_visible(self, **_kwargs):
        return self.visible

    def is_editable(self, **_kwargs):
        return True

    def fill(self, value):
        self.filled.append(value)

    def click(self, **_kwargs):
        self.clicked += 1
        if self.page is not None:
            self.page.active_element = self
            if self is getattr(self.page, "submit", None):
                self.page.submit_about_you()


class _FakeLocator:
    def __init__(self, elements):
        self.elements = list(elements)

    @property
    def first(self):
        if self.elements:
            return self.elements[0]
        return _FakeElement(visible=False)

    def all(self):
        return self.elements


class _FakeKeyboard:
    def __init__(self, page):
        self.page = page

    def press(self, *_args, **_kwargs):
        return None

    def type(self, value, **_kwargs):
        self.page.active_element.typed.append(value)


class _FakeOtpInput:
    def __init__(self, *, visible=True, text=""):
        self.visible = visible
        self.text = text
        self.filled_values = []
        self.clicked = False

    def is_visible(self, timeout=0):
        return self.visible

    def fill(self, value):
        self.filled_values.append(value)

    def click(self, timeout=0, force=False):
        self.clicked = True

    def type(self, value, delay=0):
        self.filled_values.append(value)

    def inner_text(self, timeout=0):
        return self.text


class _FakeOtpCollection:
    def __init__(self, items=None, text=None):
        self._items = list(items or [])
        self._text = text

    @property
    def first(self):
        if self._items:
            return self._items[0]
        return _FakeOtpInput(visible=False)

    def all(self):
        return list(self._items)

    def inner_text(self, timeout=0):
        if self._text is None:
            raise AssertionError("unexpected inner_text call")
        return self._text


class _FakeOtpPage:
    def __init__(self, *, url="https://auth.openai.com/email-verification", body="", slot_inputs=None, otp_input=None):
        self.url = url
        self._body = body
        self._slot_inputs = list(slot_inputs or [])
        self._otp_input = otp_input or _FakeOtpInput(visible=False)
        self.submit_button = _FakeOtpInput(visible=True)
        self.keyboard = type("_Keyboard", (), {"type": lambda _self, *_args, **_kwargs: None})()

    def locator(self, selector):
        if selector == "body":
            return _FakeOtpCollection(text=self._body)
        if selector == codex_auth._OTP_SINGLE_INPUT_SELECTORS:
            return _FakeOtpCollection(items=self._slot_inputs)
        if selector == codex_auth._OTP_INPUT_SELECTORS:
            return _FakeOtpCollection(items=[self._otp_input])
        if selector in {
            'button[type="submit"]',
            'button:has-text("Continue")',
            'button:has-text("继续")',
            'button:has-text("Verify")',
        }:
            return _FakeOtpCollection(items=[self.submit_button])
        return _FakeOtpCollection(items=[])


class _FakeChooseAccountPage:
    _GENERIC_SELECTORS = {
        "button",
        "a",
        '[role="button"]',
        '[role="option"]',
        '[aria-selected="true"]',
        '[aria-selected="false"]',
        "[data-state]",
        "li",
        "label",
        "div",
    }

    def __init__(self, *, account_elements, continue_button=None):
        self.url = "https://auth.openai.com/choose-an-account"
        self._account_elements = list(account_elements)
        self._continue_button = continue_button or _FakeOtpInput(visible=False)

    def locator(self, selector):
        if selector == "body":
            return _FakeOtpCollection(text="Choose an account Continue as user@example.com")
        if selector == 'button:has-text("Continue"), button:has-text("继续"), button:has-text("Allow")':
            return _FakeOtpCollection(items=[self._continue_button])
        if selector in self._GENERIC_SELECTORS:
            return _FakeOtpCollection(items=self._account_elements)
        return _FakeOtpCollection(items=[])


def test_codex_otp_helper_fills_segmented_inputs():
    slots = [_FakeOtpInput() for _ in range(6)]
    page = _FakeOtpPage(slot_inputs=slots)

    assert codex_auth._fill_otp_code(page, "481556") is True

    assert [slot.filled_values[-1] for slot in slots] == list("481556")


def test_codex_resolve_email_verification_marks_used_after_success(monkeypatch):
    slots = [_FakeOtpInput() for _ in range(6)]
    page = _FakeOtpPage(slot_inputs=slots)
    used_email_ids = set()

    monkeypatch.setattr(codex_auth, "_poll_mail_verification_code", lambda *args, **kwargs: ("481556", 1888))
    monkeypatch.setattr(codex_auth, "_wait_for_otp_submit_result", lambda *args, **kwargs: ("accepted", None))
    monkeypatch.setattr(codex_auth.time, "sleep", lambda *_args, **_kwargs: None)

    status = codex_auth._resolve_email_verification(
        page,
        mail_client=object(),
        email="user@example.com",
        after_email_id=1000,
        used_email_ids=used_email_ids,
        wait_log="[Codex] test wait emailId > %d",
    )

    assert status == "accepted"
    assert used_email_ids == {1888}
    assert [slot.filled_values[-1] for slot in slots] == list("481556")
    assert page.submit_button.clicked is True


def test_codex_select_oauth_account_clicks_matching_email(monkeypatch):
    other = _FakeOtpInput(text="other@example.com")
    target = _FakeOtpInput(text="user@example.com")
    confirm = _FakeOtpInput(text="Continue")
    page = _FakeChooseAccountPage(account_elements=[other, target], continue_button=confirm)

    monkeypatch.setattr(codex_auth.time, "sleep", lambda *_args, **_kwargs: None)

    assert codex_auth._is_choose_account_page(page) is True
    assert codex_auth._select_oauth_account(page, "user@example.com") is True
    assert other.clicked is False
    assert target.clicked is True
    assert confirm.clicked is True


class _FakeOAuthAboutYouPage:
    def __init__(self, *, spinbuttons=True, expected_order=None):
        self.url = "https://auth.openai.com/about-you"
        self.name = _FakeElement(self)
        self.submit = _FakeElement(self)
        self.label = _FakeElement(self)
        self.age = _FakeElement(self, visible=not spinbuttons)
        self.spinbuttons = [_FakeElement(self), _FakeElement(self), _FakeElement(self)] if spinbuttons else []
        self.active_element = None
        self.keyboard = _FakeKeyboard(self)
        self.expected_order = expected_order
        self.submit_attempts = 0

    def submit_about_you(self):
        self.submit_attempts += 1
        if self.expected_order is None:
            self.url = "https://auth.openai.com/oauth/authorize"
            return
        latest = [button.typed[-1] if button.typed else "" for button in self.spinbuttons]
        if latest == self.expected_order:
            self.url = "https://auth.openai.com/oauth/authorize"

    def locator(self, selector):
        if selector == '[role="spinbutton"]':
            return _FakeLocator(self.spinbuttons)
        if selector == 'input[name="name"]':
            return _FakeLocator([self.name])
        if selector.startswith("input[name=\"age\""):
            return _FakeLocator([self.age])
        if selector == "text=生日日期":
            return _FakeLocator([self.label])
        if "button" in selector:
            return _FakeLocator([self.submit])
        return _FakeLocator([])


def test_oauth_about_you_uses_signup_profile_snapshot(monkeypatch):
    profile = SignupProfile(
        full_name="Alice Carter",
        birthday={"year": "1989", "month": "07", "day": "14"},
        age="36",
    )
    page = _FakeOAuthAboutYouPage(spinbuttons=True)

    monkeypatch.setattr(codex_auth.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(codex_auth, "_screenshot", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        codex_auth,
        "_wait_for_oauth_about_you_exit",
        lambda page, **_kwargs: "about-you" not in page.url,
    )

    assert codex_auth._complete_oauth_about_you(page, signup_profile=profile) is True
    assert page.name.filled == ["Alice Carter"]
    assert [button.typed for button in page.spinbuttons] == [["1989"], ["07"], ["14"]]
    assert page.submit.clicked == 1


def test_oauth_about_you_retries_birthday_orders_until_page_exits(monkeypatch):
    profile = SignupProfile(
        full_name="Alice Carter",
        birthday={"year": "1989", "month": "07", "day": "14"},
        age="36",
    )
    page = _FakeOAuthAboutYouPage(spinbuttons=True, expected_order=["07", "14", "1989"])

    monkeypatch.setattr(codex_auth.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(codex_auth, "_screenshot", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        codex_auth,
        "_wait_for_oauth_about_you_exit",
        lambda page, **_kwargs: "about-you" not in page.url,
    )

    assert codex_auth._complete_oauth_about_you(page, signup_profile=profile) is True
    assert page.submit_attempts == 2
    assert [button.typed for button in page.spinbuttons] == [
        ["1989", "07"],
        ["07", "14"],
        ["14", "1989"],
    ]


def test_oauth_about_you_returns_false_when_profile_page_never_exits(monkeypatch):
    profile = SignupProfile(
        full_name="Alice Carter",
        birthday={"year": "1989", "month": "07", "day": "14"},
        age="36",
    )
    page = _FakeOAuthAboutYouPage(spinbuttons=True, expected_order=["never", "matches", "this"])

    monkeypatch.setattr(codex_auth.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(codex_auth, "_screenshot", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        codex_auth,
        "_wait_for_oauth_about_you_exit",
        lambda page, **_kwargs: "about-you" not in page.url,
    )

    assert codex_auth._complete_oauth_about_you(page, signup_profile=profile) is False
    assert page.submit_attempts == 3


def test_create_account_direct_reuses_signup_profile_for_register_and_oauth(monkeypatch):
    profile = SignupProfile(
        full_name="Noah Bennett",
        birthday={"year": "1991", "month": "04", "day": "09"},
        age="35",
    )
    captured = {}

    class _FakeMailClient:
        def create_temp_email(self):
            return "mail-id", "new-user@example.com"

        def delete_account(self, *_args, **_kwargs):
            return None

    def fake_register_once(_mail_client, email, password, *, cloudmail_account_id=None, signup_profile=None):
        captured["register"] = {
            "email": email,
            "password": password,
            "cloudmail_account_id": cloudmail_account_id,
            "signup_profile": signup_profile,
        }
        return True, "session-token"

    def fake_post_oauth(email, password, mail_client, **kwargs):
        captured["oauth"] = {
            "email": email,
            "password": password,
            "mail_client": mail_client,
            **kwargs,
        }
        return email

    monkeypatch.setattr(manager_mod, "generate_signup_profile", lambda: profile)
    monkeypatch.setattr(manager_mod, "random_password", lambda: "Password123!")
    monkeypatch.setattr(manager_mod, "_register_direct_once", fake_register_once)
    monkeypatch.setattr(manager_mod, "_run_post_register_oauth", fake_post_oauth)
    monkeypatch.setattr(manager_mod, "add_account", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(manager_mod, "get_chatgpt_account_id", lambda: "workspace-account")

    result = manager_mod.create_account_direct(mail_client=_FakeMailClient(), leave_workspace=True)

    assert result == "new-user@example.com"
    assert captured["register"]["signup_profile"] is profile
    assert captured["oauth"]["signup_profile"] is profile
    assert captured["oauth"]["chatgpt_session_token"] == "session-token"
    assert captured["oauth"]["leave_workspace"] is True


def test_create_account_direct_returns_none_when_post_oauth_not_ready(monkeypatch):
    profile = SignupProfile(
        full_name="Nolan Price",
        birthday={"year": "1990", "month": "05", "day": "04"},
        age="36",
    )
    release_calls = []

    class _FakeMailClient:
        pass

    monkeypatch.setattr(
        manager_mod,
        "_attempt_chatgpt_signup_only",
        lambda *_args, **_kwargs: {
            "success": True,
            "email": "not-ready@example.com",
            "password": "Password123!",
            "account_id": "mail-id",
            "session_token": "session-token",
            "signup_profile": profile,
            "auth_proxy_url": "http://auth-proxy",
            "playwright_proxy_url": "http://playwright-proxy",
            "mail_client": _FakeMailClient(),
        },
    )
    monkeypatch.setattr(manager_mod, "add_account", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(manager_mod, "get_chatgpt_account_id", lambda: "workspace-account")
    monkeypatch.setattr(
        manager_mod,
        "_run_post_register_oauth",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        manager_mod,
        "_release_account_ipv6_proxy",
        lambda email: release_calls.append(email),
    )

    result = manager_mod.create_account_direct(mail_client=_FakeMailClient(), leave_workspace=False, parallel=1)

    assert result is None
    assert release_calls == ["not-ready@example.com"]


def test_direct_register_step_recognizes_auth_error_page(monkeypatch):
    page = type("_Page", (), {"url": "https://chatgpt.com/api/auth/error"})()

    monkeypatch.setattr(manager_mod, "_is_google_redirect", lambda _page: False)

    assert manager_mod._detect_direct_register_step(page) == "error"


def test_create_account_direct_races_signup_workers_and_uses_winner(monkeypatch):
    calls = []
    added = []
    out = {}

    class _RaceMailClient:
        counter = 0
        provider_name = "race"

        def __init__(self):
            type(self).counter += 1
            self.idx = type(self).counter

        def login(self):
            return None

        def create_temp_email(self):
            return f"mail-{self.idx}", f"user-{self.idx}@example.com"

        def delete_account(self, *_args, **_kwargs):
            return None

    def fake_register_once(_mail_client, email, password, *, cloudmail_account_id=None, signup_profile=None):
        calls.append(
            {
                "email": email,
                "password": password,
                "cloudmail_account_id": cloudmail_account_id,
                "signup_profile": signup_profile,
            }
        )
        return email == "user-2@example.com", f"token-for-{email}"

    monkeypatch.setattr(manager_mod, "_ensure_account_ipv6_proxy", lambda _email: ("", ""))
    monkeypatch.setattr(manager_mod, "_release_account_ipv6_proxy", lambda _email: None)
    monkeypatch.setattr(manager_mod, "_register_direct_once", fake_register_once)
    monkeypatch.setattr(manager_mod, "_is_email_in_team", lambda _email: False)
    monkeypatch.setattr(manager_mod, "time", manager_mod.time)
    monkeypatch.setattr(manager_mod.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(manager_mod, "add_account", lambda *args, **kwargs: added.append((args, kwargs)))
    monkeypatch.setattr(manager_mod, "get_chatgpt_account_id", lambda: "workspace-account")
    monkeypatch.setattr(
        manager_mod,
        "_run_post_register_oauth",
        lambda email, *_args, **_kwargs: email,
    )

    result = manager_mod.create_account_direct(
        mail_client=_RaceMailClient(),
        out_outcome=out,
        parallel=3,
    )

    assert result == "user-2@example.com"
    assert sorted({call["email"] for call in calls}) == [
        "user-1@example.com",
        "user-2@example.com",
        "user-3@example.com",
    ]
    assert sum(1 for call in calls if call["email"] == "user-2@example.com") == 1
    assert added[0][0][0] == "user-2@example.com"
    assert out["direct_register_parallel"] == 3
    assert out["direct_register_failures"] == 2


def test_direct_register_parallel_downgrades_when_memory_high(monkeypatch):
    monkeypatch.setenv("AUTOTEAM_REGISTER_PARALLEL_MEMORY_WARN_RATIO", "0.70")
    monkeypatch.setattr(
        "autoteam.runtime_resources.collect_runtime_resource_snapshot",
        lambda: {"cgroup_memory_usage_ratio": 0.95, "browser_process_live": 0},
    )

    assert manager_mod._cap_direct_register_parallel(4) == 1


def test_run_post_register_oauth_passes_signup_profile_to_team_oauth(monkeypatch):
    profile = SignupProfile(
        full_name="Mia Wilson",
        birthday={"year": "1990", "month": "02", "day": "03"},
        age="36",
    )
    login_calls = []
    updates = []

    class _FakeChatGPTTeamAPI:
        def start(self):
            return None

        def stop(self):
            return None

    monkeypatch.setattr(manager_mod, "ChatGPTTeamAPI", _FakeChatGPTTeamAPI)
    monkeypatch.setattr(
        "autoteam.master_health.is_master_subscription_healthy",
        lambda _api: (True, "active", {}),
    )
    monkeypatch.setattr(
        manager_mod,
        "login_codex_via_browser",
        lambda *args, **kwargs: login_calls.append({"args": args, "kwargs": kwargs})
        or {
            "plan_type": "team",
            "plan_type_raw": "team",
            "plan_supported": True,
            "account_id": "codex-account",
        },
    )
    monkeypatch.setattr(manager_mod, "save_auth_file", lambda _bundle: "auths/new-user.json")
    monkeypatch.setattr(manager_mod, "update_account", lambda email, **kwargs: updates.append((email, kwargs)))
    monkeypatch.setattr(manager_mod, "get_chatgpt_account_id", lambda: "workspace-account")

    result = manager_mod._run_post_register_oauth(
        "new-user@example.com",
        "Password123!",
        mail_client=object(),
        signup_profile=profile,
    )

    assert result == "new-user@example.com"
    assert login_calls[0]["kwargs"]["signup_profile"] is profile
    assert updates[-1][0] == "new-user@example.com"
    assert updates[-1][1]["status"] == accounts_mod.STATUS_ACTIVE
