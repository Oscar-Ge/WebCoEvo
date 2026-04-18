# Poster Summary Figures Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate two poster-ready summary figures plus a figure-rich report that explain website-version drift, ExpeL degradation, reflection-rule robustness, and non-monotonic reflection iteration.

**Architecture:** Reuse existing report summaries instead of recomputing raw experiment results. Read the existing control, first-modified, website-version-line, and hardv3 matrix summaries; normalize them into a compact poster-summary data model; render two SVG hybrid charts with small Website V3 reflection insets; then write a markdown report that embeds the figures and explains the intended poster narrative.

**Tech Stack:** Python `argparse`/`json`/`pathlib`, existing report JSON/Markdown artifacts, pytest, SVG text generation.

---

### Task 1: Add failing tests for poster-summary data and rendering

**Files:**
- Create: `tests/test_poster_summary_report.py`
- Reference: `docs/plans/2026-04-18-poster-summary-figures-design.md`

**Step 1: Write the failing test**

Add tests that build a tiny synthetic summary bundle and assert a new poster-summary module can:

- normalize two panels:
  - `training_task_sets`
  - `heldout_validation_task_sets`
- expose website-version labels:
  - `Website V1`
  - `Website V2`
  - `Website V3`
- expose reflection inset labels:
  - `Reflection Rules V1`
  - `Reflection Rules V2`
  - `Reflection Rules V3`
  - `Reflection Rules V4`
- render SVG containing:
  - `Training Task Sets`
  - `Held-out Validation Task Sets`
  - `Reflection Rules on Website V3`
  - `ExpeL Rules`
  - `Best Reflection Rules`
- render markdown report containing both figure paths and at least one key sentence about ExpeL degradation and reflection generalization.

**Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_poster_summary_report.py -q
```

Expected: FAIL because the poster-summary generator does not exist yet.

### Task 2: Implement the poster-summary generator

**Files:**
- Create: `linkding_xvr_minimal/reporting_poster_summary.py`
- Create: `scripts/reporting/generate_poster_summary_report.py`

**Step 1: Implement the minimal data model**

Read the existing report summaries and map them into:

- main-series values for:
  - `No Rules`
  - `ExpeL Rules`
  - `Best Reflection Rules`
- reflection inset values for `Reflection Rules V1` through `Reflection Rules V4`

**Step 2: Implement SVG rendering**

Generate:

- `figures/training_task_sets_poster_summary.svg`
- `figures/heldout_validation_task_sets_poster_summary.svg`

Each SVG should follow the approved design:

- grouped bars by website version
- line overlays for ExpeL and Best Reflection
- small Website V3 reflection inset
- poster-friendly labels only

**Step 3: Implement markdown report rendering**

Generate:

- `docs/reports/2026-04-18-poster-summary-figures-report.md`

The report should:

- embed both SVGs
- explain the three intended poster claims
- include the public mapping for website versions and reflection versions
- include concise presenter-oriented takeaways

**Step 4: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_poster_summary_report.py -q
```

Expected: PASS.

### Task 3: Regenerate real figures and verify content

**Files:**
- Output: `figures/training_task_sets_poster_summary.svg`
- Output: `figures/heldout_validation_task_sets_poster_summary.svg`
- Output: `docs/reports/2026-04-18-poster-summary-figures-report.md`

**Step 1: Run the real generator**

Run:

```bash
python3 scripts/reporting/generate_poster_summary_report.py
```

Expected: all three outputs are written successfully.

**Step 2: Verify generated content**

Run:

```bash
rg -n "Training Task Sets|Held-out Validation Task Sets|Reflection Rules on Website V3|ExpeL Rules|Best Reflection Rules" \
  figures/training_task_sets_poster_summary.svg \
  figures/heldout_validation_task_sets_poster_summary.svg \
  docs/reports/2026-04-18-poster-summary-figures-report.md
```

Expected: all key labels appear.

**Step 3: Run fresh tests**

Run:

```bash
python3 -m pytest tests/test_poster_summary_report.py -q
```

Expected: PASS.
