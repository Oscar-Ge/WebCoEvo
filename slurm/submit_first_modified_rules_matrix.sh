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
SBATCH_TIME="${SBATCH_TIME:-04:00:00}"
TASK_LIMIT="${TASK_LIMIT:-0}"
LINKDING_DRIFT_PROFILE="${LINKDING_DRIFT_PROFILE:-first_modified}"

SHARD_NAMES_CSV="${SHARD_NAMES_CSV:-access,surface,content,runtime_process,structural_functional}"
SHARD_VARIANTS_CSV="${SHARD_VARIANTS_CSV:-access,surface,content,runtime:process,structural:functional}"
IFS=',' read -r -a SHARD_NAMES <<< "${SHARD_NAMES_CSV}"
IFS=',' read -r -a SHARD_VARIANTS <<< "${SHARD_VARIANTS_CSV}"
if [[ "${#SHARD_NAMES[@]}" -ne "${#SHARD_VARIANTS[@]}" ]]; then
  echo "SHARD_NAMES_CSV and SHARD_VARIANTS_CSV must have the same length." >&2
  exit 1
fi

submit_shard() {
  local job_name="$1"
  local run_label="$2"
  local task_file="$3"
  local rulebook="$4"
  local drift_variants="$5"
  local expel_rule_file="$6"
  local require_xvr="$7"
  local require_expel="$8"
  local port_offset="$9"
  local runtime_dir="${10}"
  local output_dir="${11}"

  sbatch --parsable \
    --time="${SBATCH_TIME}" \
    --job-name="${job_name}" \
    --output="${job_name}-%j.log" \
    --error="${job_name}-%j.log" \
    --export=ALL,REPO_ROOT="${REPO_ROOT}",RUN_LABEL="${run_label}",TASK_FILE="${task_file}",RULEBOOK="${rulebook}",DRIFT_VARIANTS="${drift_variants}",RUNTIME_VARIANTS="${drift_variants}",TASK_HOST_PROFILE=variant,LINKDING_DRIFT_PROFILE="${LINKDING_DRIFT_PROFILE}",EXPEL_RULE_FILE="${expel_rule_file}",EXPEL_FIDELITY="${EXPEL_FIDELITY}",REQUIRE_XVR_RULES="${require_xvr}",REQUIRE_EXPEL_RULES="${require_expel}",TASK_LIMIT="${TASK_LIMIT}",LINKDING_DRIFT_PORT_OFFSET="${port_offset}",LINKDING_DRIFT_BASE_DIR="${runtime_dir}",OUTPUT_DIR="${output_dir}",AGENT_MODE="${AGENT_MODE}",UITARS_MODEL="${UITARS_MODEL}",OPENAI_BASE_URL="${OPENAI_BASE_URL}",MAX_STEPS="${MAX_STEPS}",MAX_TOKENS="${MAX_TOKENS}" \
    "${RUN_SCRIPT}"
}

datasets=("focus20" "taskbank36")
settings=("expel_only" "v2_4")

echo "[first-modified-rules-matrix] repo=${REPO_ROOT}"
echo "[first-modified-rules-matrix] run_stamp=${RUN_STAMP}"
echo "[first-modified-rules-matrix] profile=${LINKDING_DRIFT_PROFILE}"
echo "[first-modified-rules-matrix] task_limit=${TASK_LIMIT}"
echo "[first-modified-rules-matrix] endpoint=${OPENAI_BASE_URL}"

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
      expel_only)
        rulebook="${MIN_ROOT}/rulebooks/no_xvr_empty.json"
        expel_rule_file="${MIN_ROOT}/rulebooks/expel_official_v2.json"
        require_xvr=0
        require_expel=1
        setting_short="exp"
        run_label="${dataset}_first_modified_expel_only_official_minimal_v1"
        ;;
      v2_4)
        rulebook="${MIN_ROOT}/rulebooks/v2_4.json"
        expel_rule_file="${MIN_ROOT}/rulebooks/expel_official_v2.json"
        require_xvr=1
        require_expel=1
        setting_short="v24"
        run_label="${dataset}_first_modified_v2_4_expel_official_minimal_v1"
        ;;
      *)
        echo "Unknown setting: ${setting}" >&2
        exit 1
        ;;
    esac

    group_base=$((40000 + dataset_idx * 3000 + setting_idx * 500))
    echo "[first-modified-rules-matrix] dataset=${dataset} setting=${setting} task_file=${task_file}"

    for shard_idx in "${!SHARD_NAMES[@]}"; do
      shard_name="${SHARD_NAMES[$shard_idx]}"
      drift_variants="${SHARD_VARIANTS[$shard_idx]}"
      port_offset=$((group_base + (shard_idx + 1) * 100))
      runtime_dir="/home/gecm/linkding-drift-runtimes/${run_label}-${shard_name}-${RUN_STAMP}"
      output_dir="${MIN_ROOT}/results/${run_label}/shard_${shard_name}/run_${RUN_STAMP}"
      job_name="fm${dataset_prefix}${setting_short}_${shard_name:0:3}"

      job_id="$(
        submit_shard \
          "${job_name}" \
          "${run_label}" \
          "${task_file}" \
          "${rulebook}" \
          "${drift_variants}" \
          "${expel_rule_file}" \
          "${require_xvr}" \
          "${require_expel}" \
          "${port_offset}" \
          "${runtime_dir}" \
          "${output_dir}"
      )"
      echo "submitted dataset=${dataset} setting=${setting} shard=${shard_name} job=${job_id}"
    done
  done
done
