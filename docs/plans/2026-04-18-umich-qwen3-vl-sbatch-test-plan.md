# UMich Qwen3-VL sbatch Test Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Submit a small, auditable UMich Slurm test matrix for (1) no-rules vs ExpeL-only on clean Linkding 1.45.0 for Focus20 and TaskBank36, and (2) ExpeL-only vs ExpeL+v2.4 reflection rules on the `websites/first_modified` drift site.

**Architecture:** Reuse the existing Singularity/Slurm execution path, but add one thin generalization layer around site profile selection and rule requirements. Keep the existing hardv3 scripts intact where possible; add profile-aware submitters for clean control and first-modified runs.

**Tech Stack:** UMich Great Lakes Slurm, `python/3.11.5`, `singularity/4.x`, WebCoEvo `linkding_xvr_minimal.runner`, Qwen3-VL endpoint via `OPENAI_BASE_URL`, existing Linkding 1.45.0 Singularity image.

---

## Experiment Matrix

### Matrix 1: Clean Linkding 1.45.0 Rule Baselines

Purpose: measure how much ExpeL rules help on the clean v1.45.0 site before adding website drift.

Datasets:
- `configs/focus20_hardv3_full.raw.json`, expected expanded count `68`
- `configs/taskbank36_hardv3_full.raw.json`, expected expanded count `167`

Site profile:
- `control`, unmodified Linkding 1.45.0
- All task start URLs are rewritten to the single control host, regardless of the task row's `variant`.

Rule settings:
- `no_rules`: no ExpeL rules and no XVR reflection rules
- `expel_only`: `rulebooks/expel_official_v2.json`, no XVR reflection rules

Expected full jobs after smoke:
- `focus20 × {no_rules, expel_only}` = 2 jobs
- `taskbank36 × {no_rules, expel_only}` = 2 jobs
- Total = 4 jobs

### Matrix 2: First-Modified Website Transfer

Purpose: compare ExpeL-only against ExpeL+v2.4 reflection rules on the original first-modified drift site.

Datasets:
- Same Focus20 and TaskBank36 task files.

Site profile:
- `first_modified`, using `websites/first_modified/variant_templates/`
- Keep the same five shard groups used by hardv3:
  - `access`
  - `surface`
  - `content`
  - `runtime_process = runtime:process`
  - `structural_functional = structural:functional`

Rule settings:
- `expel_only`: ExpeL rules, no XVR reflection rules
- `v2_4`: ExpeL rules plus `rulebooks/v2_4.json`

Expected full jobs after smoke:
- `2 datasets × 2 rule settings × 5 shard groups = 20 jobs`

Assumption: `v2_4` means the same protocol as the existing hardv3 matrix: ExpeL official rules plus v2.4 XVR reflection rules. If we want "v2.4 XVR without ExpeL", define a third setting later.

---

## Current Blockers in the Existing Scripts

The existing `slurm/run_hardv3_variant_singularity.slurm.sh` is hardv3-matrix-specific:

- It requires `RULEBOOK`.
- It always passes `--fail-on-empty-xvr-rules`.
- It always verifies `--require-cross-version-rules`.
- It assumes each task row's variant maps to the same runtime variant.
- It uses `scripts/singularity/linkding_drift_manifest.py`, whose runtime source of truth is hardv3 under `scripts/singularity/linkding_drift/variants/`.

Therefore, do not submit the requested jobs directly with `submit_hardv3_matrix.sh`. First add a small profile-aware submit path.

---

## Task 1: Add no-XVR Rulebook and Rule-Requirement Switches

**Files:**
- Create: `rulebooks/no_xvr_empty.json`
- Modify: `slurm/run_hardv3_variant_singularity.slurm.sh`
- Test: `tests/test_slurm_submitters.py`

**Step 1: Add an empty XVR rulebook**

Create `rulebooks/no_xvr_empty.json`:

```json
{
  "schema_version": "webcoevo-xvr-empty-v1",
  "rules": []
}
```

Use this for `no_rules` and `expel_only` so the runner's current `--rulebook` requirement remains satisfied.

**Step 2: Make XVR strictness configurable**

Add env flags to the Slurm runner:

```bash
export REQUIRE_XVR_RULES="${REQUIRE_XVR_RULES:-1}"
export REQUIRE_EXPEL_RULES="${REQUIRE_EXPEL_RULES:-1}"
```

Change runner args from unconditional:

```bash
--fail-on-empty-xvr-rules
```

to:

```bash
runner_args=()
if [[ "${REQUIRE_XVR_RULES}" == "1" ]]; then
  runner_args+=(--fail-on-empty-xvr-rules)
fi
```

Change trace verification from unconditional XVR verification to:

```bash
verify_args=(--trace "${OUTPUT_DIR}/*trace*.jsonl")
if [[ "${REQUIRE_XVR_RULES}" == "1" ]]; then
  verify_args+=(--require-cross-version-rules --require-rulebook-path)
fi
if [[ -n "${EXPEL_RULE_FILE:-}" && "${REQUIRE_EXPEL_RULES}" == "1" ]]; then
  verify_args+=(--require-expel-rules)
fi
```

**Step 3: Allow empty ExpeL file**

Keep the existing behavior:

```bash
if [[ -n "${EXPEL_RULE_FILE:-}" ]]; then
  expel_args=(...)
fi
```

For `no_rules`, submit with:

```bash
EXPEL_RULE_FILE=""
REQUIRE_EXPEL_RULES=0
RULEBOOK="$PWD/rulebooks/no_xvr_empty.json"
REQUIRE_XVR_RULES=0
```

**Step 4: Test**

Run:

```bash
python3 -m pytest tests/test_slurm_submitters.py -q
```

Expected:
- Existing hardv3 submitter tests still pass.
- New test confirms non-reflection settings export `REQUIRE_XVR_RULES=0`.

---

## Task 2: Add Profile-Aware Website Runtime

**Files:**
- Modify: `scripts/singularity/linkding_drift_manifest.py`
- Modify: `scripts/singularity/linkding_drift_runtime_lib.sh`
- Create: `tests/test_first_modified_manifest.py`

**Step 1: Add a manifest profile selector**

Add an environment selector:

```bash
LINKDING_DRIFT_PROFILE="${LINKDING_DRIFT_PROFILE:-hardv3}"
```

Supported profiles:
- `hardv3`: current default, no behavior change
- `first_modified`: source bind mounts from `websites/first_modified/variant_templates`
- `control`: no bind mounts, only the unmodified Linkding 1.45.0 site

**Step 2: Implement first-modified bind mounts**

For `first_modified`, bind exactly these files:

| Variant | Source under `websites/first_modified/variant_templates` | Target |
| --- | --- | --- |
| `access` | `access/templates/registration/login.html` | `/etc/linkding/bookmarks/templates/registration/login.html` |
| `surface` | `surface/templates/shared/layout.html` | `/etc/linkding/bookmarks/templates/shared/layout.html` |
| `content` | `content/templates/shared/nav_menu.html` | `/etc/linkding/bookmarks/templates/shared/nav_menu.html` |
| `content` | `content/templates/tags/index.html` | `/etc/linkding/bookmarks/templates/tags/index.html` |
| `structural` | `structural/templates/shared/nav_menu.html` | `/etc/linkding/bookmarks/templates/shared/nav_menu.html` |
| `functional` | `functional/templates/bookmarks/bookmark_page.html` | `/etc/linkding/bookmarks/templates/bookmarks/bookmark_page.html` |
| `process` | `process/templates/bookmarks/new.html` | `/etc/linkding/bookmarks/templates/bookmarks/new.html` |
| `runtime` | `runtime/templates/shared/layout.html` | `/etc/linkding/bookmarks/templates/shared/layout.html` |

**Step 3: Test**

Run:

```bash
LINKDING_DRIFT_PROFILE=first_modified python3 scripts/singularity/linkding_drift_manifest.py --variant surface --format binds
LINKDING_DRIFT_PROFILE=control python3 scripts/singularity/linkding_drift_manifest.py --variant control --format binds
python3 -m pytest tests/test_first_modified_manifest.py -q
```

Expected:
- First-modified profile returns bind mounts under `websites/first_modified/variant_templates`.
- Control profile returns zero bind mounts.
- Default hardv3 behavior remains unchanged.

---

## Task 3: Add Control-Site Task Rewriting

**Files:**
- Modify: `slurm/run_hardv3_variant_singularity.slurm.sh`, or create `slurm/run_linkding_profile_singularity.slurm.sh`
- Test: `tests/test_slurm_submitters.py`

**Step 1: Add separate runtime and task variant concepts**

For hardv3/first_modified, current behavior is correct:

```bash
RUNTIME_VARIANTS="${DRIFT_VARIANTS}"
TASK_VARIANTS="${DRIFT_VARIANTS}"
```

For clean control, use:

```bash
RUNTIME_VARIANTS="control"
TASK_VARIANTS="access:surface:content:runtime:process:structural:functional"
TASK_HOST_PROFILE="control"
```

**Step 2: Rewrite all task variants to control**

When `TASK_HOST_PROFILE=control`, create variant host pairs that map every task variant to the control URL:

```bash
control_url="http://127.0.0.1:$(drift_variant_port control)"
variant_pairs=(
  "access=${control_url}"
  "surface=${control_url}"
  "content=${control_url}"
  "runtime=${control_url}"
  "process=${control_url}"
  "structural=${control_url}"
  "functional=${control_url}"
)
```

The existing `rewrite_task_start_urls` helper can then keep all task variants while sending them to the clean v1.45.0 runtime.

**Step 3: Add optional task limit for smoke**

Add:

```bash
export TASK_LIMIT="${TASK_LIMIT:-0}"
```

Pass `limit=int(TASK_LIMIT)` into `rewrite_task_start_urls` for smoke tests.

**Step 4: Test compile behavior**

Run:

```bash
TASK_LIMIT=2 TASK_HOST_PROFILE=control DRIFT_VARIANTS=access:surface \
python3 -m pytest tests/test_slurm_submitters.py -q
```

Expected:
- The Slurm script can express a clean-control run with all task variants rewritten to the single control host.

---

## Task 4: Add Two Test Submitters

**Files:**
- Create: `slurm/submit_control_rules_matrix.sh`
- Create: `slurm/submit_first_modified_rules_matrix.sh`
- Test: `tests/test_slurm_submitters.py`

### Submitter A: clean control no-rules vs ExpeL-only

Default settings:

```bash
datasets=("focus20" "taskbank36")
settings=("no_rules" "expel_only")
SBATCH_TIME="${SBATCH_TIME:-02:00:00}"
TASK_LIMIT="${TASK_LIMIT:-0}"
MAX_STEPS="${MAX_STEPS:-30}"
MAX_TOKENS="${MAX_TOKENS:-300}"
AGENT_MODE="${AGENT_MODE:-vl_action_reflection}"
UITARS_MODEL="${UITARS_MODEL:-Qwen/Qwen3-VL-30B-A3B-Instruct}"
OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://promaxgb10-d668.eecs.umich.edu:8000/v1}"
```

Per setting:

```bash
case "${setting}" in
  no_rules)
    rulebook="${MIN_ROOT}/rulebooks/no_xvr_empty.json"
    expel_rule_file=""
    require_xvr=0
    require_expel=0
    ;;
  expel_only)
    rulebook="${MIN_ROOT}/rulebooks/no_xvr_empty.json"
    expel_rule_file="${MIN_ROOT}/rulebooks/expel_official_v2.json"
    require_xvr=0
    require_expel=1
    ;;
esac
```

Run labels:

```bash
focus20_1450_control_no_rules_minimal_v1
focus20_1450_control_expel_only_official_minimal_v1
taskbank36_1450_control_no_rules_minimal_v1
taskbank36_1450_control_expel_only_official_minimal_v1
```

### Submitter B: first_modified ExpeL-only vs v2.4

Default settings:

```bash
datasets=("focus20" "taskbank36")
settings=("expel_only" "v2_4")
SHARD_NAMES=("access" "surface" "content" "runtime_process" "structural_functional")
SHARD_VARIANTS=("access" "surface" "content" "runtime:process" "structural:functional")
LINKDING_DRIFT_PROFILE="first_modified"
SBATCH_TIME="${SBATCH_TIME:-04:00:00}"
```

Per setting:

```bash
case "${setting}" in
  expel_only)
    rulebook="${MIN_ROOT}/rulebooks/no_xvr_empty.json"
    expel_rule_file="${MIN_ROOT}/rulebooks/expel_official_v2.json"
    require_xvr=0
    require_expel=1
    ;;
  v2_4)
    rulebook="${MIN_ROOT}/rulebooks/v2_4.json"
    expel_rule_file="${MIN_ROOT}/rulebooks/expel_official_v2.json"
    require_xvr=1
    require_expel=1
    ;;
esac
```

Run labels:

```bash
focus20_first_modified_expel_only_official_minimal_v1
focus20_first_modified_v2_4_expel_official_minimal_v1
taskbank36_first_modified_expel_only_official_minimal_v1
taskbank36_first_modified_v2_4_expel_official_minimal_v1
```

---

## Task 5: Preflight Before sbatch

**Files:**
- No new files.

**Step 1: Check module and Python environment on Great Lakes**

Run on the login node:

```bash
cd /home/gecm/WebCoEvo
module list
module purge
module load python/3.11.5
module load singularity/4.3.4 || module load singularity/4.1.5
python -V
test -x .venv/bin/python
```

Expected:
- Python module loads cleanly.
- `.venv/bin/python` exists and is executable.

**Step 2: Check endpoint env**

Run:

```bash
cd /home/gecm/WebCoEvo
set -a
source .env.umich
set +a
python3 - <<'PY'
import os
print("OPENAI_BASE_URL=", os.environ.get("OPENAI_BASE_URL"))
print("OPENAI_API_KEY set=", bool(os.environ.get("OPENAI_API_KEY")))
print("UITARS_MODEL=", os.environ.get("UITARS_MODEL", "Qwen/Qwen3-VL-30B-A3B-Instruct"))
PY
```

Expected:
- `OPENAI_API_KEY set=True`
- `OPENAI_BASE_URL` points to the UMich Qwen3-VL endpoint, usually `http://promaxgb10-d668.eecs.umich.edu:8000/v1`.

**Step 3: Preflight rule selection**

Run:

```bash
.venv/bin/python -m linkding_xvr_minimal.runner \
  --task-file configs/focus20_hardv3_smoke.raw.json \
  --rulebook rulebooks/no_xvr_empty.json \
  --run-label preflight_no_xvr \
  --variant access \
  --preflight-rules-only
```

Expected:
- `task_count > 0`
- `preflight[].selected_rule_ids` is empty
- exit code `0`

Run:

```bash
.venv/bin/python -m linkding_xvr_minimal.runner \
  --task-file configs/focus20_hardv3_smoke.raw.json \
  --rulebook rulebooks/v2_4.json \
  --expel-rule-file rulebooks/expel_official_v2.json \
  --expel-fidelity official_eval \
  --run-label preflight_v24 \
  --variant access \
  --preflight-rules-only \
  --fail-on-empty-xvr-rules
```

Expected:
- `preflight[].selected_rule_ids` is nonempty
- `expel_preflight[].selected_rule_ids` is nonempty
- exit code `0`

---

## Task 6: Submit Smoke sbatch Jobs

**Files:**
- No new files.

Use tiny smoke limits first.

### Smoke A: clean control

```bash
cd /home/gecm/WebCoEvo
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_control_rules_smoke_qwen3vl_v1" \
TASK_LIMIT=2 \
SBATCH_TIME=00:30:00 \
MAX_STEPS=12 \
MAX_TOKENS=300 \
AGENT_MODE=vl_action_reflection \
UITARS_MODEL="Qwen/Qwen3-VL-30B-A3B-Instruct" \
bash slurm/submit_control_rules_matrix.sh
```

Expected submissions:
- 4 jobs total
- 2 tasks per job
- output under `results/*control*/*/run_${RUN_STAMP}` or equivalent submitter path

### Smoke B: first_modified

```bash
cd /home/gecm/WebCoEvo
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_first_modified_rules_smoke_qwen3vl_v1" \
TASK_LIMIT=2 \
SBATCH_TIME=00:30:00 \
MAX_STEPS=12 \
MAX_TOKENS=300 \
AGENT_MODE=vl_action_reflection \
UITARS_MODEL="Qwen/Qwen3-VL-30B-A3B-Instruct" \
bash slurm/submit_first_modified_rules_matrix.sh
```

Expected submissions:
- 20 jobs total if all shards are enabled
- For an even smaller first smoke, allow `SHARD_NAMES=("access")` / `SHARD_VARIANTS=("access")` override in the submitter and submit 4 jobs first.

### Monitor smoke

```bash
squeue --me -o "%.18i %.24j %.10T %.10M %.10l %.30R"
tail -f m*f20*-%j.log
sacct -j <jobid> --format=JobID,JobName,State,Elapsed,ExitCode,MaxRSS
```

Success criteria:
- Slurm state reaches `COMPLETED`.
- Eval JSONL exists.
- Trace JSONL exists.
- `no_rules` traces do not require ExpeL or XVR fields.
- `expel_only` traces have `injected_rule_ids`.
- `v2_4` traces have both `injected_rule_ids` and `cross_version_reflection_rule_ids`.

---

## Task 7: Submit Full sbatch Tests

Submit full only after smoke passes.

### Full A: clean control

```bash
cd /home/gecm/WebCoEvo
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_control_rules_full_qwen3vl_v1" \
TASK_LIMIT=0 \
SBATCH_TIME=02:00:00 \
MAX_STEPS=30 \
MAX_TOKENS=300 \
AGENT_MODE=vl_action_reflection \
UITARS_MODEL="Qwen/Qwen3-VL-30B-A3B-Instruct" \
bash slurm/submit_control_rules_matrix.sh
```

Expected:
- 4 jobs
- Focus20 jobs write 68 eval rows each.
- TaskBank36 jobs write 167 eval rows each.

### Full B: first_modified

```bash
cd /home/gecm/WebCoEvo
RUN_STAMP="$(date +%Y%m%d_%H%M%S)_first_modified_rules_full_qwen3vl_v1" \
TASK_LIMIT=0 \
SBATCH_TIME=04:00:00 \
MAX_STEPS=30 \
MAX_TOKENS=300 \
AGENT_MODE=vl_action_reflection \
UITARS_MODEL="Qwen/Qwen3-VL-30B-A3B-Instruct" \
bash slurm/submit_first_modified_rules_matrix.sh
```

Expected:
- 20 jobs
- Focus20 total per setting is 68 rows after aggregating shards.
- TaskBank36 total per setting is 167 rows after aggregating shards.

---

## Task 8: Result Sanity Checks

**Files:**
- Optionally extend: `scripts/reporting/generate_hardv3_matrix_report.py`

Run row-count checks:

```bash
find results -path "*control*run_*" -name "uitars_eval_*.jsonl" -print
find results -path "*first_modified*run_*" -name "uitars_eval_*.jsonl" -print
```

Check counts:

```bash
python3 - <<'PY'
from pathlib import Path
for p in sorted(Path("results").rglob("uitars_eval_*.jsonl")):
    if "control" in str(p) or "first_modified" in str(p):
        n = sum(1 for line in p.open() if line.strip())
        s = sum(1 for line in p.open() if '"success": true' in line)
        print(n, s, p)
PY
```

Expected:
- Smoke counts match `TASK_LIMIT`.
- Full control counts are `68` and `167`.
- Full first_modified counts sum to `68` and `167` per dataset/setting across shards.

Then generate a small comparison table:

| Site | Dataset | Setting A | Setting B | Primary comparison |
| --- | --- | --- | --- | --- |
| clean 1.45.0 | Focus20 | no_rules | expel_only | ExpeL gain on clean training-like tasks |
| clean 1.45.0 | TaskBank36 | no_rules | expel_only | ExpeL gain on clean held-out tasks |
| first_modified | Focus20 | expel_only | ExpeL+v2.4 | Reflection-rule gain on first-modified training-like tasks |
| first_modified | TaskBank36 | expel_only | ExpeL+v2.4 | Reflection-rule gain on first-modified held-out tasks |

---

## Do Not Submit Until These Pass

- `python3 -m pytest tests/test_slurm_submitters.py -q`
- `python3 -m pytest tests/test_first_modified_manifest.py -q`
- Preflight no-XVR rule selection exits `0`.
- Preflight v2.4+ExpeL rule selection exits `0`.
- One control smoke job and one first_modified access-shard smoke job complete.

After that, submit the full 4-job control matrix and 20-job first_modified matrix.
