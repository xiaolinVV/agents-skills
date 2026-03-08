---
name: skills-symlink-manager
description: Manage canonical skills in ~/.agents/skills and create/check/repair symlinks into multiple agent skill directories. Use when you need to sync skills across agents, audit link status, or fix incorrect/duplicated skill folders.
---

# Skills Symlink Manager

## Overview

Keep `~/.agents/skills` as the single source of truth and symlink into detected agent skill directories using `scripts/skills_symlink_manager.py`.

## Commands (A/B/C/D)

- **C — Status**: show link state for detected agents and canonical skills.
- **A — Link one skill**: create symlinks for a single skill.
- **B — Link all skills**: create symlinks for every skill under `~/.agents/skills`.
- **D — Fix**: force-repair conflicts by replacing wrong links or existing folders.

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
# C: status for all detected agents
python3 scripts/skills_symlink_manager.py status --verbose

# A: link one skill (dry run)
python3 scripts/skills_symlink_manager.py link --skill my-skill --dry-run

# B: link all skills to detected agents
python3 scripts/skills_symlink_manager.py link --all-skills

# D: force fix a single skill (dry run)
python3 scripts/skills_symlink_manager.py fix --skill my-skill --dry-run

# Limit to specific agents
python3 scripts/skills_symlink_manager.py status --agents claude-code,codex

# JSON output + prefix filter
python3 scripts/skills_symlink_manager.py status --prefix my- --json

# JSONL output + exclude prefix
python3 scripts/skills_symlink_manager.py status --exclude-prefix tmp- --json-lines
```
