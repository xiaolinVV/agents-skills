#!/usr/bin/env python3
"""Normalize legacy Office and OpenDocument files for downstream quote extraction.

This script converts old binary Office files (.doc/.ppt/.xls) and OpenDocument
files (.odt/.odp/.ods) into modern OOXML equivalents using LibreOffice.
It also classifies already-supported files and optionally copies them into the
normalization workspace so later steps can process one directory consistently.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

SUPPORTED_NOOP = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".docm": "docx",
    ".pptx": "pptx",
    ".pptm": "pptx",
    ".xlsx": "xlsx",
    ".xlsm": "xlsx",
    ".csv": "table",
    ".tsv": "table",
    ".txt": "text",
    ".md": "text",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".bmp": "image",
    ".gif": "image",
    ".webp": "image",
    ".tif": "image",
    ".tiff": "image",
}

CONVERT_MAP = {
    ".doc": ("docx", "docx"),
    ".ppt": ("pptx", "pptx"),
    ".xls": ("xlsx", "xlsx"),
    ".odt": ("docx", "docx"),
    ".odp": ("pptx", "pptx"),
    ".ods": ("xlsx", "xlsx"),
}


def unique_path(out_dir: Path, stem: str, suffix: str) -> Path:
    candidate = out_dir / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate
    idx = 2
    while True:
        candidate = out_dir / f"{stem}-{idx}{suffix}"
        if not candidate.exists():
            return candidate
        idx += 1


def find_soffice() -> str:
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    raise FileNotFoundError("LibreOffice/soffice not found in PATH")


def convert_with_soffice(src: Path, out_dir: Path, convert_to: str) -> Path:
    soffice = find_soffice()
    before = set(out_dir.iterdir()) if out_dir.exists() else set()
    cmd = [
        soffice,
        "--headless",
        "--convert-to",
        convert_to,
        "--outdir",
        str(out_dir),
        str(src),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip() or "conversion failed"
        raise RuntimeError(detail)

    expected = out_dir / f"{src.stem}.{convert_to}"
    if expected.exists():
        return expected

    after = set(out_dir.iterdir())
    created = [p for p in after - before if p.is_file() and p.suffix.lower() == f".{convert_to}" and p.stem == src.stem]
    if len(created) == 1:
        return created[0]

    matches = sorted(p for p in out_dir.glob(f"{src.stem}*.{convert_to}") if p.is_file())
    if matches:
        return matches[-1]

    detail = (proc.stderr or proc.stdout).strip() or "converter did not produce output"
    raise RuntimeError(detail)


def classify(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in SUPPORTED_NOOP:
        return SUPPORTED_NOOP[ext]
    if ext in CONVERT_MAP:
        return CONVERT_MAP[ext][1]
    return "unsupported"


def process_file(src: Path, out_dir: Path, copy_supported: bool) -> Dict[str, str]:
    src = src.resolve()
    ext = src.suffix.lower()
    record: Dict[str, str] = {
        "input": str(src),
        "input_ext": ext,
        "normalized_type": classify(src),
    }

    if not src.exists():
        record.update(status="error", error="file not found")
        return record

    if ext in SUPPORTED_NOOP:
        if copy_supported:
            dst = unique_path(out_dir, src.stem, src.suffix)
            shutil.copy2(src, dst)
            record.update(status="copied", action="copy", output=str(dst))
        else:
            record.update(status="kept", action="keep", output=str(src))
        return record

    if ext in CONVERT_MAP:
        convert_to, normalized_type = CONVERT_MAP[ext]
        try:
            converted = convert_with_soffice(src, out_dir, convert_to)
        except Exception as exc:  # noqa: BLE001
            record.update(status="error", action="convert", normalized_type=normalized_type, error=str(exc))
            return record

        record.update(status="converted", action="convert", output=str(converted), normalized_type=normalized_type)
        return record

    record.update(status="error", error="unsupported file type")
    return record


def build_manifest(records: List[Dict[str, str]], out_dir: Path) -> Dict[str, object]:
    errors = [r for r in records if r.get("status") == "error"]
    return {
        "output_dir": str(out_dir.resolve()),
        "ok": not errors,
        "items": records,
        "error_count": len(errors),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize Office inputs for quotation workflows.")
    parser.add_argument("files", nargs="+", help="Input files to normalize")
    parser.add_argument("--output-dir", required=True, help="Directory to write normalized files into")
    parser.add_argument(
        "--no-copy-supported",
        action="store_true",
        help="Keep already-supported files in place instead of copying them into the output directory",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    records = [process_file(Path(raw), out_dir, copy_supported=not args.no_copy_supported) for raw in args.files]
    manifest = build_manifest(records, out_dir)
    json.dump(manifest, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
