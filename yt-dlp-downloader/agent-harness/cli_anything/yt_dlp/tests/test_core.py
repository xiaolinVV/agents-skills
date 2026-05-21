from __future__ import annotations

import json
from pathlib import Path

from cli_anything.yt_dlp.core.jobs import DownloadJob, build_structured_download_args, stable_archive_key
from cli_anything.yt_dlp.core.options import parse_help_sections, search_options
from cli_anything.yt_dlp.core.results import envelope, overall_status
from cli_anything.yt_dlp.core.session import SessionStore
from cli_anything.yt_dlp.utils.yt_dlp_backend import (
    build_js_runtime_args,
    detect_macos_browser_apps,
    parse_after_move_paths,
)


HELP_TEXT = """Usage: yt-dlp [OPTIONS] URL [URL...]

Options:

  General Options:
    -h, --help                      Print this help text and exit
    --ignore-config                 Don't load configuration files
    --js-runtimes RUNTIME[:PATH]    Additional JavaScript runtime to enable

  Download Options:
    -N, --concurrent-fragments N    Number of fragments
    --limit-rate RATE               Maximum download rate
"""


def test_parse_help_sections_groups_options() -> None:
    sections = parse_help_sections(HELP_TEXT)

    assert [section.name for section in sections] == ["General Options", "Download Options"]
    assert sections[0].options[0].flags == ["-h", "--help"]
    assert sections[0].options[1].flags == ["--ignore-config"]
    assert sections[1].options[1].metavar == "RATE"


def test_search_options_finds_flags_and_descriptions() -> None:
    sections = parse_help_sections(HELP_TEXT)

    matches = search_options(sections, "runtime")

    assert len(matches) == 1
    assert matches[0].section == "General Options"
    assert matches[0].flags == ["--js-runtimes"]


def test_structured_download_command_keeps_skill_defaults(tmp_path: Path) -> None:
    job = DownloadJob(urls=["https://example.test/video"], output_dir=tmp_path, playlist_mode="single")

    args = build_structured_download_args(job, js_runtime_args=["--js-runtimes", "deno:/bin/deno"])

    assert args[:2] == ["--ignore-config", "--js-runtimes"]
    assert "-f" in args
    assert "bv*+ba/b" in args
    assert "--merge-output-format" in args
    assert "mp4" in args
    assert "--print" in args
    assert "after_move:filepath" in args
    assert "--no-playlist" in args
    assert "https://example.test/video" == args[-1]


def test_parse_after_move_paths_prefers_existing_files(tmp_path: Path) -> None:
    final_file = tmp_path / "clip.mp4"
    final_file.write_bytes(b"data")

    paths = parse_after_move_paths(f"[download] noise\n{final_file}\nmissing.mp4\n")

    assert paths == [str(final_file)]


def test_stable_archive_key_uses_extractor_and_playlist_id() -> None:
    key = stable_archive_key({"extractor": "YoutubeTab", "playlist_id": "PL 1"}, "https://example.test")

    assert key == "youtubetab-PL-1"


def test_result_envelope_status_rollup() -> None:
    result = envelope("probe", "success", results=[{"status": "success"}], backend={"path": "/bin/yt-dlp"})

    assert result["command"] == "probe"
    assert result["backend"]["path"] == "/bin/yt-dlp"
    assert overall_status([{"status": "success"}, {"status": "error"}]) == "partial_error"


def test_session_store_saves_state_and_history(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, name="demo")

    store.save_state({"output_dir": "/tmp/out"})
    store.append_history("raw", {"args": ["--version"]}, {"status": "success"})

    assert store.load_state()["output_dir"] == "/tmp/out"
    history = json.loads(store.history_path.read_text(encoding="utf-8"))
    assert history[0]["command"] == "raw"


def test_macos_browser_detection_accepts_application_bundles(tmp_path: Path) -> None:
    apps = tmp_path / "Applications"
    (apps / "Google Chrome.app").mkdir(parents=True)
    (apps / "Firefox.app").mkdir()

    detected = detect_macos_browser_apps(app_roots=[apps])

    assert detected["chrome"]["available"] is True
    assert detected["firefox"]["available"] is True


def test_build_js_runtime_args_uses_preferred_runtime_path() -> None:
    args = build_js_runtime_args({"preferred": "deno", "runtimes": {"deno": {"path": "/usr/bin/deno"}}})

    assert args == ["--js-runtimes", "deno:/usr/bin/deno"]
