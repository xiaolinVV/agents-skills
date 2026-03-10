#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${script_dir}/common.sh"
load_state_config

usage() {
  cat <<USAGE
Usage: $(basename "$0") [all|backend|frontend]...

Stop services started by start-local-stack.sh using stored PID files.
Default target is: all
USAGE
}

if [[ $# -eq 0 ]]; then
  targets=(all)
else
  targets=()
  for arg in "$@"; do
    case "${arg}" in
      -h|--help) usage; exit 0 ;;
      all|backend|frontend) targets+=("${arg}") ;;
      *) echo "Unknown argument: ${arg}" >&2; usage >&2; exit 1 ;;
    esac
  done
fi

if [[ " ${targets[*]} " == *" all "* ]]; then
  targets=(frontend backend)
fi

stop_service() {
  local name="$1"
  local pid_file="$2"
  local port="$3"
  local pid

  pid="$(read_pid "${pid_file}")"
  if [[ -z "${pid}" ]]; then
    if port_is_busy "${port}"; then
      echo "${name} is listening on ${port} but not managed by this script; leaving it alone" >&2
    else
      echo "${name} already stopped"
    fi
    return 0
  fi
  if ! is_pid_alive "${pid}"; then
    echo "${name} pid ${pid} already dead"
    rm -f "${pid_file}"
    return 0
  fi
  echo "stopping ${name} pid ${pid}..."
  kill "${pid}" 2>/dev/null || true
  for _ in $(seq 1 20); do
    if ! is_pid_alive "${pid}"; then
      rm -f "${pid_file}"
      echo "${name} stopped"
      return 0
    fi
    sleep 1
  done
  echo "${name} did not exit after SIGTERM; sending SIGKILL" >&2
  kill -9 "${pid}" 2>/dev/null || true
  rm -f "${pid_file}"
}

for target in "${targets[@]}"; do
  case "${target}" in
    frontend) stop_service "frontend" "${frontend_pid_file}" "${frontend_port}" ;;
    backend) stop_service "backend" "${backend_pid_file}" "${backend_port}" ;;
  esac
done

cleanup_state_if_idle

echo
"${script_dir}/service-status.sh"
