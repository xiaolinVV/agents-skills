from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from typing import Any

import click

from cli_anything.yt_dlp import __version__
from cli_anything.yt_dlp.core.jobs import DEFAULT_CHUNK_SIZE, DEFAULT_HUGE_THRESHOLD, DEFAULT_OUTPUT_DIR
from cli_anything.yt_dlp.core.options import find_section, flatten_options, parse_help_sections, search_options
from cli_anything.yt_dlp.core.results import envelope, overall_status
from cli_anything.yt_dlp.core.session import SessionStore
from cli_anything.yt_dlp.utils import yt_dlp_backend as backend


_json_output = False


def _out(data: Any) -> None:
    if _json_output:
        click.echo(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    else:
        _pretty(data)


def _pretty(data: Any) -> None:
    if isinstance(data, dict):
        if "dependencies" in data:
            deps = data["dependencies"]
            click.echo("yt-dlp system status")
            click.echo(f"- yt-dlp: {_yes(deps['yt_dlp']['available'])} {deps['yt_dlp'].get('version') or ''}".rstrip())
            click.echo(f"- ffmpeg: {_yes(deps['ffmpeg']['available'])} {deps['ffmpeg'].get('version') or ''}".rstrip())
            click.echo(f"- ffprobe: {_yes(deps['ffprobe']['available'])} {deps['ffprobe'].get('version') or ''}".rstrip())
            click.echo(f"- preferred JS runtime: {deps['js_runtime'].get('preferred') or 'missing'}")
            click.echo(f"- ready for download: {_yes(data.get('ready_for_download'))}")
            if not deps["ffmpeg"]["available"]:
                click.echo(f"- ffmpeg install hint: {data.get('ffmpeg_install_hint')}")
            return
        if "results" in data and isinstance(data["results"], list):
            click.echo(f"{data.get('command', 'command')}: {data.get('status')}")
            for item in data["results"]:
                click.echo(f"- {item.get('url', item.get('title', 'item'))}: {item.get('status')}")
                for path in item.get("final_paths", []) or []:
                    click.echo(f"  file: {path}")
                if item.get("hint"):
                    click.echo(f"  hint: {item['hint']}")
                if item.get("stderr_tail"):
                    click.echo(f"  stderr: {item['stderr_tail']}")
            return
        if "stdout" in data and data.get("stdout"):
            click.echo(data["stdout"], nl=False)
            return
        for key, value in data.items():
            click.echo(f"{key}: {value}")
    elif isinstance(data, list):
        for item in data:
            _pretty(item)
    else:
        click.echo(str(data))


def _yes(value: Any) -> str:
    return "yes" if value else "no"


def _err(message: str, command: str = "error") -> None:
    if _json_output:
        click.echo(json.dumps(envelope(command, "error", error=message), ensure_ascii=False, indent=2), err=False)
    else:
        click.echo(f"Error: {message}", err=True)


def _handle_errors(fn):
    import functools

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except backend.UsageError as exc:
            _err(str(exc), command=getattr(fn, "__name__", "error").replace("_cmd", ""))
            raise SystemExit(2) from exc
        except Exception as exc:  # noqa: BLE001
            _err(f"Unexpected error: {exc}", command=getattr(fn, "__name__", "error").replace("_cmd", ""))
            raise SystemExit(1) from exc

    return wrapper


@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Emit machine-readable JSON.")
@click.option("--session", "session_name", default="default", show_default=True, help="Session name.")
@click.option("--profile", default=None, help="Profile name to load from session state.")
@click.option("--no-color", is_flag=True, help="Disable colored REPL output.")
@click.version_option(__version__)
@click.pass_context
def cli(ctx: click.Context, use_json: bool, session_name: str, profile: str | None, no_color: bool) -> None:
    """Agent-native CLI-Anything harness for yt-dlp."""
    global _json_output
    _json_output = use_json
    ctx.ensure_object(dict)
    ctx.obj["session"] = SessionStore(name=session_name)
    ctx.obj["profile"] = profile
    ctx.obj["no_color"] = no_color
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


@cli.group("system")
def system_group() -> None:
    """Runtime, dependency, and update commands."""


@system_group.command("status")
@click.option("--strict", is_flag=True, help="Exit non-zero when download dependencies are missing.")
@click.pass_context
@_handle_errors
def system_status(ctx: click.Context, strict: bool) -> None:
    """Check yt-dlp, ffmpeg, JS runtimes, and browsers."""
    state = backend.preflight_state()
    payload = envelope(
        "system status",
        "success" if state["ready_for_download"] else "partial_error",
        dependencies={
            "python": state["python"],
            "pip": state["pip"],
            "yt_dlp": state["yt_dlp"],
            "ffmpeg": state["ffmpeg"],
            "ffprobe": state["ffprobe"],
            "yt_dlp_ejs": state["yt_dlp_ejs"],
            "secretstorage": state["secretstorage"],
            "js_runtime": state["js_runtime"],
            "browsers": state["browsers"],
        },
        ready_for_download=state["ready_for_download"],
        ready_for_full_youtube=state["ready_for_full_youtube"],
        ffmpeg_install_hint=state["ffmpeg_install_hint"],
        session=ctx.obj["session"].to_dict(),
    )
    _out(payload)
    if strict and not state["ready_for_download"]:
        raise SystemExit(1)


@system_group.command("bootstrap")
@click.option("--channel", type=click.Choice(["stable", "nightly"]), default="stable", show_default=True)
@click.option("--install-ffmpeg", is_flag=True, help="Report an ffmpeg install hint; no package manager command is run automatically.")
@_handle_errors
def system_bootstrap(channel: str, install_ffmpeg: bool) -> None:
    """Install or update yt-dlp in the managed Python environment."""
    result = backend.bootstrap(channel=channel, install_ffmpeg=install_ffmpeg)
    payload = dict(result)
    payload.pop("command", None)
    status = payload.pop("status")
    _out(envelope("system bootstrap", status, **payload))
    if result["status"] == "error":
        raise SystemExit(1)


@system_group.command("version")
@_handle_errors
def system_version() -> None:
    """Print the official yt-dlp version."""
    result = backend.raw(["--version"])
    _out(envelope("system version", result["status"], returncode=result["returncode"], stdout_tail=result["stdout_tail"], stderr_tail=result["stderr_tail"]))
    if result["returncode"] != 0:
        raise SystemExit(result["returncode"])


@system_group.command("update")
@click.option("--channel", type=click.Choice(["stable", "nightly", "master"]), default="stable", show_default=True)
@click.option("--tag", default="latest", show_default=True)
@click.option("--yes", is_flag=True, help="Run the update instead of only showing the command.")
@_handle_errors
def system_update(channel: str, tag: str, yes: bool) -> None:
    """Update yt-dlp through its official updater when supported by the install source."""
    update_arg = f"{channel}@{tag}"
    args = ["--update-to", update_arg]
    if not yes:
        _out(envelope("system update", "dry_run", command=["yt-dlp", *args]))
        return
    result = backend.raw(args)
    _out(envelope("system update", result["status"], returncode=result["returncode"], stdout_tail=result["stdout_tail"], stderr_tail=result["stderr_tail"]))
    if result["returncode"] != 0:
        raise SystemExit(result["returncode"])


@cli.command("raw", context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
@_handle_errors
def raw_cmd(ctx: click.Context, args: tuple[str, ...]) -> None:
    """Mirror official yt-dlp: pass arbitrary arguments after `--`."""
    if not args:
        raise backend.UsageError("raw requires yt-dlp arguments, e.g. raw -- --version")
    result = backend.raw(args)
    payload = envelope(
        "raw",
        result["status"],
        returncode=result["returncode"],
        backend={"path": backend.resolve_ytdlp_bin()},
        args=list(args),
        stdout_tail=result["stdout_tail"],
        stderr_tail=result["stderr_tail"],
        stdout=result["stdout"] if not _json_output else None,
    )
    ctx.obj["session"].append_history("raw", {"args": list(args)}, payload)
    _out(payload)
    if result["returncode"] != 0:
        raise SystemExit(result["returncode"])


@cli.group("options")
def options_group() -> None:
    """Search and inspect the current yt-dlp option catalog."""


def _option_sections() -> list[Any]:
    return parse_help_sections(backend.get_help_text())


@options_group.command("sections")
@_handle_errors
def options_sections() -> None:
    """List yt-dlp help sections."""
    sections = _option_sections()
    _out(envelope("options sections", "success", sections=[section.name for section in sections]))


@options_group.command("list")
@click.option("--section", "section_name", default=None, help="Filter by section name.")
@_handle_errors
def options_list(section_name: str | None) -> None:
    """List parsed yt-dlp options."""
    sections = _option_sections()
    if section_name:
        section = find_section(sections, section_name)
        options = section.options if section else []
    else:
        options = flatten_options(sections)
    _out(envelope("options list", "success", options=[option.to_dict() for option in options]))


@options_group.command("search")
@click.argument("text")
@_handle_errors
def options_search(text: str) -> None:
    """Search flags, metavars, and descriptions."""
    matches = search_options(_option_sections(), text)
    _out(envelope("options search", "success", query=text, matches=[match.to_dict() for match in matches]))


@options_group.command("show")
@click.argument("section_name")
@_handle_errors
def options_show(section_name: str) -> None:
    """Show one help section."""
    section = find_section(_option_sections(), section_name)
    status = "success" if section else "error"
    _out(envelope("options show", status, section=section.to_dict() if section else None))
    if section is None:
        raise SystemExit(1)


@cli.group("inspect")
def inspect_group() -> None:
    """Probe URLs and list available media metadata."""


@inspect_group.command("probe")
@click.argument("urls", nargs=-1, required=True)
@click.option("--browser", type=click.Choice(sorted(backend.BROWSER_COMMANDS.keys())))
@click.option("--cookies-file")
@_handle_errors
def inspect_probe(urls: tuple[str, ...], browser: str | None, cookies_file: str | None) -> None:
    """Inspect URLs without downloading."""
    auth_args, auth_meta = backend.build_auth_args(browser, cookies_file)
    results = [backend.probe_url(url, auth_args) for url in urls]
    _out(envelope("inspect probe", overall_status(results), results=results, **auth_meta))


@inspect_group.command("info")
@click.argument("urls", nargs=-1, required=True)
@click.option("--browser", type=click.Choice(sorted(backend.BROWSER_COMMANDS.keys())))
@click.option("--cookies-file")
@_handle_errors
def inspect_info(urls: tuple[str, ...], browser: str | None, cookies_file: str | None) -> None:
    """Dump full yt-dlp JSON metadata."""
    auth_args, auth_meta = backend.build_auth_args(browser, cookies_file)
    results = []
    for url in urls:
        result = backend.raw(["--ignore-config", *backend.build_js_runtime_args(), "--dump-single-json", *auth_args, url])
        results.append({"url": url, **result})
    _out(envelope("inspect info", overall_status(results), results=results, **auth_meta))


def _inspect_raw(command_name: str, flag: str, url: str) -> None:
    result = backend.raw(["--ignore-config", flag, url])
    _out(envelope(f"inspect {command_name}", result["status"], returncode=result["returncode"], stdout_tail=result["stdout_tail"], stderr_tail=result["stderr_tail"], stdout=result["stdout"] if not _json_output else None))
    if result["returncode"] != 0:
        raise SystemExit(result["returncode"])


@inspect_group.command("formats")
@click.argument("url")
@_handle_errors
def inspect_formats(url: str) -> None:
    """List available formats for a URL."""
    _inspect_raw("formats", "--list-formats", url)


@inspect_group.command("subtitles")
@click.argument("url")
@_handle_errors
def inspect_subtitles(url: str) -> None:
    """List available subtitles for a URL."""
    _inspect_raw("subtitles", "--list-subs", url)


@inspect_group.command("thumbnails")
@click.argument("url")
@_handle_errors
def inspect_thumbnails(url: str) -> None:
    """List available thumbnails for a URL."""
    _inspect_raw("thumbnails", "--list-thumbnails", url)


@cli.command("download")
@click.argument("urls", nargs=-1, required=True)
@click.option("--output-dir", default=str(DEFAULT_OUTPUT_DIR), show_default=True)
@click.option("--playlist-mode", type=click.Choice(["auto", "single", "playlist"]), default="auto", show_default=True)
@click.option("--browser", type=click.Choice(sorted(backend.BROWSER_COMMANDS.keys())))
@click.option("--cookies-file")
@click.option("--chunk-size", type=click.IntRange(1), default=DEFAULT_CHUNK_SIZE, show_default=True)
@click.option("--huge-threshold", type=click.IntRange(1), default=DEFAULT_HUGE_THRESHOLD, show_default=True)
@click.option("--max-downloads", type=click.IntRange(1), default=None)
@click.option("--extra-arg", multiple=True, metavar="ARG", help="Pass an additional official yt-dlp argument. Repeat for values.")
@click.pass_context
@_handle_errors
def download_cmd(
    ctx: click.Context,
    urls: tuple[str, ...],
    output_dir: str,
    playlist_mode: str,
    browser: str | None,
    cookies_file: str | None,
    chunk_size: int,
    huge_threshold: int,
    max_downloads: int | None,
    extra_arg: tuple[str, ...],
) -> None:
    """Download URLs with agent-safe defaults."""
    state = backend.preflight_state()
    if not state["yt_dlp"]["available"]:
        raise backend.UsageError("yt-dlp is missing. Run system bootstrap first.")
    if not state["ffmpeg"]["available"]:
        raise backend.UsageError(f"ffmpeg is missing. Install hint: {state['ffmpeg_install_hint']}")
    auth_args, auth_meta = backend.build_auth_args(browser, cookies_file)
    result = backend.download_many(
        urls=urls,
        output_dir=Path(output_dir),
        auth_args=auth_args,
        playlist_mode=playlist_mode,
        extra_args=extra_arg,
        chunk_size=chunk_size,
        huge_threshold=huge_threshold,
        max_downloads=max_downloads,
    )
    payload_data = dict(result)
    status = payload_data.pop("status")
    payload = envelope("download", status, ffmpeg_install_hint=state["ffmpeg_install_hint"], **payload_data, **auth_meta)
    ctx.obj["session"].append_history("download", {"urls": list(urls), "output_dir": output_dir}, payload)
    _out(payload)
    if result["status"] != "success":
        raise SystemExit(1)


@cli.group("batch")
def batch_group() -> None:
    """Batch download helpers."""


@batch_group.command("from-file")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--output-dir", default=str(DEFAULT_OUTPUT_DIR), show_default=True)
@click.option("--playlist-mode", type=click.Choice(["auto", "single", "playlist"]), default="auto", show_default=True)
@click.option("--extra-arg", multiple=True, metavar="ARG")
@_handle_errors
def batch_from_file(file: Path, output_dir: str, playlist_mode: str, extra_arg: tuple[str, ...]) -> None:
    """Download URLs listed one per line in a file."""
    urls = [line.strip() for line in file.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")]
    result = backend.download_many(urls=urls, output_dir=Path(output_dir), auth_args=[], playlist_mode=playlist_mode, extra_args=extra_arg)
    payload_data = dict(result)
    status = payload_data.pop("status")
    _out(envelope("batch from-file", status, source_file=str(file), **payload_data))
    if result["status"] != "success":
        raise SystemExit(1)


@cli.group("archive")
@click.pass_context
def archive_group(ctx: click.Context) -> None:
    """Inspect or clear session archive files."""


@archive_group.command("path")
@click.pass_context
def archive_path(ctx: click.Context) -> None:
    store: SessionStore = ctx.obj["session"]
    _out(envelope("archive path", "success", archive_dir=str(store.archive_dir())))


@archive_group.command("status")
@click.pass_context
def archive_status(ctx: click.Context) -> None:
    store: SessionStore = ctx.obj["session"]
    files = sorted(store.archive_dir().glob("*.txt"))
    _out(envelope("archive status", "success", files=[str(path) for path in files], count=len(files)))


@archive_group.command("clear")
@click.option("--yes", is_flag=True, help="Actually remove archive files.")
@click.pass_context
def archive_clear(ctx: click.Context, yes: bool) -> None:
    store: SessionStore = ctx.obj["session"]
    files = sorted(store.archive_dir().glob("*.txt"))
    if yes:
        for path in files:
            path.unlink()
    _out(envelope("archive clear", "success" if yes else "dry_run", files=[str(path) for path in files], removed=len(files) if yes else 0))


@cli.group("extractors")
def extractors_group() -> None:
    """List and search official yt-dlp extractors."""


@extractors_group.command("list")
@_handle_errors
def extractors_list() -> None:
    result = backend.raw(["--list-extractors"])
    lines = [line.strip() for line in result["stdout"].splitlines() if line.strip()]
    _out(envelope("extractors list", result["status"], count=len(lines), extractors=lines, stderr_tail=result["stderr_tail"]))


@extractors_group.command("search")
@click.argument("text")
@_handle_errors
def extractors_search(text: str) -> None:
    result = backend.raw(["--list-extractors"])
    lines = [line.strip() for line in result["stdout"].splitlines() if line.strip()]
    matches = [line for line in lines if text.lower() in line.lower()]
    _out(envelope("extractors search", result["status"], query=text, count=len(matches), extractors=matches, stderr_tail=result["stderr_tail"]))


@extractors_group.command("describe")
@_handle_errors
def extractors_describe() -> None:
    result = backend.raw(["--extractor-descriptions"])
    _out(envelope("extractors describe", result["status"], returncode=result["returncode"], stdout_tail=result["stdout_tail"], stderr_tail=result["stderr_tail"], stdout=result["stdout"] if not _json_output else None))
    if result["returncode"] != 0:
        raise SystemExit(result["returncode"])


@cli.group("session")
def session_group() -> None:
    """Show or edit the lightweight CLI session."""


@session_group.command("show")
@click.pass_context
def session_show(ctx: click.Context) -> None:
    store: SessionStore = ctx.obj["session"]
    _out(envelope("session show", "success", session=store.to_dict(), state=store.load_state()))


@session_group.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def session_set(ctx: click.Context, key: str, value: str) -> None:
    store: SessionStore = ctx.obj["session"]
    state = store.load_state()
    try:
        parsed: Any = json.loads(value)
    except json.JSONDecodeError:
        parsed = value
    state[key] = parsed
    store.save_state(state)
    _out(envelope("session set", "success", key=key, value=parsed))


@session_group.command("reset")
@click.option("--yes", is_flag=True, help="Actually remove session state/history.")
@click.pass_context
def session_reset(ctx: click.Context, yes: bool) -> None:
    store: SessionStore = ctx.obj["session"]
    if yes:
        store.reset()
    _out(envelope("session reset", "success" if yes else "dry_run", session=store.to_dict()))


@session_group.command("history")
@click.pass_context
def session_history(ctx: click.Context) -> None:
    store: SessionStore = ctx.obj["session"]
    history = store.load_history()
    _out(envelope("session history", "success", count=len(history), history=history))


@cli.command("repl")
def repl() -> None:
    """Start the interactive REPL."""
    from cli_anything.yt_dlp.utils.repl_skin import ReplSkin

    skin = ReplSkin("yt-dlp", version=__version__)
    skin.print_banner()
    pt_session = skin.create_prompt_session()
    while True:
        try:
            line = skin.get_input(pt_session).strip()
        except (KeyboardInterrupt, EOFError):
            skin.print_goodbye()
            break
        if not line:
            continue
        if line.lower() in {"exit", "quit", "q"}:
            skin.print_goodbye()
            break
        try:
            cli.main(args=shlex.split(line), standalone_mode=False)
        except SystemExit:
            pass
        except ValueError as exc:
            _err(f"Invalid input: {exc}")
        except Exception as exc:  # noqa: BLE001
            _err(str(exc))


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
