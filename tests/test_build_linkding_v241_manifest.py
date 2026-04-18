import json
import os
import subprocess
import sys
from pathlib import Path


def _touch_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _make_run(root, family_name, shard_name, run_name, suffix):
    run_dir = root / family_name / shard_name / run_name
    _touch_jsonl(run_dir / "uitars_eval_{}.jsonl".format(suffix), [{"task_id": 1, "success": True}])
    _touch_jsonl(run_dir / "uitars_trace_{}.jsonl".format(suffix), [{"task_id": 1, "step": 0}])
    return run_dir


def test_build_linkding_v241_manifest_cli_resolves_required_runs_and_optional_expel_only(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    results_root = tmp_path / "results"
    output_file = tmp_path / "run_manifest.json"

    _make_run(
        results_root,
        "focus20_first_modified_v2_4_expel_official_minimal_v1",
        "shard_access",
        "run_20260417_233737_first_modified_rules_smoke_qwen3vl_v3",
        "20260417_233927",
    )
    focus20_first_full = _make_run(
        results_root,
        "focus20_first_modified_v2_4_expel_official_minimal_v1",
        "shard_access",
        "run_20260417_234856_first_modified_rules_full_qwen3vl_v1",
        "20260418_025741",
    )
    focus20_hard = _make_run(
        results_root,
        "focus20_hardv3_v2_4_expel_official_minimal_v1",
        "shard_surface",
        "run_20260417_125123_webcoevo_3x2_focus20expel_v2",
        "20260417_125755",
    )
    taskbank_first = _make_run(
        results_root,
        "taskbank36_first_modified_v2_4_expel_official_minimal_v1",
        "shard_runtime_process",
        "run_20260417_234856_first_modified_rules_full_qwen3vl_v1",
        "20260418_061110",
    )
    taskbank_hard = _make_run(
        results_root,
        "taskbank36_hardv3_v2_4_expel_official_minimal_v1",
        "shard_surface",
        "run_20260417_125123_webcoevo_3x2_focus20expel_v2",
        "20260417_144509",
    )
    focus20_first_expel_only = _make_run(
        results_root,
        "focus20_first_modified_expel_only_official_minimal_v1",
        "shard_access",
        "run_20260417_234856_first_modified_rules_full_qwen3vl_v1",
        "20260417_235423",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_linkding_v241_manifest.py",
            "--results-root",
            str(results_root),
            "--output-file",
            str(output_file),
        ],
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.returncode == 0, result.stderr
    manifest = json.loads(output_file.read_text(encoding="utf-8"))

    focus20_v24 = manifest["focus20"]["first_modified"]["v2_4"]
    assert focus20_v24["run_dir"].endswith("run_20260417_234856_first_modified_rules_full_qwen3vl_v1")
    assert focus20_v24["eval_path"].endswith(".jsonl")
    assert focus20_v24["trace_path"].endswith(".jsonl")
    assert focus20_v24["eval_paths"] == [
        str(focus20_first_full / "uitars_eval_20260418_025741.jsonl")
    ]
    assert focus20_v24["trace_paths"] == [
        str(focus20_first_full / "uitars_trace_20260418_025741.jsonl")
    ]

    taskbank_v24 = manifest["taskbank36"]["hardv3"]["v2_4"]
    assert taskbank_v24["run_dir"].endswith("run_20260417_125123_webcoevo_3x2_focus20expel_v2")
    assert taskbank_v24["eval_paths"] == [
        str(taskbank_hard / "uitars_eval_20260417_144509.jsonl")
    ]

    optional_entry = manifest["focus20"]["first_modified"]["expel_only"]
    assert optional_entry["run_dir"].endswith("run_20260417_234856_first_modified_rules_full_qwen3vl_v1")
    assert optional_entry["eval_paths"] == [
        str(focus20_first_expel_only / "uitars_eval_20260417_235423.jsonl")
    ]

    summary = json.loads(result.stdout)
    assert summary["required_entries"] == 4
    assert summary["optional_entries"] == 1
    assert summary["taskbank36"]["first_modified"]["v2_4"]["run_dir"] == str(taskbank_first)
    assert summary["focus20"]["hardv3"]["v2_4"]["run_dir"] == str(focus20_hard)

