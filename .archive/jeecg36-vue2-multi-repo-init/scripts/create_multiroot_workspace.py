#!/usr/bin/env python3
"""Create a VS Code multi-root workspace file for jeecg multi-repo projects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_FOLDERS = [
    {"name": "jeecg-boot", "path": "jeecg-boot"},
    {"name": "ant-design-vue-jeecg", "path": "ant-design-vue-jeecg"},
    {"name": "docs", "path": "docs"},
    {"name": "_bmad", "path": "_bmad"},
    {"name": "_bmad-output", "path": "_bmad-output"},
]

OPTIONAL_FOLDER_MAP = {
    "uniapp": {"name": "jeecg-uniapp", "path": "jeecg-uniapp"},
    "openspec": {"name": "openspec", "path": "openspec"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace-root",
        required=True,
        help="Top-level workspace directory that contains all child repositories",
    )
    parser.add_argument(
        "--workspace-name",
        help="Workspace file basename. Defaults to workspace root folder name.",
    )
    parser.add_argument(
        "--output",
        help="Explicit output path for .code-workspace file.",
    )
    parser.add_argument(
        "--include-uniapp",
        action="store_true",
        help="Include jeecg-uniapp in workspace file",
    )
    parser.add_argument(
        "--include-openspec",
        action="store_true",
        help="Include openspec in workspace file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing workspace file",
    )
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation")
    return parser.parse_args()


def resolve_output_path(root: Path, args: argparse.Namespace) -> Path:
    if args.output:
        return Path(args.output).expanduser().resolve()
    name = args.workspace_name or root.name
    if not name.endswith(".code-workspace"):
        name = f"{name}.code-workspace"
    return (root / name).resolve()


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root).expanduser().resolve()
    output_path = resolve_output_path(root, args)

    folders = list(REQUIRED_FOLDERS)
    if args.include_uniapp:
        folders.append(OPTIONAL_FOLDER_MAP["uniapp"])
    if args.include_openspec:
        folders.append(OPTIONAL_FOLDER_MAP["openspec"])

    workspace = {
        "folders": folders,
        "settings": {
            "workbench.editor.wrapTabs": True,
        },
    }

    if output_path.exists() and not args.overwrite:
        raise FileExistsError(
            f"Workspace file already exists: {output_path}. Use --overwrite to replace it."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(workspace, ensure_ascii=False, indent=max(0, args.indent)) + "\n",
        encoding="utf-8",
    )

    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
