#!/usr/bin/env python3
"""Find historical quote workspaces by fuzzy project name."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from quote_workspace_common import default_root_dir, default_root_dirs, history_candidates_from_roots


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Find historical quote workspaces for revision.')
    parser.add_argument('query', help='Quote or project name query to match against archived workspaces')
    parser.add_argument('--root-dir', default='', help='Override the default quote workspace root directory')
    parser.add_argument('--limit', type=int, default=5, help='Maximum number of candidates to return')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root_dirs = [(Path(args.root_dir).expanduser() if args.root_dir else default_root_dir()).resolve()] if args.root_dir else default_root_dirs()
    candidates = history_candidates_from_roots(root_dirs, str(args.query or ''), limit=max(args.limit, 1))
    manifest = {
        'query': str(args.query or ''),
        'root_dir': str(root_dirs[0]),
        'root_dirs': [str(path) for path in root_dirs],
        'root_exists': any(path.exists() and path.is_dir() for path in root_dirs),
        'candidates': [candidate.to_dict() for candidate in candidates],
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
