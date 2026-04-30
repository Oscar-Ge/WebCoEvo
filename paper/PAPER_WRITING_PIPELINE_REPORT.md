# Paper Writing Pipeline Report

**Input**: `/home/gecm/webAgentBenchmark/paper` plus WebCoEvo reports/results under `/home/gecm/WebCoEvo`
**Venue style**: existing ACL-style LaTeX project
**Date**: 2026-04-26

## Pipeline Summary

| Phase | Status | Output |
| --- | --- | --- |
| 1. Paper Plan | Done | `PAPER_PLAN.md` |
| 2. Figures/Tables | Done | `figures/latex_includes.tex` |
| 3. LaTeX Writing | Done | `main.tex`, `sections/*.tex`, appendix |
| 4. Compilation | Done | `main.pdf` |
| 5. Improvement Pass | Done | Compiler cleanup for citations, references, and overfull boxes |

## Key Upgrades

- Reframed the paper around WebCoEvo as an auditable co-evolution loop.
- Replaced the older hardv3/non-access result story with the newer April 17-18 WebCoEvo results.
- Added the current headline numbers: V2.4 reaches 65/68 on Focus20 hardv3, and V2.4/V2.4.1 tie at 97/167 on held-out TaskBank36 hardv3.
- Added the V2.4.1 method story: GPT-5.4-assisted transition mining edits two rules, but promotion remains non-monotonic.
- Rebuilt the appendix around current local artifacts and full hardv3 per-drift tables.

## Verification

- Ran `pdflatex`, `bibtex`, and final `pdflatex` pass in `/home/gecm/WebCoEvo/paper`.
- Final `main.log` has no undefined citations, undefined references, rerun warnings, or overfull boxes.
- `main.pdf` was generated successfully as a PDF document.

## Deliverables

- `main.pdf` - compiled upgraded paper.
- `main.tex` - paper entrypoint.
- `sections/*.tex` - rewritten method, setup, results, discussion, appendix, and updated abstract/introduction.
- `figures/latex_includes.tex` - self-contained LaTeX figure/table floats from WebCoEvo results.
