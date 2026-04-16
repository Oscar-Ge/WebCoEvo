#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

expel_args=()
if [[ -n "${EXPEL_RULE_FILE:-}" ]]; then
  expel_args=(
    --expel-rule-file "$EXPEL_RULE_FILE"
    --expel-rule-limit "${EXPEL_RULE_LIMIT:-3}"
    --expel-fidelity "${EXPEL_FIDELITY:-minimal}"
  )
fi

python3 -m linkding_xvr_minimal.runner \
  --task-file configs/focus20_hardv3_smoke.raw.json \
  --rulebook rulebooks/v2_6.json \
  "${expel_args[@]}" \
  --run-label focus20_hardv3_smoke_xvr26_minimal_v1 \
  --max-steps "${MAX_STEPS:-30}" \
  --model "${UITARS_MODEL:-Qwen/Qwen3-VL-30B-A3B-Instruct}" \
  --base-url "${OPENAI_BASE_URL:?OPENAI_BASE_URL is required}" \
  --api-key "${OPENAI_API_KEY:?OPENAI_API_KEY is required}" \
  --agent-mode "${AGENT_MODE:-vl_action_reflection}" \
  --headless \
  --fail-on-empty-xvr-rules
