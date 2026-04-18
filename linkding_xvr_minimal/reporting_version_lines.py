import argparse
import html
import json
import os
from pathlib import Path


VERSION_ORDER = ["control_1450", "first_modified", "hardv3"]
VERSION_LABELS = {
    "control_1450": "Control 1.45.0",
    "hardv3": "Hardv3",
    "first_modified": "First-Modified",
}

SERIES_ORDER = ["expel_only", "v2_4"]
SERIES_LABELS = {
    "expel_only": "ExpeL Only",
    "v2_4": "V2.4",
}
SERIES_COLORS = {
    "expel_only": "#f59e0b",
    "v2_4": "#2563eb",
}

BENCHMARK_KEYS = {
    "focus20": {
        "label": "Focus20",
        "hardv3_key": "focus20_hardv3",
        "umich_key": "focus20",
    },
    "taskbank36": {
        "label": "TaskBank36",
        "hardv3_key": "taskbank36_hardv3",
        "umich_key": "taskbank36",
    },
}


def _load_json(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def build_version_line_summary(hardv3_summary_path, umich_summary_path):
    hardv3_summary = _load_json(hardv3_summary_path)
    umich_summary = _load_json(umich_summary_path)

    summary = {
        "model": umich_summary.get("model", ""),
        "endpoint": umich_summary.get("endpoint", ""),
        "hardv3_summary_path": str(Path(hardv3_summary_path)),
        "umich_summary_path": str(Path(umich_summary_path)),
        "benchmarks": {},
    }

    for benchmark_key, spec in BENCHMARK_KEYS.items():
        benchmark = {
            "label": spec["label"],
            "x_labels": [VERSION_LABELS[key] for key in VERSION_ORDER],
            "series_order": list(SERIES_ORDER),
            "series": {},
        }
        for series_key in SERIES_ORDER:
            benchmark["series"][series_key] = {
                "label": SERIES_LABELS[series_key],
                "points": [
                    _build_control_point(umich_summary, spec["umich_key"], series_key),
                    _build_first_modified_point(umich_summary, spec["umich_key"], series_key),
                    _build_hardv3_point(hardv3_summary, spec["hardv3_key"], series_key),
                ],
            }
        summary["benchmarks"][benchmark_key] = benchmark
    return summary


def _build_control_point(umich_summary, benchmark_key, series_key):
    if series_key != "expel_only":
        return {
            "available": False,
            "status": "missing",
            "note": "No control V2.4 run is available in the current summaries.",
        }

    payload = umich_summary["scenarios"]["control_1450"]["benchmarks"][benchmark_key]["settings"]["expel_only"]
    return _normalize_umich_point(payload)


def _build_first_modified_point(umich_summary, benchmark_key, series_key):
    payload = umich_summary["scenarios"]["first_modified"]["benchmarks"][benchmark_key]["settings"][series_key]
    return _normalize_umich_point(payload)


def _build_hardv3_point(hardv3_summary, benchmark_key, series_key):
    payload = hardv3_summary["benchmarks"][benchmark_key]["settings"][series_key]
    return {
        "available": True,
        "status": "complete",
        "successes": payload["successes"],
        "total": hardv3_summary["benchmarks"][benchmark_key]["expected_total"],
        "rate": payload["overall_rate"],
        "note": "",
    }


def _normalize_umich_point(payload):
    if payload.get("final_success_rate_available", False) and payload.get("overall_rate") is not None:
        return {
            "available": True,
            "status": payload.get("status", "complete"),
            "successes": payload["successes"],
            "total": payload.get("expected_total") or payload.get("completed") or 0,
            "rate": payload["overall_rate"],
            "note": "",
        }
    return {
        "available": False,
        "status": payload.get("status", "partial"),
        "successes": payload.get("successes"),
        "completed": payload.get("completed"),
        "completion_rate": payload.get("completion_rate"),
        "lower_bound_rate": payload.get("lower_bound_rate"),
        "note": "Point unavailable because the run did not produce a final benchmark-wide success rate.",
    }


def render_version_line_svg(benchmark_key, benchmark):
    width = 1120
    height = 560
    chart_left = 100
    chart_top = 120
    chart_width = 900
    chart_height = 320
    chart_bottom = chart_top + chart_height
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
        ".axis { font: 12px 'Helvetica Neue', Arial, sans-serif; fill: #374151; }",
        ".legend { font: 13px 'Helvetica Neue', Arial, sans-serif; fill: #1f2937; }",
        ".value { font: 12px 'Helvetica Neue', Arial, sans-serif; fill: #111827; }",
        ".na { font: 11px 'Helvetica Neue', Arial, sans-serif; fill: #9ca3af; }",
        "</style>",
        '<rect width="100%%" height="100%%" fill="#ffffff"/>',
        '<text x="80" y="52" class="title">%s Website Version Lines</text>' % escape(benchmark["label"]),
        '<text x="80" y="78" class="subtitle">X-axis: website version. Y-axis: final success rate. Missing points are shown as N/A.</text>',
    ]
    parts.extend(_render_line_legend(80, 102, benchmark["series_order"]))
    parts.extend(_render_axes(chart_left, chart_top, chart_width, chart_height))

    step = chart_width / float(len(benchmark["x_labels"]) - 1)
    x_positions = [chart_left + index * step for index in range(len(benchmark["x_labels"]))]
    for index, label in enumerate(benchmark["x_labels"]):
        parts.extend(_multiline_text(int(x_positions[index]), chart_bottom + 28, label.split(" "), "axis"))

    for series_key in benchmark["series_order"]:
        series = benchmark["series"][series_key]
        points = series["points"]
        line_segments = []
        current_segment = []
        for index, point in enumerate(points):
            x = x_positions[index]
            if point["available"]:
                y = chart_bottom - chart_height * point["rate"]
                current_segment.append((x, y))
                parts.append(
                    '<circle cx="%.1f" cy="%.1f" r="6" fill="%s" stroke="#ffffff" stroke-width="2"/>'
                    % (x, y, SERIES_COLORS[series_key])
                )
                parts.append(
                    '<text x="%.1f" y="%.1f" class="value" text-anchor="middle">%s</text>'
                    % (x, y - 12, escape("%.1f%%" % (point["rate"] * 100.0)))
                )
            else:
                if current_segment:
                    line_segments.append(list(current_segment))
                    current_segment = []
                parts.append(
                    '<circle cx="%.1f" cy="%.1f" r="6" fill="#ffffff" stroke="%s" stroke-width="2" stroke-dasharray="3 2"/>'
                    % (x, chart_bottom - 8, SERIES_COLORS[series_key])
                )
                parts.append(
                    '<text x="%.1f" y="%.1f" class="na" text-anchor="middle">N/A</text>'
                    % (x, chart_bottom - 18)
                )
        if current_segment:
            line_segments.append(list(current_segment))
        for segment in line_segments:
            if len(segment) < 2:
                continue
            parts.append(
                '<polyline fill="none" stroke="%s" stroke-width="3" points="%s"/>'
                % (
                    SERIES_COLORS[series_key],
                    " ".join("%.1f,%.1f" % point for point in segment),
                )
            )

    if benchmark_key == "taskbank36":
        parts.append(
            '<text x="80" y="500" class="subtitle">TaskBank36 control point is unavailable because the control baseline did not finish before the Slurm time limit.</text>'
        )
    else:
        parts.append(
            '<text x="80" y="500" class="subtitle">Control 1.45.0 has an ExpeL-only point, but no matching V2.4 run in the current experiment set.</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def _render_line_legend(x, y, series_order):
    cursor_x = x
    parts = []
    for series_key in series_order:
        parts.append(
            '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="3"/>'
            % (cursor_x, y - 4, cursor_x + 22, y - 4, SERIES_COLORS[series_key])
        )
        parts.append(
            '<circle cx="%d" cy="%d" r="5" fill="%s" stroke="#ffffff" stroke-width="2"/>'
            % (cursor_x + 11, y - 4, SERIES_COLORS[series_key])
        )
        parts.append(
            '<text x="%d" y="%d" class="legend">%s</text>'
            % (cursor_x + 32, y, escape(SERIES_LABELS[series_key]))
        )
        cursor_x += 32 + len(SERIES_LABELS[series_key]) * 8 + 36
    return parts


def _render_axes(x, y, width, height):
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


def _multiline_text(x, y, lines, css_class):
    parts = ['<text x="%d" y="%d" class="%s" text-anchor="middle">' % (x, y, css_class)]
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else 15
        parts.append('<tspan x="%d" dy="%d">%s</tspan>' % (x, dy, escape(line)))
    parts.append("</text>")
    return parts


def render_markdown_report(summary, figure_paths):
    focus20 = summary["benchmarks"]["focus20"]
    taskbank36 = summary["benchmarks"]["taskbank36"]
    focus20_labels = focus20["x_labels"]
    taskbank36_labels = taskbank36["x_labels"]
    focus20_expel = focus20["series"]["expel_only"]["points"]
    focus20_v24 = focus20["series"]["v2_4"]["points"]
    taskbank36_expel = taskbank36["series"]["expel_only"]["points"]
    taskbank36_v24 = taskbank36["series"]["v2_4"]["points"]
    lines = [
        "# Website Version Line Report",
        "",
        "> This report merges the existing hardv3 matrix summary with the UMich Qwen3-VL rule-comparison summary.",
        "",
        "## Setup",
        "",
        "- Model: `%s`" % summary["model"],
        "- Endpoint: `%s`" % summary["endpoint"],
        "- Website versions on the x-axis: `%s`, `%s`, `%s`."
        % (focus20_labels[0], focus20_labels[1], focus20_labels[2]),
        "- Two compared series: `ExpeL Only` and `V2.4`.",
        "",
        "## Focus20",
        "",
        "![Focus20 website version lines](%s)" % figure_paths["focus20"],
        "",
        "For Focus20, `ExpeL Only` moves from `%s` on the control site to `%s` on `%s`, then to `%s` on `%s`."
        % (
            _format_point(focus20_expel[0]),
            _format_point(focus20_expel[1]),
            focus20_labels[1],
            _format_point(focus20_expel[2]),
            focus20_labels[2],
        ),
        "`V2.4` has no control point in the current summaries, but it reaches `%s` on `%s` and `%s` on `%s`."
        % (_format_point(focus20_v24[1]), focus20_labels[1], _format_point(focus20_v24[2]), focus20_labels[2]),
        "",
        _render_version_table(focus20),
        "",
        "## TaskBank36",
        "",
        "![TaskBank36 website version lines](%s)" % figure_paths["taskbank36"],
        "",
        "TaskBank36 control point is unavailable for a final success-rate comparison because the control baseline did not complete before the Slurm time limit."
        " The completed website-version comparison therefore starts from `%s` and continues to `%s`."
        % (
            taskbank36_labels[1],
            taskbank36_labels[2],
        ),
        "`ExpeL Only` reaches `%s` on `%s` and `%s` on `%s`, while `V2.4` goes from `%s` on `%s` to `%s` on `%s`."
        % (
            _format_point(taskbank36_expel[1]),
            taskbank36_labels[1],
            _format_point(taskbank36_expel[2]),
            taskbank36_labels[2],
            _format_point(taskbank36_v24[1]),
            taskbank36_labels[1],
            _format_point(taskbank36_v24[2]),
            taskbank36_labels[2],
        ),
        "",
        _render_version_table(taskbank36),
        "",
        "## Interpretation",
        "",
        "Across the completed comparisons, `First-Modified` is the strongest website version for both rule settings, and `V2.4` consistently stays above `ExpeL Only` whenever both are available."
        " The hardest version for `ExpeL Only` is `Hardv3`, which pulls Focus20 down to `11.8%` and TaskBank36 to `39.5%`.",
        "",
        "## Data Sources",
        "",
    ]
    if summary.get("hardv3_summary_path"):
        lines.append("- Hardv3 summary: `%s`" % summary["hardv3_summary_path"])
    if summary.get("umich_summary_path"):
        lines.append("- UMich rule-comparison summary: `%s`" % summary["umich_summary_path"])
    return "\n".join(lines).rstrip() + "\n"


def _render_version_table(benchmark):
    lines = [
        "| Website Version | ExpeL Only | V2.4 |",
        "| --- | ---: | ---: |",
    ]
    for index, version_key in enumerate(VERSION_ORDER):
        expel = benchmark["series"]["expel_only"]["points"][index]
        v24 = benchmark["series"]["v2_4"]["points"][index]
        lines.append(
            "| %s | %s | %s |"
            % (
                VERSION_LABELS[version_key],
                _format_point(expel),
                _format_point(v24),
            )
        )
    return "\n".join(lines)


def _format_point(point):
    if not point["available"]:
        return "N/A"
    return "%d/%d (%0.1f%%)" % (
        point["successes"],
        point["total"],
        point["rate"] * 100.0,
    )


def write_report_assets(summary, figure_dir, report_dir, report_filename):
    figure_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    focus20_figure_path = figure_dir / "focus20_website_version_lines.svg"
    taskbank36_figure_path = figure_dir / "taskbank36_website_version_lines.svg"
    focus20_figure_path.write_text(
        render_version_line_svg("focus20", summary["benchmarks"]["focus20"]),
        encoding="utf-8",
    )
    taskbank36_figure_path.write_text(
        render_version_line_svg("taskbank36", summary["benchmarks"]["taskbank36"]),
        encoding="utf-8",
    )
    report_path = report_dir / report_filename
    figure_paths = {
        "focus20": os.path.relpath(focus20_figure_path, start=report_dir),
        "taskbank36": os.path.relpath(taskbank36_figure_path, start=report_dir),
    }
    report_path.write_text(
        render_markdown_report(summary, figure_paths),
        encoding="utf-8",
    )
    summary_path = report_dir / "2026-04-18-website-version-line-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "report_path": str(report_path),
        "summary_path": str(summary_path),
        "focus20_figure_path": str(focus20_figure_path),
        "taskbank36_figure_path": str(taskbank36_figure_path),
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Generate the website-version line-chart report.")
    parser.add_argument(
        "--hardv3-summary",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "docs" / "reports" / "2026-04-17-hardv3-xvr-matrix-summary.json",
        help="Path to the hardv3 matrix summary JSON.",
    )
    parser.add_argument(
        "--umich-summary",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "docs" / "reports" / "2026-04-18-umich-qwen3-rule-comparison-summary.json",
        help="Path to the UMich rule-comparison summary JSON.",
    )
    parser.add_argument(
        "--figure-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "figures",
        help="Output directory for generated SVG figures.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "docs" / "reports",
        help="Output directory for the Markdown report.",
    )
    parser.add_argument(
        "--report-filename",
        default="2026-04-18-website-version-line-report.md",
        help="Filename for the generated Markdown report.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    summary = build_version_line_summary(args.hardv3_summary, args.umich_summary)
    outputs = write_report_assets(
        summary=summary,
        figure_dir=args.figure_dir.resolve(),
        report_dir=args.report_dir.resolve(),
        report_filename=args.report_filename,
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))
    return 0


def escape(text):
    return html.escape(str(text), quote=True)
