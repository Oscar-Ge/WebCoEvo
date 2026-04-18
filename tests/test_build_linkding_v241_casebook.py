import json
import os
import subprocess
import sys
from pathlib import Path


def _task(task_id, source_task_id, drift_type):
    return {
        "task_id": task_id,
        "intent": "Complete {} task {}".format(drift_type, task_id),
        "intent_template": "complete hardv3 task",
        "start_url": "http://localhost:9103/tasks/{}".format(task_id),
        "instantiation_dict": {
            "version": "1.45.0",
            "source_task_id": source_task_id,
            "focus20_source_task_id": source_task_id,
            "family": "F{}".format(source_task_id),
            "drift_type": drift_type,
            "variant": drift_type,
            "start_url": "http://localhost:9103/tasks/{}".format(task_id),
        },
    }


def _eval(task_id, success, steps=2, error=""):
    return {
        "task_id": task_id,
        "success": success,
        "steps": steps,
        "error": error,
    }


def _step(task_id, step, action="", model_output="", url="", error="", final_answer="", success_so_far=False):
    return {
        "task_id": task_id,
        "step": step,
        "event": "task_step",
        "action": action,
        "model_output": model_output,
        "url": url,
        "error": error,
        "final_answer": final_answer,
        "success_so_far": success_so_far,
    }


def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_build_linkding_v241_casebook_cli_writes_transition_gap_casebook_and_delta_outputs(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    focus_task_file = tmp_path / "focus20_hardv3_full.raw.json"
    taskbank_task_file = tmp_path / "taskbank36_hardv3_full.raw.json"
    manifest_file = tmp_path / "run_manifest.json"
    output_dir = tmp_path / "artifacts"

    focus_task_file.write_text(
        json.dumps(
            [
                _task(101, 16011, "runtime"),
                _task(102, 16012, "content"),
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    taskbank_task_file.write_text(
        json.dumps(
            [
                _task(201, 17011, "runtime"),
                _task(202, 17012, "content"),
            ],
            indent=2,
        ),
        encoding="utf-8",
    )

    focus_left_eval = tmp_path / "focus_left_eval.jsonl"
    focus_right_eval = tmp_path / "focus_right_eval.jsonl"
    focus_left_trace = tmp_path / "focus_left_trace.jsonl"
    focus_right_trace = tmp_path / "focus_right_trace.jsonl"
    taskbank_left_eval = tmp_path / "taskbank_left_eval.jsonl"
    taskbank_right_eval = tmp_path / "taskbank_right_eval.jsonl"
    taskbank_left_trace = tmp_path / "taskbank_left_trace.jsonl"
    taskbank_right_trace = tmp_path / "taskbank_right_trace.jsonl"

    _write_jsonl(focus_left_eval, [_eval(101, True), _eval(102, True)])
    _write_jsonl(focus_right_eval, [_eval(101, True), _eval(102, False, steps=6, error="max_steps_no_success")])
    _write_jsonl(
        focus_left_trace,
        [
            _step(101, 0, action="send_msg_to_user('done')", final_answer="done"),
            _step(102, 0, action="send_msg_to_user('done')", final_answer="done"),
        ],
    )
    _write_jsonl(
        focus_right_trace,
        [
            _step(101, 0, action="send_msg_to_user('done')", final_answer="done"),
            _step(102, 0, url="/bookmarks?query=amber", model_output="Exact query amber is visible"),
            _step(102, 1, action="click('Apply')", url="/bookmarks?query=amber"),
        ],
    )

    _write_jsonl(taskbank_left_eval, [_eval(201, True), _eval(202, False)])
    _write_jsonl(taskbank_right_eval, [_eval(201, True), _eval(202, False)])
    _write_jsonl(
        taskbank_left_trace,
        [
            _step(201, 0, action="send_msg_to_user('done')", final_answer="done"),
            _step(202, 0, action="noop"),
        ],
    )
    _write_jsonl(
        taskbank_right_trace,
        [
            _step(201, 0, action="send_msg_to_user('done')", final_answer="done"),
            _step(202, 0, action="noop"),
        ],
    )

    manifest_file.write_text(
        json.dumps(
            {
                "focus20": {
                    "first_modified": {
                        "v2_4": {
                            "run_dir": str(tmp_path / "focus20_first_modified_run"),
                            "eval_path": str(focus_left_eval),
                            "trace_path": str(focus_left_trace),
                            "eval_paths": [str(focus_left_eval)],
                            "trace_paths": [str(focus_left_trace)],
                        }
                    },
                    "hardv3": {
                        "v2_4": {
                            "run_dir": str(tmp_path / "focus20_hardv3_run"),
                            "eval_path": str(focus_right_eval),
                            "trace_path": str(focus_right_trace),
                            "eval_paths": [str(focus_right_eval)],
                            "trace_paths": [str(focus_right_trace)],
                        }
                    },
                },
                "taskbank36": {
                    "first_modified": {
                        "v2_4": {
                            "run_dir": str(tmp_path / "taskbank36_first_modified_run"),
                            "eval_path": str(taskbank_left_eval),
                            "trace_path": str(taskbank_left_trace),
                            "eval_paths": [str(taskbank_left_eval)],
                            "trace_paths": [str(taskbank_left_trace)],
                        }
                    },
                    "hardv3": {
                        "v2_4": {
                            "run_dir": str(tmp_path / "taskbank36_hardv3_run"),
                            "eval_path": str(taskbank_right_eval),
                            "trace_path": str(taskbank_right_trace),
                            "eval_paths": [str(taskbank_right_eval)],
                            "trace_paths": [str(taskbank_right_trace)],
                        }
                    },
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_linkding_v241_casebook.py",
            "--manifest-file",
            str(manifest_file),
            "--focus20-task-file",
            str(focus_task_file),
            "--taskbank-task-file",
            str(taskbank_task_file),
            "--output-dir",
            str(output_dir),
        ],
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.returncode == 0, result.stderr
    assert (output_dir / "focus20_transition_first_modified_to_hardv3.json").exists()
    assert (output_dir / "focus20_behavior_gaps.json").exists()
    assert (output_dir / "focus20_mining_cases.jsonl").exists()
    assert (output_dir / "focus20_delta_manifest.json").exists()
    assert (output_dir / "focus20_casebook.md").exists()
    assert (output_dir / "taskbank36_transition_first_modified_to_hardv3.json").exists()
    assert (output_dir / "taskbank36_casebook.md").exists()

    focus_casebook = (output_dir / "focus20_casebook.md").read_text(encoding="utf-8")
    assert "both_success" in focus_casebook
    assert "lost" in focus_casebook
    assert "old success -> new success" in focus_casebook
    assert "old success -> new fail" in focus_casebook

    summary = json.loads(result.stdout)
    assert summary["focus20"]["transition_counts"]["both_success"] == 1
    assert summary["focus20"]["transition_counts"]["lost"] == 1
    assert summary["taskbank36"]["transition_counts"]["both_fail"] == 1
