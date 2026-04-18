# Hardv3 Matrix Report Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate a reusable Markdown report and two benchmark-specific main figures for the hardv3 XVR matrix results.

**Architecture:** Add a small report-generation module that discovers the latest result shards, aggregates success statistics by benchmark, rule setting, and drift type, renders SVG figures, and writes a polished Markdown report. Keep the implementation pure-Python so it can run in a minimal environment without extra plotting dependencies.

**Tech Stack:** Python `json`/`argparse`/`pathlib`/`re`, pytest, repo-local scripts under `scripts/`, Markdown assets under `docs/reports/`, SVG output under `figures/`.

---

### Task 1: Freeze aggregation expectations with tests

**Files:**
- Create: `tests/test_hardv3_matrix_report.py`
- Create: `linkding_xvr_minimal/reporting_hardv3.py`

1. Write a failing test for latest-run discovery across `expel_only` and `v2_*` result roots.
2. Write a failing test for benchmark/rule/drift aggregation using tiny fixture JSONL files.
3. Run `python3 -m pytest tests/test_hardv3_matrix_report.py -q` and confirm failure.
4. Implement the minimal aggregation helpers to make the test pass.
5. Re-run the focused test.

### Task 2: Add figure and report rendering

**Files:**
- Modify: `linkding_xvr_minimal/reporting_hardv3.py`
- Create: `scripts/reporting/generate_hardv3_matrix_report.py`

1. Write a failing test for SVG generation and Markdown report content.
2. Implement benchmark-specific two-panel SVG figures:
   `left = 7 drift categories`, `right = benchmark-level overall comparison`.
3. Implement Markdown rendering with executive summary, figure embeds, and result tables.
4. Re-run `python3 -m pytest tests/test_hardv3_matrix_report.py -q`.

### Task 3: Generate real assets

**Files:**
- Create: `figures/focus20_hardv3_xvr_matrix.svg`
- Create: `figures/taskbank36_hardv3_xvr_matrix.svg`
- Create: `docs/reports/2026-04-17-hardv3-xvr-matrix-report.md`

1. Run the report-generation script on the current result directories.
2. Check that both SVGs and the Markdown report are written to the expected paths.
3. Spot-check the reported success rates against the known matrix values.

### Task 4: Verify before completion

**Files:**
- No new files expected.

1. Run the focused pytest suite.
2. Re-run the generation script.
3. Confirm the assets exist and the report references the generated figures correctly.
