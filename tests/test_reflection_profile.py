from linkding_xvr_minimal.rule_pipeline.reflection_profile import (
    build_capability_profile,
    group_transition_rows,
    label_capability,
    recommend_next_action,
)


def _row(task_id, drift_type, variant, source_task_id, left_success, right_success, transition, validity="valid_for_mining"):
    return {
        "task_id": task_id,
        "drift_type": drift_type,
        "variant": variant,
        "source_task_id": source_task_id,
        "focus20_source_task_id": source_task_id,
        "left_success": left_success,
        "right_success": right_success,
        "transition": transition,
        "validity": validity,
    }


def test_label_capability_uses_success_rate_and_invalid_rows():
    assert label_capability(8, 10) == "can_do"
    assert label_capability(4, 10) == "borderline"
    assert label_capability(1, 10) == "cannot_do"
    assert label_capability(0, 0, invalid_count=3) == "invalid_for_mining"


def test_group_transition_rows_by_drift_variant_and_source_task():
    rows = [
        _row(1, "runtime", "runtime", 16017, True, False, "lost"),
        _row(2, "runtime", "runtime", 16017, False, True, "saved"),
        _row(3, "access", "access", 9738, True, True, "both_success"),
    ]

    by_drift = group_transition_rows(rows, "drift_type")
    by_variant = group_transition_rows(rows, "variant")
    by_source = group_transition_rows(rows, "source_task_id")

    assert by_drift["runtime"]["tasks"] == 2
    assert by_drift["runtime"]["right_successes"] == 1
    assert by_drift["runtime"]["transition_counts"] == {"lost": 1, "saved": 1}
    assert by_variant["access"]["right_successes"] == 1
    assert by_source["16017"]["tasks"] == 2


def test_recommend_next_action_prefers_infra_repair_rules_or_hardening():
    assert recommend_next_action({"status": "invalid_for_mining"}) == "fix_infrastructure"
    assert recommend_next_action({"status": "borderline", "transition_counts": {"lost": 2}}) == "repair_rules"
    assert recommend_next_action({"status": "can_do", "right_success_rate": 0.95}) == "harden_environment"
    assert recommend_next_action({"status": "cannot_do"}) == "repair_rules"


def test_build_capability_profile_emits_group_summaries():
    artifact = {
        "schema_version": "webcoevo-xvr-transitions-v1",
        "comparison": {"left_label": "v2_4", "right_label": "v2_5"},
        "rows": [
            _row(1, "runtime", "runtime", 16017, True, False, "lost"),
            _row(2, "runtime", "runtime", 16017, False, True, "saved"),
            _row(3, "access", "access", 9738, True, True, "both_success"),
            _row(4, "access", "access", 9738, False, False, "both_fail", validity="invalid_for_mining"),
        ],
    }

    profile = build_capability_profile(artifact, group_bys=("drift_type", "source_task_id"))

    assert profile["schema_version"] == "webcoevo-xvr-capability-profile-v1"
    runtime = [
        row for row in profile["groups"]
        if row["group_by"] == "drift_type" and row["group_value"] == "runtime"
    ][0]
    assert runtime["tasks"] == 2
    assert runtime["right_success_rate"] == 0.5
    assert runtime["status"] == "borderline"
    assert runtime["recommended_next_action"] == "repair_rules"
