# Local Dev Runbook

## Scope

This skill covers the standard Jeecg local stack:

1. Backend: `jeecg-boot` or a sibling backend directory that contains the standard Jeecg module layout
2. Frontend: `ant-design-vue-jeecg`

Default local stack order:

1. Backend
2. Frontend

## Supported Layouts

Preferred workspace layout:

```text
<workspace-root>/
  jeecg-boot/
  ant-design-vue-jeecg/
```

Also supported:

- Running from inside `jeecg-boot/`
- Running from inside `ant-design-vue-jeecg/`
- Backend directories whose name is not `jeecg-boot` as long as they contain:
  - `pom.xml`
  - `jeecg-module-system/`
  - `jeecg-module-system/jeecg-system-start/`
  - and live beside `ant-design-vue-jeecg/`

If detection fails, rerun from the workspace root or set `JEECG_DEV_START_DIR=/abs/path/to/workspace-or-subdir` before calling the scripts.

## Interactive Session Helpers

Use these scripts when the user wants the default foreground debugging mode with automatic port selection and cross-service wiring:

```bash
~/.agents/skills/jeecg-dev-run/scripts/prepare-session-stack.sh
~/.agents/skills/jeecg-dev-run/scripts/run-session-service.sh backend --skip-backend-build
~/.agents/skills/jeecg-dev-run/scripts/run-session-service.sh frontend
~/.agents/skills/jeecg-dev-run/scripts/session-status.sh
~/.agents/skills/jeecg-dev-run/scripts/clear-session-stack.sh
```

Behavior:

- `prepare-session-stack.sh` chooses free ports and writes them to `logs/local-dev-stack/session.env`
- `run-session-service.sh` runs one service in the current foreground session using that session state
- Backend and frontend reuse the same chosen addresses from `session.env`
- `session-status.sh` probes the ports and URLs from `session.env`
- `clear-session-stack.sh` only clears session metadata; use it after stopping the interactive services
- Backend still runs from `logs/local-dev-stack/backend-home/` so generated runtime files stay out of the backend git worktree

## Managed Background Scripts

Use these scripts for repeatable detached local start/stop:

```bash
~/.agents/skills/jeecg-dev-run/scripts/start-local-stack.sh
~/.agents/skills/jeecg-dev-run/scripts/stop-local-stack.sh
~/.agents/skills/jeecg-dev-run/scripts/service-status.sh
~/.agents/skills/jeecg-dev-run/scripts/inspect-local-stack.sh
```

Behavior:

- `start-local-stack.sh` starts detached local background processes
- Logs go to `logs/local-dev-stack/`
- PID files go to `logs/local-dev-stack/pids/`
- Backend runtime home is `logs/local-dev-stack/backend-home/`
- Chosen ports and URLs are persisted to `logs/local-dev-stack/stack.env`
- `stop-local-stack.sh` only stops processes that were started by the managed start script
- If a default target port is busy, the start script picks the next free local port and writes the real addresses to `stack.env`
- `inspect-local-stack.sh --json` returns machine-readable state and action hints such as `can_stop_background` or `can_clear_session`

Default convention:

- If the user only says `run`, `start`, `启动`, or asks for local debugging, prefer the interactive session mode.
- Only use the managed background scripts when the user explicitly says `nohup`, `后台`, `常驻`, `detach`, or wants a detached start/stop lifecycle.

Useful examples:

```bash
# Start backend + frontend with a backend rebuild
~/.agents/skills/jeecg-dev-run/scripts/start-local-stack.sh

# Start only backend, skip the rebuild
~/.agents/skills/jeecg-dev-run/scripts/start-local-stack.sh backend --skip-backend-build

# Stop everything started by the managed script
~/.agents/skills/jeecg-dev-run/scripts/stop-local-stack.sh
```

## Backend

Interactive run path:

Run from the backend root:

```bash
mvn -pl jeecg-module-system/jeecg-system-start -am clean package -DskipTests
```

Then run the jar from the isolated runtime home:

```bash
java -jar <backend-root>/jeecg-module-system/jeecg-system-start/target/jeecg-system-start-*.jar
```

Why this path exists:

- The generic root command `mvn -pl jeecg-module-system/jeecg-system-start -am spring-boot:run` can invoke the Spring Boot plugin on the parent reactor first and fail with `Unable to find a suitable main class`.
- `clean package` is the safer default because old `target/` artifacts can otherwise survive and make the running backend lag behind the latest source.
- The managed runtime starts the jar from `logs/local-dev-stack/backend-home/`, not from `jeecg-system-start/`, so runtime-generated `config/` trees do not dirty the backend repository.

Success signals:

- Log contains `The following 1 profile is active: "dev"` in the common case
- `http://127.0.0.1:<backend-port>/jeecg-boot/` returns `200`

Managed background mode behavior:

- If `8080` is busy, the script picks the next free local port
- The chosen port is written to `stack.env`
- The backend receives the chosen frontend URL through `--jeecg.domainUrl.pc`

## Frontend

Interactive run path from `ant-design-vue-jeecg/`:

```bash
npm run serve
```

Success signals:

- The dev server prints `App running at:`
- `http://127.0.0.1:<frontend-port>/` returns `200`

Managed background mode behavior:

- If `3000` is busy, the script picks the next free local port
- `VUE_APP_API_BASE_URL` is injected from the actual chosen backend URL before `npm run serve`
- This matters because the frontend request layer reads `window._CONFIG['domianURL']` or `process.env.VUE_APP_API_BASE_URL`, not only the webpack dev proxy

Expected warnings:

- Vue CLI may print `Browserslist: caniuse-lite is outdated`
- Webpack may warn about SQL files that cannot be parsed as modules
- These warnings are acceptable if the dev server reaches `App running at:` and serves `200`

## Recommended Probes

Backend:

```bash
curl -s -o /tmp/jeecg-dev-run-backend.out -w "%{http_code}\n" http://127.0.0.1:8080/jeecg-boot/
```

Frontend:

```bash
curl -s -o /tmp/jeecg-dev-run-frontend.out -w "%{http_code}\n" http://127.0.0.1:3000/
```

## Failure Triage Rule

When startup fails, use this decision rule:

1. Collect the immediate symptom first:
   - last process output
   - current port listeners
   - state file or PID file contents when the scripted modes were used
   - health probe result if the process partially started
2. Decide whether it is mainly an environment problem or a code/project problem.
3. For environment problems, try the obvious repair first:
   - free or shift the port
   - rebuild the backend jar
   - confirm `node_modules/.bin/vue-cli-service` exists
   - clear stale session or background PID files
4. For code/project problems, stop after the first grounded diagnosis and report the evidence.
