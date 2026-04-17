import json
import os
import subprocess
import sys


def _rule(rule_id, title, scope=None):
    return {
        "rule_id": rule_id,
        "title": title,
        "scope": scope or {"drift_types": ["runtime"]},
        "trigger": {
            "old_assumption": "The old action is safe.",
            "observed_symptoms": ["Runtime drift is visible."],
        },
        "adaptation_strategy": ["Use a safer visible target."],
        "verification_check": ["The visible state advances."],
        "forbidden_actions": ["Do not repeat stale hidden clicks."],
        "confidence": 0.8,
    }


def test_build_reflection_rules_cli_uses_stub_proposals_and_writes_candidate(tmp_path):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    base_rulebook = tmp_path / "base.json"
    mining_cases = tmp_path / "cases.jsonl"
    stub_proposals = tmp_path / "proposals.json"
    output_file = tmp_path / "candidate.json"

    base_rulebook.write_text(
        json.dumps(
            {
                "artifact_type": "cross_version_reflection_rules",
                "version": "v2_6",
                "rules": [_rule("xvr26_0001", "Old runtime rule")],
            }
        ),
        encoding="utf-8",
    )
    mining_cases.write_text(
        json.dumps(
            {
                "case_id": "gap.hidden_click_repeated.101",
                "gap_id": "hidden_click_repeated",
                "transition": "lost",
                "diagnosis": {"observed_gap": "Hidden click repeated."},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    stub_proposals.write_text(
        json.dumps(
            {
                "schema_version": "webcoevo-xvr-rule-proposals-v1",
                "proposals": [
                    {
                        "operation": "edit_rule",
                        "target_rule_id": "xvr26_0001",
                        "rule": _rule("", "Edited runtime rule"),
                        "support": {"gap_ids": ["hidden_click_repeated"], "supporting_task_ids": [101]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_reflection_rules.py",
            "--base-rulebook",
            str(base_rulebook),
            "--mining-cases",
            str(mining_cases),
            "--output-file",
            str(output_file),
            "--stub-proposals-file",
            str(stub_proposals),
            "--max-rules",
            "8",
        ],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.returncode == 0, result.stderr
    candidate = json.loads(output_file.read_text(encoding="utf-8"))
    assert candidate["artifact_type"] == "cross_version_reflection_rules"
    assert candidate["rule_count"] == 1
    assert candidate["rules"][0]["title"] == "Edited runtime rule"
    assert candidate["rules"][0]["support"]["gap_ids"] == ["hidden_click_repeated"]
    summary = json.loads(result.stdout)
    assert summary["accepted_proposals"] == 1
    assert summary["rejected_proposals"] == 0
