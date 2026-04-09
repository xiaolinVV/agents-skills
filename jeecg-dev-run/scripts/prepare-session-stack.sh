#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${script_dir}/common.sh"
state_file="${state_dir}/session.env"
export LOCAL_STACK_STATE_FILE="${state_file}"
load_state_config

usage() {
  cat <<USAGE
Usage: $(basename "$0")

Choose ports for interactive session debugging, persist them to:
  ${state_file}
USAGE
}

if [[ $# -gt 0 ]]; then
  case "$1" in
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
fi

session_backend_pid_file="${pid_dir}/session-backend.pid"
session_frontend_pid_file="${pid_dir}/session-frontend.pid"

backend_port="$(choose_port "backend(session)" "${session_backend_pid_file}" "${backend_port}" "${default_backend_port}")"
frontend_port="$(choose_port "frontend(session)" "${session_frontend_pid_file}" "${frontend_port}" "${default_frontend_port}")"
backend_url="http://${lan_ip}:${backend_port}/jeecg-boot/"
frontend_url="http://${lan_ip}:${frontend_port}/"
stack_mode="session"
stack_agent="${STACK_AGENT:-codex}"
stack_created_at="$(date -Iseconds)"
write_state_config

cat <<INFO
Interactive session state written to:
  ${state_file}

Detected LAN IP: ${lan_ip}

Chosen addresses:
  backend : ${backend_url}
  frontend: ${frontend_url}

Start in separate sessions or terminals with:
  ${script_dir}/run-session-service.sh backend --skip-backend-build
  ${script_dir}/run-session-service.sh frontend
INFO
