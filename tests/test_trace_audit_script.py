import json
import os
import subprocess
import sys


ROOT = os.path.dirname(os.path.dirname(__file__))


def test_trace_audit_requires_cross_version_rules(tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_text(
        json.dumps(
            {
                "task_id": 1,
                "event": "task_step",
                "cross_version_reflection_rule_ids": ["xvr"],
                "cross_version_reflection_rules_path": "rulebooks/v2_6.json",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/verify_trace_rules.py",
            "--trace",
            str(trace),
            "--require-cross-version-rules",
            "--require-rulebook-path",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.returncode == 0, result.stderr


def test_trace_audit_fails_when_rules_are_missing(tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_text(
        json.dumps(
            {
                "task_id": 1,
                "event": "task_step",
                "cross_version_reflection_rule_ids": [],
                "cross_version_reflection_rules_path": "rulebooks/v2_6.json",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/verify_trace_rules.py",
            "--trace",
            str(trace),
            "--require-cross-version-rules",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.returncode == 2
    assert "missing cross_version_reflection_rule_ids" in result.stderr
