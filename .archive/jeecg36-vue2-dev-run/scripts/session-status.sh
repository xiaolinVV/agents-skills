#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${script_dir}/common.sh"
state_file="${state_dir}/session.env"
export LOCAL_STACK_STATE_FILE="${state_file}"
load_state_config

check_http() {
  local url="$1"
  curl --noproxy '*' -s -o /tmp/jeecg-dev-run-status.tmp -w "%{http_code}" --max-time 5 "${url}" || true
}

print_service() {
  local name="$1"
  local pid_file="$2"
  local port="$3"
  local url="$4"
  local expected_hint="$5"
  local pid code

  pid="$(read_pid "${pid_file}")"

  echo "== ${name} =="
  if [[ -n "${pid}" ]] && is_pid_alive "${pid}"; then
    echo "session pid: ${pid}"
  elif [[ -f "${pid_file}" ]]; then
    echo "session pid file: stale"
  else
    echo "session pid: none"
  fi
  echo "port ${port}:"
  port_listener "${port}" || true
  echo "probe ${url}:"
  code="$(check_http "${url}")"
  echo "http ${code} (expected ${expected_hint})"
  echo
}

echo "workspace_root: ${workspace_root}"
echo "backend_dir: ${backend_dir}"
echo "frontend_dir: ${frontend_dir}"
echo "session state: ${state_file}"
echo "agent: ${stack_agent}"
echo "mode: ${stack_mode}"
echo "created_at: ${stack_created_at:-unknown}"
echo

print_service "backend" "${pid_dir}/session-backend.pid" "${backend_port}" "${backend_url}" "200"
print_service "frontend" "${pid_dir}/session-frontend.pid" "${frontend_port}" "${frontend_url}" "200"
