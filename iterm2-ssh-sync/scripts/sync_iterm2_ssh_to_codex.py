#!/usr/bin/env python3

import argparse
import json
import plistlib
import re
import shlex
import sys
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_PLIST = Path('~/Library/Preferences/com.googlecode.iterm2.plist').expanduser()
DEFAULT_TARGET = Path('~/.codex/ssh-config.toml').expanduser()
DEFAULT_STATE = Path('~/.codex/iterm2-ssh-sync-state.json').expanduser()

SSH_SECTION_RE = re.compile(r'^\[ssh_servers\.([^\]]+)\]\s*$')
IP_RE = re.compile(r'^[0-9.]+$')
SSH_OPTIONS_WITH_VALUE = {'-p', '-o', '-i', '-J', '-F', '-b', '-c', '-D', '-L', '-R', '-W', '-E', '-l', '-S'}
MANAGED_FIELDS = ('host', 'user', 'password', 'port', 'description')


@dataclass
class ProfileEntry:
    guid: str
    badge: str
    description: str
    command: str
    host: str
    user: str
    password: str
    port: int


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def load_alias_map(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {'badge': {}, 'host': {}}
    data = load_json(path)
    badge = data.get('badge') or {}
    host = data.get('host') or {}
    if not isinstance(badge, dict) or not isinstance(host, dict):
        raise ValueError('alias map must contain object keys "badge" and "host"')
    return {
        'badge': {str(key): str(value) for key, value in badge.items()},
        'host': {str(key): str(value) for key, value in host.items()},
    }


def normalize_alias(value: str) -> str:
    alias = value.strip().lower()
    alias = alias.replace('@', '_').replace('.', '_').replace('-', '_').replace(' ', '_')
    alias = re.sub(r'[^a-z0-9_]+', '_', alias)
    alias = re.sub(r'_+', '_', alias).strip('_')
    if not alias:
        return ''
    if alias[0].isdigit():
        alias = f'srv_{alias}'
    return alias


def generated_alias(entry: ProfileEntry, alias_map: dict[str, dict[str, str]]) -> str:
    mapped_badge = alias_map['badge'].get(entry.badge)
    if mapped_badge:
        alias = normalize_alias(mapped_badge)
        if alias:
            return alias

    mapped_host = alias_map['host'].get(entry.host)
    if mapped_host:
        alias = normalize_alias(mapped_host)
        if alias:
            return alias

    if entry.badge and not IP_RE.fullmatch(entry.badge):
        alias = normalize_alias(entry.badge)
        if alias:
            if entry.port != 22 and not re.search(rf'(^|_)(p{entry.port}|{entry.port})($|_)', alias):
                alias = f'{alias}_p{entry.port}'
            normalized_user = normalize_alias(entry.user)
            if entry.user != 'root' and normalized_user and not re.search(rf'(^|_){re.escape(normalized_user)}($|_)', alias):
                alias = f'{alias}_u_{normalized_user}'
            return alias

    alias = f"srv_{entry.host.replace('.', '_')}"
    if entry.port != 22:
        alias += f'_p{entry.port}'
    normalized_user = normalize_alias(entry.user)
    if entry.user != 'root' and normalized_user:
        alias += f'_u_{normalized_user}'
    return normalize_alias(alias)


def make_unique_alias(base_alias: str, used_aliases: set[str]) -> str:
    alias = base_alias
    index = 2
    while alias in used_aliases:
        alias = f'{base_alias}_{index}'
        index += 1
    used_aliases.add(alias)
    return alias


def parse_sshpass_command(command: str) -> tuple[str, int, str, str] | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if not tokens:
        return None

    sshpass_index = next((idx for idx, token in enumerate(tokens) if Path(token).name == 'sshpass'), None)
    if sshpass_index is None:
        return None

    password = None
    ssh_index = None
    index = sshpass_index + 1
    while index < len(tokens):
        token = tokens[index]
        if token == '-p' and index + 1 < len(tokens):
            password = tokens[index + 1]
            index += 2
            continue
        if Path(token).name == 'ssh':
            ssh_index = index
            break
        index += 1

    if password is None or ssh_index is None:
        return None

    port = 22
    target = None
    index = ssh_index + 1
    while index < len(tokens):
        token = tokens[index]
        if token in SSH_OPTIONS_WITH_VALUE:
            if index + 1 >= len(tokens):
                return None
            if token == '-p':
                try:
                    port = int(tokens[index + 1])
                except ValueError:
                    return None
            index += 2
            continue
        if token.startswith('-'):
            index += 1
            continue
        if '@' in token:
            target = token
            break
        index += 1

    if not target or '@' not in target:
        return None

    user, host = target.split('@', 1)
    user = user.strip()
    host = host.strip()
    if not user or not host:
        return None
    return password, port, user, host


def extract_entries(plist_path: Path) -> list[ProfileEntry]:
    with open(plist_path, 'rb') as handle:
        data = plistlib.load(handle)

    entries: list[ProfileEntry] = []
    for item in data.get('New Bookmarks', []):
        command = str(item.get('Command') or '').strip()
        parsed = parse_sshpass_command(command)
        if not parsed:
            continue
        password, port, user, host = parsed
        entries.append(
            ProfileEntry(
                guid=str(item.get('Guid') or '').strip(),
                badge=str(item.get('Badge Text') or '').strip(),
                description=str(item.get('Description') or '').strip(),
                command=command,
                host=host,
                user=user,
                password=password,
                port=port,
            )
        )
    return entries


def default_preamble() -> str:
    return '\n'.join([
        '# Codex SSH server definitions',
        '# Imported entries may be maintained by iterm2-ssh-sync',
    ])


def toml_loads(text: str) -> dict[str, Any]:
    try:
        import tomllib
    except ModuleNotFoundError as exc:
        raise RuntimeError('Python 3.11+ is required for tomllib') from exc
    return tomllib.loads(text) if text.strip() else {}


def load_target(path: Path) -> tuple[str, list[str], dict[str, dict[str, Any]]]:
    if not path.exists():
        return default_preamble(), [], {}

    text = path.read_text(encoding='utf-8')
    preamble_lines: list[str] = []
    aliases_in_order: list[str] = []
    before_first_section = True
    for line in text.splitlines():
        section_match = SSH_SECTION_RE.match(line.strip())
        if section_match:
            before_first_section = False
            aliases_in_order.append(section_match.group(1))
            continue
        if before_first_section:
            preamble_lines.append(line)

    data = toml_loads(text)
    servers = data.get('ssh_servers') or {}
    if not isinstance(servers, dict):
        raise ValueError('ssh-config.toml must contain [ssh_servers.*] tables')
    normalized = {str(alias): dict(values) for alias, values in servers.items() if isinstance(values, dict)}
    return '\n'.join(preamble_lines).rstrip(), aliases_in_order, normalized


def serialize_value(value: Any) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return '[' + ', '.join(serialize_value(item) for item in value) + ']'
    raise TypeError(f'unsupported TOML value type: {type(value).__name__}')


def field_order(server: dict[str, Any]) -> list[str]:
    preferred = ['host', 'user', 'password', 'key_path', 'passphrase', 'port', 'default_dir', 'platform', 'proxy_jump', 'description', 'sudo_password']
    seen = [key for key in preferred if key in server]
    remainder = sorted(key for key in server.keys() if key not in seen)
    return seen + remainder


def write_target(path: Path, preamble: str, aliases_in_order: list[str], servers: dict[str, dict[str, Any]]) -> None:
    ordered_aliases = [alias for alias in aliases_in_order if alias in servers]
    ordered_aliases.extend(sorted(alias for alias in servers if alias not in ordered_aliases))
    lines: list[str] = []
    header = preamble.strip()
    if header:
        lines.append(header)
        lines.append('')
    for alias in ordered_aliases:
        lines.append(f'[ssh_servers.{alias}]')
        for key in field_order(servers[alias]):
            value = servers[alias][key]
            if value is None:
                continue
            lines.append(f'{key} = {serialize_value(value)}')
        lines.append('')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')


def build_match_index(servers: dict[str, dict[str, Any]]) -> dict[tuple[str, str, int], list[str]]:
    index: dict[tuple[str, str, int], list[str]] = {}
    for alias, server in servers.items():
        host = str(server.get('host') or '').strip()
        user = str(server.get('user') or '').strip()
        port = int(server.get('port') or 22)
        if not host or not user:
            continue
        index.setdefault((host, user, port), []).append(alias)
    return index


def managed_snapshot(entry: ProfileEntry) -> dict[str, Any]:
    return {
        'badge': entry.badge,
        'host': entry.host,
        'user': entry.user,
        'port': entry.port,
    }


def diff_managed_fields(previous: dict[str, Any] | None, desired: dict[str, Any]) -> list[str]:
    if previous is None:
        return list(MANAGED_FIELDS)
    changed: list[str] = []
    for key in MANAGED_FIELDS:
        before = previous.get(key, None)
        after = desired.get(key, None)
        if before != after:
            changed.append(key)
    return changed


def same_target(server: dict[str, Any], entry: ProfileEntry) -> bool:
    return (
        str(server.get('host') or '').strip() == entry.host and
        str(server.get('user') or '').strip() == entry.user and
        int(server.get('port') or 22) == entry.port
    )


def resolve_alias(
    entry: ProfileEntry,
    state: dict[str, Any],
    servers: dict[str, dict[str, Any]],
    match_index: dict[tuple[str, str, int], list[str]],
    alias_map: dict[str, dict[str, str]],
    used_aliases: set[str],
) -> tuple[str, str]:
    profiles = state.setdefault('profiles', {})
    record = profiles.get(entry.guid)
    if isinstance(record, dict):
        alias = str(record.get('alias') or '').strip()
        if alias:
            used_aliases.add(alias)
            return alias, 'state_guid'

    key = (entry.host, entry.user, entry.port)
    candidates = match_index.get(key) or []
    if len(candidates) == 1:
        alias = candidates[0]
        used_aliases.add(alias)
        return alias, 'adopted_match'

    generated = generated_alias(entry, alias_map)
    if generated in used_aliases:
        if generated in servers and same_target(servers[generated], entry):
            return generated, 'generated_match'
        generated = make_unique_alias(generated, used_aliases)
        return generated, 'generated_new'

    used_aliases.add(generated)
    return generated, 'generated_new'


def build_server(entry: ProfileEntry, existing: dict[str, Any] | None) -> dict[str, Any]:
    server = deepcopy(existing) if existing else {}
    server['host'] = entry.host
    server['user'] = entry.user
    server['password'] = entry.password
    server['port'] = entry.port
    label = entry.badge or f'{entry.user}@{entry.host}'
    server['description'] = f'Imported from iTerm2 profile: {label}'
    return server


def redact_entry(entry: ProfileEntry, alias: str | None = None) -> dict[str, Any]:
    payload = {
        'guid': entry.guid,
        'badge': entry.badge,
        'host': entry.host,
        'user': entry.user,
        'port': entry.port,
    }
    if alias:
        payload['alias'] = alias
    return payload


def cmd_scan(args: argparse.Namespace) -> int:
    entries = extract_entries(Path(args.iterm2_plist).expanduser())
    payload = {
        'count': len(entries),
        'entries': [redact_entry(entry) if not args.show_passwords else {**redact_entry(entry), 'password': entry.password} for entry in entries],
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print(f'found {len(entries)} importable iTerm2 SSH profiles')
    for entry in entries:
        print(f'- {entry.user}@{entry.host}:{entry.port} badge={entry.badge or "-"} guid={entry.guid or "-"}')
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    plist_path = Path(args.iterm2_plist).expanduser()
    target_path = Path(args.target).expanduser()
    state_path = Path(args.state).expanduser()
    alias_map = load_alias_map(Path(args.alias_map).expanduser() if args.alias_map else None)

    entries = extract_entries(plist_path)
    preamble, aliases_in_order, servers = load_target(target_path)
    original_servers = deepcopy(servers)
    state = load_json(state_path) or {'version': 1, 'profiles': {}}
    state.setdefault('version', 1)
    state.setdefault('profiles', {})

    match_index = build_match_index(servers)
    used_aliases = set(servers.keys())
    seen_guids: set[str] = set()

    added: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []
    adopted: list[dict[str, Any]] = []
    stale_tracked: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []

    for entry in entries:
        alias, source = resolve_alias(entry, state, servers, match_index, alias_map, used_aliases)
        previous = deepcopy(servers.get(alias)) if alias in servers else None
        desired = build_server(entry, servers.get(alias))
        servers[alias] = desired
        state['profiles'][entry.guid] = {
            'alias': alias,
            **managed_snapshot(entry),
            'last_seen_at': now_iso(),
        }
        if alias not in aliases_in_order:
            aliases_in_order.append(alias)

        summary = redact_entry(entry, alias)
        summary['alias_source'] = source
        changed_fields = diff_managed_fields(previous, desired)
        if changed_fields:
            summary['changed_fields'] = changed_fields
        if source == 'adopted_match':
            adopted.append(summary)

        if previous is None:
            added.append(summary)
        elif changed_fields:
            updated.append(summary)
        else:
            unchanged.append(summary)
        seen_guids.add(entry.guid)

    stale_guids = [guid for guid in list(state['profiles'].keys()) if guid not in seen_guids]
    for guid in stale_guids:
        record = state['profiles'].get(guid) or {}
        alias = str(record.get('alias') or '').strip()
        payload = {
            'guid': guid,
            'alias': alias,
            'host': record.get('host', ''),
            'user': record.get('user', ''),
            'port': int(record.get('port') or 22),
            'badge': record.get('badge', ''),
        }
        stale_tracked.append(payload)

    if args.prune_missing:
        for item in stale_tracked:
            alias = item['alias']
            guid = item['guid']
            if alias and alias in servers:
                removed.append(item)
                del servers[alias]
            if guid in state['profiles']:
                del state['profiles'][guid]

    changed = original_servers != servers or bool(removed)
    result = {
        'entries_seen': len(entries),
        'target': str(target_path),
        'state': str(state_path),
        'write': bool(args.write),
        'prune_missing': bool(args.prune_missing),
        'changed': changed,
        'added': added,
        'updated': updated,
        'unchanged': unchanged,
        'adopted_existing_alias': adopted,
        'stale_tracked': stale_tracked,
        'removed': removed,
    }

    if args.write:
        write_target(target_path, preamble, aliases_in_order, servers)
        dump_json(state_path, state)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    mode = 'write' if args.write else 'dry-run'
    print(
        f'{mode}: seen={len(entries)} added={len(added)} updated={len(updated)} '
        f'unchanged={len(unchanged)} stale={len(stale_tracked)} removed={len(removed)} adopted={len(adopted)}'
    )
    if updated:
        print('updated:')
        for item in updated[:20]:
            reason = ','.join(item.get('changed_fields', []))
            print(f'  - {item["alias"]} -> {item["user"]}@{item["host"]}:{item["port"]} fields={reason}')
    if stale_tracked:
        print('stale_tracked:')
        for item in stale_tracked[:20]:
            print(f'  - {item["alias"]} ({item["user"]}@{item["host"]}:{item["port"]})')
    if removed:
        print('removed:')
        for item in removed[:20]:
            print(f'  - {item["alias"]}')
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Sync password-based SSH servers from iTerm2 profiles into Codex ssh-config.toml')
    subparsers = parser.add_subparsers(dest='command', required=True)

    scan = subparsers.add_parser('scan', help='Scan iTerm2 profiles and list importable SSH entries')
    scan.add_argument('--iterm2-plist', default=str(DEFAULT_PLIST), help='Path to com.googlecode.iterm2.plist')
    scan.add_argument('--json', action='store_true', help='Output JSON')
    scan.add_argument('--show-passwords', action='store_true', help='Include passwords in scan output')
    scan.set_defaults(func=cmd_scan)

    sync = subparsers.add_parser('sync', help='Incrementally sync iTerm2 SSH entries into Codex ssh-config.toml')
    sync.add_argument('--iterm2-plist', default=str(DEFAULT_PLIST), help='Path to com.googlecode.iterm2.plist')
    sync.add_argument('--target', default=str(DEFAULT_TARGET), help='Target ssh-config.toml path')
    sync.add_argument('--state', default=str(DEFAULT_STATE), help='State file path for incremental sync')
    sync.add_argument('--alias-map', help='Optional JSON file with badge/host to alias mapping')
    sync.add_argument('--prune-missing', '--delete-missing', dest='prune_missing', action='store_true', help='Delete previously tracked aliases no longer present in iTerm2')
    sync.add_argument('--write', action='store_true', help='Persist changes to target and state files')
    sync.add_argument('--dry-run', action='store_true', help='Accepted for readability; no write happens unless --write is present')
    sync.add_argument('--json', action='store_true', help='Output JSON summary')
    sync.set_defaults(func=cmd_sync)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
