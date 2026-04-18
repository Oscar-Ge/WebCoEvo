#!/usr/bin/env bash
set -euo pipefail

MIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-${MIN_ROOT}}"
RUN_SCRIPT="${RUN_SCRIPT:-${MIN_ROOT}/slurm/run_hardv3_variant_singularity.slurm.sh}"
RUN_STAMP="${RUN_STAMP:-$(date +%Y%m%d_%H%M%S)}"
EXPEL_FIDELITY="${EXPEL_FIDELITY:-official_eval}"
MAX_STEPS="${MAX_STEPS:-30}"
MAX_TOKENS="${MAX_TOKENS:-300}"
AGENT_MODE="${AGENT_MODE:-vl_action_reflection}"
UITARS_MODEL="${UITARS_MODEL:-Qwen/Qwen3-VL-30B-A3B-Instruct}"
OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://promaxgb10-d668.eecs.umich.edu:8000/v1}"
SBATCH_TIME="${SBATCH_TIME:-02:00:00}"
TASK_LIMIT="${TASK_LIMIT:-0}"

TASK_VARIANTS="access:surface:content:runtime:process:structural:functional"
RUNTIME_VARIANTS="control"
LINKDING_DRIFT_PROFILE="control"

submit_job() {
  local job_name="$1"
  local run_label="$2"
  local task_file="$3"
  local rulebook="$4"
  local expel_rule_file="$5"
  local require_xvr="$6"
  local require_expel="$7"
  local port_offset="$8"
  local runtime_dir="$9"
  local output_dir="${10}"

  sbatch --parsable \
    --time="${SBATCH_TIME}" \
    --job-name="${job_name}" \
    --output="${job_name}-%j.log" \
    --error="${job_name}-%j.log" \
    --export=ALL,REPO_ROOT="${REPO_ROOT}",RUN_LABEL="${run_label}",TASK_FILE="${task_file}",RULEBOOK="${rulebook}",DRIFT_VARIANTS="${TASK_VARIANTS}",RUNTIME_VARIANTS="${RUNTIME_VARIANTS}",TASK_HOST_PROFILE=control,LINKDING_DRIFT_PROFILE="${LINKDING_DRIFT_PROFILE}",EXPEL_RULE_FILE="${expel_rule_file}",EXPEL_FIDELITY="${EXPEL_FIDELITY}",REQUIRE_XVR_RULES="${require_xvr}",REQUIRE_EXPEL_RULES="${require_expel}",TASK_LIMIT="${TASK_LIMIT}",LINKDING_DRIFT_PORT_OFFSET="${port_offset}",LINKDING_DRIFT_BASE_DIR="${runtime_dir}",OUTPUT_DIR="${output_dir}",AGENT_MODE="${AGENT_MODE}",UITARS_MODEL="${UITARS_MODEL}",OPENAI_BASE_URL="${OPENAI_BASE_URL}",MAX_STEPS="${MAX_STEPS}",MAX_TOKENS="${MAX_TOKENS}" \
    "${RUN_SCRIPT}"
}

datasets=("focus20" "taskbank36")
settings=("no_rules" "expel_only")

echo "[control-rules-matrix] repo=${REPO_ROOT}"
echo "[control-rules-matrix] run_stamp=${RUN_STAMP}"
echo "[control-rules-matrix] task_limit=${TASK_LIMIT}"
echo "[control-rules-matrix] endpoint=${OPENAI_BASE_URL}"

for dataset_idx in "${!datasets[@]}"; do
  dataset="${datasets[$dataset_idx]}"
  case "${dataset}" in
    focus20)
      task_file="${MIN_ROOT}/configs/focus20_hardv3_full.raw.json"
      dataset_prefix="f20"
      ;;
    taskbank36)
      task_file="${MIN_ROOT}/configs/taskbank36_hardv3_full.raw.json"
      dataset_prefix="tb36"
      ;;
    *)
      echo "Unknown dataset: ${dataset}" >&2
      exit 1
      ;;
  esac

  for setting_idx in "${!settings[@]}"; do
    setting="${settings[$setting_idx]}"
    case "${setting}" in
      no_rules)
        rulebook="${MIN_ROOT}/rulebooks/no_xvr_empty.json"
        expel_rule_file=""
        require_xvr=0
        require_expel=0
        setting_short="none"
        run_label="${dataset}_1450_control_no_rules_minimal_v1"
        ;;
      expel_only)
        rulebook="${MIN_ROOT}/rulebooks/no_xvr_empty.json"
        expel_rule_file="${MIN_ROOT}/rulebooks/expel_official_v2.json"
        require_xvr=0
        require_expel=1
        setting_short="exp"
        run_label="${dataset}_1450_control_expel_only_official_minimal_v1"
        ;;
      *)
        echo "Unknown setting: ${setting}" >&2
        exit 1
        ;;
    esac

    port_offset=$((30000 + dataset_idx * 1000 + setting_idx * 100))
    runtime_dir="/home/gecm/linkding-drift-runtimes/${run_label}-${RUN_STAMP}"
    output_dir="${MIN_ROOT}/results/${run_label}/run_${RUN_STAMP}"
    job_name="ctrl_${dataset_prefix}_${setting_short}"

    job_id="$(
      submit_job \
        "${job_name}" \
        "${run_label}" \
        "${task_file}" \
        "${rulebook}" \
        "${expel_rule_file}" \
        "${require_xvr}" \
        "${require_expel}" \
        "${port_offset}" \
        "${runtime_dir}" \
        "${output_dir}"
    )"
    echo "submitted dataset=${dataset} setting=${setting} job=${job_id}"
  done
done
