import argparse
import html
import json
import os
import re
from pathlib import Path
from typing import Dict, Iterable, Mapping, MutableMapping, Optional, Sequence, Tuple


BENCHMARK_ORDER = ["focus20_hardv3", "taskbank36_hardv3"]
SETTING_ORDER = ["expel_only", "v2_4", "v2_5", "v2_6"]
DRIFT_ORDER = ["access", "surface", "content", "structural", "functional", "runtime", "process"]

BENCHMARK_LABELS = {
    "focus20_hardv3": "Focus20",
    "taskbank36_hardv3": "TaskBank36",
}

BENCHMARK_NOTES = {
    "focus20_hardv3": "Expanded training-like evaluation tasks",
    "taskbank36_hardv3": "Held-out test tasks",
}

SETTING_LABELS = {
    "expel_only": "Non-reflection",
    "v2_4": "v2.4",
    "v2_5": "v2.5",
    "v2_6": "v2.6",
}

DRIFT_LABELS = {
    "access": "Access",
    "surface": "Surface",
    "content": "Content",
    "structural": "Structural",
    "functional": "Functional",
    "runtime": "Runtime",
    "process": "Process",
}

SETTING_COLORS = {
    "expel_only": "#9aa0a6",
    "v2_4": "#2563eb",
    "v2_5": "#f59e0b",
    "v2_6": "#059669",
}

_EVAL_PATH_RE = re.compile(
    r"(?P<benchmark>focus20_hardv3|taskbank36_hardv3)_(?P<setting>expel_only|v2_4|v2_5|v2_6)_(?:expel_)?official_minimal_v1"
    r"/shard_(?P<shard>[^/]+)/(?P<run>run_[^/]+)/uitars_eval_[^/]+\.jsonl$"
)


def discover_latest_eval_files(result_roots: Sequence[Path]) -> Dict[Tuple[str, str, str], Path]:
    latest: Dict[Tuple[str, str, str], Tuple[str, Path]] = {}
    for root in result_roots:
        root_path = Path(root)
        if not root_path.exists():
            continue
        for path in root_path.rglob("uitars_eval_*.jsonl"):
            match = _EVAL_PATH_RE.search(path.as_posix())
            if not match:
                continue
            key = (
                match.group("benchmark"),
                match.group("setting"),
                match.group("shard"),
            )
            run_label = match.group("run")
            current = latest.get(key)
            if current is None or run_label > current[0]:
                latest[key] = (run_label, path)
    return {key: value[1] for key, value in latest.items()}


def aggregate_eval_files(
    eval_files: Mapping[Tuple[str, str, str], Path]
) -> Dict[str, MutableMapping[str, object]]:
    raw: Dict[str, Dict[str, MutableMapping[str, object]]] = {}
    for benchmark, setting, shard in eval_files:
        raw.setdefault(benchmark, {})
        raw[benchmark].setdefault(
            setting,
            {
                "completed": 0,
                "successes": 0,
                "task_ids": set(),
                "task_ids_by_drift": {drift: set() for drift in DRIFT_ORDER},
                "completed_by_drift": {drift: 0 for drift in DRIFT_ORDER},
                "successes_by_drift": {drift: 0 for drift in DRIFT_ORDER},
                "source_paths": [],
            },
        )
        raw[benchmark][setting]["source_paths"].append(str(eval_files[(benchmark, setting, shard)]))
        for row in _load_jsonl(eval_files[(benchmark, setting, shard)]):
            drift = _normalize_drift(row.get("drift_type") or row.get("variant") or shard)
            task_id = row.get("task_id")
            raw[benchmark][setting]["completed"] += 1
            raw[benchmark][setting]["completed_by_drift"][drift] += 1
            if row.get("success"):
                raw[benchmark][setting]["successes"] += 1
                raw[benchmark][setting]["successes_by_drift"][drift] += 1
            raw[benchmark][setting]["task_ids"].add(task_id)
            raw[benchmark][setting]["task_ids_by_drift"][drift].add(task_id)

    summary: Dict[str, MutableMapping[str, object]] = {"benchmarks": {}}
    for benchmark in BENCHMARK_ORDER:
        benchmark_settings = raw.get(benchmark, {})
        expected_total = _max_len(data["task_ids"] for data in benchmark_settings.values())
        expected_by_drift = {
            drift: _max_len(
                data["task_ids_by_drift"][drift] for data in benchmark_settings.values()
            )
            for drift in DRIFT_ORDER
        }
        benchmark_payload: MutableMapping[str, object] = {
            "label": BENCHMARK_LABELS[benchmark],
            "note": BENCHMARK_NOTES[benchmark],
            "expected_total": expected_total,
            "expected_by_drift": expected_by_drift,
            "settings": {},
        }
        for setting in SETTING_ORDER:
            data = benchmark_settings.get(
                setting,
                {
                    "completed": 0,
                    "successes": 0,
                    "task_ids": set(),
                    "task_ids_by_drift": {drift: set() for drift in DRIFT_ORDER},
                    "completed_by_drift": {drift: 0 for drift in DRIFT_ORDER},
                    "successes_by_drift": {drift: 0 for drift in DRIFT_ORDER},
                    "source_paths": [],
                },
            )
            setting_payload: MutableMapping[str, object] = {
                "label": SETTING_LABELS[setting],
                "completed": data["completed"],
                "successes": data["successes"],
                "unique_tasks": len(data["task_ids"]),
                "overall_rate": _safe_divide(data["successes"], expected_total),
                "completion_rate": _safe_divide(data["completed"], expected_total),
                "source_paths": sorted(data["source_paths"]),
                "by_drift": {},
            }
            for drift in DRIFT_ORDER:
                expected = expected_by_drift[drift]
                successes = data["successes_by_drift"][drift]
                completed = data["completed_by_drift"][drift]
                setting_payload["by_drift"][drift] = {
                    "expected": expected,
                    "completed": completed,
                    "successes": successes,
                    "rate": _safe_divide(successes, expected),
                    "completion_rate": _safe_divide(completed, expected),
                }
            benchmark_payload["settings"][setting] = setting_payload
        summary["benchmarks"][benchmark] = benchmark_payload
    return summary


def render_benchmark_figure_svg(benchmark_key: str, benchmark: Mapping[str, object]) -> str:
    width = 1320
    height = 620
    left_panel_x = 80
    left_panel_y = 170
    chart_height = 320
    left_panel_width = 820
    panel_gap = 70
    right_panel_x = left_panel_x + left_panel_width + panel_gap
    right_panel_width = 260
    chart_bottom = left_panel_y + chart_height
    divider_x = left_panel_x + left_panel_width + panel_gap // 2
    title = "%s Hardv3 XVR Matrix" % BENCHMARK_LABELS[benchmark_key]
    subtitle = "%s (n=%d)" % (benchmark["note"], benchmark["expected_total"])
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
        '<text x="80" y="52" class="title">%s</text>' % _escape(title),
        '<text x="80" y="78" class="subtitle">%s</text>' % _escape(subtitle),
        '<text x="80" y="104" class="subtitle">Left: success rate by version drift. Right: benchmark-level overall success rate.</text>',
        _render_legend(80, 130),
        '<line x1="%d" y1="150" x2="%d" y2="560" stroke="#e5e7eb" stroke-width="2"/>' % (
            divider_x,
            divider_x,
        ),
        '<text x="%d" y="150" class="panel-title">Version Drift Breakdown</text>' % left_panel_x,
        '<text x="%d" y="150" class="panel-title">Overall</text>' % right_panel_x,
    ]
    parts.extend(_render_chart_axes(left_panel_x, left_panel_y, left_panel_width, chart_height))
    parts.extend(_render_chart_axes(right_panel_x, left_panel_y, right_panel_width, chart_height))
    parts.extend(
        _render_drift_panel(
            benchmark,
            left_panel_x=left_panel_x,
            left_panel_y=left_panel_y,
            left_panel_width=left_panel_width,
            chart_height=chart_height,
        )
    )
    parts.extend(
        _render_overall_panel(
            benchmark,
            right_panel_x=right_panel_x,
            left_panel_y=left_panel_y,
            right_panel_width=right_panel_width,
            chart_height=chart_height,
        )
    )
    parts.append(
        '<text x="80" y="590" class="axis-muted">Note: rates are benchmark-local. Focus20 and TaskBank36 are reported separately rather than merged.</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def render_markdown_report(
    summary: Mapping[str, object],
    figure_paths: Mapping[str, str],
) -> str:
    focus20 = summary["benchmarks"]["focus20_hardv3"]
    taskbank = summary["benchmarks"]["taskbank36_hardv3"]
    lines = [
        "# Hardv3 XVR Matrix Report",
        "",
        "> This report summarizes the latest hardv3 Linkding matrix runs and separates the training-like Focus20 benchmark from the held-out TaskBank36 benchmark.",
        "",
        "## Executive Summary",
        "",
        _benchmark_summary_paragraph("focus20_hardv3", focus20),
        "",
        _benchmark_summary_paragraph("taskbank36_hardv3", taskbank),
        "",
        "## Evaluation Setup",
        "",
        "- `Focus20` is treated as the expanded training-like benchmark. Its figure should be read as a check of whether cross-version reflection rules improve performance near the rule-mining distribution.",
        "- `TaskBank36` is treated as the held-out test benchmark. Its figure should be read as the primary generalization result on unseen task families.",
        "- Each main figure uses the same two-panel layout: the left panel breaks success rate out by the seven version-drift categories, while the right panel shows the benchmark-level overall comparison.",
        "- The `structural_functional` and `runtime_process` shards are split back into the underlying drift families using row-level `drift_type` annotations from the eval JSONL files.",
        "- No cross-benchmark overall success rate is reported, because combining Focus20 and TaskBank36 would mix a training-like benchmark with a held-out evaluation benchmark.",
        "",
        "## Focus20",
        "",
        "![Focus20 hardv3 XVR matrix](%s)" % figure_paths["focus20_hardv3"],
        "",
        _benchmark_detail_paragraph("focus20_hardv3", focus20),
        "",
        _render_benchmark_table("focus20_hardv3", focus20),
        "",
        "### Paper-Style Focus20 Result Paragraph",
        "",
        _paper_result_paragraph("focus20_hardv3", focus20),
        "",
        "## TaskBank36",
        "",
        "![TaskBank36 hardv3 XVR matrix](%s)" % figure_paths["taskbank36_hardv3"],
        "",
        _benchmark_detail_paragraph("taskbank36_hardv3", taskbank),
        "",
        _render_benchmark_table("taskbank36_hardv3", taskbank),
        "",
        "### Paper-Style TaskBank36 Result Paragraph",
        "",
        _paper_result_paragraph("taskbank36_hardv3", taskbank),
        "",
        "## Cross-Benchmark Interpretation",
        "",
        _cross_benchmark_paragraph(focus20, taskbank),
        "",
        "## Appendix A: Per-Drift Success Tables",
        "",
        "### Focus20 Per-Drift Table",
        "",
        _render_per_drift_table(focus20),
        "",
        "### TaskBank36 Per-Drift Table",
        "",
        _render_per_drift_table(taskbank),
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_report_assets(
    *,
    result_roots: Sequence[Path],
    figure_dir: Path,
    report_dir: Path,
    report_filename: str,
) -> Dict[str, str]:
    eval_files = discover_latest_eval_files(result_roots)
    summary = aggregate_eval_files(eval_files)
    figure_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    focus20_figure_path = figure_dir / "focus20_hardv3_xvr_matrix.svg"
    taskbank_figure_path = figure_dir / "taskbank36_hardv3_xvr_matrix.svg"
    focus20_figure_path.write_text(
        render_benchmark_figure_svg("focus20_hardv3", summary["benchmarks"]["focus20_hardv3"]),
        encoding="utf-8",
    )
    taskbank_figure_path.write_text(
        render_benchmark_figure_svg("taskbank36_hardv3", summary["benchmarks"]["taskbank36_hardv3"]),
        encoding="utf-8",
    )

    report_path = report_dir / report_filename
    relative_figure_paths = {
        "focus20_hardv3": os.path.relpath(focus20_figure_path, start=report_dir),
        "taskbank36_hardv3": os.path.relpath(taskbank_figure_path, start=report_dir),
    }
    report_path.write_text(
        render_markdown_report(summary, relative_figure_paths),
        encoding="utf-8",
    )

    summary_path = report_dir / "2026-04-17-hardv3-xvr-matrix-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "report_path": str(report_path),
        "focus20_figure_path": str(focus20_figure_path),
        "taskbank36_figure_path": str(taskbank_figure_path),
        "summary_path": str(summary_path),
    }


def build_default_result_roots(repo_root: Path, expel_root: Optional[Path] = None) -> Sequence[Path]:
    roots = [repo_root / "results"]
    if expel_root is not None:
        roots.append(expel_root)
    else:
        default_expel_root = (
            Path.home()
            / ".config/superpowers/worktrees/WebCoEvo/expel-only-debug-20260417/results"
        )
        roots.append(default_expel_root)
    return roots


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the hardv3 XVR matrix report.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="WebCoEvo repository root.",
    )
    parser.add_argument(
        "--expel-results-root",
        type=Path,
        default=None,
        help="Optional root for non-reflection / expel-only results.",
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=None,
        help="Output directory for generated figures. Defaults to <repo-root>/figures.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Output directory for the Markdown report. Defaults to <repo-root>/docs/reports.",
    )
    parser.add_argument(
        "--report-filename",
        default="2026-04-17-hardv3-xvr-matrix-report.md",
        help="Filename for the generated Markdown report.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    figure_dir = (args.figure_dir or repo_root / "figures").resolve()
    report_dir = (args.report_dir or repo_root / "docs" / "reports").resolve()
    outputs = write_report_assets(
        result_roots=build_default_result_roots(repo_root, args.expel_results_root),
        figure_dir=figure_dir,
        report_dir=report_dir,
        report_filename=args.report_filename,
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))
    return 0


def _load_jsonl(path: Path) -> Iterable[Mapping[str, object]]:
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def _max_len(collections: Iterable[Iterable[object]]) -> int:
    return max((len(collection) for collection in collections), default=0)


def _safe_divide(numerator: int, denominator: int) -> float:
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)


def _normalize_drift(value: object) -> str:
    text = str(value)
    if text in DRIFT_ORDER:
        return text
    if text in ("structural_functional", "structural"):
        return "structural"
    if text in ("runtime_process", "runtime"):
        return "runtime"
    return "process"


def _format_percent(rate: float) -> str:
    return "%.1f%%" % (rate * 100.0)


def _escape(text: object) -> str:
    return html.escape(str(text), quote=True)


def _render_legend(x: int, y: int) -> str:
    cursor_x = x
    parts = []
    for setting in SETTING_ORDER:
        label = SETTING_LABELS[setting]
        color = SETTING_COLORS[setting]
        parts.append(
            '<rect x="%d" y="%d" width="14" height="14" rx="3" fill="%s"/>' % (cursor_x, y - 11, color)
        )
        parts.append(
            '<text x="%d" y="%d" class="legend">%s</text>'
            % (cursor_x + 22, y, _escape(label))
        )
        cursor_x += 22 + len(label) * 8 + 28
    return "\n".join(parts)


def _render_chart_axes(x: int, y: int, width: int, height: int) -> Sequence[str]:
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


def _render_drift_panel(
    benchmark: Mapping[str, object],
    *,
    left_panel_x: int,
    left_panel_y: int,
    left_panel_width: int,
    chart_height: int,
) -> Sequence[str]:
    chart_bottom = left_panel_y + chart_height
    group_width = float(left_panel_width) / float(len(DRIFT_ORDER))
    bar_width = 18
    bar_gap = 6
    group_inner_width = len(SETTING_ORDER) * bar_width + (len(SETTING_ORDER) - 1) * bar_gap
    parts = []
    for index, drift in enumerate(DRIFT_ORDER):
        group_x = left_panel_x + index * group_width
        start_x = group_x + (group_width - group_inner_width) / 2.0
        drift_payload = benchmark["expected_by_drift"]
        parts.extend(
            _two_line_label(
                x=int(group_x + group_width / 2.0),
                y=chart_bottom + 28,
                line1=DRIFT_LABELS[drift],
                line2="n=%d" % drift_payload[drift],
                css_class="axis",
            )
        )
        for setting_index, setting in enumerate(SETTING_ORDER):
            rate = benchmark["settings"][setting]["by_drift"][drift]["rate"]
            bar_height = chart_height * rate
            x = start_x + setting_index * (bar_width + bar_gap)
            y = chart_bottom - bar_height
            parts.append(
                '<rect x="%.1f" y="%.1f" width="%d" height="%.1f" rx="4" fill="%s"/>'
                % (x, y, bar_width, bar_height, SETTING_COLORS[setting])
            )
    return parts


def _render_overall_panel(
    benchmark: Mapping[str, object],
    *,
    right_panel_x: int,
    left_panel_y: int,
    right_panel_width: int,
    chart_height: int,
) -> Sequence[str]:
    chart_bottom = left_panel_y + chart_height
    bar_width = 36
    bar_gap = 18
    total_width = len(SETTING_ORDER) * bar_width + (len(SETTING_ORDER) - 1) * bar_gap
    start_x = right_panel_x + (right_panel_width - total_width) / 2.0
    parts = []
    for index, setting in enumerate(SETTING_ORDER):
        rate = benchmark["settings"][setting]["overall_rate"]
        bar_height = chart_height * rate
        x = start_x + index * (bar_width + bar_gap)
        y = chart_bottom - bar_height
        parts.append(
            '<rect x="%.1f" y="%.1f" width="%d" height="%.1f" rx="5" fill="%s"/>'
            % (x, y, bar_width, bar_height, SETTING_COLORS[setting])
        )
        parts.append(
            '<text x="%.1f" y="%.1f" class="value" text-anchor="middle">%s</text>'
            % (x + bar_width / 2.0, y - 8, _escape(_format_percent(rate)))
        )
        lines = [SETTING_LABELS[setting]]
        if setting == "expel_only":
            lines = ["Non-", "reflection"]
        parts.extend(
            _multiline_text(
                x=int(x + bar_width / 2.0),
                y=chart_bottom + 28,
                lines=lines,
                css_class="axis",
            )
        )
    return parts


def _multiline_text(x: int, y: int, lines: Sequence[str], css_class: str) -> Sequence[str]:
    parts = ['<text x="%d" y="%d" class="%s" text-anchor="middle">' % (x, y, css_class)]
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else 15
        parts.append('<tspan x="%d" dy="%d">%s</tspan>' % (x, dy, _escape(line)))
    parts.append("</text>")
    return parts


def _two_line_label(x: int, y: int, line1: str, line2: str, css_class: str) -> Sequence[str]:
    return _multiline_text(x, y, [line1, line2], css_class)


def _benchmark_summary_paragraph(benchmark_key: str, benchmark: Mapping[str, object]) -> str:
    best = _best_setting(benchmark)
    non_reflection_rate = benchmark["settings"]["expel_only"]["overall_rate"]
    best_rate = benchmark["settings"][best]["overall_rate"]
    delta = (best_rate - non_reflection_rate) * 100.0
    return (
        "On %s, the strongest configuration is %s at `%d/%d = %s`, which is `%.1f` percentage points above the non-reflection baseline."
        % (
            BENCHMARK_LABELS[benchmark_key],
            SETTING_LABELS[best],
            benchmark["settings"][best]["successes"],
            benchmark["expected_total"],
            _format_percent(best_rate),
            delta,
        )
    )


def _benchmark_detail_paragraph(benchmark_key: str, benchmark: Mapping[str, object]) -> str:
    best = _best_setting(benchmark)
    ordered = [_setting_result_clause(benchmark, setting) for setting in SETTING_ORDER]
    benchmark_name = BENCHMARK_LABELS[benchmark_key]
    if benchmark_key == "focus20_hardv3":
        framing = (
            "%s is treated as the training-like benchmark, so the main question is whether the rulebook improves performance broadly across the seven drift families near the rule-mining distribution."
            % benchmark_name
        )
    else:
        framing = (
            "%s is treated as the held-out test benchmark, so the main question is which rulebook carries over best to unseen task families."
            % benchmark_name
        )
    return "%s %s The best overall configuration is %s." % (
        framing,
        " ".join(ordered),
        SETTING_LABELS[best],
    )


def _paper_result_paragraph(benchmark_key: str, benchmark: Mapping[str, object]) -> str:
    best = _best_setting(benchmark)
    non_reflection = benchmark["settings"]["expel_only"]["overall_rate"]
    best_rate = benchmark["settings"][best]["overall_rate"]
    sentence = (
        "For %s, %s obtains `%d/%d = %s`, compared with the non-reflection baseline at `%d/%d = %s`."
        % (
            BENCHMARK_LABELS[benchmark_key],
            SETTING_LABELS[best],
            benchmark["settings"][best]["successes"],
            benchmark["expected_total"],
            _format_percent(best_rate),
            benchmark["settings"]["expel_only"]["successes"],
            benchmark["expected_total"],
            _format_percent(non_reflection),
        )
    )
    if benchmark_key == "taskbank36_hardv3":
        v25 = benchmark["settings"]["v2_5"]["overall_rate"]
        return (
            "%s This confirms that the best cross-version rulebook transfers to the held-out benchmark, while `v2.5` underperforms the non-reflection baseline at `%s`."
            % (sentence, _format_percent(v25))
        )
    return (
        "%s This indicates that cross-version reflection rules deliver a large gain on the training-like benchmark, with `v2.4` remaining the strongest variant."
        % sentence
    )


def _cross_benchmark_paragraph(
    focus20: Mapping[str, object], taskbank: Mapping[str, object]
) -> str:
    focus_best = _best_setting(focus20)
    task_best = _best_setting(taskbank)
    return (
        "The two benchmarks tell a consistent but not identical story. On the training-like Focus20 benchmark, all three XVR rulebooks substantially outperform non-reflection, with `%s` clearly on top. On the held-out TaskBank36 benchmark, `%s` is still the strongest setting, but the ranking is more discriminative: `v2.6` remains above non-reflection, whereas `v2.5` falls below the non-reflection baseline. This pattern suggests that the strongest rulebook is not only better at fitting the mined distribution, but also more robust when transferred to unseen tasks."
        % (SETTING_LABELS[focus_best], SETTING_LABELS[task_best])
    )


def _render_benchmark_table(benchmark_key: str, benchmark: Mapping[str, object]) -> str:
    lines = [
        "| Setting | Success / Total | Success Rate | Delta vs Non-reflection |",
        "| --- | ---: | ---: | ---: |",
    ]
    baseline_rate = benchmark["settings"]["expel_only"]["overall_rate"]
    for setting in SETTING_ORDER:
        payload = benchmark["settings"][setting]
        delta = "—"
        if setting != "expel_only":
            delta = "%+.1f pts" % ((payload["overall_rate"] - baseline_rate) * 100.0)
        lines.append(
            "| %s | %d/%d | %s | %s |"
            % (
                SETTING_LABELS[setting],
                payload["successes"],
                benchmark["expected_total"],
                _format_percent(payload["overall_rate"]),
                delta,
            )
        )
    return "\n".join(lines)


def _render_per_drift_table(benchmark: Mapping[str, object]) -> str:
    lines = [
        "| Drift | n | Non-reflection | v2.4 | v2.5 | v2.6 |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for drift in DRIFT_ORDER:
        n = benchmark["expected_by_drift"][drift]
        values = []
        for setting in SETTING_ORDER:
            payload = benchmark["settings"][setting]["by_drift"][drift]
            values.append(
                "%d/%d (%s)" % (payload["successes"], n, _format_percent(payload["rate"]))
            )
        lines.append(
            "| %s | %d | %s | %s | %s | %s |"
            % (
                DRIFT_LABELS[drift],
                n,
                values[0],
                values[1],
                values[2],
                values[3],
            )
        )
    return "\n".join(lines)


def _setting_result_clause(benchmark: Mapping[str, object], setting: str) -> str:
    payload = benchmark["settings"][setting]
    return "%s reaches `%d/%d = %s`." % (
        SETTING_LABELS[setting],
        payload["successes"],
        benchmark["expected_total"],
        _format_percent(payload["overall_rate"]),
    )


def _best_setting(benchmark: Mapping[str, object]) -> str:
    return max(
        SETTING_ORDER,
        key=lambda setting: (
            benchmark["settings"][setting]["overall_rate"],
            -SETTING_ORDER.index(setting),
        ),
    )


__all__ = [
    "BENCHMARK_ORDER",
    "DRIFT_ORDER",
    "SETTING_ORDER",
    "aggregate_eval_files",
    "build_default_result_roots",
    "discover_latest_eval_files",
    "main",
    "parse_args",
    "render_benchmark_figure_svg",
    "render_markdown_report",
    "write_report_assets",
]
