# Linkding Website Assets

This directory keeps the Linkding website generations that matter for WebCoEvo experiments. The runtime still reads from `scripts/singularity/linkding_drift/variants`; this directory is an auditable archive so the baseline, first modified website, and hardv3 website can be compared without the old `webAgentBenchmark` checkout.

## Generations

- `original/`: clean Linkding `1.45.0` control snapshots. These are rendered HTML and PNG captures from the unmodified control profile. CSRF values in captured HTML are replaced with `SANITIZED_CSRF_TOKEN`.
- `first_modified/`: the first vibe-coded drift website generation. Templates were restored from old repo commit `9879707` and visual before/after evidence was copied from the April 3 report.
- `hardv3/`: the release-grounded hardv3 website generation used by the current runner. It includes the active template overrides and rendered validation captures.

## Runtime Source Of Truth

The hardv3 runner starts variants through:

```text
scripts/singularity/linkding_drift/variants/
scripts/singularity/linkding_drift_manifest.py
```

The copy under `websites/hardv3/variant_templates/` is a versioned archive for review. If runtime behavior changes, update both locations or document why the archive intentionally differs.
