import json
import random
from pathlib import Path


class RuleSelectionContext(object):
    def __init__(
        self,
        source_task_id=0,
        focus20_source_task_id=0,
        drift_type="",
        task_id=0,
        variant="",
    ):
        self.source_task_id = _to_int(source_task_id)
        self.focus20_source_task_id = _to_int(focus20_source_task_id)
        self.drift_type = str(drift_type or "").strip().lower()
        self.task_id = _to_int(task_id)
        self.variant = str(variant or "").strip().lower()

    def to_dict(self):
        return {
            "source_task_id": self.source_task_id,
            "focus20_source_task_id": self.focus20_source_task_id,
            "drift_type": self.drift_type,
            "task_id": self.task_id,
            "variant": self.variant,
        }


def load_rulebook(path):
    rulebook_path = Path(path)
    payload = json.loads(rulebook_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        raw_rules = payload.get("rules") or []
    else:
        raw_rules = payload
    rules = [normalize_rule(rule) for rule in raw_rules if isinstance(rule, dict)]
    return {"path": str(rulebook_path), "payload": payload, "rules": rules}


def normalize_rule(raw):
    rule = dict(raw)
    rule["scope"] = extract_scope(rule)
    return rule


def extract_scope(rule):
    source_task_ids = set()
    drift_types = set()
    scope = rule.get("scope")

    def add_source_values(values):
        for value in _as_list(values):
            value = _to_int(value)
            if value:
                source_task_ids.add(value)

    def add_drift_values(values):
        for value in _as_list(values):
            text = str(value or "").strip().lower()
            if text:
                drift_types.add(text)

    def add_mixed_values(values):
        for value in _as_list(values):
            text = str(value or "").strip()
            if not text:
                continue
            try:
                source_task_ids.add(int(text))
            except (TypeError, ValueError):
                drift_types.add(text.lower())

    if isinstance(scope, dict):
        add_source_values(scope.get("source_task_ids"))
        add_source_values(scope.get("source_task_id"))
        add_source_values(scope.get("focus20_source_task_ids"))
        add_source_values(scope.get("focus20_source_task_id"))
        add_drift_values(scope.get("drift_types"))
        add_drift_values(scope.get("drift_type"))
    elif isinstance(scope, (list, tuple, set)):
        add_mixed_values(scope)

    add_source_values(rule.get("source_task_ids"))
    add_source_values(rule.get("source_task_id"))
    add_source_values(rule.get("focus20_source_task_ids"))
    add_source_values(rule.get("focus20_source_task_id"))
    add_drift_values(rule.get("drift_types"))
    add_drift_values(rule.get("drift_type"))

    normalized = {}
    if source_task_ids:
        normalized["source_task_ids"] = sorted(source_task_ids)
    if drift_types:
        normalized["drift_types"] = sorted(drift_types)
    return normalized


def select_rules(rulebook, context, limit=8, fail_on_empty=False, shuffled=False):
    rules = [normalize_rule(rule) for rule in rulebook.get("rules", [])]
    limit = max(0, int(limit or 0))
    selected = []
    miss_reasons = {}
    for rule in rules:
        match, reason = _matches_context(rule, context)
        if match:
            selected.append(rule)
        else:
            rule_id = str(rule.get("rule_id") or "<missing-rule-id>")
            miss_reasons[rule_id] = reason

    if shuffled:
        rng = random.Random(0)
        rng.shuffle(selected)
    else:
        selected.sort(key=_sort_key)
    selected = selected[:limit]
    selected_ids = [str(rule.get("rule_id")) for rule in selected if rule.get("rule_id")]
    rendered = render_rules_block(selected)
    warning = ""
    if not selected:
        warning = (
            "No cross-version reflection rules selected for context "
            + json.dumps(context.to_dict(), sort_keys=True)
        )
        if fail_on_empty:
            raise ValueError(warning)

    return {
        "selected_rules": selected,
        "selected_rule_ids": selected_ids,
        "rendered_block": rendered,
        "rulebook_path": str(rulebook.get("path") or ""),
        "selection_context": context.to_dict(),
        "miss_reasons": miss_reasons,
        "warning": warning,
    }


def render_rules_block(rules):
    rows = list(rules or [])
    if not rows:
        return ""
    lines = [
        "## Cross-version adaptation rules",
        (
            "Use these scoped reflection rules only when live page evidence matches the trigger. "
            "They augment any general rulebook; page state and grounded bids still take priority."
        ),
    ]
    for index, rule in enumerate(rows, start=1):
        rule_id = str(rule.get("rule_id") or "").strip()
        title = str(rule.get("title") or "Untitled cross-version rule").strip()
        label = "[{}] ".format(rule_id) if rule_id else ""
        lines.append("{}. {}{}".format(index, label, title))
        scope = extract_scope(rule)
        scope_bits = []
        if scope.get("source_task_ids"):
            scope_bits.append("source_task_ids={}".format(scope["source_task_ids"]))
        if scope.get("drift_types"):
            scope_bits.append("drift_types={}".format(scope["drift_types"]))
        if scope_bits:
            lines.append("   - Scope: " + ", ".join(scope_bits))
        trigger = rule.get("trigger")
        if isinstance(trigger, dict):
            old_assumption = str(trigger.get("old_assumption") or "").strip()
            if old_assumption:
                lines.append("   - Trigger: " + old_assumption)
            symptoms = _limited_texts(trigger.get("observed_symptoms"), 2)
            if symptoms:
                lines.append("   - Symptoms: " + "; ".join(symptoms))
        for label_name, key, max_items in [
            ("Observe", "required_observations", 2),
            ("Adapt", "adaptation_strategy", 3),
            ("Avoid", "forbidden_actions", 2),
            ("Verify", "verification_check", 2),
        ]:
            values = _limited_texts(rule.get(key), max_items)
            if values:
                lines.append("   - {}: {}".format(label_name, "; ".join(values)))
    return "\n".join(lines)


def _matches_context(rule, context):
    scope = extract_scope(rule)
    source_ids = set(_int_values(scope.get("source_task_ids")))
    drift_types = set(str(value).strip().lower() for value in _as_list(scope.get("drift_types")) if str(value).strip())

    if not source_ids and not drift_types:
        return False, "empty_scope"
    if source_ids:
        context_ids = set(
            value
            for value in [context.source_task_id, context.focus20_source_task_id]
            if value
        )
        if not context_ids.intersection(source_ids):
            return False, "source_task_id_mismatch"
    if drift_types:
        drift = context.drift_type
        variant = context.variant
        if drift not in drift_types and variant not in drift_types:
            return False, "drift_type_mismatch"
    return True, ""


def _sort_key(rule):
    return (-_confidence(rule), -_support_count(rule), str(rule.get("rule_id") or ""))


def _confidence(rule):
    try:
        return float(rule.get("confidence") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _support_count(rule):
    support = rule.get("support")
    if not isinstance(support, dict):
        return 0
    try:
        return int(support.get("support_count") or 0)
    except (TypeError, ValueError):
        return 0


def _limited_texts(values, limit):
    out = []
    for value in _as_list(values):
        text = str(value or "").strip()
        if text:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _int_values(values):
    out = []
    for value in _as_list(values):
        value = _to_int(value)
        if value:
            out.append(value)
    return out


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
