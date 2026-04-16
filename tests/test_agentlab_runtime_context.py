import json
import sys
import types


if "bgym" not in sys.modules:
    fake_bgym = types.ModuleType("bgym")

    class FakeAgent(object):
        pass

    class FakeHighLevelActionSet(object):
        def __init__(self, *args, **kwargs):
            pass

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

from linkding_xvr_minimal.agentlab_agent import UITARSAgentLabArgs, _task_metadata_from_obs
from linkding_xvr_minimal.browser_task import compile_raw_task
from linkding_xvr_minimal.runner import build_task_context_json


def _raw_access_task():
    return {
        "sites": ["linkding"],
        "task_id": 1600501,
        "start_url": "http://127.0.0.1:9103/login?next=/bookmarks/new",
        "intent": "Authenticate and land on a prefilled add-bookmark form.",
        "instantiation_dict": {
            "version": "1.45.0",
            "family_id": "AF20_LOGIN_PREFILLED_BOOKMARK_FORM_WITH_TAGS",
            "focus20_source_task_id": 16005,
            "variant": "access",
            "drift_type": "access",
        },
    }


def test_task_metadata_can_be_recovered_from_goal_when_obs_has_no_task_info():
    spec = compile_raw_task(_raw_access_task())
    contexts = json.loads(build_task_context_json([spec]))

    metadata = _task_metadata_from_obs(
        {
            "goal": "Authenticate and land on a prefilled add-bookmark form.",
            "url": "http://127.0.0.1:9103/login/?next=/bookmarks/new",
        },
        contexts=contexts,
    )

    assert metadata["task_id"] == 1600501
    assert metadata["source_task_id"] == 16005
    assert metadata["drift_type"] == "access"


def test_agentlab_args_keep_rulebook_and_context_as_scalar_fields():
    args = UITARSAgentLabArgs(
        rulebook_path="rulebooks/v2_6.json",
        expel_rule_file="expel.json",
        task_context_json='[{"goal": "g", "metadata": {"task_id": 1}}]',
    )

    assert args.rulebook is None
    assert isinstance(args.rulebook_path, str)
    assert isinstance(args.expel_rule_file, str)
    assert isinstance(args.task_context_json, str)
    assert not any(isinstance(value, (dict, list)) for value in vars(args).values())
