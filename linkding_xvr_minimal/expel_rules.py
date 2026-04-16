import json
from pathlib import Path


def load_expel_rules(path):
    rule_path = Path(path)
    payload = json.loads(rule_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        rows = payload.get("rules") or payload.get("rulebook") or payload.get("items") or []
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []
    return {
        "path": str(rule_path),
        "payload": payload,
        "schema_version": payload.get("schema_version", "") if isinstance(payload, dict) else "",
        "rules": [normalize_expel_rule(row) for row in rows if isinstance(row, dict)],
    }


def normalize_expel_rule(rule):
    out = dict(rule)
    raw_scope = out.get("scope")
    rule_id = (
        out.get("rule_id")
        or out.get("id")
        or out.get("rule_uuid")
        or out.get("memory_id")
        or out.get("episode_id")
        or ""
    )
    text = (
        out.get("text")
        or out.get("rule")
        or out.get("summary")
        or out.get("instruction")
        or out.get("title")
        or ""
    )
    out["rule_id"] = str(rule_id or "").strip()
    out["text"] = str(text or "").strip()
    out["scope"] = _normalized_scope(out)
    out["scope_kind"] = str(raw_scope or out.get("scope_kind") or "").strip().lower()
    out["scope_id"] = str(out.get("scope_id") or "").strip()
    return out


def select_expel_rules(rulebook, task_metadata, limit=3, fidelity="minimal"):
    rules = [
        normalize_expel_rule(rule)
        for rule in rulebook.get("rules", [])
        if isinstance(rule, dict)
        and str(
            rule.get("text")
            or rule.get("rule")
            or rule.get("summary")
            or rule.get("instruction")
            or rule.get("title")
            or ""
        ).strip()
    ]
    limit = max(0, int(limit or 0))
    context = _selection_context(task_metadata)
    fidelity = str(fidelity or "minimal")
    if fidelity in set(["official_eval", "official_full"]):
        selected = sorted(rules, key=_official_rule_sort_key)
    elif limit <= 0:
        selected = []
    else:
        selected = sorted(
            rules,
            key=lambda rule: (
                _scope_rank(rule, context),
                -_score(rule),
                -_float(rule.get("confidence")),
                -_support_count(rule),
                str(rule.get("rule_id") or ""),
            ),
        )[:limit]
    selected_ids = [str(rule.get("rule_id")) for rule in selected if rule.get("rule_id")]
    return {
        "selected_rules": selected,
        "selected_rule_ids": selected_ids,
        "rendered_block": render_expel_rules_block(selected),
        "rulebook_path": str(rulebook.get("path") or ""),
        "selection_context": context,
        "fidelity": fidelity,
    }


def render_expel_rules_block(rules):
    rows = [normalize_expel_rule(rule) for rule in list(rules or []) if isinstance(rule, dict)]
    rows = [rule for rule in rows if rule.get("text")]
    if not rows:
        return ""
    lines = [
        "## Task experience rules",
        "Use these ExpeL-style rules as soft guidance distilled from past trajectories.",
    ]
    for idx, rule in enumerate(rows, start=1):
        rule_id = str(rule.get("rule_id") or "expel_rule_{}".format(idx)).strip()
        text = str(rule.get("text") or "").strip()
        lines.append("{}. [{}] {}".format(idx, rule_id, text))
    return "\n".join(lines)


def build_expel_prompt_payload(rulebook, task_metadata, limit=3, fidelity="minimal"):
    if isinstance(rulebook, str):
        rulebook = load_expel_rules(rulebook)
    selection = select_expel_rules(rulebook, task_metadata, limit=limit, fidelity=fidelity)
    return {
        "prompt_block": selection["rendered_block"],
        "selection": selection,
        "extra_info": {
            "injected_rule_ids": selection["selected_rule_ids"],
            "injected_rule_texts": [
                str(rule.get("text") or "").strip()
                for rule in selection["selected_rules"]
                if str(rule.get("text") or "").strip()
            ],
            "cross_version_reflection_rule_ids": [],
            "cross_version_reflection_rule_texts": [],
            "cross_version_reflection_rules_path": "",
            "cross_version_selection_context": {},
            "cross_version_rule_miss_reasons": {},
            "cross_version_warning": "",
            "expel_rulebook_path": selection["rulebook_path"],
            "expel_selection_context": selection["selection_context"],
            "expel_fidelity": selection["fidelity"],
        },
    }


def _selection_context(task_metadata):
    return {
        "source_task_id": _int(task_metadata.get("source_task_id")),
        "focus20_source_task_id": _int(task_metadata.get("focus20_source_task_id")),
        "drift_type": str(task_metadata.get("drift_type") or "").strip().lower(),
        "task_id": _int(task_metadata.get("task_id")),
        "variant": str(task_metadata.get("variant") or "").strip().lower(),
        "family": str(task_metadata.get("family") or "").strip(),
    }


def _scope_rank(rule, context):
    if str(rule.get("scope_kind") or "").strip().lower() == "family":
        family = str(context.get("family") or "").strip()
        if family and family == str(rule.get("scope_id") or "").strip():
            return 0
    if str(rule.get("scope_kind") or "").strip().lower() == "global":
        return 2
    scope = _normalized_scope(rule)
    if _scope_matches(scope, context):
        # Prefer source-specific matches over drift-only matches.
        return 0 if scope.get("source_task_ids") else 1
    if not scope:
        return 2
    return 3


def _scope_matches(scope, context):
    if not scope:
        return False
    source_ids = set(scope.get("source_task_ids") or [])
    drift_types = set(scope.get("drift_types") or [])
    source_task_id = int(context.get("source_task_id") or 0)
    focus20_source_task_id = int(context.get("focus20_source_task_id") or 0)
    drift_type = str(context.get("drift_type") or "").strip().lower()
    variant = str(context.get("variant") or "").strip().lower()
    if source_ids and source_task_id not in source_ids and focus20_source_task_id not in source_ids:
        return False
    if drift_types and drift_type not in drift_types and variant not in drift_types:
        return False
    return True


def _normalized_scope(rule):
    source_ids = set()
    drift_types = set()
    scope = rule.get("scope")
    if isinstance(scope, dict):
        source_ids.update(_int_values(scope.get("source_task_ids")))
        source_ids.update(_int_values([scope.get("source_task_id")]))
        source_ids.update(_int_values(scope.get("focus20_source_task_ids")))
        source_ids.update(_int_values([scope.get("focus20_source_task_id")]))
        drift_types.update(_str_values(scope.get("drift_types")))
        drift_types.update(_str_values([scope.get("drift_type")]))
    elif isinstance(scope, (list, tuple, set)):
        for item in scope:
            text = str(item or "").strip()
            if not text:
                continue
            try:
                source_ids.add(int(text))
            except Exception:
                drift_types.add(text.lower())
    source_ids.update(_int_values(rule.get("source_task_ids")))
    source_ids.update(_int_values([rule.get("source_task_id")]))
    source_ids.update(_int_values(rule.get("focus20_source_task_ids")))
    source_ids.update(_int_values([rule.get("focus20_source_task_id")]))
    drift_types.update(_str_values(rule.get("drift_types")))
    drift_types.update(_str_values([rule.get("drift_type")]))
    out = {}
    if source_ids:
        out["source_task_ids"] = sorted(source_ids)
    if drift_types:
        out["drift_types"] = sorted(drift_types)
    return out


def _int_values(values):
    out = []
    if isinstance(values, (str, int)):
        values = [values]
    for value in values or []:
        try:
            out.append(int(value))
        except Exception:
            continue
    return out


def _str_values(values):
    if isinstance(values, str):
        values = [values]
    return [str(value).strip().lower() for value in values or [] if str(value).strip()]


def _support_count(rule):
    provenance = rule.get("provenance_episode_ids")
    if isinstance(provenance, list) and provenance:
        return len(provenance)
    support = rule.get("support")
    if isinstance(support, dict):
        return _int(support.get("support_count") or support.get("count"))
    return _int(rule.get("support_count") or rule.get("count"))


def _score(rule):
    return _int(rule.get("score"))


def _official_rule_sort_key(rule):
    return (-_score(rule), str(rule.get("rule_id") or ""))


def _int(value):
    try:
        return int(value or 0)
    except Exception:
        return 0


def _float(value):
    try:
        return float(value or 0.0)
    except Exception:
        return 0.0
