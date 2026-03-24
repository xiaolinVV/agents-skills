#!/usr/bin/env python3
"""Shared workspace helpers for software quote projects."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

ROOT_PARENT_CANDIDATES = ("文稿", "文档", "Documents")
QUOTE_ROOT_DIRNAME = "功能清单报价"
TIMESTAMP_RE = re.compile(r"^(?P<stem>.+)-(?P<stamp>\d{8}-\d{6})$")
GENERIC_SOURCE_ALIASES = {"需求", "需求说明", "项目需求", "方案", "说明", "报价", "报价表", "报价清单"}
NOISE_PATTERNS = [
    "功能清单报价表",
    "功能清单",
    "报价清单",
    "报价表",
    "报价单",
    "报价",
    "清单",
]


@dataclass(frozen=True)
class WorkspaceLayout:
    root_dir: Path
    project_dir: Path
    source_dir: Path
    normalized_dir: Path
    output_dir: Path
    output_xlsx: Path
    quote_json: Path
    workspace_manifest: Path


@dataclass(frozen=True)
class HistoryCandidate:
    project_dir: Path
    project_name: str
    timestamp: str
    output_xlsx: Path | None
    quote_json: Path | None
    workspace_manifest: Path | None
    resume_capability: str
    aliases: tuple[str, ...]
    match_score: float
    match_basis: str

    def to_dict(self) -> dict[str, object]:
        return {
            "project_dir": str(self.project_dir),
            "project_name": self.project_name,
            "timestamp": self.timestamp,
            "output_xlsx": str(self.output_xlsx) if self.output_xlsx else "",
            "quote_json": str(self.quote_json) if self.quote_json else "",
            "workspace_manifest": str(self.workspace_manifest) if self.workspace_manifest else "",
            "resume_capability": self.resume_capability,
            "aliases": list(self.aliases),
            "match_score": round(self.match_score, 6),
            "match_basis": self.match_basis,
        }


def sanitize_component(value: str, fallback: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", "-", (value or "").strip())
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-._ ")
    return text or fallback


def default_root_dir(home: Path | None = None) -> Path:
    return default_root_dirs(home)[0]


def default_root_dirs(home: Path | None = None) -> list[Path]:
    home = home or Path.home()
    roots: list[Path] = []
    seen: set[Path] = set()
    for parent_name in ROOT_PARENT_CANDIDATES:
        parent = home / parent_name
        if not parent.is_dir():
            continue
        root = (parent / QUOTE_ROOT_DIRNAME).resolve()
        if root not in seen:
            roots.append(root)
            seen.add(root)
    fallback = (home / QUOTE_ROOT_DIRNAME).resolve()
    if fallback not in seen:
        roots.append(fallback)
    return roots


def project_stem(project_name: str) -> str:
    return sanitize_component(project_name, "quote") if project_name else "quote"


def output_file_name(project_name: str) -> str:
    safe_name = sanitize_component(project_name, "") if project_name else ""
    return f"{safe_name}功能清单报价表.xlsx" if safe_name else "功能清单报价表.xlsx"


def build_layout(project_name: str, root_dir: Path | None = None, stamp: str | None = None) -> WorkspaceLayout:
    root = (root_dir or default_root_dir()).expanduser().resolve()
    timestamp = stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    project_dir = root / f"{project_stem(project_name)}-{timestamp}"
    source_dir = project_dir / "source"
    normalized_dir = project_dir / "normalized"
    output_dir = project_dir / "output"
    output_xlsx = output_dir / output_file_name(project_name)
    quote_json = project_dir / "quote-project.json"
    workspace_manifest = project_dir / "workspace-manifest.json"
    for path in (source_dir, normalized_dir, output_dir):
        path.mkdir(parents=True, exist_ok=True)
    return WorkspaceLayout(
        root_dir=root,
        project_dir=project_dir,
        source_dir=source_dir,
        normalized_dir=normalized_dir,
        output_dir=output_dir,
        output_xlsx=output_xlsx,
        quote_json=quote_json,
        workspace_manifest=workspace_manifest,
    )


def parse_project_dir_name(name: str) -> tuple[str, str]:
    match = TIMESTAMP_RE.match(name)
    if not match:
        return name, ""
    return match.group("stem"), match.group("stamp")


def normalize_match_text(value: str) -> str:
    text = (value or "").strip().lower()
    for pattern in NOISE_PATTERNS:
        text = text.replace(pattern.lower(), "")
    text = TIMESTAMP_RE.sub(lambda m: m.group("stem"), text)
    text = re.sub(r"[-_\s]+", "", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
    return text.strip()


def common_prefix_length(left: str, right: str) -> int:
    size = 0
    for lch, rch in zip(left, right):
        if lch != rch:
            break
        size += 1
    return size


def char_overlap_score(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    left_chars = set(left)
    right_chars = set(right)
    union = left_chars | right_chars
    if not union:
        return 0.0
    return len(left_chars & right_chars) / len(union)



def match_score(query: str, candidate: str) -> float:
    q = normalize_match_text(query)
    c = normalize_match_text(candidate)
    if not q or not c:
        return 0.0
    ratio = SequenceMatcher(None, q, c).ratio()
    substring = 1.0 if q in c or c in q else 0.0
    prefix = common_prefix_length(q, c) / max(len(q), len(c), 1)
    overlap = char_overlap_score(q, c)
    return ratio * 0.45 + substring * 0.2 + prefix * 0.2 + overlap * 0.15


def load_json(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def valid_quote_json_path(path: Path | None) -> Path | None:
    if not path or not path.is_file():
        return None
    return path if load_json(path) is not None else None


def latest_output_xlsx(project_dir: Path) -> Path | None:
    output_dir = project_dir / "output"
    if not output_dir.is_dir():
        return None
    matches = sorted(
        (path for path in output_dir.glob("*.xlsx") if path.is_file()),
        key=lambda path: (path.stat().st_mtime, path.name),
        reverse=True,
    )
    return matches[0] if matches else None


def alias_entries_from_project_dir(project_dir: Path) -> list[tuple[str, float]]:
    entries: list[tuple[str, float]] = []
    stem, _timestamp = parse_project_dir_name(project_dir.name)
    entries.append((stem, 1.0))

    manifest_path = project_dir / "workspace-manifest.json"
    manifest = load_json(manifest_path) if manifest_path.exists() else None
    if manifest:
        entries.extend((str(value), 0.95) for value in manifest.get("aliases") or [] if str(value).strip())
        entries.extend((str(value), 1.0) for value in [manifest.get("project_name")] if str(value or "").strip())
        entries.extend((str(value), 0.85) for value in [manifest.get("title")] if str(value or "").strip())

    quote_json_path = project_dir / "quote-project.json"
    quote_payload = load_json(quote_json_path) if valid_quote_json_path(quote_json_path) else None
    if quote_payload:
        entries.extend((str(value), 1.0) for value in [quote_payload.get("project_name")] if str(value or "").strip())

    output_xlsx = latest_output_xlsx(project_dir)
    if output_xlsx:
        entries.append((output_xlsx.stem, 0.9))

    source_dir = project_dir / "source"
    if source_dir.is_dir():
        for path in source_dir.iterdir():
            if not path.is_file():
                continue
            normalized = normalize_match_text(path.stem)
            weight = 0.35
            if normalized in GENERIC_SOURCE_ALIASES or len(normalized) < 5:
                weight = 0.15
            entries.append((path.stem, weight))

    deduped: list[str] = []
    seen: set[str] = set()
    collapsed_entries: list[tuple[str, float]] = []
    for alias, weight in entries:
        text = str(alias or "").strip()
        if not text:
            continue
        marker = normalize_match_text(text) or text
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(text)
        collapsed_entries.append((text, weight))
    return collapsed_entries


def aliases_from_project_dir(project_dir: Path) -> list[str]:
    return [alias for alias, _weight in alias_entries_from_project_dir(project_dir)]


def infer_project_name(project_dir: Path) -> str:
    manifest = load_json(project_dir / "workspace-manifest.json")
    if manifest and str(manifest.get("project_name") or "").strip():
        return str(manifest["project_name"]).strip()
    payload = load_json(project_dir / "quote-project.json")
    if payload and str(payload.get("project_name") or "").strip():
        return str(payload["project_name"]).strip()
    stem, _timestamp = parse_project_dir_name(project_dir.name)
    return stem


def infer_resume_capability(project_dir: Path) -> str:
    if valid_quote_json_path(project_dir / "quote-project.json"):
        return "quote_json"
    if latest_output_xlsx(project_dir):
        return "xlsx_recovered"
    if (project_dir / "source").is_dir() and any((project_dir / "source").iterdir()):
        return "source_regenerated"
    return "unavailable"


def history_candidates(root_dir: Path, query: str, limit: int = 5) -> list[HistoryCandidate]:
    if not root_dir.exists() or not root_dir.is_dir():
        return []

    candidates: list[HistoryCandidate] = []
    for project_dir in root_dir.iterdir():
        if not project_dir.is_dir():
            continue
        alias_entries = alias_entries_from_project_dir(project_dir)
        if not alias_entries:
            alias_entries = [(project_dir.name, 1.0)]
        aliases = [alias for alias, _weight in alias_entries]
        best_basis = aliases[0]
        best_score = -1.0
        for alias, weight in alias_entries:
            score = match_score(query, alias) * weight
            if score > best_score:
                best_score = score
                best_basis = alias
        project_name = infer_project_name(project_dir)
        _stem, timestamp = parse_project_dir_name(project_dir.name)
        output_xlsx = latest_output_xlsx(project_dir)
        quote_json = valid_quote_json_path(project_dir / "quote-project.json")
        manifest_path = project_dir / "workspace-manifest.json" if (project_dir / "workspace-manifest.json").is_file() else None
        candidates.append(
            HistoryCandidate(
                project_dir=project_dir.resolve(),
                project_name=project_name,
                timestamp=timestamp,
                output_xlsx=output_xlsx.resolve() if output_xlsx else None,
                quote_json=quote_json.resolve() if quote_json else None,
                workspace_manifest=manifest_path.resolve() if manifest_path else None,
                resume_capability=infer_resume_capability(project_dir),
                aliases=tuple(aliases),
                match_score=best_score,
                match_basis=best_basis,
            )
        )

    candidates.sort(
        key=lambda item: (
            item.match_score,
            item.timestamp,
            item.project_dir.name,
        ),
        reverse=True,
    )
    return candidates[: max(limit, 1)]


def history_candidates_from_roots(root_dirs: list[Path], query: str, limit: int = 5) -> list[HistoryCandidate]:
    combined: list[HistoryCandidate] = []
    seen: set[Path] = set()
    for root_dir in root_dirs:
        for candidate in history_candidates(root_dir, query, limit=10_000):
            if candidate.project_dir in seen:
                continue
            seen.add(candidate.project_dir)
            combined.append(candidate)

    combined.sort(
        key=lambda item: (
            item.match_score,
            item.timestamp,
            item.project_dir.name,
        ),
        reverse=True,
    )
    return combined[: max(limit, 1)]


def ensure_path(value: str | Path | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser().resolve()


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def copy_tree_contents(src_dir: Path, dst_dir: Path) -> list[dict[str, str]]:
    copied: list[dict[str, str]] = []
    if not src_dir.is_dir():
        return copied
    for path in sorted(src_dir.iterdir()):
        target = dst_dir / path.name
        if path.is_dir():
            shutil_copytree(path, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            import shutil

            shutil.copy2(path, target)
        copied.append({"input": str(path.resolve()), "archived": str(target.resolve())})
    return copied


def shutil_copytree(src: Path, dst: Path) -> None:
    import shutil

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
