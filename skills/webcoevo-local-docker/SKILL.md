---
name: webcoevo-local-docker
description: Use when running WebCoEvo on a local Linux workstation or macOS machine with Docker instead of the HPC Slurm and Singularity stack, especially for local smoke runs, manual variant inspection, or sequential full-matrix experiments.
---

# WebCoEvo Local Docker

## When To Use

Use this skill when the user wants WebCoEvo on:

- Docker Desktop on macOS
- Docker Engine on Linux
- a local workstation instead of the shared HPC cluster

Do not use this skill for Slurm jobs or Singularity-based cluster runs.

The local flow uses `docker compose` through the helper scripts in `scripts/docker/`.

Warning: this route has never been tested end to end in WebCoEvo. Treat it as documentation plus starter scripts that still require extra validation before any local result should be trusted.

## Quick Start

Preflight only:

```bash
scripts/docker/local_smoke.sh preflight
```

Bring up one local variant for manual inspection:

```bash
VARIANT=access LINKDING_HOST_PORT=9103 scripts/docker/local_smoke.sh up
```

Run one local smoke task:

```bash
OPENAI_API_KEY=... \
OPENAI_BASE_URL=http://host.docker.internal:8000/v1 \
VARIANT=access \
scripts/docker/local_smoke.sh smoke
```

Stop the local container:

```bash
scripts/docker/local_smoke.sh down
```

## Local Full Matrix

Run a sequential local matrix:

```bash
OPENAI_API_KEY=... \
OPENAI_BASE_URL=http://host.docker.internal:8000/v1 \
TASK_FILE=configs/focus20_hardv3_full.raw.json \
RUN_PREFIX=local_focus20_full \
scripts/docker/local_matrix.sh
```

For TaskBank36:

```bash
OPENAI_API_KEY=... \
OPENAI_BASE_URL=http://host.docker.internal:8000/v1 \
TASK_FILE=configs/taskbank36_hardv3_full.raw.json \
RUN_PREFIX=local_taskbank36_full \
scripts/docker/local_matrix.sh
```

## Notes

- The local matrix runs one variant at a time.
- Default host-to-model routing assumes `host.docker.internal`.
- Treat local full-matrix times as estimates: smoke is usually minutes, Focus20 is often half a day to overnight, and TaskBank36 is often overnight to multi-day.
- The detailed local guide lives in `docker/README.md`.
- Because the Docker path is untested, budget extra bring-up and debugging time before using it seriously.
