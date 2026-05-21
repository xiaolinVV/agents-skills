---
name: "yt-dlp-downloader"
description: >-
  Download and inspect media URLs through a CLI-Anything harness for yt-dlp,
  with JSON output, browser cookies, archive handling, and raw passthrough to
  the official yt-dlp CLI.
---

# YT-DLP Downloader

Use this skill when the user gives media URLs supported by `yt-dlp` and wants to
download, probe, inspect formats, use browser cookies, or pass official yt-dlp
flags.

## Command

After copying this skill to a new host, initialize it:

```bash
python3 scripts/init_skill.py --json
```

For a host where `yt-dlp` should be installed automatically if missing:

```bash
python3 scripts/init_skill.py --json --bootstrap-yt-dlp
```

The initializer installs the bundled CLI-Anything harness, checks the CLI
command, runs system status, and returns next actions for missing PATH entries or
system packages such as `ffmpeg`.

```bash
cli-anything-yt-dlp --json system status
```

If the command is unavailable, install the bundled harness:

```bash
cd ~/.agents/skills/yt-dlp-downloader/agent-harness
python3 -m pip install -e .
```

## Common Workflows

Probe before downloading:

```bash
cli-anything-yt-dlp --json inspect probe "<URL>"
```

Download one video:

```bash
cli-anything-yt-dlp --json download --playlist-mode single "<URL>"
```

Download a playlist incrementally:

```bash
cli-anything-yt-dlp --json download --playlist-mode playlist "<URL>"
```

Use browser cookies only when the user asks for logged-in access:

```bash
cli-anything-yt-dlp --json download --browser chrome "<URL>"
```

Mirror official yt-dlp arguments:

```bash
cli-anything-yt-dlp --json raw -- --version
cli-anything-yt-dlp raw -- --list-extractors
```

Search the current option catalog:

```bash
cli-anything-yt-dlp --json options search subtitles
```

## Defaults

- Structured downloads pass `--ignore-config`.
- Structured downloads prefer `bv*+ba/b` and MP4 merge output.
- Structured downloads report final moved paths with `after_move:filepath`.
- Large playlists use archive files to avoid redownloading existing entries.
- `raw` does not add defaults; it is official `yt-dlp` passthrough.

## Boundaries

Download only content the user is authorized to download. Do not help bypass DRM,
paid access controls, or account restrictions.
