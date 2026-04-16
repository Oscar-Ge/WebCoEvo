from pathlib import Path

import pytest

from linkding_xvr_minimal.rulebook import (
    RuleSelectionContext,
    extract_scope,
    load_rulebook,
    render_rules_block,
    select_rules,
)


ROOT = Path(__file__).resolve().parents[1]


def _rule(rule_id, **kwargs):
    row = {"rule_id": rule_id, "title": "Rule " + rule_id, "confidence": 0.5}
    row.update(kwargs)
    return row


@pytest.mark.parametrize(
    "rule",
    [
        _rule("dict_scope", scope={"source_task_ids": [16005], "drift_types": ["access"]}),
        _rule("legacy_list_scope", scope=["access", "runtime"]),
        _rule("top_level_lists", source_task_ids=[16005], drift_types=["access"]),
        _rule("top_level_single", source_task_id=16005, drift_type="access"),
        _rule("top_level_focus20_single", focus20_source_task_id=16005, drift_type="access"),
        _rule("top_level_focus20_list", focus20_source_task_ids=[16005], drift_types=["access"]),
        _rule("dict_focus20_single", scope={"focus20_source_task_id": 16005, "drift_type": "access"}),
        _rule("dict_focus20_list", scope={"focus20_source_task_ids": [16005], "drift_types": ["access"]}),
    ],
)
def test_selector_supports_all_known_scope_schemas(rule):
    result = select_rules(
        {"path": "inline.json", "rules": [rule]},
        RuleSelectionContext(
            source_task_id=16005,
            focus20_source_task_id=16005,
            drift_type="access",
            task_id=1600501,
            variant="access",
        ),
        limit=8,
        fail_on_empty=True,
    )

    assert result["selected_rule_ids"] == [rule["rule_id"]]
    assert result["rulebook_path"] == "inline.json"
    assert result["selection_context"]["source_task_id"] == 16005
    assert result["selection_context"]["focus20_source_task_id"] == 16005


def test_focus20_scope_fallback_is_not_blocked_by_missing_source_task_id():
    scope = extract_scope({"scope": {"focus20_source_task_ids": [16005]}})

    assert scope["source_task_ids"] == [16005]


def test_empty_selection_reports_miss_reasons_and_can_fail_fast():
    rulebook = {
        "path": "inline.json",
        "rules": [_rule("wrong_drift", scope={"drift_types": ["runtime"]})],
    }
    context = RuleSelectionContext(
        source_task_id=16005,
        focus20_source_task_id=16005,
        drift_type="access",
        task_id=1600501,
        variant="access",
    )

    result = select_rules(rulebook, context, limit=8, fail_on_empty=False)
    assert result["selected_rule_ids"] == []
    assert result["miss_reasons"]
    assert result["warning"]

    with pytest.raises(ValueError, match="No cross-version reflection rules selected"):
        select_rules(rulebook, context, limit=8, fail_on_empty=True)


def test_rendered_block_uses_fixed_cross_version_heading():
    block = render_rules_block([
        _rule(
            "xvr_test",
            scope={"drift_types": ["access"]},
            trigger={"old_assumption": "old"},
            adaptation_strategy=["adapt"],
            verification_check=["verify"],
        )
    ])

    assert "## Cross-version adaptation rules" in block
    assert "xvr_test" in block
    assert "adapt" in block


def test_v26_rulebook_selects_for_every_hardv3_drift_type():
    rulebook = load_rulebook(ROOT / "rulebooks" / "v2_6.json")

    for drift_type in ["access", "surface", "content", "runtime", "process", "structural", "functional"]:
        result = select_rules(
            rulebook,
            RuleSelectionContext(
                source_task_id=16005,
                focus20_source_task_id=16005,
                drift_type=drift_type,
                task_id=1600501,
                variant=drift_type,
            ),
            limit=8,
            fail_on_empty=True,
        )
        assert result["selected_rule_ids"], drift_type
