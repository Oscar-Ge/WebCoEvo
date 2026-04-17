import json
import os
import subprocess
import sys

from linkding_xvr_minimal.rule_pipeline.reflection_delta import (
    build_delta_manifest,
    build_delta_task_file,
    select_delta_rows,
)


def _transition(task_id, transition, drift_type="runtime"):
    return {
        "task_id": task_id,
        "transition": transition,
        "validity": "valid_for_mining",
        "drift_type": drift_type,
        "source_task_id": 16000 + task_id,
    }


def _task(task_id, drift_type="runtime"):
    return {
        "task_id": task_id,
        "intent": "Complete task {}".format(task_id),
        "start_url": "http://localhost:9103/tasks/{}".format(task_id),
        "instantiation_dict": {
            "version": "1.45.0",
            "source_task_id": 16000 + task_id,
            "focus20_source_task_id": 16000 + task_id,
            "family": "F{}".format(task_id),
            "drift_type": drift_type,
            "variant": drift_type,
            "start_url": "http://localhost:9103/tasks/{}".format(task_id),
        },
    }


def test_select_delta_rows_buckets_saved_lost_success_and_failures():
    artifact = {
        "rows": [
            _transition(1, "saved"),
            _transition(2, "saved"),
            _transition(3, "lost"),
            _transition(4, "both_success"),
            _transition(5, "both_fail"),
            dict(_transition(6, "lost"), validity="invalid_for_mining"),
        ]
    }

    selection = select_delta_rows(artifact, max_per_bucket=1)

    assert selection["buckets"]["must_keep"] == [1]
    assert selection["buckets"]["must_recover"] == [3]
    assert selection["buckets"]["regression_rails"] == [4]
    assert selection["buckets"]["diagnostic_frontier"] == [5]
    assert selection["selected_task_ids"] == [1, 3, 4, 5]


def test_build_delta_task_file_returns_raw_rows_in_selected_order():
    task_rows = [_task(10), _task(11), _task(12)]

    rows = build_delta_task_file(task_rows, [12, 10])

    assert [row["task_id"] for row in rows] == [12, 10]
    assert rows[0]["intent"] == "Complete task 12"


def test_build_delta_manifest_records_counts_and_paths():
    selection = {
        "buckets": {"must_keep": [1], "must_recover": [2], "regression_rails": [], "diagnostic_frontier": [3]},
        "selected_task_ids": [1, 2, 3],
    }

    manifest = build_delta_manifest(selection, output_task_file="delta.raw.json", max_per_bucket=1)

    assert manifest["schema_version"] == "webcoevo-xvr-delta-slice-v1"
    assert manifest["output_task_file"] == "delta.raw.json"
    assert manifest["bucket_counts"] == {
        "diagnostic_frontier": 1,
        "must_keep": 1,
        "must_recover": 1,
        "regression_rails": 0,
    }


def test_build_reflection_delta_slice_cli_writes_tasks_and_manifest(tmp_path):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    transition_file = tmp_path / "transitions.json"
    task_file = tmp_path / "tasks.json"
    output_task_file = tmp_path / "delta.raw.json"
    manifest_file = tmp_path / "manifest.json"

    transition_file.write_text(
        json.dumps(
            {
                "rows": [
                    _transition(1, "saved"),
                    _transition(2, "lost"),
                    _transition(3, "both_success"),
                    _transition(4, "both_fail"),
                ]
            }
        ),
        encoding="utf-8",
    )
    task_file.write_text(json.dumps([_task(index) for index in range(1, 5)]), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_reflection_delta_slice.py",
            "--transition-artifact",
            str(transition_file),
            "--task-file",
            str(task_file),
            "--output-task-file",
            str(output_task_file),
            "--manifest-file",
            str(manifest_file),
            "--max-per-bucket",
            "1",
        ],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.returncode == 0, result.stderr
    rows = json.loads(output_task_file.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert [row["task_id"] for row in rows] == [1, 2, 3, 4]
    assert manifest["selected_task_ids"] == [1, 2, 3, 4]
    assert json.loads(result.stdout)["selected_count"] == 4
