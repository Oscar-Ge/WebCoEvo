#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

TASK_FILE="${TASK_FILE:-configs/focus20_hardv3_full.raw.json}"
RULEBOOKS="${RULEBOOKS:-rulebooks/v2_4.json,rulebooks/v2_5.json,rulebooks/v2_6.json}"
VARIANTS="${VARIANTS:-access,surface,content,runtime,process,structural,functional}"
RUN_PREFIX="${RUN_PREFIX:-local_full_matrix}"
LINKDING_HOST_PORT="${LINKDING_HOST_PORT:-19103}"
MAX_STEPS="${MAX_STEPS:-30}"
MAX_TOKENS="${MAX_TOKENS:-300}"

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "Error: OPENAI_API_KEY is required for local matrix runs." >&2
  exit 1
fi

IFS=',' read -r -a rulebook_array <<< "${RULEBOOKS}"
IFS=',' read -r -a variant_array <<< "${VARIANTS}"

for rulebook in "${rulebook_array[@]}"; do
  rulebook="$(echo "${rulebook}" | xargs)"
  rulebook_stem="$(basename "${rulebook}" .json)"
  for variant in "${variant_array[@]}"; do
    variant="$(echo "${variant}" | xargs)"
    run_label="${RUN_PREFIX}_${rulebook_stem}_${variant}"
    echo "[local-matrix] task_file=${TASK_FILE} rulebook=${rulebook} variant=${variant} run_label=${run_label}"
    RUN_LABEL="${run_label}" \
    TASK_FILE="${TASK_FILE}" \
    RULEBOOK="${rulebook}" \
    VARIANT="${variant}" \
    TASK_LIMIT=0 \
    LINKDING_HOST_PORT="${LINKDING_HOST_PORT}" \
    MAX_STEPS="${MAX_STEPS}" \
    MAX_TOKENS="${MAX_TOKENS}" \
      "${SCRIPT_DIR}/local_smoke.sh" smoke
  done
done
