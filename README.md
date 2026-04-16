# WebCoEvo

WebCoEvo is a self-contained Linkding XVR evaluation runner for testing cross-version reflection rules on hardv3 drift websites.

It was extracted from the larger `webAgentBenchmark` research tree so Linkding Focus20 and TaskBank36 experiments can be run, audited, and reproduced without the historical `webevolve/` and multi-generation harness stack.

Chinese documentation is available in [README-cn.md](README-cn.md).

## What This Repo Contains

- `linkding_xvr_minimal/`: the Python runner, BrowserGym task wrapper, UI-TARS AgentLab adapter, prompt injection, rule selection, reset/login handling, and legacy eval/trace export.
- `configs/`: bundled hardv3 task JSON files for Focus20 smoke/full and TaskBank36 full.
- `rulebooks/`: bundled V2.4/V2.5/V2.6 cross-version reflection rulebooks plus `expel_official_v2.json`.
- `scripts/singularity/`: self-contained Linkding drift runtime helpers and hardv3 variant template assets.
- `websites/`: bundled Linkding website-generation assets: original control snapshots, the first modified website generation, and the hardv3 release-grounded website.
- `scripts/verify_trace_rules.py`: trace audit gate for XVR and ExpeL rule injection.
- `slurm/`: smoke, full, and hardv3 matrix submitters.
- `skills/`: repo-local Codex skills for running, monitoring, and analyzing WebCoEvo experiments.
- `tests/`: unit tests for metadata normalization, rule selection, prompt injection, export fields, reset behavior, and submitter safety.

This repo does not require the old `webAgentBenchmark` checkout at runtime.

## Architecture

The runner has four layers:

1. Task layer: `tasks.py` loads raw JSON and normalizes `task_id`, `source_task_id`, `focus20_source_task_id`, `drift_type`, `variant`, `family`, `version`, and `start_url`.
2. Rule layer: `rulebook.py` and `expel_rules.py` load, normalize, select, and render XVR reflection rules and ExpeL-style task experience rules.
3. Browser/agent layer: `browser_task.py`, `benchmark.py`, `agentlab_agent.py`, and `prompting.py` register BrowserGym tasks, reset/login Linkding, inject rules into prompts, parse UI-TARS actions, and run AgentLab.
4. Export/audit layer: `export.py` writes legacy eval/trace JSONL, backfills preflight rule IDs into reset-error rows, and `verify_trace_rules.py` checks that rule injection is visible in traces.

The Singularity scripts start local Linkding drift variants, rewrite task start URLs to per-job localhost ports, reset variant data, create the baseline user, run the Python runner, and audit traces.

## Website Assets

The repo carries three Linkding website generations:

- `websites/original/`: clean Linkding `1.45.0` control HTML/PNG snapshots. The runtime `control` variant has no template bind mounts.
- `websites/first_modified/`: the first vibe-coded drift generation restored from old commit `9879707`, plus the April 3 before/after screenshots.
- `websites/hardv3/`: the release-grounded hardv3 website, including template overrides, validation HTML, screenshots, and design notes.

The runtime source of truth for hardv3 remains `scripts/singularity/linkding_drift/variants/`; `websites/hardv3/variant_templates/` is an archive copy for review and repo portability.

## Setup

Create or activate a Python environment with the benchmark dependencies:

```bash
cd /path/to/WebCoEvo
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[benchmark,dev]'
```

On the UMich cluster, the Slurm scripts load `python/3.11.5` and `singularity/4.x`. If your Python environment is not `.venv/bin/python`, pass:

```bash
export PYTHON_BIN=/path/to/python
```

Set the model endpoint:

```bash
export OPENAI_BASE_URL=http://your-openai-compatible-endpoint/v1
export OPENAI_API_KEY=...
export UITARS_MODEL=Qwen/Qwen3-VL-30B-A3B-Instruct
```

You can also create a local `.env.umich`; the Slurm scripts source it if present. Do not commit secrets.

## Local Gates

Run unit tests:

```bash
python3 -m pytest -q
```

Compile tasks without launching a browser:

```bash
python3 -m linkding_xvr_minimal.runner \
  --task-file configs/focus20_hardv3_smoke.raw.json \
  --rulebook rulebooks/v2_6.json \
  --run-label focus20_smoke_compile \
  --compile-only
```

Check rule injection before any agent run:

```bash
python3 -m linkding_xvr_minimal.runner \
  --task-file configs/focus20_hardv3_smoke.raw.json \
  --rulebook rulebooks/v2_6.json \
  --run-label focus20_smoke_preflight_v26 \
  --preflight-rules-only \
  --fail-on-empty-xvr-rules \
  --expel-rule-file rulebooks/expel_official_v2.json \
  --expel-fidelity official_eval
```

Expected: every selected task has nonempty `preflight[].selected_rule_ids`, and ExpeL preflight has nonempty `expel_preflight[].selected_rule_ids`.

## Smoke Run

Submit one access-task smoke run with the bundled Linkding drift runtime:

```bash
RUN_LABEL=focus20_hardv3_smoke_access_xvr26_webcoevo_v1 \
EXPEL_RULE_FILE="$PWD/rulebooks/expel_official_v2.json" \
EXPEL_FIDELITY=official_eval \
sbatch slurm/run_smoke_access_singularity.slurm.sh
```

The script writes outputs under:

```text
results/<RUN_LABEL>/
```

It also runs:

```bash
python3 scripts/verify_trace_rules.py \
  --trace 'results/<RUN_LABEL>/result_access/*trace*.jsonl' \
  --require-cross-version-rules \
  --require-rulebook-path \
  --require-expel-rules
```

## Full Matrix

Submit Focus20 and TaskBank36 hardv3 for V2.4/V2.5/V2.6:

```bash
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_webcoevo_full_v1" \
EXPEL_RULE_FILE="$PWD/rulebooks/expel_official_v2.json" \
EXPEL_FIDELITY=official_eval \
SBATCH_TIME=04:00:00 \
bash slurm/submit_hardv3_matrix.sh
```

The matrix covers:

- Focus20 full hardv3: 68 tasks.
- TaskBank36 hardv3 full: all bundled TaskBank36 rows.
- Rulebooks: `v2_4.json`, `v2_5.json`, `v2_6.json`.
- Shards: `access`, `surface`, `content`, `runtime:process`, `structural:functional`.

Runtime directories default to:

```text
/home/gecm/linkding-drift-runtimes/<run-label>-<shard>-<run-stamp>
```

Override with `LINKDING_DRIFT_BASE_DIR` if your cluster quota requires another path.

## Outputs

Each run writes:

- `study/`: AgentLab study artifacts.
- `*eval*.jsonl`: legacy eval rows.
- `*trace*.jsonl`: legacy trace rows with rule audit fields.
- `tasks.offset.json`: task file rewritten to local drift ports.

Rule audit fields are intentionally separate:

- `injected_rule_ids`: ExpeL/task-experience rules.
- `cross_version_reflection_rule_ids`: XVR reflection rules.
- `cross_version_reflection_rules_path`: rulebook path.

Reset-time failures are exported separately from agent failures and still receive preflight rule audit fields.

## Repo-Local Skills

The `skills/` directory contains lightweight Codex skills:

- `webcoevo-run`: launch unit checks, preflight checks, smoke jobs, and full matrix jobs.
- `webcoevo-monitor`: monitor Slurm jobs, logs, trace audits, and rerun decisions.
- `webcoevo-analyze`: aggregate eval JSONL files into success-rate tables.

Agents can use them by referencing the skill path, for example:

```text
Use the skill at skills/webcoevo-run/SKILL.md to launch a smoke run.
```

## Migration Notes

WebCoEvo avoids silent rule injection failures by:

- running preflight selection before AgentLab starts,
- failing fast when XVR rules are empty if `--fail-on-empty-xvr-rules` is set,
- exporting ExpeL and XVR rule IDs in distinct fields,
- backfilling preflight rule IDs into reset-error eval/trace rows,
- auditing traces after Slurm runs.

The intentionally omitted historical features are:

- knowledge-graph mining and broad ExpeL discovery,
- TaskBank generation/analysis scaffolds,
- paper/report/figure pipelines,
- retrieved trajectory exemplar injection,
- retry guidance text from previous failed attempts.
