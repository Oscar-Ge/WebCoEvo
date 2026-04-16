import pytest

from linkding_xvr_minimal.browser_task import (
    ExecutableTaskSpec,
    ResetError,
    WebEvolveBrowserTask,
    compile_raw_task,
    goto_start_url,
    is_login_like,
    latest_explicit_completion,
    page_corpus,
)


class FakePage(object):
    def __init__(self, fail_once=False):
        self.calls = []
        self.fail_once = fail_once
        self.url = ""

    def goto(self, url, timeout=None, wait_until=None):
        self.calls.append({"url": url, "timeout": timeout, "wait_until": wait_until})
        if self.fail_once and len(self.calls) == 1:
            raise TimeoutError("transient timeout")
        self.url = url


def test_localhost_goto_uses_30s_timeout_and_retries_once():
    page = FakePage(fail_once=True)

    goto_start_url(page, "http://localhost:9103/login?next=/bookmarks/new", retry_sleep_sec=0)

    assert len(page.calls) == 2
    assert page.calls[0]["timeout"] == 30000
    assert page.calls[1]["timeout"] == 30000
    assert page.calls[0]["wait_until"] == "domcontentloaded"


def test_remote_goto_uses_shorter_timeout_and_does_not_retry():
    page = FakePage(fail_once=True)

    with pytest.raises(TimeoutError):
        goto_start_url(page, "https://example.com")

    assert len(page.calls) == 1
    assert page.calls[0]["timeout"] == 10000


def test_login_next_urls_are_login_like():
    assert is_login_like("http://localhost:9103/login?next=/bookmarks/new")
    assert is_login_like("http://localhost:9103/login/?next=/bookmarks/new")


def test_setup_wraps_start_url_failure_as_reset_error():
    spec = ExecutableTaskSpec(
        task_id=1,
        task_name="browsergym/test",
        site="linkding",
        version="1.45.0",
        family="family",
        intent="goal",
        start_url="http://localhost:9103/bookmarks",
        base_url="http://localhost:9103",
        require_login=False,
        require_reset=False,
    )
    task = WebEvolveBrowserTask(seed=0, spec=spec)
    page = FakePage(fail_once=True)

    with pytest.raises(ResetError):
        task.setup(page, goto_retry_sleep_sec=0, goto_retries=0)


def test_compile_raw_task_includes_normalized_metadata():
    raw = {
        "sites": ["linkding"],
        "task_id": 1600501,
        "start_url": "http://localhost:9103/bookmarks/new",
        "intent": "goal",
        "instantiation_dict": {
            "version": "1.45.0",
            "family_id": "AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS",
            "focus20_source_task_id": 16005,
            "variant": "access",
            "drift_type": "access",
        },
        "eval": {"state_check": {"url_must_include": ["/bookmarks/new"]}},
    }

    spec = compile_raw_task(raw)

    assert spec.task_id == 1600501
    assert spec.base_url == "http://localhost:9103"
    assert spec.metadata["normalized_task"]["source_task_id"] == 16005
    assert spec.state_check["url_must_include"] == ["/bookmarks/new"]


def test_compile_raw_task_drops_missing_storage_state_file():
    raw = {
        "sites": ["linkding"],
        "task_id": 970402,
        "start_url": "http://localhost:9100/bookmarks",
        "intent": "goal",
        "require_login": True,
        "storage_state": "auth/linkding_state.json",
        "instantiation_dict": {
            "version": "1.45.0",
            "family_id": "SF04_ADD_FORM",
            "focus20_source_task_id": 9704,
            "variant": "surface",
            "drift_type": "surface",
        },
        "eval": {"state_check": {"url_must_include": ["/bookmarks/new"]}},
    }

    spec = compile_raw_task(raw)

    assert spec.storage_state is None


def test_page_corpus_includes_form_values_for_prefilled_bookmark_checks():
    class CorpusPage(object):
        def evaluate(self, script):
            assert "querySelectorAll" in script
            return "Bookmark form\nhttps://example.com/focus20/login-prefill-tagged\nFocus20 Login Prefill Tagged\nfocus20-login"

    corpus = page_corpus(CorpusPage())

    assert "https://example.com/focus20/login-prefill-tagged" in corpus
    assert "Focus20 Login Prefill Tagged" in corpus
    assert "focus20-login" in corpus


def test_latest_completion_ignores_browsergym_greeting_and_requires_explicit_answer():
    assert (
        latest_explicit_completion(
            [
                {"role": "assistant", "message": "Hi! I am your UI assistant, I can perform web tasks for you."},
                {"role": "user", "message": "Goal: sign in"},
            ]
        )
        == ""
    )
    assert (
        latest_explicit_completion(
            [
                {"role": "assistant", "message": "Hi! I am your UI assistant, I can perform web tasks for you."},
                {"role": "user", "message": "Goal: sign in"},
                {"role": "assistant", "message": "login tagged"},
            ]
        )
        == "login tagged"
    )


def _spec(**overrides):
    defaults = dict(
        task_id=9700,
        task_name="browsergym/test",
        site="linkding",
        version="1.45.0",
        family="TEST_FAMILY",
        intent="Reach settings and report success.",
        start_url="http://localhost:9099/bookmarks",
        base_url="http://localhost:9099",
        require_login=True,
        require_reset=False,
        state_check={},
        metadata={"normalized_task": {"source_task_id": 9704}},
    )
    defaults.update(overrides)
    return ExecutableTaskSpec(**defaults)


class LoginFallbackPage(object):
    def __init__(
        self,
        login_after_goto=False,
        delayed_login=False,
        manual_bookmarks_after_submit=False,
        sticky_login_url=False,
        password_available_on_login=True,
    ):
        self.url = ""
        self._title_text = ""
        self._body_text = ""
        self._password_available_on_login = password_available_on_login
        self._submitted_login = False
        self._login_after_goto = login_after_goto
        self._delayed_login = delayed_login
        self._manual_bookmarks_after_submit = manual_bookmarks_after_submit
        self._sticky_login_url = sticky_login_url
        self.goto_calls = []
        self.fill_calls = []
        self.click_calls = []
        self.press_calls = []
        self.eval_selector_calls = []
        self.wait_for_url_calls = []

    def goto(self, url, timeout=None, wait_until=None):
        self.goto_calls.append({"url": url, "timeout": timeout, "wait_until": wait_until})
        if self._login_after_goto and "/bookmarks" in url and not self._submitted_login:
            self.url = url.rsplit("/bookmarks", 1)[0] + "/login?next=/bookmarks"
            self._body_text = "Login page"
            self._title_text = "Login - Linkding"
            return
        self.url = url
        self._body_text = "Bookmarks page"
        self._title_text = "Bookmarks - Linkding"

    def title(self):
        return self._title_text

    def fill(self, selector, value, timeout=None):
        self.fill_calls.append({"selector": selector, "value": value, "timeout": timeout})

    def click(self, selector, timeout=None):
        self.click_calls.append({"selector": selector, "timeout": timeout})
        if "/login" not in self.url:
            return
        self._submitted_login = True
        if self._delayed_login:
            self._body_text = "Logging in"
            return
        if self._sticky_login_url:
            self._body_text = "Bookmarks page"
            self._title_text = "Bookmarks - Linkding"
            return
        self.url = self.url.split("?", 1)[0].rsplit("/login", 1)[0] + "/bookmarks"
        self._body_text = "Bookmarks page"
        self._title_text = "Bookmarks - Linkding"

    def press(self, selector, key, timeout=None):
        self.press_calls.append({"selector": selector, "key": key, "timeout": timeout})

    def eval_on_selector(self, selector, script):
        self.eval_selector_calls.append({"selector": selector, "script": script})

    def wait_for_url(self, pattern, timeout=None):
        self.wait_for_url_calls.append({"pattern": pattern, "timeout": timeout})
        if self._delayed_login:
            if self._sticky_login_url:
                self._body_text = "Bookmarks page"
                self._title_text = "Bookmarks - Linkding"
                return
            self.url = self.url.split("?", 1)[0].rsplit("/login", 1)[0] + "/bookmarks"
            self._body_text = "Bookmarks page"
            self._title_text = "Bookmarks - Linkding"

    def wait_for_load_state(self, state, timeout=None):
        return None

    def wait_for_selector(self, selector, timeout=None):
        if selector == "input[name='username']":
            return True
        if selector in {"input[name='password']", "input[type='password']"} and self._password_available_on_login:
            return True
        raise TimeoutError("selector not available: {}".format(selector))

    def evaluate(self, script):
        if "window.location.href" in script:
            return self.url
        if "[data-hardv3-login-reveal]" in script or "Use local credentials" in script:
            return False
        if "document.querySelector(\"input[name='username']\")" in script:
            return "/login" in self.url
        if "document.querySelector(\"input[name='password']\")" in script:
            return "/login" in self.url and self._password_available_on_login
        if "document.body && document.body.innerText" in script:
            return self._body_text
        return ""


def test_setup_performs_baseline_login_when_auth_state_missing():
    page = LoginFallbackPage(login_after_goto=True)
    task = WebEvolveBrowserTask(seed=7, spec=_spec())

    goal, info = task.setup(page)

    assert goal == "Reach settings and report success."
    assert page.fill_calls == [
        {"selector": "input[name='username']", "value": "baseline", "timeout": 3000},
        {"selector": "input[name='password']", "value": "Baseline123!", "timeout": 3000},
    ]
    assert page.click_calls == [
        {"selector": "button[type='submit'], input[type='submit']", "timeout": 3000}
    ]
    assert page.url.endswith("/bookmarks")
    assert info["site"] == "linkding"


def test_setup_waits_for_delayed_login_navigation():
    page = LoginFallbackPage(login_after_goto=True, delayed_login=True)
    task = WebEvolveBrowserTask(seed=7, spec=_spec())

    goal, info = task.setup(page)

    assert goal == "Reach settings and report success."
    assert page.url.endswith("/bookmarks")
    assert page.wait_for_url_calls == [{"pattern": "**/bookmarks*", "timeout": 5000}]
    assert info["base_url"] == "http://localhost:9099"


class TwoStepLoginPage(LoginFallbackPage):
    def __init__(self):
        super().__init__(login_after_goto=True, password_available_on_login=False)
        self._password_available = False
        self._authenticated = False

    def goto(self, url, timeout=None, wait_until=None):
        if self._authenticated:
            self.goto_calls.append({"url": url, "timeout": timeout, "wait_until": wait_until})
            self.url = url
            self._body_text = "Bookmarks page"
            self._title_text = "Bookmarks - Linkding"
            return
        self._password_available = False
        super().goto(url, timeout=timeout, wait_until=wait_until)

    def fill(self, selector, value, timeout=None):
        if selector == "input[name='password']" and not self._password_available:
            raise TimeoutError("password field not revealed yet")
        super().fill(selector, value, timeout=timeout)

    def click(self, selector, timeout=None):
        self.click_calls.append({"selector": selector, "timeout": timeout})
        if "/login" not in self.url:
            return
        if not self._password_available:
            self._password_available = True
            self._body_text = "Login step 2"
            self._title_text = "Login - Linkding"
            return
        self._submitted_login = True
        self._authenticated = True
        self.url = self.url.rsplit("/login", 1)[0] + "/bookmarks"
        self._body_text = "Bookmarks page"
        self._title_text = "Bookmarks - Linkding"

    def evaluate(self, script):
        if "window.location.href" in script:
            return self.url
        if "document.querySelector(\"input[name='username']\")" in script:
            return "/login" in self.url and self._password_available
        if "document.querySelector(\"input[name='password']\")" in script:
            return self._password_available
        if "document.body && document.body.innerText" in script:
            return self._body_text
        return ""

    def wait_for_selector(self, selector, timeout=None):
        if selector == "input[name='password']" and self._password_available:
            return True
        raise TimeoutError("selector not available: {}".format(selector))


def test_setup_handles_two_step_login_before_filling_password():
    page = TwoStepLoginPage()
    task = WebEvolveBrowserTask(seed=7, spec=_spec())

    goal, info = task.setup(page)

    assert goal == "Reach settings and report success."
    assert page.fill_calls == [
        {"selector": "input[name='username']", "value": "baseline", "timeout": 3000},
        {"selector": "input[name='password']", "value": "Baseline123!", "timeout": 3000},
    ]
    assert page.click_calls == [
        {"selector": "button[type='submit'], input[type='submit']", "timeout": 3000},
        {"selector": "button[type='submit'], input[type='submit']", "timeout": 3000},
    ]
    assert page.url.endswith("/bookmarks")
    assert info["site"] == "linkding"


class HiddenAccessRevealLoginPage(LoginFallbackPage):
    def __init__(self):
        super().__init__(login_after_goto=True, password_available_on_login=False)
        self._login_revealed = False

    def fill(self, selector, value, timeout=None):
        if selector in {"input[name='username']", "input[name='password']"} and not self._login_revealed:
            raise TimeoutError("field hidden before reveal: {}".format(selector))
        super().fill(selector, value, timeout=timeout)

    def click(self, selector, timeout=None):
        self.click_calls.append({"selector": selector, "timeout": timeout})
        if "Use local credentials" in selector or "data-hardv3-login-reveal" in selector:
            self._login_revealed = True
            self._password_available_on_login = True
            self._body_text = "Login form revealed"
            return
        if "/login" in self.url:
            self._submitted_login = True
            self.url = self.url.rsplit("/login", 1)[0] + "/bookmarks"
            self._body_text = "Bookmarks page"
            self._title_text = "Bookmarks - Linkding"

    def evaluate(self, script):
        if "window.location.href" in script:
            return self.url
        if "[data-hardv3-login-reveal]" in script or "Use local credentials" in script:
            return "/login" in self.url and not self._login_revealed
        if "document.querySelector(\"input[name='username']\")" in script:
            return "/login" in self.url and self._login_revealed
        if "document.querySelector(\"input[name='password']\")" in script:
            return "/login" in self.url and self._login_revealed
        if "document.body && document.body.innerText" in script:
            return self._body_text
        return ""

    def wait_for_selector(self, selector, timeout=None):
        if selector in {"input[name='username']", "input[name='password']"} and self._login_revealed:
            return True
        raise TimeoutError("selector not available: {}".format(selector))


def test_setup_reveals_hidden_access_login_before_filling_username():
    page = HiddenAccessRevealLoginPage()
    task = WebEvolveBrowserTask(seed=7, spec=_spec())

    goal, info = task.setup(page)

    assert goal == "Reach settings and report success."
    assert page.click_calls[0]["selector"] in {
        "button[data-hardv3-login-reveal]",
        "button:has-text('Use local credentials')",
        "text=Use local credentials",
    }
    assert page.fill_calls == [
        {"selector": "input[name='username']", "value": "baseline", "timeout": 3000},
        {"selector": "input[name='password']", "value": "Baseline123!", "timeout": 3000},
    ]
    assert page.url.endswith("/bookmarks")
    assert info["site"] == "linkding"
