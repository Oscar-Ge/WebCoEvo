"""Verify candidate reflection rulebooks before runtime consumption."""

import json
from pathlib import Path

from linkding_xvr_minimal.rule_pipeline.reflection_proposals import RULE_REQUIRED_FIELDS
from linkding_xvr_minimal.rulebook import RuleSelectionContext, load_rulebook, select_rules
from linkding_xvr_minimal.tasks import load_raw_tasks, normalize_task_metadata


def verify_rulebook_contract(payload, max_rules=8, no_task_scopes=True, required_gap_phrases=None):
    rules = _rules_from_payload(payload)
    errors = []
    warnings = []
    max_rules = int(max_rules or 0)
    if max_rules and len(rules) > max_rules:
        errors.append("too_many_rules")
    for index, rule in enumerate(rules):
        missing = [field for field in RULE_REQUIRED_FIELDS if _is_empty(rule.get(field))]
        if missing:
            errors.append("rule[{}].missing_required_fields:{}".format(index, ",".join(missing)))
        if _is_empty(rule.get("scope")):
            errors.append("rule[{}].empty_scope".format(index))
        if bool(no_task_scopes) and _contains_task_scope(rule):
            errors.append("rule[{}].task_scope_not_allowed".format(index))

    combined = json.dumps(rules, sort_keys=True).lower()
    for phrase in list(required_gap_phrases or []):
        text = str(phrase or "").strip().lower()
        if text and text not in combined:
            errors.append("missing_required_gap_phrase:{}".format(text))

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "rule_count": len(rules),
        "max_rules": max_rules,
        "no_task_scopes": bool(no_task_scopes),
    }


def verify_rule_coverage(task_file, rulebook_path, rule_limit=8):
    rows = load_raw_tasks(Path(task_file))
    rulebook = load_rulebook(Path(rulebook_path))
    covered = 0
    missing_task_ids = []
    out_rows = []
    for row in rows:
        metadata = normalize_task_metadata(row)
        context = RuleSelectionContext(
            source_task_id=metadata.get("source_task_id"),
            focus20_source_task_id=metadata.get("focus20_source_task_id"),
            drift_type=metadata.get("drift_type"),
            task_id=metadata.get("task_id"),
            variant=metadata.get("variant"),
        )
        selection = select_rules(rulebook, context, limit=rule_limit)
        selected_ids = list(selection.get("selected_rule_ids") or [])
        if selected_ids:
            covered += 1
        else:
            missing_task_ids.append(int(metadata.get("task_id") or 0))
        out_rows.append(
            {
                "task_id": int(metadata.get("task_id") or 0),
                "drift_type": str(metadata.get("drift_type") or ""),
                "variant": str(metadata.get("variant") or ""),
                "source_task_id": int(metadata.get("source_task_id") or 0),
                "selected_rule_ids": selected_ids,
                "warning": str(selection.get("warning") or ""),
            }
        )
    return {
        "task_count": len(rows),
        "covered": covered,
        "missing_task_ids": sorted(missing_task_ids),
        "rows": out_rows,
    }


def build_verification_report(
    payload,
    task_file=None,
    rulebook_path=None,
    max_rules=8,
    no_task_scopes=True,
    required_gap_phrases=None,
    rule_limit=8,
):
    contract = verify_rulebook_contract(
        payload,
        max_rules=max_rules,
        no_task_scopes=no_task_scopes,
        required_gap_phrases=required_gap_phrases,
    )
    coverage = {}
    if task_file and rulebook_path:
        coverage = verify_rule_coverage(task_file, rulebook_path, rule_limit=rule_limit)
    ok = bool(contract.get("ok")) and not bool(coverage.get("missing_task_ids"))
    if not coverage:
        ok = bool(contract.get("ok"))
    return {
        "schema_version": "webcoevo-xvr-rulebook-verification-v1",
        "ok": ok,
        "contract": contract,
        "coverage": coverage,
    }


def _rules_from_payload(payload):
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        return [row for row in list(payload.get("rules") or []) if isinstance(row, dict)]
    return []


def _contains_task_scope(rule):
    if not isinstance(rule, dict):
        return False
    task_keys = [
        "task_id",
        "task_ids",
        "source_task_id",
        "source_task_ids",
        "focus20_source_task_id",
        "focus20_source_task_ids",
    ]
    for key in task_keys:
        if not _is_empty(rule.get(key)):
            return True
    scope = rule.get("scope")
    if isinstance(scope, dict):
        return any(not _is_empty(scope.get(key)) for key in task_keys)
    return False


def _is_empty(value):
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False
