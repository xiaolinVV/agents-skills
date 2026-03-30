#!/usr/bin/env python3
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from parse_roster import parse_roster_text


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_roster_meta(roster_text: str, roster, roster_file: str = ''):
    roster_hash = hashlib.sha256(roster_text.encode('utf-8')).hexdigest()
    return {
        'source_file': roster_file,
        'roster_hash': roster_hash,
        'roster_group_count': len(roster),
        'roster_snapshot_name': Path(roster_file).name if roster_file else 'inline-roster',
        'roster_snapshot_text': roster_text,
    }


def main():
    parser = argparse.ArgumentParser(description='Initialize a fresh XHS like audit batch state file.')
    parser.add_argument('--roster-file', required=True, help='Raw roster text file.')
    parser.add_argument('--state-file', required=True, help='Target state JSON file.')
    parser.add_argument('--session-name', default='xhs-like-audit', help='Logical batch/session name.')
    args = parser.parse_args()

    roster_path = Path(args.roster_file).expanduser().resolve()
    roster_text = roster_path.read_text(encoding='utf-8')
    roster = parse_roster_text(roster_text)
    roster_meta = build_roster_meta(roster_text, roster, str(roster_path))

    state = {
        'version': 2,
        'session_name': args.session_name,
        'created_at': utc_now_iso(),
        'updated_at': utc_now_iso(),
        'rules': {
            'like_first': True,
            'quoted_block_is_alias_group': True,
            'fuzzy_match_allowed': True,
            'prefer_undercounting': True,
        },
        'roster_meta': roster_meta,
        'roster': roster,
        'images': [],
        'totals': {
            'valid_groups': 0,
        },
    }

    target = Path(args.state_file)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Initialized {target}')


if __name__ == '__main__':
    main()
