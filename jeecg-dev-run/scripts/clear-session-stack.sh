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
Usage: $(basename "$0") [--force]

Clear interactive session metadata after the session services have been stopped.
Default behavior refuses cleanup while a recorded session PID is still alive.
USAGE
}

force=0
for arg in "$@"; do
  case "${arg}" in
    --force) force=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: ${arg}" >&2; usage >&2; exit 1 ;;
  esac
done

session_pid_files=(
  "${pid_dir}/session-backend.pid"
  "${pid_dir}/session-frontend.pid"
)

for pid_file in "${session_pid_files[@]}"; do
  pid="$(read_pid "${pid_file}")"
  if [[ -n "${pid}" ]] && is_pid_alive "${pid}"; then
    if [[ "${force}" -eq 0 ]]; then
      echo "session process ${pid} from ${pid_file} is still alive; stop it before cleanup or use --force" >&2
      exit 1
    fi
  fi
  rm -f "${pid_file}"
done

rm -f "${state_file}"
echo "session metadata cleared"
