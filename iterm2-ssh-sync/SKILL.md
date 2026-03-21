---
name: iterm2-ssh-sync
description: Use when users want to discover password-based SSH servers stored in iTerm2 profiles, import or sync them into the shared `~/.config/mcp-ssh-manager/ssh-config.toml`, preserve aliases across repeated runs, perform dry-run previews, or do incremental updates and optional prune of stale imported entries.
---

# iTerm2 SSH Sync

## Overview

This skill turns iTerm2 profiles into a repeatable source of truth for Codex SSH server config.

It is for **password-based server connections** stored in iTerm2 `Command` fields such as `sshpass -p ... ssh ...`. It is **not** for Git host entries in `~/.ssh/config`.

## When To Use

Use this skill when the user asks to:
- sync SSH server entries from iTerm2 into the shared `~/.config/mcp-ssh-manager/ssh-config.toml`
- import newly added iTerm2 server profiles without duplicating old entries
- update passwords, hosts, ports, users, or badge-derived descriptions incrementally from iTerm2
- preview what would change before writing
- prune Codex SSH entries that no longer exist in iTerm2

Do not use this skill for:
- Git platform SSH aliases in `~/.ssh/config`
- key-based SSH config cleanup
- testing server connectivity unless the user explicitly asks

## Core Rules

- Treat iTerm2 `New Bookmarks` as the source of truth for imported password-based servers.
- Parse iTerm2 via Python `plistlib`, not brittle shell scraping.
- Use iTerm2 profile `Guid` as the stable sync identity.
- Keep a sync state file at the shared path `~/.config/mcp-ssh-manager/iterm2-ssh-sync-state.json` so repeated runs stay incremental.
- Match existing Codex entries by state first. If the same iTerm2 `Guid` already exists, update that alias in place even when host or port changes. Only fall back to unique `host + user + port` adoption when state is missing.
- Preserve existing extra fields like `default_dir` if the target alias already has them.
- Do not guess `default_dir` from iTerm2.
- Dry-run first when the change is not obvious.

## Workflow

### 1. Scan iTerm2 profiles

Run:

```bash
python3 scripts/sync_iterm2_ssh_to_codex.py scan --json
```

This shows which iTerm2 profiles contain password-based SSH commands and what can be imported.

### 2. Preview the sync

Run:

```bash
python3 scripts/sync_iterm2_ssh_to_codex.py sync --dry-run --json
```

This shows which entries would be added, updated in place, kept, or marked as stale because they disappeared from iTerm2.

Quick wrapper:

```bash
./scripts/sync-now.sh              # preview, then ask
./scripts/sync-now.sh --yes        # preview, then write
./scripts/sync-now.sh --preview    # preview only
```

### 3. Apply the sync

Run:

```bash
python3 scripts/sync_iterm2_ssh_to_codex.py sync --write
./scripts/sync-now.sh --yes
```

This updates the shared `~/.config/mcp-ssh-manager/ssh-config.toml` and the state file. The first `sync --write` bootstraps the state file; after that, changed host/port/password values can be updated in place for the same iTerm2 profile `Guid`.

### 4. Prune stale imported entries

Deletion stays explicit because blind delete is how you break userspace. The script always reports stale tracked entries; actual removal happens only when cleanup is requested:

```bash
python3 scripts/sync_iterm2_ssh_to_codex.py sync --dry-run --prune-missing --json
python3 scripts/sync_iterm2_ssh_to_codex.py sync --write --prune-missing
./scripts/sync-now.sh --yes --prune
```

## Alias Control

Default alias generation works like this:
- prefer `Badge Text` when it produces a readable ASCII slug
- otherwise fall back to host-based aliases like `srv_192_168_10_30`
- keep aliases stable through the state file

If badge text contains Chinese or ugly business names, provide an alias map JSON:

```bash
python3 scripts/sync_iterm2_ssh_to_codex.py sync \
  --dry-run \
  --alias-map references/alias-map.example.json \
  --json
```

See `references/sync-rules.md` for the alias-map format and merge rules.

## Files

- Script: `scripts/sync_iterm2_ssh_to_codex.py`
- Quick entry: `scripts/sync-now.sh`
- Rules: `references/sync-rules.md`
- Default iTerm2 source: `~/Library/Preferences/com.googlecode.iterm2.plist`
- Default shared target: `~/.config/mcp-ssh-manager/ssh-config.toml`
- Default shared state file: `~/.config/mcp-ssh-manager/iterm2-ssh-sync-state.json`
- Legacy compatibility: if the shared target/state do not exist but legacy `~/.codex/ssh-config.toml` or `~/.codex/iterm2-ssh-sync-state.json` already exist, the script falls back to the legacy path until you migrate or replace them with symlinks.

## Decision Output

【核心判断】
- ✅ 值得做：当 iTerm2 已经是事实上的服务器入口时，重复手工搬运配置就是浪费生命。
- ❌ 不值得做：如果用户要处理的是 Git 平台 SSH 配置，那是另一回事，别混在一起。

【关键洞察】
- 数据结构：稳定主键不是 host，而是 iTerm2 profile `Guid`
- 复杂度：增量同步靠 state 文件消除重复导入
- 风险点：别误删非本 skill 管理的手工 SSH 条目
