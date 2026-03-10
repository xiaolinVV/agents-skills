#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
start_dir="${JEECG_DEV_START_DIR:-$(pwd -P)}"

canonical_dir() {
  (cd "$1" >/dev/null 2>&1 && pwd -P)
}

is_backend_root() {
  local candidate="$1"
  [[ -f "${candidate}/pom.xml" ]] \
    && [[ -d "${candidate}/jeecg-module-system" ]] \
    && [[ -d "${candidate}/jeecg-module-system/jeecg-system-start" ]]
}

find_backend_child() {
  local root="$1"
  local matches=()
  local child

  shopt -s nullglob
  for child in "${root}"/*; do
    [[ -d "${child}" ]] || continue
    if is_backend_root "${child}"; then
      matches+=("$(canonical_dir "${child}")")
    fi
  done
  shopt -u nullglob

  if [[ "${#matches[@]}" -eq 1 ]]; then
    printf '%s\n' "${matches[0]}"
    return 0
  fi
  return 1
}

resolve_workspace_layout() {
  local current parent backend_candidate

  current="$(canonical_dir "${start_dir}")"
  while true; do
    if [[ -d "${current}/ant-design-vue-jeecg" ]]; then
      if [[ -d "${current}/jeecg-boot" ]]; then
        workspace_root="${current}"
        backend_dir="$(canonical_dir "${current}/jeecg-boot")"
        frontend_dir="$(canonical_dir "${current}/ant-design-vue-jeecg")"
        return 0
      fi
      if backend_candidate="$(find_backend_child "${current}")"; then
        workspace_root="${current}"
        backend_dir="${backend_candidate}"
        frontend_dir="$(canonical_dir "${current}/ant-design-vue-jeecg")"
        return 0
      fi
    fi

    if is_backend_root "${current}"; then
      if [[ -d "${current}/ant-design-vue-jeecg" ]]; then
        workspace_root="${current}"
        backend_dir="${current}"
        frontend_dir="$(canonical_dir "${current}/ant-design-vue-jeecg")"
        return 0
      fi
      parent="$(dirname "${current}")"
      if [[ -d "${parent}/ant-design-vue-jeecg" ]]; then
        workspace_root="$(canonical_dir "${parent}")"
        backend_dir="${current}"
        frontend_dir="$(canonical_dir "${parent}/ant-design-vue-jeecg")"
        return 0
      fi
    fi

    if [[ "$(basename "${current}")" == "jeecg-boot" ]]; then
      parent="$(dirname "${current}")"
      if [[ -d "${parent}/ant-design-vue-jeecg" ]]; then
        workspace_root="$(canonical_dir "${parent}")"
        backend_dir="${current}"
        frontend_dir="$(canonical_dir "${parent}/ant-design-vue-jeecg")"
        return 0
      fi
    fi

    if [[ "$(basename "${current}")" == "ant-design-vue-jeecg" ]]; then
      parent="$(dirname "${current}")"
      if [[ -d "${parent}/jeecg-boot" ]]; then
        workspace_root="$(canonical_dir "${parent}")"
        backend_dir="$(canonical_dir "${parent}/jeecg-boot")"
        frontend_dir="${current}"
        return 0
      fi
      if is_backend_root "${parent}"; then
        workspace_root="${parent}"
        backend_dir="${parent}"
        frontend_dir="${current}"
        return 0
      fi
    fi

    if [[ "${current}" == "/" ]]; then
      break
    fi
    current="$(dirname "${current}")"
  done

  return 1
}

fail_common() {
  cat >&2 <<EOF
Unable to detect a Jeecg workspace from: ${start_dir}
Expected one of these layouts:
  - <workspace>/jeecg-boot + <workspace>/ant-design-vue-jeecg
  - a backend root with jeecg-module-system beside ant-design-vue-jeecg
Try one of these fixes:
  1. rerun the command from the workspace root
  2. rerun it from the backend or frontend directory
  3. set JEECG_DEV_START_DIR=/abs/path/to/workspace-or-subdir
EOF
  return 1 2>/dev/null || exit 1
}

if ! resolve_workspace_layout; then
  fail_common
fi

backend_start_dir="${backend_dir}/jeecg-module-system/jeecg-system-start"
if [[ ! -d "${backend_start_dir}" ]]; then
  echo "Missing backend start module under ${backend_dir}" >&2
  return 1 2>/dev/null || exit 1
fi

state_dir="${workspace_root}/logs/local-dev-stack"
pid_dir="${state_dir}/pids"
backend_runtime_home="${state_dir}/backend-home"
mkdir -p "${pid_dir}" "${backend_runtime_home}"

state_file="${LOCAL_STACK_STATE_FILE:-${state_dir}/stack.env}"
mkdir -p "$(dirname "${state_file}")"

backend_pid_file="${pid_dir}/backend.pid"
frontend_pid_file="${pid_dir}/frontend.pid"
backend_log="${state_dir}/backend.log"
frontend_log="${state_dir}/frontend.log"

default_backend_port=8080
default_frontend_port=3000
frontend_cli="${frontend_dir}/node_modules/.bin/vue-cli-service"

resolve_backend_jar() {
  local jar_candidates=()
  local latest_jar=""
  shopt -s nullglob
  jar_candidates=("${backend_start_dir}"/target/jeecg-system-start-*.jar)
  shopt -u nullglob
  if [[ "${#jar_candidates[@]}" -eq 0 ]]; then
    return 1
  fi
  for candidate in "${jar_candidates[@]}"; do
    if [[ -z "${latest_jar}" || "${candidate}" -nt "${latest_jar}" ]]; then
      latest_jar="${candidate}"
    fi
  done
  printf '%s\n' "${latest_jar}"
}

load_state_config() {
  unset BACKEND_PORT FRONTEND_PORT BACKEND_URL FRONTEND_URL STACK_MODE STACK_AGENT STACK_CREATED_AT
  if [[ -f "${state_file}" ]]; then
    # shellcheck disable=SC1090
    source "${state_file}"
  fi
  backend_port="${BACKEND_PORT:-${default_backend_port}}"
  frontend_port="${FRONTEND_PORT:-${default_frontend_port}}"
  backend_url="${BACKEND_URL:-http://127.0.0.1:${backend_port}/jeecg-boot/}"
  frontend_url="${FRONTEND_URL:-http://127.0.0.1:${frontend_port}/}"
  stack_mode="${STACK_MODE:-background}"
  stack_agent="${STACK_AGENT:-codex}"
  stack_created_at="${STACK_CREATED_AT:-}"
}

write_state_config() {
  cat > "${state_file}" <<EOF
STACK_MODE=${stack_mode}
STACK_AGENT=${stack_agent}
STACK_CREATED_AT=${stack_created_at}
BACKEND_PORT=${backend_port}
FRONTEND_PORT=${frontend_port}
BACKEND_URL=${backend_url}
FRONTEND_URL=${frontend_url}
EOF
}

is_pid_alive() {
  local pid="$1"
  [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

read_pid() {
  local pid_file="$1"
  if [[ -f "${pid_file}" ]]; then
    tr -d "[:space:]" < "${pid_file}"
  fi
}

port_listener() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp 2>/dev/null | grep -E ":${port}[[:space:]]" || true
    return 0
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true
    return 0
  fi
  return 0
}

port_is_busy() {
  local port="$1"
  [[ -n "$(port_listener "${port}")" ]]
}

find_available_port() {
  local preferred_port="$1"
  local probe_port="${preferred_port}"
  local upper_bound=$((preferred_port + 200))
  while (( probe_port <= upper_bound )); do
    if ! port_is_busy "${probe_port}"; then
      printf '%s\n' "${probe_port}"
      return 0
    fi
    probe_port=$((probe_port + 1))
  done
  return 1
}

choose_port() {
  local service_name="$1"
  local pid_file="$2"
  local previous_port="$3"
  local preferred_port="$4"
  local pid chosen_port

  pid="$(read_pid "${pid_file}")"
  if [[ -n "${pid}" ]] && is_pid_alive "${pid}"; then
    printf '%s\n' "${previous_port}"
    return 0
  fi
  if [[ -n "${previous_port}" ]] && ! port_is_busy "${previous_port}"; then
    printf '%s\n' "${previous_port}"
    return 0
  fi
  if ! port_is_busy "${preferred_port}"; then
    printf '%s\n' "${preferred_port}"
    return 0
  fi

  chosen_port="$(find_available_port "${preferred_port}")"
  echo "${service_name} port ${preferred_port} busy; using ${chosen_port}" >&2
  printf '%s\n' "${chosen_port}"
}

start_detached() {
  local pid_file="$1"
  local log_file="$2"
  shift 2
  if command -v setsid >/dev/null 2>&1; then
    setsid "$@" </dev/null >> "${log_file}" 2>&1 &
  else
    nohup "$@" </dev/null >> "${log_file}" 2>&1 &
  fi
  echo $! > "${pid_file}"
}

wait_for_http_code() {
  local url="$1"
  local expected="$2"
  local timeout_seconds="$3"
  local start_ts code

  start_ts="$(date +%s)"
  while true; do
    code="$(curl -s -o /tmp/jeecg-dev-run-http.tmp -w "%{http_code}" --max-time 5 "${url}" || true)"
    if [[ "${code}" == "${expected}" ]]; then
      return 0
    fi
    if (( $(date +%s) - start_ts >= timeout_seconds )); then
      echo "Last HTTP code for ${url}: ${code}" >&2
      return 1
    fi
    sleep 1
  done
}

cleanup_state_if_idle() {
  local pid_file pid
  for pid_file in "${backend_pid_file}" "${frontend_pid_file}"; do
    pid="$(read_pid "${pid_file}")"
    if [[ -n "${pid}" ]] && is_pid_alive "${pid}"; then
      return 0
    fi
  done
  rm -f "${state_file}"
}
