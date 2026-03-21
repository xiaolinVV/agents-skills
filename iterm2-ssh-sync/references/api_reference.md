# Command Reference

This file documents the practical command surface for `iterm2-ssh-sync`.

## Python entry

### Scan

```bash
python3 scripts/sync_iterm2_ssh_to_codex.py scan --json
```

Outputs importable password-based SSH entries discovered in iTerm2 profiles.

Options:
- `--iterm2-plist PATH`: override the default iTerm2 plist path
- `--json`: emit JSON
- `--show-passwords`: include plaintext passwords in output; use only when explicitly needed

### Sync

```bash
python3 scripts/sync_iterm2_ssh_to_codex.py sync --dry-run --json
python3 scripts/sync_iterm2_ssh_to_codex.py sync --write
python3 scripts/sync_iterm2_ssh_to_codex.py sync --write --prune-missing
```

Options:
- `--iterm2-plist PATH`: override iTerm2 plist source
- `--target PATH`: override target `ssh-config.toml`
- `--state PATH`: override incremental state file
- `--alias-map PATH`: inject explicit alias mapping
- `--prune-missing` / `--delete-missing`: remove stale tracked aliases
- `--write`: persist changes
- `--dry-run`: preview only
- `--json`: emit machine-readable summary

## Shell entry

```bash
./scripts/sync-now.sh
./scripts/sync-now.sh --yes
./scripts/sync-now.sh --preview
./scripts/sync-now.sh --yes --prune
```

Behavior:
- default: preview, then ask before write
- `--yes`: preview, then write without prompt
- `--preview`: preview only
- `--prune`: propagate stale-entry deletion to Python sync
- `--json`: preview in JSON form

## Output Semantics

### `added`
New alias created in target config.

### `updated`
Existing alias updated in place. See `changed_fields` for exactly what changed.

### `unchanged`
Tracked or adopted alias already matches iTerm2 state.

### `adopted_existing_alias`
State was missing, but an existing target alias with the same `host + user + port` was reused.

### `stale_tracked`
Alias tracked by the state file but no longer present in iTerm2. Report-only unless prune is requested.

### `removed`
Stale tracked aliases actually deleted because prune was enabled.
