#!/usr/bin/env bash
set -euo pipefail

MIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_ROOT="${REPO_ROOT:-${MIN_ROOT}}"
RUN_SCRIPT="${MIN_ROOT}/slurm/run_hardv3_variant_singularity.slurm.sh"
RUN_STAMP="${RUN_STAMP:-$(date +%Y%m%d_%H%M%S)}"
EXPEL_RULE_FILE="${EXPEL_RULE_FILE:-${MIN_ROOT}/rulebooks/expel_official_v2.json}"
EXPEL_FIDELITY="${EXPEL_FIDELITY:-official_eval}"
MAX_STEPS="${MAX_STEPS:-30}"
MAX_TOKENS="${MAX_TOKENS:-300}"
AGENT_MODE="${AGENT_MODE:-vl_action_reflection}"
UITARS_MODEL="${UITARS_MODEL:-Qwen/Qwen3-VL-30B-A3B-Instruct}"
SBATCH_TIME="${SBATCH_TIME:-04:00:00}"

declare -a SHARD_NAMES=("access" "surface" "content" "runtime_process" "structural_functional")
declare -a SHARD_VARIANTS=("access" "surface" "content" "runtime:process" "structural:functional")

submit_shard() {
  local job_name="$1"
  local run_label="$2"
  local task_file="$3"
  local rulebook="$4"
  local drift_variants="$5"
  local port_offset="$6"
  local runtime_dir="$7"
  local output_dir="$8"

  sbatch --parsable \
    --time="${SBATCH_TIME}" \
    --job-name="${job_name}" \
    --output="${job_name}-%j.log" \
    --error="${job_name}-%j.log" \
    --export=ALL,REPO_ROOT="${REPO_ROOT}",RUN_LABEL="${run_label}",TASK_FILE="${task_file}",RULEBOOK="${rulebook}",DRIFT_VARIANTS="${drift_variants}",EXPEL_RULE_FILE="${EXPEL_RULE_FILE}",EXPEL_FIDELITY="${EXPEL_FIDELITY}",LINKDING_DRIFT_PORT_OFFSET="${port_offset}",LINKDING_DRIFT_BASE_DIR="${runtime_dir}",OUTPUT_DIR="${output_dir}",AGENT_MODE="${AGENT_MODE}",UITARS_MODEL="${UITARS_MODEL}",MAX_STEPS="${MAX_STEPS}",MAX_TOKENS="${MAX_TOKENS}" \
    "${RUN_SCRIPT}"
}

datasets=("focus20" "taskbank36")
rulebooks=("v2_4" "v2_5" "v2_6")

echo "[minimal-hardv3-matrix] repo=${REPO_ROOT}"
echo "[minimal-hardv3-matrix] run_stamp=${RUN_STAMP}"
echo "[minimal-hardv3-matrix] expel_rule_file=${EXPEL_RULE_FILE}"
echo "[minimal-hardv3-matrix] expel_fidelity=${EXPEL_FIDELITY}"

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

  for rule_idx in "${!rulebooks[@]}"; do
    rulebook_name="${rulebooks[$rule_idx]}"
    rulebook_path="${MIN_ROOT}/rulebooks/${rulebook_name}.json"
    run_label="${dataset}_hardv3_${rulebook_name}_expel_official_minimal_v1"
    group_base=$((20000 + dataset_idx * 3000 + rule_idx * 500))

    echo "[minimal-hardv3-matrix] dataset=${dataset} rulebook=${rulebook_name} task_file=${task_file}"

    for shard_idx in "${!SHARD_NAMES[@]}"; do
      shard_name="${SHARD_NAMES[$shard_idx]}"
      drift_variants="${SHARD_VARIANTS[$shard_idx]}"
      port_offset=$((group_base + (shard_idx + 1) * 100))
      runtime_dir="/home/gecm/linkding-drift-runtimes/${run_label}-${shard_name}-${RUN_STAMP}"
      output_dir="${MIN_ROOT}/results/${run_label}/shard_${shard_name}/run_${RUN_STAMP}"
      short_rule="${rulebook_name#v2_}"
      job_name="m${dataset_prefix}r${short_rule}_${shard_name:0:3}"
      job_id="$(
        submit_shard \
          "${job_name}" \
          "${run_label}" \
          "${task_file}" \
          "${rulebook_path}" \
          "${drift_variants}" \
          "${port_offset}" \
          "${runtime_dir}" \
          "${output_dir}"
      )"
      echo "submitted dataset=${dataset} rulebook=${rulebook_name} shard=${shard_name} job=${job_id}"
    done
  done
done
