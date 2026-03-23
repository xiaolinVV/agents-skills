---
name: jeecg-dev-run
description: Run and troubleshoot the local Jeecg-Boot development stack for any workspace that follows the standard backend plus Vue admin layout (`jeecg-boot/` and `ant-design-vue-jeecg/`). Use this as the generic fallback runner when the current workspace does not provide a more specific repo-local local-run skill, or when explicitly invoked as `$jeecg-dev-run`.
---

# Jeecg Dev Run

Use this skill as the generic local runner for Jeecg-based business workspaces. Keep it focused on the standard backend plus frontend stack and leave repo-specific extras to repo-local skills.

## Workflow

1. Read `references/local-dev-runbook.md` before starting or debugging services.
2. Before using this skill, check whether the current workspace provides a more specific repo-local local-run skill.
   - If a repo-local runner exists, that runner takes precedence.
   - If no repo-local runner exists and the workspace matches the standard Jeecg layout, use this skill.
   - If the user explicitly invokes `$jeecg-dev-run`, always use this skill.
3. Detect the workspace from the current directory, a backend subdirectory, or a frontend subdirectory before touching any service.
4. Respect `JEECG_DEV_START_DIR` as an explicit workspace override when the caller needs to pin a specific Jeecg workspace.
5. Default to the interactive session helpers unless the user explicitly asks for `nohup`, `后台`, `常驻`, or another detached background flow.
6. Use this startup order unless the user asks otherwise:
   - Backend
   - Frontend
7. When a target port is busy, choose the next free local port and persist the selected ports to the mode-specific state file before launching dependents.
8. Wire the frontend from the selected backend URL instead of assuming `8080`.
9. After each meaningful start, stop, or restart, run `service-status.sh` or `session-status.sh` before reporting success.
10. If something fails, inspect the active process output first, then compare the symptom against `references/local-dev-runbook.md`.
11. Use `inspect-local-stack.sh` when the user wants a neutral view of current state files, port listeners, or action hints.

## Failure Policy

- Do not stop at `failed to run` and dump raw logs without judgment.
- First distinguish the failure type:
  - **Likely environment issue**: missing local toolchain, missing Node dependencies, occupied ports, stale PID/state files, absent backend jar, or shell-level mismatches.
  - **Likely code/project issue**: compile errors, runtime exceptions from application code, schema mismatches caused by project changes, incompatible config semantics inside the repo, or business logic failures after startup.
- For **environment issues**, try to self-heal first and rerun until the service works or the machine blocks further progress.
- For **code/project issues**, stop after the first diagnosis, summarize the likely root cause with evidence, and report before making code changes unless the user explicitly asks for a fix.
- If the service starts with non-blocking warnings, distinguish `usable now` from `needs later cleanup`.

## Final Summary Contract

- After any meaningful start, stop, restart, or troubleshooting action, always give a concrete run summary.
- Include, when applicable:
  - Which services were touched
  - Which mode was used: `session` or `background`
  - Actual ports and URLs
  - Health-check result for each relevant service
  - Cross-service wiring actually in effect (`frontend -> backend`)
  - Non-blocking warnings that still matter
  - Whether the git worktree was kept clean or gained runtime side effects
  - The next exact commands for start, stop, status, inspect, or cleanup
- If the user asked to investigate a failure:
  - For environment problems, state what was auto-fixed before reporting the final state
  - For code/project problems, state the initial diagnosis clearly and stop before unauthorized fixes

## Repo Structure Rules

- Treat this skill as the generic Jeecg runner, not as a replacement for repo-specific local-run skills.
- Repo-local runners win over this generic skill by default; this skill is the fallback for standard Jeecg workspaces that do not provide their own local-run skill.
- Resolve the workspace from the current directory or from `JEECG_DEV_START_DIR` when the caller needs an explicit path override.
- Support these layouts:
  - Standard workspace root containing `jeecg-boot/` and `ant-design-vue-jeecg/`
  - Running from inside `jeecg-boot/`
  - Running from inside `ant-design-vue-jeecg/`
  - Backend directories whose name differs from `jeecg-boot` but still contain the standard Jeecg module layout and live beside `ant-design-vue-jeecg/`
- Do not use `mvn spring-boot:run` from the backend root as the default startup path. In Jeecg workspaces it can hit the parent reactor and fail with `Unable to find a suitable main class`.
- Treat the default backend mode as the built-jar path after `clean package -DskipTests`.
- Keep backend runtime writes out of the backend git worktree by running the jar from `logs/local-dev-stack/backend-home/`.
- Treat `--skip-backend-build` as an explicit fast path that accepts the risk of reusing the newest existing jar.

## Fast Checks

- Use `scripts/service-status.sh` to summarize managed PIDs, port listeners, and HTTP probes for the detached mode.
- Backend is healthy when `http://127.0.0.1:<port>/jeecg-boot/` returns `200`.
- Frontend is healthy when `http://127.0.0.1:<port>/` returns `200`.
- Use `scripts/session-status.sh` for the interactive session mode.
- Use `scripts/inspect-local-stack.sh --json` when the output must be machine-readable.

## Resources

- `references/local-dev-runbook.md` - workspace detection rules, startup order, verification probes, and common Jeecg pitfalls.
- `scripts/common.sh` - shared workspace detection, state handling, port selection, and status helpers.
- `scripts/prepare-session-stack.sh` - choose ports and persist interactive session wiring.
- `scripts/run-session-service.sh` - run backend or frontend in the current foreground session using the prepared session wiring.
- `scripts/session-status.sh` - inspect interactive session state.
- `scripts/clear-session-stack.sh` - clear session metadata after interactive services have been stopped.
- `scripts/inspect-local-stack.sh` - inspect known stack state files, visible listeners, and suggested follow-up actions.
- `scripts/start-local-stack.sh` - managed detached startup with logs and PID files.
- `scripts/stop-local-stack.sh` - managed stop for services started by the companion start script.
- `scripts/service-status.sh` - quick local status summary for backend and frontend.
