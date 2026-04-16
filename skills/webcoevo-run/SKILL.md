---
name: webcoevo-run
description: Run WebCoEvo Linkding XVR evaluations. Use when choosing between the HPC Slurm/Singularity path and the local Docker path, launching smoke tests, preflight rule-injection checks, compile-only checks, or Focus20/TaskBank36 evaluations with ExpeL rules plus V2.4/V2.5/V2.6 cross-version reflection rulebooks.
---

# WebCoEvo Run

## Choose The Path

- `HPC / Slurm`: use `slurm/` plus `scripts/singularity/` for official runs and long matrices.
- `Local Docker`: use `scripts/docker/local_smoke.sh` and `scripts/docker/local_matrix.sh` on Linux or macOS.

When the user says local laptop, home machine, Docker Desktop, Linux workstation, or macOS, prefer the Docker path.

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

## Local Docker Smoke

Use the Docker path for Linux or macOS:

```bash
scripts/docker/local_smoke.sh preflight
```

```bash
OPENAI_API_KEY=... \
OPENAI_BASE_URL=http://host.docker.internal:8000/v1 \
VARIANT=access \
scripts/docker/local_smoke.sh smoke
```

Use `scripts/docker/local_smoke.sh up` when the user wants to inspect one variant manually in a local browser.

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

## Local Docker Full Matrix

For local machines, the matrix runs sequentially one variant at a time:

```bash
OPENAI_API_KEY=... \
OPENAI_BASE_URL=http://host.docker.internal:8000/v1 \
TASK_FILE=configs/focus20_hardv3_full.raw.json \
RUN_PREFIX=local_focus20_full \
scripts/docker/local_matrix.sh
```

Planning ranges for local users:

- smoke: 2 to 15 minutes
- Focus20 full x 3 rulebooks x 7 variants: half a day to overnight
- TaskBank36 full x 3 rulebooks x 7 variants: overnight to multi-day

Present those as estimates and let the user decide whether local full-matrix time is acceptable.

## Required Environment

Ensure these are available before running AgentLab jobs:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`, or accept the cluster default in the Slurm scripts
- `python/3.11.5` and `singularity/4.x` modules on the cluster
- a `.venv` at repo root, or pass `PYTHON_BIN=/path/to/python`

Do not commit `results/`, `.env*`, runtime directories, or `.sif` images.
