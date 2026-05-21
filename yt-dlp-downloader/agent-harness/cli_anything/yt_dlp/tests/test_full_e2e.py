from __future__ import annotations

import json
import os
import functools
import http.server
import shutil
import subprocess
import sys
import threading
from pathlib import Path


HARNESS_ROOT = Path(__file__).resolve().parents[3]
SKILL_ROOT = HARNESS_ROOT.parent


def _resolve_cli(name: str) -> list[str]:
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    return [sys.executable, "-m", "cli_anything.yt_dlp.yt_dlp_cli"]


class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-anything-yt-dlp")

    def _run(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(self.CLI_BASE + args, capture_output=True, text=True, check=check)

    def test_help(self) -> None:
        result = self._run(["--help"])

        assert "system" in result.stdout
        assert "download" in result.stdout

    def test_system_status_json(self) -> None:
        result = self._run(["--json", "system", "status"], check=False)
        data = json.loads(result.stdout)

        assert data["command"] == "system status"
        assert "yt_dlp" in data["dependencies"]

    def test_raw_version_json(self) -> None:
        result = self._run(["--json", "raw", "--", "--version"])
        data = json.loads(result.stdout)

        assert data["command"] == "raw"
        assert data["returncode"] == 0
        assert data["stdout_tail"].strip()


def test_legacy_preflight_shim_json() -> None:
    script = SKILL_ROOT / "scripts" / "yt_dlp_downloader.py"

    result = subprocess.run([sys.executable, str(script), "preflight", "--json"], capture_output=True, text=True)
    data = json.loads(result.stdout)

    assert data["command"] == "preflight"
    assert "yt_dlp" in data


def test_download_local_http_video_json(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for this E2E test")

    media_dir = tmp_path / "media"
    media_dir.mkdir()
    source = media_dir / "tiny.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=16x16:rate=1",
            "-t",
            "1",
            "-pix_fmt",
            "yuv420p",
            str(source),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(media_dir))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/tiny.mp4"
        output_dir = tmp_path / "out"
        result = subprocess.run(
            _resolve_cli("cli-anything-yt-dlp")
            + ["--json", "download", "--playlist-mode", "single", "--output-dir", str(output_dir), url],
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)

    data = json.loads(result.stdout)
    assert data["command"] == "download"
    assert data["status"] == "success"
    final_paths = data["results"][0]["final_paths"]
    assert final_paths
    assert Path(final_paths[0]).exists()
