import json
import random
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from linkding_xvr_minimal.tasks import normalize_task_metadata

try:
    import requests
except Exception:  # pragma: no cover - benchmark extra may be absent in unit-test envs
    requests = None


LOCAL_START_URL_TIMEOUT_MS = 30000
REMOTE_START_URL_TIMEOUT_MS = 10000
FENCED_CODE_RE = re.compile(r"^\s*```(?:[A-Za-z0-9_+-]+)?\s*\n(.*?)\n?```\s*$", re.DOTALL)
SEND_MSG_RE = re.compile(r'^\s*send_msg_to_user\((.+)\)\s*$', re.DOTALL)
EXPLICIT_FINAL_RE = re.compile(
    r"^\s*(?:action:\s*)?(?:final answer|done|completed)\s*:\s*(.+)$",
    re.IGNORECASE | re.DOTALL,
)
ACTION_CALL_RE = re.compile(r"^\s*[a-z_]+\s*\(", re.IGNORECASE)


class ResetError(RuntimeError):
    pass


class ExecutableTaskSpec(object):
    def __init__(
        self,
        task_id,
        task_name,
        site,
        version,
        family,
        intent,
        start_url,
        base_url,
        require_login,
        require_reset,
        storage_state=None,
        evaluator=None,
        state_check=None,
        must_include=None,
        metadata=None,
    ):
        self.task_id = int(task_id)
        self.task_name = task_name
        self.site = site
        self.version = version
        self.family = family
        self.intent = intent
        self.start_url = start_url
        self.base_url = base_url
        self.require_login = bool(require_login)
        self.require_reset = bool(require_reset)
        self.storage_state = storage_state
        self.evaluator = evaluator or {}
        self.state_check = state_check or {}
        self.must_include = must_include or []
        self.metadata = metadata or {}


def is_login_like(url):
    return bool(re.search(r"/login/?(?:\\?|$)", str(url or "").lower()))


def is_local_url(url):
    parsed = urlparse(str(url or ""))
    return (parsed.hostname or "").strip().lower() in set(["localhost", "127.0.0.1"])


def goto_start_url(page, url, retry_sleep_sec=1.0, goto_retries=1):
    timeout_ms = LOCAL_START_URL_TIMEOUT_MS if is_local_url(url) else REMOTE_START_URL_TIMEOUT_MS
    attempts = 0
    while True:
        try:
            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            return
        except Exception:
            if not is_local_url(url) or attempts >= int(goto_retries):
                raise
            attempts += 1
            if retry_sleep_sec:
                time.sleep(float(retry_sleep_sec))


def origin_from_url(url):
    parsed = urlparse(str(url or ""))
    if not parsed.scheme or not parsed.netloc:
        return ""
    return "{}://{}".format(parsed.scheme, parsed.netloc)


def _storage_state_roots():
    module_path = Path(__file__).resolve()
    return [Path.cwd(), module_path.parents[1], module_path.parents[2]]


def normalize_storage_state(path, roots=None):
    if not path:
        return None
    state_path = Path(path)
    if state_path.is_absolute():
        return str(state_path) if state_path.exists() else None
    for root in roots or _storage_state_roots():
        candidate = Path(root) / state_path
        if candidate.exists():
            return str(candidate)
    return None


def task_name(site, version, task_id):
    version_label = str(version or "unknown").replace(".", "_")
    return "browsergym/linkding_xvr_minimal.{}.{}.{}".format(site, version_label, int(task_id))


def compile_raw_task(row):
    metadata = normalize_task_metadata(row)
    site = (row.get("sites") or ["linkding"])[0]
    evaluator = row.get("eval") or {}
    state_check = evaluator.get("state_check") or {}
    must_include = (evaluator.get("reference_answers") or {}).get("must_include") or []
    spec_metadata = {"raw_task": row, "normalized_task": metadata}
    return ExecutableTaskSpec(
        task_id=metadata["task_id"],
        task_name=task_name(site, metadata["version"], metadata["task_id"]),
        site=site,
        version=metadata["version"],
        family=metadata["family"],
        intent=str(row.get("intent") or row.get("intent_template") or ""),
        start_url=metadata["start_url"],
        base_url=origin_from_url(metadata["start_url"]),
        require_login=bool(row.get("require_login", False)),
        require_reset=bool(row.get("require_reset", False)),
        storage_state=normalize_storage_state(row.get("storage_state")),
        evaluator=evaluator,
        state_check=state_check,
        must_include=[str(token) for token in must_include],
        metadata=spec_metadata,
    )


def compile_task_file(path, limit=0):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(rows, dict):
        rows = rows.get("rows") or rows.get("tasks") or []
    if limit:
        rows = rows[: int(limit)]
    return [compile_raw_task(row) for row in rows]


class AbstractBrowserTask(object):
    def __init__(self, seed):
        self.seed = seed
        self.random = random.Random(seed)
        self.viewport = {"width": 1280, "height": 720}
        self.slow_mo = 1000
        self.timeout = 5000
        self.locale = None
        self.timezone_id = None


class WebEvolveBrowserTask(AbstractBrowserTask):
    def __init__(self, seed, spec):
        super(WebEvolveBrowserTask, self).__init__(seed)
        self.spec = spec

    @classmethod
    def get_task_id(cls):
        return "linkding_xvr_minimal.custom"

    def setup(self, page, goto_retry_sleep_sec=1.0, goto_retries=1):
        try:
            goto_start_url(
                page,
                self.spec.start_url,
                retry_sleep_sec=goto_retry_sleep_sec,
                goto_retries=goto_retries,
            )
        except Exception as exc:
            raise ResetError("reset_start_url_failed: {}".format(exc))
        if self.spec.require_login:
            try:
                ensure_baseline_login(page, self.spec.base_url)
            except Exception as exc:
                raise ResetError("baseline_login_failed: {}".format(exc))
        metadata = dict((self.spec.metadata or {}).get("normalized_task") or {})
        info = {
            "task_id": self.spec.task_id,
            "task_name": self.spec.task_name,
            "start_url": self.spec.start_url,
            "base_url": self.spec.base_url,
            "site": self.spec.site,
            "version": self.spec.version,
            "family": self.spec.family,
            "source_task_id": metadata.get("source_task_id", 0),
            "focus20_source_task_id": metadata.get("focus20_source_task_id", 0),
            "source_family": metadata.get("source_family", ""),
            "variant": metadata.get("variant", ""),
            "drift_type": metadata.get("drift_type", ""),
            "raw_task": (self.spec.metadata or {}).get("raw_task", {}),
            "normalized_task": metadata,
        }
        return self.spec.intent, info

    def validate(self, page, chat_messages):
        state_ok, state_msg = state_check_passes(self.spec, page)
        if state_ok:
            return 1.0, True, state_msg, {"success": True, "reason": "state_check"}
        final_answer = latest_explicit_completion(chat_messages)
        if self.spec.must_include and final_answer:
            lower = final_answer.lower()
            if all(str(token).lower() in lower for token in self.spec.must_include):
                return 1.0, True, "must_include final answer passed", {
                    "success": True,
                    "reason": "must_include",
                }
            return 0.0, True, "final answer missing required tokens", {
                "success": False,
                "reason": "must_include_failed",
            }
        return 0.0, False, "", {"success": False, "reason": "incomplete"}

    def teardown(self):
        return None


def current_url(page):
    url = getattr(page, "url", "") or ""
    if url:
        return str(url)
    evaluate = getattr(page, "evaluate", None)
    if callable(evaluate):
        try:
            return str(evaluate("window.location.href") or "")
        except Exception:
            return ""
    return ""


def page_title(page):
    title = getattr(page, "title", None)
    if callable(title):
        try:
            return str(title() or "")
        except Exception:
            return ""
    return ""


def has_username_input(page):
    evaluate = getattr(page, "evaluate", None)
    if not callable(evaluate):
        return False
    try:
        return bool(
            evaluate(
                """
                (() => Boolean(
                  document.querySelector("input[name='username']")
                ))()
                """
            )
        )
    except Exception:
        return False


def has_password_input(page):
    evaluate = getattr(page, "evaluate", None)
    if not callable(evaluate):
        return False
    try:
        return bool(
            evaluate(
                """
                (() => Boolean(
                  document.querySelector("input[name='password']") ||
                  document.querySelector("input[type='password']")
                ))()
                """
            )
        )
    except Exception:
        return False


def has_login_form(page):
    return has_username_input(page) and has_password_input(page)


def has_login_reveal_control(page):
    evaluate = getattr(page, "evaluate", None)
    if not callable(evaluate):
        return False
    try:
        return bool(
            evaluate(
                """
                (() => {
                  if (document.querySelector("[data-hardv3-login-reveal]")) {
                    return true;
                  }
                  return Array.from(
                    document.querySelectorAll("button, [role='button'], a")
                  ).some((node) => ((node.innerText || node.textContent || "").trim()) === "Use local credentials");
                })()
                """
            )
        )
    except Exception:
        return False


def reveal_login_form_if_needed(page):
    if has_username_input(page):
        return
    if not has_login_reveal_control(page):
        return
    wait_for_selector = getattr(page, "wait_for_selector", None)
    for selector in (
        "button[data-hardv3-login-reveal]",
        "text=Use local credentials",
        "button:has-text('Use local credentials')",
    ):
        try:
            page.click(selector, timeout=2000)
        except Exception:
            continue
        if callable(wait_for_selector):
            try:
                wait_for_selector("input[name='username']", timeout=2000)
            except Exception:
                pass
        if has_username_input(page):
            return


def looks_authenticated(page):
    url = current_url(page)
    if url and not is_login_like(url):
        return True
    title = page_title(page).lower()
    if "bookmarks" in title and "login" not in title:
        return True
    body = page_corpus(page).lower()
    if "bookmarks" in body and not has_login_form(page):
        return True
    return False


def settle_login_navigation(page):
    wait_for_url = getattr(page, "wait_for_url", None)
    if callable(wait_for_url):
        try:
            wait_for_url("**/bookmarks*", timeout=5000)
        except Exception:
            pass
    wait_for_load_state = getattr(page, "wait_for_load_state", None)
    if callable(wait_for_load_state):
        try:
            wait_for_load_state("domcontentloaded", timeout=3000)
        except Exception:
            pass


def probe_authenticated_bookmarks(page, base_url):
    try:
        goto_start_url(page, "{}/bookmarks".format(base_url.rstrip("/")), retry_sleep_sec=0.0)
    except Exception:
        return looks_authenticated(page)
    settle_login_navigation(page)
    return looks_authenticated(page)


def wait_for_password_input(page):
    if has_password_input(page):
        return True
    wait_for_selector = getattr(page, "wait_for_selector", None)
    if callable(wait_for_selector):
        for selector in ("input[name='password']", "input[type='password']"):
            try:
                wait_for_selector(selector, timeout=2000)
                return True
            except Exception:
                continue
    return has_password_input(page)


def click_login_submit(page, base_url):
    try:
        page.click("button[type='submit'], input[type='submit']", timeout=3000)
    except Exception:
        settle_login_navigation(page)
        if not is_login_like(current_url(page)):
            return looks_authenticated(page) or probe_authenticated_bookmarks(page, base_url)
        raise
    settle_login_navigation(page)
    return False


def seed_session_via_http(page, base_url, username, password):
    if requests is None:
        return False
    context = getattr(page, "context", None)
    if context is None or not hasattr(context, "add_cookies"):
        return False
    login_url = "{}/login/".format(base_url.rstrip("/"))
    try:
        session = requests.Session()
        response = session.get(login_url, params={"next": "/bookmarks"}, timeout=10)
        response.raise_for_status()
        match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
        if not match:
            return False
        csrf = match.group(1)
        post = session.post(
            login_url,
            data={
                "username": username,
                "password": password,
                "csrfmiddlewaretoken": csrf,
                "next": "/bookmarks",
            },
            headers={"Referer": str(response.url)},
            allow_redirects=True,
            timeout=10,
        )
        post.raise_for_status()
    except Exception:
        return False
    session_id = session.cookies.get("sessionid")
    if not session_id:
        return False
    parsed = urlparse(base_url)
    domain = parsed.hostname or "127.0.0.1"
    secure = parsed.scheme == "https"
    cookies = []
    for name in ("csrftoken", "sessionid"):
        value = session.cookies.get(name)
        if not value:
            continue
        cookies.append(
            {
                "name": name,
                "value": value,
                "domain": domain,
                "path": "/",
                "httpOnly": name == "sessionid",
                "secure": secure,
                "sameSite": "Lax",
            }
        )
    if not cookies:
        return False
    try:
        context.add_cookies(cookies)
    except Exception:
        return False
    return True


def ensure_baseline_login(page, base_url):
    if not is_login_like(current_url(page)):
        return
    username = "baseline"
    password = "Baseline123!"
    if seed_session_via_http(page, base_url, username, password):
        if probe_authenticated_bookmarks(page, base_url):
            return
    reveal_login_form_if_needed(page)
    page.fill("input[name='username']", username, timeout=3000)
    if not wait_for_password_input(page):
        if click_login_submit(page, base_url):
            return
        if not is_login_like(current_url(page)):
            if looks_authenticated(page) or probe_authenticated_bookmarks(page, base_url):
                return
        if not wait_for_password_input(page):
            if probe_authenticated_bookmarks(page, base_url):
                return
    page.fill("input[name='password']", password, timeout=3000)
    if click_login_submit(page, base_url):
        return
    if looks_authenticated(page) or probe_authenticated_bookmarks(page, base_url):
        return
    if is_login_like(current_url(page)):
        page.press("input[name='password']", "Enter", timeout=2000)
        settle_login_navigation(page)
    if looks_authenticated(page) or probe_authenticated_bookmarks(page, base_url):
        return
    if is_login_like(current_url(page)):
        page.eval_on_selector("form", "f => f.submit()")
        settle_login_navigation(page)
    if looks_authenticated(page) or probe_authenticated_bookmarks(page, base_url):
        return
    if is_login_like(current_url(page)):
        raise RuntimeError("baseline login failed for {}; still on login page".format(base_url))


def state_check_passes(spec, page):
    if not spec.state_check:
        return False, ""
    page_url = str(getattr(page, "url", "") or "")
    body = page_corpus(page)
    page_url_lower = page_url.lower()
    body_lower = body.lower()
    for token in spec.state_check.get("url_must_include", []):
        if str(token).lower() not in page_url_lower:
            return False, "url missing required token: {}".format(token)
    for token in spec.state_check.get("url_must_not_include", []):
        if str(token).lower() in page_url_lower:
            return False, "url contains forbidden token: {}".format(token)
    for token in spec.state_check.get("body_must_include", []):
        if str(token).lower() not in body_lower:
            return False, "body missing required token: {}".format(token)
    for token in spec.state_check.get("body_must_not_include", []):
        if str(token).lower() in body_lower:
            return False, "body contains forbidden token: {}".format(token)
    return True, spec.state_check.get("success_summary", "state_check passed")


def page_corpus(page):
    evaluate = getattr(page, "evaluate", None)
    if not callable(evaluate):
        return ""
    try:
        return str(
            evaluate(
                """
(() => {
  const parts = [];
  if (document.body && document.body.innerText) {
    parts.push(document.body.innerText);
  }
  for (const node of Array.from(document.querySelectorAll("input, textarea, select"))) {
    for (const key of ["name", "id", "placeholder", "aria-label", "value"]) {
      const value = node.getAttribute(key) || node[key] || "";
      if (value) {
        parts.push(String(value));
      }
    }
  }
  return parts.join("\\n");
})()
"""
            )
            or ""
        )
    except Exception:
        return ""


def latest_explicit_completion(chat_messages):
    for message in reversed(list(chat_messages or [])):
        text = str(message.get("message") or message.get("content") or "").strip()
        if text:
            if message.get("role") != "assistant":
                return ""
            explicit = parse_explicit_completion(text)
            if explicit:
                return explicit
            action_candidate = text
            fenced = FENCED_CODE_RE.match(action_candidate)
            if fenced:
                action_candidate = fenced.group(1).strip()
            if ACTION_CALL_RE.match(action_candidate):
                continue
            if text.startswith("Hi! I am your UI assistant"):
                continue
            return text
    return ""


def parse_explicit_completion(text):
    stripped = str(text or "").strip()
    if not stripped:
        return ""
    fenced = FENCED_CODE_RE.match(stripped)
    if fenced:
        stripped = fenced.group(1).strip()
    send_msg = SEND_MSG_RE.match(stripped)
    if send_msg:
        payload = send_msg.group(1).strip()
        if (payload.startswith('"') and payload.endswith('"')) or (
            payload.startswith("'") and payload.endswith("'")
        ):
            payload = payload[1:-1]
        return payload.strip()
    match = EXPLICIT_FINAL_RE.match(stripped)
    if match:
        return match.group(1).strip()
    return ""
