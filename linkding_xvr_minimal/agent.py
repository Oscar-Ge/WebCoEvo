from linkding_xvr_minimal.rulebook import RuleSelectionContext, load_rulebook, select_rules
from linkding_xvr_minimal.expel_rules import build_expel_prompt_payload


def build_cross_version_prompt_payload(rulebook, task_metadata, limit=8, fail_on_empty=False):
    if isinstance(rulebook, str):
        rulebook = load_rulebook(rulebook)
    context = RuleSelectionContext(
        source_task_id=task_metadata.get("source_task_id", 0),
        focus20_source_task_id=task_metadata.get("focus20_source_task_id", 0),
        drift_type=task_metadata.get("drift_type", ""),
        task_id=task_metadata.get("task_id", 0),
        variant=task_metadata.get("variant", ""),
    )
    selection = select_rules(
        rulebook,
        context,
        limit=limit,
        fail_on_empty=fail_on_empty,
    )
    extra_info = {
        "injected_rule_ids": [],
        "injected_rule_texts": [],
        "cross_version_reflection_rule_ids": selection["selected_rule_ids"],
        "cross_version_reflection_rule_texts": [
            str(rule.get("title") or rule.get("text") or "").strip()
            for rule in selection["selected_rules"]
            if str(rule.get("title") or rule.get("text") or "").strip()
        ],
        "cross_version_reflection_rules_path": selection["rulebook_path"],
        "cross_version_selection_context": selection["selection_context"],
        "cross_version_rule_miss_reasons": selection["miss_reasons"],
        "cross_version_warning": selection["warning"],
    }
    return {
        "prompt_block": selection["rendered_block"],
        "selection": selection,
        "extra_info": extra_info,
    }


class UITARSAgentLabArgs(object):
    def __init__(
        self,
        model="Qwen/Qwen3-VL-30B-A3B-Instruct",
        base_url="",
        api_key="",
        max_tokens=300,
        agent_mode="text_only",
        rulebook=None,
        rule_limit=8,
        fail_on_empty_xvr_rules=False,
    ):
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.agent_mode = agent_mode
        self.rulebook = rulebook
        self.rule_limit = rule_limit
        self.fail_on_empty_xvr_rules = fail_on_empty_xvr_rules

    def make_agent(self):
        return UITARSAgentLab(self)


class UITARSAgentLab(object):
    def __init__(self, args):
        self.args = args

    def build_rule_payload(self, task_metadata):
        if not self.args.rulebook:
            return {"prompt_block": "", "selection": {}, "extra_info": {}}
        return build_cross_version_prompt_payload(
            rulebook=self.args.rulebook,
            task_metadata=task_metadata,
            limit=self.args.rule_limit,
            fail_on_empty=self.args.fail_on_empty_xvr_rules,
        )
