#!/usr/bin/env python3
"""Compatibility shim for the yt-dlp-downloader skill.

The implementation lives in the CLI-Anything harness under `agent-harness/`.
This script preserves the old skill entry point:

  python3 scripts/yt_dlp_downloader.py preflight --json
  python3 scripts/yt_dlp_downloader.py download URL
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
HARNESS_ROOT = SKILL_ROOT / "agent-harness"
sys.path.insert(0, str(HARNESS_ROOT))

from cli_anything.yt_dlp.core.jobs import DEFAULT_CHUNK_SIZE, DEFAULT_HUGE_THRESHOLD, DEFAULT_OUTPUT_DIR  # noqa: E402
from cli_anything.yt_dlp.core.results import overall_status  # noqa: E402
from cli_anything.yt_dlp.utils import yt_dlp_backend as backend  # noqa: E402


def print_result(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return
    command = payload.get("command")
    if command == "preflight":
        print_preflight(payload)
    elif command == "bootstrap":
        print_bootstrap(payload)
    elif command == "probe":
        print_probe(payload)
    elif command == "download":
        print_download(payload)
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def print_preflight(payload: dict[str, Any]) -> None:
    print("yt-dlp preflight")
    print(f"- python: {payload['python']['version']} ({payload['python']['path']})")
    print(f"- yt-dlp: {'yes' if payload['yt_dlp']['available'] else 'no'} {payload['yt_dlp'].get('version') or ''}".rstrip())
    print(f"- ffmpeg: {'yes' if payload['ffmpeg']['available'] else 'no'} {payload['ffmpeg'].get('version') or ''}".rstrip())
    print(f"- ffprobe: {'yes' if payload['ffprobe']['available'] else 'no'} {payload['ffprobe'].get('version') or ''}".rstrip())
    print(f"- yt-dlp-ejs: {'yes' if payload['yt_dlp_ejs']['available'] else 'no'} {payload['yt_dlp_ejs'].get('version') or ''}".rstrip())
    print(f"- preferred JS runtime: {payload['js_runtime'].get('preferred') or 'missing'}")
    print(f"- browser cookies candidates: {', '.join(payload['browsers']['available']) or 'none'}")
    print(f"- ready for download: {'yes' if payload['ready_for_download'] else 'no'}")
    print(f"- ready for full YouTube support: {'yes' if payload['ready_for_full_youtube'] else 'no'}")
    if not payload["ffmpeg"]["available"]:
        print(f"- ffmpeg install hint: {payload['ffmpeg_install_hint']}")


def print_bootstrap(payload: dict[str, Any]) -> None:
    print("yt-dlp bootstrap")
    print(f"- status: {payload['status']}")
    for step in payload.get("steps", []):
        print(f"- {step['name']}: {'ok' if step.get('ok') else 'failed'}")
        if step.get("stderr_tail"):
            print(step["stderr_tail"])
    print_preflight(payload["preflight"])


def print_probe(payload: dict[str, Any]) -> None:
    print("yt-dlp probe")
    print(f"- urls: {len(payload['results'])}")
    for item in payload["results"]:
        print(f"- url: {item['url']}")
        print(f"  status: {item['status']}")
        if item.get("extractor"):
            print(f"  extractor: {item['extractor']}")
        if item.get("title"):
            print(f"  title: {item['title']}")
        if item.get("entry_count") is not None:
            print(f"  entry_count: {item['entry_count']}")
        print(f"  playlist_like: {'yes' if item.get('is_playlist_like') else 'no'}")
        if item.get("hint"):
            print(f"  hint: {item['hint']}")


def print_download(payload: dict[str, Any]) -> None:
    print("yt-dlp download")
    print(f"- overall status: {payload['status']}")
    print(f"- output_dir: {payload['output_dir']}")
    for item in payload["results"]:
        print(f"- url: {item['url']}")
        print(f"  status: {item['status']}")
        if item.get("download_mode"):
            print(f"  mode: {item['download_mode']}")
        for path in item.get("final_paths", []) or []:
            print(f"  file: {path}")
        if item.get("hint"):
            print(f"  hint: {item['hint']}")


def command_preflight(args: argparse.Namespace) -> int:
    payload = backend.preflight_state()
    print_result(payload, args.json)
    return 0 if payload["ready_for_download"] else 1


def command_bootstrap(args: argparse.Namespace) -> int:
    payload = backend.bootstrap(channel=args.channel, install_ffmpeg=args.install_ffmpeg)
    print_result(payload, args.json)
    return 0 if payload["status"] == "success" else 1


def command_probe(args: argparse.Namespace) -> int:
    auth_args, auth_meta = backend.build_auth_args(args.browser, args.cookies_file)
    results = [backend.probe_url(url, auth_args) for url in args.urls]
    payload = {"command": "probe", "status": overall_status(results), "results": results, **auth_meta}
    print_result(payload, args.json)
    return 0 if payload["status"] == "success" else 1


def command_download(args: argparse.Namespace) -> int:
    state = backend.preflight_state()
    if not state["yt_dlp"]["available"]:
        raise backend.UsageError("yt-dlp is missing. Run bootstrap first.")
    if not state["ffmpeg"]["available"]:
        raise backend.UsageError(f"ffmpeg is missing. Install hint: {state['ffmpeg_install_hint']}")
    auth_args, auth_meta = backend.build_auth_args(args.browser, args.cookies_file)
    result = backend.download_many(
        urls=args.urls,
        output_dir=Path(args.output_dir),
        auth_args=auth_args,
        playlist_mode=args.playlist_mode,
        extra_args=args.extra_arg,
        chunk_size=args.chunk_size,
        huge_threshold=args.huge_threshold,
        max_downloads=args.max_downloads,
    )
    payload = {"command": "download", **result, "ffmpeg_install_hint": state["ffmpeg_install_hint"], **auth_meta}
    print_result(payload, args.json)
    return 0 if payload["status"] == "success" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="yt-dlp-downloader compatibility helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight", help="Check runtime dependencies")
    preflight.add_argument("--json", action="store_true")
    preflight.set_defaults(handler=command_preflight)

    bootstrap = subparsers.add_parser("bootstrap", help="Install or update yt-dlp")
    bootstrap.add_argument("--channel", choices=("stable", "nightly"), default="stable")
    bootstrap.add_argument("--install-ffmpeg", action="store_true")
    bootstrap.add_argument("--json", action="store_true")
    bootstrap.set_defaults(handler=command_bootstrap)

    probe = subparsers.add_parser("probe", help="Inspect URLs without downloading")
    probe.add_argument("urls", nargs="+")
    probe.add_argument("--browser", choices=sorted(backend.BROWSER_COMMANDS.keys()))
    probe.add_argument("--cookies-file")
    probe.add_argument("--json", action="store_true")
    probe.set_defaults(handler=command_probe)

    download = subparsers.add_parser("download", help="Download URLs")
    download.add_argument("urls", nargs="+")
    download.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    download.add_argument("--playlist-mode", choices=("auto", "single", "playlist"), default="auto")
    download.add_argument("--browser", choices=sorted(backend.BROWSER_COMMANDS.keys()))
    download.add_argument("--cookies-file")
    download.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    download.add_argument("--huge-threshold", type=int, default=DEFAULT_HUGE_THRESHOLD)
    download.add_argument("--max-downloads", type=int)
    download.add_argument("--extra-arg", action="append", default=[], metavar="ARG")
    download.add_argument("--json", action="store_true")
    download.set_defaults(handler=command_download)

    return parser


def validate_args(args: argparse.Namespace) -> None:
    if getattr(args, "chunk_size", DEFAULT_CHUNK_SIZE) <= 0:
        raise backend.UsageError("--chunk-size must be greater than 0")
    if getattr(args, "huge_threshold", DEFAULT_HUGE_THRESHOLD) <= 0:
        raise backend.UsageError("--huge-threshold must be greater than 0")
    max_downloads = getattr(args, "max_downloads", None)
    if max_downloads is not None and max_downloads <= 0:
        raise backend.UsageError("--max-downloads must be greater than 0")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        validate_args(args)
        return args.handler(args)
    except backend.UsageError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"command": args.command, "status": "error", "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
