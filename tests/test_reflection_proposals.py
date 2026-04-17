import json

from linkding_xvr_minimal.rule_pipeline.reflection_proposals import (
    extract_json_payload,
    normalize_proposal,
    parse_rule_proposals,
    validate_proposal,
)


def _rule(title="Finalize exact query evidence", scope=None):
    return {
        "title": title,
        "scope": scope or {"drift_types": ["runtime", "content"]},
        "trigger": {
            "old_assumption": "The page still needs another apply action.",
            "observed_symptoms": ["Exact query evidence is already visible."],
        },
        "adaptation_strategy": [
            "Finalize immediately when exact query evidence is already active."
        ],
        "verification_check": ["The URL or visible field contains the requested query."],
        "forbidden_actions": ["Do not click Apply after final evidence is visible."],
        "confidence": 0.9,
    }


def test_extract_json_payload_accepts_fenced_dict_and_plain_array():
    fenced = "draft\n```json\n{}\n```\nthanks".format(
        json.dumps({"schema_version": "webcoevo-xvr-rule-proposals-v1", "proposals": []})
    )
    assert extract_json_payload(fenced)["schema_version"] == "webcoevo-xvr-rule-proposals-v1"

    array_payload = [{"operation": "keep_rule", "target_rule_id": "xvr26_0001"}]
    assert extract_json_payload(json.dumps(array_payload)) == array_payload


def test_normalize_proposal_accepts_operation_aliases_and_preserves_support():
    proposal = normalize_proposal(
        {
            "op": "edit_rule",
            "rule_id": "xvr26_0007",
            "rule": _rule(),
            "support": {"gap_ids": ["query_state_finalization_missed"]},
        }
    )

    assert proposal["operation"] == "edit_rule"
    assert proposal["target_rule_id"] == "xvr26_0007"
    assert proposal["support"]["gap_ids"] == ["query_state_finalization_missed"]


def test_parse_rule_proposals_accepts_core_operations_from_llm_text():
    payload = {
        "schema_version": "webcoevo-xvr-rule-proposals-v1",
        "proposals": [
            {"operation": "add_rule", "rule": _rule("Add query rule")},
            {"operation": "edit_rule", "target_rule_id": "xvr26_0007", "rule": _rule("Edit query rule")},
            {"operation": "keep_rule", "target_rule_id": "xvr26_0001"},
            {"operation": "drop_rule", "target_rule_id": "xvr26_0008", "reason": "covered by edited rule"},
        ],
    }

    parsed = parse_rule_proposals("Here is the JSON:\n```json\n{}\n```".format(json.dumps(payload)))

    assert [proposal["operation"] for proposal in parsed["accepted"]] == [
        "add_rule",
        "edit_rule",
        "keep_rule",
        "drop_rule",
    ]
    assert parsed["rejected"] == []


def test_validate_proposal_rejects_unknown_ops_missing_fields_and_task_scopes():
    unknown = normalize_proposal({"operation": "rewrite_everything", "rule": _rule()})
    missing = normalize_proposal({"operation": "add_rule", "rule": {"title": "Too small"}})
    task_scoped = normalize_proposal(
        {"operation": "add_rule", "rule": _rule(scope={"task_ids": [101], "drift_types": ["runtime"]})}
    )

    assert "unknown_operation" in validate_proposal(unknown)
    assert "missing_rule_fields" in validate_proposal(missing)
    assert "task_scope_not_allowed" in validate_proposal(task_scoped)
    assert validate_proposal(task_scoped, allow_task_scope=True) == []


def test_parse_rule_proposals_returns_rejected_diagnostics():
    payload = {
        "proposals": [
            {"operation": "add_rule", "rule": _rule()},
            {"operation": "edit_rule", "target_rule_id": "", "rule": _rule()},
            {"operation": "drop_rule"},
        ]
    }

    parsed = parse_rule_proposals(json.dumps(payload))

    assert len(parsed["accepted"]) == 1
    assert len(parsed["rejected"]) == 2
    assert parsed["rejected"][0]["errors"] == ["missing_target_rule_id"]
