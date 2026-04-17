import json
import os
import subprocess
import sys

from linkding_xvr_minimal.rule_pipeline.reflection_decision import (
    decide_promotion,
    render_promotion_decision_md,
    summarize_eval_comparison,
    summarize_transition_artifact,
)


def _eval(task_id, success, error=""):
    return {"task_id": task_id, "success": success, "error": error}


def _transition(task_id, transition, validity="valid_for_mining"):
    return {"task_id": task_id, "transition": transition, "validity": validity}


def test_summarize_eval_comparison_tracks_improvements_regressions_and_buckets():
    manifest = {
        "buckets": {
            "must_recover": [1],
            "must_keep": [2],
            "regression_rails": [3],
            "diagnostic_frontier": [4],
        }
    }

    summary = summarize_eval_comparison(
        baseline_eval_rows=[_eval(1, False), _eval(2, True), _eval(3, True), _eval(4, False)],
        candidate_eval_rows=[_eval(1, True), _eval(2, False), _eval(3, True), _eval(4, False)],
        delta_manifest=manifest,
    )

    assert summary["improved_task_ids"] == [1]
    assert summary["regressed_task_ids"] == [2]
    assert summary["bucket_regressions"]["must_keep"] == [2]
    assert summary["baseline_success_rate"] == 0.5
    assert summary["candidate_success_rate"] == 0.5


def test_summarize_transition_artifact_maps_saved_and_lost_to_decision_summary():
    summary = summarize_transition_artifact(
        {
            "rows": [
                _transition(1, "saved"),
                _transition(2, "lost"),
                _transition(3, "both_success"),
                _transition(4, "invalid_for_mining", validity="invalid_for_mining"),
            ]
        }
    )

    assert summary["improved_task_ids"] == [1]
    assert summary["regressed_task_ids"] == [2]
    assert summary["invalid_count"] == 1
    assert summary["transition_counts"]["saved"] == 1


def test_decide_promotion_rejects_invalid_rulebook_or_infra_dominated_runs():
    assert (
        decide_promotion(
            {"task_count": 4, "invalid_count": 0},
            verification_report={"ok": False, "contract": {"errors": ["too_many_rules"]}},
        )["decision"]
        == "reject"
    )
    assert decide_promotion({"task_count": 4, "invalid_count": 3})["decision"] == "fix_infrastructure"


def test_decide_promotion_promotes_iterates_or_hardens_conservatively():
    verification = {"ok": True, "contract": {"ok": True}}
    promote = decide_promotion(
        {"task_count": 3, "improved_task_ids": [1], "regressed_task_ids": [], "invalid_count": 0},
        verification_report=verification,
    )
    iterate = decide_promotion(
        {
            "task_count": 3,
            "improved_task_ids": [1],
            "regressed_task_ids": [2],
            "bucket_regressions": {"must_keep": [2]},
            "invalid_count": 0,
        },
        verification_report=verification,
    )
    harden = decide_promotion(
        {
            "task_count": 20,
            "baseline_success_rate": 0.95,
            "candidate_success_rate": 0.95,
            "improved_task_ids": [],
            "regressed_task_ids": [],
            "invalid_count": 0,
        },
        verification_report=verification,
    )

    assert promote["decision"] == "promote"
    assert iterate["decision"] == "iterate"
    assert harden["decision"] == "harden_environment"
    assert "Decision: promote" in render_promotion_decision_md(promote)


def test_decide_reflection_promotion_cli_writes_markdown(tmp_path):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    transition_file = tmp_path / "transitions.json"
    verification_file = tmp_path / "verification.json"
    output_file = tmp_path / "promotion.md"
    transition_file.write_text(
        json.dumps({"rows": [_transition(1, "saved"), _transition(2, "both_success")]}),
        encoding="utf-8",
    )
    verification_file.write_text(json.dumps({"ok": True, "contract": {"ok": True}}), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/decide_reflection_promotion.py",
            "--transition-artifact",
            str(transition_file),
            "--verification-report",
            str(verification_file),
            "--output-file",
            str(output_file),
        ],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["decision"] == "promote"
    assert "Decision: promote" in output_file.read_text(encoding="utf-8")
