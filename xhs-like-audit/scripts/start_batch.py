#!/usr/bin/env python3
import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from pathlib import PurePosixPath
from zipfile import ZipFile

from lint_roster import lint_roster, render_lint_report_text
from parse_roster import parse_roster_text

IMAGE_SUFFIXES = {
    '.jpg',
    '.jpeg',
    '.png',
    '.webp',
    '.bmp',
    '.gif',
    '.heic',
    '.heif',
}


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_batch_name():
    return datetime.now().strftime('xhs-batch-%Y%m%d-%H%M%S')


def build_roster_meta(roster_text: str, roster, roster_file: str = ''):
    roster_hash = hashlib.sha256(roster_text.encode('utf-8')).hexdigest()
    return {
        'source_file': roster_file,
        'roster_hash': roster_hash,
        'roster_group_count': len(roster),
        'roster_snapshot_name': Path(roster_file).name if roster_file else 'inline-roster',
        'roster_snapshot_text': roster_text,
    }


def normalize_zip_member_path(name: str) -> str | None:
    posix_path = PurePosixPath(name)
    if not name or name.endswith('/'):
        return None
    if posix_path.is_absolute():
        raise ValueError(f'Unsafe zip member path: {name}')
    if any(part in ('..', '') for part in posix_path.parts):
        raise ValueError(f'Unsafe zip member path: {name}')
    if posix_path.parts and posix_path.parts[0] == '__MACOSX':
        return None
    if posix_path.suffix.lower() not in IMAGE_SUFFIXES:
        return None
    return posix_path.as_posix()


def extract_zip_images(zip_file: Path, images_dir: Path):
    manifest = []
    seen_targets = set()

    with ZipFile(zip_file) as zf:
        for info in sorted(zf.infolist(), key=lambda item: item.filename):
            relative_path = normalize_zip_member_path(info.filename)
            if relative_path is None:
                continue

            if relative_path in seen_targets:
                raise ValueError(f'Duplicate image path inside zip: {relative_path}')
            seen_targets.add(relative_path)

            target = images_dir / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open('wb') as dst:
                shutil.copyfileobj(src, dst)

            manifest.append(
                {
                    'index': len(manifest) + 1,
                    'relative_path': relative_path,
                    'absolute_path': str(target.resolve()),
                }
            )

    if not manifest:
        raise ValueError(f'No supported image files found in zip: {zip_file}')

    return manifest


def build_next_steps(
    *,
    batch_dir: Path,
    roster_copy: Path,
    state_file: Path,
    roster_meta: dict,
    roster_lint_file: Path | None,
    roster_lint_report: dict,
    manifest_file: Path | None,
    zip_src: Path | None,
    manifest: list[dict],
):
    files_lines = [
        f'- roster: {roster_copy}',
        f'- state: {state_file}',
        '- images/: place original screenshots here' if not zip_src else '- images/: extracted screenshots from zip live here',
        '- judged/: save one JSON payload per image here',
    ]
    if manifest_file:
        files_lines.append(f'- manifest: {manifest_file}')
    if roster_lint_file:
        files_lines.append(f'- roster-lint: {roster_lint_file}')

    sections = [
        f'Batch created: {batch_dir}',
        '',
        'Files:',
        *files_lines,
        '',
        'Roster version:',
        f"- snapshot: {roster_meta['roster_snapshot_name']}",
        f"- group_count: {roster_meta['roster_group_count']}",
        f"- roster_hash: {roster_meta['roster_hash']}",
    ]

    warning_count = roster_lint_report['summary']['warning_count']
    if warning_count:
        sections.extend(
            [
                '',
                'Roster lint:',
                f'- roster has warning(s): {warning_count}',
                '- warning policy: warning only, batch creation continues',
                '- hard merge rule: only quoted multi-line blocks count as one blogger group',
                '- fuzzy rule: match names only after an active heart, and count only when the visible name maps uniquely',
            ]
        )

    if zip_src:
        sections.extend(
            [
                '',
                'Zip import:',
                f'- source_zip: {zip_src}',
                f'- extracted_images: {len(manifest)}',
            ]
        )
        if len(manifest) >= 20:
            sections.extend(
                [
                    '- batch_size: large',
                    '- recommendation: use images-manifest.json to split into 5-10 image shards, judge with subagents, then apply update_counts.py serially',
                ]
            )

    sections.extend(
        [
            '',
            'Next commands:',
            '1) Judge one image visually, then save a payload json into judged/',
            '   Tip: include "image_path" in the payload when possible so duplicate detection can fingerprint the file.',
            f"2) Update counts:\n   python3 scripts/update_counts.py --state-file '{state_file}' --matches-file '{batch_dir / 'judged' / 'image-001.json'}'",
            f"3) Render ordered report with zeros:\n   python3 scripts/render_report.py --state-file '{state_file}' --preset roster",
            f"4) Render summary:\n   python3 scripts/render_report.py --state-file '{state_file}' --preset summary",
            '',
        ]
    )

    return '\n'.join(sections)


def main():
    parser = argparse.ArgumentParser(description='Create a ready-to-use Xiaohongshu like audit batch workspace.')
    parser.add_argument('--roster-file', required=True, help='Raw roster text file.')
    parser.add_argument('--zip-file', help='Optional zip archive of screenshots to extract into images/.')
    parser.add_argument('--batch-root', default='.', help='Parent directory for the new batch folder.')
    parser.add_argument('--batch-name', default=None, help='Optional batch folder name.')
    args = parser.parse_args()

    batch_root = Path(args.batch_root).expanduser().resolve()
    batch_name = args.batch_name or default_batch_name()
    batch_dir = batch_root / batch_name
    images_dir = batch_dir / 'images'
    judged_dir = batch_dir / 'judged'

    roster_src = Path(args.roster_file).expanduser().resolve()
    roster_text = roster_src.read_text(encoding='utf-8')
    roster = parse_roster_text(roster_text)
    roster_lint_report = lint_roster(roster)
    roster_meta = build_roster_meta(roster_text, roster, str(roster_src))

    zip_src = Path(args.zip_file).expanduser().resolve() if args.zip_file else None
    manifest = []
    manifest_file = None
    roster_lint_file = None

    try:
        batch_dir.mkdir(parents=True, exist_ok=False)

        roster_copy = batch_dir / 'roster.txt'
        shutil.copy2(roster_src, roster_copy)

        images_dir.mkdir()
        judged_dir.mkdir()

        if roster_lint_report['summary']['warning_count']:
            roster_lint_file = batch_dir / 'roster-lint.txt'
            roster_lint_file.write_text(render_lint_report_text(roster_lint_report), encoding='utf-8')

        if zip_src:
            manifest = extract_zip_images(zip_src, images_dir)
            manifest_file = batch_dir / 'images-manifest.json'
            manifest_payload = {
                'source_zip': str(zip_src),
                'image_count': len(manifest),
                'images': manifest,
            }
            manifest_file.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

        state = {
            'version': 2,
            'session_name': batch_name,
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

        state_file = batch_dir / 'state.json'
        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

        next_steps = build_next_steps(
            batch_dir=batch_dir,
            roster_copy=roster_copy,
            state_file=state_file,
            roster_meta=roster_meta,
            roster_lint_file=roster_lint_file,
            roster_lint_report=roster_lint_report,
            manifest_file=manifest_file,
            zip_src=zip_src,
            manifest=manifest,
        )
        (batch_dir / 'next-steps.txt').write_text(next_steps, encoding='utf-8')

        print(batch_dir)
        if roster_lint_report['summary']['warning_count']:
            print(
                f"Roster lint: {roster_lint_report['summary']['warning_count']} warning(s). "
                f"See {roster_lint_file}",
                file=sys.stderr,
            )
    except Exception:
        shutil.rmtree(batch_dir, ignore_errors=True)
        raise


if __name__ == '__main__':
    main()
