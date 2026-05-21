from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse

from cli_anything.yt_dlp.core.jobs import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_HUGE_THRESHOLD,
    DownloadJob,
    build_structured_download_args,
    stable_archive_key,
)
from cli_anything.yt_dlp.core.results import overall_status


YTDLP_BIN = "yt-dlp"
TAIL_LINE_COUNT = 60
STATE_DIR = Path.home() / ".local" / "share" / "yt-dlp-downloader"
MANAGED_VENV_DIR = STATE_DIR / "venv"
MANAGED_PYTHON = MANAGED_VENV_DIR / "bin" / "python"
MANAGED_YTDLP = MANAGED_VENV_DIR / "bin" / "yt-dlp"
USER_SITE_YTDLP = Path.home() / ".local" / "bin" / "yt-dlp"
PREFERRED_JS_RUNTIMES = ("deno", "node", "bun", "qjs", "quickjs")
BROWSER_COMMANDS = {
    "chrome": ("google-chrome-stable", "google-chrome", "chrome"),
    "chromium": ("chromium", "chromium-browser"),
    "firefox": ("firefox",),
}
MACOS_BROWSER_APPS = {
    "chrome": ("Google Chrome.app",),
    "chromium": ("Chromium.app",),
    "firefox": ("Firefox.app",),
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
    return subprocess.run([str(arg) for arg in cmd], capture_output=True, text=True, errors="replace")


def tail_text(text: str, line_count: int = TAIL_LINE_COUNT) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ""
    snippet = "\n".join(lines[-line_count:])
    return snippet[:4000] + "...<truncated>" if len(snippet) > 4000 else snippet


def unique_preserve_order(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def which(name: str) -> str | None:
    return shutil.which(name)


def resolve_binary(binary: str) -> str | None:
    candidate = Path(binary).expanduser()
    if candidate.exists() and os.access(candidate, os.X_OK):
        return str(candidate.resolve())
    return which(binary)


def resolve_ytdlp_bin() -> str | None:
    explicit = os.environ.get("CLI_ANYTHING_YT_DLP_BIN", "").strip()
    if explicit:
        return resolve_binary(explicit)
    if MANAGED_YTDLP.exists() and os.access(MANAGED_YTDLP, os.X_OK):
        return str(MANAGED_YTDLP.resolve())
    if USER_SITE_YTDLP.exists() and os.access(USER_SITE_YTDLP, os.X_OK):
        return str(USER_SITE_YTDLP.resolve())
    return which(YTDLP_BIN)


def managed_python_has_pip() -> bool:
    if not MANAGED_PYTHON.exists() or not os.access(MANAGED_PYTHON, os.X_OK):
        return False
    return run_command([str(MANAGED_PYTHON), "-m", "pip", "--version"]).returncode == 0


def resolve_pip_python() -> str:
    return str(MANAGED_PYTHON.resolve()) if managed_python_has_pip() else sys.executable


def command_version(command: Sequence[str]) -> dict[str, Any]:
    binary = resolve_binary(command[0])
    if not binary:
        return {"available": False, "path": None, "version": None}
    proc = run_command([binary, *command[1:]])
    version = ""
    for line in (proc.stdout or proc.stderr).splitlines():
        if line.strip():
            version = line.strip()
            break
    return {"available": proc.returncode == 0, "path": binary, "version": version or None}


def pip_show(package: str) -> dict[str, Any]:
    python_bin = resolve_pip_python()
    proc = run_command([python_bin, "-m", "pip", "show", package])
    if proc.returncode != 0:
        return {"available": False, "version": None, "location": None, "python": python_bin}
    fields: dict[str, str] = {}
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


def detect_js_runtime() -> dict[str, Any]:
    runtimes: dict[str, dict[str, Any]] = {}
    preferred: str | None = None
    for runtime in PREFERRED_JS_RUNTIMES:
        info = command_version([runtime, "--version"])
        runtimes[runtime] = info
        if info["available"] and preferred is None:
            preferred = runtime
    return {"preferred": preferred, "runtimes": runtimes}


def build_js_runtime_args(js_info: dict[str, Any] | None = None) -> list[str]:
    info = js_info or detect_js_runtime()
    preferred = info.get("preferred")
    if not preferred:
        return []
    runtime_info = (info.get("runtimes") or {}).get(preferred) or {}
    runtime_path = runtime_info.get("path")
    return ["--js-runtimes", f"{preferred}:{runtime_path}"] if runtime_path else ["--js-runtimes", str(preferred)]


def detect_macos_browser_apps(app_roots: Sequence[Path] | None = None) -> dict[str, dict[str, Any]]:
    roots = [Path(root).expanduser() for root in (app_roots or [Path("/Applications"), Path.home() / "Applications"])]
    detected: dict[str, dict[str, Any]] = {}
    for browser, app_names in MACOS_BROWSER_APPS.items():
        found: Path | None = None
        for root in roots:
            for app_name in app_names:
                candidate = root / app_name
                if candidate.exists():
                    found = candidate
                    break
            if found:
                break
        detected[browser] = {
            "available": found is not None,
            "command": found.name if found else None,
            "path": str(found) if found else None,
            "version": None,
        }
    return detected


def detect_browsers() -> dict[str, Any]:
    browsers: dict[str, dict[str, Any]] = {}
    available: list[str] = []
    macos_apps = detect_macos_browser_apps() if sys.platform == "darwin" else {}
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
        if not chosen_path and logical_name in macos_apps and macos_apps[logical_name]["available"]:
            app = macos_apps[logical_name]
            chosen_path = app["path"]
            chosen_command = app["command"]
            version = app["version"]
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


def detect_platform_tools() -> dict[str, str | None]:
    return {
        "apt_get": which("apt-get"),
        "brew": which("brew"),
        "pacman": which("pacman"),
        "dnf": which("dnf"),
        "yum": which("yum"),
    }


def ffmpeg_install_hint(platform_tools: dict[str, Any]) -> str:
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


def preflight_state() -> dict[str, Any]:
    python_info = {"available": True, "path": sys.executable, "version": sys.version.split()[0]}
    pip_info = command_version([sys.executable, "-m", "pip", "--version"])
    ytdlp_bin = resolve_ytdlp_bin()
    ytdlp_info = command_version([ytdlp_bin or YTDLP_BIN, "--version"])
    ytdlp_info["source"] = _ytdlp_source(ytdlp_bin)
    ytdlp_info["managed_venv"] = str(MANAGED_VENV_DIR)
    ffmpeg_info = command_version(["ffmpeg", "-version"])
    ffprobe_info = command_version(["ffprobe", "-version"])
    ejs_info = pip_show("yt-dlp-ejs")
    secretstorage_info = pip_show("secretstorage")
    js_info = detect_js_runtime()
    browser_info = detect_browsers()
    platform_tools = detect_platform_tools()
    hint = ffmpeg_install_hint(platform_tools)
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
        "ffmpeg_install_hint": hint,
        "ready_for_download": bool(ytdlp_info["available"] and ffmpeg_info["available"]),
        "ready_for_full_youtube": bool(
            ytdlp_info["available"] and ffmpeg_info["available"] and ejs_info["available"] and js_info["preferred"]
        ),
    }


def _ytdlp_source(path: str | None) -> str | None:
    if not path:
        return None
    resolved = Path(path).resolve()
    if MANAGED_YTDLP.exists() and resolved == MANAGED_YTDLP.resolve():
        return "managed-venv"
    if USER_SITE_YTDLP.exists() and resolved == USER_SITE_YTDLP.resolve():
        return "user-site"
    return "path"


def bootstrap(channel: str = "stable", install_ffmpeg: bool = False) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not MANAGED_PYTHON.exists():
        try:
            venv.EnvBuilder(with_pip=True).create(MANAGED_VENV_DIR)
            steps.append({"name": "create managed venv", "ok": True, "returncode": 0, "command": [sys.executable, "-m", "venv", str(MANAGED_VENV_DIR)]})
        except Exception as exc:  # noqa: BLE001
            steps.append(
                {
                    "name": "create managed venv",
                    "ok": False,
                    "returncode": 1,
                    "command": [sys.executable, "-m", "venv", str(MANAGED_VENV_DIR)],
                    "stderr_tail": str(exc),
                }
            )
    install_python = str(MANAGED_PYTHON) if managed_python_has_pip() else sys.executable
    package_args = [install_python, "-m", "pip", "install", "-U"]
    if install_python == sys.executable and sys.platform.startswith("linux"):
        package_args.extend(["--user", "--break-system-packages"])
    elif install_python == sys.executable:
        package_args.append("--user")
    if channel == "nightly":
        package_args.append("--pre")
    package_args.extend(["yt-dlp[default]", "secretstorage"])
    pip_proc = run_command(package_args)
    steps.append(
        {
            "name": f"install yt-dlp ({channel})",
            "ok": pip_proc.returncode == 0,
            "returncode": pip_proc.returncode,
            "command": package_args,
            "stdout_tail": tail_text(pip_proc.stdout),
            "stderr_tail": tail_text(pip_proc.stderr),
        }
    )

    hint = ffmpeg_install_hint(detect_platform_tools())
    if install_ffmpeg:
        steps.append(
            {
                "name": "install ffmpeg",
                "ok": False,
                "returncode": 1,
                "command": [],
                "stderr_tail": f"Automatic ffmpeg installation is intentionally not run by default. Hint: {hint}",
            }
        )
    state = preflight_state()
    ok = bool(state["yt_dlp"]["available"] and (not install_ffmpeg or state["ffmpeg"]["available"]))
    return {
        "command": "bootstrap",
        "status": "success" if ok else "partial_error",
        "steps": steps,
        "preflight": state,
        "ffmpeg_install_hint": hint,
    }


def build_auth_args(browser: str | None, cookies_file: str | None) -> tuple[list[str], dict[str, Any]]:
    if browser and cookies_file:
        raise UsageError("Use either --browser or --cookies-file, not both")
    auth_meta = {
        "browser": browser,
        "cookies_file": str(Path(cookies_file).expanduser()) if cookies_file else None,
        "used_browser_cookies": False,
    }
    args: list[str] = []
    if browser:
        browser_info = detect_browsers()
        if browser not in BROWSER_COMMANDS:
            allowed = ", ".join(sorted(BROWSER_COMMANDS))
            raise UsageError(f"Unsupported browser '{browser}'. Use one of: {allowed}")
        if browser not in browser_info["available"]:
            available = ", ".join(browser_info["available"]) or "none"
            raise UsageError(f"Browser '{browser}' is not available. Available browser cookie sources: {available}")
        if sys.platform.startswith("linux") and browser in {"chrome", "chromium"} and not pip_show("secretstorage")["available"]:
            raise UsageError(
                "Linux Chrome/Chromium cookies require Python package 'secretstorage'. "
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


def parse_json_output(stdout: str) -> dict[str, Any]:
    candidate = stdout.strip()
    if not candidate:
        raise ValueError("yt-dlp produced empty stdout")
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        for line in reversed(candidate.splitlines()):
            line = line.strip()
            if line:
                return json.loads(line)
        raise


def parse_after_move_paths(stdout: str) -> list[str]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        return []
    existing = [line for line in lines if Path(line).exists()]
    if existing:
        return unique_preserve_order(existing)
    filtered = [line for line in lines if not line.startswith("[")]
    return unique_preserve_order(filtered)


def probe_url(url: str, auth_args: Sequence[str]) -> dict[str, Any]:
    ytdlp_bin = resolve_ytdlp_bin()
    if not ytdlp_bin:
        raise UsageError("yt-dlp is missing. Run system bootstrap first.")
    command = [
        ytdlp_bin,
        "--ignore-config",
        *build_js_runtime_args(),
        "--dump-single-json",
        "--flat-playlist",
        *auth_args,
        url,
    ]
    proc = run_command(command)
    base_result: dict[str, Any] = {
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
    except Exception as exc:  # noqa: BLE001
        base_result["error"] = f"Failed to parse yt-dlp JSON: {exc}"
        base_result["hint"] = anti_bot_hint(url, None, base_result["stderr_tail"])
        return base_result

    entries = payload.get("entries")
    entry_count = _first_non_none(
        _coerce_int(payload.get("playlist_count")),
        _coerce_int(payload.get("n_entries")),
        len(entries) if isinstance(entries, list) else None,
    )
    extractor = payload.get("extractor_key") or payload.get("extractor")
    is_playlist_like = bool(payload.get("_type") in {"playlist", "multi_video"} or isinstance(entries, list) or payload.get("playlist"))
    base_result.update(
        {
            "status": "success",
            "extractor": extractor,
            "id": payload.get("id"),
            "title": payload.get("title"),
            "webpage_url": payload.get("webpage_url"),
            "playlist_title": (payload.get("playlist_title") or payload.get("title")) if is_playlist_like else None,
            "playlist_id": (payload.get("playlist_id") or payload.get("id")) if is_playlist_like else None,
            "is_playlist_like": is_playlist_like,
            "entry_count": entry_count,
            "stdout_tail": "",
        }
    )
    return base_result


def raw(args: Sequence[str]) -> dict[str, Any]:
    ytdlp_bin = resolve_ytdlp_bin()
    if not ytdlp_bin:
        raise UsageError("yt-dlp is missing. Run system bootstrap first.")
    command = [ytdlp_bin, *args]
    proc = run_command(command)
    return {
        "command": command,
        "returncode": proc.returncode,
        "status": "success" if proc.returncode == 0 else "error",
        "stdout_tail": tail_text(proc.stdout),
        "stderr_tail": tail_text(proc.stderr),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def run_download_once(
    job: DownloadJob,
    url: str,
    extractor: str | None,
    archive_file: Path | None = None,
    playlist_items: tuple[int, int] | None = None,
    max_downloads: int | None = None,
) -> dict[str, Any]:
    ytdlp_bin = resolve_ytdlp_bin()
    if not ytdlp_bin:
        raise UsageError("yt-dlp is missing. Run system bootstrap first.")
    command = [
        ytdlp_bin,
        *build_structured_download_args(
            DownloadJob(
                urls=[url],
                output_dir=job.output_dir,
                playlist_mode=job.playlist_mode,
                auth_args=job.auth_args,
                extra_args=job.extra_args,
                chunk_size=job.chunk_size,
                huge_threshold=job.huge_threshold,
                max_downloads=job.max_downloads,
                output_template=job.output_template,
            ),
            js_runtime_args=build_js_runtime_args(),
            archive_file=archive_file,
            playlist_items=playlist_items,
            max_downloads=max_downloads,
        ),
    ]
    proc = run_command(command)
    final_paths = parse_after_move_paths(proc.stdout)
    non_mp4_paths = [path for path in final_paths if Path(path).suffix.lower() != ".mp4"]
    stderr_tail = tail_text(proc.stderr)
    return {
        "returncode": proc.returncode,
        "command": command,
        "final_paths": final_paths,
        "non_mp4_passthrough_paths": non_mp4_paths,
        "stdout_tail": tail_text(proc.stdout),
        "stderr_tail": stderr_tail,
        "hint": anti_bot_hint(url, extractor, stderr_tail),
    }


def download_url(job: DownloadJob, url: str) -> dict[str, Any]:
    auth_args = list(job.auth_args)
    probe_result = probe_url(url, auth_args)
    extractor = probe_result.get("extractor")
    base_result: dict[str, Any] = {
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
        job.playlist_mode != "single"
        and probe_result.get("status") == "success"
        and playlist_like
        and entry_count is not None
        and entry_count > job.huge_threshold
    )

    if should_chunk:
        archives_dir = Path(job.output_dir).expanduser().resolve() / ".archives"
        archives_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archives_dir / f"{stable_archive_key(probe_result, url)}.txt"
        base_result["archive_file"] = str(archive_path)
        base_result["download_mode"] = "incremental-batched"
        remaining = job.max_downloads
        start = 1
        while start <= entry_count:
            if remaining is not None and remaining <= 0:
                break
            end = min(start + job.chunk_size - 1, entry_count)
            chunk_limit = remaining if remaining is not None else None
            chunk = run_download_once(job, url, extractor, archive_file=archive_path, playlist_items=(start, end), max_downloads=chunk_limit)
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
        if base_result["status"] not in {"success", "partial_error"} and all(chunk["returncode"] == 0 for chunk in base_result["chunks"]):
            base_result["status"] = "success"
        base_result["final_paths"] = unique_preserve_order(base_result["final_paths"])
        base_result["non_mp4_passthrough_paths"] = unique_preserve_order(base_result["non_mp4_passthrough_paths"])
        return base_result

    direct = run_download_once(job, url, extractor, max_downloads=job.max_downloads)
    base_result.update(direct)
    base_result["status"] = "success" if direct["returncode"] == 0 else "error"
    return base_result


def download_many(
    urls: Sequence[str],
    output_dir: Path,
    auth_args: Sequence[str],
    playlist_mode: str = "auto",
    extra_args: Sequence[str] = (),
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    huge_threshold: int = DEFAULT_HUGE_THRESHOLD,
    max_downloads: int | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    job = DownloadJob(
        urls=list(urls),
        output_dir=output_dir,
        playlist_mode=playlist_mode,
        auth_args=tuple(auth_args),
        extra_args=tuple(extra_args),
        chunk_size=chunk_size,
        huge_threshold=huge_threshold,
        max_downloads=max_downloads,
    )
    results = [download_url(job, url) for url in urls]
    return {"status": overall_status(results), "output_dir": str(output_dir), "results": results}


def get_help_text() -> str:
    result = raw(["--help"])
    if result["returncode"] != 0:
        raise UsageError(result.get("stderr_tail") or "yt-dlp --help failed")
    return result["stdout"]


def _first_non_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _coerce_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def looks_like_xiaohongshu(url: str, extractor: str | None, stderr: str) -> bool:
    haystacks = [url.lower(), (extractor or "").lower(), stderr.lower()]
    return any("xiaohongshu" in item or "xhslink" in item or "rednote" in item for item in haystacks)


def anti_bot_hint(url: str, extractor: str | None, stderr: str) -> str | None:
    lower_stderr = stderr.lower()
    if looks_like_xiaohongshu(url, extractor, stderr) and any(pattern in lower_stderr for pattern in ANTI_BOT_PATTERNS):
        return "Xiaohongshu is unstable. The extractor likely hit anti-bot or CAPTCHA; cookies may still fail."
    if any(pattern in lower_stderr for pattern in ANTI_BOT_PATTERNS):
        return "The site likely rate-limited or challenged yt-dlp. Try cookies, a different URL, or a newer yt-dlp build."
    return None
