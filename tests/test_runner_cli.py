import json
import os
import subprocess
import sys


def _run(args):
    env = dict(os.environ)
    env["PYTHONPATH"] = "."
    return subprocess.run(
        [sys.executable, "-m", "linkding_xvr_minimal.runner"] + args,
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )


def test_compile_only_prints_normalized_metadata():
    result = _run(
        [
            "--task-file",
            "configs/focus20_hardv3_smoke.raw.json",
            "--rulebook",
            "rulebooks/v2_6.json",
            "--run-label",
            "test_compile",
            "--limit",
            "1",
            "--compile-only",
        ]
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["task_count"] == 1
    assert payload["tasks"][0]["source_task_id"]
    assert payload["tasks"][0]["focus20_source_task_id"]
    assert payload["tasks"][0]["drift_type"]


def test_preflight_rules_only_prints_selected_rule_ids():
    result = _run(
        [
            "--task-file",
            "configs/focus20_hardv3_smoke.raw.json",
            "--rulebook",
            "rulebooks/v2_6.json",
            "--run-label",
            "test_preflight",
            "--limit",
            "1",
            "--preflight-rules-only",
            "--fail-on-empty-xvr-rules",
        ]
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["task_count"] == 1
    assert payload["preflight"][0]["selected_rule_ids"]
    assert payload["preflight"][0]["rulebook_path"].endswith("rulebooks/v2_6.json")


def test_preflight_fail_on_empty_returns_nonzero(tmp_path):
    rulebook = tmp_path / "empty.json"
    rulebook.write_text('{"rules": [{"rule_id": "none", "scope": {"drift_types": ["impossible"]}}]}', encoding="utf-8")

    result = _run(
        [
            "--task-file",
            "configs/focus20_hardv3_smoke.raw.json",
            "--rulebook",
            str(rulebook),
            "--run-label",
            "test_empty",
            "--limit",
            "1",
            "--preflight-rules-only",
            "--fail-on-empty-xvr-rules",
        ]
    )

    assert result.returncode == 2
    assert "No cross-version reflection rules selected" in result.stderr


def test_variant_filter_applies_before_compile_output():
    result = _run(
        [
            "--task-file",
            "configs/focus20_hardv3_smoke.raw.json",
            "--rulebook",
            "rulebooks/v2_6.json",
            "--run-label",
            "test_variant",
            "--variant",
            "runtime",
            "--compile-only",
        ]
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["task_count"] == 1
    assert payload["tasks"][0]["variant"] == "runtime"


def test_preflight_rules_only_reports_optional_expel_rules(tmp_path):
    expel_path = tmp_path / "expel.json"
    expel_path.write_text(
        '{"rules": [{"rule_id": "expel_login", "text": "Use local credentials.", "scope": {"drift_types": ["access"]}}]}',
        encoding="utf-8",
    )

    result = _run(
        [
            "--task-file",
            "configs/focus20_hardv3_smoke.raw.json",
            "--rulebook",
            "rulebooks/v2_6.json",
            "--expel-rule-file",
            str(expel_path),
            "--run-label",
            "test_expel_preflight",
            "--variant",
            "access",
            "--preflight-rules-only",
            "--fail-on-empty-xvr-rules",
        ]
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["expel_preflight"][0]["selected_rule_ids"] == ["expel_login"]


def test_preflight_official_expel_fidelity_loads_full_rulebook():
    result = _run(
        [
            "--task-file",
            "configs/focus20_hardv3_smoke.raw.json",
            "--rulebook",
            "rulebooks/v2_6.json",
            "--expel-rule-file",
            "rulebooks/expel_official_v2.json",
            "--expel-fidelity",
            "official_eval",
            "--run-label",
            "test_official_expel_preflight",
            "--variant",
            "access",
            "--preflight-rules-only",
            "--fail-on-empty-xvr-rules",
        ]
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    rulebook_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rulebooks", "expel_official_v2.json")
    with open(rulebook_path, encoding="utf-8") as fh:
        expected_rule_count = len(json.load(fh)["rules"])
    assert payload["expel_preflight"][0]["fidelity"] == "official_eval"
    assert len(payload["expel_preflight"][0]["selected_rule_ids"]) == expected_rule_count
