import json
import os
import subprocess
import sys

from linkding_xvr_minimal.agent import build_cross_version_prompt_payload
from linkding_xvr_minimal.rulebook import load_rulebook
from linkding_xvr_minimal.tasks import normalize_task_metadata


def _task(task_id, source_task_id, drift_type):
    return {
        "task_id": task_id,
        "intent": "Complete hardv3 {} task {}".format(drift_type, task_id),
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
        "version": "1.45.0",
        "success": success,
        "steps": steps,
        "elapsed_sec": float(steps),
        "error": error,
        "selected_rule_ids": ["xvr_base"],
    }


def _trace(task_id, action="click('#target')", model_output="visible target", final_answer="", count=2):
    return [
        {
            "task_id": task_id,
            "version": "1.45.0",
            "step": index,
            "event": "task_step",
            "action": action,
            "model_output": model_output,
            "url": "http://localhost:9103/tasks/{}".format(task_id),
            "error": "",
            "final_answer": final_answer if index == count - 1 else "",
            "success_so_far": False,
        }
        for index in range(count)
    ]


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _run_json(repo_root, args):
    result = subprocess.run(
        [sys.executable] + args,
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_reflection_pipeline_stub_e2e_builds_verifies_and_selects_candidate(tmp_path):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    task_file = tmp_path / "tasks.json"
    left_eval = tmp_path / "left_eval.jsonl"
    right_eval = tmp_path / "right_eval.jsonl"
    left_trace = tmp_path / "left_trace.jsonl"
    right_trace = tmp_path / "right_trace.jsonl"
    transition_file = tmp_path / "transitions.json"
    gaps_file = tmp_path / "behavior_gaps.json"
    cases_file = tmp_path / "mining_cases.jsonl"
    base_rulebook = tmp_path / "base_rulebook.json"
    proposals_file = tmp_path / "stub_proposals.json"
    candidate_rulebook = tmp_path / "candidate_rulebook.json"
    delta_task_file = tmp_path / "delta.raw.json"
    delta_manifest = tmp_path / "delta_manifest.json"

    tasks = [
        _task(101, 16011, "runtime"),
        _task(102, 16012, "content"),
        _task(103, 16013, "surface"),
        _task(104, 16014, "access"),
    ]
    task_file.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
    _write_jsonl(
        left_eval,
        [
            _eval(101, False),
            _eval(102, True),
            _eval(103, True),
            _eval(104, False),
        ],
    )
    _write_jsonl(
        right_eval,
        [
            _eval(101, True),
            _eval(102, False, steps=6, error="max_steps_no_success"),
            _eval(103, True),
            _eval(104, False, steps=6, error="max_steps_no_success"),
        ],
    )
    left_trace_rows = []
    right_trace_rows = []
    for task in tasks:
        task_id = task["task_id"]
        left_trace_rows.extend(_trace(task_id, final_answer="done" if task_id in [102, 103] else ""))
    right_trace_rows.extend(_trace(101, final_answer="done"))
    right_trace_rows.extend(
        _trace(
            102,
            action="click('#apply')",
            model_output="query exact match visible but keep applying",
            count=3,
        )
    )
    right_trace_rows.extend(_trace(103, final_answer="done"))
    right_trace_rows.extend(_trace(104, action="noop", model_output="final evidence visible", count=3))
    _write_jsonl(left_trace, left_trace_rows)
    _write_jsonl(right_trace, right_trace_rows)

    base_rulebook.write_text(
        json.dumps(
            {
                "artifact_type": "cross_version_reflection_rules",
                "version": "base-empty",
                "rules": [],
            }
        ),
        encoding="utf-8",
    )
    proposals_file.write_text(
        json.dumps(
            {
                "schema_version": "webcoevo-xvr-rule-proposals-v1",
                "proposals": [
                    {
                        "operation": "add_rule",
                        "rule": {
                            "title": "Finalize visible evidence and avoid repeated recovery loops",
                            "scope": {
                                "drift_types": ["runtime", "content", "surface", "access"]
                            },
                            "trigger": {
                                "old_assumption": "More browser actions are needed after final evidence is visible.",
                                "observed_symptoms": [
                                    "Exact query, requested page, or final task evidence is visible."
                                ],
                            },
                            "adaptation_strategy": [
                                "When final evidence is visible, send the final answer instead of clicking Apply, noop, or repeating recovery."
                            ],
                            "verification_check": [
                                "The selected rule appears for each drift type in the delta slice."
                            ],
                            "forbidden_actions": [
                                "Do not keep applying, nooping, or clicking after final evidence is visible."
                            ],
                            "confidence": 0.9,
                        },
                        "support": {
                            "gap_ids": [
                                "query_state_finalization_missed",
                                "target_reached_but_no_final_answer",
                            ],
                            "supporting_task_ids": [102, 104],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    _run_json(
        repo_root,
        [
            "scripts/build_xvr_transition_artifact.py",
            "--task-file",
            str(task_file),
            "--left-label",
            "v2_4",
            "--left-eval",
            str(left_eval),
            "--left-trace",
            str(left_trace),
            "--right-label",
            "candidate",
            "--right-eval",
            str(right_eval),
            "--right-trace",
            str(right_trace),
            "--output-file",
            str(transition_file),
        ],
    )
    transition_payload = json.loads(transition_file.read_text(encoding="utf-8"))
    assert transition_payload["summary"]["transition_counts"] == {
        "both_fail": 1,
        "both_success": 1,
        "lost": 1,
        "saved": 1,
    }

    _run_json(
        repo_root,
        [
            "scripts/mine_reflection_gaps.py",
            "--transition-artifact",
            str(transition_file),
            "--output-file",
            str(gaps_file),
            "--cases-file",
            str(cases_file),
        ],
    )
    gaps_payload = json.loads(gaps_file.read_text(encoding="utf-8"))
    assert gaps_payload["summary"]["num_gaps"] > 0
    assert cases_file.read_text(encoding="utf-8").strip()

    _run_json(
        repo_root,
        [
            "scripts/build_reflection_rules.py",
            "--base-rulebook",
            str(base_rulebook),
            "--mining-cases",
            str(cases_file),
            "--output-file",
            str(candidate_rulebook),
            "--stub-proposals-file",
            str(proposals_file),
            "--candidate-version",
            "stub-e2e",
        ],
    )
    candidate_payload = json.loads(candidate_rulebook.read_text(encoding="utf-8"))
    assert candidate_payload["artifact_type"] == "cross_version_reflection_rules"
    assert candidate_payload["rule_count"] == 1

    verification = _run_json(
        repo_root,
        [
            "scripts/verify_reflection_rulebook.py",
            "--task-file",
            str(task_file),
            "--rulebook",
            str(candidate_rulebook),
            "--max-rules",
            "8",
            "--no-task-scopes",
            "--require-full-coverage",
            "--json",
        ],
    )
    assert verification["ok"] is True

    _run_json(
        repo_root,
        [
            "scripts/build_reflection_delta_slice.py",
            "--transition-artifact",
            str(transition_file),
            "--task-file",
            str(task_file),
            "--output-task-file",
            str(delta_task_file),
            "--manifest-file",
            str(delta_manifest),
            "--max-per-bucket",
            "1",
        ],
    )
    delta_rows = json.loads(delta_task_file.read_text(encoding="utf-8"))
    assert len(delta_rows) == 4

    rulebook = load_rulebook(candidate_rulebook)
    preflight_payload = build_cross_version_prompt_payload(
        rulebook=rulebook,
        task_metadata=normalize_task_metadata(delta_rows[0]),
        limit=8,
        fail_on_empty=True,
    )
    assert preflight_payload["selection"]["selected_rule_ids"] == ["xvr_candidate_0001"]
