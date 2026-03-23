#!/usr/bin/env python3
"""Prepare a deterministic workspace for quote generation.

Creates one project directory under a stable root, copies source files into
`source/`, and returns a JSON manifest that later steps can consume.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class WorkspaceLayout:
    root_dir: Path
    project_dir: Path
    source_dir: Path
    normalized_dir: Path
    output_dir: Path
    output_xlsx: Path


def sanitize_component(value: str, fallback: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", "-", (value or "").strip())
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-._ ")
    return text or fallback


def default_root_dir(home: Path | None = None) -> Path:
    home = home or Path.home()
    chinese_parent = home / "文档"
    english_parent = home / "Documents"
    if chinese_parent.is_dir():
        return chinese_parent / "功能清单报价"
    if english_parent.is_dir():
        return english_parent / "功能清单报价"
    return home / "功能清单报价"


def project_stem(project_name: str) -> str:
    return sanitize_component(project_name, "quote") if project_name else "quote"


def output_file_name(project_name: str) -> str:
    safe_name = sanitize_component(project_name, "") if project_name else ""
    return f"{safe_name}功能清单报价表.xlsx" if safe_name else "功能清单报价表.xlsx"


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


def build_layout(project_name: str, root_dir: Path | None = None, stamp: str | None = None) -> WorkspaceLayout:
    root = (root_dir or default_root_dir()).expanduser().resolve()
    timestamp = stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    project_dir = root / f"{project_stem(project_name)}-{timestamp}"
    source_dir = project_dir / "source"
    normalized_dir = project_dir / "normalized"
    output_dir = project_dir / "output"
    output_xlsx = output_dir / output_file_name(project_name)
    for path in (source_dir, normalized_dir, output_dir):
        path.mkdir(parents=True, exist_ok=True)
    return WorkspaceLayout(
        root_dir=root,
        project_dir=project_dir,
        source_dir=source_dir,
        normalized_dir=normalized_dir,
        output_dir=output_dir,
        output_xlsx=output_xlsx,
    )


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a stable workspace for quote generation.")
    parser.add_argument("sources", nargs="*", help="Source files to archive into the project workspace")
    parser.add_argument("--project-name", default="", help="Project name used in the directory and final file name")
    parser.add_argument("--root-dir", default="", help="Override the default root directory")
    parser.add_argument(
        "--timestamp",
        default="",
        help="Use a fixed timestamp like 20260323-101500; primarily useful for deterministic validation",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    layout = build_layout(
        project_name=str(args.project_name or "").strip(),
        root_dir=Path(args.root_dir).expanduser() if args.root_dir else None,
        stamp=str(args.timestamp or "").strip() or None,
    )
    archived_sources = archive_sources(args.sources, layout.source_dir)
    manifest = {
        "root_dir": str(layout.root_dir),
        "project_dir": str(layout.project_dir),
        "source_dir": str(layout.source_dir),
        "normalized_dir": str(layout.normalized_dir),
        "output_dir": str(layout.output_dir),
        "output_xlsx": str(layout.output_xlsx),
        "archived_sources": archived_sources,
    }
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
