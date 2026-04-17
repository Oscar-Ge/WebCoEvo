import json

from linkding_xvr_minimal.rule_pipeline.reflection_cases import (
    build_diagnosis,
    build_mining_case,
    build_mining_cases,
    write_jsonl,
)


def _row(task_id, transition="lost"):
    return {
        "task_id": task_id,
        "source_task_id": 16017,
        "focus20_source_task_id": 16017,
        "family": "F16017_QUERY",
        "variant": "runtime",
        "drift_type": "runtime",
        "intent": "Filter bookmarks by query amber.",
        "transition": transition,
        "left_label": "v2_4",
        "right_label": "v2_5",
        "left_success": True,
        "right_success": False,
        "left_error": "",
        "right_error": "max_steps_no_success",
        "left_trace_excerpt": [{"step": 0, "action": "send_msg_to_user('done')"}],
        "right_trace_excerpt": [
            {"step": index, "action": "click('Apply')", "url": "/bookmarks?query=amber"}
            for index in range(10)
        ],
    }


def test_build_diagnosis_returns_gap_specific_constraints():
    diagnosis = build_diagnosis(_row(1), "query_state_finalization_missed")

    assert "query" in diagnosis["observed_gap"].lower()
    assert "final" in diagnosis["must_preserve"].lower()
    assert "apply" in diagnosis["must_avoid"].lower()


def test_build_mining_case_is_compact_and_structured():
    case = build_mining_case(_row(2), "query_state_finalization_missed", "v2_4", "v2_5")

    assert case["case_id"] == "gap.query_state_finalization_missed.2"
    assert case["gap_id"] == "query_state_finalization_missed"
    assert case["task_metadata"]["source_task_id"] == 16017
    assert case["transition"] == "lost"
    assert case["left_result"]["label"] == "v2_4"
    assert case["right_result"]["label"] == "v2_5"
    assert len(case["right_result"]["trace_excerpt"]) == 6
    assert "diagnosis" in case
    assert "/home/" not in json.dumps(case)


def test_build_mining_cases_selects_gap_support_rows_and_writes_jsonl(tmp_path):
    artifact = {
        "comparison": {"left_label": "v2_4", "right_label": "v2_5"},
        "rows": [_row(3), _row(4, transition="saved")],
    }
    gaps = {
        "gaps": [
            {
                "gap_id": "query_state_finalization_missed",
                "priority": "high",
                "supporting_task_ids": [3, 4],
            }
        ]
    }

    cases = build_mining_cases(artifact, gaps, max_cases_per_gap=1)
    output_path = tmp_path / "cases.jsonl"
    write_jsonl(output_path, cases)
    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]

    assert len(cases) == 1
    assert rows[0]["case_id"] == "gap.query_state_finalization_missed.3"
