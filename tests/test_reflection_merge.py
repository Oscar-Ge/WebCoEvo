import json

import pytest

from linkding_xvr_minimal.rule_pipeline.reflection_merge import (
    apply_rule_proposals,
    assign_candidate_rule_ids,
    attach_support_metadata,
    load_base_rulebook_payload,
)
from linkding_xvr_minimal.rulebook import RuleSelectionContext, load_rulebook, select_rules


def _rule(rule_id, title, scope=None, support=None):
    return {
        "rule_id": rule_id,
        "title": title,
        "scope": scope or {"drift_types": ["runtime"]},
        "trigger": {
            "old_assumption": "A stale behavior is safe.",
            "observed_symptoms": ["Runtime drift is visible."],
        },
        "adaptation_strategy": ["Use the safer cross-version behavior."],
        "verification_check": ["The page state changed toward the goal."],
        "forbidden_actions": ["Do not repeat stale actions."],
        "support": support or {"support_count": 2, "supporting_task_ids": [101]},
        "confidence": 0.8,
    }


def test_assign_candidate_rule_ids_is_deterministic_without_mutating_inputs():
    rules = [_rule("old_b", "B"), _rule("old_a", "A")]

    assigned = assign_candidate_rule_ids(rules, prefix="xvr_test")

    assert [rule["rule_id"] for rule in assigned] == ["xvr_test_0001", "xvr_test_0002"]
    assert rules[0]["rule_id"] == "old_b"
    assert assigned[0]["source_rule_id"] == "old_b"


def test_attach_support_metadata_preserves_existing_and_proposal_support():
    rule = _rule("xvr26_0007", "Query rule", support={"support_count": 3})
    proposal = {
        "operation": "edit_rule",
        "target_rule_id": "xvr26_0007",
        "support": {"gap_ids": ["query_state_finalization_missed"], "supporting_task_ids": [501]},
    }

    out = attach_support_metadata(rule, proposal)

    assert out["support"]["support_count"] == 3
    assert out["support"]["gap_ids"] == ["query_state_finalization_missed"]
    assert out["support"]["supporting_task_ids"] == [501]
    assert out["support"]["source_rule_id"] == "xvr26_0007"


def test_apply_rule_proposals_merges_edits_drops_additions_and_caps_rules(tmp_path):
    base_payload = {
        "artifact_type": "cross_version_reflection_rules",
        "version": "v2_6",
        "rules": [
            _rule("xvr26_0001", "Old hidden click rule"),
            _rule("xvr26_0002", "Old loop rule", scope={"drift_types": ["content"]}),
        ],
    }
    proposals = [
        {
            "operation": "edit_rule",
            "target_rule_id": "xvr26_0001",
            "rule": _rule("", "Edited hidden click rule"),
            "support": {"gap_ids": ["hidden_click_repeated"]},
        },
        {"operation": "drop_rule", "target_rule_id": "xvr26_0002", "reason": "covered by edited rule"},
        {
            "operation": "add_rule",
            "rule": _rule("", "Added query finalization rule", scope={"drift_types": ["content"]}),
            "support": {"gap_ids": ["query_state_finalization_missed"]},
        },
    ]

    candidate = apply_rule_proposals(
        base_payload,
        proposals,
        version="candidate-v1",
        max_rules=8,
    )

    assert candidate["artifact_type"] == "cross_version_reflection_rules"
    assert candidate["version"] == "candidate-v1"
    assert candidate["rule_count"] == 2
    assert [rule["rule_id"] for rule in candidate["rules"]] == ["xvr_candidate_0001", "xvr_candidate_0002"]
    assert [rule["title"] for rule in candidate["rules"]] == [
        "Edited hidden click rule",
        "Added query finalization rule",
    ]
    assert candidate["rules"][0]["support"]["gap_ids"] == ["hidden_click_repeated"]

    output_file = tmp_path / "candidate.json"
    output_file.write_text(json.dumps(candidate), encoding="utf-8")
    rulebook = load_rulebook(output_file)
    selection = select_rules(
        rulebook,
        RuleSelectionContext(source_task_id=1, drift_type="runtime", variant="runtime"),
    )
    assert selection["selected_rule_ids"] == ["xvr_candidate_0001"]


def test_apply_rule_proposals_rejects_task_scopes_by_default_and_caps_count():
    base_payload = {"rules": [_rule("xvr26_0001", "Keep me")]}
    task_scoped = _rule("", "Task patch", scope={"task_ids": [123], "drift_types": ["runtime"]})

    with pytest.raises(ValueError, match="task_scope_not_allowed"):
        apply_rule_proposals(
            base_payload,
            [{"operation": "add_rule", "rule": task_scoped}],
            version="bad",
        )

    proposals = [
        {"operation": "add_rule", "rule": _rule("", "Added {}".format(index))}
        for index in range(5)
    ]
    candidate = apply_rule_proposals(base_payload, proposals, version="cap", max_rules=3)
    assert candidate["rule_count"] == 3


def test_load_base_rulebook_payload_accepts_dict_and_list_files(tmp_path):
    dict_file = tmp_path / "dict.json"
    list_file = tmp_path / "list.json"
    dict_file.write_text(json.dumps({"rules": [_rule("xvr26_0001", "One")]}), encoding="utf-8")
    list_file.write_text(json.dumps([_rule("xvr26_0002", "Two")]), encoding="utf-8")

    assert load_base_rulebook_payload(dict_file)["rules"][0]["rule_id"] == "xvr26_0001"
    assert load_base_rulebook_payload(list_file)["rules"][0]["rule_id"] == "xvr26_0002"
