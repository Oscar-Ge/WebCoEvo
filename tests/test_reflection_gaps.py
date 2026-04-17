import json
import os
import subprocess
import sys

from linkding_xvr_minimal.rule_pipeline.reflection_gaps import (
    build_behavior_gaps,
    detect_gap_labels,
    priority_for_gap,
)


def _step(step, action="", model_output="", url="", error="", final_answer="", success_so_far=False):
    return {
        "step": step,
        "event": "task_step",
        "action": action,
        "model_output": model_output,
        "url": url,
        "error": error,
        "final_answer": final_answer,
        "success_so_far": success_so_far,
    }


def _row(task_id, transition, right_trace, right_error="", start_url=""):
    return {
        "task_id": task_id,
        "source_task_id": task_id,
        "focus20_source_task_id": task_id,
        "family": "F{}".format(task_id),
        "variant": "runtime",
        "drift_type": "runtime",
        "intent": "Complete query task",
        "start_url": start_url,
        "transition": transition,
        "validity": "valid_for_mining",
        "right_error": right_error,
        "right_trace_excerpt": right_trace,
        "left_trace_excerpt": [],
    }


def test_detect_gap_labels_from_trace_features():
    hidden = _row(
        1,
        "both_fail",
        [
            _step(0, action="click('#settings')", error="element is hidden"),
            _step(1, action="click('#settings')", error="element is hidden"),
        ],
    )
    query = _row(
        2,
        "lost",
        [
            _step(0, url="/bookmarks?query=amber", model_output="Exact query amber is visible"),
            _step(1, action="click('Apply')", url="/bookmarks?query=amber"),
        ],
    )
    login = _row(
        3,
        "lost",
        [_step(0, url="/login?next=/bookmarks/new"), _step(1, url="/login")],
        start_url="http://localhost/login?next=/bookmarks/new",
    )
    reached = _row(
        4,
        "both_fail",
        [
            _step(0, url="/settings", model_output="Requested Settings page is visible", success_so_far=True),
            _step(1, action="noop", url="/settings", model_output="still on requested page"),
        ],
    )
    mark = _row(
        5,
        "both_fail",
        [_step(0, action="click('csrfmiddlewaretoken hidden input')", model_output="hidden input")],
    )

    assert "hidden_click_repeated" in detect_gap_labels(hidden)
    assert "query_state_finalization_missed" in detect_gap_labels(query)
    assert "login_next_lost" in detect_gap_labels(login)
    assert "target_reached_but_no_final_answer" in detect_gap_labels(reached)
    assert "noninteractive_mark_clicked" in detect_gap_labels(mark)


def test_build_behavior_gaps_groups_support_and_risk_rows():
    artifact = {
        "schema_version": "webcoevo-xvr-transitions-v1",
        "rows": [
            _row(
                11,
                "lost",
                [
                    _step(0, url="/bookmarks?query=amber", model_output="query amber visible"),
                    _step(1, action="click('Apply')"),
                ],
            ),
            _row(
                12,
                "saved",
                [
                    _step(0, url="/bookmarks?query=amber", model_output="query amber visible"),
                    _step(1, action="send_msg_to_user('done')", final_answer="done"),
                ],
            ),
            _row(13, "invalid_for_mining", [], right_error="auth_session_failure"),
        ],
    }

    payload = build_behavior_gaps(artifact)
    gaps = {row["gap_id"]: row for row in payload["gaps"]}

    assert payload["schema_version"] == "webcoevo-xvr-behavior-gaps-v1"
    assert gaps["query_state_finalization_missed"]["transition_mix"] == {"lost": 1, "saved": 1}
    assert gaps["query_state_finalization_missed"]["supporting_task_ids"] == [11, 12]
    assert gaps["query_state_finalization_missed"]["risk_task_ids"] == [11]
    assert gaps["query_state_finalization_missed"]["recommended_rule_action"] == "edit_rule"
    assert priority_for_gap(gaps["query_state_finalization_missed"]) == "high"


def test_mine_reflection_gaps_cli_writes_gap_json(tmp_path):
    repo_root = os.path.dirname(os.path.dirname(__file__))
    artifact_file = tmp_path / "transition.json"
    output_file = tmp_path / "gaps.json"
    artifact_file.write_text(
        json.dumps(
            {
                "schema_version": "webcoevo-xvr-transitions-v1",
                "rows": [
                    _row(
                        21,
                        "lost",
                        [
                            _step(0, url="/bookmarks?query=amber", model_output="query amber visible"),
                            _step(1, action="click('Apply')"),
                        ],
                    )
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/mine_reflection_gaps.py",
            "--transition-artifact",
            str(artifact_file),
            "--output-file",
            str(output_file),
        ],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["summary"]["num_gaps"] == 1
    assert payload["gaps"][0]["gap_id"] == "query_state_finalization_missed"
