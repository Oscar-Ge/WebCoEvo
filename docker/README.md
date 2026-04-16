# Local Docker Guide

This directory is the local Linux/macOS path. It is not the HPC path.

## What This Is For

- Use `slurm/` and `scripts/singularity/` on shared HPC servers.
- Use `docker/` and `scripts/docker/` on a local Linux workstation or macOS machine with Docker Desktop or Docker Engine plus the Compose plugin.

The Docker path is meant for local smoke runs, preflight checks, manual website inspection, and sequential full-matrix runs when you accept that they may take a long time.

## Prerequisites

- Docker with `docker compose`
- A reachable OpenAI-compatible endpoint
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`

If your model server is on the same host as Docker, prefer:

```bash
export OPENAI_BASE_URL=http://host.docker.internal:8000/v1
```

That works on Docker Desktop and on recent Linux Docker setups because the generated compose file adds `host.docker.internal:host-gateway`.

## Quick Start

Generate a local compose file and run preflight only:

```bash
scripts/docker/local_smoke.sh preflight
```

Bring up one variant locally for manual inspection:

```bash
VARIANT=access LINKDING_HOST_PORT=9103 scripts/docker/local_smoke.sh up
```

Run one local smoke task through Docker:

```bash
OPENAI_API_KEY=... \
OPENAI_BASE_URL=http://host.docker.internal:8000/v1 \
VARIANT=access \
RULEBOOK=rulebooks/v2_6.json \
scripts/docker/local_smoke.sh smoke
```

Tear the local container down:

```bash
scripts/docker/local_smoke.sh down
```

## Sequential Local Full Matrix

For a local full matrix, WebCoEvo runs one variant at a time and reuses the same local host port. That keeps the setup simple and avoids pretending a laptop is a small Slurm cluster.

Example: Focus20 full x V2.4/V2.5/V2.6 x all seven hardv3 variants:

```bash
OPENAI_API_KEY=... \
OPENAI_BASE_URL=http://host.docker.internal:8000/v1 \
TASK_FILE=configs/focus20_hardv3_full.raw.json \
RUN_PREFIX=local_focus20_full \
scripts/docker/local_matrix.sh
```

Example: TaskBank36 full:

```bash
OPENAI_API_KEY=... \
OPENAI_BASE_URL=http://host.docker.internal:8000/v1 \
TASK_FILE=configs/taskbank36_hardv3_full.raw.json \
RUN_PREFIX=local_taskbank36_full \
scripts/docker/local_matrix.sh
```

You can narrow it:

```bash
RULEBOOKS=rulebooks/v2_4.json \
VARIANTS=access,runtime \
TASK_FILE=configs/focus20_hardv3_full.raw.json \
scripts/docker/local_matrix.sh
```

## Time Budget

These are rough planning numbers, not guarantees:

- Preflight only: usually under 1 minute
- One smoke task: often 2 to 15 minutes
- One full variant shard on Focus20: often 20 to 90 minutes
- Focus20 full x 3 rulebooks x 7 variants: often half a day to overnight
- TaskBank36 full x 3 rulebooks x 7 variants: often overnight to multi-day
- Combined 3x2 full matrix on a local setup: budget at least overnight, and often longer

The real runtime depends much more on model latency and browser stability than on Docker itself. Decide locally whether that time is worth it.
