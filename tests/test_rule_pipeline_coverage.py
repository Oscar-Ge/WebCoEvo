import json
import os
import subprocess
import sys
from pathlib import Path

from linkding_xvr_minimal.browser_task import compile_raw_task
from linkding_xvr_minimal.expel_rules import load_expel_rules
from linkding_xvr_minimal.rulebook import load_rulebook
from linkding_xvr_minimal.tasks import load_raw_tasks


def test_summarize_xvr_coverage_reports_full_smoke_coverage():
    from linkding_xvr_minimal.rule_pipeline.coverage import summarize_xvr_coverage

    repo_root = Path(__file__).resolve().parents[1]
    rows = load_raw_tasks(repo_root / "configs" / "focus20_hardv3_smoke.raw.json")
    specs = [compile_raw_task(row) for row in rows]
    rulebook = load_rulebook(repo_root / "rulebooks" / "v2_6.json")

    summary = summarize_xvr_coverage(specs, rulebook, limit=8, fail_on_empty=True)

    assert summary["covered"] == len(specs)
    assert summary["missing_task_ids"] == []
    assert set(summary["by_drift_type"].keys()) == {
        "access",
        "content",
        "functional",
        "process",
        "runtime",
        "structural",
        "surface",
    }


def test_summarize_expel_coverage_reports_official_eval_selection():
    from linkding_xvr_minimal.rule_pipeline.coverage import summarize_expel_coverage

    repo_root = Path(__file__).resolve().parents[1]
    rows = load_raw_tasks(repo_root / "configs" / "focus20_hardv3_smoke.raw.json")
    specs = [compile_raw_task(row) for row in rows]
    rulebook = load_expel_rules(repo_root / "rulebooks" / "expel_official_v2.json")

    summary = summarize_expel_coverage(
        specs,
        rulebook,
        limit=3,
        fidelity="official_eval",
    )

    assert summary["covered"] == len(specs)
    assert summary["missing_task_ids"] == []
    assert summary["fidelity"] == "official_eval"
    assert summary["selected_rule_count_min"] == 16
    assert summary["selected_rule_count_max"] == 16


def test_verify_rule_coverage_cli_emits_machine_readable_report(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "scripts/verify_rule_coverage.py",
            "--task-file",
            "configs/focus20_hardv3_smoke.raw.json",
            "--rulebook",
            "rulebooks/v2_6.json",
            "--expel-rule-file",
            "rulebooks/expel_official_v2.json",
            "--expel-fidelity",
            "official_eval",
            "--require-full-xvr-coverage",
            "--require-full-expel-coverage",
            "--json",
        ],
        cwd=str(repo_root),
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["task_count"] == 7
    assert payload["xvr"]["missing_task_ids"] == []
    assert payload["expel"]["missing_task_ids"] == []
