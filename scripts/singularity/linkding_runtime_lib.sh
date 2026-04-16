#!/usr/bin/env bash
set -euo pipefail

LINKDING_BASE_DIR="${LINKDING_BASE_DIR:-$HOME/linkding-baselines}"
SINGULARITY_BIN="${SINGULARITY_BIN:-singularity}"
SINGULARITY_IMAGE_DIR="${SINGULARITY_IMAGE_DIR:-${LINKDING_BASE_DIR}/images}"
LINKDING_SINGLE_PORT="${LINKDING_SINGLE_PORT:-9090}"
LINKDING_INSTANCE_NAMESPACE="${LINKDING_INSTANCE_NAMESPACE:-${SLURM_JOB_ID:-$$}}"
LINKDING_KEEP_RUNTIME_TMP="${LINKDING_KEEP_RUNTIME_TMP:-0}"

if [[ -n "${LINKDING_VERSIONS:-}" ]]; then
  IFS=',' read -r -a LINKDING_VERSIONS <<< "${LINKDING_VERSIONS}"
  for i in "${!LINKDING_VERSIONS[@]}"; do
    LINKDING_VERSIONS[$i]="$(echo "${LINKDING_VERSIONS[$i]}" | xargs)"
  done
else
  LINKDING_VERSIONS=(
    "1.4.0"
    "1.14.0"
    "1.25.0"
    "1.45.0"
  )
fi

require_singularity() {
  local version_out=""
  if command -v "${SINGULARITY_BIN}" >/dev/null 2>&1; then
    version_out="$("${SINGULARITY_BIN}" --version 2>&1 || true)"
    if [[ -n "${version_out}" ]] && [[ "${version_out}" != *"modules system"* ]]; then
      return 0
    fi
  fi

  if [[ -n "${MODULESHOME:-}" ]] && [[ -f "${MODULESHOME}/init/bash" ]]; then
    # shellcheck source=/dev/null
    source "${MODULESHOME}/init/bash"
  fi

  if command -v module >/dev/null 2>&1; then
    module load singularity/4.3.4 >/dev/null 2>&1 || module load singularity >/dev/null 2>&1 || true
  fi

  if ! command -v "${SINGULARITY_BIN}" >/dev/null 2>&1; then
    echo "Error: singularity command not found (SINGULARITY_BIN=${SINGULARITY_BIN})." >&2
    exit 1
  fi
  version_out="$("${SINGULARITY_BIN}" --version 2>&1 || true)"
  if [[ -z "${version_out}" ]] || [[ "${version_out}" == *"modules system"* ]]; then
    echo "Error: singularity exists but is not usable; try loading the cluster singularity module." >&2
    exit 1
  fi
}

port_in_use() {
  local port="$1"
  python3 - "$port" <<'PY'
import socket, sys
port = int(sys.argv[1])
s = socket.socket()
try:
    s.bind(("127.0.0.1", port))
except OSError:
    sys.exit(0)
else:
    sys.exit(1)
finally:
    s.close()
PY
}

pick_free_port() {
  local start_port="${1:-29090}"
  local end_port="${2:-29990}"
  local port
  for (( port=start_port; port<=end_port; port++ )); do
    if ! port_in_use "${port}"; then
      echo "${port}"
      return 0
    fi
  done
  echo "Error: could not find a free localhost port in ${start_port}-${end_port}" >&2
  return 1
}

version_to_suffix() {
  local version="$1"
  echo "${version//./}"
}

version_to_legacy_port() {
  local version="$1"
  local minor
  minor="$(echo "${version}" | cut -d'.' -f2)"
  printf '90%02d' "${minor}"
}

instance_name_for_version() {
  local version="$1"
  local suffix
  suffix="$(version_to_suffix "${version}")"
  echo "linkding_${suffix}_${LINKDING_INSTANCE_NAMESPACE}"
}

pid_file_for_version() {
  local version="$1"
  local suffix
  suffix="$(version_to_suffix "${version}")"
  echo "${LINKDING_BASE_DIR}/v${version}/linkding_${suffix}_${LINKDING_INSTANCE_NAMESPACE}.pid"
}

log_file_for_version() {
  local version="$1"
  local suffix
  suffix="$(version_to_suffix "${version}")"
  echo "${LINKDING_BASE_DIR}/v${version}/linkding_${suffix}_${LINKDING_INSTANCE_NAMESPACE}.log"
}

image_path_for_version() {
  local version="$1"
  local suffix
  suffix="$(version_to_suffix "${version}")"
  echo "${SINGULARITY_IMAGE_DIR}/linkding_${suffix}.sif"
}

data_dir_for_version() {
  local version="$1"
  echo "${LINKDING_BASE_DIR}/v${version}/data"
}

tmp_dir_for_version() {
  local version="$1"
  echo "${LINKDING_BASE_DIR}/v${version}/tmp/${LINKDING_INSTANCE_NAMESPACE}"
}

secretkey_path_for_version() {
  local version="$1"
  echo "${LINKDING_BASE_DIR}/v${version}/secretkey.txt"
}

stats_port_for_single_port() {
  local port="$1"
  if ! [[ "${port}" =~ ^[0-9]+$ ]] || (( port < 1 || port > 65535 )); then
    echo "Error: invalid HTTP port for stats socket: ${port}" >&2
    return 1
  fi

  # Keep the stats socket distinct from the HTTP port without overflowing past
  # TCP's max port. uWSGI can wrap too-large values into privileged ports.
  local candidate
  candidate="$((port + 20000))"
  if (( candidate <= 65535 )); then
    echo "${candidate}"
    return 0
  fi

  candidate="$((port - 20000))"
  if (( candidate >= 1024 )); then
    echo "${candidate}"
    return 0
  fi

  echo "Error: could not derive a safe stats port for HTTP port ${port}" >&2
  return 1
}

ensure_runtime_paths() {
  local version="$1"
  local data_dir tmp_dir secretkey_path
  data_dir="$(data_dir_for_version "${version}")"
  tmp_dir="$(tmp_dir_for_version "${version}")"
  secretkey_path="$(secretkey_path_for_version "${version}")"
  mkdir -p "${data_dir}" "${tmp_dir}"
  if [[ ! -s "${secretkey_path}" ]]; then
    head -c 48 /dev/urandom | base64 | tr -d '\n' > "${secretkey_path}"
  fi
}

ensure_image() {
  local version="$1"
  local image
  image="$(image_path_for_version "${version}")"
  mkdir -p "${SINGULARITY_IMAGE_DIR}"
  if [[ ! -f "${image}" ]]; then
    echo "[singularity] pulling image for ${version} -> ${image}"
    "${SINGULARITY_BIN}" pull "${image}" "docker://sissbruecker/linkding:${version}"
  else
    echo "[singularity] image exists for ${version}: ${image}"
  fi
}

should_keep_runtime_tmp() {
  case "${LINKDING_KEEP_RUNTIME_TMP}" in
    1|true|TRUE|yes|YES)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

cleanup_runtime_tmp_dir() {
  local tmp_dir="$1"
  if rm -rf "${tmp_dir}" >/dev/null 2>&1; then
    return 0
  fi
  if [[ -e "${tmp_dir}" ]]; then
    echo "[singularity] warning: unable to fully remove runtime tmp ${tmp_dir}; continuing" >&2
  fi
}

stop_instance() {
  local version="$1"
  local pid_file pid tmp_dir
  pid_file="$(pid_file_for_version "${version}")"
  tmp_dir="$(tmp_dir_for_version "${version}")"
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
  if ! should_keep_runtime_tmp; then
    cleanup_runtime_tmp_dir "${tmp_dir}"
  fi
}

start_instance() {
  local version="$1"
  local image data_dir tmp_dir secretkey_path pid_file log_file stats_port runtime_ini
  image="$(image_path_for_version "${version}")"
  data_dir="$(data_dir_for_version "${version}")"
  tmp_dir="$(tmp_dir_for_version "${version}")"
  secretkey_path="$(secretkey_path_for_version "${version}")"
  pid_file="$(pid_file_for_version "${version}")"
  log_file="$(log_file_for_version "${version}")"
  stats_port="$(stats_port_for_single_port "${LINKDING_SINGLE_PORT}")"
  runtime_ini="${tmp_dir}/uwsgi.runtime.ini"

  stop_instance "${version}"
  ensure_image "${version}"
  ensure_runtime_paths "${version}"

  "${SINGULARITY_BIN}" exec "${image}" /bin/sh -lc 'cat /etc/linkding/uwsgi.ini' | \
    awk -v port="${LINKDING_SINGLE_PORT}" -v stats_port="${stats_port}" '
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

  echo "[singularity] starting service for ${version} from ${image} on :${LINKDING_SINGLE_PORT}"
  setsid "${SINGULARITY_BIN}" exec \
    --cleanenv \
    --bind "${data_dir}:/etc/linkding/data" \
    --bind "${tmp_dir}:/etc/linkding/tmp" \
    --bind "${secretkey_path}:/etc/linkding/secretkey.txt" \
    --bind "${runtime_ini}:/etc/linkding/uwsgi.runtime.ini" \
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

wait_ready() {
  local url="$1"
  local timeout_sec="${2:-60}"
  local elapsed=0
  while (( elapsed < timeout_sec )); do
    if curl -fsS "${url}/login" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  echo "Error: Linkding not ready at ${url} after ${timeout_sec}s" >&2
  return 1
}

exec_manage_shell() {
  local version="$1"
  local code="$2"
  local image data_dir tmp_dir secretkey_path
  image="$(image_path_for_version "${version}")"
  data_dir="$(data_dir_for_version "${version}")"
  tmp_dir="$(tmp_dir_for_version "${version}")"
  secretkey_path="$(secretkey_path_for_version "${version}")"

  ensure_image "${version}"
  ensure_runtime_paths "${version}"

  SINGULARITYENV_LINKDING_SHELL_CODE="${code}" "${SINGULARITY_BIN}" exec \
    --cleanenv \
    --bind "${data_dir}:/etc/linkding/data" \
    --bind "${tmp_dir}:/etc/linkding/tmp" \
    --bind "${secretkey_path}:/etc/linkding/secretkey.txt" \
    "${image}" \
    /bin/sh -lc 'if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then LD_PYTHON="${VIRTUAL_ENV}/bin/python"; elif [ -x /opt/venv/bin/python ]; then LD_PYTHON=/opt/venv/bin/python; else LD_PYTHON=python; fi; cd /etc/linkding && "$LD_PYTHON" manage.py shell -c "$LINKDING_SHELL_CODE"'
}

exec_manage_shell_last_line() {
  local version="$1"
  local code="$2"
  exec_manage_shell "${version}" "${code}" | tail -n 1 | tr -d '\r'
}

stop_all_namespaced_instances() {
  local version
  for version in "${LINKDING_VERSIONS[@]}"; do
    stop_instance "${version}"
  done
}
