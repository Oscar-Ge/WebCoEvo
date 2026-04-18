import json
import os
import subprocess
import sys
from pathlib import Path

from linkding_xvr_minimal.rule_pipeline.reflection_verify import verify_rulebook_contract


ROOT = Path(__file__).resolve().parents[1]


def test_v241_rulebook_contract_real_candidate_has_no_task_scopes_and_covers_required_gap_phrases():
    rulebook_path = ROOT / "rulebooks" / "v2_4_1.json"
    summary_path = ROOT / "artifacts" / "reflection" / "v2_4_1" / "gpt54_candidate_summary.json"

    payload = json.loads(rulebook_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    required_gap_phrases = list(summary.get("required_gap_phrases") or [])

    report = verify_rulebook_contract(
        payload,
        max_rules=8,
        no_task_scopes=True,
        required_gap_phrases=required_gap_phrases,
    )

    assert payload["rule_count"] == 8
    assert report["ok"] is True
    assert report["errors"] == []
    assert payload["required_gap_phrases"] == required_gap_phrases


def test_v241_rulebook_verify_cli_reports_ok_and_full_focus20_coverage():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/verify_reflection_rulebook.py",
            "--task-file",
            "configs/focus20_hardv3_full.raw.json",
            "--rulebook",
            "rulebooks/v2_4_1.json",
            "--no-task-scopes",
            "--json",
        ],
        cwd=str(ROOT),
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["contract"]["ok"] is True
    assert payload["coverage"]["missing_task_ids"] == []
    assert payload["coverage"]["covered"] == payload["coverage"]["task_count"] == 68
