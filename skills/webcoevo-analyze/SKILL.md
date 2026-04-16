---
name: webcoevo-analyze
description: Analyze WebCoEvo eval outputs. Use when aggregating Focus20 or TaskBank36 JSONL results, computing success rates for no-XVR/V2.4/V2.5/V2.6 comparisons, checking task counts, or producing concise tables from `results/**/uitars_eval*.jsonl` and trace files.
---

# WebCoEvo Analyze

## Inputs

Use only eval JSONL files from the same runner generation, task file, model endpoint, and rule-injection semantics. Do not mix old runs where XVR rule injection may have been silent or unaudited.

Expected eval rows include:

- `task_id`
- `drift_type`
- `variant`
- `success` or equivalent score field
- `cross_version_reflection_rule_ids`
- `injected_rule_ids`

## Aggregation

Find eval files:

```bash
find results -path '*run_*/*eval*.jsonl' -print | sort
```

For each run label, compute:

- number of rows
- number of successes
- success rate
- drift-type breakdown
- missing XVR/ExpeL audit fields

Use absolute counts in reports, for example `44/68 = 64.7%`.

## Sanity Checks

Before comparing V2.4/V2.5/V2.6:

- Focus20 full should contain 68 tasks.
- TaskBank36 hardv3 full should contain the expected task count from `configs/taskbank36_hardv3_full.raw.json`.
- Rulebook path should match the claimed version.
- `cross_version_reflection_rule_ids` should be nonempty for every task row or reset-error backfilled row.
- `injected_rule_ids` should be nonempty when `expel_official_v2.json` was passed.

## Reporting

Keep the result table compact:

```text
Dataset      Rulebook  Success  Rate
Focus20      V2.4      44/68    64.7%
TaskBank36   V2.4      61/131   46.6%
```

List infrastructure exclusions separately from model failures.
