import importlib.util
import json
from pathlib import Path


def _load_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "reporting"
        / "generate_umich_qwen3_rule_report.py"
    )
    spec = importlib.util.spec_from_file_location("generate_umich_qwen3_rule_report", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _setting(successes, total):
    return {
        "complete": True,
        "completed": total,
        "successes": successes,
        "overall_rate": successes / total,
        "completion_rate": 1.0,
        "observed_success_rate": successes / total,
        "by_drift": {
            "access": {"expected": 36, "completed": 36, "successes": 27, "completion_rate": 1.0, "rate": 27 / 36, "observed_success_rate": 27 / 36},
            "surface": {"expected": 36, "completed": 36, "successes": 26, "completion_rate": 1.0, "rate": 26 / 36, "observed_success_rate": 26 / 36},
            "content": {"expected": 14, "completed": 14, "successes": 8, "completion_rate": 1.0, "rate": 8 / 14, "observed_success_rate": 8 / 14},
            "structural": {"expected": 13, "completed": 13, "successes": 10, "completion_rate": 1.0, "rate": 10 / 13, "observed_success_rate": 10 / 13},
            "functional": {"expected": 13, "completed": 13, "successes": 10, "completion_rate": 1.0, "rate": 10 / 13, "observed_success_rate": 10 / 13},
            "runtime": {"expected": 36, "completed": 36, "successes": 27, "completion_rate": 1.0, "rate": 27 / 36, "observed_success_rate": 27 / 36},
            "process": {"expected": 19, "completed": 19, "successes": 16, "completion_rate": 1.0, "rate": 16 / 19, "observed_success_rate": 16 / 19},
        },
    }


def _benchmark(no_rules, expel_only, expected_total, expected_by_drift):
    return {
        "label": "TaskBank36",
        "expected_total": expected_total,
        "expected_by_drift": dict(expected_by_drift),
        "all_complete": True,
        "settings": {
            "no_rules": no_rules,
            "expel_only": expel_only,
        },
    }


def _focus20_benchmark():
    total = 68
    expected_by_drift = {
        "access": 13,
        "surface": 13,
        "content": 9,
        "structural": 6,
        "functional": 5,
        "runtime": 16,
        "process": 6,
    }
    return {
        "label": "Focus20",
        "expected_total": total,
        "expected_by_drift": expected_by_drift,
        "all_complete": True,
        "settings": {
            "no_rules": {
                "complete": True,
                "completed": total,
                "successes": 9,
                "overall_rate": 9 / total,
                "completion_rate": 1.0,
                "observed_success_rate": 9 / total,
                "by_drift": {drift: {"expected": n, "completed": n, "successes": 0, "completion_rate": 1.0, "rate": 0.0, "observed_success_rate": 0.0} for drift, n in expected_by_drift.items()},
            },
            "expel_only": {
                "complete": True,
                "completed": total,
                "successes": 56,
                "overall_rate": 56 / total,
                "completion_rate": 1.0,
                "observed_success_rate": 56 / total,
                "by_drift": {drift: {"expected": n, "completed": n, "successes": n, "completion_rate": 1.0, "rate": 1.0, "observed_success_rate": 1.0} for drift, n in expected_by_drift.items()},
            },
        },
    }


def _first_modified_benchmark(label, total, expel_successes, v24_successes, expected_by_drift):
    return {
        "label": label,
        "expected_total": total,
        "expected_by_drift": dict(expected_by_drift),
        "all_complete": True,
        "settings": {
            "expel_only": {
                "complete": True,
                "completed": total,
                "successes": expel_successes,
                "overall_rate": expel_successes / total,
                "completion_rate": 1.0,
                "observed_success_rate": expel_successes / total,
                "by_drift": {drift: {"expected": n, "completed": n, "successes": min(n, expel_successes), "completion_rate": 1.0, "rate": min(n, expel_successes) / n, "observed_success_rate": min(n, expel_successes) / n} for drift, n in expected_by_drift.items()},
            },
            "v2_4": {
                "complete": True,
                "completed": total,
                "successes": v24_successes,
                "overall_rate": v24_successes / total,
                "completion_rate": 1.0,
                "observed_success_rate": v24_successes / total,
                "by_drift": {drift: {"expected": n, "completed": n, "successes": n, "completion_rate": 1.0, "rate": 1.0, "observed_success_rate": 1.0} for drift, n in expected_by_drift.items()},
            },
        },
    }


def _summary():
    taskbank_expected_by_drift = {
        "access": 36,
        "surface": 36,
        "content": 14,
        "structural": 13,
        "functional": 13,
        "runtime": 36,
        "process": 19,
    }
    return {
        "report_date": "2026-04-18",
        "model": "Qwen/Qwen3-VL-30B-A3B-Instruct",
        "endpoint": "http://example.test/v1",
        "agent_mode": "vl_action_reflection",
        "max_steps": 30,
        "max_tokens": 300,
        "provenance": {
            "control_submit_script": "slurm/submit_control_rules_matrix.sh",
            "first_modified_submit_script": "slurm/submit_first_modified_rules_matrix.sh",
            "control_initial_fail_jobs": "a",
            "control_smoke_retry_jobs": "b",
            "control_full_jobs": "c",
            "first_modified_access_smoke_retry_jobs": "d",
            "first_modified_full_jobs": "e",
        },
        "scenarios": {
            "control_1450": {
                "setting_order": ["no_rules", "expel_only"],
                "benchmarks": {
                    "focus20": _focus20_benchmark(),
                    "taskbank36": _benchmark(
                        no_rules=_setting(133, 167),
                        expel_only=_setting(124, 167),
                        expected_total=167,
                        expected_by_drift=taskbank_expected_by_drift,
                    ),
                },
            },
            "first_modified": {
                "setting_order": ["expel_only", "v2_4"],
                "benchmarks": {
                    "focus20": _first_modified_benchmark(
                        "Focus20",
                        68,
                        60,
                        67,
                        {
                            "access": 13,
                            "surface": 13,
                            "content": 9,
                            "structural": 6,
                            "functional": 5,
                            "runtime": 16,
                            "process": 6,
                        },
                    ),
                    "taskbank36": _first_modified_benchmark(
                        "TaskBank36",
                        167,
                        114,
                        143,
                        taskbank_expected_by_drift,
                    ),
                },
            },
        },
    }


def test_write_report_assets_uses_success_figure_for_complete_taskbank_control(tmp_path):
    module = _load_module()

    outputs = module.write_report_assets(
        summary=_summary(),
        figure_dir=tmp_path / "figures",
        report_dir=tmp_path / "reports",
        report_filename="report.md",
    )

    figure_path = Path(outputs["figure_paths"]["control_1450_taskbank36_status"])
    svg = (tmp_path / "reports" / figure_path).read_text(encoding="utf-8")
    assert "TaskBank36 Control 1.45.0: No Rules vs ExpeL" in svg
    assert "Rates are final success rates." in svg
    assert "79.6%" in svg
    assert "74.3%" in svg
    assert "completion coverage" not in svg


def test_render_markdown_report_uses_complete_taskbank_control_language(tmp_path):
    module = _load_module()

    report = module.render_markdown_report(
        _summary(),
        figure_paths={
            "control_1450_focus20": "../../figures/focus20_control_rules_success.svg",
            "control_1450_taskbank36_status": "../../figures/taskbank36_control_rules_status.svg",
            "first_modified_focus20": "../../figures/focus20_first_modified_rules_success.svg",
            "first_modified_taskbank36": "../../figures/taskbank36_first_modified_rules_success.svg",
        },
        report_dir=tmp_path,
    )

    assert "On the original Linkding 1.45.0 TaskBank36 benchmark" in report
    assert "133/167 | 79.6%" in report
    assert "124/167 | 74.3%" in report
    assert "did not finish before the Slurm time limit" not in report
    assert "Observed completion bias is non-uniform" not in report


def test_build_summary_prefers_complete_rerun_eval_when_filtered_run_is_incomplete(tmp_path):
    module = _load_module()

    results_root = tmp_path / "results"
    results_root.mkdir()
    config_path = tmp_path / "taskbank36.json"
    config_path.write_text(
        json.dumps(
            [
                {"task_id": 1, "drift_type": "structural"},
                {"task_id": 2, "drift_type": "functional"},
            ]
        ),
        encoding="utf-8",
    )

    def write_eval(run_label, run_name, filename, rows):
        run_dir = results_root / run_label / run_name
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / filename
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")

    write_eval(
        "taskbank36_1450_control_no_rules_minimal_v1",
        "run_20260417_234856_control_rules_full_qwen3vl_v1",
        "uitars_eval_old.jsonl",
        [
            {"task_id": 1, "drift_type": "structural", "success": False},
            {"task_id": 2, "drift_type": "functional", "success": True},
        ],
    )
    write_eval(
        "taskbank36_1450_control_expel_only_official_minimal_v1",
        "run_20260417_234856_control_rules_full_qwen3vl_v1",
        "uitars_eval_old.jsonl",
        [
            {"task_id": 1, "drift_type": "structural", "success": False},
        ],
    )
    write_eval(
        "taskbank36_1450_control_expel_only_official_minimal_v1",
        "run_20260418_104526_ctrl_rerun",
        "uitars_eval_new.jsonl",
        [
            {"task_id": 1, "drift_type": "structural", "success": True},
            {"task_id": 2, "drift_type": "functional", "success": True},
        ],
    )

    old_results_root = module.RESULTS_ROOT
    old_benchmark_specs = module.BENCHMARK_SPECS
    old_scenarios = module.SCENARIOS
    try:
        module.RESULTS_ROOT = results_root
        module.BENCHMARK_SPECS = {
            "taskbank36": {
                "label": "TaskBank36",
                "config_path": config_path,
            }
        }
        module.SCENARIOS = {
            "control_1450": {
                "title": "Control",
                "description": "Control",
                "setting_order": ["no_rules", "expel_only"],
                "benchmarks": {
                    "taskbank36": {
                        "run_label_by_setting": {
                            "no_rules": "taskbank36_1450_control_no_rules_minimal_v1",
                            "expel_only": "taskbank36_1450_control_expel_only_official_minimal_v1",
                        },
                        "run_name_filter": "full_qwen3vl_v1",
                        "allow_partial": True,
                    }
                },
            }
        }

        summary = module.build_summary()
    finally:
        module.RESULTS_ROOT = old_results_root
        module.BENCHMARK_SPECS = old_benchmark_specs
        module.SCENARIOS = old_scenarios

    payload = summary["scenarios"]["control_1450"]["benchmarks"]["taskbank36"]["settings"]["expel_only"]
    assert payload["complete"] is True
    assert payload["completed"] == 2
    assert payload["successes"] == 2
    assert any("run_20260418_104526_ctrl_rerun" in path for path in payload["source_paths"])


def test_build_summary_uses_unfiltered_rerun_eval_when_filtered_run_has_only_study(tmp_path):
    module = _load_module()

    results_root = tmp_path / "results"
    results_root.mkdir()
    config_path = tmp_path / "taskbank36.json"
    config_path.write_text(
        json.dumps(
            [
                {"task_id": 1, "drift_type": "structural"},
                {"task_id": 2, "drift_type": "functional"},
            ]
        ),
        encoding="utf-8",
    )

    study_dir = (
        results_root
        / "taskbank36_1450_control_expel_only_official_minimal_v1"
        / "run_20260417_234856_control_rules_full_qwen3vl_v1"
        / "study"
        / "2026-04-18_01-45-45_MinimalUITARSAgentLab_on_linkding_xvr_minimal.linkding.1_45_0.1_0"
    )
    study_dir.mkdir(parents=True, exist_ok=True)
    (study_dir / "summary_info.json").write_text(
        json.dumps({"cum_reward": 0.0, "truncated": True}),
        encoding="utf-8",
    )

    rerun_dir = (
        results_root
        / "taskbank36_1450_control_expel_only_official_minimal_v1"
        / "run_20260418_104526_ctrl_rerun"
    )
    rerun_dir.mkdir(parents=True, exist_ok=True)
    (rerun_dir / "uitars_eval_new.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"task_id": 1, "drift_type": "structural", "success": True}),
                json.dumps({"task_id": 2, "drift_type": "functional", "success": True}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    no_rules_dir = (
        results_root
        / "taskbank36_1450_control_no_rules_minimal_v1"
        / "run_20260418_104526_ctrl_rerun"
    )
    no_rules_dir.mkdir(parents=True, exist_ok=True)
    (no_rules_dir / "uitars_eval_new.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"task_id": 1, "drift_type": "structural", "success": False}),
                json.dumps({"task_id": 2, "drift_type": "functional", "success": True}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    old_results_root = module.RESULTS_ROOT
    old_benchmark_specs = module.BENCHMARK_SPECS
    old_scenarios = module.SCENARIOS
    try:
        module.RESULTS_ROOT = results_root
        module.BENCHMARK_SPECS = {
            "taskbank36": {
                "label": "TaskBank36",
                "config_path": config_path,
            }
        }
        module.SCENARIOS = {
            "control_1450": {
                "title": "Control",
                "description": "Control",
                "setting_order": ["no_rules", "expel_only"],
                "benchmarks": {
                    "taskbank36": {
                        "run_label_by_setting": {
                            "no_rules": "taskbank36_1450_control_no_rules_minimal_v1",
                            "expel_only": "taskbank36_1450_control_expel_only_official_minimal_v1",
                        },
                        "run_name_filter": "full_qwen3vl_v1",
                        "allow_partial": True,
                    }
                },
            }
        }

        summary = module.build_summary()
    finally:
        module.RESULTS_ROOT = old_results_root
        module.BENCHMARK_SPECS = old_benchmark_specs
        module.SCENARIOS = old_scenarios

    payload = summary["scenarios"]["control_1450"]["benchmarks"]["taskbank36"]["settings"]["expel_only"]
    assert payload["complete"] is True
    assert payload["completed"] == 2
    assert payload["successes"] == 2
    assert any("run_20260418_104526_ctrl_rerun" in path for path in payload["source_paths"])
