#!/usr/bin/env python3
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_alias_maps(roster):
    canonical_map = {}
    alias_map = {}
    for item in roster:
        canonical_map[item['canonical']] = item
        for alias in item['aliases']:
            alias_map[alias] = item['canonical']
    return canonical_map, alias_map


def load_matches(args):
    if args.matches_file:
        return json.loads(Path(args.matches_file).read_text(encoding='utf-8'))
    if args.matches_json:
        return json.loads(args.matches_json)
    raise SystemExit('Provide --matches-file or --matches-json')


def resolve_canonical(match, canonical_map, alias_map):
    for key in ('canonical', 'alias', 'display_name'):
        value = match.get(key)
        if not value:
            continue
        if value in canonical_map:
            return value
        if value in alias_map:
            return alias_map[value]
    raise ValueError(f'Cannot resolve canonical roster entry for match: {match}')


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


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def resolve_fingerprint(payload):
    image_path = payload.get('image_path')
    if image_path:
        path = Path(image_path).expanduser().resolve()
        if path.exists() and path.is_file():
            return str(path), sha256_file(path)
    fingerprint = payload.get('fingerprint')
    return image_path or '', fingerprint or ''


def main():
    parser = argparse.ArgumentParser(description='Append or replace one image result in XHS audit state.')
    parser.add_argument('--state-file', required=True, help='State JSON file.')
    parser.add_argument('--matches-file', help='JSON payload file for one judged image.')
    parser.add_argument('--matches-json', help='Inline JSON payload for one judged image.')
    parser.add_argument('--replace-image', action='store_true', help='Replace an existing image entry if present.')
    args = parser.parse_args()

    state_path = Path(args.state_file)
    state = json.loads(state_path.read_text(encoding='utf-8'))
    payload = load_matches(args)

    roster = state['roster']
    canonical_map, alias_map = build_alias_maps(roster)

    image_name = payload.get('image')
    if not image_name:
        raise SystemExit('Payload must include "image"')

    image_path, fingerprint = resolve_fingerprint(payload)

    resolved_matches = []
    for match in payload.get('matches', []):
        liked = bool(match.get('liked', False))
        counted = bool(match.get('counted', liked))
        canonical = resolve_canonical(match, canonical_map, alias_map)
        resolved_matches.append(
            {
                'canonical': canonical,
                'display_name': match.get('display_name') or match.get('alias') or canonical,
                'liked': liked,
                'counted': counted,
                'notes': match.get('notes', ''),
            }
        )

    entry = {
        'image': image_name,
        'image_path': image_path,
        'fingerprint': fingerprint,
        'notes': payload.get('notes', ''),
        'matches': resolved_matches,
        'updated_at': utc_now_iso(),
    }

    existing_index = None
    duplicate_fingerprint_image = None
    for idx, image in enumerate(state['images']):
        if image.get('image') == image_name:
            existing_index = idx
        if fingerprint and image.get('fingerprint') == fingerprint and image.get('image') != image_name:
            duplicate_fingerprint_image = image.get('image')

    if duplicate_fingerprint_image and not args.replace_image:
        raise SystemExit(
            f'Duplicate image fingerprint detected: {image_name} matches existing image {duplicate_fingerprint_image}. '
            'Use a different image or intentionally replace the existing one.'
        )

    if existing_index is not None:
        if not args.replace_image:
            raise SystemExit(f'Image already exists: {image_name}. Use --replace-image to overwrite it.')
        state['images'][existing_index] = entry
    else:
        state['images'].append(entry)

    state['updated_at'] = utc_now_iso()
    recalc_totals(state)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Updated {state_path} with {image_name}')


if __name__ == '__main__':
    main()
