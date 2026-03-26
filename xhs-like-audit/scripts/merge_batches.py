#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_state(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def roster_signature(state):
    meta = state.get('roster_meta', {})
    return {
        'roster_hash': meta.get('roster_hash', ''),
        'roster_group_count': meta.get('roster_group_count', len(state.get('roster', []))),
        'canonical_order': [item['canonical'] for item in state.get('roster', [])],
    }


def recalc_totals(state):
    total = 0
    canonical_map = {item['canonical']: item for item in state['roster']}
    for item in state['roster']:
        item['count'] = 0
    for image in state['images']:
        for match in image['matches']:
            if match.get('counted') and match.get('liked'):
                canonical = match['canonical']
                canonical_map[canonical]['count'] += 1
                total += 1
    state['totals']['valid_groups'] = total


def main():
    parser = argparse.ArgumentParser(description='Merge multiple XHS audit batch state files into one combined batch.')
    parser.add_argument('--state-files', nargs='+', required=True, help='Input state JSON files to merge.')
    parser.add_argument('--output-file', required=True, help='Merged state JSON output path.')
    parser.add_argument('--session-name', default='xhs-like-audit-merged', help='Merged session name.')
    args = parser.parse_args()

    states = [load_state(path) for path in args.state_files]
    base = states[0]
    base_signature = roster_signature(base)

    merged = {
        'version': 2,
        'session_name': args.session_name,
        'created_at': utc_now_iso(),
        'updated_at': utc_now_iso(),
        'rules': base.get('rules', {}),
        'roster_meta': dict(base.get('roster_meta', {})),
        'roster': [
            {
                'index': item['index'],
                'canonical': item['canonical'],
                'aliases': list(item['aliases']),
                'count': 0,
            }
            for item in base['roster']
        ],
        'images': [],
        'totals': {'valid_groups': 0},
        'sources': [],
    }

    seen_images = set()
    seen_fingerprints = set()

    for path, state in zip(args.state_files, states):
        sig = roster_signature(state)
        if sig['roster_hash'] != base_signature['roster_hash'] or sig['canonical_order'] != base_signature['canonical_order']:
            raise SystemExit(
                'Roster mismatch: '\
                f'{path}\n'\
                f'- expected roster_hash={base_signature["roster_hash"]}, group_count={base_signature["roster_group_count"]}\n'\
                f'- got roster_hash={sig["roster_hash"]}, group_count={sig["roster_group_count"]}\n'\
                'Different roster versions should not be merged directly.'
            )

        session_name = state.get('session_name') or Path(path).stem
        merged['sources'].append({'state_file': str(Path(path).resolve()), 'session_name': session_name})

        for image in state.get('images', []):
            merged_image_name = f'{session_name}/{image.get("image", "unknown")}'
            if merged_image_name in seen_images:
                raise SystemExit(f'Duplicate merged image key: {merged_image_name}')
            seen_images.add(merged_image_name)

            fingerprint = image.get('fingerprint', '')
            if fingerprint:
                if fingerprint in seen_fingerprints:
                    raise SystemExit(f'Duplicate image fingerprint across batches: {merged_image_name}')
                seen_fingerprints.add(fingerprint)

            merged['images'].append(
                {
                    'image': merged_image_name,
                    'source_session': session_name,
                    'source_image': image.get('image', ''),
                    'image_path': image.get('image_path', ''),
                    'fingerprint': fingerprint,
                    'notes': image.get('notes', ''),
                    'matches': image.get('matches', []),
                    'updated_at': image.get('updated_at', utc_now_iso()),
                }
            )

    recalc_totals(merged)

    output = Path(args.output_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Merged into {output}')


if __name__ == '__main__':
    main()
