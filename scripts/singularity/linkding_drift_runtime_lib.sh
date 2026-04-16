#!/usr/bin/env bash
set -euo pipefail

LINKDING_DRIFT_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${LINKDING_DRIFT_LIB_DIR}/linkding_runtime_lib.sh"

LINKDING_DRIFT_BASE_DIR="${LINKDING_DRIFT_BASE_DIR:-$HOME/linkding-drift-runtime}"
LINKDING_DRIFT_IMAGE_DIR="${LINKDING_DRIFT_IMAGE_DIR:-${LINKDING_DRIFT_BASE_DIR}/images}"
LINKDING_DRIFT_VERSION="${LINKDING_DRIFT_VERSION:-1.45.0}"
LINKDING_DRIFT_NAMESPACE="${LINKDING_DRIFT_NAMESPACE:-${SLURM_JOB_ID:-$$}}"
LINKDING_DRIFT_PORT_OFFSET="${LINKDING_DRIFT_PORT_OFFSET:-0}"

_drift_manifest_py() {
  python3 "${LINKDING_DRIFT_LIB_DIR}/linkding_drift_manifest.py" "$@"
}

list_drift_variants() {
  _drift_manifest_py --format names
}

drift_runtime_root() {
  echo "${LINKDING_DRIFT_BASE_DIR}"
}

drift_variant_dir() {
  local variant="$1"
  echo "${LINKDING_DRIFT_BASE_DIR}/${variant}"
}

drift_data_dir() {
  local variant="$1"
  echo "$(drift_variant_dir "${variant}")/data"
}

drift_tmp_dir() {
  local variant="$1"
  echo "$(drift_variant_dir "${variant}")/tmp"
}

drift_secretkey_path() {
  local variant="$1"
  echo "$(drift_variant_dir "${variant}")/secretkey.txt"
}

drift_pid_file() {
  local variant="$1"
  echo "$(drift_variant_dir "${variant}")/linkding_${variant}_${LINKDING_DRIFT_NAMESPACE}.pid"
}

drift_log_file() {
  local variant="$1"
  echo "$(drift_variant_dir "${variant}")/linkding_${variant}_${LINKDING_DRIFT_NAMESPACE}.log"
}

drift_image_path() {
  echo "${LINKDING_DRIFT_IMAGE_DIR}/linkding_drift_1450.sif"
}

drift_variant_port() {
  local variant="$1"
  local base_port
  base_port="$(_drift_manifest_py --variant "${variant}" --field port)"
  echo "$((base_port + LINKDING_DRIFT_PORT_OFFSET))"
}

pick_drift_port_offset() {
  local start_port="${1:-29090}"
  local end_port="${2:-29983}"
  local candidate_port
  local width
  width="$(list_drift_variants | wc -l | xargs)"
  for (( candidate_port=start_port; candidate_port<=end_port; candidate_port++ )); do
    local ok=1
    local port
    for (( port=candidate_port; port<candidate_port+width; port++ )); do
      if port_in_use "${port}"; then
        ok=0
        break
      fi
    done
    if [[ "${ok}" == "1" ]]; then
      echo "$((candidate_port - 9099))"
      return 0
    fi
  done
  echo "Error: could not find a free contiguous drift port block in ${start_port}-${end_port}" >&2
  return 1
}

ensure_drift_port_offset() {
  if [[ "${LINKDING_DRIFT_PORT_OFFSET}" != "0" ]]; then
    return 0
  fi
  local variant
  for variant in $(list_drift_variants); do
    if port_in_use "$(_drift_manifest_py --variant "${variant}" --field port)"; then
      LINKDING_DRIFT_PORT_OFFSET="$(pick_drift_port_offset)"
      export LINKDING_DRIFT_PORT_OFFSET
      echo "[drift] default ports busy, switched offset to ${LINKDING_DRIFT_PORT_OFFSET} (control=$(drift_variant_port control))"
      return 0
    fi
  done
}

drift_bind_args() {
  local variant="$1"
  while IFS=$'\t' read -r source target; do
    [[ -n "${source}" ]] || continue
    printf -- '--bind %s:%s\n' "${source}" "${target}"
  done < <(_drift_manifest_py --variant "${variant}" --format binds)
}

ensure_drift_runtime_paths() {
  local variant="$1"
  local data_dir tmp_dir secretkey_path
  data_dir="$(drift_data_dir "${variant}")"
  tmp_dir="$(drift_tmp_dir "${variant}")"
  secretkey_path="$(drift_secretkey_path "${variant}")"
  mkdir -p "${data_dir}" "${tmp_dir}"
  if [[ ! -s "${secretkey_path}" ]]; then
    head -c 48 /dev/urandom | base64 | tr -d '\n' > "${secretkey_path}"
  fi
}

ensure_drift_image() {
  local image
  image="$(drift_image_path)"
  mkdir -p "${LINKDING_DRIFT_IMAGE_DIR}"
  require_singularity
  if [[ ! -f "${image}" ]]; then
    echo "[drift] pulling base image for ${LINKDING_DRIFT_VERSION} -> ${image}"
    "${SINGULARITY_BIN}" pull "${image}" "docker://sissbruecker/linkding:${LINKDING_DRIFT_VERSION}"
  else
    echo "[drift] image exists: ${image}"
  fi
}

validate_drift_bind_sources() {
  local variant
  for variant in $(list_drift_variants); do
    while IFS=$'\t' read -r source _target; do
      [[ -n "${source}" ]] || continue
      if [[ ! -e "${source}" ]]; then
        echo "Error: missing bind source for ${variant}: ${source}" >&2
        return 1
      fi
    done < <(_drift_manifest_py --variant "${variant}" --format binds)
  done
}

stop_drift_variant() {
  local variant="$1"
  local pid_file pid
  pid_file="$(drift_pid_file "${variant}")"
  if [[ -f "${pid_file}" ]]; then
    pid="$(cat "${pid_file}" 2>/dev/null || true)"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
      kill -TERM "-${pid}" >/dev/null 2>&1 || kill -TERM "${pid}" >/dev/null 2>&1 || true
      sleep 1
      kill -0 "${pid}" >/dev/null 2>&1 && kill -KILL "-${pid}" >/dev/null 2>&1 || true
      kill -0 "${pid}" >/dev/null 2>&1 && kill -KILL "${pid}" >/dev/null 2>&1 || true
    fi
    rm -f "${pid_file}"
  fi
}

_stop_drift_pid_file() {
  local pid_file="$1"
  local pid
  [[ -f "${pid_file}" ]] || return 0
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
    kill -TERM "-${pid}" >/dev/null 2>&1 || kill -TERM "${pid}" >/dev/null 2>&1 || true
    sleep 1
    kill -0 "${pid}" >/dev/null 2>&1 && kill -KILL "-${pid}" >/dev/null 2>&1 || true
    kill -0 "${pid}" >/dev/null 2>&1 && kill -KILL "${pid}" >/dev/null 2>&1 || true
  fi
  rm -f "${pid_file}"
}

start_drift_variant() {
  local variant="$1"
  local image data_dir tmp_dir secretkey_path pid_file log_file runtime_ini port stats_port
  ensure_drift_port_offset
  image="$(drift_image_path)"
  data_dir="$(drift_data_dir "${variant}")"
  tmp_dir="$(drift_tmp_dir "${variant}")"
  secretkey_path="$(drift_secretkey_path "${variant}")"
  pid_file="$(drift_pid_file "${variant}")"
  log_file="$(drift_log_file "${variant}")"
  runtime_ini="${tmp_dir}/uwsgi.runtime.ini"
  port="$(drift_variant_port "${variant}")"
  stats_port="$(stats_port_for_single_port "${port}")"

  ensure_drift_image
  ensure_drift_runtime_paths "${variant}"
  stop_drift_variant "${variant}"

  "${SINGULARITY_BIN}" exec "${image}" /bin/sh -lc 'cat /etc/linkding/uwsgi.ini' | \
    awk -v port="${port}" -v stats_port="${stats_port}" '
      BEGIN { http_seen=0; stats_seen=0 }
      /^[[:space:]]*http[[:space:]]*=/ {
        print "http = :" port
        http_seen=1
        next
      }
      /^[[:space:]]*stats[[:space:]]*=/ {
        print "stats = 127.0.0.1:" stats_port
        stats_seen=1
        next
      }
      { print }
      END {
        if (!http_seen) {
          print "http = :" port
        }
        if (!stats_seen) {
          print "stats = 127.0.0.1:" stats_port
        }
      }
    ' > "${runtime_ini}"

  local -a bind_args=(
    --bind "${data_dir}:/etc/linkding/data"
    --bind "${tmp_dir}:/etc/linkding/tmp"
    --bind "${secretkey_path}:/etc/linkding/secretkey.txt"
    --bind "${runtime_ini}:/etc/linkding/uwsgi.runtime.ini"
  )
  while IFS=$'\t' read -r source target; do
    [[ -n "${source}" ]] || continue
    bind_args+=(--bind "${source}:${target}")
  done < <(_drift_manifest_py --variant "${variant}" --format binds)

  echo "[drift] starting ${variant} on :${port}"
  env setsid "${SINGULARITY_BIN}" exec \
    --cleanenv \
    "${bind_args[@]}" \
    "${image}" \
    /bin/sh -lc "
      if [ -n \"\${VIRTUAL_ENV:-}\" ] && [ -x \"\${VIRTUAL_ENV}/bin/python\" ]; then
        LD_PYTHON=\"\${VIRTUAL_ENV}/bin/python\"
      elif [ -x /opt/venv/bin/python ]; then
        LD_PYTHON=/opt/venv/bin/python
      else
        LD_PYTHON=python
      fi
      if [ -n \"\${VIRTUAL_ENV:-}\" ] && [ -x \"\${VIRTUAL_ENV}/bin/uwsgi\" ]; then
        LD_UWSGI=\"\${VIRTUAL_ENV}/bin/uwsgi\"
      elif [ -x /opt/venv/bin/uwsgi ]; then
        LD_UWSGI=/opt/venv/bin/uwsgi
      else
        LD_UWSGI=uwsgi
      fi
      cd /etc/linkding
      \$LD_PYTHON manage.py migrate
      exec \$LD_UWSGI \
        --ini /etc/linkding/uwsgi.runtime.ini \
        --chdir /etc/linkding \
        --pythonpath /etc/linkding
    " >"${log_file}" 2>&1 < /dev/null &
  echo $! > "${pid_file}"
}

wait_drift_variant_ready() {
  local variant="$1"
  local timeout_sec="${2:-60}"
  local port
  ensure_drift_port_offset
  port="$(drift_variant_port "${variant}")"
  if ! wait_ready "http://127.0.0.1:${port}" "${timeout_sec}"; then
    echo "Error: drift variant ${variant} on port ${port} failed readiness; inspect $(drift_log_file "${variant}")" >&2
    return 1
  fi
}

exec_drift_manage_shell() {
  local variant="$1"
  local code="$2"
  local image data_dir tmp_dir secretkey_path
  image="$(drift_image_path)"
  data_dir="$(drift_data_dir "${variant}")"
  tmp_dir="$(drift_tmp_dir "${variant}")"
  secretkey_path="$(drift_secretkey_path "${variant}")"

  ensure_drift_image
  ensure_drift_runtime_paths "${variant}"

  local -a bind_args=(
    --bind "${data_dir}:/etc/linkding/data"
    --bind "${tmp_dir}:/etc/linkding/tmp"
    --bind "${secretkey_path}:/etc/linkding/secretkey.txt"
  )
  while IFS=$'\t' read -r source target; do
    [[ -n "${source}" ]] || continue
    bind_args+=(--bind "${source}:${target}")
  done < <(_drift_manifest_py --variant "${variant}" --format binds)

  SINGULARITYENV_LINKDING_SHELL_CODE="${code}" "${SINGULARITY_BIN}" exec \
    --cleanenv \
    "${bind_args[@]}" \
    "${image}" \
    /bin/sh -lc 'if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then LD_PYTHON="${VIRTUAL_ENV}/bin/python"; elif [ -x /opt/venv/bin/python ]; then LD_PYTHON=/opt/venv/bin/python; else LD_PYTHON=python; fi; cd /etc/linkding && "$LD_PYTHON" manage.py shell -c "$LINKDING_SHELL_CODE"'
}

stop_all_drift_variants() {
  local stop_scope="${LINKDING_DRIFT_STOP_SCOPE:-namespace}"
  local variant
  if [[ "${stop_scope}" == "all" ]]; then
    for variant in $(list_drift_variants); do
      shopt -s nullglob
      local pid_file
      for pid_file in "$(drift_variant_dir "${variant}")"/linkding_"${variant}"_*.pid; do
        _stop_drift_pid_file "${pid_file}"
      done
      shopt -u nullglob
    done
    return 0
  fi

  for variant in $(list_drift_variants); do
    stop_drift_variant "${variant}"
  done
}
