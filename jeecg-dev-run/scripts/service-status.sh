#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${script_dir}/common.sh"
load_state_config

check_http() {
  local url="$1"
  curl -s -o /tmp/jeecg-dev-run-status.tmp -w "%{http_code}" --max-time 5 "${url}" || true
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
    echo "managed pid: ${pid}"
  elif [[ -f "${pid_file}" ]]; then
    echo "managed pid file: stale"
  else
    echo "managed pid: none"
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
echo "state_file: ${state_file}"
echo

print_service "backend" "${backend_pid_file}" "${backend_port}" "${backend_url}" "200"
print_service "frontend" "${frontend_pid_file}" "${frontend_port}" "${frontend_url}" "200"
