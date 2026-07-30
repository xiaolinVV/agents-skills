#!/usr/bin/env python3
import argparse
import hashlib
import os
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


DOCS_SUBDIR = Path('docs') / 'jeecg-boot文档中心' / 'Online 表单 VUE2 版' / '原理与链路分析'


def find_docs_root(start: Path) -> Optional[Path]:
    cur = start.resolve()
    while True:
        candidate = cur / DOCS_SUBDIR
        if candidate.exists():
            return candidate
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def file_hash(path: Path) -> str:
    h = hashlib.sha1()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def resolve_file_list(dest_dir: Path, src_dir: Path, explicit: Optional[List[str]]) -> List[str]:
    if explicit:
        return explicit
    names = []
    for p in sorted(dest_dir.iterdir()):
        if not p.is_file():
            continue
        if (src_dir / p.name).is_file():
            names.append(p.name)
    return names


def sync_files(src_dir: Path, dest_dir: Path, names: Iterable[str], apply: bool) -> Tuple[int, int, int, int]:
    same = updated = added = missing = 0
    for name in names:
        src = src_dir / name
        dest = dest_dir / name
        if not src.is_file():
            print(f"[missing] {name} (source not found)")
            missing += 1
            continue
        if dest.is_file():
            if file_hash(src) == file_hash(dest):
                print(f"[same] {name}")
                same += 1
            else:
                if apply:
                    dest.write_bytes(src.read_bytes())
                    print(f"[updated] {name}")
                else:
                    print(f"[would-update] {name}")
                updated += 1
        else:
            if apply:
                dest.write_bytes(src.read_bytes())
                print(f"[added] {name}")
            else:
                print(f"[would-add] {name}")
            added += 1
    return same, updated, added, missing


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Sync jeecg docs sources into skill references (dry-run by default).'
    )
    parser.add_argument('--src', help='Docs source directory (defaults to repo docs path)')
    parser.add_argument('--dest', help='Skill references directory (defaults to this skill)')
    parser.add_argument('--file', action='append', dest='files',
                        help='Specific file name to sync (repeatable). If omitted, sync files present in references.')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default is dry-run)')
    args = parser.parse_args()

    dest_dir = Path(args.dest).expanduser().resolve() if args.dest else (Path(__file__).resolve().parent.parent / 'references')
    if not dest_dir.exists():
        print(f"[error] references dir not found: {dest_dir}")
        raise SystemExit(2)

    if args.src:
        src_dir = Path(args.src).expanduser().resolve()
    else:
        src_dir = find_docs_root(Path(os.getcwd()))
    if not src_dir or not src_dir.exists():
        print('[error] docs source not found. Provide --src explicitly.')
        raise SystemExit(2)

    names = resolve_file_list(dest_dir, src_dir, args.files)
    if not names:
        print('[error] no files to sync. Use --file to specify files explicitly.')
        raise SystemExit(2)

    same, updated, added, missing = sync_files(src_dir, dest_dir, names, args.apply)
    mode = 'apply' if args.apply else 'dry-run'
    print(f"[summary] mode={mode} same={same} updated={updated} added={added} missing={missing}")


if __name__ == '__main__':
    main()
