import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "reporting" / "generate_linkding_v241_report.py"


def test_generate_linkding_v241_report_cli_writes_markdown_and_promotion_packet(tmp_path):
    artifacts_dir = tmp_path / "artifacts" / "reflection" / "v2_4_1"
    docs_dir = tmp_path / "docs" / "reports"
    rulebooks_dir = tmp_path / "rulebooks"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    rulebooks_dir.mkdir(parents=True, exist_ok=True)

    (artifacts_dir / "api_smoke.json").write_text(
        json.dumps(
            {
                "ok": True,
                "chat_ok": True,
                "generation_endpoint": "responses_stream",
                "provider_models_ok": True,
                "response_excerpt": "OK",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (artifacts_dir / "focus20_transition_first_modified_to_hardv3.json").write_text(
        json.dumps(
            {
                "summary": {
                    "num_rows": 68,
                    "transition_counts": {"both_success": 65, "lost": 2, "both_fail": 1},
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (artifacts_dir / "taskbank36_transition_first_modified_to_hardv3.json").write_text(
        json.dumps(
            {
                "summary": {
                    "num_rows": 167,
                    "transition_counts": {"both_success": 89, "lost": 54, "saved": 8, "both_fail": 16},
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (artifacts_dir / "focus20_casebook.md").write_text(
        "\n".join(
            [
                "# focus20 Casebook",
                "",
                "## Transition Legend",
                "- `both_success`: old success -> new success",
                "- `lost`: old success -> new fail",
                "",
                "## Representative `lost` Excerpts",
                "- task 1600303 (`content` / `lost`)",
                "  right: release_lookup fallback replaced the filtered bookmark destination after login",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "gpt54_candidate_summary.json").write_text(
        json.dumps(
            {
                "candidate_version": "v2_4_1",
                "selected_transport": "responses_stream",
                "proposal_summary": {"accepted": 2, "rejected": 1},
                "required_gap_phrases": ["login next", "filtered bookmark", "final answer"],
                "provider_summary": {
                    "preserve_patterns": ["Preserve the original next redirect."],
                    "lost_patterns": ["Filtered bookmark destinations were replaced after login."],
                },
                "evidence": {"mode": "transition_casebook_fallback"},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (rulebooks_dir / "v2_4.json").write_text(
        json.dumps(
            {
                "version": "v2_4",
                "rules": [
                    {"rule_id": "xvr24_0003", "title": "Finalize instead of noop when URL already proves the target state"},
                    {"rule_id": "xvr24_0004", "title": "Preserve task-specific login next parameters"},
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (rulebooks_dir / "v2_4_1.json").write_text(
        json.dumps(
            {
                "version": "v2_4_1",
                "rule_count": 2,
                "required_gap_phrases": ["login next", "filtered bookmark", "final answer"],
                "rules": [
                    {"rule_id": "xvr_candidate_0001", "source_rule_id": "xvr24_0003", "title": "Finalize instead of acting when URL already proves completion"},
                    {"rule_id": "xvr_candidate_0002", "source_rule_id": "xvr24_0004", "title": "Preserve task-specific login next destinations and their query parameters across authentication"},
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--root-dir",
            str(tmp_path),
        ],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.returncode == 0, result.stderr
    report_path = docs_dir / "2026-04-18-gpt54-v2_4_1-reflection-hardening-report.md"
    packet_path = artifacts_dir / "promotion_packet.json"
    assert report_path.exists()
    assert packet_path.exists()

    report_text = report_path.read_text(encoding="utf-8")
    assert "API smoke status" in report_text
    assert "Focus20 transition counts" in report_text
    assert "TaskBank36 held-out summary" in report_text
    assert "old success -> new success" in report_text
    assert "old success -> new fail" in report_text
    assert "v2.4 -> v2.4.1 rule delta summary" in report_text

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    assert packet["api_smoke"]["generation_endpoint"] == "responses_stream"
    assert packet["focus20"]["transition_counts"]["lost"] == 2
    assert packet["taskbank36"]["transition_counts"]["saved"] == 8
    assert packet["rule_delta"]["edited_rule_count"] == 2
