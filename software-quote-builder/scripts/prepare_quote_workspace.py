#!/usr/bin/env python3
"""Prepare a deterministic workspace for quote generation or historical revision."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Iterable

from quote_workspace_common import (
    WorkspaceLayout,
    build_layout,
    copy_tree_contents,
    default_root_dir,
    ensure_path,
    infer_project_name,
    output_file_name,
    parse_project_dir_name,
    valid_quote_json_path,
    write_json,
)


def unique_copy_name(dst_dir: Path, original_name: str) -> Path:
    candidate = dst_dir / original_name
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    index = 2
    while True:
        numbered = dst_dir / f"{stem}__{index:02d}{suffix}"
        if not numbered.exists():
            return numbered
        index += 1


def archive_sources(source_paths: Iterable[str], dst_dir: Path) -> list[dict[str, str]]:
    archived: list[dict[str, str]] = []
    for raw_path in source_paths:
        src = Path(raw_path).expanduser().resolve()
        if not src.exists():
            raise FileNotFoundError(f"source file not found: {src}")
        if not src.is_file():
            raise ValueError(f"source path must be a file: {src}")
        dst = unique_copy_name(dst_dir, src.name)
        shutil.copy2(src, dst)
        archived.append({"input": str(src), "archived": str(dst)})
    return archived


def resolve_project_name(explicit_name: str, base_project_dir: Path | None, base_quote_json: Path | None) -> str:
    name = str(explicit_name or '').strip()
    if name:
        return name
    if base_quote_json and base_quote_json.is_file():
        try:
            payload = json.loads(base_quote_json.read_text(encoding='utf-8'))
        except Exception:
            payload = None
        if isinstance(payload, dict) and str(payload.get('project_name') or '').strip():
            return str(payload['project_name']).strip()
    if base_project_dir and base_project_dir.exists():
        return infer_project_name(base_project_dir)
    return ''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Prepare a stable workspace for quote generation.')
    parser.add_argument('sources', nargs='*', help='Source files to archive into the project workspace')
    parser.add_argument('--project-name', default='', help='Project name used in the directory and final file name')
    parser.add_argument('--root-dir', default='', help='Override the default root directory')
    parser.add_argument('--base-project-dir', default='', help='Existing historical project directory to resume from')
    parser.add_argument('--base-quote-json', default='', help='Explicit historical quote-project.json to copy')
    parser.add_argument('--base-output-xlsx', default='', help='Explicit historical workbook path for xlsx recovery')
    parser.add_argument(
        '--timestamp',
        default='',
        help='Use a fixed timestamp like 20260323-101500; primarily useful for deterministic validation',
    )
    return parser.parse_args()


def write_resume_payload(layout: WorkspaceLayout, project_name: str, base_project_dir: Path | None, base_quote_json: Path | None, base_output_xlsx: Path | None) -> tuple[str, Path | None, Path | None]:
    valid_base_quote_json = valid_quote_json_path(base_quote_json)
    if valid_base_quote_json:
        shutil.copy2(valid_base_quote_json, layout.quote_json)
        return 'quote_json', valid_base_quote_json.resolve(), base_output_xlsx.resolve() if base_output_xlsx and base_output_xlsx.exists() else None

    discovered_quote_json = valid_quote_json_path(base_project_dir / 'quote-project.json') if base_project_dir else None
    if discovered_quote_json:
        shutil.copy2(discovered_quote_json, layout.quote_json)
        resolved_xlsx = base_output_xlsx.resolve() if base_output_xlsx and base_output_xlsx.exists() else None
        return 'quote_json', discovered_quote_json.resolve(), resolved_xlsx

    from quote_resume import build_source_regenerated_stub, discover_base_output_xlsx, recover_quote_payload_from_xlsx

    resolved_output = None
    if base_output_xlsx and base_output_xlsx.is_file():
        resolved_output = base_output_xlsx.resolve()
    elif base_project_dir:
        resolved_output = discover_base_output_xlsx(base_project_dir)

    if resolved_output and resolved_output.is_file():
        payload = recover_quote_payload_from_xlsx(resolved_output, fallback_project_dir=base_project_dir)
        payload.setdefault('project_name', project_name)
        write_json(layout.quote_json, payload)
        return 'xlsx_recovered', None, resolved_output.resolve()

    source_paths = sorted(layout.source_dir.iterdir()) if layout.source_dir.is_dir() else []
    payload = build_source_regenerated_stub(project_name, [path for path in source_paths if path.is_file()])
    write_json(layout.quote_json, payload)
    return 'source_regenerated', None, None


def main() -> int:
    args = parse_args()
    base_project_dir = ensure_path(args.base_project_dir)
    base_quote_json = ensure_path(args.base_quote_json)
    base_output_xlsx = ensure_path(args.base_output_xlsx)
    explicit_root = ensure_path(args.root_dir)
    project_name = resolve_project_name(str(args.project_name or '').strip(), base_project_dir, base_quote_json)
    chosen_root = explicit_root or (base_project_dir.parent if base_project_dir else default_root_dir())

    layout = build_layout(
        project_name=project_name,
        root_dir=chosen_root,
        stamp=str(args.timestamp or '').strip() or None,
    )

    archived_sources: list[dict[str, str]] = []
    if base_project_dir:
        archived_sources.extend(copy_tree_contents(base_project_dir / 'source', layout.source_dir))
    archived_sources.extend(archive_sources(args.sources, layout.source_dir))

    resume_mode = 'new'
    resolved_quote_json = None
    resolved_output_xlsx = None
    if base_project_dir or base_quote_json or base_output_xlsx:
        resume_mode, resolved_quote_json, resolved_output_xlsx = write_resume_payload(
            layout=layout,
            project_name=project_name,
            base_project_dir=base_project_dir,
            base_quote_json=base_quote_json,
            base_output_xlsx=base_output_xlsx,
        )

    aliases = []
    if project_name:
        aliases.extend([project_name, output_file_name(project_name).removesuffix('.xlsx')])
    if base_project_dir:
        aliases.append(parse_project_dir_name(base_project_dir.name)[0])

    workspace_manifest = {
        'project_name': project_name,
        'title': f'{project_name}功能清单报价表' if project_name else '功能清单报价表',
        'created_at': parse_project_dir_name(layout.project_dir.name)[1],
        'root_dir': str(layout.root_dir),
        'project_dir': str(layout.project_dir),
        'source_dir': str(layout.source_dir),
        'normalized_dir': str(layout.normalized_dir),
        'output_dir': str(layout.output_dir),
        'output_xlsx': str(layout.output_xlsx),
        'quote_json': str(layout.quote_json),
        'archived_sources': archived_sources,
        'base_project_dir': str(base_project_dir) if base_project_dir else '',
        'base_quote_json': str(resolved_quote_json) if resolved_quote_json else '',
        'base_output_xlsx': str(resolved_output_xlsx) if resolved_output_xlsx else '',
        'resume_mode': resume_mode,
        'aliases': [alias for alias in aliases if alias],
    }
    write_json(layout.workspace_manifest, workspace_manifest)

    manifest = {
        'root_dir': str(layout.root_dir),
        'project_dir': str(layout.project_dir),
        'source_dir': str(layout.source_dir),
        'normalized_dir': str(layout.normalized_dir),
        'output_dir': str(layout.output_dir),
        'output_xlsx': str(layout.output_xlsx),
        'quote_json': str(layout.quote_json),
        'workspace_manifest': str(layout.workspace_manifest),
        'archived_sources': archived_sources,
        'base_project_dir': str(base_project_dir) if base_project_dir else '',
        'base_quote_json': str(resolved_quote_json) if resolved_quote_json else '',
        'base_output_xlsx': str(resolved_output_xlsx) if resolved_output_xlsx else '',
        'resume_mode': resume_mode,
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
