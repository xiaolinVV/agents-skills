#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${script_dir}/common.sh"
load_state_config

usage() {
  cat <<USAGE
Usage: $(basename "$0") [all|backend|frontend]... [--skip-backend-build]

Start the local development stack in detached mode with PID files and logs.
Default target is: all
Logs: ${state_dir}
USAGE
}

skip_backend_build=0
if [[ $# -eq 0 ]]; then
  targets=(all)
else
  targets=()
  for arg in "$@"; do
    case "${arg}" in
      --skip-backend-build) skip_backend_build=1 ;;
      -h|--help) usage; exit 0 ;;
      all|backend|frontend) targets+=("${arg}") ;;
      *) echo "Unknown argument: ${arg}" >&2; usage >&2; exit 1 ;;
    esac
  done
fi

if [[ " ${targets[*]} " == *" all "* ]]; then
  targets=(backend frontend)
fi

backend_port="$(choose_port "backend" "${backend_pid_file}" "${backend_port}" "${default_backend_port}")"
frontend_port="$(choose_port "frontend" "${frontend_pid_file}" "${frontend_port}" "${default_frontend_port}")"
backend_url="http://${lan_ip}:${backend_port}/jeecg-boot/"
frontend_url="http://${lan_ip}:${frontend_port}/"
stack_mode="background"
stack_agent="${STACK_AGENT:-codex}"
stack_created_at="$(date -Iseconds)"
write_state_config

start_backend() {
  local pid backend_jar

  pid="$(read_pid "${backend_pid_file}")"
  if [[ -n "${pid}" ]] && is_pid_alive "${pid}"; then
    echo "backend already managed by pid ${pid}"
    return 0
  fi
  if port_is_busy "${backend_port}"; then
    echo "backend port ${backend_port} already busy; not starting unmanaged service" >&2
    return 0
  fi
  if [[ "${skip_backend_build}" -eq 0 ]]; then
    echo "building backend jar with clean package..."
    (cd "${backend_dir}" && mvn -pl jeecg-module-system/jeecg-system-start -am clean package -DskipTests)
  else
    echo "skip backend build requested; using the newest existing jar under target/"
  fi
  if ! backend_jar="$(resolve_backend_jar)"; then
    echo "backend jar missing under ${backend_start_dir}/target" >&2
    return 1
  fi
  echo "starting backend..."
  (
    cd "${backend_runtime_home}"
    start_detached "${backend_pid_file}" "${backend_log}" \
      java -jar "${backend_jar}" \
      --server.port="${backend_port}" \
      --jeecg.domainUrl.pc="http://${lan_ip}:${frontend_port}"
  )
  if ! wait_for_http_code "${backend_url}" 200 90; then
    echo "backend failed to become ready; tailing log" >&2
    tail -n 80 "${backend_log}" >&2 || true
    return 1
  fi
  echo "backend ready"
}

start_frontend() {
  local pid

  pid="$(read_pid "${frontend_pid_file}")"
  if [[ -n "${pid}" ]] && is_pid_alive "${pid}"; then
    echo "frontend already managed by pid ${pid}"
    return 0
  fi
  if port_is_busy "${frontend_port}"; then
    echo "frontend port ${frontend_port} already busy; not starting unmanaged service" >&2
    return 0
  fi
  echo "starting frontend..."
  (
    cd "${frontend_dir}"
    start_detached "${frontend_pid_file}" "${frontend_log}" \
      env \
      PORT="${frontend_port}" \
      VUE_APP_API_BASE_URL="http://${lan_ip}:${backend_port}/jeecg-boot" \
      node --openssl-legacy-provider "${frontend_cli}" serve --port "${frontend_port}"
  )
  if ! wait_for_http_code "${frontend_url}" 200 180; then
    echo "frontend failed to become ready; tailing log" >&2
    tail -n 80 "${frontend_log}" >&2 || true
    return 1
  fi
  echo "frontend ready"
}

for target in "${targets[@]}"; do
  case "${target}" in
    backend) start_backend ;;
    frontend) start_frontend ;;
  esac
done

echo
"${script_dir}/service-status.sh"
