# Website Version Line Report

> This report merges the existing hardv3 matrix summary with the UMich Qwen3-VL rule-comparison summary.

## Setup

- Model: `Qwen/Qwen3-VL-30B-A3B-Instruct`
- Endpoint: `http://promaxgb10-d668.eecs.umich.edu:8000/v1`
- Website versions on the x-axis: `Control 1.45.0`, `First-Modified`, `Hardv3`.
- Two compared series: `ExpeL Only` and `V2.4`.

## Focus20

![Focus20 website version lines](../../figures/focus20_website_version_lines.svg)

For Focus20, `ExpeL Only` moves from `56/68 (82.4%)` on the control site to `60/68 (88.2%)` on `First-Modified`, then to `8/68 (11.8%)` on `Hardv3`.
`V2.4` has no control point in the current summaries, but it reaches `67/68 (98.5%)` on `First-Modified` and `65/68 (95.6%)` on `Hardv3`.

| Website Version | ExpeL Only | V2.4 |
| --- | ---: | ---: |
| Control 1.45.0 | 56/68 (82.4%) | N/A |
| First-Modified | 60/68 (88.2%) | 67/68 (98.5%) |
| Hardv3 | 8/68 (11.8%) | 65/68 (95.6%) |

## TaskBank36

![TaskBank36 website version lines](../../figures/taskbank36_website_version_lines.svg)

TaskBank36 control point is unavailable for a final success-rate comparison because the control baseline did not complete before the Slurm time limit. The completed website-version comparison therefore starts from `First-Modified` and continues to `Hardv3`.
`ExpeL Only` reaches `114/167 (68.3%)` on `First-Modified` and `66/167 (39.5%)` on `Hardv3`, while `V2.4` goes from `143/167 (85.6%)` on `First-Modified` to `97/167 (58.1%)` on `Hardv3`.

| Website Version | ExpeL Only | V2.4 |
| --- | ---: | ---: |
| Control 1.45.0 | N/A | N/A |
| First-Modified | 114/167 (68.3%) | 143/167 (85.6%) |
| Hardv3 | 66/167 (39.5%) | 97/167 (58.1%) |

## Interpretation

Across the completed comparisons, `First-Modified` is the strongest website version for both rule settings, and `V2.4` consistently stays above `ExpeL Only` whenever both are available. The hardest version for `ExpeL Only` is `Hardv3`, which pulls Focus20 down to `11.8%` and TaskBank36 to `39.5%`.

## Data Sources

- Hardv3 summary: `/home/gecm/WebCoEvo/docs/reports/2026-04-17-hardv3-xvr-matrix-summary.json`
- UMich rule-comparison summary: `/home/gecm/WebCoEvo/docs/reports/2026-04-18-umich-qwen3-rule-comparison-summary.json`
