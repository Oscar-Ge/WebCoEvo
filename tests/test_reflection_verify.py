import json
import os
import subprocess
import sys

from linkding_xvr_minimal.rule_pipeline.reflection_verify import (
    build_verification_report,
    verify_rule_coverage,
    verify_rulebook_contract,
)


def _rule(rule_id="xvr_candidate_0001", title="Query finalization rule", scope=None):
    return {
        "rule_id": rule_id,
        "title": title,
        "scope": {"drift_types": ["runtime"]} if scope is None else scope,
        "trigger": {
            "old_assumption": "The page still needs another query apply.",
            "observed_symptoms": ["Exact query evidence is visible."],
        },
        "adaptation_strategy": ["Finalize exact query evidence before clicking Apply."],
        "verification_check": ["The query is visible in URL or field state."],
        "forbidden_actions": ["Do not apply again after final evidence is visible."],
        "confidence": 0.9,
    }


def _task(task_id=101, drift_type="runtime"):
    return {
        "task_id": task_id,
        "intent": "Open the filtered bookmarks page.",
        "start_url": "http://localhost:9103/bookmarks/?q=test",
        "instantiation_dict": {
            "version": "1.45.0",
            "source_task_id": 16017,
            "focus20_source_task_id": 16017,
            "family": "F16017",
            "drift_type": drift_type,
            "variant": drift_type,
            "start_url": "http://localhost:9103/bookmarks/?q=test",
        },
    }


def test_verify_rulebook_contract_accepts_valid_compact_candidate():
    report = verify_rulebook_contract(
        {"rules": [_rule()]},
        max_rules=8,
        no_task_scopes=True,
        required_gap_phrases=["query"],
    )

    assert report["ok"] is True
    assert report["errors"] == []
    assert report["rule_count"] == 1


def test_verify_rulebook_contract_rejects_size_missing_scope_task_scope_and_gap_requirements():
    payload = {
        "rules": [
            _rule(scope={}),
            _rule(rule_id="xvr_candidate_0002", scope={"task_ids": [101], "drift_types": ["runtime"]}),
            dict(_rule(rule_id="xvr_candidate_0003"), adaptation_strategy=[]),
        ]
        + [_rule(rule_id="xvr_candidate_{:04d}".format(index), title="Extra {}".format(index)) for index in range(4, 11)]
    }

    report = verify_rulebook_contract(
        payload,
        max_rules=8,
        no_task_scopes=True,
        required_gap_phrases=["checkpoint"],
    )

    assert report["ok"] is False
    assert "too_many_rules" in report["errors"]
    assert "rule[0].empty_scope" in report["errors"]
    assert "rule[1].task_scope_not_allowed" in report["errors"]
    assert "rule[2].missing_required_fields:adaptation_strategy" in report["errors"]
    assert "missing_required_gap_phrase:checkpoint" in report["errors"]


def test_verify_rule_coverage_uses_runtime_rulebook_selection(tmp_path):
    task_file = tmp_path / "tasks.json"
    rulebook_file = tmp_path / "rulebook.json"
    task_file.write_text(json.dumps([_task()]), encoding="utf-8")
    rulebook_file.write_text(json.dumps({"rules": [_rule()]}), encoding="utf-8")

    coverage = verify_rule_coverage(task_file, rulebook_file, rule_limit=8)

    assert coverage["task_count"] == 1
    assert coverage["covered"] == 1
    assert coverage["missing_task_ids"] == []
    assert coverage["rows"][0]["selected_rule_ids"] == ["xvr_candidate_0001"]


def test_verify_reflection_rulebook_cli_returns_nonzero_on_contract_failure(tmp_path):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    task_file = tmp_path / "tasks.json"
    rulebook_file = tmp_path / "rulebook.json"
    task_file.write_text(json.dumps([_task()]), encoding="utf-8")
    rulebook_file.write_text(json.dumps({"rules": [_rule(scope={"task_ids": [101]})]}), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/verify_reflection_rulebook.py",
            "--task-file",
            str(task_file),
            "--rulebook",
            str(rulebook_file),
            "--max-rules",
            "8",
            "--no-task-scopes",
            "--require-full-coverage",
            "--json",
        ],
        cwd=repo_root,
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["contract"]["ok"] is False
    assert "rule[0].task_scope_not_allowed" in payload["contract"]["errors"]


def test_build_verification_report_combines_contract_and_coverage(tmp_path):
    task_file = tmp_path / "tasks.json"
    rulebook_file = tmp_path / "rulebook.json"
    payload = {"rules": [_rule()]}
    task_file.write_text(json.dumps([_task()]), encoding="utf-8")
    rulebook_file.write_text(json.dumps(payload), encoding="utf-8")

    report = build_verification_report(
        payload,
        task_file=task_file,
        rulebook_path=rulebook_file,
        max_rules=8,
        no_task_scopes=True,
    )

    assert report["ok"] is True
    assert report["contract"]["ok"] is True
    assert report["coverage"]["covered"] == 1
