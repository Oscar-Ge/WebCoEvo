---
name: webcoevo-run
description: Run WebCoEvo Linkding XVR evaluations. Use when launching smoke tests, preflight rule-injection checks, local compile-only checks, Slurm hardv3 matrix jobs, or any Focus20/TaskBank36 evaluation with ExpeL rules plus V2.4/V2.5/V2.6 cross-version reflection rulebooks.
---

# WebCoEvo Run

## Quick Checks

Start from the repository root.

Run unit tests before submitting jobs:

```bash
python3 -m pytest -q
```

Check task/rulebook injection without launching a browser:

```bash
python3 -m linkding_xvr_minimal.runner \
  --task-file configs/focus20_hardv3_smoke.raw.json \
  --rulebook rulebooks/v2_6.json \
  --run-label preflight_smoke_v26 \
  --variant access \
  --preflight-rules-only \
  --fail-on-empty-xvr-rules \
  --expel-rule-file rulebooks/expel_official_v2.json \
  --expel-fidelity official_eval
```

Expected: nonempty `preflight[].selected_rule_ids` and nonempty `expel_preflight[].selected_rule_ids`.

## Slurm Smoke

Use the bundled smoke submitter first:

```bash
RUN_LABEL=focus20_hardv3_smoke_access_xvr26_webcoevo_v1 \
EXPEL_RULE_FILE=rulebooks/expel_official_v2.json \
EXPEL_FIDELITY=official_eval \
sbatch slurm/run_smoke_access_singularity.slurm.sh
```

The smoke script starts one access drift runtime, rewrites the smoke task start URL to localhost, runs one UI-TARS/AgentLab task, exports eval/trace JSONL, then audits the trace for XVR and ExpeL rule fields.

## Full Matrix

Submit the 3x2 hardv3 matrix:

```bash
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_webcoevo_full_v1" \
EXPEL_RULE_FILE="$PWD/rulebooks/expel_official_v2.json" \
EXPEL_FIDELITY=official_eval \
SBATCH_TIME=04:00:00 \
bash slurm/submit_hardv3_matrix.sh
```

For long TaskBank36 V2.6 surface/runtime reruns, submit directly with `--time=08:00:00` or edit the matrix submitter for that shard.

## Required Environment

Ensure these are available before running AgentLab jobs:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`, or accept the cluster default in the Slurm scripts
- `python/3.11.5` and `singularity/4.x` modules on the cluster
- a `.venv` at repo root, or pass `PYTHON_BIN=/path/to/python`

Do not commit `results/`, `.env*`, runtime directories, or `.sif` images.
