import json
import os
import subprocess
import sys


def _run_script(script_name, args, cwd):
    return subprocess.run(
        [sys.executable, "scripts/{}".format(script_name)] + list(args),
        cwd=cwd,
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_build_episode_artifact_writes_public_episode_json(tmp_path):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    task_file = tmp_path / "tasks.json"
    task_file.write_text(
        json.dumps(
            [
                {
                    "task_id": 973001,
                    "intent": "Login and reach the home page.",
                    "intent_template": "login task",
                    "start_url": "http://localhost:9103/login",
                    "instantiation_dict": {
                        "version": "1.45.0",
                        "family": "AF20_ANCHOR_LOGIN_HOME",
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    trace_file = tmp_path / "trace.jsonl"
    eval_file = tmp_path / "eval.jsonl"
    _write_jsonl(
        trace_file,
        [
            {
                "task_id": 973001,
                "version": "1.45.0",
                "step": 0,
                "event": "task_step",
                "action": "goto('/login')",
                "model_output": "Observe login form.",
                "url": "http://localhost:9103/login",
                "error": "",
                "final_answer": "",
                "success_so_far": False,
                "retry_guidance_text": "",
            }
        ],
    )
    _write_jsonl(
        eval_file,
        [
            {
                "task_id": 973001,
                "version": "1.45.0",
                "success": True,
                "error": "",
                "final_answer": "done",
                "steps": 1,
                "elapsed_sec": 0.5,
            }
        ],
    )

    output_file = tmp_path / "episodes.json"
    result = _run_script(
        "build_episode_artifact.py",
        [
            "--trace",
            str(trace_file),
            "--eval",
            str(eval_file),
            "--task-file",
            str(task_file),
            "--source-version",
            "1.45.0",
            "--output-file",
            str(output_file),
        ],
        cwd=repo_root,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "webcoevo-rule-episodes-v1"
    assert payload["summary"]["num_episodes"] == 1
    assert payload["episodes"][0]["task_id"] == 973001


def test_build_recovery_artifact_groups_failed_then_success_attempts(tmp_path):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    episodes_file = tmp_path / "episodes.json"
    episodes_file.write_text(
        json.dumps(
            {
                "schema_version": "webcoevo-rule-episodes-v1",
                "summary": {"num_episodes": 2},
                "episodes": [
                    {
                        "episode_id": "episode.9738.1_45_0.trial.1",
                        "task_id": 9738,
                        "attempt_index": 0,
                        "goal": "Recover login redirect.",
                        "version": "1.45.0",
                        "success": False,
                        "error": "timeout",
                    },
                    {
                        "episode_id": "episode.9738.1_45_0.trial.2",
                        "task_id": 9738,
                        "attempt_index": 1,
                        "goal": "Recover login redirect.",
                        "version": "1.45.0",
                        "success": True,
                        "error": "",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    output_file = tmp_path / "recovery.json"
    result = _run_script(
        "build_recovery_artifact.py",
        [
            "--episodes-file",
            str(episodes_file),
            "--output-file",
            str(output_file),
        ],
        cwd=repo_root,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["summary"]["num_tasks"] == 1
    assert payload["summary"]["num_failed_then_success_tasks"] == 1
    assert payload["tasks"][0]["task_id"] == 9738
    assert len(payload["tasks"][0]["attempts"]) == 2


def test_build_expel_rules_from_recovery_supports_local_stub_mode(tmp_path):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    recovery_artifact = tmp_path / "recovery.json"
    recovery_artifact.write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": 9738,
                        "goal": "Recover login redirect.",
                        "version": "1.45.0",
                        "attempts": [
                            {
                                "attempt_index": 0,
                                "success": False,
                                "episode": {
                                    "episode_id": "episode.9738.fail.0",
                                    "task_id": 9738,
                                    "goal": "Recover login redirect.",
                                    "source_version": "1.45.0",
                                    "version": "1.45.0",
                                    "family": "AF20_LOGIN_REDIRECT",
                                    "success": False,
                                    "error": "timeout",
                                    "steps": [],
                                },
                            },
                            {
                                "attempt_index": 1,
                                "success": True,
                                "episode": {
                                    "episode_id": "episode.9738.success.1",
                                    "task_id": 9738,
                                    "goal": "Recover login redirect.",
                                    "source_version": "1.45.0",
                                    "version": "1.45.0",
                                    "family": "AF20_LOGIN_REDIRECT",
                                    "success": True,
                                    "error": "",
                                    "steps": [],
                                },
                            },
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    stub_critique = tmp_path / "stub_critique.txt"
    stub_critique.write_text(
        "ADD: Preserve task-specific login redirect parameters after authentication.\n",
        encoding="utf-8",
    )
    stub_insights = tmp_path / "stub_insights.json"
    stub_insights.write_text(
        json.dumps(
            [
                {
                    "summary": "Preserve redirect parameters.",
                    "when": "When login uses a next parameter.",
                    "query_terms": ["redirect", "next"],
                }
            ]
        ),
        encoding="utf-8",
    )

    output_file = tmp_path / "expel_rules.json"
    result = _run_script(
        "build_expel_rules_from_recovery.py",
        [
            "--recovery-artifact",
            str(recovery_artifact),
            "--output-file",
            str(output_file),
            "--stub-critique-file",
            str(stub_critique),
            "--stub-insights-file",
            str(stub_insights),
            "--include-insights",
        ],
        cwd=repo_root,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "webcoevo-expel-memory-v1"
    assert payload["summary"]["num_failed_then_success_tasks"] == 1
    assert payload["summary"]["num_rules"] == 1
    assert payload["rules"][0]["text"] == "Preserve task-specific login redirect parameters after authentication."
    assert payload["source_cases"][0]["task_id"] == 9738
    assert payload["rule_generation_records"][0]["operations"][0]["operation"] == "ADD"
