#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

VARIANT="${VARIANT:-access}"
LINKDING_HOST_PORT="${LINKDING_HOST_PORT:-9103}"
RUN_LABEL="${RUN_LABEL:-local_${VARIANT}_smoke}"
RULEBOOK="${RULEBOOK:-rulebooks/v2_6.json}"
TASK_FILE="${TASK_FILE:-configs/focus20_hardv3_smoke.raw.json}"
EXPEL_RULE_FILE="${EXPEL_RULE_FILE:-rulebooks/expel_official_v2.json}"
EXPEL_FIDELITY="${EXPEL_FIDELITY:-official_eval}"
EXPEL_RULE_LIMIT="${EXPEL_RULE_LIMIT:-3}"
MAX_STEPS="${MAX_STEPS:-10}"
MAX_TOKENS="${MAX_TOKENS:-300}"
TASK_LIMIT="${TASK_LIMIT:-1}"
AGENT_MODE="${AGENT_MODE:-vl_action_reflection}"
OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://host.docker.internal:8000/v1}"
UITARS_MODEL="${UITARS_MODEL:-Qwen/Qwen3-VL-30B-A3B-Instruct}"
COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/.docker/compose.${VARIANT}.yml}"
RUN_DIR="${RUN_DIR:-${REPO_ROOT}/results/${RUN_LABEL}}"
CONTAINER_RUN_DIR="/workspace/results/${RUN_LABEL}"
CONTAINER_TASK_FILE="${CONTAINER_RUN_DIR}/tasks.${VARIANT}.docker.json"

compose() {
  docker compose -f "${COMPOSE_FILE}" "$@"
}

wait_ready() {
  local url="$1"
  local timeout="${2:-90}"
  local start
  start="$(date +%s)"
  until curl -fsS "${url}" >/dev/null 2>&1; do
    if (( "$(date +%s)" - start > timeout )); then
      echo "Error: ${url} did not become ready within ${timeout}s" >&2
      return 1
    fi
    sleep 2
  done
}

manage_shell() {
  local code="$1"
  compose exec -T -e LINKDING_SHELL_CODE="${code}" linkding /bin/sh -lc '
    if [ -x /opt/venv/bin/python ]; then LD_PYTHON=/opt/venv/bin/python; else LD_PYTHON=python; fi
    cd /etc/linkding
    "$LD_PYTHON" manage.py shell -c "$LINKDING_SHELL_CODE"
  '
}

reset_variant_state() {
  manage_shell "
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
"
}

ensure_baseline_user() {
  compose exec -T \
    -e BULK_USER="${BASELINE_USER:-baseline}" \
    -e BULK_PASS="${BASELINE_PASS:-Baseline123!}" \
    -e BULK_EMAIL="${BASELINE_EMAIL:-baseline+${VARIANT}@local.test}" \
    linkding /bin/sh -lc '
      if [ -x /opt/venv/bin/python ]; then LD_PYTHON=/opt/venv/bin/python; else LD_PYTHON=python; fi
      cd /etc/linkding
      "$LD_PYTHON" manage.py shell -c "import os; from django.contrib.auth import get_user_model; User=get_user_model(); u,_=User.objects.get_or_create(username=os.environ[\"BULK_USER\"], defaults={\"email\": os.environ[\"BULK_EMAIL\"]}); u.email=os.environ[\"BULK_EMAIL\"]; u.is_staff=True; u.is_superuser=True; u.set_password(os.environ[\"BULK_PASS\"]); u.save(); print(\"baseline_ready\")"
    '
}

rewrite_task_file() {
  mkdir -p "${RUN_DIR}"
  compose run --rm runner python - "${TASK_FILE}" "${CONTAINER_TASK_FILE}" "${VARIANT}" "http://linkding:9090" "${TASK_LIMIT}" <<'PY'
import json
import sys
from pathlib import Path

from linkding_xvr_minimal.tasks import load_raw_tasks, rewrite_task_start_urls

src, dest, variant, host_url, limit = sys.argv[1:]
rows = load_raw_tasks(src)
rewritten = rewrite_task_start_urls(rows, variant_host_map={variant: host_url}, variants=[variant])
limit = int(limit)
if limit > 0:
    rewritten = rewritten[:limit]
Path(dest).parent.mkdir(parents=True, exist_ok=True)
Path(dest).write_text(json.dumps(rewritten, indent=2, ensure_ascii=False), encoding="utf-8")
print(len(rewritten))
PY
}

usage() {
  cat <<'EOF'
Usage: scripts/docker/local_smoke.sh [preflight|up|smoke|down]

Environment:
  VARIANT=access
  LINKDING_HOST_PORT=9103
  OPENAI_BASE_URL=http://host.docker.internal:8000/v1
  OPENAI_API_KEY=...
  TASK_LIMIT=1   # set TASK_LIMIT=0 to keep all tasks for the selected variant
EOF
}

command="${1:-preflight}"

python3 scripts/docker/generate_local_compose.py \
  --variant "${VARIANT}" \
  --host-port "${LINKDING_HOST_PORT}" \
  --out "${COMPOSE_FILE}" >/dev/null

case "${command}" in
  preflight)
    compose run --rm runner python -m linkding_xvr_minimal.runner \
      --task-file "${TASK_FILE}" \
      --rulebook "${RULEBOOK}" \
      --run-label "${RUN_LABEL}_preflight" \
      --variant "${VARIANT}" \
      --preflight-rules-only \
      --fail-on-empty-xvr-rules \
      --expel-rule-file "${EXPEL_RULE_FILE}" \
      --expel-rule-limit "${EXPEL_RULE_LIMIT}" \
      --expel-fidelity "${EXPEL_FIDELITY}"
    ;;
  up)
    compose up -d linkding
    wait_ready "http://127.0.0.1:${LINKDING_HOST_PORT}/" 90
    reset_variant_state
    ensure_baseline_user
    echo "Linkding ${VARIANT} is ready at http://127.0.0.1:${LINKDING_HOST_PORT}"
    ;;
  smoke)
    if [[ -z "${OPENAI_API_KEY:-}" ]]; then
      echo "Error: OPENAI_API_KEY is required for smoke. Use preflight/up without a model key." >&2
      exit 1
    fi
    compose up -d linkding
    wait_ready "http://127.0.0.1:${LINKDING_HOST_PORT}/" 90
    reset_variant_state
    ensure_baseline_user
    task_count="$(rewrite_task_file | tail -n 1)"
    if [[ "${task_count}" == "0" ]]; then
      echo "Error: expected at least one ${VARIANT} task, got ${task_count}" >&2
      exit 1
    fi
    limit_args=()
    if [[ "${TASK_LIMIT}" != "0" ]]; then
      limit_args+=(--limit "${TASK_LIMIT}")
    fi
    compose run --rm runner python -m linkding_xvr_minimal.runner \
      --task-file "${CONTAINER_TASK_FILE}" \
      --rulebook "${RULEBOOK}" \
      --expel-rule-file "${EXPEL_RULE_FILE}" \
      --expel-rule-limit "${EXPEL_RULE_LIMIT}" \
      --expel-fidelity "${EXPEL_FIDELITY}" \
      --run-label "${RUN_LABEL}" \
      --variant "${VARIANT}" \
      "${limit_args[@]}" \
      --max-steps "${MAX_STEPS}" \
      --max-tokens "${MAX_TOKENS}" \
      --model "${UITARS_MODEL}" \
      --base-url "${OPENAI_BASE_URL}" \
      --api-key "${OPENAI_API_KEY}" \
      --agent-mode "${AGENT_MODE}" \
      --headless \
      --fail-on-empty-xvr-rules \
      --output-dir "${CONTAINER_RUN_DIR}/result_${VARIANT}"
    compose run --rm runner python scripts/verify_trace_rules.py \
      --trace "${CONTAINER_RUN_DIR}/result_${VARIANT}/*trace*.jsonl" \
      --require-cross-version-rules \
      --require-rulebook-path \
      --require-expel-rules
    ;;
  down)
    compose down
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
