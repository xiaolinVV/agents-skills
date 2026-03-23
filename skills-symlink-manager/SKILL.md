---
name: skills-symlink-manager
description: Manage canonical skills in ~/.agents/skills and create/check/repair symlinks into multiple agent skill directories. Use when you need to sync skills across agents, audit link status, or fix incorrect/duplicated skill folders.
---

# Skills Symlink Manager

## Overview

Keep `~/.agents/skills` as the single source of truth and symlink into detected agent skill directories using `scripts/skills_symlink_manager.py`.

Current coverage includes major local agents plus **OpenClaw** global skills (`~/.openclaw/skills`). The agent key remains `openclaw-workspace` for backward compatibility, but the target directory is the OpenClaw global skills dir — not `~/.openclaw/workspace/skills`.

## Local policy overrides

- **OpenClaw target**: use `~/.openclaw/skills` for shared OpenClaw skills. Do not use `~/.openclaw/workspace/skills` for shared installs.
- **`superpowers` special case**: do **not** bulk-link `superpowers` into arbitrary agent skill dirs. It is managed separately per platform:
  - OpenClaw uses the OpenClaw-specific copy under `~/.openclaw/skills/superpowers`
  - Codex uses the upstream repo via `~/.agents/skills/superpowers -> ~/.codex/superpowers/skills`
  - Claude Code / OpenCode use their native plugin installs
- The script enforces this by skipping `superpowers` during link/fix operations.

## Commands (A/B/C/D/E)

- **C — Status**: show link state for detected agents and canonical skills.
- **A — Link one skill**: create symlinks for a single skill.
- **B — Link all skills**: create symlinks for every skill under `~/.agents/skills`.
- **D — Fix**: force-repair conflicts by replacing wrong links or existing folders.
- **E — SkillHub canonical install/update**: install or upgrade skills directly in `~/.agents/skills`; prefer SkillHub first, then fallback to ClawHub if needed; for skills with `package.json`, auto-install dependencies; then link + Git commit/push.

## Safety rules

- Default is non-destructive: no deletes unless you run `fix` or `--force`.
- Always start with `--dry-run` for link/fix to see planned actions.

## Options

- `--prefix <name>`: only include skills whose name starts with the prefix (repeatable or comma-separated).
- `--exclude-prefix <name>`: exclude skills whose name starts with the prefix (repeatable or comma-separated).
- `--json`: machine-readable output (single JSON object).
- `--json-lines`: one JSON object per agent (mutually exclusive with `--json`).
- Combine JSON output with `--verbose` to include per-skill details in status.

## Agent detection

- Uses the same built-in agent list and detection rules as `vercel-labs/skills`.
- Targets detected agents by default; use `--agents` or `--all-agents` to override.

## Examples

```bash
# C: status for all detected agents (now includes OpenClaw global skills when present)
python3 scripts/skills_symlink_manager.py status --verbose

# A: link one skill (dry run)
python3 scripts/skills_symlink_manager.py link --skill my-skill --dry-run

# B: link all skills to detected agents
python3 scripts/skills_symlink_manager.py link --all-skills

# D: force fix a single skill (dry run)
python3 scripts/skills_symlink_manager.py fix --skill my-skill --dry-run

# Limit to specific agents (OpenClaw key stays `openclaw-workspace` for compatibility)
python3 scripts/skills_symlink_manager.py --agents claude-code,codex,openclaw-workspace status

# JSON output + prefix filter
python3 scripts/skills_symlink_manager.py --prefix my- status --json

# JSONL output + exclude prefix
python3 scripts/skills_symlink_manager.py --exclude-prefix tmp- status --json-lines

# E1: install into canonical repo, preferring SkillHub and falling back to ClawHub if needed
python3 scripts/skillhub_canonical.py caldav-calendar

# Same thing via convenience wrapper
skillhub-canonical caldav-calendar

# E2: upgrade one installed skill, then relink + git commit/push
skillhub-canonical upgrade caldav-calendar

# E3: upgrade all installed SkillHub skills in canonical repo
skillhub-canonical update --all

# E4: check available upgrades without changing files
skillhub-canonical upgrade --check-only
```
