#!/usr/bin/env python3
"""
WebCoEvo — Publication-Ready Poster Visualizations
===================================================
Generates 6 high-quality figures from the WebCoEvo experiment data:
  1. Main poster panel: ExpeL vs Reflection across website versions
  2. Reflection rule iteration comparison (bar chart)
  3. Radar chart: drift-type performance on Website V3
  4. Heatmap: rule version × drift type success rates
  5. Website version trajectory lines
  6. Control vs First-Modified per-drift breakdown
"""

import json
import os
import sys
import math
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.ticker as mticker

# ─────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_report_dir():
    """Find WebCoEvo docs/reports from either a standalone or in-repo paper dir."""
    override = os.environ.get("WEBCOEVO_REPORT_DIR")
    if override:
        report_dir = os.path.abspath(override)
        if os.path.isdir(report_dir):
            return report_dir
        raise FileNotFoundError(f"WEBCOEVO_REPORT_DIR does not exist: {report_dir}")

    candidates = [
        os.path.join(SCRIPT_DIR, "WebCoEvo", "docs", "reports"),
        os.path.join(os.path.dirname(SCRIPT_DIR), "docs", "reports"),
    ]

    current = SCRIPT_DIR
    while True:
        candidates.append(os.path.join(current, "docs", "reports"))
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    for report_dir in candidates:
        report_dir = os.path.abspath(report_dir)
        if os.path.isdir(report_dir):
            return report_dir

    raise FileNotFoundError(
        "Could not locate WebCoEvo docs/reports. "
        "Set WEBCOEVO_REPORT_DIR to the directory containing the summary JSON files."
    )


REPORT_DIR = find_report_dir()
REPO_DIR = os.path.abspath(os.path.join(REPORT_DIR, os.pardir, os.pardir))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────
# Load data
# ─────────────────────────────────────────────────────────────────
def load_json(name):
    path = os.path.join(REPORT_DIR, name)
    with open(path, encoding="utf-8") as f:
        return json.load(f)

poster_data = load_json("2026-04-18-poster-summary-figures-summary.json")
hardv3_data = load_json("2026-04-17-hardv3-xvr-matrix-summary.json")
version_line_data = load_json("2026-04-18-website-version-line-summary.json")
umich_data = load_json("2026-04-18-umich-qwen3-rule-comparison-summary.json")

# ─────────────────────────────────────────────────────────────────
# Publication style
# ─────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif", "Times New Roman", "Georgia"],
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "axes.labelsize": 12,
    "legend.fontsize": 10,
    "legend.frameon": False,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.15,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.18,
    "grid.linestyle": "-",
    "lines.linewidth": 2.2,
    "lines.markersize": 7,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
})

# Color palette — "Ocean Dusk" + colorblind-safe accents
C_NO_RULES   = "#B0BEC5"   # cool gray
C_EXPEL      = "#D97706"   # amber
C_REFLECT    = "#2563EB"   # blue
C_REFLECT_V1 = "#1D4ED8"   # deep blue
C_REFLECT_V2 = "#60A5FA"   # sky blue
C_REFLECT_V3 = "#818CF8"   # indigo
C_REFLECT_V4 = "#059669"   # green
C_RADAR_R1   = "#1D4ED8"   # deep blue
C_RADAR_R4   = "#059669"   # green, separated from R1 in radar plots
C_ACCENT     = "#E76F51"   # coral

DRIFT_COLORS = {
    "access":     "#264653",
    "content":    "#2A9D8F",
    "functional": "#E9C46A",
    "process":    "#F4A261",
    "runtime":    "#E76F51",
    "structural": "#0072B2",
    "surface":    "#56B4E9",
}

RULE_COLORS = {
    "expel_only": C_EXPEL,
    "v2_4":       C_REFLECT_V1,
    "v2_5":       C_REFLECT_V2,
    "v2_6":       C_REFLECT_V3,
    "v2_4_1":     C_REFLECT_V4,
}

RULE_LABELS = {
    "expel_only": "ExpeL Only",
    "v2_4":       "R1",
    "v2_4_1":     "R4",
    "v2_5":       "R2",
    "v2_6":       "R3",
}

DRIFT_ORDER = ["access", "content", "functional", "process", "runtime", "structural", "surface"]
DRIFT_LABELS = {d: d.capitalize() for d in DRIFT_ORDER}


def save_fig(fig, name, aliases=None):
    """Save figure as both PNG and PDF."""
    names = [name] + list(aliases or [])
    for output_name in names:
        png_path = os.path.join(OUTPUT_DIR, f"{output_name}.png")
        pdf_path = os.path.join(OUTPUT_DIR, f"{output_name}.pdf")
        fig.savefig(png_path, dpi=300, facecolor="white", edgecolor="none")
        fig.savefig(pdf_path, facecolor="white", edgecolor="none")
        print(f"  ✅ Saved {png_path}")
        print(f"  ✅ Saved {pdf_path}")
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════
# FIGURE 1: Main Poster Panel — ExpeL vs Reflection across versions
# ═══════════════════════════════════════════════════════════════════
def figure1_main_poster():
    print("\n📊 Figure 1: Main Poster Panel — ExpeL vs Reflection")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), sharey=True)
    fig.subplots_adjust(wspace=0.08)

    panels = [
        ("training_task_sets_main", "Training Task Sets (Focus20, n=68)"),
        ("heldout_validation_task_sets_main", "Held-out Validation (TaskBank36, n=167)"),
    ]

    for ax_idx, (panel_key, title) in enumerate(panels):
        ax = axes[ax_idx]
        panel = poster_data["main_panels"][panel_key]
        websites = panel["website_versions"]

        x_positions = np.arange(len(websites))
        bar_width = 0.22

        # Collect series data
        no_rules_rates = []
        expel_rates = []
        reflect_rates = []

        for w in websites:
            series = w["series"]
            no_rules_rates.append(series.get("no_rules", {}).get("rate", None))
            expel_rates.append(series.get("expel_rules", {}).get("rate", None))
            reflect_rates.append(series.get("best_reflection_rules", {}).get("rate", None))

        # Plot bars
        series_data = [
            ("No Rules", no_rules_rates, C_NO_RULES),
            ("ExpeL Rules", expel_rates, C_EXPEL),
            ("Best Reflection", reflect_rates, C_REFLECT),
        ]

        offsets = [-bar_width, 0, bar_width]
        for (label, rates, color), offset in zip(series_data, offsets):
            valid_x = []
            valid_y = []
            for i, r in enumerate(rates):
                if r is not None:
                    valid_x.append(x_positions[i] + offset)
                    valid_y.append(r * 100)
            if valid_y:
                bars = ax.bar(valid_x, valid_y, bar_width * 0.88, label=label,
                              color=color, edgecolor="white", linewidth=0.8,
                              zorder=3, alpha=0.92)
                for bx, by in zip(valid_x, valid_y):
                    ax.text(bx, by + 1.2, f"{by:.1f}%", ha="center", va="bottom",
                            fontsize=8, fontweight="bold", color="#333333")

        # Trend lines for ExpeL and Reflection
        for rates, color, marker in [
            (expel_rates, C_EXPEL, "o"),
            (reflect_rates, C_REFLECT, "s"),
        ]:
            valid_x = []
            valid_y = []
            for i, r in enumerate(rates):
                if r is not None:
                    valid_x.append(x_positions[i])
                    valid_y.append(r * 100)
            if len(valid_y) >= 2:
                ax.plot(valid_x, valid_y, color=color, marker=marker,
                        markersize=6, linewidth=2.5, zorder=5, alpha=0.7,
                        markeredgecolor="white", markeredgewidth=1.5)

        # X-axis labels
        xlabels = [f"{w['label']}\n({w['sublabel']})" for w in websites]
        ax.set_xticks(x_positions)
        ax.set_xticklabels(xlabels, fontsize=9)
        ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
        ax.set_ylim(0, 108)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))

        if ax_idx == 0:
            ax.set_ylabel("Task Success Rate", fontsize=12, fontweight="bold")

        # Add subtle background shading for each website version
        for i in range(len(websites)):
            if i % 2 == 0:
                ax.axvspan(i - 0.42, i + 0.42, alpha=0.04, color="#2563EB", zorder=0)

    # Shared legend
    handles = [
        mpatches.Patch(facecolor=C_NO_RULES, edgecolor="white", label="No Rules"),
        mpatches.Patch(facecolor=C_EXPEL, edgecolor="white", label="ExpeL Rules"),
        mpatches.Patch(facecolor=C_REFLECT, edgecolor="white", label="Best Reflection Rules"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=3, fontsize=11,
               bbox_to_anchor=(0.5, 1.02), frameon=False)

    fig.suptitle("WebCoEvo: Rule Robustness Under Website Evolution",
                 fontsize=16, fontweight="bold", y=1.08,
                 color="#111827")

    save_fig(fig, "fig1_main_poster_panel")


# ═══════════════════════════════════════════════════════════════════
# FIGURE 2: Reflection Rule Iteration Comparison
# ═══════════════════════════════════════════════════════════════════
def figure2_reflection_iteration():
    print("\n📊 Figure 2: Reflection Rule Iteration on Website V3")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    fig.subplots_adjust(wspace=0.08)

    panels = [
        ("training_task_sets_reflection_v3", "Training Task Sets"),
        ("heldout_validation_task_sets_reflection_v3", "Held-out Validation"),
    ]

    display_order = ["v2_4", "v2_5", "v2_6", "v2_4_1"]
    display_colors = {
        "v2_4": C_REFLECT_V1,
        "v2_4_1": C_REFLECT_V4,
        "v2_5": C_REFLECT_V2,
        "v2_6": C_REFLECT_V3,
    }

    for ax_idx, (panel_key, title) in enumerate(panels):
        ax = axes[ax_idx]
        panel = poster_data["reflection_panels"][panel_key]
        series_by_key = {s.get("key"): s for s in panel["series"]}
        series = [series_by_key[k] for k in display_order if k in series_by_key]

        display_names = {"v2_4": "R1", "v2_4_1": "R4", "v2_5": "R2", "v2_6": "R3"}
        labels = [display_names.get(s.get("key"), s["label"]) for s in series]
        rates = [s["rate"] * 100 for s in series]
        is_best = [s["is_best"] for s in series]
        colors = [display_colors[s.get("key")] for s in series]

        x = np.arange(len(labels))
        bars = ax.bar(x, rates, width=0.6, color=colors, edgecolor="white",
                      linewidth=1.2, zorder=3, alpha=0.92)

        # Highlight best with bold border
        for i, (bar, best) in enumerate(zip(bars, is_best)):
            if best:
                bar.set_edgecolor("#0F172A")
                bar.set_linewidth(2.5)

        # Value labels
        for i, (r, best) in enumerate(zip(rates, is_best)):
            weight = "bold" if best else "normal"
            ax.text(i, r + 1.2, f"{r:.1f}%", ha="center", va="bottom",
                    fontsize=10, fontweight=weight, color="#111827")

        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=11)
        ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
        ax.set_ylim(0, 108)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))

        if ax_idx == 0:
            ax.set_ylabel("Success Rate on Website V3", fontsize=12, fontweight="bold")

        # Override stale report wording after renaming rule sets by reflection time.
        if panel_key == "training_task_sets_reflection_v3":
            takeaway = "Not monotonic: R1 remains best"
        else:
            takeaway = "Not monotonic: R1 and R4 tie"
        ax.annotate(takeaway, xy=(0.5, -0.18), xycoords="axes fraction",
                    ha="center", fontsize=9, fontstyle="italic", color="#6B7280")

    fig.suptitle("Reflection Rule Iterations on Website V3\n"
                 "Later iterations are not guaranteed to be stronger",
                 fontsize=14, fontweight="bold", y=1.04, color="#111827")

    save_fig(fig, "fig2_reflection_iteration")


# ═══════════════════════════════════════════════════════════════════
# FIGURE 3: Radar Chart — Drift-Type Performance on Website V3
# ═══════════════════════════════════════════════════════════════════
def figure3_radar_chart():
    print("\n📊 Figure 3: Radar Chart — Drift-Type Performance on Website V3")

    fig, axes = plt.subplots(1, 2, figsize=(14, 6),
                              subplot_kw=dict(polar=True))
    fig.subplots_adjust(wspace=0.45, top=0.88, bottom=0.16)

    benchmarks = [
        ("focus20_hardv3", "Training Tasks"),
        ("taskbank36_hardv3", "Held-out Validation"),
    ]

    rule_keys = ["expel_only", "v2_4", "v2_4_1"]
    rule_labels_short = {"expel_only": "ExpeL-style", "v2_4": "R1", "v2_4_1": "R4"}
    rule_colors = {"expel_only": C_EXPEL, "v2_4": C_RADAR_R1, "v2_4_1": C_RADAR_R4}
    rule_markers = {"expel_only": "o", "v2_4": "s", "v2_4_1": "D"}

    for ax_idx, (bench_key, title) in enumerate(benchmarks):
        ax = axes[ax_idx]
        bench = hardv3_data["benchmarks"][bench_key]
        settings = bench["settings"]

        categories = [DRIFT_LABELS[d] for d in DRIFT_ORDER]
        N = len(categories)
        angles = [n / float(N) * 2 * math.pi for n in range(N)]
        angles += angles[:1]  # close the polygon

        # Set up the radar
        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_rlabel_position(30)

        # Draw gridlines
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(["20%", "40%", "60%", "80%", "100%"],
                           fontsize=7, color="#6B7280")
        ax.set_ylim(0, 105)

        # Category labels
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=9, fontweight="bold")

        # Plot each rule version
        for rule_key in rule_keys:
            if rule_key not in settings:
                continue
            drift_data = settings[rule_key]["by_drift"]
            values = [drift_data[d]["rate"] * 100 for d in DRIFT_ORDER]
            values += values[:1]

            ax.plot(angles, values, color=rule_colors[rule_key],
                    linewidth=2.2, marker=rule_markers[rule_key],
                    markersize=5, label=rule_labels_short[rule_key],
                    markeredgecolor="white", markeredgewidth=1)
            ax.fill(angles, values, color=rule_colors[rule_key], alpha=0.08)

        ax.set_title(title, fontsize=13, fontweight="bold", pad=18, y=1.08)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.02),
               ncol=3, fontsize=10, frameon=True, fancybox=True,
               edgecolor="#E5E7EB", facecolor="white")

    save_fig(fig, "fig3_v3_drift_rule_profile", aliases=["fig3_radar_drift_performance"])


# ═══════════════════════════════════════════════════════════════════
# FIGURE 4: Heatmap — Rule Set × Drift Type
# ═══════════════════════════════════════════════════════════════════
def figure4_heatmap():
    print("\n📊 Figure 4: Heatmap — Rule Set × Drift Type")

    fig, axes = plt.subplots(1, 2, figsize=(16, 5.5))
    fig.subplots_adjust(wspace=0.25)

    benchmarks = [
        ("focus20_hardv3", "Training Tasks (Focus20)"),
        ("taskbank36_hardv3", "Held-out Validation (TaskBank36)"),
    ]

    rule_keys = ["expel_only", "v2_4", "v2_5", "v2_6", "v2_4_1"]
    rule_labels = ["ExpeL Only", "R1\n(v2.4)", "R2\n(v2.5)",
                   "R3\n(v2.6)", "R4\n(v2.4.1)"]

    for ax_idx, (bench_key, title) in enumerate(benchmarks):
        ax = axes[ax_idx]
        bench = hardv3_data["benchmarks"][bench_key]
        settings = bench["settings"]

        # Build matrix
        matrix = np.zeros((len(rule_keys), len(DRIFT_ORDER)))
        for i, rk in enumerate(rule_keys):
            drift_data = settings[rk]["by_drift"]
            for j, dk in enumerate(DRIFT_ORDER):
                matrix[i, j] = drift_data[dk]["rate"] * 100

        # Plot heatmap
        im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto", vmin=0, vmax=100)

        # Annotate cells
        for i in range(len(rule_keys)):
            for j in range(len(DRIFT_ORDER)):
                val = matrix[i, j]
                text_color = "white" if val > 65 else "#333333"
                fontw = "bold" if val >= 90 else "normal"
                ax.text(j, i, f"{val:.0f}%", ha="center", va="center",
                        fontsize=9, fontweight=fontw, color=text_color)

        ax.set_xticks(np.arange(len(DRIFT_ORDER)))
        ax.set_xticklabels([DRIFT_LABELS[d] for d in DRIFT_ORDER],
                           fontsize=9, rotation=30, ha="right")
        ax.set_yticks(np.arange(len(rule_keys)))
        ax.set_yticklabels(rule_labels, fontsize=9)
        ax.set_title(title, fontsize=13, fontweight="bold", pad=12)

        # Add overall rate in the y-axis labels (cleaner than separate badges)
        new_ylabels = []
        for i, rk in enumerate(rule_keys):
            overall = settings[rk]["overall_rate"] * 100
            new_ylabels.append(f"{rule_labels[i]}  [{overall:.1f}%]")
        ax.set_yticklabels(new_ylabels, fontsize=8.5)

    # Colorbar
    cbar = fig.colorbar(im, ax=axes, shrink=0.75, aspect=25, pad=0.04)
    cbar.set_label("Success Rate (%)", fontsize=10)
    cbar.ax.tick_params(labelsize=9)

    fig.suptitle("Success Rate by Rule Set × Drift Type on Website V3",
                 fontsize=15, fontweight="bold", y=1.02, color="#111827")

    save_fig(fig, "fig4_heatmap_rule_drift")


# ═══════════════════════════════════════════════════════════════════
# FIGURE 5: Website Version Trajectory Lines
# ═══════════════════════════════════════════════════════════════════
def figure5_version_lines():
    print("\n📊 Figure 5: Website Version Trajectory Lines")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
    fig.subplots_adjust(wspace=0.08)

    benchmarks = [
        ("focus20", "Training Tasks (Focus20)"),
        ("taskbank36", "Held-out Validation (TaskBank36)"),
    ]

    series_styles = {
        "expel_only": {"color": C_EXPEL, "marker": "o", "label": "ExpeL Only", "ls": "-"},
        "v2_4":       {"color": C_REFLECT, "marker": "s", "label": "R1 Reflection Rules", "ls": "-"},
    }

    for ax_idx, (bench_key, title) in enumerate(benchmarks):
        ax = axes[ax_idx]
        bench = version_line_data["benchmarks"][bench_key]
        x_labels = bench["x_labels"]
        x = np.arange(len(x_labels))

        for series_key in bench["series_order"]:
            style = series_styles[series_key]
            points = bench["series"][series_key]["points"]

            valid_x = []
            valid_y = []
            for i, pt in enumerate(points):
                if pt.get("available", False) and pt.get("rate") is not None:
                    valid_x.append(i)
                    valid_y.append(pt["rate"] * 100)

            if valid_y:
                ax.plot(valid_x, valid_y, color=style["color"],
                        marker=style["marker"], markersize=9,
                        linewidth=2.8, label=style["label"],
                        markeredgecolor="white", markeredgewidth=2,
                        linestyle=style["ls"], zorder=5)

                # Value annotations — offset based on series to avoid overlap
                for vx, vy in zip(valid_x, valid_y):
                    if series_key == "v2_4":
                        offset_y = 8
                        offset_x = 12
                    else:
                        offset_y = -14
                        offset_x = -12
                    ax.annotate(f"{vy:.1f}%", (vx, vy),
                                textcoords="offset points",
                                xytext=(offset_x, offset_y),
                                ha="center", fontsize=9, fontweight="bold",
                                color=style["color"],
                                bbox=dict(boxstyle="round,pad=0.15",
                                          facecolor="white", edgecolor="none",
                                          alpha=0.85))

            # Mark missing points
            for i, pt in enumerate(points):
                if not pt.get("available", False):
                    ax.plot(i, 50, marker="x", color="#CBD5E1",
                            markersize=10, markeredgewidth=2, zorder=3)
                    ax.annotate("N/A", (i, 50),
                                textcoords="offset points", xytext=(0, -12),
                                ha="center", fontsize=8, color="#9CA3AF")

        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, fontsize=10)
        ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
        ax.set_ylim(0, 108)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))

        if ax_idx == 0:
            ax.set_ylabel("Task Success Rate", fontsize=12, fontweight="bold")

        ax.legend(loc="lower left", fontsize=10, frameon=True,
                  fancybox=True, edgecolor="#E5E7EB", facecolor="white")

        # Add gradient background to show degradation
        ax.axvspan(-0.5, 0.5, alpha=0.04, color="#059669", zorder=0)  # green = original
        ax.axvspan(1.5, 2.5, alpha=0.04, color="#DC2626", zorder=0)   # red = hardest

    fig.suptitle("Performance Trajectory Across Website Versions\n"
                 "ExpeL collapses under drift while Reflection remains robust",
                 fontsize=14, fontweight="bold", y=1.06, color="#111827")

    save_fig(fig, "fig5_version_trajectory")


# ═══════════════════════════════════════════════════════════════════
# FIGURE 6: Control vs First-Modified Per-Drift Breakdown
# ═══════════════════════════════════════════════════════════════════
def figure6_control_vs_firstmod():
    print("\n📊 Figure 6: Control vs First-Modified Per-Drift Breakdown")

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.subplots_adjust(hspace=0.35, wspace=0.25)

    scenarios = [
        ("control_1450", "Control (Website V1)"),
        ("first_modified", "First-Modified (Website V2)"),
    ]
    bench_keys = [
        ("focus20", "Focus20 (Training)"),
        ("taskbank36", "TaskBank36 (Held-out)"),
    ]

    for row, (scenario_key, scenario_title) in enumerate(scenarios):
        scenario = umich_data["scenarios"][scenario_key]
        for col, (bench_key, bench_title) in enumerate(bench_keys):
            ax = axes[row][col]
            bench = scenario["benchmarks"][bench_key]
            settings = bench["settings"]

            setting_keys = scenario.get("setting_order",
                                        list(settings.keys()))

            x = np.arange(len(DRIFT_ORDER))
            n_settings = len(setting_keys)
            bar_width = 0.7 / n_settings

            setting_colors = {
                "no_rules": C_NO_RULES,
                "expel_only": C_EXPEL,
                "v2_4": C_REFLECT,
            }
            setting_labels = {
                "no_rules": "No Rules",
                "expel_only": "ExpeL Only",
                "v2_4": "R1 Reflection",
            }

            for i, sk in enumerate(setting_keys):
                drift_data = settings[sk]["by_drift"]
                rates = [drift_data[d]["rate"] * 100 for d in DRIFT_ORDER]
                offset = (i - n_settings / 2 + 0.5) * bar_width
                color = setting_colors.get(sk, DRIFT_COLORS.get(sk, "#888"))
                label = setting_labels.get(sk, sk)

                bars = ax.bar(x + offset, rates, bar_width * 0.88,
                              label=label, color=color,
                              edgecolor="white", linewidth=0.6, zorder=3)

                # Value labels on bars
                for bx, by in zip(x + offset, rates):
                    if by > 5:
                        ax.text(bx, by + 1, f"{by:.0f}", ha="center",
                                va="bottom", fontsize=7, color="#555")

            ax.set_xticks(x)
            ax.set_xticklabels([DRIFT_LABELS[d] for d in DRIFT_ORDER],
                               fontsize=9, rotation=25, ha="right")
            ax.set_ylim(0, 112)
            ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
            ax.set_title(f"{scenario_title} — {bench_title}",
                         fontsize=11, fontweight="bold", pad=8)

            if col == 0:
                ax.set_ylabel("Success Rate", fontsize=10, fontweight="bold")

            ax.legend(loc="upper right", fontsize=8, frameon=True,
                      fancybox=True, edgecolor="#E5E7EB")

    fig.suptitle("Per-Drift-Type Breakdown: Control vs First-Modified Websites\n"
                 "Qwen3-VL-30B Agent Evaluation",
                 fontsize=15, fontweight="bold", y=1.02, color="#111827")

    save_fig(fig, "fig6_control_vs_firstmod")


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("WebCoEvo — Generating Publication-Ready Visualizations")
    print("=" * 60)

    figure1_main_poster()
    figure2_reflection_iteration()
    figure3_radar_chart()
    figure4_heatmap()
    figure5_version_lines()
    figure6_control_vs_firstmod()

    print("\n" + "=" * 60)
    print("✅ All 6 figures generated successfully!")
    print(f"   Output directory: {OUTPUT_DIR}")
    print("=" * 60)
