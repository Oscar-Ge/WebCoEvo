"""Parse and validate structured reflection-rule proposals."""

import json
import re


ALLOWED_OPERATIONS = set(["add_rule", "edit_rule", "keep_rule", "drop_rule"])
RULE_REQUIRED_FIELDS = [
    "title",
    "scope",
    "trigger",
    "adaptation_strategy",
    "verification_check",
    "forbidden_actions",
]
TASK_SCOPE_KEYS = set(
    [
        "task_id",
        "task_ids",
        "source_task_id",
        "source_task_ids",
        "focus20_source_task_id",
        "focus20_source_task_ids",
    ]
)


def extract_json_payload(text):
    if isinstance(text, (dict, list)):
        return text
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("empty proposal text")

    for fenced in re.findall(r"```(?:json)?\s*(.*?)```", raw, flags=re.IGNORECASE | re.DOTALL):
        try:
            return json.loads(fenced.strip())
        except ValueError:
            continue

    try:
        return json.loads(raw)
    except ValueError:
        pass

    decoder = json.JSONDecoder()
    starts = [index for index, char in enumerate(raw) if char in set(["{", "["])]
    for start in starts:
        try:
            payload, _ = decoder.raw_decode(raw[start:])
            return payload
        except ValueError:
            continue
    raise ValueError("no JSON object or array found in proposal text")


def normalize_proposal(raw):
    row = dict(raw or {})
    operation = str(row.get("operation") or row.get("op") or row.get("action") or "").strip()
    target_rule_id = str(
        row.get("target_rule_id")
        or row.get("target_id")
        or row.get("existing_rule_id")
        or row.get("rule_id")
        or ""
    ).strip()
    rule = row.get("rule")
    if rule is None:
        rule = row.get("proposed_rule")
    if isinstance(rule, dict):
        rule = dict(rule)
    else:
        rule = {}
    return {
        "operation": operation,
        "target_rule_id": target_rule_id,
        "rule": rule,
        "reason": str(row.get("reason") or row.get("rationale") or "").strip(),
        "support": _as_dict(row.get("support")),
        "raw": row,
    }


def validate_proposal(proposal, allow_task_scope=False):
    row = normalize_proposal(proposal)
    errors = []
    operation = row["operation"]
    if operation not in ALLOWED_OPERATIONS:
        errors.append("unknown_operation")
        return errors
    if operation in set(["edit_rule", "keep_rule", "drop_rule"]) and not row["target_rule_id"]:
        errors.append("missing_target_rule_id")
    if operation in set(["add_rule", "edit_rule"]):
        rule = dict(row.get("rule") or {})
        missing = [field for field in RULE_REQUIRED_FIELDS if _is_empty(rule.get(field))]
        if missing:
            errors.append("missing_rule_fields")
        if not allow_task_scope and _contains_task_scope(rule):
            errors.append("task_scope_not_allowed")
    return errors


def parse_rule_proposals(text, allow_task_scope=False):
    payload = extract_json_payload(text)
    raw_proposals = _proposal_rows(payload)
    accepted = []
    rejected = []
    for index, raw in enumerate(raw_proposals):
        proposal = normalize_proposal(raw)
        errors = validate_proposal(proposal, allow_task_scope=allow_task_scope)
        if errors:
            rejected.append({"index": index, "errors": errors, "proposal": proposal})
        else:
            accepted.append(proposal)
    return {
        "schema_version": "webcoevo-xvr-rule-proposals-v1",
        "accepted": accepted,
        "rejected": rejected,
        "raw_payload": payload,
    }


def _proposal_rows(payload):
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        rows = payload.get("proposals") or payload.get("items") or payload.get("rules") or []
        if isinstance(rows, dict):
            return [rows]
        return [row for row in list(rows or []) if isinstance(row, dict)]
    return []


def _contains_task_scope(rule):
    if not isinstance(rule, dict):
        return False
    for key in TASK_SCOPE_KEYS:
        if not _is_empty(rule.get(key)):
            return True
    scope = rule.get("scope")
    if isinstance(scope, dict):
        return any(not _is_empty(scope.get(key)) for key in TASK_SCOPE_KEYS)
    return False


def _as_dict(value):
    if isinstance(value, dict):
        return dict(value)
    return {}


def _is_empty(value):
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False
