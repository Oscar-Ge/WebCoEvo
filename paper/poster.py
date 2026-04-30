#!/usr/bin/env python3
"""
WebCoEvo — Poster-Ready Figures v3
===================================
- Maximum font size, zero overlap
- Simplified labels: V1 / V2 / V3, no codenames
- 600 DPI for poster printing
- Two figures: Hero panel + Heatmap
"""

import json, os, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_report_dir():
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
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def load_json(name):
    with open(os.path.join(REPORT_DIR, name), encoding="utf-8") as f:
        return json.load(f)

poster = load_json("2026-04-18-poster-summary-figures-summary.json")
hardv3 = load_json("2026-04-17-hardv3-xvr-matrix-summary.json")

# ── Colors ──
C_NO_RULES = "#B0BEC5"
C_EXPEL    = "#D97706"
C_REFLECT  = "#2563EB"
C_RV1 = "#1D4ED8"
C_RV2 = "#60A5FA"
C_RV3 = "#818CF8"
C_RV4 = "#059669"

DRIFT_ORDER  = ["access","content","functional","process","runtime","structural","surface"]
DRIFT_LABELS = {d: d.capitalize() for d in DRIFT_ORDER}
RULE_KEYS    = ["expel_only","v2_4","v2_4_1","v2_5","v2_6"]
RULE_SHORT   = ["ExpeL","R1","R4","R2","R3"]

DPI = 600

def save(fig, name):
    for ext in ("png", "pdf"):
        p = os.path.join(OUTPUT_DIR, f"{name}.{ext}")
        fig.savefig(p, dpi=DPI, facecolor="white", edgecolor="none")
        print(f"  ✅ {p}")
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════
# FIGURE A — Hero panel
# ═══════════════════════════════════════════════════════════════
def figure_a():
    print("\n📊 Figure A: Hero Panel")

    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["DejaVu Serif","Times New Roman"],
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.13, "grid.linestyle": "-",
    })

    fig = plt.figure(figsize=(20, 7.5))
    gs = gridspec.GridSpec(1, 3, width_ratios=[1, 1, 0.65],
                           wspace=0.22, left=0.06, right=0.97,
                           top=0.82, bottom=0.10)

    panels = [
        ("training_task_sets_main",              "Training Tasks",     gs[0]),
        ("heldout_validation_task_sets_main",     "Validation Tasks",   gs[1]),
    ]

    for panel_key, title, gs_slot in panels:
        ax = fig.add_subplot(gs_slot)
        panel_data = poster["main_panels"][panel_key]
        websites = panel_data["website_versions"]
        x = np.arange(len(websites))
        bw = 0.25

        no_rules = [w["series"].get("no_rules",{}).get("rate") for w in websites]
        expel    = [w["series"].get("expel_rules",{}).get("rate") for w in websites]
        reflect  = [w["series"].get("best_reflection_rules",{}).get("rate") for w in websites]

        bar_specs = [
            ("No Rules",    no_rules, C_NO_RULES, -bw),
            ("ExpeL",       expel,    C_EXPEL,     0),
            ("Reflection",  reflect,  C_REFLECT,   bw),
        ]

        for label, rates, color, offset in bar_specs:
            bxs, bys = [], []
            for i, r in enumerate(rates):
                if r is not None:
                    bxs.append(x[i] + offset)
                    bys.append(r * 100)
            if bys:
                ax.bar(bxs, bys, bw * 0.88, color=color,
                       edgecolor="white", linewidth=0.8,
                       zorder=3, alpha=0.92, label=label)
                for bx, by in zip(bxs, bys):
                    if by >= 30:
                        ax.text(bx, by - 2.5, f"{by:.1f}",
                                ha="center", va="top",
                                fontsize=13, fontweight="bold", color="white")
                    else:
                        ax.text(bx, by + 1.5, f"{by:.1f}",
                                ha="center", va="bottom",
                                fontsize=13, fontweight="bold", color="#333")

        # Trend lines — aligned to bar centers
        for rates, color, off in [(expel, C_EXPEL, 0),
                                   (reflect, C_REFLECT, bw)]:
            lx, ly = [], []
            for i, r in enumerate(rates):
                if r is not None:
                    lx.append(x[i] + off)
                    ly.append(r * 100)
            if len(ly) >= 2:
                ax.plot(lx, ly, color=color, linewidth=2.0,
                        linestyle="--", zorder=4, alpha=0.40)

        # Axis — simplified
        ax.set_xticks(x)
        ax.set_xticklabels(["V1", "V2", "V3"], fontsize=16, fontweight="bold")
        ax.set_ylim(0, 112)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
        ax.tick_params(axis="y", labelsize=14)
        ax.set_title(title, fontsize=20, fontweight="bold", pad=14)
        ax.set_xlabel("Website", fontsize=16, fontweight="bold", labelpad=6)
        if "Training" in title:
            ax.set_ylabel("Success Rate", fontsize=16, fontweight="bold")

    # ── Sub-panel C: Reflection iterations ──
    ax_r = fig.add_subplot(gs[2])
    ref_panels = [
        ("training_task_sets_reflection_v3",              "Train."),
        ("heldout_validation_task_sets_reflection_v3",    "Valid."),
    ]
    display_order = ["v2_4", "v2_4_1", "v2_5", "v2_6"]
    color_by_key = {"v2_4": C_RV1, "v2_4_1": C_RV4, "v2_5": C_RV2, "v2_6": C_RV3}
    v_labels = ["R1","R4","R2","R3"]

    group_x = np.array([0, 1.4])
    n_bars = 4
    bw2 = 0.24

    for gi, (pk, glabel) in enumerate(ref_panels):
        series_by_key = {item["key"]: item for item in poster["reflection_panels"][pk]["series"]}
        series = [series_by_key[k] for k in display_order if k in series_by_key]
        for bi, item in enumerate(series):
            rate = item["rate"] * 100
            off = (bi - n_bars/2 + 0.5) * bw2
            bx = group_x[gi] + off
            bar = ax_r.bar(bx, rate, bw2*0.88, color=color_by_key[item["key"]],
                           edgecolor="white", linewidth=0.8, zorder=3)
            if item["is_best"]:
                bar[0].set_edgecolor("#0F172A")
                bar[0].set_linewidth(2.5)
            if rate >= 25:
                ax_r.text(bx, rate - 2, f"{rate:.0f}",
                          ha="center", va="top",
                          fontsize=12, fontweight="bold", color="white")
            else:
                ax_r.text(bx, rate + 1, f"{rate:.0f}",
                          ha="center", va="bottom",
                          fontsize=12, fontweight="bold", color="#333")

    ax_r.set_xticks(group_x)
    ax_r.set_xticklabels(["Train.", "Valid."], fontsize=15, fontweight="bold")
    ax_r.set_ylim(0, 112)
    ax_r.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax_r.tick_params(axis="y", labelsize=14)
    ax_r.set_title("Reflection Rule Sets\non Website V3",
                    fontsize=18, fontweight="bold", pad=12, linespacing=1.25)

    ref_handles = [mpatches.Patch(facecolor=color_by_key[k], edgecolor="white", label=l)
                   for k, l in zip(display_order, v_labels)]
    ax_r.legend(handles=ref_handles, loc="upper right", fontsize=13,
                ncol=2, handlelength=1.2, handletextpad=0.3,
                columnspacing=0.6, frameon=True, fancybox=True,
                edgecolor="#E5E7EB", facecolor="white")

    # ── Shared legend ──
    main_h = [
        mpatches.Patch(facecolor=C_NO_RULES, edgecolor="white", label="No Rules"),
        mpatches.Patch(facecolor=C_EXPEL,    edgecolor="white", label="ExpeL"),
        mpatches.Patch(facecolor=C_REFLECT,  edgecolor="white", label="Reflection"),
    ]
    fig.legend(handles=main_h, loc="upper center", ncol=3,
               fontsize=16, bbox_to_anchor=(0.42, 0.97), frameon=False,
               handlelength=2.0, handletextpad=0.5, columnspacing=2.5)

    save(fig, "poster_fig_a_hero")


# ═══════════════════════════════════════════════════════════════
# FIGURE B — Heatmap
# ═══════════════════════════════════════════════════════════════
def figure_b():
    print("\n📊 Figure B: Heatmap")

    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["DejaVu Serif","Times New Roman"],
        "axes.spines.top": True, "axes.spines.right": True,
        "axes.grid": False,
    })

    fig, axes = plt.subplots(1, 2, figsize=(18, 5.8))
    fig.subplots_adjust(wspace=0.32, left=0.09, right=0.88,
                        top=0.84, bottom=0.16)

    benchmarks = [
        ("focus20_hardv3",    "Training Tasks"),
        ("taskbank36_hardv3", "Validation Tasks"),
    ]

    for ax_idx, (bk, title) in enumerate(benchmarks):
        ax = axes[ax_idx]
        settings = hardv3["benchmarks"][bk]["settings"]

        mat = np.zeros((len(RULE_KEYS), len(DRIFT_ORDER)))
        for i, rk in enumerate(RULE_KEYS):
            for j, dk in enumerate(DRIFT_ORDER):
                mat[i, j] = settings[rk]["by_drift"][dk]["rate"] * 100

        im = ax.imshow(mat, cmap="YlOrRd", aspect="auto", vmin=0, vmax=100)

        for i in range(len(RULE_KEYS)):
            for j in range(len(DRIFT_ORDER)):
                val = mat[i, j]
                tc = "white" if val > 55 else "#333"
                fw = "bold" if val >= 85 else "normal"
                ax.text(j, i, f"{val:.0f}", ha="center", va="center",
                        fontsize=14, fontweight=fw, color=tc)

        ax.set_xticks(np.arange(len(DRIFT_ORDER)))
        ax.set_xticklabels([DRIFT_LABELS[d] for d in DRIFT_ORDER],
                           fontsize=12, rotation=35, ha="right")

        # Y labels: rule name [avg%]
        ylabels = []
        for i, rk in enumerate(RULE_KEYS):
            avg = settings[rk]["overall_rate"] * 100
            ylabels.append(f"{RULE_SHORT[i]}  [{avg:.0f}%]")
        ax.set_yticks(np.arange(len(RULE_KEYS)))
        ax.set_yticklabels(ylabels, fontsize=13)
        ax.set_title(title, fontsize=20, fontweight="bold", pad=12)
        ax.tick_params(axis="both", length=0)

    cbar = fig.colorbar(im, ax=axes, shrink=0.85, aspect=22, pad=0.03)
    cbar.set_label("Success Rate (%)", fontsize=14, fontweight="bold")
    cbar.ax.tick_params(labelsize=12)

    fig.suptitle("Success Rate by Rule × Drift Type on Website V3",
                 fontsize=22, fontweight="bold", y=0.97, color="#111827")

    save(fig, "poster_fig_b_heatmap")


if __name__ == "__main__":
    print("=" * 60)
    print("WebCoEvo — Poster Figures v3 (600 DPI)")
    print("=" * 60)
    figure_a()
    figure_b()
    print("\n✅ Done!", OUTPUT_DIR)
