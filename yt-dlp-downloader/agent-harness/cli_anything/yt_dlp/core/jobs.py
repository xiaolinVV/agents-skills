from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from typing import Any, Sequence


DEFAULT_OUTPUT_DIR = Path.home() / "视频" / "yt-dlp"
DEFAULT_CHUNK_SIZE = 100
DEFAULT_HUGE_THRESHOLD = 100


@dataclass(frozen=True)
class DownloadJob:
    urls: Sequence[str]
    output_dir: Path = DEFAULT_OUTPUT_DIR
    playlist_mode: str = "auto"
    auth_args: Sequence[str] = field(default_factory=tuple)
    extra_args: Sequence[str] = field(default_factory=tuple)
    chunk_size: int = DEFAULT_CHUNK_SIZE
    huge_threshold: int = DEFAULT_HUGE_THRESHOLD
    max_downloads: int | None = None
    output_template: str = "%(title)s [%(id)s].%(ext)s"


def build_structured_download_args(
    job: DownloadJob,
    js_runtime_args: Sequence[str] = (),
    archive_file: Path | None = None,
    playlist_items: tuple[int, int] | None = None,
    max_downloads: int | None = None,
) -> list[str]:
    args = [
        "--ignore-config",
        *js_runtime_args,
        "--no-progress",
        "-f",
        "bv*+ba/b",
        "--merge-output-format",
        "mp4",
        "-P",
        f"home:{Path(job.output_dir).expanduser()}",
        "-o",
        job.output_template,
        "--print",
        "after_move:filepath",
    ]
    if job.playlist_mode == "single":
        args.append("--no-playlist")
    elif job.playlist_mode == "playlist":
        args.append("--yes-playlist")

    if archive_file:
        args.extend(["--download-archive", str(archive_file)])
    if playlist_items:
        args.extend(["--playlist-items", f"{playlist_items[0]}:{playlist_items[1]}"])

    effective_max = max_downloads if max_downloads is not None else job.max_downloads
    if effective_max is not None:
        args.extend(["--max-downloads", str(effective_max)])

    args.extend(job.auth_args)
    args.extend(job.extra_args)
    args.extend(job.urls)
    return [str(arg) for arg in args]


def stable_archive_key(probe_result: dict[str, Any], url: str) -> str:
    extractor = (probe_result.get("extractor") or "generic").lower()
    media_id = probe_result.get("playlist_id") or probe_result.get("id")
    raw = f"{extractor}-{media_id}" if media_id else hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    sanitized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in raw)
    return sanitized.strip("-") or hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
