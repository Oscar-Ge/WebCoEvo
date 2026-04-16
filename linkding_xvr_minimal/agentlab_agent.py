import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import bgym
from agentlab.agents.agent_args import AgentArgs
from openai import OpenAI

from linkding_xvr_minimal.agent import build_cross_version_prompt_payload, build_expel_prompt_payload
from linkding_xvr_minimal.expel_rules import load_expel_rules
from linkding_xvr_minimal.prompting import (
    build_hardv3_task_guidance,
    build_text_only_action_prompt,
    build_vl_action_prompt,
)
from linkding_xvr_minimal.rulebook import load_rulebook


CODE_BLOCK_RE = re.compile(r"```(?:[A-Za-z0-9_+-]+)?\s*\n?(.*?)```", re.DOTALL)
LOGIN_CONTEXT_RE = re.compile(r"\b(login|log in|sign in|username|password|credential)\b", re.I)
SEND_MSG_RE = re.compile(r'^send_msg_to_user\((.+)\)$')
ACTION_BID_RE = re.compile(r"^[a-z_]+\((?:['\"])([^'\"]+)(?:['\"])", re.IGNORECASE)


class ParseError(ValueError):
    pass


@dataclass
class UITARSAgentLabArgs(AgentArgs):
    agent_name: str = "MinimalUITARSAgentLab"
    model: str = "Qwen/Qwen3-VL-30B-A3B-Instruct"
    base_url: str = ""
    api_key: str = ""
    max_tokens: int = 300
    temperature: float = 0.0
    observation_char_limit: int = 2500
    agent_mode: str = "text_only"
    rulebook: object = None
    rulebook_path: str = ""
    expel_rule_file: str = ""
    expel_fidelity: str = "minimal"
    task_context_json: str = "[]"
    rule_limit: int = 8
    expel_rule_limit: int = 3
    max_parse_retries: int = 3
    fail_on_empty_xvr_rules: bool = False

    def make_agent(self):
        return UITARSAgentLab(self)

    def set_reproducibility_mode(self):
        self.temperature = 0.0


class UITARSAgentLab(bgym.Agent):
    action_set = bgym.HighLevelActionSet(
        ["chat", "infeas", "bid", "nav"],
        multiaction=False,
    )

    def __init__(self, args):
        self.args = args
        self.client = OpenAI(base_url=args.base_url, api_key=args.api_key)
        self.rulebook = args.rulebook or _load_rulebook_from_path(args.rulebook_path)
        self.expel_rulebook = _load_expel_rulebook_from_path(args.expel_rule_file)
        self.task_contexts = _load_task_contexts(args.task_context_json)
        self.last_extra_info = {}
        self.pending_actions = []
        self.pending_source_output = ""
        self.pending_fingerprint = None
        self.max_parse_retries = max(1, int(args.max_parse_retries))
        self.capture_frames = args.agent_mode == "vl_action_reflection"
        self.action_input_mode = "multimodal" if self.capture_frames else "text_only"
        self.reflection_input_mode = self.action_input_mode

    def get_action(self, obs):
        last_action_error = str(obs.get("last_action_error") or "").strip() if isinstance(obs, dict) else ""
        if last_action_error:
            self.pending_actions = []
            self.pending_source_output = ""
            self.pending_fingerprint = None

        observation_fingerprint = _observation_fingerprint(obs)
        if self.pending_actions and self.pending_fingerprint == observation_fingerprint:
            action = self.pending_actions.pop(0)
            agent_info = self._queued_action_info(action)
            if not self.pending_actions:
                self.pending_source_output = ""
                self.pending_fingerprint = None
            return action, agent_info
        if self.pending_actions:
            self.pending_actions = []
            self.pending_source_output = ""
            self.pending_fingerprint = None

        messages, extra_info = self._build_messages(obs)
        text = ""
        last_parse_error = None
        for attempt in range(self.max_parse_retries):
            response = self.client.chat.completions.create(
                model=self.args.model,
                messages=messages,
                temperature=self.args.temperature,
                max_tokens=self.args.max_tokens,
            )
            raw = response.choices[0].message.content
            text = _normalize_content(raw)
            messages.append({"role": "assistant", "content": text})
            try:
                action, queued_actions, recovery_path = _parse_action_response(text, self.action_set, obs)
                parse_retries_used = attempt
                break
            except ParseError as exc:
                last_parse_error = exc
                messages.append({"role": "user", "content": str(exc)})
        else:
            raise RuntimeError(
                "No Action or Final Answer parsed from model output "
                "(failure_code=parse_retry_exhausted, raw_output={!r})".format(text)
            ) from last_parse_error
        self.pending_actions = list(queued_actions)
        self.pending_source_output = text if self.pending_actions else ""
        self.pending_fingerprint = observation_fingerprint if self.pending_actions else None
        final_answer = _final_answer_from_action(action)
        extra_info.update(
            {
                "raw_model_output": text,
                "translated_action": action,
                "final_answer": final_answer,
                "model": self.args.model,
                "base_url": self.args.base_url,
                "agent_mode": self.args.agent_mode,
                "queued_actions_remaining": len(self.pending_actions),
                "recovery_path": recovery_path,
                "parse_retries_used": parse_retries_used,
                "max_parse_retries": self.max_parse_retries,
            }
        )
        self.last_extra_info = dict(extra_info)
        return (
            action,
            bgym.AgentInfo(
                think=text,
                chat_messages=messages,
                stats={"response_length": len(text)},
                extra_info=extra_info,
            ),
        )

    def _queued_action_info(self, action):
        final_answer = _final_answer_from_action(action)
        extra_info = dict(self.last_extra_info or {})
        extra_info.update(
            {
                "raw_model_output": self.pending_source_output,
                "translated_action": action,
                "final_answer": final_answer,
                "model": self.args.model,
                "base_url": self.args.base_url,
                "agent_mode": self.args.agent_mode,
                "queued_actions_remaining": len(self.pending_actions),
                "recovery_path": "bounded_multiaction_queue",
            }
        )
        return bgym.AgentInfo(
            think=self.pending_source_output,
            chat_messages=[],
            stats={"response_length": len(self.pending_source_output)},
            extra_info=extra_info,
        )

    def _build_messages(self, obs):
        task_metadata = _task_metadata_from_obs(obs, contexts=self.task_contexts)
        goal = str(obs.get("goal") or task_metadata.get("goal") or "")
        if self.args.agent_mode == "vl_action_reflection":
            user_message = build_vl_action_prompt(
                obs=obs,
                goal=goal,
                action_set=self.action_set,
                observation_char_limit=self.args.observation_char_limit,
            )
        else:
            user_message = build_text_only_action_prompt(
                obs=obs,
                goal=goal,
                action_set=self.action_set,
                observation_char_limit=self.args.observation_char_limit,
            )
        messages = [{"role": "system", "content": "You are a web assistant."}, user_message]
        extra_info = {
            "injected_rule_ids": [],
            "injected_rule_texts": [],
            "cross_version_reflection_rule_ids": [],
            "cross_version_reflection_rule_texts": [],
            "cross_version_reflection_rules_path": "",
            "cross_version_selection_context": {},
            "cross_version_rule_miss_reasons": {},
            "cross_version_warning": "",
            "expel_rulebook_path": "",
            "expel_selection_context": {},
            "expel_fidelity": self.args.expel_fidelity,
        }
        if self.expel_rulebook:
            payload = build_expel_prompt_payload(
                rulebook=self.expel_rulebook,
                task_metadata=task_metadata,
                limit=self.args.expel_rule_limit,
                fidelity=self.args.expel_fidelity,
            )
            if payload["prompt_block"]:
                messages.append({"role": "user", "content": payload["prompt_block"]})
            extra_info.update(payload["extra_info"])
        task_guidance = build_hardv3_task_guidance(obs=obs, task_metadata=task_metadata)
        if task_guidance:
            messages.append({"role": "user", "content": task_guidance})
        if self.rulebook:
            payload = build_cross_version_prompt_payload(
                rulebook=self.rulebook,
                task_metadata=task_metadata,
                limit=self.args.rule_limit,
                fail_on_empty=self.args.fail_on_empty_xvr_rules,
            )
            if payload["prompt_block"]:
                messages.append({"role": "user", "content": payload["prompt_block"]})
            _merge_xvr_extra(extra_info, payload["extra_info"])
        return messages, extra_info


def _task_metadata_from_obs(obs, contexts=None):
    task_info = obs.get("task_info") if isinstance(obs, dict) else {}
    task_info = task_info if isinstance(task_info, dict) else {}
    metadata = dict(task_info.get("normalized_task") or {})
    for key in [
        "task_id",
        "source_task_id",
        "focus20_source_task_id",
        "drift_type",
        "variant",
        "family",
        "version",
        "start_url",
    ]:
        if key not in metadata and key in task_info:
            metadata[key] = task_info[key]
    if not metadata.get("task_id"):
        metadata.update(_metadata_from_contexts(obs, contexts or []))
    metadata["goal"] = obs.get("goal") or task_info.get("goal") or ""
    return metadata


def _load_rulebook_from_path(path):
    if not path:
        return None
    return load_rulebook(Path(path))


def _load_expel_rulebook_from_path(path):
    if not path:
        return None
    return load_expel_rules(Path(path))


def _merge_xvr_extra(extra_info, xvr_extra):
    for key, value in (xvr_extra or {}).items():
        if key in set(["injected_rule_ids", "injected_rule_texts"]) and extra_info.get(key):
            continue
        extra_info[key] = value


def _load_task_contexts(payload):
    if not payload:
        return []
    try:
        contexts = json.loads(payload)
    except Exception:
        return []
    if not isinstance(contexts, list):
        return []
    return [context for context in contexts if isinstance(context, dict)]


def _metadata_from_contexts(obs, contexts):
    best_context = None
    best_score = 0
    goal = _normalize_goal(_obs_goal(obs))
    current_url = str(obs.get("url") or "") if isinstance(obs, dict) else ""
    for context in contexts:
        score = 0
        context_goals = [
            context.get("goal", ""),
            context.get("goal_prefixed", ""),
            (context.get("metadata") or {}).get("goal", ""),
        ]
        if goal and any(goal == _normalize_goal(candidate) for candidate in context_goals):
            score += 4
        if _same_origin(current_url, context.get("start_url", "")):
            score += 2
        if _same_normalized_path(current_url, context.get("start_url", "")):
            score += 1
        if score > best_score:
            best_score = score
            best_context = context
    if not best_context or best_score <= 0:
        return {}
    return dict(best_context.get("metadata") or {})


def _obs_goal(obs):
    if not isinstance(obs, dict):
        return ""
    if obs.get("goal"):
        return str(obs.get("goal"))
    goal_object = obs.get("goal_object")
    if isinstance(goal_object, (list, tuple)):
        parts = []
        for item in goal_object:
            if isinstance(item, dict) and item.get("text"):
                parts.append(str(item.get("text")))
        return "\n".join(parts)
    return ""


def _normalize_goal(value):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if text.lower().startswith("goal:"):
        text = text[5:].strip()
    return text


def _same_origin(left, right):
    left_url = urlparse(str(left or ""))
    right_url = urlparse(str(right or ""))
    return bool(left_url.scheme and right_url.scheme and left_url.netloc == right_url.netloc)


def _same_normalized_path(left, right):
    left_path = urlparse(str(left or "")).path.rstrip("/")
    right_path = urlparse(str(right or "")).path.rstrip("/")
    return bool(left_path and right_path and left_path == right_path)


def _extract_bid_from_action(action):
    match = ACTION_BID_RE.match(str(action or "").strip())
    if not match:
        return None
    return match.group(1)


def _extract_code_blocks(text):
    return [match.group(1) for match in CODE_BLOCK_RE.finditer(str(text or ""))]


def _extract_code_block_actions(text, action_set):
    blocks = _extract_code_blocks(text)
    if not blocks:
        return None
    block = blocks[0].strip()
    if not block:
        return None
    actions = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        action = parse_browsergym_action_output(stripped, action_set)
        if action is None:
            return None
        actions.append(action)
    return actions or None


def parse_browsergym_action_output(text, action_set):
    stripped = str(text or "").strip()
    if not stripped:
        return None
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    if len(lines) != 1:
        return None
    action = lines[0]
    if _is_terminal_action(action):
        return action
    try:
        action_set.to_python_code(action)
    except Exception:
        return None
    return action


def parse_most_basic_action_output(text, action_set):
    actions = _extract_code_block_actions(text, action_set)
    if not actions or len(actions) != 1:
        return None
    return actions[0]


def _looks_like_login_flow(obs):
    haystacks = [
        str(obs.get("goal") or ""),
        str(obs.get("url") or ""),
        str(obs.get("pruned_html") or ""),
        str(obs.get("axtree_txt") or ""),
    ]
    return any(LOGIN_CONTEXT_RE.search(item) for item in haystacks if item)


def _recover_bounded_multiaction(text, action_set, obs):
    actions = _extract_code_block_actions(text, action_set)
    if not actions or len(actions) not in set([2, 3]):
        return None
    if not _looks_like_login_flow(obs):
        return None
    if not all(action.startswith("fill(") for action in actions[:-1]):
        return None
    if not actions[-1].startswith("click("):
        return None
    fill_bids = [_extract_bid_from_action(action) for action in actions[:-1]]
    if any(bid is None for bid in fill_bids):
        return None
    if len(set(fill_bids)) != len(fill_bids):
        return None
    return actions


def _parse_action_response(text, action_set, obs):
    action = parse_most_basic_action_output(text, action_set)
    if action is not None:
        return action, [], "most_basic_single_action"
    action = parse_browsergym_action_output(text, action_set)
    if action is not None:
        return action, [], "bare_single_action"
    queued_actions = _recover_bounded_multiaction(text, action_set, obs)
    if queued_actions:
        return queued_actions[0], queued_actions[1:], "bounded_multiaction_queue"
    raise ParseError(
        "Reply with exactly one BrowserGym action inside triple backticks, for example:\n"
        "```\nclick('31')\n```"
    )


def _is_terminal_action(action):
    try:
        expr = ast.parse(action, mode="eval").body
    except SyntaxError:
        return False
    return (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Name)
        and expr.func.id in set(["send_msg_to_user", "report_infeasible"])
        and len(expr.args) == 1
        and not expr.keywords
    )


def _final_answer_from_action(action):
    match = SEND_MSG_RE.match(str(action or ""))
    if not match:
        return None
    try:
        return str(ast.literal_eval(match.group(1)))
    except Exception:
        return match.group(1)


def _observation_fingerprint(obs):
    url = str(obs.get("url") or "").strip()
    bid_matches = re.findall(r'bid=["\']([^"\']+)["\']', str(obs.get("pruned_html") or ""))
    if not bid_matches:
        bid_matches = re.findall(r"\[([^\]]+)\]", str(obs.get("axtree_txt") or ""))
    return url, tuple(sorted(set(bid_matches)))


def _normalize_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(content or "")
