# WebCoEvo

WebCoEvo is a self-contained Linkding evaluation repo for cross-version reflection-rule experiments on hardv3 drift websites.

It was extracted from the larger `webAgentBenchmark` tree so the Linkding benchmark path can live in one smaller repo with clear inputs, clear runtime wiring, and auditable outputs.

Chinese documentation is available in [README-cn.md](README-cn.md).

## Course Project

WebCoEvo was developed as part of the **UMich EECS545 Winter 2026** course project by Chenming Ge, Chengyang Shi, Yifei Xu, Yuxiang Yang, and Binglin Zhong. It represents a shared effort that we were fortunate to pursue under the generous guidance of Prof. Honglak Lee and the thoughtful mentorship of Violet Fu.

## Scope

This repo is intentionally narrow. It is for:

- Linkding `1.45.0`
- hardv3 drift variants
- Focus20 and TaskBank36 task slices bundled in `configs/`
- ExpeL-style task experience rules
- XVR rulebooks such as `v2_4.json`, `v2_5.json`, and `v2_6.json`
- legacy eval JSONL and trace JSONL export

This repo is not trying to preserve the full historical `webAgentBenchmark` stack. It does not aim to carry the old KG mining pipeline, broad website-generation framework, paper assets, or multi-generation harness sprawl.

## Current Status

- The repo does not require the old `webAgentBenchmark` checkout at runtime.
- The official execution path is still the HPC Slurm/Singularity route.
- On the current UMich setup, Slurm jobs reuse `~/webAgentBenchmark/.venv/bin/python` when it is available; set `PYTHON_BIN` explicitly for other environments.
- The local Docker route exists as documentation and starter scripts, but it has never been tested end to end.

## Repository Layout

| Path | Role |
| --- | --- |
| `linkding_xvr_minimal/` | Python package: task normalization, rule loading, BrowserGym task wrapper, prompt construction, agent adapter, export logic |
| `configs/` | Bundled task files for Focus20 hardv3 smoke/full and TaskBank36 hardv3 full |
| `rulebooks/` | Bundled XVR rulebooks and ExpeL rule files |
| `scripts/singularity/` | Runtime helpers and hardv3 website bind-mount assets used by the HPC path |
| `slurm/` | Official submitters and Slurm execution scripts |
| `scripts/docker/` | Local Docker helpers for compose generation, smoke runs, and sequential local matrix runs |
| `docker/` | Runner Dockerfile and local Docker guide |
| `websites/` | Archived website generations: original control snapshots, first modified website, and hardv3 review copies |
| `skills/` | Repo-local Codex skills for run, monitor, analyze, and local Docker usage |
| `tests/` | Unit tests for runner behavior, export logic, submitters, website assets, and Docker-doc invariants |

## Architecture

The current system is easier to understand as six connected layers rather than the older four-layer summary:

1. **Experiment Inputs**
   - `configs/` holds raw task JSON.
   - `rulebooks/` holds XVR and ExpeL rule inputs.

2. **Task Normalization**
   - `linkding_xvr_minimal/tasks.py` and `linkding_xvr_minimal/browser_task.py` normalize every task into a consistent metadata shape:
     `task_id`, `source_task_id`, `focus20_source_task_id`, `drift_type`, `variant`, `family`, `version`, and `start_url`.

3. **Rule Selection And Prompt Injection**
   - `linkding_xvr_minimal/rulebook.py` selects XVR rules.
   - `linkding_xvr_minimal/expel_rules.py` selects ExpeL rules.
   - `linkding_xvr_minimal/prompting.py`, `agent.py`, and `agentlab_agent.py` render those rules into the agent prompt and preserve audit fields for export.

4. **Website Runtime**
   - `scripts/singularity/linkding_drift_manifest.py` defines drift variants and bind mounts.
   - `scripts/singularity/linkding_drift/variants/` is the runtime source of truth for hardv3 website overrides.
   - Slurm scripts reset site state, create the baseline user, rewrite task URLs to variant-specific localhost ports, and launch the run.

5. **Execution Backends**
   - **HPC / Slurm** is the production path: Singularity-based runtime, multi-shard matrix submission, cluster-friendly resource control.
   - **Local Docker** is a convenience path: compose generation plus one-variant smoke or sequential local matrix scripts.

6. **Outputs And Audit**
   - `linkding_xvr_minimal/export.py` writes eval JSONL and trace JSONL.
   - `scripts/verify_trace_rules.py` audits whether ExpeL and XVR injection fields are visible in trace rows.
   - Reset-time failures remain distinct from agent failures and still receive preflight audit backfill.

## Data Flow

The end-to-end flow is:

1. Load a raw task file from `configs/`.
2. Normalize task metadata.
3. Select ExpeL and XVR rules for each task.
4. Start the target website variant and rewrite start URLs to the runtime host.
5. Reset website state and ensure the baseline login user exists.
6. Run the UI-TARS/AgentLab loop against BrowserGym.
7. Export eval rows and trace rows.
8. Audit the trace for `injected_rule_ids`, `cross_version_reflection_rule_ids`, and the rulebook path.

## Runtime Source Of Truth

The repo deliberately separates runtime sources from review archives:

- Runtime hardv3 website source of truth:
  - `scripts/singularity/linkding_drift/variants/`
  - `scripts/singularity/linkding_drift_manifest.py`
- Review and migration archive:
  - `websites/hardv3/`
  - `websites/original/`
  - `websites/first_modified/`

That means `websites/` is useful for inspection and portability, but it is not the runtime authority.

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

Set the model endpoint:

```bash
export OPENAI_BASE_URL=http://your-openai-compatible-endpoint/v1
export OPENAI_API_KEY=...
export UITARS_MODEL=Qwen/Qwen3-VL-30B-A3B-Instruct
```

On the UMich cluster, the Slurm scripts load `python/3.11.5` and `singularity/4.x`. If your Python environment is not `.venv/bin/python`, pass:

```bash
export PYTHON_BIN=/path/to/python
```

You can also create a local `.env.umich`; the Slurm scripts source it if present. Do not commit secrets.

## Quick Modes

### Unit tests

```bash
python3 -m pytest -q
```

### Compile only

```bash
python3 -m linkding_xvr_minimal.runner \
  --task-file configs/focus20_hardv3_smoke.raw.json \
  --rulebook rulebooks/v2_6.json \
  --run-label focus20_smoke_compile \
  --compile-only
```

### Preflight rule audit

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

## HPC / Slurm Path

The default guidance in this repo is for HPC servers:

- `slurm/` submitters
- `scripts/singularity/` runtime helpers
- shared module environments such as `python/3.11.5` and `singularity/4.x`

Use this path for official matrix runs, quota-aware runtime placement, and long jobs that you want Slurm to manage.

### Smoke Run

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

### Full Matrix

```bash
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_webcoevo_full_v1" \
EXPEL_RULE_FILE="$PWD/rulebooks/expel_official_v2.json" \
EXPEL_FIDELITY=official_eval \
SBATCH_TIME=04:00:00 \
bash slurm/submit_hardv3_matrix.sh
```

The matrix covers:

- Focus20 full hardv3: 68 tasks
- TaskBank36 hardv3 full: all bundled TaskBank36 rows
- Rulebooks: `v2_4.json`, `v2_5.json`, `v2_6.json`
- Shards: `access`, `surface`, `content`, `runtime:process`, `structural:functional`

Runtime directories default to:

```text
/home/gecm/linkding-drift-runtimes/<run-label>-<shard>-<run-stamp>
```

Override with `LINKDING_DRIFT_BASE_DIR` if your cluster quota requires another path.

### Rule-Ablation And Transfer Matrices

For the EECS545 project experiments, the repo also includes two profile-aware submitters:

- `slurm/submit_control_rules_matrix.sh`: clean Linkding `1.45.0` baseline, comparing `no_rules` vs `expel_only` on Focus20 and TaskBank36.
- `slurm/submit_first_modified_rules_matrix.sh`: historical `websites/first_modified` drift profile, comparing `expel_only` vs `ExpeL + v2_4` on Focus20 and TaskBank36.

Smoke examples:

```bash
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_control_rules_smoke_qwen3vl_v1" \
TASK_LIMIT=2 \
SBATCH_TIME=00:30:00 \
MAX_STEPS=12 \
bash slurm/submit_control_rules_matrix.sh
```

```bash
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_first_modified_rules_smoke_qwen3vl_v1" \
TASK_LIMIT=2 \
SBATCH_TIME=00:30:00 \
MAX_STEPS=12 \
SHARD_NAMES_CSV=access \
SHARD_VARIANTS_CSV=access \
bash slurm/submit_first_modified_rules_matrix.sh
```

Full examples:

```bash
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_control_rules_full_qwen3vl_v1" \
TASK_LIMIT=0 \
SBATCH_TIME=02:00:00 \
bash slurm/submit_control_rules_matrix.sh
```

```bash
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_first_modified_rules_full_qwen3vl_v1" \
TASK_LIMIT=0 \
SBATCH_TIME=04:00:00 \
bash slurm/submit_first_modified_rules_matrix.sh
```

The generalized runner supports `LINKDING_DRIFT_PROFILE=hardv3|first_modified|control`, `REQUIRE_XVR_RULES`, `REQUIRE_EXPEL_RULES`, `TASK_HOST_PROFILE`, `RUNTIME_VARIANTS`, and `TASK_LIMIT`.

## Local Docker Path

For local Linux or macOS machines, use the Docker path instead of the HPC Singularity path:

- runner image: `docker/Dockerfile.runner`
- compose generator: `scripts/docker/generate_local_compose.py`
- one-variant local smoke helper: `scripts/docker/local_smoke.sh`
- sequential local full-matrix helper: `scripts/docker/local_matrix.sh`
- local guide: `docker/README.md`

Warning: the Docker route in this repo has never been tested end to end. It has not been run as a validated local benchmark path yet, and it requires additional testing before you should trust it for real experiments or reported results.

Quick examples:

```bash
scripts/docker/local_smoke.sh preflight
```

```bash
OPENAI_API_KEY=... \
OPENAI_BASE_URL=http://host.docker.internal:8000/v1 \
VARIANT=access \
scripts/docker/local_smoke.sh smoke
```

```bash
OPENAI_API_KEY=... \
OPENAI_BASE_URL=http://host.docker.internal:8000/v1 \
TASK_FILE=configs/focus20_hardv3_full.raw.json \
RUN_PREFIX=local_focus20_full \
scripts/docker/local_matrix.sh
```

Rough local time budgets:

- preflight: under 1 minute
- smoke: 2 to 15 minutes
- Focus20 full x 3 rulebooks x 7 variants: often half a day to overnight
- TaskBank36 full x 3 rulebooks x 7 variants: often overnight to multi-day

These are planning ranges so local users can decide whether to run the full matrix on their own machine.

## Build Rule Inputs

WebCoEvo now includes a lightweight producer-side pipeline for public, auditable rule artifacts. The intended flow is:

1. build episode artifacts from trace/eval JSONL,
2. build recovery artifacts from episode attempts,
3. induce ExpeL-style rules,
4. audit rule coverage before runtime injection.

Build an episode artifact from existing run outputs:

```bash
python3 scripts/build_episode_artifact.py \
  --trace "results/<run-label>/*trace*.jsonl" \
  --eval "results/<run-label>/*eval*.jsonl" \
  --task-file configs/focus20_hardv3_smoke.raw.json \
  --source-version 1.45.0 \
  --output-file rulebooks/generated/<run-label>/episodes.json
```

Build a recovery artifact from the episode attempts:

```bash
python3 scripts/build_recovery_artifact.py \
  --episodes-file rulebooks/generated/<run-label>/episodes.json \
  --output-file rulebooks/generated/<run-label>/recovery.json
```

Then build an ExpeL-style rule artifact from that recovery summary:

```bash
python3 scripts/build_expel_rules_from_recovery.py \
  --recovery-artifact rulebooks/generated/<run-label>/recovery.json \
  --output-file rulebooks/generated/<run-label>/expel_rules.json \
  --base-url "$OPENAI_BASE_URL" \
  --api-key "$OPENAI_API_KEY" \
  --model "${UITARS_MODEL:-gpt-5.4}"
```

For local testing without a model endpoint, the ExpeL builder supports stub files:

```bash
python3 scripts/build_recovery_artifact.py \
  --episodes-file rulebooks/generated/dev/episodes.json \
  --output-file rulebooks/generated/dev/recovery.json

python3 scripts/build_expel_rules_from_recovery.py \
  --recovery-artifact rulebooks/generated/dev/recovery.json \
  --output-file rulebooks/generated/dev/expel_rules.json \
  --stub-critique-file /path/to/local_stub_rule_ops.txt \
  --stub-insights-file /path/to/local_stub_insights.json \
  --include-insights
```

Audit coverage before any real agent run:

```bash
python3 scripts/verify_rule_coverage.py \
  --task-file configs/focus20_hardv3_smoke.raw.json \
  --rulebook rulebooks/v2_6.json \
  --expel-rule-file rulebooks/generated/<run-label>/expel_rules.json \
  --require-full-xvr-coverage \
  --require-full-expel-coverage \
  --json
```

## Build Reflection Rules

WebCoEvo also includes a public, auditable pipeline for cross-version reflection rules. This pipeline is separate from the ExpeL rule generator: it compares matched XVR runs, mines behavior gaps, asks a model or local stub for structured rule proposals, merges those proposals deterministically, verifies the candidate rulebook, and prepares a delta evaluation slice.

Focus20 is the mining set for reflection rule wording. TaskBank36 is held out for validation and should not be used to write deployable reflection rules unless the research protocol is explicitly changed. The `websites/` directory remains archive/review material only: websites/ is not the runtime source of truth. Runtime behavior still comes from `scripts/singularity/linkding_drift/variants/`.

Recommended generated layout:

```text
rulebooks/generated/<run-label>/reflection/
  transition_artifact.json
  capability_profile.json
  behavior_gaps.json
  mining_cases.jsonl
  rule_proposals.json
  candidate_rulebook.json
  verification_report.json
  delta_slice.raw.json
  promotion_decision.md
```

Build the matched transition artifact from paired eval/trace JSONL:

```bash
python3 scripts/build_xvr_transition_artifact.py \
  --task-file configs/focus20_hardv3_full.raw.json \
  --left-label v2_4 \
  --left-eval "results/<left-run>/*eval*.jsonl" \
  --left-trace "results/<left-run>/*trace*.jsonl" \
  --right-label candidate \
  --right-eval "results/<right-run>/*eval*.jsonl" \
  --right-trace "results/<right-run>/*trace*.jsonl" \
  --output-file rulebooks/generated/<run-label>/reflection/transition_artifact.json
```

Mine deterministic behavior gaps and compact model-facing cases:

```bash
python3 scripts/mine_reflection_gaps.py \
  --transition-artifact rulebooks/generated/<run-label>/reflection/transition_artifact.json \
  --output-file rulebooks/generated/<run-label>/reflection/behavior_gaps.json \
  --cases-file rulebooks/generated/<run-label>/reflection/mining_cases.jsonl
```

Build a candidate rulebook from structured proposals. Use `--stub-proposals-file` for local reproducibility, or provide an OpenAI-compatible endpoint for live proposal generation.

```bash
python3 scripts/build_reflection_rules.py \
  --base-rulebook rulebooks/v2_6.json \
  --mining-cases rulebooks/generated/<run-label>/reflection/mining_cases.jsonl \
  --output-file rulebooks/generated/<run-label>/reflection/candidate_rulebook.json \
  --stub-proposals-file rulebooks/generated/<run-label>/reflection/rule_proposals.json \
  --max-rules 8
```

Verify that the candidate is compact, deployable, and compatible with the runtime `load_rulebook` / `select_rules` path:

```bash
python3 scripts/verify_reflection_rulebook.py \
  --task-file configs/focus20_hardv3_full.raw.json \
  --rulebook rulebooks/generated/<run-label>/reflection/candidate_rulebook.json \
  --max-rules 8 \
  --no-task-scopes \
  --require-full-coverage \
  --json > rulebooks/generated/<run-label>/reflection/verification_report.json
```

Build a small delta-slice task file for promotion testing:

```bash
python3 scripts/build_reflection_delta_slice.py \
  --transition-artifact rulebooks/generated/<run-label>/reflection/transition_artifact.json \
  --task-file configs/focus20_hardv3_full.raw.json \
  --output-task-file rulebooks/generated/<run-label>/reflection/delta_slice.raw.json \
  --manifest-file rulebooks/generated/<run-label>/reflection/delta_manifest.json \
  --max-per-bucket 8
```

Finally, write the promotion decision record:

```bash
python3 scripts/decide_reflection_promotion.py \
  --transition-artifact rulebooks/generated/<run-label>/reflection/transition_artifact.json \
  --verification-report rulebooks/generated/<run-label>/reflection/verification_report.json \
  --output-file rulebooks/generated/<run-label>/reflection/promotion_decision.md
```

Consume the resulting artifacts with the existing preflight/runtime path:

```bash
python3 -m linkding_xvr_minimal.runner \
  --task-file configs/focus20_hardv3_smoke.raw.json \
  --rulebook rulebooks/v2_6.json \
  --expel-rule-file rulebooks/generated/<run-label>/expel_rules.json \
  --run-label rules_pipeline_preflight_smoke \
  --preflight-rules-only \
  --fail-on-empty-xvr-rules
```

Generated rule artifacts should live under `rulebooks/generated/`; see `rulebooks/generated/README.md` for the expected metadata and provenance fields.

This producer pipeline does not change the runtime source of truth: `scripts/singularity/linkding_drift/variants/` remains the runtime authority, and `websites/` is not the runtime authority.

## Outputs

Each run writes:

- `study/`: AgentLab study artifacts
- `*eval*.jsonl`: legacy eval rows
- `*trace*.jsonl`: legacy trace rows with rule audit fields
- `tasks.offset.json`: task file rewritten to local drift ports

Rule audit fields are intentionally separate:

- `injected_rule_ids`: ExpeL/task-experience rules
- `cross_version_reflection_rule_ids`: XVR reflection rules
- `cross_version_reflection_rules_path`: rulebook path

Reset-time failures are exported separately from agent failures and still receive preflight rule audit fields.

## Repo-Local Skills

The `skills/` directory contains lightweight Codex skills:

- `webcoevo-run`: choose a route and launch checks or runs
- `webcoevo-monitor`: inspect logs, traces, and rerun conditions
- `webcoevo-analyze`: aggregate eval JSONL into summary tables
- `webcoevo-local-docker`: explain and operate the unvalidated local Docker path

Agents can use them by referencing the skill path, for example:

```text
Use the skill at skills/webcoevo-run/SKILL.md to launch a smoke run.
```

## Migration Notes

WebCoEvo avoids silent rule injection failures by:

- running preflight selection before AgentLab starts
- failing fast when XVR rules are empty if `--fail-on-empty-xvr-rules` is set
- exporting ExpeL and XVR rule IDs in distinct fields
- backfilling preflight rule IDs into reset-error eval/trace rows
- auditing traces after runs

The intentionally omitted historical features are still:

- the old knowledge-graph mining harness and broader benchmark-maintenance framework
- TaskBank generation/analysis scaffolds
- paper/report/figure pipelines
- retrieved trajectory exemplar injection
- retry guidance text from previous failed attempts

What WebCoEvo does include now is a narrower public producer pipeline: episode extraction, failed-then-success recovery mining, ExpeL-style rule induction, and rule coverage auditing, all scoped to the Linkding XVR path and kept repo-local.
