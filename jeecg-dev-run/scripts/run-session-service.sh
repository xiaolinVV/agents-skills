#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=common.sh
source "${script_dir}/common.sh"
state_file="${state_dir}/session.env"
export LOCAL_STACK_STATE_FILE="${state_file}"

usage() {
  cat <<USAGE
Usage: $(basename "$0") backend|frontend [--skip-backend-build]

Run one local service in the current foreground session using the prepared
interactive session ports from:
  ${state_file}
USAGE
}

skip_backend_build=0
service_name=""
for arg in "$@"; do
  case "${arg}" in
    --skip-backend-build) skip_backend_build=1 ;;
    -h|--help) usage; exit 0 ;;
    backend|frontend)
      if [[ -n "${service_name}" ]]; then
        echo "Only one service can be started at a time" >&2
        exit 1
      fi
      service_name="${arg}"
      ;;
    *) echo "Unknown argument: ${arg}" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ -z "${service_name}" ]]; then
  usage >&2
  exit 1
fi

if [[ ! -f "${state_file}" ]]; then
  "${script_dir}/prepare-session-stack.sh" >/dev/null
fi
load_state_config

session_pid_file="${pid_dir}/session-${service_name}.pid"

run_backend() {
  local backend_jar
  if port_is_busy "${backend_port}"; then
    echo "backend session port ${backend_port} is already busy" >&2
    exit 1
  fi
  if [[ "${skip_backend_build}" -eq 0 ]]; then
    (cd "${backend_dir}" && mvn -pl jeecg-module-system/jeecg-system-start -am clean package -DskipTests)
  else
    echo "skip backend build requested; using the newest existing jar under target/" >&2
  fi
  backend_jar="$(resolve_backend_jar)"
  cd "${backend_runtime_home}"
  echo $$ > "${session_pid_file}"
  exec java -jar "${backend_jar}" \
    --server.port="${backend_port}" \
    --jeecg.domainUrl.pc="http://${lan_ip}:${frontend_port}"
}

run_frontend() {
  if port_is_busy "${frontend_port}"; then
    echo "frontend session port ${frontend_port} is already busy" >&2
    exit 1
  fi
  cd "${frontend_dir}"
  echo $$ > "${session_pid_file}"
  exec env \
    PORT="${frontend_port}" \
    VUE_APP_API_BASE_URL="http://${lan_ip}:${backend_port}/jeecg-boot" \
    node --openssl-legacy-provider "${frontend_cli}" serve --port "${frontend_port}"
}

case "${service_name}" in
  backend) run_backend ;;
  frontend) run_frontend ;;
esac
