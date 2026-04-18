import json
from pathlib import Path
from typing import Dict, List

from linkding_xvr_minimal.reporting_hardv3 import (
    aggregate_eval_files,
    discover_latest_eval_files,
    render_benchmark_figure_svg,
    render_markdown_report,
)


def _write_eval(
    root: Path,
    *,
    benchmark: str,
    setting: str,
    shard: str,
    run_label: str,
    rows: List[Dict[str, object]],
) -> Path:
    if setting == "expel_only":
        parent = root / f"{benchmark}_{setting}_official_minimal_v1"
    else:
        parent = root / f"{benchmark}_{setting}_expel_official_minimal_v1"
    run_dir = parent / f"shard_{shard}" / run_label
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"uitars_eval_{run_label}.jsonl"
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def test_discover_latest_eval_files_prefers_latest_run_and_mixed_naming(tmp_path):
    _write_eval(
        tmp_path / "repo-results",
        benchmark="focus20_hardv3",
        setting="v2_4",
        shard="access",
        run_label="run_20260416_010101_old",
        rows=[{"task_id": 1, "drift_type": "access", "variant": "access", "success": False}],
    )
    latest = _write_eval(
        tmp_path / "repo-results",
        benchmark="focus20_hardv3",
        setting="v2_4",
        shard="access",
        run_label="run_20260417_020202_new",
        rows=[{"task_id": 1, "drift_type": "access", "variant": "access", "success": True}],
    )
    expel_only = _write_eval(
        tmp_path / "external-results",
        benchmark="focus20_hardv3",
        setting="expel_only",
        shard="surface",
        run_label="run_20260417_030303_debug",
        rows=[{"task_id": 2, "drift_type": "surface", "variant": "surface", "success": False}],
    )

    discovered = discover_latest_eval_files(
        [tmp_path / "repo-results", tmp_path / "external-results"]
    )

    assert discovered[("focus20_hardv3", "v2_4", "access")] == latest
    assert discovered[("focus20_hardv3", "expel_only", "surface")] == expel_only


def test_aggregate_eval_files_computes_overall_and_per_drift_rates(tmp_path):
    expel_root = tmp_path / "expel"
    repo_root = tmp_path / "repo"
    files = {
        ("focus20_hardv3", "expel_only", "access"): _write_eval(
            expel_root,
            benchmark="focus20_hardv3",
            setting="expel_only",
            shard="access",
            run_label="run_20260417_010000",
            rows=[
                {"task_id": 1, "drift_type": "access", "variant": "access", "success": False},
                {"task_id": 2, "drift_type": "runtime", "variant": "runtime", "success": True},
                {"task_id": 3, "drift_type": "process", "variant": "process", "success": False},
            ],
        ),
        ("focus20_hardv3", "v2_4", "access"): _write_eval(
            repo_root,
            benchmark="focus20_hardv3",
            setting="v2_4",
            shard="access",
            run_label="run_20260417_020000",
            rows=[
                {"task_id": 1, "drift_type": "access", "variant": "access", "success": True},
                {"task_id": 2, "drift_type": "runtime", "variant": "runtime", "success": True},
                {"task_id": 3, "drift_type": "process", "variant": "process", "success": True},
            ],
        ),
        ("taskbank36_hardv3", "expel_only", "structural_functional"): _write_eval(
            expel_root,
            benchmark="taskbank36_hardv3",
            setting="expel_only",
            shard="structural_functional",
            run_label="run_20260417_030000",
            rows=[
                {"task_id": 10, "drift_type": "structural", "variant": "structural", "success": False},
                {"task_id": 11, "drift_type": "functional", "variant": "functional", "success": True},
            ],
        ),
        ("taskbank36_hardv3", "v2_4", "structural_functional"): _write_eval(
            repo_root,
            benchmark="taskbank36_hardv3",
            setting="v2_4",
            shard="structural_functional",
            run_label="run_20260417_040000",
            rows=[
                {"task_id": 10, "drift_type": "structural", "variant": "structural", "success": True},
                {"task_id": 11, "drift_type": "functional", "variant": "functional", "success": True},
            ],
        ),
    }

    summary = aggregate_eval_files(files)

    focus20 = summary["benchmarks"]["focus20_hardv3"]
    assert focus20["expected_total"] == 3
    assert focus20["expected_by_drift"]["access"] == 1
    assert focus20["settings"]["expel_only"]["successes"] == 1
    assert focus20["settings"]["expel_only"]["overall_rate"] == 1 / 3
    assert focus20["settings"]["v2_4"]["by_drift"]["process"]["rate"] == 1.0

    taskbank = summary["benchmarks"]["taskbank36_hardv3"]
    assert taskbank["expected_total"] == 2
    assert taskbank["settings"]["expel_only"]["overall_rate"] == 0.5
    assert taskbank["settings"]["v2_4"]["by_drift"]["structural"]["rate"] == 1.0


def test_renderers_include_expected_figure_and_report_content(tmp_path):
    files = {
        ("focus20_hardv3", "expel_only", "access"): _write_eval(
            tmp_path / "expel",
            benchmark="focus20_hardv3",
            setting="expel_only",
            shard="access",
            run_label="run_20260417_010000",
            rows=[
                {"task_id": 1, "drift_type": "access", "variant": "access", "success": False},
                {"task_id": 2, "drift_type": "surface", "variant": "surface", "success": True},
            ],
        ),
        ("focus20_hardv3", "v2_4", "access"): _write_eval(
            tmp_path / "repo",
            benchmark="focus20_hardv3",
            setting="v2_4",
            shard="access",
            run_label="run_20260417_020000",
            rows=[
                {"task_id": 1, "drift_type": "access", "variant": "access", "success": True},
                {"task_id": 2, "drift_type": "surface", "variant": "surface", "success": True},
            ],
        ),
        ("taskbank36_hardv3", "expel_only", "runtime_process"): _write_eval(
            tmp_path / "expel",
            benchmark="taskbank36_hardv3",
            setting="expel_only",
            shard="runtime_process",
            run_label="run_20260417_030000",
            rows=[
                {"task_id": 10, "drift_type": "runtime", "variant": "runtime", "success": False},
                {"task_id": 11, "drift_type": "process", "variant": "process", "success": True},
            ],
        ),
        ("taskbank36_hardv3", "v2_4", "runtime_process"): _write_eval(
            tmp_path / "repo",
            benchmark="taskbank36_hardv3",
            setting="v2_4",
            shard="runtime_process",
            run_label="run_20260417_040000",
            rows=[
                {"task_id": 10, "drift_type": "runtime", "variant": "runtime", "success": True},
                {"task_id": 11, "drift_type": "process", "variant": "process", "success": True},
            ],
        ),
    }
    summary = aggregate_eval_files(files)

    svg = render_benchmark_figure_svg("focus20_hardv3", summary["benchmarks"]["focus20_hardv3"])
    report = render_markdown_report(
        summary,
        figure_paths={
            "focus20_hardv3": "../../figures/focus20_hardv3_xvr_matrix.svg",
            "taskbank36_hardv3": "../../figures/taskbank36_hardv3_xvr_matrix.svg",
        },
    )

    assert "Focus20" in svg
    assert "Access" in svg
    assert "Overall" in svg
    assert "Non-reflection" in svg

    assert "# Hardv3 XVR Matrix Report" in report
    assert "../../figures/focus20_hardv3_xvr_matrix.svg" in report
    assert "| Non-reflection | 1/2 | 50.0% |" in report
    assert "TaskBank36 is treated as the held-out test benchmark" in report
