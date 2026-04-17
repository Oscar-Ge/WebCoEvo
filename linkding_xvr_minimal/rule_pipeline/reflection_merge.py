"""Merge structured reflection-rule proposals into candidate rulebooks."""

import copy
import json
from pathlib import Path

from linkding_xvr_minimal.rule_pipeline.reflection_proposals import (
    normalize_proposal,
    validate_proposal,
)


def load_base_rulebook_payload(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return {"artifact_type": "cross_version_reflection_rules", "rules": list(payload)}
    if isinstance(payload, dict):
        out = dict(payload)
        out["rules"] = list(out.get("rules") or [])
        return out
    return {"artifact_type": "cross_version_reflection_rules", "rules": []}


def apply_rule_proposals(base_payload, proposals, version, max_rules=8, allow_task_scope=False):
    base = dict(base_payload or {})
    rules = [copy.deepcopy(rule) for rule in list(base.get("rules") or []) if isinstance(rule, dict)]
    audit = []
    max_rules = max(0, int(max_rules or 0))

    for raw_proposal in list(proposals or []):
        proposal = normalize_proposal(raw_proposal)
        errors = validate_proposal(proposal, allow_task_scope=allow_task_scope)
        if errors:
            raise ValueError(",".join(errors))
        operation = proposal["operation"]
        target_rule_id = proposal["target_rule_id"]
        if operation == "keep_rule":
            audit.append(_audit_row(proposal, "kept"))
            continue
        if operation == "drop_rule":
            before = len(rules)
            rules = [rule for rule in rules if str(rule.get("rule_id") or "") != target_rule_id]
            audit.append(_audit_row(proposal, "dropped" if len(rules) < before else "missing_target"))
            continue
        if operation == "edit_rule":
            index = _find_rule_index(rules, target_rule_id)
            if index < 0:
                raise ValueError("missing_target_rule_id")
            old_rule = rules[index]
            new_rule = copy.deepcopy(proposal["rule"])
            if "support" not in new_rule and isinstance(old_rule.get("support"), dict):
                new_rule["support"] = copy.deepcopy(old_rule["support"])
            new_rule["source_rule_id"] = target_rule_id
            rules[index] = attach_support_metadata(new_rule, proposal)
            audit.append(_audit_row(proposal, "edited"))
            continue
        if operation == "add_rule":
            rules.append(attach_support_metadata(copy.deepcopy(proposal["rule"]), proposal))
            audit.append(_audit_row(proposal, "added"))

    if not allow_task_scope:
        for rule in rules:
            if _contains_deployable_task_scope(rule):
                raise ValueError("task_scope_not_allowed")

    capped_rules = rules[:max_rules] if max_rules else []
    assigned_rules = assign_candidate_rule_ids(capped_rules)
    return {
        "artifact_type": "cross_version_reflection_rules",
        "schema_version": "webcoevo-xvr-candidate-rulebook-v1",
        "version": str(version or ""),
        "base_version": str(base.get("version") or ""),
        "base_artifact_type": str(base.get("artifact_type") or ""),
        "rule_count": len(assigned_rules),
        "filters": {
            "max_rules": max_rules,
            "no_task_ids": not bool(allow_task_scope),
        },
        "merge_audit": audit,
        "rules": assigned_rules,
    }


def assign_candidate_rule_ids(rules, prefix="xvr_candidate"):
    out = []
    for index, rule in enumerate(list(rules or []), start=1):
        item = copy.deepcopy(rule)
        source_rule_id = str(item.get("source_rule_id") or item.get("rule_id") or "").strip()
        if source_rule_id:
            item["source_rule_id"] = source_rule_id
        item["rule_id"] = "{}_{:04d}".format(str(prefix or "xvr_candidate"), index)
        out.append(item)
    return out


def attach_support_metadata(rule, proposal):
    out = copy.deepcopy(rule or {})
    normalized = normalize_proposal(proposal)
    support = copy.deepcopy(out.get("support") or {})
    proposal_support = dict(normalized.get("support") or {})
    for key, value in proposal_support.items():
        if not _is_empty(value):
            support[key] = copy.deepcopy(value)
    source_rule_id = str(
        normalized.get("target_rule_id")
        or out.get("source_rule_id")
        or out.get("rule_id")
        or ""
    ).strip()
    if source_rule_id:
        support["source_rule_id"] = source_rule_id
        out["source_rule_id"] = source_rule_id
    if support:
        out["support"] = support
    return out


def _find_rule_index(rules, rule_id):
    target = str(rule_id or "").strip()
    for index, rule in enumerate(list(rules or [])):
        if str(rule.get("rule_id") or "").strip() == target:
            return index
    return -1


def _audit_row(proposal, status):
    return {
        "operation": str(proposal.get("operation") or ""),
        "target_rule_id": str(proposal.get("target_rule_id") or ""),
        "status": str(status or ""),
        "reason": str(proposal.get("reason") or ""),
    }


def _contains_deployable_task_scope(rule):
    if not isinstance(rule, dict):
        return False
    for key in [
        "task_id",
        "task_ids",
        "source_task_id",
        "source_task_ids",
        "focus20_source_task_id",
        "focus20_source_task_ids",
    ]:
        if not _is_empty(rule.get(key)):
            return True
    scope = rule.get("scope")
    if isinstance(scope, dict):
        return any(
            not _is_empty(scope.get(key))
            for key in [
                "task_id",
                "task_ids",
                "source_task_id",
                "source_task_ids",
                "focus20_source_task_id",
                "focus20_source_task_ids",
            ]
        )
    return False


def _is_empty(value):
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False
