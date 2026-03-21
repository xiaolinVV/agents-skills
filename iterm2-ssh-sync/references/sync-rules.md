# Sync Rules

## Source

- Read iTerm2 profiles from `~/Library/Preferences/com.googlecode.iterm2.plist`
- Target config should use the shared canonical path `~/.config/mcp-ssh-manager/ssh-config.toml`
- Preserve legacy `~/.codex/ssh-config.toml` only as a compatibility fallback during migration
- Only import commands that look like password-based SSH launches through `sshpass`
- Ignore Git host aliases from `~/.ssh/config`

## Stable Identity

- Primary identity: iTerm2 profile `Guid`
- Fallback adoption for existing target config: unique `host + user + port`
- The very first write bootstraps this state. Without state, a changed host or port cannot be magically recognized as the same machine.

## Incremental Update Rules

1. If state already knows the profile `Guid`, always reuse its alias and update that section in place. This covers password, host, user, and port changes without creating a duplicate alias.
2. If state is missing but target config has exactly one matching `host + user + port`, adopt that alias.
3. Otherwise generate a new alias.
4. Update managed fields:
   - `host`
   - `user`
   - `password`
   - `port`
   - `description`
5. Preserve existing optional fields on the adopted alias, such as:
   - `default_dir`
   - `key_path`
   - `proxy_jump`
   - `sudo_password`

## Prune Rules

- Every sync reports `stale_tracked` entries that disappeared from iTerm2.
- `--prune-missing` or `--delete-missing` removes only aliases tracked in the sync state but no longer present in iTerm2.
- It must not touch unrelated hand-written entries.

## Alias Map Format

Use a JSON file like this:

```json
{
  "badge": {
    "FastGPT@10.30": "fastgpt_10_30",
    "RAGFlow@10.31": "ragflow_10_31",
    "爱收鞋": "aishouxie"
  },
  "host": {
    "192.168.10.30": "fastgpt_10_30"
  }
}
```

Resolution order:
1. exact badge match
2. exact host match
3. generated slug from badge
4. generated host-based alias

## Recommended Usage

```bash
python3 scripts/sync_iterm2_ssh_to_codex.py scan --json
python3 scripts/sync_iterm2_ssh_to_codex.py sync --dry-run --json
python3 scripts/sync_iterm2_ssh_to_codex.py sync --write
```

## Safety Notes

- iTerm2 commands may contain plaintext passwords. Treat output and generated files as sensitive.
- Do not print passwords unless debugging is explicitly required.
- Do not run connectivity tests unless the user asks.
