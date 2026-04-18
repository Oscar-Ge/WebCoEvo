#!/usr/bin/env python3

import argparse
import html
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = ROOT / "results"

DRIFT_ORDER = [
    "access",
    "surface",
    "content",
    "structural",
    "functional",
    "runtime",
    "process",
]

DRIFT_LABELS = {
    "access": "Access",
    "surface": "Surface",
    "content": "Content",
    "structural": "Structural",
    "functional": "Functional",
    "runtime": "Runtime",
    "process": "Process",
}

SETTING_LABELS = {
    "no_rules": "No Rules",
    "expel_only": "ExpeL Only",
    "v2_4": "V2.4 XVR",
}

SETTING_COLORS = {
    "no_rules": "#9aa0a6",
    "expel_only": "#f59e0b",
    "v2_4": "#2563eb",
}

BENCHMARK_SPECS = {
    "focus20": {
        "label": "Focus20",
        "config_path": ROOT / "configs" / "focus20_hardv3_full.raw.json",
    },
    "taskbank36": {
        "label": "TaskBank36",
        "config_path": ROOT / "configs" / "taskbank36_hardv3_full.raw.json",
    },
}

SCENARIOS = {
    "control_1450": {
        "title": "Control Linkding 1.45.0: No Rules vs ExpeL",
        "summary_kind": "success",
        "description": (
            "Original Linkding 1.45.0 control site with no cross-version drift. "
            "This comparison isolates the effect of enabling ExpeL rules."
        ),
        "setting_order": ["no_rules", "expel_only"],
        "benchmarks": {
            "focus20": {
                "run_label_by_setting": {
                    "no_rules": "focus20_1450_control_no_rules_minimal_v1",
                    "expel_only": "focus20_1450_control_expel_only_official_minimal_v1",
                },
                "run_name_filter": "full_qwen3vl_v1",
                "allow_partial": False,
            },
            "taskbank36": {
                "run_label_by_setting": {
                    "no_rules": "taskbank36_1450_control_no_rules_minimal_v1",
                    "expel_only": "taskbank36_1450_control_expel_only_official_minimal_v1",
                },
                "run_name_filter": "full_qwen3vl_v1",
                "allow_partial": True,
            },
        },
    },
    "first_modified": {
        "title": "First-Modified Drift: ExpeL vs V2.4",
        "summary_kind": "success",
        "description": (
            "Fresh Linkding drift websites from `websites/first_modified`. "
            "This comparison measures whether V2.4 reflection rules improve on ExpeL alone."
        ),
        "setting_order": ["expel_only", "v2_4"],
        "benchmarks": {
            "focus20": {
                "run_label_by_setting": {
                    "expel_only": "focus20_first_modified_expel_only_official_minimal_v1",
                    "v2_4": "focus20_first_modified_v2_4_expel_official_minimal_v1",
                },
                "run_name_filter": "full_qwen3vl_v1",
                "allow_partial": False,
            },
            "taskbank36": {
                "run_label_by_setting": {
                    "expel_only": "taskbank36_first_modified_expel_only_official_minimal_v1",
                    "v2_4": "taskbank36_first_modified_v2_4_expel_official_minimal_v1",
                },
                "run_name_filter": "full_qwen3vl_v1",
                "allow_partial": False,
            },
        },
    },
}

PROVENANCE = {
    "date": "2026-04-18",
    "model": "Qwen/Qwen3-VL-30B-A3B-Instruct",
    "endpoint": "http://promaxgb10-d668.eecs.umich.edu:8000/v1",
    "agent_mode": "vl_action_reflection",
    "max_steps": 30,
    "max_tokens": 300,
    "control_submit_script": "slurm/submit_control_rules_matrix.sh",
    "first_modified_submit_script": "slurm/submit_first_modified_rules_matrix.sh",
    "control_initial_fail_jobs": "48217988-48217995",
    "control_smoke_retry_jobs": "48218424, 48218426, 48218428, 48218430",
    "control_full_jobs": "48219141, 48219143, 48219145, 48219147",
    "first_modified_initial_fail_jobs": "48217989-48217995",
    "first_modified_access_smoke_retry_jobs": "48218425, 48218427, 48218429, 48218431",
    "first_modified_full_jobs": "the fm* jobs from 48219140 through 48219163",
    "taskbank36_control_no_rules_timeout": "Job 48219145 hit the 02:00:00 Slurm time limit at 2026-04-18T02:45:35.",
    "taskbank36_control_expel_timeout": "Job 48219147 hit the 02:00:00 Slurm time limit at 2026-04-18T03:44:43.",
}

RUN_PATH_RE = re.compile(
    r"/(?P<run_label>[^/]+)/(?:shard_(?P<shard>[^/]+)/)?(?P<run>run_[^/]+)/uitars_eval_[^/]+\.jsonl$"
)
STUDY_TASK_RE = re.compile(r"\.(?P<task_id>\d+)_\d+$")


def load_task_metadata():
    metadata = {}
    for benchmark_key, spec in BENCHMARK_SPECS.items():
        with spec["config_path"].open(encoding="utf-8") as handle:
            tasks = json.load(handle)
        task_map = {}
        expected_by_drift = {}
        for row in tasks:
            task_id = int(row["task_id"])
            drift = normalize_drift(row.get("drift_type") or row.get("variant"))
            task_map[task_id] = drift
            expected_by_drift[drift] = expected_by_drift.get(drift, 0) + 1
        for drift in DRIFT_ORDER:
            expected_by_drift.setdefault(drift, 0)
        metadata[benchmark_key] = {
            "label": spec["label"],
            "expected_total": len(tasks),
            "expected_by_drift": expected_by_drift,
            "task_map": task_map,
        }
    return metadata


def discover_latest_eval_paths(run_label, run_name_filter):
    root = RESULTS_ROOT / run_label
    if not root.exists():
        return []
    latest = {}
    for path in root.rglob("uitars_eval_*.jsonl"):
        match = RUN_PATH_RE.search(path.as_posix())
        if not match:
            continue
        run_name = match.group("run")
        if run_name_filter and run_name_filter not in run_name:
            continue
        shard = match.group("shard") or "__single__"
        current = latest.get(shard)
        if current is None or run_name > current[0]:
            latest[shard] = (run_name, path)
    paths = [latest[key][1] for key in sorted(latest)]
    return paths


def discover_latest_run_dir(run_label, run_name_filter):
    root = RESULTS_ROOT / run_label
    if not root.exists():
        return None
    candidates = []
    for path in root.iterdir():
        if not path.is_dir():
            continue
        if not path.name.startswith("run_"):
            continue
        if run_name_filter and run_name_filter not in path.name:
            continue
        candidates.append(path)
    if not candidates:
        return None
    return sorted(candidates)[-1]


def aggregate_from_eval(paths, benchmark_meta):
    payload = empty_payload(benchmark_meta)
    seen_tasks = set()
    for path in paths:
        payload["source_paths"].append(str(path))
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                task_id = row.get("task_id")
                drift = normalize_drift(row.get("drift_type") or row.get("variant"))
                seen_tasks.add(task_id)
                payload["completed"] += 1
                payload["by_drift"][drift]["completed"] += 1
                if row.get("success"):
                    payload["successes"] += 1
                    payload["by_drift"][drift]["successes"] += 1
    payload["unique_tasks"] = len(seen_tasks)
    finalize_payload(payload, benchmark_meta, status="complete" if payload["completed"] == benchmark_meta["expected_total"] else "partial")
    return payload


def aggregate_from_study(run_dir, benchmark_meta):
    payload = empty_payload(benchmark_meta)
    payload["study_run_dir"] = str(run_dir)
    seen_tasks = set()
    for path in run_dir.rglob("summary_info.json"):
        match = STUDY_TASK_RE.search(path.parent.name)
        if not match:
            continue
        task_id = int(match.group("task_id"))
        drift = benchmark_meta["task_map"].get(task_id)
        if drift is None or task_id in seen_tasks:
            continue
        seen_tasks.add(task_id)
        payload["source_paths"].append(str(path))
        with path.open(encoding="utf-8") as handle:
            row = json.load(handle)
        payload["completed"] += 1
        payload["by_drift"][drift]["completed"] += 1
        if float(row.get("cum_reward", 0.0)) >= 1.0:
            payload["successes"] += 1
            payload["by_drift"][drift]["successes"] += 1
        if row.get("truncated"):
            payload["truncated"] += 1
            payload["by_drift"][drift]["truncated"] += 1
    payload["unique_tasks"] = len(seen_tasks)
    finalize_payload(payload, benchmark_meta, status="partial")
    return payload


def empty_payload(benchmark_meta):
    return {
        "completed": 0,
        "successes": 0,
        "truncated": 0,
        "unique_tasks": 0,
        "expected_total": benchmark_meta["expected_total"],
        "expected_by_drift": dict(benchmark_meta["expected_by_drift"]),
        "source_paths": [],
        "by_drift": {
            drift: {"completed": 0, "successes": 0, "truncated": 0}
            for drift in DRIFT_ORDER
        },
    }


def finalize_payload(payload, benchmark_meta, status):
    payload["status"] = status
    payload["complete"] = payload["completed"] == benchmark_meta["expected_total"]
    payload["final_success_rate_available"] = payload["complete"]
    payload["completion_rate"] = safe_divide(payload["completed"], benchmark_meta["expected_total"])
    payload["lower_bound_rate"] = safe_divide(payload["successes"], benchmark_meta["expected_total"])
    payload["overall_rate"] = (
        safe_divide(payload["successes"], benchmark_meta["expected_total"])
        if payload["complete"]
        else None
    )
    payload["observed_success_rate"] = safe_divide(payload["successes"], payload["completed"])
    for drift in DRIFT_ORDER:
        expected = benchmark_meta["expected_by_drift"][drift]
        drift_payload = payload["by_drift"][drift]
        drift_payload["expected"] = expected
        drift_payload["completion_rate"] = safe_divide(drift_payload["completed"], expected)
        drift_payload["rate"] = safe_divide(drift_payload["successes"], expected)
        drift_payload["observed_success_rate"] = safe_divide(
            drift_payload["successes"], drift_payload["completed"]
        )


def build_summary():
    task_metadata = load_task_metadata()
    summary = {
        "report_date": PROVENANCE["date"],
        "model": PROVENANCE["model"],
        "endpoint": PROVENANCE["endpoint"],
        "agent_mode": PROVENANCE["agent_mode"],
        "max_steps": PROVENANCE["max_steps"],
        "max_tokens": PROVENANCE["max_tokens"],
        "scenarios": {},
        "provenance": PROVENANCE,
    }
    for scenario_key in sorted(SCENARIOS):
        scenario_spec = SCENARIOS[scenario_key]
        scenario_payload = {
            "title": scenario_spec["title"],
            "description": scenario_spec["description"],
            "setting_order": list(scenario_spec["setting_order"]),
            "benchmarks": {},
        }
        for benchmark_key in sorted(scenario_spec["benchmarks"]):
            benchmark_spec = scenario_spec["benchmarks"][benchmark_key]
            benchmark_meta = task_metadata[benchmark_key]
            benchmark_payload = {
                "label": benchmark_meta["label"],
                "expected_total": benchmark_meta["expected_total"],
                "expected_by_drift": dict(benchmark_meta["expected_by_drift"]),
                "settings": {},
            }
            for setting in scenario_spec["setting_order"]:
                run_label = benchmark_spec["run_label_by_setting"][setting]
                eval_paths = discover_latest_eval_paths(run_label, benchmark_spec["run_name_filter"])
                if eval_paths:
                    setting_payload = aggregate_from_eval(eval_paths, benchmark_meta)
                else:
                    if not benchmark_spec.get("allow_partial"):
                        raise RuntimeError(
                            "Missing eval files for %s / %s / %s"
                            % (scenario_key, benchmark_key, setting)
                        )
                    run_dir = discover_latest_run_dir(run_label, benchmark_spec["run_name_filter"])
                    if run_dir is None:
                        raise RuntimeError(
                            "Missing run directory for %s / %s / %s"
                            % (scenario_key, benchmark_key, setting)
                        )
                    setting_payload = aggregate_from_study(run_dir, benchmark_meta)
                setting_payload["label"] = SETTING_LABELS[setting]
                setting_payload["run_label"] = run_label
                benchmark_payload["settings"][setting] = setting_payload
            benchmark_payload["all_complete"] = all(
                benchmark_payload["settings"][setting]["complete"]
                for setting in scenario_spec["setting_order"]
            )
            scenario_payload["benchmarks"][benchmark_key] = benchmark_payload
        summary["scenarios"][scenario_key] = scenario_payload
    return summary


def write_report_assets(summary, figure_dir, report_dir, report_filename):
    figure_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    figure_paths = {}
    figure_paths["control_1450_focus20"] = write_figure(
        figure_dir / "focus20_control_rules_success.svg",
        render_success_figure_svg(
            "Focus20 Control 1.45.0: No Rules vs ExpeL",
            "Overall success rate and per-drift success rate on the original Linkding 1.45.0 site.",
            summary["scenarios"]["control_1450"]["setting_order"],
            summary["scenarios"]["control_1450"]["benchmarks"]["focus20"],
        ),
        report_dir,
    )
    figure_paths["control_1450_taskbank36_status"] = write_figure(
        figure_dir / "taskbank36_control_rules_status.svg",
        render_partial_status_figure_svg(
            "TaskBank36 Control 1.45.0: Run Status",
            "Full baseline runs were interrupted by the 02:00:00 Slurm time limit; completion is shown instead of final success rate.",
            summary["scenarios"]["control_1450"]["setting_order"],
            summary["scenarios"]["control_1450"]["benchmarks"]["taskbank36"],
        ),
        report_dir,
    )
    figure_paths["first_modified_focus20"] = write_figure(
        figure_dir / "focus20_first_modified_rules_success.svg",
        render_success_figure_svg(
            "Focus20 First-Modified: ExpeL vs V2.4",
            "Overall success rate and per-drift success rate on `websites/first_modified`.",
            summary["scenarios"]["first_modified"]["setting_order"],
            summary["scenarios"]["first_modified"]["benchmarks"]["focus20"],
        ),
        report_dir,
    )
    figure_paths["first_modified_taskbank36"] = write_figure(
        figure_dir / "taskbank36_first_modified_rules_success.svg",
        render_success_figure_svg(
            "TaskBank36 First-Modified: ExpeL vs V2.4",
            "Held-out TaskBank36 success rate on `websites/first_modified`.",
            summary["scenarios"]["first_modified"]["setting_order"],
            summary["scenarios"]["first_modified"]["benchmarks"]["taskbank36"],
        ),
        report_dir,
    )

    report_path = report_dir / report_filename
    report_path.write_text(
        render_markdown_report(summary, figure_paths, report_dir),
        encoding="utf-8",
    )

    summary_path = report_dir / "2026-04-18-umich-qwen3-rule-comparison-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "report_path": str(report_path),
        "summary_path": str(summary_path),
        "figure_paths": figure_paths,
    }


def write_figure(path, content, report_dir):
    path.write_text(content, encoding="utf-8")
    return os.path.relpath(path, start=report_dir)


def render_markdown_report(summary, figure_paths, report_dir):
    control_focus20 = summary["scenarios"]["control_1450"]["benchmarks"]["focus20"]
    control_taskbank = summary["scenarios"]["control_1450"]["benchmarks"]["taskbank36"]
    first_focus20 = summary["scenarios"]["first_modified"]["benchmarks"]["focus20"]
    first_taskbank = summary["scenarios"]["first_modified"]["benchmarks"]["taskbank36"]
    access_asset = os.path.relpath(
        ROOT / "websites" / "first_modified" / "report" / "assets" / "access_before_after.png",
        start=report_dir,
    )
    structural_asset = os.path.relpath(
        ROOT / "websites" / "first_modified" / "report" / "assets" / "structural_before_after.png",
        start=report_dir,
    )
    lines = [
        "# UMich Qwen3-VL Linkding Rules Comparison Report",
        "",
        "> Generated on April 18, 2026 from the latest completed Slurm jobs under `WebCoEvo/results/`.",
        "",
        "## Executive Summary",
        "",
        "- On the control Linkding 1.45.0 Focus20 benchmark, `ExpeL Only` improves from `%s` to `%s` (`%+.1f` points)."
        % (
            format_ratio_line(control_focus20["settings"]["no_rules"], control_focus20["expected_total"]),
            format_ratio_line(control_focus20["settings"]["expel_only"], control_focus20["expected_total"]),
            delta_points(
                control_focus20["settings"]["expel_only"]["overall_rate"],
                control_focus20["settings"]["no_rules"]["overall_rate"],
            ),
        ),
        "- On `websites/first_modified`, `V2.4 XVR` improves over `ExpeL Only` on both Focus20 (`%s` to `%s`) and TaskBank36 (`%s` to `%s`)."
        % (
            format_ratio_line(first_focus20["settings"]["expel_only"], first_focus20["expected_total"]),
            format_ratio_line(first_focus20["settings"]["v2_4"], first_focus20["expected_total"]),
            format_ratio_line(first_taskbank["settings"]["expel_only"], first_taskbank["expected_total"]),
            format_ratio_line(first_taskbank["settings"]["v2_4"], first_taskbank["expected_total"]),
        ),
        "- The full TaskBank36 control baselines are not available: jobs `48219145` and `48219147` were canceled at the Slurm time limit, so the report separates completed success-rate results from incomplete run-status evidence.",
        "",
        "## Evaluation Setup",
        "",
        "- Model: `%s`" % summary["model"],
        "- Endpoint: `%s`" % summary["endpoint"],
        "- Agent mode: `%s`" % summary["agent_mode"],
        "- Budget: `MAX_STEPS=%d`, `MAX_TOKENS=%d`" % (summary["max_steps"], summary["max_tokens"]),
        "- Control submitter: `%s` uses `SBATCH_TIME=02:00:00`." % summary["provenance"]["control_submit_script"],
        "- First-modified submitter: `%s` uses `SBATCH_TIME=04:00:00`." % summary["provenance"]["first_modified_submit_script"],
        "",
        "## Slurm Provenance",
        "",
        "| Matrix | Key Slurm jobs | Notes |",
        "| --- | --- | --- |",
        "| Control 1.45.0 | `%s` (initial smoke failure), `%s` (smoke retry), `%s` (full) | Initial smoke jobs failed because `/home/gecm/WebCoEvo/.venv/bin/python` was not executable. |"
        % (
            summary["provenance"]["control_initial_fail_jobs"],
            summary["provenance"]["control_smoke_retry_jobs"],
            summary["provenance"]["control_full_jobs"],
        ),
        "| First-modified | `%s` (initial/access smoke), `%s` (full) | The longer 04:00:00 time budget was sufficient for the full first-modified matrix. |"
        % (
            summary["provenance"]["first_modified_access_smoke_retry_jobs"],
            summary["provenance"]["first_modified_full_jobs"],
        ),
        "",
        "## Matrix A: Control Linkding 1.45.0 (`No Rules` vs `ExpeL Only`)",
        "",
        "### Focus20",
        "",
        "![Focus20 control rules success](%s)" % figure_paths["control_1450_focus20"],
        "",
        "On the original Linkding 1.45.0 Focus20 benchmark, adding ExpeL rules raises success from `%s` to `%s`."
        % (
            format_ratio_line(control_focus20["settings"]["no_rules"], control_focus20["expected_total"]),
            format_ratio_line(control_focus20["settings"]["expel_only"], control_focus20["expected_total"]),
        ),
        "The strongest per-drift gains are on `access` (`0/13` to `13/13`), `process` (`1/6` to `6/6`), and `runtime` (`2/16` to `13/16`). The main non-improving family is `structural`, which stays at `2/6` even with ExpeL enabled.",
        "",
        render_success_table(control_focus20, ["no_rules", "expel_only"]),
        "",
        "### TaskBank36",
        "",
        "![TaskBank36 control rules status](%s)" % figure_paths["control_1450_taskbank36_status"],
        "",
        "The full TaskBank36 control baselines did not finish before the Slurm time limit. Job `48219145` (`No Rules`) stopped at `2026-04-18T02:45:35`, and job `48219147` (`ExpeL Only`) stopped at `2026-04-18T03:44:43`.",
        "This means the report cannot claim final TaskBank36 control success rates. Instead, it reports completion coverage and observed success on the completed subset only.",
        "",
        render_partial_status_table(control_taskbank, ["no_rules", "expel_only"]),
        "",
        "Observed completion bias is non-uniform: the `ExpeL Only` run never reached the `structural` or `functional` tail of the task order, so its observed subset should not be read as a benchmark-level win or loss.",
        "",
        "## Matrix B: `websites/first_modified` (`ExpeL Only` vs `V2.4 XVR`)",
        "",
        "### Visual Context",
        "",
        "The figures below come from the existing `websites/first_modified/report/assets/` gallery and illustrate two of the drift patterns that the rules must handle.",
        "",
        "![First-modified access before/after](%s)" % access_asset,
        "",
        "![First-modified structural before/after](%s)" % structural_asset,
        "",
        "### Focus20",
        "",
        "![Focus20 first-modified rules success](%s)" % figure_paths["first_modified_focus20"],
        "",
        "On first-modified Focus20, `V2.4 XVR` improves on `ExpeL Only` from `%s` to `%s` (`%+.1f` points)."
        % (
            format_ratio_line(first_focus20["settings"]["expel_only"], first_focus20["expected_total"]),
            format_ratio_line(first_focus20["settings"]["v2_4"], first_focus20["expected_total"]),
            delta_points(
                first_focus20["settings"]["v2_4"]["overall_rate"],
                first_focus20["settings"]["expel_only"]["overall_rate"],
            ),
        ),
        "The remaining ExpeL-only errors are concentrated in `content`, `runtime`, and `structural`; V2.4 closes almost all of them and reaches `67/68` overall.",
        "",
        render_success_table(first_focus20, ["expel_only", "v2_4"]),
        "",
        "### TaskBank36",
        "",
        "![TaskBank36 first-modified rules success](%s)" % figure_paths["first_modified_taskbank36"],
        "",
        "On held-out TaskBank36 under first-modified drift, `V2.4 XVR` improves over `ExpeL Only` from `%s` to `%s` (`%+.1f` points)."
        % (
            format_ratio_line(first_taskbank["settings"]["expel_only"], first_taskbank["expected_total"]),
            format_ratio_line(first_taskbank["settings"]["v2_4"], first_taskbank["expected_total"]),
            delta_points(
                first_taskbank["settings"]["v2_4"]["overall_rate"],
                first_taskbank["settings"]["expel_only"]["overall_rate"],
            ),
        ),
        "The largest held-out gains are on `runtime` (`16/36` to `30/36`), `structural` (`9/13` to `13/13`), and `access` (`27/36` to `33/36`). The only regression is `content`, which drops slightly from `9/14` to `8/14`.",
        "",
        render_success_table(first_taskbank, ["expel_only", "v2_4"]),
        "",
        "## Cross-Matrix Interpretation",
        "",
        "Three conclusions are stable in the completed data. First, ExpeL rules alone already provide a large gain on the original Focus20 control site (`13.2%` to `82.4%`). Second, on first-modified websites, ExpeL is already strong (`88.2%` on Focus20 and `68.3%` on TaskBank36), but V2.4 still adds clear headroom. Third, the first-modified V2.4 gains are broad rather than isolated: they improve `access`, `runtime`, `structural`, `functional`, and `surface`, while leaving only `content` as a mild negative-transfer pocket on TaskBank36.",
        "",
        "## Paper-Style Result Snippets",
        "",
        "- Control Focus20: `On the original Linkding 1.45.0 control site, enabling ExpeL rules raises Focus20 success from 9/68 (13.2%) to 56/68 (82.4%), with the largest gains on access, process, and runtime tasks.`",
        "- First-modified Focus20: `On the first-modified drift suite, the V2.4 reflection rulebook improves Focus20 success from 60/68 (88.2%) to 67/68 (98.5%), nearly closing the remaining gap after ExpeL-only transfer.`",
        "- First-modified TaskBank36: `On held-out TaskBank36 under first-modified drift, V2.4 improves over ExpeL-only from 114/167 (68.3%) to 143/167 (85.6%), with especially strong gains on runtime, structural, and access tasks.`",
        "",
        "## Appendix A: Per-Drift Tables",
        "",
        "### Control Focus20",
        "",
        render_complete_per_drift_table(control_focus20, ["no_rules", "expel_only"]),
        "",
        "### First-Modified Focus20",
        "",
        render_complete_per_drift_table(first_focus20, ["expel_only", "v2_4"]),
        "",
        "### First-Modified TaskBank36",
        "",
        render_complete_per_drift_table(first_taskbank, ["expel_only", "v2_4"]),
        "",
        "### Control TaskBank36 Partial Coverage",
        "",
        render_partial_per_drift_table(control_taskbank, ["no_rules", "expel_only"]),
    ]
    return "\n".join(lines).rstrip() + "\n"


def render_success_table(benchmark_payload, setting_order):
    baseline = benchmark_payload["settings"][setting_order[0]]["overall_rate"]
    lines = [
        "| Setting | Success / Total | Success Rate | Delta vs First Setting |",
        "| --- | ---: | ---: | ---: |",
    ]
    for index, setting in enumerate(setting_order):
        payload = benchmark_payload["settings"][setting]
        delta = "—" if index == 0 else "%+.1f pts" % delta_points(payload["overall_rate"], baseline)
        lines.append(
            "| %s | %d/%d | %s | %s |"
            % (
                SETTING_LABELS[setting],
                payload["successes"],
                benchmark_payload["expected_total"],
                format_percent(payload["overall_rate"]),
                delta,
            )
        )
    return "\n".join(lines)


def render_partial_status_table(benchmark_payload, setting_order):
    lines = [
        "| Setting | Completed / Total | Completion Rate | Successes on Completed Tasks | Observed Success Rate |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for setting in setting_order:
        payload = benchmark_payload["settings"][setting]
        lines.append(
            "| %s | %d/%d | %s | %d/%d | %s |"
            % (
                SETTING_LABELS[setting],
                payload["completed"],
                benchmark_payload["expected_total"],
                format_percent(payload["completion_rate"]),
                payload["successes"],
                payload["completed"],
                format_percent(payload["observed_success_rate"]),
            )
        )
    return "\n".join(lines)


def render_complete_per_drift_table(benchmark_payload, setting_order):
    lines = ["| Drift | n | %s | %s |" % tuple(SETTING_LABELS[setting] for setting in setting_order)]
    lines.append("| --- | ---: | ---: | ---: |")
    for drift in DRIFT_ORDER:
        row = [DRIFT_LABELS[drift], str(benchmark_payload["expected_by_drift"][drift])]
        for setting in setting_order:
            payload = benchmark_payload["settings"][setting]["by_drift"][drift]
            row.append("%d/%d (%s)" % (payload["successes"], payload["expected"], format_percent(payload["rate"])))
        lines.append("| %s |" % " | ".join(row))
    return "\n".join(lines)


def render_partial_per_drift_table(benchmark_payload, setting_order):
    lines = [
        "| Drift | n | No Rules completion | No Rules observed success | ExpeL completion | ExpeL observed success |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for drift in DRIFT_ORDER:
        no_rules = benchmark_payload["settings"]["no_rules"]["by_drift"][drift]
        expel_only = benchmark_payload["settings"]["expel_only"]["by_drift"][drift]
        lines.append(
            "| %s | %d | %d/%d (%s) | %d/%d (%s) | %d/%d (%s) | %d/%d (%s) |"
            % (
                DRIFT_LABELS[drift],
                benchmark_payload["expected_by_drift"][drift],
                no_rules["completed"],
                no_rules["expected"],
                format_percent(no_rules["completion_rate"]),
                no_rules["successes"],
                no_rules["completed"],
                format_percent(no_rules["observed_success_rate"]),
                expel_only["completed"],
                expel_only["expected"],
                format_percent(expel_only["completion_rate"]),
                expel_only["successes"],
                expel_only["completed"],
                format_percent(expel_only["observed_success_rate"]),
            )
        )
    return "\n".join(lines)


def render_success_figure_svg(title, subtitle, setting_order, benchmark_payload):
    return render_two_panel_figure_svg(
        title=title,
        subtitle=subtitle,
        setting_order=setting_order,
        benchmark_payload=benchmark_payload,
        mode="success",
    )


def render_partial_status_figure_svg(title, subtitle, setting_order, benchmark_payload):
    return render_two_panel_figure_svg(
        title=title,
        subtitle=subtitle,
        setting_order=setting_order,
        benchmark_payload=benchmark_payload,
        mode="completion",
    )


def render_two_panel_figure_svg(title, subtitle, setting_order, benchmark_payload, mode):
    width = 1280
    height = 620
    left_panel_x = 80
    left_panel_y = 170
    chart_height = 320
    left_panel_width = 820
    panel_gap = 70
    right_panel_x = left_panel_x + left_panel_width + panel_gap
    right_panel_width = 230
    divider_x = left_panel_x + left_panel_width + panel_gap // 2
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (
            width,
            height,
            width,
            height,
        ),
        "<style>",
        ".title { font: 700 28px 'Helvetica Neue', Arial, sans-serif; fill: #111827; }",
        ".subtitle { font: 400 15px 'Helvetica Neue', Arial, sans-serif; fill: #4b5563; }",
        ".panel-title { font: 700 16px 'Helvetica Neue', Arial, sans-serif; fill: #111827; }",
        ".axis { font: 12px 'Helvetica Neue', Arial, sans-serif; fill: #374151; }",
        ".axis-muted { font: 11px 'Helvetica Neue', Arial, sans-serif; fill: #6b7280; }",
        ".legend { font: 13px 'Helvetica Neue', Arial, sans-serif; fill: #1f2937; }",
        ".value { font: 12px 'Helvetica Neue', Arial, sans-serif; fill: #111827; }",
        "</style>",
        '<rect width="100%%" height="100%%" fill="#ffffff"/>',
        '<text x="80" y="52" class="title">%s</text>' % escape(title),
        '<text x="80" y="78" class="subtitle">%s</text>' % escape(subtitle),
        '<text x="80" y="104" class="subtitle">Left: per-drift rates. Right: benchmark-level overall summary.</text>',
        render_legend(80, 130, setting_order),
        '<line x1="%d" y1="150" x2="%d" y2="560" stroke="#e5e7eb" stroke-width="2"/>' % (
            divider_x,
            divider_x,
        ),
        '<text x="%d" y="150" class="panel-title">Per-Drift</text>' % left_panel_x,
        '<text x="%d" y="150" class="panel-title">Overall</text>' % right_panel_x,
    ]
    parts.extend(render_chart_axes(left_panel_x, left_panel_y, left_panel_width, chart_height))
    parts.extend(render_chart_axes(right_panel_x, left_panel_y, right_panel_width, chart_height))
    parts.extend(
        render_drift_panel(
            benchmark_payload,
            setting_order=setting_order,
            left_panel_x=left_panel_x,
            left_panel_y=left_panel_y,
            left_panel_width=left_panel_width,
            chart_height=chart_height,
            mode=mode,
        )
    )
    parts.extend(
        render_overall_panel(
            benchmark_payload,
            setting_order=setting_order,
            right_panel_x=right_panel_x,
            left_panel_y=left_panel_y,
            right_panel_width=right_panel_width,
            chart_height=chart_height,
            mode=mode,
        )
    )
    note = (
        "Rates are final success rates."
        if mode == "success"
        else "Bars show completion coverage; observed success among completed tasks is printed above each bar."
    )
    parts.append('<text x="80" y="590" class="axis-muted">%s</text>' % escape(note))
    parts.append("</svg>")
    return "\n".join(parts)


def render_legend(x, y, setting_order):
    cursor_x = x
    parts = []
    for setting in setting_order:
        label = SETTING_LABELS[setting]
        color = SETTING_COLORS[setting]
        parts.append(
            '<rect x="%d" y="%d" width="14" height="14" rx="3" fill="%s"/>' % (cursor_x, y - 11, color)
        )
        parts.append(
            '<text x="%d" y="%d" class="legend">%s</text>'
            % (cursor_x + 22, y, escape(label))
        )
        cursor_x += 22 + len(label) * 8 + 36
    return "\n".join(parts)


def render_chart_axes(x, y, width, height):
    bottom = y + height
    parts = [
        '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#111827" stroke-width="1.5"/>'
        % (x, bottom, x + width, bottom),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#111827" stroke-width="1.5"/>'
        % (x, y, x, bottom),
    ]
    for tick in (0, 25, 50, 75, 100):
        tick_y = bottom - int(height * tick / 100.0)
        parts.append(
            '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#e5e7eb" stroke-width="1"/>'
            % (x, tick_y, x + width, tick_y)
        )
        parts.append(
            '<text x="%d" y="%d" class="axis" text-anchor="end">%d%%</text>'
            % (x - 10, tick_y + 4, tick)
        )
    return parts


def render_drift_panel(benchmark_payload, setting_order, left_panel_x, left_panel_y, left_panel_width, chart_height, mode):
    chart_bottom = left_panel_y + chart_height
    group_width = float(left_panel_width) / float(len(DRIFT_ORDER))
    bar_width = 26
    bar_gap = 10
    inner_width = len(setting_order) * bar_width + (len(setting_order) - 1) * bar_gap
    parts = []
    for index, drift in enumerate(DRIFT_ORDER):
        group_x = left_panel_x + index * group_width
        start_x = group_x + (group_width - inner_width) / 2.0
        parts.extend(
            multiline_text(
                int(group_x + group_width / 2.0),
                chart_bottom + 28,
                [DRIFT_LABELS[drift], "n=%d" % benchmark_payload["expected_by_drift"][drift]],
                "axis",
            )
        )
        for setting_index, setting in enumerate(setting_order):
            payload = benchmark_payload["settings"][setting]["by_drift"][drift]
            rate = payload["rate"] if mode == "success" else payload["completion_rate"]
            bar_height = chart_height * rate
            x = start_x + setting_index * (bar_width + bar_gap)
            y = chart_bottom - bar_height
            parts.append(
                '<rect x="%.1f" y="%.1f" width="%d" height="%.1f" rx="4" fill="%s"/>'
                % (x, y, bar_width, bar_height, SETTING_COLORS[setting])
            )
    return parts


def render_overall_panel(benchmark_payload, setting_order, right_panel_x, left_panel_y, right_panel_width, chart_height, mode):
    chart_bottom = left_panel_y + chart_height
    bar_width = 44
    bar_gap = 26
    total_width = len(setting_order) * bar_width + (len(setting_order) - 1) * bar_gap
    start_x = right_panel_x + (right_panel_width - total_width) / 2.0
    parts = []
    for index, setting in enumerate(setting_order):
        payload = benchmark_payload["settings"][setting]
        rate = payload["overall_rate"] if mode == "success" else payload["completion_rate"]
        bar_height = chart_height * rate
        x = start_x + index * (bar_width + bar_gap)
        y = chart_bottom - bar_height
        parts.append(
            '<rect x="%.1f" y="%.1f" width="%d" height="%.1f" rx="5" fill="%s"/>'
            % (x, y, bar_width, bar_height, SETTING_COLORS[setting])
        )
        parts.append(
            '<text x="%.1f" y="%.1f" class="value" text-anchor="middle">%s</text>'
            % (x + bar_width / 2.0, y - 8, escape(format_percent(rate)))
        )
        if mode == "completion":
            observed = "%d/%d = %s" % (
                payload["successes"],
                payload["completed"],
                format_percent(payload["observed_success_rate"]),
            )
            parts.extend(multiline_text(int(x + bar_width / 2.0), y - 32, ["obs.", observed], "axis-muted"))
        label_lines = [SETTING_LABELS[setting]]
        if setting == "expel_only":
            label_lines = ["ExpeL", "Only"]
        elif setting == "no_rules":
            label_lines = ["No", "Rules"]
        elif setting == "v2_4":
            label_lines = ["V2.4", "XVR"]
        parts.extend(multiline_text(int(x + bar_width / 2.0), chart_bottom + 28, label_lines, "axis"))
    return parts


def multiline_text(x, y, lines, css_class):
    parts = ['<text x="%d" y="%d" class="%s" text-anchor="middle">' % (x, y, css_class)]
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else 15
        parts.append('<tspan x="%d" dy="%d">%s</tspan>' % (x, dy, escape(line)))
    parts.append("</text>")
    return parts


def normalize_drift(value):
    text = str(value)
    if text in DRIFT_ORDER:
        return text
    if text in ("structural_functional", "structural"):
        return "structural"
    if text in ("runtime_process", "runtime"):
        return "runtime"
    return "process"


def safe_divide(numerator, denominator):
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)


def format_percent(rate):
    return "%.1f%%" % (rate * 100.0)


def delta_points(current, baseline):
    return (current - baseline) * 100.0


def escape(text):
    return html.escape(str(text), quote=True)


def format_ratio_line(setting_payload, total):
    return "%d/%d = %s" % (
        setting_payload["successes"],
        total,
        format_percent(setting_payload["overall_rate"]),
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate the UMich Qwen3-VL Linkding rules comparison report."
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=ROOT / "figures",
        help="Output directory for generated SVG figures.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=ROOT / "docs" / "reports",
        help="Output directory for the Markdown report and JSON summary.",
    )
    parser.add_argument(
        "--report-filename",
        default="2026-04-18-umich-qwen3-rule-comparison-report.md",
        help="Markdown filename for the generated report.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    summary = build_summary()
    outputs = write_report_assets(
        summary=summary,
        figure_dir=args.figure_dir.resolve(),
        report_dir=args.report_dir.resolve(),
        report_filename=args.report_filename,
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
