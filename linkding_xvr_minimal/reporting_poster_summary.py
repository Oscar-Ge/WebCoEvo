import argparse
import html
import json
import os
from pathlib import Path
from typing import Mapping, MutableMapping, Optional, Sequence


PANEL_ORDER = ["training_task_sets", "heldout_validation_task_sets"]
WEBSITE_LABELS = ["Website V1", "Website V2", "Website V3"]
WEBSITE_SUBLABELS = [
    "Original 1.45.0",
    "First vibe-coded version",
    "Harder vibe-coded version",
]
REFLECTION_LABELS = {
    "v2_4": "Reflection Rules V1",
    "v2_5": "Reflection Rules V2",
    "v2_6": "Reflection Rules V3",
    "v2_4_1": "Reflection Rules V4",
}
SERIES_LABELS = {
    "no_rules": "No Rules",
    "expel_rules": "ExpeL Rules",
    "best_reflection_rules": "Best Reflection Rules",
}
SERIES_COLORS = {
    "no_rules": "#b8bec7",
    "expel_rules": "#d97706",
    "best_reflection_rules": "#2563eb",
}
INSET_COLORS = {
    "v2_4": "#1d4ed8",
    "v2_5": "#60a5fa",
    "v2_6": "#93c5fd",
    "v2_4_1": "#2563eb",
}
PANEL_META = {
    "training_task_sets": {
        "title": "Training Task Sets",
        "subtitle": "Performance across website versions",
        "umich_benchmark": "focus20",
        "hardv3_benchmark": "focus20_hardv3",
        "takeaway": (
            "ExpeL helps on the original training-like environment, but reflection stays stronger as website versions drift."
        ),
        "caption": (
            "On training task sets, ExpeL rules help dramatically on the original environment but collapse on the harder vibe-coded Website V3, while reflection rules remain strong across newer website versions."
        ),
        "v3_inset_note": "Not monotonic: V1 remains best",
    },
    "heldout_validation_task_sets": {
        "title": "Held-out Validation Task Sets",
        "subtitle": "Transfer to unseen task sets across website versions",
        "umich_benchmark": "taskbank36",
        "hardv3_benchmark": "taskbank36_hardv3",
        "takeaway": (
            "Reflection rules transfer better to held-out validation task sets, while ExpeL degrades sharply under newer vibe-coded websites."
        ),
        "caption": (
            "On held-out validation task sets, ExpeL rules degrade sharply as the website changes, while reflection rules transfer better to unseen tasks and remain stronger on both vibe-coded versions."
        ),
        "v3_inset_note": "Not monotonic: V1 and V4 tie",
    },
}


def build_poster_summary(
    umich_summary: Mapping[str, object],
    hardv3_summary: Mapping[str, object],
) -> MutableMapping[str, object]:
    main_panels: MutableMapping[str, object] = {}
    reflection_panels: MutableMapping[str, object] = {}
    for panel_key in PANEL_ORDER:
        spec = PANEL_META[panel_key]
        umich_benchmark = spec["umich_benchmark"]
        hardv3_benchmark = spec["hardv3_benchmark"]

        control_settings = umich_summary["scenarios"]["control_1450"]["benchmarks"][umich_benchmark]["settings"]
        first_settings = umich_summary["scenarios"]["first_modified"]["benchmarks"][umich_benchmark]["settings"]
        hardv3_settings = hardv3_summary["benchmarks"][hardv3_benchmark]["settings"]
        hardv3_total = hardv3_summary["benchmarks"][hardv3_benchmark]["expected_total"]

        best_v3_keys = _best_hardv3_keys(hardv3_settings)
        best_v3_key = best_v3_keys[0]

        website_versions = [
            {
                "label": WEBSITE_LABELS[0],
                "sublabel": WEBSITE_SUBLABELS[0],
                "series": {
                    "no_rules": _series_payload(control_settings["no_rules"]),
                    "expel_rules": _series_payload(control_settings["expel_only"]),
                },
            },
            {
                "label": WEBSITE_LABELS[1],
                "sublabel": WEBSITE_SUBLABELS[1],
                "series": {
                    "expel_rules": _series_payload(first_settings["expel_only"]),
                    "best_reflection_rules": {
                        **_series_payload(first_settings["v2_4"]),
                        "public_version": REFLECTION_LABELS["v2_4"],
                    },
                },
            },
            {
                "label": WEBSITE_LABELS[2],
                "sublabel": WEBSITE_SUBLABELS[2],
                "series": {
                    "expel_rules": _series_payload(hardv3_settings["expel_only"], total=hardv3_total),
                    "best_reflection_rules": {
                        **_series_payload(hardv3_settings[best_v3_key], total=hardv3_total),
                        "public_version": _public_reflection_label(best_v3_keys),
                    },
                },
            },
        ]
        reflection_series = [
            {
                "key": key,
                "label": REFLECTION_LABELS[key],
                **_series_payload(hardv3_settings[key], total=hardv3_total),
                "is_best": key in best_v3_keys,
            }
            for key in ("v2_4", "v2_5", "v2_6", "v2_4_1")
        ]

        main_panels["%s_main" % panel_key] = {
            "title": spec["title"],
            "subtitle": spec["subtitle"],
            "takeaway": spec["takeaway"],
            "caption": spec["caption"],
            "website_versions": website_versions,
        }
        reflection_panels["%s_reflection_v3" % panel_key] = {
            "title": spec["title"],
            "subtitle": "Reflection Rules on Website V3",
            "takeaway": spec["v3_inset_note"],
            "series": reflection_series,
        }
    return {
        "main_panel_order": [
            "training_task_sets_main",
            "heldout_validation_task_sets_main",
        ],
        "reflection_panel_order": [
            "training_task_sets_reflection_v3",
            "heldout_validation_task_sets_reflection_v3",
        ],
        "main_panels": main_panels,
        "reflection_panels": reflection_panels,
        "public_mapping": {
            "website_versions": {
                "Website V1": "Original Linkding 1.45.0",
                "Website V2": "First vibe-coded website version",
                "Website V3": "Harder vibe-coded website version",
            },
            "reflection_versions": {
                "Reflection Rules V1": "internal v2.4",
                "Reflection Rules V2": "internal v2.5",
                "Reflection Rules V3": "internal v2.6",
                "Reflection Rules V4": "internal v2.4.1",
            },
        },
        "claims": [
            "ExpeL rules lose robustness as the website changes from Website V1 to Website V3.",
            "Reflection rules transfer better to held-out validation task sets than ExpeL rules.",
            "Reflection rules can be iterated from V1 to V4, but later iterations are not guaranteed to be stronger.",
        ],
    }


def render_main_panel_svg(panel: Mapping[str, object]) -> str:
    width = 1040
    height = 620
    chart_left = 92
    chart_top = 136
    chart_width = 840
    chart_height = 360
    legend_y = 104

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (
            width,
            height,
            width,
            height,
        ),
        "<style>",
        ".title { font: 700 34px 'Helvetica Neue', Arial, sans-serif; fill: #111827; }",
        ".subtitle { font: 500 20px 'Helvetica Neue', Arial, sans-serif; fill: #4b5563; }",
        ".legend { font: 16px 'Helvetica Neue', Arial, sans-serif; fill: #1f2937; }",
        ".axis { font: 16px 'Helvetica Neue', Arial, sans-serif; fill: #374151; }",
        ".small { font: 13px 'Helvetica Neue', Arial, sans-serif; fill: #6b7280; }",
        ".value { font: 15px 'Helvetica Neue', Arial, sans-serif; fill: #111827; }",
        ".note { font: 18px 'Helvetica Neue', Arial, sans-serif; fill: #374151; }",
        "</style>",
        '<rect width="100%%" height="100%%" fill="#ffffff"/>',
        '<text x="92" y="50" class="title">%s</text>' % _escape(panel["title"]),
        '<text x="92" y="78" class="subtitle">%s</text>' % _escape(panel["subtitle"]),
    ]
    parts.extend(_render_main_legend(92, legend_y))
    parts.extend(_render_axes(chart_left, chart_top, chart_width, chart_height, axis_class="axis"))
    parts.extend(_render_main_bars_and_lines(panel, chart_left, chart_top, chart_width, chart_height, axis_class="axis", value_class="value"))
    parts.append('<text x="92" y="566" class="note">%s</text>' % _escape(panel["takeaway"]))
    parts.append("</svg>")
    return "\n".join(parts)


def render_reflection_panel_svg(panel: Mapping[str, object]) -> str:
    width = 620
    height = 430
    chart_left = 70
    chart_top = 118
    chart_width = 500
    chart_height = 220
    bottom = chart_top + chart_height
    bar_width = 68
    gap = 28

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
        ".subtitle { font: 600 18px 'Helvetica Neue', Arial, sans-serif; fill: #4b5563; }",
        ".axis { font: 15px 'Helvetica Neue', Arial, sans-serif; fill: #374151; }",
        ".small { font: 13px 'Helvetica Neue', Arial, sans-serif; fill: #6b7280; }",
        ".value { font: 14px 'Helvetica Neue', Arial, sans-serif; fill: #111827; }",
        ".note { font: 17px 'Helvetica Neue', Arial, sans-serif; fill: #374151; }",
        "</style>",
        '<rect width="100%%" height="100%%" fill="#ffffff"/>',
        '<text x="70" y="44" class="title">%s</text>' % _escape(panel["title"]),
        '<text x="70" y="74" class="subtitle">%s</text>' % _escape(panel["subtitle"]),
    ]
    parts.extend(_render_axes(chart_left, chart_top, chart_width, chart_height, axis_class="axis"))

    total_width = len(panel["series"]) * bar_width + (len(panel["series"]) - 1) * gap
    start_x = chart_left + (chart_width - total_width) / 2.0
    for index, item in enumerate(panel["series"]):
        bar_x = start_x + index * (bar_width + gap)
        bar_height = chart_height * item["rate"]
        bar_y = bottom - bar_height
        color = INSET_COLORS[item["key"]]
        stroke = "#0f172a" if item["is_best"] else "none"
        stroke_width = 3 if item["is_best"] else 0
        parts.append(
            '<rect x="%.1f" y="%.1f" width="%d" height="%.1f" rx="8" fill="%s" stroke="%s" stroke-width="%d"/>' % (
                bar_x,
                bar_y,
                bar_width,
                bar_height,
                color,
                stroke,
                stroke_width,
            )
        )
        parts.append(
            '<text x="%.1f" y="%.1f" class="value" text-anchor="middle">%s</text>' % (
                bar_x + bar_width / 2.0,
                bar_y - 10,
                _escape("%.1f%%" % (item["rate"] * 100.0)),
            )
        )
        short_label = item["label"].replace("Reflection Rules ", "")
        parts.extend(_multiline_text(int(bar_x + bar_width / 2.0), bottom + 26, [short_label], "axis"))
    parts.append('<text x="70" y="392" class="note">%s</text>' % _escape(panel["takeaway"]))
    parts.append("</svg>")
    return "\n".join(parts)


def render_report_markdown(summary: Mapping[str, object], figure_paths: Mapping[str, str]) -> str:
    training = summary["main_panels"]["training_task_sets_main"]
    heldout = summary["main_panels"]["heldout_validation_task_sets_main"]
    lines = [
        "# Poster Summary Figures Report",
        "",
        "> This report packages a 4-panel poster layout with two large main figures and two smaller reflection-evolution figures.",
        "",
        "## Core Message",
        "",
        "- ExpeL degrades under website drift.",
        "- Reflection stays stronger on newer websites and transfers better to held-out validation task sets.",
        "- Reflection rule iteration is real, but not monotonic.",
        "",
        "## 4-panel poster layout",
        "",
        "- Left column: two larger main panels.",
        "- Right column: two smaller `Reflection Rules on Website V3` panels.",
        "- Use big labels and keep spoken explanation short.",
        "",
        "## Training Task Sets",
        "",
        "![Training Task Sets Main](%s)" % figure_paths["training_task_sets_main"],
        "",
        "![Training Task Sets Reflection V3](%s)" % figure_paths["training_task_sets_reflection_v3"],
        "",
        training["caption"],
        "",
        _render_panel_table(training),
        "",
        "## Held-out Validation Task Sets",
        "",
        "![Held-out Validation Task Sets Main](%s)" % figure_paths["heldout_validation_task_sets_main"],
        "",
        "![Held-out Validation Task Sets Reflection V3](%s)" % figure_paths["heldout_validation_task_sets_reflection_v3"],
        "",
        heldout["caption"],
        "",
        _render_panel_table(heldout),
        "",
        "## Short script",
        "",
        "- Start with the orange line: ExpeL drops as the website changes.",
        "- Then point to the blue bars: reflection remains stronger on newer websites.",
        "- Finally point to the right-side panels: later reflection versions are not always better.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_poster_assets(
    *,
    umich_summary_path: Path,
    hardv3_summary_path: Path,
    figure_dir: Path,
    report_dir: Path,
) -> Mapping[str, str]:
    umich_summary = _load_json(umich_summary_path)
    hardv3_summary = _load_json(hardv3_summary_path)
    summary = build_poster_summary(umich_summary, hardv3_summary)

    figure_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    training_main_figure = figure_dir / "training_task_sets_main_poster_summary.svg"
    training_reflection_figure = figure_dir / "training_task_sets_reflection_v3_poster_summary.svg"
    heldout_main_figure = figure_dir / "heldout_validation_task_sets_main_poster_summary.svg"
    heldout_reflection_figure = figure_dir / "heldout_validation_task_sets_reflection_v3_poster_summary.svg"
    report_path = report_dir / "2026-04-18-poster-summary-figures-report.md"
    summary_path = report_dir / "2026-04-18-poster-summary-figures-summary.json"

    training_main_figure.write_text(
        render_main_panel_svg(summary["main_panels"]["training_task_sets_main"]),
        encoding="utf-8",
    )
    training_reflection_figure.write_text(
        render_reflection_panel_svg(summary["reflection_panels"]["training_task_sets_reflection_v3"]),
        encoding="utf-8",
    )
    heldout_main_figure.write_text(
        render_main_panel_svg(summary["main_panels"]["heldout_validation_task_sets_main"]),
        encoding="utf-8",
    )
    heldout_reflection_figure.write_text(
        render_reflection_panel_svg(summary["reflection_panels"]["heldout_validation_task_sets_reflection_v3"]),
        encoding="utf-8",
    )
    relative_paths = {
        "training_task_sets_main": os.path.relpath(training_main_figure, start=report_dir),
        "training_task_sets_reflection_v3": os.path.relpath(training_reflection_figure, start=report_dir),
        "heldout_validation_task_sets_main": os.path.relpath(heldout_main_figure, start=report_dir),
        "heldout_validation_task_sets_reflection_v3": os.path.relpath(heldout_reflection_figure, start=report_dir),
    }
    report_path.write_text(
        render_report_markdown(summary, relative_paths),
        encoding="utf-8",
    )
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "training_main_figure_path": str(training_main_figure),
        "training_reflection_figure_path": str(training_reflection_figure),
        "heldout_main_figure_path": str(heldout_main_figure),
        "heldout_reflection_figure_path": str(heldout_reflection_figure),
        "report_path": str(report_path),
        "summary_path": str(summary_path),
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate poster summary figures and report.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="WebCoEvo repository root.",
    )
    parser.add_argument(
        "--umich-summary",
        type=Path,
        default=None,
        help="Optional override for the UMich rules comparison summary JSON.",
    )
    parser.add_argument(
        "--hardv3-summary",
        type=Path,
        default=None,
        help="Optional override for the hardv3 matrix summary JSON.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    outputs = write_poster_assets(
        umich_summary_path=(args.umich_summary or repo_root / "docs" / "reports" / "2026-04-18-umich-qwen3-rule-comparison-summary.json").resolve(),
        hardv3_summary_path=(args.hardv3_summary or repo_root / "docs" / "reports" / "2026-04-17-hardv3-xvr-matrix-summary.json").resolve(),
        figure_dir=(repo_root / "figures").resolve(),
        report_dir=(repo_root / "docs" / "reports").resolve(),
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))
    return 0


def _series_payload(payload: Mapping[str, object], total: Optional[int] = None) -> MutableMapping[str, object]:
    value_total = payload.get("expected_total", total)
    return {
        "successes": int(payload["successes"]),
        "total": int(value_total),
        "rate": float(payload["overall_rate"]),
    }


def _best_hardv3_keys(settings: Mapping[str, Mapping[str, object]]) -> Sequence[str]:
    keys = ("v2_4", "v2_5", "v2_6", "v2_4_1")
    best_rate = max(float(settings[key]["overall_rate"]) for key in keys)
    return [key for key in keys if float(settings[key]["overall_rate"]) == best_rate]


def _public_reflection_label(keys: Sequence[str]) -> str:
    if len(keys) == 1:
        return REFLECTION_LABELS[keys[0]]
    parts = []
    for key in keys:
        label = REFLECTION_LABELS[key]
        if parts:
            parts.append(label.replace("Reflection Rules ", ""))
        else:
            parts.append(label)
    return " / ".join(parts)


def _render_main_legend(x: int, y: int) -> Sequence[str]:
    cursor_x = x
    parts = []
    for key in ("no_rules", "expel_rules", "best_reflection_rules"):
        parts.append(
            '<rect x="%d" y="%d" width="14" height="14" rx="3" fill="%s"/>' % (
                cursor_x,
                y - 11,
                SERIES_COLORS[key],
            )
        )
        parts.append(
            '<text x="%d" y="%d" class="legend">%s</text>' % (
                cursor_x + 22,
                y,
                _escape(SERIES_LABELS[key]),
            )
        )
        cursor_x += 22 + len(SERIES_LABELS[key]) * 8 + 34
    return parts


def _render_axes(x: int, y: int, width: int, height: int, axis_class: str) -> Sequence[str]:
    bottom = y + height
    parts = [
        '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#111827" stroke-width="1.5"/>' % (x, bottom, x + width, bottom),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#111827" stroke-width="1.5"/>' % (x, y, x, bottom),
    ]
    for tick in (0, 25, 50, 75, 100):
        tick_y = bottom - int(height * tick / 100.0)
        parts.append(
            '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#e5e7eb" stroke-width="1"/>' % (
                x,
                tick_y,
                x + width,
                tick_y,
            )
        )
        parts.append(
            '<text x="%d" y="%d" class="%s" text-anchor="end">%d%%</text>' % (
                x - 10,
                tick_y + 4,
                axis_class,
                tick,
            )
        )
    return parts


def _render_main_bars_and_lines(
    panel: Mapping[str, object],
    x: int,
    y: int,
    width: int,
    height: int,
    axis_class: str,
    value_class: str,
) -> Sequence[str]:
    bottom = y + height
    group_width = width / 3.0
    bar_width = 46
    bar_gap = 16
    parts = []
    expel_points = []
    reflection_points = []

    for index, website in enumerate(panel["website_versions"]):
        center_x = x + group_width * index + group_width / 2.0
        parts.extend(_multiline_text(int(center_x), bottom + 32, [website["label"], website["sublabel"]], axis_class))

        series_order = [key for key in ("no_rules", "expel_rules", "best_reflection_rules") if key in website["series"]]
        total_width = len(series_order) * bar_width + (len(series_order) - 1) * bar_gap
        start_x = center_x - total_width / 2.0
        for series_index, series_key in enumerate(series_order):
            payload = website["series"][series_key]
            bar_height = height * payload["rate"]
            bar_x = start_x + series_index * (bar_width + bar_gap)
            bar_y = bottom - bar_height
            color = SERIES_COLORS[series_key]
            parts.append(
                '<rect x="%.1f" y="%.1f" width="%d" height="%.1f" rx="6" fill="%s"/>' % (
                    bar_x,
                    bar_y,
                    bar_width,
                    bar_height,
                    color,
                )
            )
            label_y = bar_y - 10
            parts.append(
                '<text x="%.1f" y="%.1f" class="%s" text-anchor="middle">%s</text>' % (
                    bar_x + bar_width / 2.0,
                    label_y,
                    value_class,
                    _escape("%.1f%%" % (payload["rate"] * 100.0)),
                )
            )
            if series_key == "expel_rules":
                expel_points.append((bar_x + bar_width / 2.0, bar_y))
            elif series_key == "best_reflection_rules":
                reflection_points.append((bar_x + bar_width / 2.0, bar_y))

    if len(expel_points) >= 2:
        parts.append(
            '<polyline fill="none" stroke="%s" stroke-width="3" points="%s"/>' % (
                SERIES_COLORS["expel_rules"],
                " ".join("%.1f,%.1f" % point for point in expel_points),
            )
        )
        for cx, cy in expel_points:
            parts.append(
                '<circle cx="%.1f" cy="%.1f" r="5" fill="%s" stroke="#ffffff" stroke-width="2"/>' % (
                    cx,
                    cy,
                    SERIES_COLORS["expel_rules"],
                )
            )
    if len(reflection_points) >= 2:
        parts.append(
            '<polyline fill="none" stroke="%s" stroke-width="3" points="%s"/>' % (
                SERIES_COLORS["best_reflection_rules"],
                " ".join("%.1f,%.1f" % point for point in reflection_points),
            )
        )
        for cx, cy in reflection_points:
            parts.append(
                '<circle cx="%.1f" cy="%.1f" r="5" fill="%s" stroke="#ffffff" stroke-width="2"/>' % (
                    cx,
                    cy,
                    SERIES_COLORS["best_reflection_rules"],
                )
            )
    return parts


def _multiline_text(x: int, y: int, lines: Sequence[str], css_class: str) -> Sequence[str]:
    parts = ['<text x="%d" y="%d" class="%s" text-anchor="middle">' % (x, y, css_class)]
    for index, line in enumerate(lines):
        dy = 0 if index == 0 else 14
        parts.append('<tspan x="%d" dy="%d">%s</tspan>' % (x, dy, _escape(line)))
    parts.append("</text>")
    return parts


def _render_panel_table(panel: Mapping[str, object]) -> str:
    lines = [
        "| Website Version | No Rules | ExpeL Rules | Best Reflection Rules |",
        "| --- | ---: | ---: | ---: |",
    ]
    for website in panel["website_versions"]:
        cells = [website["label"]]
        for key in ("no_rules", "expel_rules", "best_reflection_rules"):
            if key in website["series"]:
                cells.append(_format_series_cell(website["series"][key]))
            else:
                cells.append("N/A")
        lines.append("| %s |" % " | ".join(cells))
    return "\n".join(lines)


def _format_series_cell(payload: Mapping[str, object]) -> str:
    return "%d/%d (%.1f%%)" % (
        payload["successes"],
        payload["total"],
        payload["rate"] * 100.0,
    )


def _load_json(path: Path) -> Mapping[str, object]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def _escape(text: object) -> str:
    return html.escape(str(text), quote=True)


__all__ = [
    "build_poster_summary",
    "main",
    "parse_args",
    "render_main_panel_svg",
    "render_reflection_panel_svg",
    "render_report_markdown",
    "write_poster_assets",
]
