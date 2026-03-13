#!/usr/bin/env python3
"""Helper script for the yt-dlp-downloader skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

DEFAULT_OUTPUT_DIR = Path.home() / "视频" / "yt-dlp"
DEFAULT_CHUNK_SIZE = 100
DEFAULT_HUGE_THRESHOLD = 100
TAIL_LINE_COUNT = 60
YTDLP_BIN = "yt-dlp"
STATE_DIR = Path.home() / ".local" / "share" / "yt-dlp-downloader"
MANAGED_VENV_DIR = STATE_DIR / "venv"
MANAGED_PYTHON = MANAGED_VENV_DIR / "bin" / "python"
MANAGED_YTDLP = MANAGED_VENV_DIR / "bin" / "yt-dlp"
USER_SITE_YTDLP = Path.home() / ".local" / "bin" / "yt-dlp"
PREFERRED_JS_RUNTIMES = ("deno", "node", "bun", "qjs", "quickjs")
BROWSER_COMMANDS = {
    "chrome": ("google-chrome-stable", "google-chrome"),
    "chromium": ("chromium", "chromium-browser"),
    "firefox": ("firefox",),
}
ANTI_BOT_PATTERNS = (
    "captcha",
    "unable to extract initial state",
    "sign in to confirm",
    "rate-limit",
    "rate limit",
    "forbidden",
    "http error 403",
)


class UsageError(RuntimeError):
    """Raised when the caller provides invalid arguments."""


def run_command(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace")


def tail_text(text: str, line_count: int = TAIL_LINE_COUNT) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    snippet = "\n".join(lines[-line_count:])
    if len(snippet) > 4000:
        return snippet[:4000] + "...<truncated>"
    return snippet


def unique_preserve_order(items: Sequence[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def which(name: str) -> Optional[str]:
    return shutil.which(name)


def resolve_binary(binary: str) -> Optional[str]:
    candidate = Path(binary).expanduser()
    if candidate.exists() and os.access(candidate, os.X_OK):
        return str(candidate.resolve())
    return which(binary)


def resolve_ytdlp_bin() -> Optional[str]:
    if MANAGED_YTDLP.exists() and os.access(MANAGED_YTDLP, os.X_OK):
        return str(MANAGED_YTDLP.resolve())
    if USER_SITE_YTDLP.exists() and os.access(USER_SITE_YTDLP, os.X_OK):
        return str(USER_SITE_YTDLP.resolve())
    return which(YTDLP_BIN)


def managed_python_has_pip() -> bool:
    if not MANAGED_PYTHON.exists() or not os.access(MANAGED_PYTHON, os.X_OK):
        return False
    proc = run_command([str(MANAGED_PYTHON), "-m", "pip", "--version"])
    return proc.returncode == 0


def resolve_pip_python() -> str:
    if managed_python_has_pip():
        return str(MANAGED_PYTHON.resolve())
    return sys.executable


def command_version(command: Sequence[str]) -> Dict[str, Any]:
    binary = resolve_binary(command[0])
    if not binary:
        return {"available": False, "path": None, "version": None}
    resolved_command = [binary, *command[1:]]
    proc = run_command(resolved_command)
    version = ""
    for line in (proc.stdout or proc.stderr).splitlines():
        if line.strip():
            version = line.strip()
            break
    return {
        "available": proc.returncode == 0,
        "path": binary,
        "version": version or None,
    }


def pip_show(package: str) -> Dict[str, Any]:
    python_bin = resolve_pip_python()
    proc = run_command([python_bin, "-m", "pip", "show", package])
    if proc.returncode != 0:
        return {"available": False, "version": None, "location": None, "python": python_bin}

    fields: Dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip().lower()] = value.strip()
    return {
        "available": True,
        "version": fields.get("version"),
        "location": fields.get("location"),
        "python": python_bin,
    }


def detect_js_runtime() -> Dict[str, Any]:
    runtimes: Dict[str, Dict[str, Any]] = {}
    preferred: Optional[str] = None
    for runtime in PREFERRED_JS_RUNTIMES:
        info = command_version([runtime, "--version"])
        runtimes[runtime] = info
        if info["available"] and preferred is None:
            preferred = runtime
    return {
        "preferred": preferred,
        "runtimes": runtimes,
    }


def build_js_runtime_args() -> List[str]:
    js_info = detect_js_runtime()
    preferred = js_info.get("preferred")
    if not preferred:
        return []
    runtime_info = js_info["runtimes"].get(preferred) or {}
    runtime_path = runtime_info.get("path")
    if runtime_path:
        return ["--js-runtimes", f"{preferred}:{runtime_path}"]
    return ["--js-runtimes", preferred]


def detect_browsers() -> Dict[str, Any]:
    browsers: Dict[str, Dict[str, Any]] = {}
    available: List[str] = []
    for logical_name, commands in BROWSER_COMMANDS.items():
        chosen_path = None
        chosen_command = None
        version = None
        for command_name in commands:
            binary = which(command_name)
            if not binary:
                continue
            proc = run_command([command_name, "--version"])
            chosen_path = binary
            chosen_command = command_name
            for line in (proc.stdout or proc.stderr).splitlines():
                if line.strip():
                    version = line.strip()
                    break
            break
        info = {
            "available": chosen_path is not None,
            "command": chosen_command,
            "path": chosen_path,
            "version": version,
        }
        browsers[logical_name] = info
        if info["available"]:
            available.append(logical_name)
    return {"available": available, "browsers": browsers}


def detect_platform_tools() -> Dict[str, Any]:
    return {
        "apt_get": which("apt-get"),
        "brew": which("brew"),
        "pacman": which("pacman"),
        "dnf": which("dnf"),
        "yum": which("yum"),
    }


def ffmpeg_install_hint(platform_tools: Dict[str, Any]) -> str:
    if platform_tools.get("apt_get"):
        return "sudo apt-get update && sudo apt-get install -y ffmpeg"
    if platform_tools.get("brew"):
        return "brew install ffmpeg"
    if platform_tools.get("pacman"):
        return "sudo pacman -S ffmpeg"
    if platform_tools.get("dnf"):
        return "sudo dnf install -y ffmpeg"
    if platform_tools.get("yum"):
        return "sudo yum install -y ffmpeg"
    return "Install ffmpeg from https://ffmpeg.org/download.html"


def preflight_state() -> Dict[str, Any]:
    python_info = {
        "available": True,
        "path": sys.executable,
        "version": sys.version.split()[0],
    }
    pip_info = command_version([sys.executable, "-m", "pip", "--version"])
    managed_ytdlp = resolve_ytdlp_bin()
    ytdlp_info = command_version([managed_ytdlp or YTDLP_BIN, "--version"])
    ytdlp_info["source"] = (
        "managed-venv" if managed_ytdlp and Path(managed_ytdlp).resolve() == MANAGED_YTDLP.resolve() else "path"
        if managed_ytdlp
        else None
    )
    ytdlp_info["managed_venv"] = str(MANAGED_VENV_DIR)
    ffmpeg_info = command_version(["ffmpeg", "-version"])
    ffprobe_info = command_version(["ffprobe", "-version"])
    ejs_info = pip_show("yt-dlp-ejs")
    secretstorage_info = pip_show("secretstorage")
    js_info = detect_js_runtime()
    browser_info = detect_browsers()
    platform_tools = detect_platform_tools()
    ffmpeg_hint = ffmpeg_install_hint(platform_tools)

    return {
        "command": "preflight",
        "python": python_info,
        "pip": pip_info,
        "yt_dlp": ytdlp_info,
        "ffmpeg": ffmpeg_info,
        "ffprobe": ffprobe_info,
        "yt_dlp_ejs": ejs_info,
        "secretstorage": secretstorage_info,
        "js_runtime": js_info,
        "browsers": browser_info,
        "ffmpeg_install_hint": ffmpeg_hint,
        "ready_for_download": bool(ytdlp_info["available"] and ffmpeg_info["available"]),
        "ready_for_full_youtube": bool(
            ytdlp_info["available"]
            and ffmpeg_info["available"]
            and ejs_info["available"]
            and js_info["preferred"]
        ),
    }


def print_result(payload: Dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    command = payload.get("command")
    if command == "preflight":
        print_preflight(payload)
        return
    if command == "bootstrap":
        print_bootstrap(payload)
        return
    if command == "probe":
        print_probe(payload)
        return
    if command == "download":
        print_download(payload)
        return
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def print_preflight(payload: Dict[str, Any]) -> None:
    print("yt-dlp preflight")
    print(f"- python: {payload['python']['version']} ({payload['python']['path']})")
    pip_line = payload["pip"].get("version") or "missing"
    print(f"- pip: {pip_line}")
    ytdlp = payload["yt_dlp"]
    ffmpeg = payload["ffmpeg"]
    ffprobe = payload["ffprobe"]
    ejs = payload["yt_dlp_ejs"]
    secretstorage = payload["secretstorage"]
    js_runtime = payload["js_runtime"]
    browsers = payload["browsers"]
    print(
        f"- yt-dlp: {'yes' if ytdlp['available'] else 'no'} "
        f"{ytdlp.get('version') or ''} [{ytdlp.get('source') or 'missing'}]".rstrip()
    )
    print(f"- ffmpeg: {'yes' if ffmpeg['available'] else 'no'} {ffmpeg.get('version') or ''}".rstrip())
    print(f"- ffprobe: {'yes' if ffprobe['available'] else 'no'} {ffprobe.get('version') or ''}".rstrip())
    print(f"- yt-dlp-ejs: {'yes' if ejs['available'] else 'no'} {ejs.get('version') or ''}".rstrip())
    print(f"- secretstorage: {'yes' if secretstorage['available'] else 'no'} {secretstorage.get('version') or ''}".rstrip())
    print(f"- preferred JS runtime: {js_runtime.get('preferred') or 'missing'}")
    available_browsers = ", ".join(browsers["available"]) if browsers["available"] else "none"
    print(f"- browser cookies candidates: {available_browsers}")
    print(f"- ready for download: {'yes' if payload['ready_for_download'] else 'no'}")
    print(f"- ready for full YouTube support: {'yes' if payload['ready_for_full_youtube'] else 'no'}")
    if not ffmpeg["available"]:
        print(f"- ffmpeg install hint: {payload['ffmpeg_install_hint']}")


def print_bootstrap(payload: Dict[str, Any]) -> None:
    print("yt-dlp bootstrap")
    print(f"- status: {payload['status']}")
    for step in payload.get("steps", []):
        print(f"- {step['name']}: {'ok' if step['ok'] else 'failed'}")
        if step.get("stdout_tail"):
            print(indent_block(step["stdout_tail"]))
        if step.get("stderr_tail"):
            print(indent_block(step["stderr_tail"]))
    if payload.get("ffmpeg_install_hint"):
        print(f"- ffmpeg install hint: {payload['ffmpeg_install_hint']}")
    print_preflight(payload["preflight"])


def print_probe(payload: Dict[str, Any]) -> None:
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
        if item.get("stderr_tail"):
            print(indent_block(item["stderr_tail"], prefix="    stderr: "))
        if item.get("error"):
            print(f"  error: {item['error']}")


def print_download(payload: Dict[str, Any]) -> None:
    print("yt-dlp download")
    print(f"- overall status: {payload['status']}")
    print(f"- output_dir: {payload['output_dir']}")
    for item in payload["results"]:
        print(f"- url: {item['url']}")
        print(f"  status: {item['status']}")
        if item.get("extractor"):
            print(f"  extractor: {item['extractor']}")
        if item.get("download_mode"):
            print(f"  mode: {item['download_mode']}")
        if item.get("archive_file"):
            print(f"  archive: {item['archive_file']}")
        if item.get("entry_count") is not None:
            print(f"  entry_count: {item['entry_count']}")
        if item.get("final_paths"):
            print("  files:")
            for path in item["final_paths"]:
                print(f"    - {path}")
        if item.get("non_mp4_passthrough_paths"):
            print("  non_mp4_passthrough:")
            for path in item["non_mp4_passthrough_paths"]:
                print(f"    - {path}")
        if item.get("hint"):
            print(f"  hint: {item['hint']}")
        if item.get("stderr_tail"):
            print(indent_block(item["stderr_tail"], prefix="    stderr: "))
        for chunk in item.get("chunks", []):
            print(
                f"    chunk {chunk['range']}: {'ok' if chunk['returncode'] == 0 else 'failed'} "
                f"({len(chunk.get('final_paths', []))} files)"
            )
    if payload.get("ffmpeg_install_hint"):
        print(f"- ffmpeg install hint: {payload['ffmpeg_install_hint']}")


def indent_block(text: str, prefix: str = "    ") -> str:
    return "\n".join(f"{prefix}{line}" for line in text.splitlines())


def ensure_tool_available(name: str, hint: Optional[str] = None) -> None:
    if which(name):
        return
    message = f"Required tool is missing: {name}"
    if hint:
        message += f". Install hint: {hint}"
    raise UsageError(message)


def build_auth_args(browser: Optional[str], cookies_file: Optional[str]) -> Tuple[List[str], Dict[str, Any]]:
    if browser and cookies_file:
        raise UsageError("Use either --browser or --cookies-file, not both")

    auth_meta = {
        "browser": browser,
        "cookies_file": str(Path(cookies_file).expanduser()) if cookies_file else None,
        "used_browser_cookies": False,
    }
    args: List[str] = []
    if browser:
        browser_info = detect_browsers()
        if browser not in BROWSER_COMMANDS:
            allowed = ", ".join(sorted(BROWSER_COMMANDS))
            raise UsageError(f"Unsupported browser '{browser}'. Use one of: {allowed}")
        if browser not in browser_info["available"]:
            available = ", ".join(browser_info["available"]) or "none"
            raise UsageError(f"Browser '{browser}' is not available. Available browser cookies sources: {available}")
        if sys.platform.startswith("linux") and browser in {"chrome", "chromium"}:
            secretstorage_info = pip_show("secretstorage")
            if not secretstorage_info["available"]:
                raise UsageError(
                    "Linux Chrome/Chromium cookies require the Python package 'secretstorage'. "
                    "Install it with: python3 -m pip install --user --break-system-packages -U secretstorage"
                )
        args.extend(["--cookies-from-browser", browser])
        auth_meta["used_browser_cookies"] = True
    elif cookies_file:
        cookie_path = Path(cookies_file).expanduser().resolve()
        if not cookie_path.exists():
            raise UsageError(f"Cookies file does not exist: {cookie_path}")
        args.extend(["--cookies", str(cookie_path)])
    return args, auth_meta


def parse_json_output(stdout: str) -> Dict[str, Any]:
    candidate = stdout.strip()
    if not candidate:
        raise ValueError("yt-dlp produced empty stdout")
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        for line in reversed(candidate.splitlines()):
            line = line.strip()
            if not line:
                continue
            return json.loads(line)
        raise


def parse_after_move_paths(stdout: str) -> List[str]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        return []
    existing = [line for line in lines if Path(line).exists()]
    if existing:
        return unique_preserve_order(existing)
    filtered = [line for line in lines if not line.startswith("[")]
    return unique_preserve_order(filtered)


def first_non_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def probe_url(url: str, auth_args: Sequence[str]) -> Dict[str, Any]:
    ytdlp_bin = resolve_ytdlp_bin()
    if not ytdlp_bin:
        raise UsageError("yt-dlp is missing. Run bootstrap first.")
    command = [ytdlp_bin, "--ignore-config", *build_js_runtime_args(), "--dump-single-json", "--flat-playlist", *auth_args, url]
    proc = run_command(command)
    base_result: Dict[str, Any] = {
        "url": url,
        "status": "error",
        "returncode": proc.returncode,
        "command": command,
        "stdout_tail": tail_text(proc.stdout),
        "stderr_tail": tail_text(proc.stderr),
        "host": urlparse(url).netloc,
    }
    if proc.returncode != 0:
        base_result["error"] = tail_text(proc.stderr) or tail_text(proc.stdout) or "probe failed"
        base_result["hint"] = anti_bot_hint(url, None, base_result["stderr_tail"])
        return base_result

    try:
        payload = parse_json_output(proc.stdout)
    except Exception as exc:
        base_result["error"] = f"Failed to parse yt-dlp JSON: {exc}"
        base_result["hint"] = anti_bot_hint(url, None, base_result["stderr_tail"])
        return base_result

    entries = payload.get("entries")
    entry_count = first_non_none(
        coerce_int(payload.get("playlist_count")),
        coerce_int(payload.get("n_entries")),
        len(entries) if isinstance(entries, list) else None,
    )
    extractor = payload.get("extractor_key") or payload.get("extractor")
    is_playlist_like = bool(
        payload.get("_type") in {"playlist", "multi_video"}
        or isinstance(entries, list)
        or payload.get("playlist")
    )
    base_result.update(
        {
            "status": "success",
            "extractor": extractor,
            "id": payload.get("id"),
            "title": payload.get("title"),
            "webpage_url": payload.get("webpage_url"),
            "playlist_title": payload.get("playlist_title") or payload.get("title") if is_playlist_like else None,
            "playlist_id": payload.get("playlist_id") or payload.get("id") if is_playlist_like else None,
            "is_playlist_like": is_playlist_like,
            "entry_count": entry_count,
            "stdout_tail": "",
        }
    )
    return base_result


def stable_archive_key(probe_result: Dict[str, Any], url: str) -> str:
    extractor = (probe_result.get("extractor") or "generic").lower()
    media_id = probe_result.get("playlist_id") or probe_result.get("id")
    if media_id:
        raw = f"{extractor}-{media_id}"
    else:
        raw = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    sanitized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in raw)
    return sanitized.strip("-") or hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def looks_like_xiaohongshu(url: str, extractor: Optional[str], stderr: str) -> bool:
    haystacks = [url.lower(), (extractor or "").lower(), stderr.lower()]
    return any("xiaohongshu" in item or "xhslink" in item or "rednote" in item for item in haystacks)


def anti_bot_hint(url: str, extractor: Optional[str], stderr: str) -> Optional[str]:
    lower_stderr = stderr.lower()
    if looks_like_xiaohongshu(url, extractor, stderr) and any(pattern in lower_stderr for pattern in ANTI_BOT_PATTERNS):
        return "Xiaohongshu is not stable. The extractor likely hit anti-bot or CAPTCHA; retrying with cookies may still fail."
    if any(pattern in lower_stderr for pattern in ANTI_BOT_PATTERNS):
        return "The site likely rate-limited or challenged yt-dlp. Try cookies, a different URL, or a newer yt-dlp build."
    return None


def resolve_output_dir(path_text: str) -> Path:
    path = Path(path_text).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_download_command(
    url: str,
    output_dir: Path,
    auth_args: Sequence[str],
    playlist_mode: str,
    extra_args: Sequence[str],
    archive_file: Optional[Path] = None,
    playlist_items: Optional[Tuple[int, int]] = None,
    max_downloads: Optional[int] = None,
) -> List[str]:
    ytdlp_bin = resolve_ytdlp_bin()
    if not ytdlp_bin:
        raise UsageError("yt-dlp is missing. Run bootstrap first.")
    command = [
        ytdlp_bin,
        "--ignore-config",
        *build_js_runtime_args(),
        "--no-progress",
        "-f",
        "bv*+ba/b",
        "--merge-output-format",
        "mp4",
        "-P",
        f"home:{output_dir}",
        "-o",
        "%(title)s [%(id)s].%(ext)s",
        "--print",
        "after_move:filepath",
    ]
    if playlist_mode == "single":
        command.append("--no-playlist")
    elif playlist_mode == "playlist":
        command.append("--yes-playlist")

    if archive_file:
        command.extend(["--download-archive", str(archive_file)])
    if playlist_items:
        command.extend(["--playlist-items", f"{playlist_items[0]}:{playlist_items[1]}"])
    if max_downloads is not None:
        command.extend(["--max-downloads", str(max_downloads)])
    command.extend(auth_args)
    command.extend(extra_args)
    command.append(url)
    return command


def run_download_once(
    url: str,
    output_dir: Path,
    auth_args: Sequence[str],
    playlist_mode: str,
    extra_args: Sequence[str],
    extractor: Optional[str],
    archive_file: Optional[Path] = None,
    playlist_items: Optional[Tuple[int, int]] = None,
    max_downloads: Optional[int] = None,
) -> Dict[str, Any]:
    command = build_download_command(
        url=url,
        output_dir=output_dir,
        auth_args=auth_args,
        playlist_mode=playlist_mode,
        extra_args=extra_args,
        archive_file=archive_file,
        playlist_items=playlist_items,
        max_downloads=max_downloads,
    )
    proc = run_command(command)
    final_paths = parse_after_move_paths(proc.stdout)
    non_mp4_paths = [path for path in final_paths if Path(path).suffix.lower() != ".mp4"]
    stderr_tail = tail_text(proc.stderr)
    result = {
        "returncode": proc.returncode,
        "command": command,
        "final_paths": final_paths,
        "non_mp4_passthrough_paths": non_mp4_paths,
        "stdout_tail": tail_text(proc.stdout),
        "stderr_tail": stderr_tail,
        "hint": anti_bot_hint(url, extractor, stderr_tail),
    }
    return result


def download_url(
    url: str,
    output_dir: Path,
    auth_args: Sequence[str],
    playlist_mode: str,
    extra_args: Sequence[str],
    chunk_size: int,
    huge_threshold: int,
    max_downloads: Optional[int],
) -> Dict[str, Any]:
    probe_result = probe_url(url, auth_args)
    extractor = probe_result.get("extractor")
    base_result: Dict[str, Any] = {
        "url": url,
        "status": "error",
        "extractor": extractor,
        "entry_count": probe_result.get("entry_count"),
        "probe": probe_result,
        "final_paths": [],
        "non_mp4_passthrough_paths": [],
        "chunks": [],
        "download_mode": "direct",
        "archive_file": None,
        "stderr_tail": "",
        "stdout_tail": "",
        "hint": probe_result.get("hint"),
    }

    playlist_like = bool(probe_result.get("is_playlist_like"))
    entry_count = probe_result.get("entry_count")
    should_chunk = bool(
        playlist_mode != "single"
        and probe_result.get("status") == "success"
        and playlist_like
        and entry_count is not None
        and entry_count > huge_threshold
    )

    if should_chunk:
        archives_dir = output_dir / ".archives"
        archives_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archives_dir / f"{stable_archive_key(probe_result, url)}.txt"
        base_result["archive_file"] = str(archive_path)
        base_result["download_mode"] = "incremental-batched"

        remaining = max_downloads
        start = 1
        while start <= entry_count:
            if remaining is not None and remaining <= 0:
                break
            end = min(start + chunk_size - 1, entry_count)
            chunk_limit = remaining if remaining is not None else None
            chunk = run_download_once(
                url=url,
                output_dir=output_dir,
                auth_args=auth_args,
                playlist_mode=playlist_mode,
                extra_args=extra_args,
                extractor=extractor,
                archive_file=archive_path,
                playlist_items=(start, end),
                max_downloads=chunk_limit,
            )
            chunk["range"] = f"{start}:{end}"
            base_result["chunks"].append(chunk)
            base_result["final_paths"].extend(chunk["final_paths"])
            base_result["non_mp4_passthrough_paths"].extend(chunk["non_mp4_passthrough_paths"])
            base_result["stdout_tail"] = chunk["stdout_tail"]
            base_result["stderr_tail"] = chunk["stderr_tail"]
            base_result["hint"] = chunk.get("hint") or base_result.get("hint")
            if chunk["returncode"] != 0:
                base_result["status"] = "partial_error" if base_result["final_paths"] else "error"
                break
            if remaining is not None:
                remaining -= len(chunk["final_paths"])
            start = end + 1
        else:
            base_result["status"] = "success"

        if base_result["status"] == "error" and not base_result["final_paths"] and base_result["chunks"]:
            pass
        elif base_result["status"] == "error" and base_result["final_paths"]:
            base_result["status"] = "partial_error"
        elif base_result["status"] == "error" and not base_result["chunks"]:
            base_result["status"] = "error"
        elif base_result["status"] not in {"success", "partial_error"}:
            if all(chunk["returncode"] == 0 for chunk in base_result["chunks"]):
                base_result["status"] = "success"
        base_result["final_paths"] = unique_preserve_order(base_result["final_paths"])
        base_result["non_mp4_passthrough_paths"] = unique_preserve_order(base_result["non_mp4_passthrough_paths"])
        return base_result

    direct = run_download_once(
        url=url,
        output_dir=output_dir,
        auth_args=auth_args,
        playlist_mode=playlist_mode,
        extra_args=extra_args,
        extractor=extractor,
        max_downloads=max_downloads,
    )
    base_result.update(direct)
    base_result["status"] = "success" if direct["returncode"] == 0 else "error"
    return base_result


def overall_status(results: Sequence[Dict[str, Any]]) -> str:
    if not results:
        return "success"
    statuses = {item.get("status") for item in results}
    if statuses == {"success"}:
        return "success"
    if "success" in statuses or "partial_error" in statuses:
        return "partial_error"
    return "error"


def command_preflight(args: argparse.Namespace) -> int:
    payload = preflight_state()
    print_result(payload, args.json)
    return 0 if payload["ready_for_download"] else 1


def command_bootstrap(args: argparse.Namespace) -> int:
    steps: List[Dict[str, Any]] = []
    install_python: Optional[str] = None
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not MANAGED_PYTHON.exists():
        venv_cmd = [sys.executable, "-m", "venv", str(MANAGED_VENV_DIR)]
        venv_proc = run_command(venv_cmd)
        steps.append(
            {
                "name": "create managed venv",
                "ok": venv_proc.returncode == 0,
                "returncode": venv_proc.returncode,
                "command": venv_cmd,
                "stdout_tail": tail_text(venv_proc.stdout),
                "stderr_tail": tail_text(venv_proc.stderr),
            }
        )
    if managed_python_has_pip():
        install_python = str(MANAGED_PYTHON)

    if install_python:
        package_args = [install_python, "-m", "pip", "install", "-U"]
        install_name = f"install yt-dlp ({args.channel}) in managed venv"
    else:
        package_args = [sys.executable, "-m", "pip", "install", "--user", "--break-system-packages", "-U"]
        install_name = f"install yt-dlp ({args.channel}) in user site"
    if args.channel == "nightly":
        package_args.append("--pre")
    package_args.extend(["yt-dlp[default]", "secretstorage"])
    pip_proc = run_command(package_args)
    steps.append(
        {
            "name": install_name,
            "ok": pip_proc.returncode == 0,
            "returncode": pip_proc.returncode,
            "command": package_args,
            "stdout_tail": tail_text(pip_proc.stdout),
            "stderr_tail": tail_text(pip_proc.stderr),
        }
    )

    ffmpeg_hint = ffmpeg_install_hint(detect_platform_tools())
    if args.install_ffmpeg:
        if which("apt-get"):
            if os.geteuid() == 0:
                ffmpeg_cmd = ["apt-get", "update"]
                update_proc = run_command(ffmpeg_cmd)
                steps.append(
                    {
                        "name": "apt-get update",
                        "ok": update_proc.returncode == 0,
                        "returncode": update_proc.returncode,
                        "command": ffmpeg_cmd,
                        "stdout_tail": tail_text(update_proc.stdout),
                        "stderr_tail": tail_text(update_proc.stderr),
                    }
                )
                install_cmd = ["apt-get", "install", "-y", "ffmpeg"]
            else:
                ffmpeg_cmd = ["sudo", "-n", "apt-get", "update"]
                update_proc = run_command(ffmpeg_cmd)
                steps.append(
                    {
                        "name": "sudo apt-get update",
                        "ok": update_proc.returncode == 0,
                        "returncode": update_proc.returncode,
                        "command": ffmpeg_cmd,
                        "stdout_tail": tail_text(update_proc.stdout),
                        "stderr_tail": tail_text(update_proc.stderr),
                    }
                )
                install_cmd = ["sudo", "-n", "apt-get", "install", "-y", "ffmpeg"]
            install_proc = run_command(install_cmd)
            steps.append(
                {
                    "name": "install ffmpeg",
                    "ok": install_proc.returncode == 0,
                    "returncode": install_proc.returncode,
                    "command": install_cmd,
                    "stdout_tail": tail_text(install_proc.stdout),
                    "stderr_tail": tail_text(install_proc.stderr),
                }
            )
        else:
            steps.append(
                {
                    "name": "install ffmpeg",
                    "ok": False,
                    "returncode": 1,
                    "command": [],
                    "stdout_tail": "",
                    "stderr_tail": f"Automatic ffmpeg install is only implemented for apt-get systems. Hint: {ffmpeg_hint}",
                }
            )

    preflight = preflight_state()
    bootstrap_ok = preflight["yt_dlp"]["available"] and (not args.install_ffmpeg or preflight["ffmpeg"]["available"])
    payload = {
        "command": "bootstrap",
        "status": "success" if bootstrap_ok else "partial_error",
        "steps": steps,
        "preflight": preflight,
        "ffmpeg_install_hint": ffmpeg_hint,
    }
    print_result(payload, args.json)
    return 0 if bootstrap_ok else 1


def command_probe(args: argparse.Namespace) -> int:
    auth_args, auth_meta = build_auth_args(args.browser, args.cookies_file)
    results = [probe_url(url, auth_args) for url in args.urls]
    payload = {
        "command": "probe",
        "status": overall_status(results),
        "results": results,
        **auth_meta,
    }
    print_result(payload, args.json)
    return 0 if payload["status"] == "success" else 1


def command_download(args: argparse.Namespace) -> int:
    state = preflight_state()
    if not state["yt_dlp"]["available"]:
        raise UsageError("yt-dlp is missing. Run bootstrap first.")
    if not state["ffmpeg"]["available"]:
        raise UsageError(f"ffmpeg is missing. Install hint: {state['ffmpeg_install_hint']}")

    auth_args, auth_meta = build_auth_args(args.browser, args.cookies_file)
    output_dir = resolve_output_dir(args.output_dir)
    results = [
        download_url(
            url=url,
            output_dir=output_dir,
            auth_args=auth_args,
            playlist_mode=args.playlist_mode,
            extra_args=args.extra_arg,
            chunk_size=args.chunk_size,
            huge_threshold=args.huge_threshold,
            max_downloads=args.max_downloads,
        )
        for url in args.urls
    ]
    payload = {
        "command": "download",
        "status": overall_status(results),
        "output_dir": str(output_dir),
        "results": results,
        "ffmpeg_install_hint": state["ffmpeg_install_hint"],
        **auth_meta,
    }
    print_result(payload, args.json)
    return 0 if payload["status"] == "success" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="yt-dlp-downloader skill helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight", help="Check runtime dependencies")
    preflight.add_argument("--json", action="store_true", help="Print JSON output")
    preflight.set_defaults(handler=command_preflight)

    bootstrap = subparsers.add_parser("bootstrap", help="Install or update yt-dlp")
    bootstrap.add_argument("--channel", choices=("stable", "nightly"), default="stable")
    bootstrap.add_argument("--install-ffmpeg", action="store_true", help="Attempt to install ffmpeg via apt-get")
    bootstrap.add_argument("--json", action="store_true", help="Print JSON output")
    bootstrap.set_defaults(handler=command_bootstrap)

    probe = subparsers.add_parser("probe", help="Inspect one or more URLs without downloading")
    probe.add_argument("urls", nargs="+", help="One or more URLs to inspect")
    probe.add_argument("--browser", choices=sorted(BROWSER_COMMANDS.keys()))
    probe.add_argument("--cookies-file")
    probe.add_argument("--json", action="store_true", help="Print JSON output")
    probe.set_defaults(handler=command_probe)

    download = subparsers.add_parser("download", help="Download one or more URLs")
    download.add_argument("urls", nargs="+", help="One or more URLs to download")
    download.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    download.add_argument("--playlist-mode", choices=("auto", "single", "playlist"), default="auto")
    download.add_argument("--browser", choices=sorted(BROWSER_COMMANDS.keys()))
    download.add_argument("--cookies-file")
    download.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    download.add_argument("--huge-threshold", type=int, default=DEFAULT_HUGE_THRESHOLD)
    download.add_argument("--max-downloads", type=int)
    download.add_argument("--extra-arg", action="append", default=[], metavar="ARG")
    download.add_argument("--json", action="store_true", help="Print JSON output")
    download.set_defaults(handler=command_download)

    return parser


def validate_args(args: argparse.Namespace) -> None:
    if getattr(args, "chunk_size", DEFAULT_CHUNK_SIZE) <= 0:
        raise UsageError("--chunk-size must be greater than 0")
    if getattr(args, "huge_threshold", DEFAULT_HUGE_THRESHOLD) <= 0:
        raise UsageError("--huge-threshold must be greater than 0")
    max_downloads = getattr(args, "max_downloads", None)
    if max_downloads is not None and max_downloads <= 0:
        raise UsageError("--max-downloads must be greater than 0")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        validate_args(args)
        return args.handler(args)
    except UsageError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"command": args.command, "status": "error", "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
