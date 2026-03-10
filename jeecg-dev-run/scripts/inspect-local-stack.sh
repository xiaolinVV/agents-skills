#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${script_dir}/common.sh"

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--json]

Inspect known local stack state files and visible listeners.
Default output is a human-readable table.
Use --json for machine-readable output.
USAGE
}

json_output=0
for arg in "$@"; do
  case "${arg}" in
    --json) json_output=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: ${arg}" >&2; usage >&2; exit 1 ;;
  esac
done

record_fields() {
  local source_name="$1"
  local mode_name="$2"
  local agent_name="$3"
  local created_at="$4"
  local service_name="$5"
  local pid_file="$6"
  local port="$7"
  local url="$8"
  local pid status

  pid="$(read_pid "${pid_file}")"
  if [[ -n "${pid}" ]] && is_pid_alive "${pid}"; then
    status="alive"
  elif [[ -f "${pid_file}" ]]; then
    status="stale"
  else
    status="none"
    pid="-"
  fi
  if [[ -z "${pid}" ]]; then
    pid="-"
  fi

  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "${source_name}" "${mode_name}" "${agent_name}" "${status}" "${service_name}" "${port}" "${pid}" "${created_at}" "${url}"
}

collect_state_records() {
  local candidate_state_file="$1"
  local source_name="$2"
  local prefix="$3"
  if [[ ! -f "${candidate_state_file}" ]]; then
    return 0
  fi

  unset BACKEND_PORT FRONTEND_PORT BACKEND_URL FRONTEND_URL STACK_MODE STACK_AGENT STACK_CREATED_AT
  # shellcheck disable=SC1090
  source "${candidate_state_file}"

  record_fields "${source_name}" "${STACK_MODE:-unknown}" "${STACK_AGENT:-unknown}" "${STACK_CREATED_AT:-unknown}" \
    "backend" "${pid_dir}/${prefix}backend.pid" "${BACKEND_PORT:-?}" "${BACKEND_URL:-unknown}"
  record_fields "${source_name}" "${STACK_MODE:-unknown}" "${STACK_AGENT:-unknown}" "${STACK_CREATED_AT:-unknown}" \
    "frontend" "${pid_dir}/${prefix}frontend.pid" "${FRONTEND_PORT:-?}" "${FRONTEND_URL:-unknown}"
}

collect_listener_lines() {
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp | grep -E ':(8080|8081|8082|3000|3001|3002) ' || true
    return 0
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | grep -E ':(8080|8081|8082|3000|3001|3002)' || true
  fi
}

render_table() {
  echo "workspace_root: ${workspace_root}"
  echo "backend_dir: ${backend_dir}"
  echo "frontend_dir: ${frontend_dir}"
  echo "state_dir: ${state_dir}"
  echo
  printf "%-10s %-11s %-8s %-8s %-16s %-6s %-8s %-25s %s\n" \
    "source" "mode" "agent" "pid" "service" "port" "pid_num" "created_at" "url"
  printf "%-10s %-11s %-8s %-8s %-16s %-6s %-8s %-25s %s\n" \
    "----------" "-----------" "--------" "--------" "----------------" "------" "--------" "-------------------------" "---"

  while IFS=$'\t' read -r source_name mode_name agent_name status service_name port pid created_at url; do
    [[ -z "${source_name}" ]] && continue
    printf "%-10s %-11s %-8s %-8s %-16s %-6s %-8s %-25s %s\n" \
      "${source_name}" "${mode_name}" "${agent_name}" "${status}" "${service_name}" "${port}" "${pid}" "${created_at}" "${url}"
  done < <(
    collect_state_records "${state_dir}/stack.env" "background" ""
    collect_state_records "${state_dir}/session.env" "session" "session-"
  )

  echo
  echo "listeners:"
  collect_listener_lines
}

render_json() {
  local records_file listeners_file
  records_file="$(mktemp)"
  listeners_file="$(mktemp)"
  trap "rm -f '${records_file}' '${listeners_file}'" EXIT

  {
    collect_state_records "${state_dir}/stack.env" "background" ""
    collect_state_records "${state_dir}/session.env" "session" "session-"
  } > "${records_file}"
  collect_listener_lines > "${listeners_file}"

  WORKSPACE_ROOT="${workspace_root}" \
  BACKEND_DIR="${backend_dir}" \
  FRONTEND_DIR="${frontend_dir}" \
  STATE_DIR="${state_dir}" \
  RECORDS_FILE="${records_file}" \
  LISTENERS_FILE="${listeners_file}" \
  STOP_BACKGROUND_COMMAND="${script_dir}/stop-local-stack.sh" \
  CLEAR_SESSION_COMMAND="${script_dir}/clear-session-stack.sh" \
    python3 - <<'PYCODE'
import json
import os

records = []
with open(os.environ['RECORDS_FILE'], 'r', encoding='utf-8') as fh:
    for raw in fh:
        line = raw.rstrip('\n')
        if not line:
            continue
        source, mode, agent, status, service, port, pid, created_at, url = line.split('\t', 8)
        records.append(
            {
                'source': source,
                'mode': mode,
                'agent': agent,
                'status': status,
                'service': service,
                'port': int(port) if port.isdigit() else port,
                'pid': None if pid == '-' else int(pid),
                'created_at': created_at,
                'url': url,
            }
        )

listeners = []
with open(os.environ['LISTENERS_FILE'], 'r', encoding='utf-8') as fh:
    for raw in fh:
        line = raw.rstrip('\n')
        if line:
            listeners.append({'raw': line})

background_records = [record for record in records if record['source'] == 'background']
session_records = [record for record in records if record['source'] == 'session']

has_background_state = bool(background_records)
has_live_background = any(record['status'] == 'alive' for record in background_records)
has_session_state = bool(session_records)
has_live_session = any(record['status'] == 'alive' for record in session_records)

payload = {
    'workspace_root': os.environ['WORKSPACE_ROOT'],
    'backend_dir': os.environ['BACKEND_DIR'],
    'frontend_dir': os.environ['FRONTEND_DIR'],
    'state_dir': os.environ['STATE_DIR'],
    'stacks': records,
    'listeners': listeners,
    'actions': {
        'can_stop_background': has_background_state,
        'stop_background_command': os.environ['STOP_BACKGROUND_COMMAND'] if has_background_state else None,
        'background_has_live_process': has_live_background,
        'can_clear_session': has_session_state and not has_live_session,
        'clear_session_command': os.environ['CLEAR_SESSION_COMMAND'] if has_session_state and not has_live_session else None,
        'session_has_live_process': has_live_session,
    },
}
print(json.dumps(payload, ensure_ascii=False, indent=2))
PYCODE
}

if [[ "${json_output}" -eq 1 ]]; then
  render_json
else
  render_table
fi
