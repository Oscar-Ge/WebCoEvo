import sys
import types


if "bgym" not in sys.modules:
    fake_bgym = types.ModuleType("bgym")

    class FakeAgent(object):
        pass

    class FakeHighLevelActionSet(object):
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def describe(self, with_long_description=False):
            return "click('bid'), fill('bid', 'value'), send_msg_to_user('message')"

        def to_python_code(self, action):
            return str(action)

    class FakeAgentInfo(object):
        def __init__(self, think="", chat_messages=None, stats=None, extra_info=None):
            self.think = think
            self.chat_messages = chat_messages or []
            self.stats = stats or {}
            self.extra_info = extra_info or {}

    fake_bgym.Agent = FakeAgent
    fake_bgym.HighLevelActionSet = FakeHighLevelActionSet
    fake_bgym.AgentInfo = FakeAgentInfo
    sys.modules["bgym"] = fake_bgym

if "agentlab.agents.agent_args" not in sys.modules:
    fake_agentlab = types.ModuleType("agentlab")
    fake_agents = types.ModuleType("agentlab.agents")
    fake_agent_args = types.ModuleType("agentlab.agents.agent_args")

    class FakeAgentArgs(object):
        pass

    fake_agent_args.AgentArgs = FakeAgentArgs
    sys.modules.setdefault("agentlab", fake_agentlab)
    sys.modules.setdefault("agentlab.agents", fake_agents)
    sys.modules["agentlab.agents.agent_args"] = fake_agent_args

if "openai" not in sys.modules:
    fake_openai = types.ModuleType("openai")

    class FakeOpenAI(object):
        def __init__(self, *args, **kwargs):
            pass

    fake_openai.OpenAI = FakeOpenAI
    sys.modules["openai"] = fake_openai

import linkding_xvr_minimal.agentlab_agent as agentlab_agent
from linkding_xvr_minimal.agentlab_agent import UITARSAgentLab, UITARSAgentLabArgs


class StrictActionSet(object):
    def describe(self, with_long_description=False):
        return "click('bid'), fill('bid', 'value'), send_msg_to_user('message')"

    def to_python_code(self, action):
        action = str(action)
        allowed_prefixes = ("click(", "fill(", "send_msg_to_user(", "report_infeasible(")
        if not action.startswith(allowed_prefixes):
            raise ValueError("invalid action")
        return action


def _stub_openai_class(responses, calls):
    class StubOpenAI(object):
        def __init__(self, *args, **kwargs):
            self._responses = responses
            self.chat = types.SimpleNamespace(
                completions=types.SimpleNamespace(create=self._create)
            )

        def _create(self, **kwargs):
            calls["count"] += 1
            if not self._responses:
                raise AssertionError("No more stubbed model responses available")
            text = self._responses.pop(0)
            return types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(
                        message=types.SimpleNamespace(content=text)
                    )
                ]
            )

    return StubOpenAI


def _make_agent(monkeypatch, responses):
    calls = {"count": 0}
    monkeypatch.setattr(
        agentlab_agent,
        "OpenAI",
        _stub_openai_class(list(responses), calls),
    )
    agent = UITARSAgentLab(
        UITARSAgentLabArgs(
            model="stub-model",
            base_url="http://stub.local/v1",
            api_key="stub-key",
        )
    )
    return agent, calls


def _make_strict_agent(monkeypatch, responses):
    agent, calls = _make_agent(monkeypatch, responses)
    agent.action_set = StrictActionSet()
    return agent, calls


def test_get_action_replays_bounded_login_multiaction_sequence(monkeypatch):
    agent, calls = _make_agent(
        monkeypatch,
        ["```python\nfill('39', 'baseline')\nfill('42', 'Baseline123!')\nclick('43')\n```"],
    )
    obs = {
        "goal": "Log in",
        "url": "http://localhost/login",
        "last_action": "",
        "last_action_error": "",
        "pruned_html": """
            <input bid="39" />
            <input bid="42" />
            <button bid="43">Log in</button>
        """,
    }

    action1, info1 = agent.get_action(obs)
    obs["last_action"] = action1
    action2, info2 = agent.get_action(obs)
    obs["last_action"] = action2
    action3, info3 = agent.get_action(obs)

    assert [action1, action2, action3] == [
        "fill('39', 'baseline')",
        "fill('42', 'Baseline123!')",
        "click('43')",
    ]
    assert calls["count"] == 1
    assert info1.extra_info["queued_actions_remaining"] == 2
    assert info2.extra_info["queued_actions_remaining"] == 1
    assert info3.extra_info["queued_actions_remaining"] == 0
    assert info1.extra_info["recovery_path"] == "bounded_multiaction_queue"
    assert "fill('39', 'baseline')" in info3.think
    assert "fill('39', 'baseline')" in info3.extra_info["raw_model_output"]


def test_get_action_clears_queued_multiaction_on_error(monkeypatch):
    agent, calls = _make_agent(
        monkeypatch,
        [
            "```python\nfill('39', 'baseline')\nfill('42', 'Baseline123!')\nclick('43')\n```",
            "```python\nclick('44')\n```",
        ],
    )
    obs = {
        "goal": "Log in",
        "url": "http://localhost/login",
        "last_action": "",
        "last_action_error": "",
        "pruned_html": """
            <input bid="39" />
            <input bid="42" />
            <button bid="43">Log in</button>
            <a bid="44">Retry</a>
        """,
    }

    action1, _ = agent.get_action(obs)
    obs["last_action"] = action1
    obs["last_action_error"] = "Element detached"
    action2, _ = agent.get_action(obs)

    assert action1 == "fill('39', 'baseline')"
    assert action2 == "click('44')"
    assert calls["count"] == 2


def test_get_action_drops_queued_multiaction_when_observation_changes(monkeypatch):
    agent, calls = _make_agent(
        monkeypatch,
        [
            "```python\nfill('39', 'baseline')\nfill('42', 'Baseline123!')\nclick('43')\n```",
            "```python\nclick('55')\n```",
        ],
    )
    obs = {
        "goal": "Log in",
        "url": "http://localhost/login",
        "last_action": "",
        "last_action_error": "",
        "pruned_html": """
            <input bid="39" />
            <input bid="42" />
            <button bid="43">Log in</button>
        """,
    }

    action1, info1 = agent.get_action(obs)
    obs["last_action"] = action1
    obs["url"] = "http://localhost/bookmarks"
    obs["pruned_html"] = """
        <div bid="55">Dashboard</div>
    """
    action2, info2 = agent.get_action(obs)

    assert action1 == "fill('39', 'baseline')"
    assert action2 == "click('55')"
    assert info1.extra_info["queued_actions_remaining"] == 2
    assert info2.extra_info["queued_actions_remaining"] == 0
    assert calls["count"] == 2


def test_get_action_recovers_single_action_from_prose_wrapped_code_block(monkeypatch):
    agent, calls = _make_strict_agent(
        monkeypatch,
        ["I will click the retry control.\n```python\nclick('44')\n```"],
    )
    obs = {
        "goal": "Open the login form",
        "url": "http://localhost/login",
        "last_action_error": "",
        "pruned_html": "<button bid=\"44\">Retry</button>",
    }

    action, info = agent.get_action(obs)

    assert action == "click('44')"
    assert calls["count"] == 1
    assert info.extra_info["recovery_path"] == "most_basic_single_action"


def test_get_action_recovers_bare_single_action(monkeypatch):
    agent, calls = _make_strict_agent(monkeypatch, ["click('44')"])
    obs = {
        "goal": "Open the login form",
        "url": "http://localhost/login",
        "last_action_error": "",
        "pruned_html": "<button bid=\"44\">Retry</button>",
    }

    action, info = agent.get_action(obs)

    assert action == "click('44')"
    assert calls["count"] == 1
    assert info.extra_info["recovery_path"] == "bare_single_action"


def test_get_action_retries_after_parse_failure(monkeypatch):
    agent, calls = _make_strict_agent(
        monkeypatch,
        [
            "I cannot decide yet.",
            "```python\nclick('44')\n```",
        ],
    )
    obs = {
        "goal": "Open the login form",
        "url": "http://localhost/login",
        "last_action_error": "",
        "pruned_html": "<button bid=\"44\">Retry</button>",
    }

    action, info = agent.get_action(obs)

    assert action == "click('44')"
    assert calls["count"] == 2
    assert info.extra_info["recovery_path"] == "most_basic_single_action"
    assert info.extra_info["parse_retries_used"] == 1
    assert any(
        "Reply with exactly one BrowserGym action" in str(message.get("content", ""))
        for message in info.chat_messages
        if isinstance(message, dict) and message.get("role") == "user"
    )
