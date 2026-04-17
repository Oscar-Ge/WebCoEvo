import json
import os
import subprocess
import sys

from linkding_xvr_minimal.rule_pipeline.reflection_compare import (
    build_transition_artifact,
    classify_invalid_reason,
    classify_transition,
    index_eval_rows,
    index_trace_rows,
    short_trace_excerpt,
)


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _task(task_id, source_task_id, drift_type):
    return {
        "task_id": task_id,
        "intent": "Complete task {}".format(task_id),
        "intent_template": "complete task",
        "start_url": "http://localhost:9103/tasks/{}".format(task_id),
        "instantiation_dict": {
            "version": "1.45.0",
            "family": "F{}".format(source_task_id),
            "source_task_id": source_task_id,
            "focus20_source_task_id": source_task_id,
            "drift_type": drift_type,
            "variant": drift_type,
        },
    }


def _eval(task_id, success, steps=2, error=""):
    return {
        "task_id": task_id,
        "version": "1.45.0",
        "success": success,
        "error": error,
        "steps": steps,
        "elapsed_sec": float(steps),
        "selected_rule_ids": ["xvr_old"],
    }


def _trace(task_id, count=2, action="click('#target')", error=""):
    return [
        {
            "task_id": task_id,
            "version": "1.45.0",
            "step": index,
            "event": "task_step",
            "action": action,
            "model_output": "observed step {}".format(index),
            "url": "http://localhost:9103/tasks/{}".format(task_id),
            "error": error,
            "final_answer": "",
            "success_so_far": False,
        }
        for index in range(count)
    ]


def test_classify_transition_covers_matched_outcomes():
    assert classify_transition(True, True) == "both_success"
    assert classify_transition(False, True) == "saved"
    assert classify_transition(True, False) == "lost"
    assert classify_transition(False, False) == "both_fail"


def test_index_helpers_and_trace_excerpt_are_deterministic():
    eval_rows = [_eval(2, True), _eval(1, False)]
    trace_rows = _trace(1, count=8) + _trace(2, count=1)

    assert sorted(index_eval_rows(eval_rows)) == [1, 2]
    assert sorted(index_trace_rows(trace_rows)) == [1, 2]
    excerpt = short_trace_excerpt(_trace(1, count=8), max_steps=6)

    assert len(excerpt) == 6
    assert excerpt[0]["step"] == 0
    assert excerpt[-1]["step"] == 5
    assert set(excerpt[0]) == set(
        [
            "step",
            "event",
            "action",
            "model_output",
            "url",
            "error",
            "final_answer",
            "success_so_far",
        ]
    )


def test_build_transition_artifact_reports_missing_duplicate_and_provenance_diagnostics():
    task_rows = [_task(501, 9738, "access"), _task(502, 16017, "runtime")]
    artifact = build_transition_artifact(
        task_rows=task_rows,
        left_eval_rows=[_eval(501, True), _eval(501, False, error="duplicate")],
        left_trace_rows=_trace(501),
        right_eval_rows=[_eval(501, True)],
        right_trace_rows=_trace(501),
        left_label="v2_4",
        right_label="v2_5",
        task_file="configs/focus20_hardv3_full.raw.json",
        provenance={
            "left_eval": "left_eval.jsonl",
            "right_eval": "right_eval.jsonl",
        },
    )

    row_502 = [row for row in artifact["rows"] if row["task_id"] == 502][0]
    assert row_502["transition"] == "incomplete_run"
    assert row_502["validity"] == "incomplete_run"
    assert row_502["invalid_reason"] == "missing_eval_row"
    assert artifact["summary"]["missing_counts"] == {"left_eval": 1, "right_eval": 1}
    assert artifact["summary"]["duplicate_counts"] == {"left_eval": 1, "right_eval": 0}
    assert artifact["provenance"]["left_eval"] == "left_eval.jsonl"


def test_build_transition_artifact_classifies_rows_and_preserves_metadata():
    task_rows = [
        _task(101, 9704, "surface"),
        _task(102, 9738, "access"),
        _task(103, 16017, "runtime"),
        _task(104, 16013, "structural"),
    ]
    left_eval_rows = [
        _eval(101, True),
        _eval(102, False),
        _eval(103, True),
        _eval(104, False),
    ]
    right_eval_rows = [
        _eval(101, True),
        _eval(102, True),
        _eval(103, False, steps=30, error="max_steps_no_success"),
        _eval(104, False),
    ]
    trace_rows = []
    for task_row in task_rows:
        trace_rows.extend(_trace(task_row["task_id"]))

    artifact = build_transition_artifact(
        task_rows=task_rows,
        left_eval_rows=left_eval_rows,
        left_trace_rows=trace_rows,
        right_eval_rows=right_eval_rows,
        right_trace_rows=trace_rows,
        left_label="v2_4",
        right_label="v2_5",
        task_file="configs/focus20_hardv3_full.raw.json",
    )

    assert artifact["schema_version"] == "webcoevo-xvr-transitions-v1"
    assert artifact["summary"]["transition_counts"] == {
        "both_fail": 1,
        "both_success": 1,
        "lost": 1,
        "saved": 1,
    }
    rows_by_task = {row["task_id"]: row for row in artifact["rows"]}
    assert rows_by_task[102]["transition"] == "saved"
    assert rows_by_task[103]["transition"] == "lost"
    assert rows_by_task[103]["source_task_id"] == 16017
    assert rows_by_task[103]["focus20_source_task_id"] == 16017
    assert rows_by_task[103]["family"] == "F16017"
    assert rows_by_task[103]["variant"] == "runtime"
    assert rows_by_task[103]["drift_type"] == "runtime"
    assert rows_by_task[103]["validity"] == "valid_for_mining"
    assert rows_by_task[103]["left_trace_excerpt"]
    assert rows_by_task[103]["right_trace_excerpt"]


def test_build_xvr_transition_artifact_cli_writes_public_json(tmp_path):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    task_file = tmp_path / "tasks.json"
    left_eval = tmp_path / "left_eval.jsonl"
    right_eval = tmp_path / "right_eval.jsonl"
    left_trace = tmp_path / "left_trace.jsonl"
    right_trace = tmp_path / "right_trace.jsonl"
    output_file = tmp_path / "transition_artifact.json"

    task_file.write_text(json.dumps([_task(201, 9738, "access")]), encoding="utf-8")
    _write_jsonl(left_eval, [_eval(201, False)])
    _write_jsonl(right_eval, [_eval(201, True)])
    _write_jsonl(left_trace, _trace(201))
    _write_jsonl(right_trace, _trace(201))

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_xvr_transition_artifact.py",
            "--task-file",
            str(task_file),
            "--left-label",
            "no_xvr",
            "--left-eval",
            str(left_eval),
            "--left-trace",
            str(left_trace),
            "--right-label",
            "v2_6",
            "--right-eval",
            str(right_eval),
            "--right-trace",
            str(right_trace),
            "--output-file",
            str(output_file),
        ],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "webcoevo-xvr-transitions-v1"
    assert payload["summary"]["transition_counts"] == {"saved": 1}
    assert payload["rows"][0]["transition"] == "saved"


def test_classify_invalid_reason_quarantines_infrastructure_and_parser_rows():
    assert (
        classify_invalid_reason(
            {"success": False, "error": "auth_session_failure: could not reveal login form"},
            _trace(301),
        )
        == "runtime_or_setup_failure"
    )
    assert (
        classify_invalid_reason(
            {"success": False, "error": "parser_failure: could not parse action"},
            _trace(302),
        )
        == "parser_or_action_format"
    )
    assert (
        classify_invalid_reason(
            {"success": False, "error": "max_steps_no_success"},
            [],
        )
        == "empty_trace"
    )


def test_build_transition_artifact_marks_invalid_rows_before_gap_mining():
    task_rows = [_task(401, 9738, "access")]
    left_eval_rows = [_eval(401, False, error="auth_session_failure during setup")]
    right_eval_rows = [_eval(401, True)]

    artifact = build_transition_artifact(
        task_rows=task_rows,
        left_eval_rows=left_eval_rows,
        left_trace_rows=[],
        right_eval_rows=right_eval_rows,
        right_trace_rows=_trace(401),
        left_label="no_xvr",
        right_label="v2_6",
    )

    row = artifact["rows"][0]
    assert row["validity"] == "invalid_for_mining"
    assert row["invalid_reason"] == "runtime_or_setup_failure"
    assert row["transition"] == "invalid_for_mining"
    assert artifact["summary"]["transition_counts"] == {"invalid_for_mining": 1}
