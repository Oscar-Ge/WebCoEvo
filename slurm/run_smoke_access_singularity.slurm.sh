#!/usr/bin/env bash
#SBATCH --job-name=min_xvr_access_smoke
#SBATCH --account=eecs545w26_class
#SBATCH --partition=standard
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:45:00
#SBATCH --output=slurm/%x-%j.log

set -euo pipefail

if [[ -n "${MODULESHOME:-}" && -f "${MODULESHOME}/init/bash" ]]; then
  # shellcheck source=/dev/null
  source "${MODULESHOME}/init/bash"
fi
if command -v module >/dev/null 2>&1; then
  module purge
  module load python/3.11.5
  module load singularity/4.3.4 >/dev/null 2>&1 || module load singularity/4.1.5
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
MIN_ROOT="${REPO_ROOT}"
PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/.venv/bin/python}"

cd "${REPO_ROOT}"

if [[ -f ".env.umich" ]]; then
  set -a
  # shellcheck source=/dev/null
  source ".env.umich"
  set +a
fi

export OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://promaxgb10-d668.eecs.umich.edu:8000/v1}"
export UITARS_MODEL="${UITARS_MODEL:-Qwen/Qwen3-VL-30B-A3B-Instruct}"
export AGENT_MODE="${AGENT_MODE:-vl_action_reflection}"
export MAX_STEPS="${MAX_STEPS:-10}"
export MAX_TOKENS="${MAX_TOKENS:-300}"
export RUN_LABEL="${RUN_LABEL:-focus20_hardv3_smoke_access_xvr26_minimal_slurm}"
export EXPEL_FIDELITY="${EXPEL_FIDELITY:-minimal}"
export BASELINE_USER="${BASELINE_USER:-baseline}"
export BASELINE_PASS="${BASELINE_PASS:-Baseline123!}"
export BASELINE_EMAIL_DOMAIN="${BASELINE_EMAIL_DOMAIN:-local.test}"
export LINKDING_DRIFT_BASE_DIR="${LINKDING_DRIFT_BASE_DIR:-/home/gecm/linkding-drift-runtimes/${RUN_LABEL}-${SLURM_JOB_ID:-manual}}"
export LINKDING_DRIFT_NAMESPACE="${LINKDING_DRIFT_NAMESPACE:-${SLURM_JOB_ID:-$$}}"
export LINKDING_DRIFT_PORT_OFFSET="${LINKDING_DRIFT_PORT_OFFSET:-0}"
export LINKDING_DRIFT_STOP_SCOPE="${LINKDING_DRIFT_STOP_SCOPE:-namespace}"
export PYTHONPATH="${MIN_ROOT}:${PYTHONPATH:-}"

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "Error: OPENAI_API_KEY is required; .env.umich did not provide it." >&2
  exit 1
fi
if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Error: PYTHON_BIN is not executable: ${PYTHON_BIN}" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "${REPO_ROOT}/scripts/singularity/linkding_drift_runtime_lib.sh"

reset_variant_state() {
  local variant="$1"
  exec_drift_manage_shell "${variant}" "
from django.apps import apps
targets = {
    ('bookmarks', 'bookmark'),
    ('bookmarks', 'tag'),
    ('bookmarks', 'bookmarkasset'),
    ('bookmarks', 'bookmarkbundle'),
    ('bookmarks', 'toast'),
}
for model in apps.get_models():
    app_label = model._meta.app_label
    model_name = model._meta.model_name
    if (app_label, model_name) in targets or app_label == 'taggit':
        model.objects.all().delete()
print('reset_ok')
" >/dev/null
}

ensure_baseline_user() {
  local variant="$1"
  local email="${BASELINE_USER}+${variant}@${BASELINE_EMAIL_DOMAIN}"
  SINGULARITYENV_BULK_USER="${BASELINE_USER}" \
  SINGULARITYENV_BULK_PASS="${BASELINE_PASS}" \
  SINGULARITYENV_BULK_EMAIL="${email}" \
    exec_drift_manage_shell "${variant}" \
    "import os; from django.contrib.auth import get_user_model; User=get_user_model(); u,_=User.objects.get_or_create(username=os.environ['BULK_USER'], defaults={'email': os.environ['BULK_EMAIL']}); u.email=os.environ['BULK_EMAIL']; u.is_staff=True; u.is_superuser=True; u.set_password(os.environ['BULK_PASS']); u.save(); print('baseline_ready')" \
    >/dev/null
}

rewrite_access_task_file() {
  local src="$1"
  local dest="$2"
  local host_url="$3"
  "${PYTHON_BIN}" - "$src" "$dest" "$host_url" <<'PY'
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

src, dest, host_url = sys.argv[1:]
host = urlsplit(host_url)
rows = json.loads(Path(src).read_text(encoding="utf-8"))
out = []
for row in rows:
    inst = row.get("instantiation_dict") or {}
    if (inst.get("variant") or inst.get("drift_type") or row.get("variant")) != "access":
        continue
    row = dict(row)
    parsed = urlsplit(row["start_url"])
    row["start_url"] = urlunsplit((host.scheme, host.netloc, parsed.path, parsed.query, parsed.fragment))
    out.append(row)
    break
Path(dest).parent.mkdir(parents=True, exist_ok=True)
Path(dest).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print(len(out))
PY
}

cleanup() {
  stop_all_drift_variants || true
}
trap cleanup EXIT

require_singularity
ensure_drift_port_offset

variant="access"
port="$(drift_variant_port "${variant}")"
host_url="http://127.0.0.1:${port}"
run_dir="${MIN_ROOT}/results/${RUN_LABEL}"
task_file="${run_dir}/tasks_access.offset.json"
mkdir -p "${run_dir}"

echo "[minimal-smoke] python=$("${PYTHON_BIN}" -V 2>&1)"
echo "[minimal-smoke] variant=${variant} host_url=${host_url} run_dir=${run_dir}"

start_drift_variant "${variant}"
wait_drift_variant_ready "${variant}" 90
reset_variant_state "${variant}"
ensure_baseline_user "${variant}"

task_count="$(rewrite_access_task_file "${MIN_ROOT}/configs/focus20_hardv3_smoke.raw.json" "${task_file}" "${host_url}")"
if [[ "${task_count}" != "1" ]]; then
  echo "Error: expected one access task, got ${task_count}" >&2
  exit 1
fi

cd "${MIN_ROOT}"
expel_args=()
if [[ -n "${EXPEL_RULE_FILE:-}" ]]; then
  expel_args=(
    --expel-rule-file "${EXPEL_RULE_FILE}"
    --expel-rule-limit "${EXPEL_RULE_LIMIT:-3}"
    --expel-fidelity "${EXPEL_FIDELITY}"
  )
fi

"${PYTHON_BIN}" -m linkding_xvr_minimal.runner \
  --task-file "${task_file}" \
  --rulebook "${MIN_ROOT}/rulebooks/v2_6.json" \
  "${expel_args[@]}" \
  --run-label "${RUN_LABEL}" \
  --variant access \
  --limit 1 \
  --max-steps "${MAX_STEPS}" \
  --max-tokens "${MAX_TOKENS}" \
  --model "${UITARS_MODEL}" \
  --base-url "${OPENAI_BASE_URL}" \
  --api-key "${OPENAI_API_KEY}" \
  --agent-mode "${AGENT_MODE}" \
  --headless \
  --fail-on-empty-xvr-rules \
  --output-dir "${run_dir}/result_access"

verify_args=(
  --trace "${run_dir}/result_access/*trace*.jsonl"
  --require-cross-version-rules
  --require-rulebook-path
)
if [[ -n "${EXPEL_RULE_FILE:-}" ]]; then
  verify_args+=(--require-expel-rules)
fi
"${PYTHON_BIN}" "${MIN_ROOT}/scripts/verify_trace_rules.py" "${verify_args[@]}"
