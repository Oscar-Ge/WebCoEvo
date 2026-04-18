# Hardv3 XVR Matrix Report

> This report summarizes the latest hardv3 Linkding matrix runs and separates the training-like Focus20 benchmark from the held-out TaskBank36 benchmark.

## Executive Summary

On Focus20, the strongest configuration is `v2.4` at `65/68 = 95.6%`, which is `83.8` percentage points above the non-reflection baseline.

On TaskBank36, the strongest configurations are `v2.4` and `v2.4.1` at `97/167 = 58.1%`, which is `18.6` percentage points above the non-reflection baseline.

## Evaluation Setup

- `Focus20` is treated as the expanded training-like benchmark. Its figure should be read as a check of whether cross-version reflection rules improve performance near the rule-mining distribution.
- `TaskBank36` is treated as the held-out test benchmark. Its figure should be read as the primary generalization result on unseen task families.
- Each main figure uses the same two-panel layout: the left panel breaks success rate out by the seven version-drift categories, while the right panel shows the benchmark-level overall comparison.
- The `structural_functional` and `runtime_process` shards are split back into the underlying drift families using row-level `drift_type` annotations from the eval JSONL files.
- No cross-benchmark overall success rate is reported, because combining Focus20 and TaskBank36 would mix a training-like benchmark with a held-out evaluation benchmark.

## Focus20

![Focus20 hardv3 XVR matrix](../../figures/focus20_hardv3_xvr_matrix.svg)

Focus20 is treated as the training-like benchmark, so the main question is whether the rulebook improves performance broadly across the seven drift families near the rule-mining distribution. Non-reflection reaches `8/68 = 11.8%`. v2.4 reaches `65/68 = 95.6%`. v2.4.1 reaches `60/68 = 88.2%`. v2.5 reaches `60/68 = 88.2%`. v2.6 reaches `60/68 = 88.2%`. The best overall configuration is `v2.4`.

| Setting | Success / Total | Success Rate | Delta vs Non-reflection |
| --- | ---: | ---: | ---: |
| Non-reflection | 8/68 | 11.8% | — |
| v2.4 | 65/68 | 95.6% | +83.8 pts |
| v2.4.1 | 60/68 | 88.2% | +76.5 pts |
| v2.5 | 60/68 | 88.2% | +76.5 pts |
| v2.6 | 60/68 | 88.2% | +76.5 pts |

### Paper-Style Focus20 Result Paragraph

For Focus20, v2.4 obtains `65/68 = 95.6%`, compared with the non-reflection baseline at `8/68 = 11.8%`. This indicates that cross-version reflection rules deliver a large gain on the training-like benchmark, with `v2.4` at the top.

## TaskBank36

![TaskBank36 hardv3 XVR matrix](../../figures/taskbank36_hardv3_xvr_matrix.svg)

TaskBank36 is treated as the held-out test benchmark, so the main question is which rulebook carries over best to unseen task families. Non-reflection reaches `66/167 = 39.5%`. v2.4 reaches `97/167 = 58.1%`. v2.4.1 reaches `97/167 = 58.1%`. v2.5 reaches `61/167 = 36.5%`. v2.6 reaches `82/167 = 49.1%`. The best overall configurations are `v2.4` and `v2.4.1`.

| Setting | Success / Total | Success Rate | Delta vs Non-reflection |
| --- | ---: | ---: | ---: |
| Non-reflection | 66/167 | 39.5% | — |
| v2.4 | 97/167 | 58.1% | +18.6 pts |
| v2.4.1 | 97/167 | 58.1% | +18.6 pts |
| v2.5 | 61/167 | 36.5% | -3.0 pts |
| v2.6 | 82/167 | 49.1% | +9.6 pts |

### Paper-Style TaskBank36 Result Paragraph

For TaskBank36, `v2.4` and `v2.4.1` tie at `97/167 = 58.1%`, compared with the non-reflection baseline at `66/167 = 39.5%`. This confirms that the best cross-version rulebook transfers to the held-out benchmark, while `v2.5` underperforms the non-reflection baseline at `36.5%`.

## Cross-Benchmark Interpretation

The two benchmarks tell a consistent but not identical story. On the training-like Focus20 benchmark, all 4 XVR rulebooks substantially outperform non-reflection, with `v2.4` on top. On the held-out TaskBank36 benchmark, `v2.4` and `v2.4.1` remain the strongest settings, but the ranking is more discriminative: `v2.6` remains above non-reflection, whereas `v2.5` falls below the non-reflection baseline. This pattern suggests that the strongest rulebook is not only better at fitting the mined distribution, but also more robust when transferred to unseen tasks.

## Appendix A: Per-Drift Success Tables

### Focus20 Per-Drift Table

| Drift | n | Non-reflection | v2.4 | v2.4.1 | v2.5 | v2.6 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Access | 13 | 0/13 (0.0%) | 13/13 (100.0%) | 13/13 (100.0%) | 13/13 (100.0%) | 13/13 (100.0%) |
| Surface | 13 | 1/13 (7.7%) | 13/13 (100.0%) | 12/13 (92.3%) | 13/13 (100.0%) | 13/13 (100.0%) |
| Content | 9 | 2/9 (22.2%) | 7/9 (77.8%) | 6/9 (66.7%) | 5/9 (55.6%) | 4/9 (44.4%) |
| Structural | 6 | 3/6 (50.0%) | 6/6 (100.0%) | 5/6 (83.3%) | 6/6 (100.0%) | 6/6 (100.0%) |
| Functional | 5 | 0/5 (0.0%) | 4/5 (80.0%) | 3/5 (60.0%) | 3/5 (60.0%) | 3/5 (60.0%) |
| Runtime | 16 | 2/16 (12.5%) | 16/16 (100.0%) | 16/16 (100.0%) | 15/16 (93.8%) | 16/16 (100.0%) |
| Process | 6 | 0/6 (0.0%) | 6/6 (100.0%) | 5/6 (83.3%) | 5/6 (83.3%) | 5/6 (83.3%) |

### TaskBank36 Per-Drift Table

| Drift | n | Non-reflection | v2.4 | v2.4.1 | v2.5 | v2.6 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Access | 36 | 6/36 (16.7%) | 8/36 (22.2%) | 10/36 (27.8%) | 3/36 (8.3%) | 12/36 (33.3%) |
| Surface | 36 | 21/36 (58.3%) | 28/36 (77.8%) | 30/36 (83.3%) | 19/36 (52.8%) | 25/36 (69.4%) |
| Content | 14 | 11/14 (78.6%) | 7/14 (50.0%) | 10/14 (71.4%) | 5/14 (35.7%) | 6/14 (42.9%) |
| Structural | 13 | 2/13 (15.4%) | 6/13 (46.2%) | 5/13 (38.5%) | 4/13 (30.8%) | 4/13 (30.8%) |
| Functional | 13 | 3/13 (23.1%) | 7/13 (53.8%) | 4/13 (30.8%) | 3/13 (23.1%) | 3/13 (23.1%) |
| Runtime | 36 | 20/36 (55.6%) | 28/36 (77.8%) | 29/36 (80.6%) | 22/36 (61.1%) | 24/36 (66.7%) |
| Process | 19 | 3/19 (15.8%) | 13/19 (68.4%) | 9/19 (47.4%) | 5/19 (26.3%) | 8/19 (42.1%) |
