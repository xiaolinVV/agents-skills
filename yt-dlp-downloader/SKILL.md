---
name: yt-dlp-downloader
description: Download, probe, inspect, and batch-handle media URLs through a CLI-Anything harness for yt-dlp. Use when a user provides URLs supported by yt-dlp, asks to save video/audio locally, inspect formats/subtitles/extractors, use browser cookies, or pass official yt-dlp flags with JSON output.
---

# YT-DLP Downloader

Use the bundled CLI-Anything harness, not ad hoc `yt-dlp` commands.

## Preflight

After this skill is copied to a new machine, initialize it first:

```bash
python3 scripts/init_skill.py --json
```

If the host should install `yt-dlp` automatically when missing:

```bash
python3 scripts/init_skill.py --json --bootstrap-yt-dlp
```

Use dry-run mode before changing a newly provisioned host:

```bash
python3 scripts/init_skill.py --json --dry-run
```

The initializer installs the bundled CLI-Anything harness, checks whether
`cli-anything-yt-dlp` is on `PATH`, runs system status, and returns next actions
for missing `ffmpeg` or PATH setup. It does not install system packages.

```bash
cli-anything-yt-dlp --json system status
```

If the command is missing:

```bash
cd ~/.agents/skills/yt-dlp-downloader/agent-harness
python3 -m pip install -e .
```

Legacy scripts still work:

```bash
python3 scripts/yt_dlp_downloader.py preflight --json
```

## Defaults

- Save structured downloads to `~/视频/yt-dlp` unless the user says otherwise.
- Structured downloads pass `--ignore-config`.
- Prefer `-f bv*+ba/b`.
- Prefer MP4 for merged streams with `--merge-output-format mp4`.
- Report final paths with `--print after_move:filepath`.
- Use explicit `--js-runtimes` when a supported runtime exists.
- Use archive files for large playlists to avoid redownloading items.
- Use browser cookies only when the user asks for logged-in/private/age-restricted access.

## Common Commands

Probe:

```bash
cli-anything-yt-dlp --json inspect probe "<URL>"
```

Download a single video:

```bash
cli-anything-yt-dlp --json download --playlist-mode single "<URL>"
```

Download a whole playlist:

```bash
cli-anything-yt-dlp --json download --playlist-mode playlist "<URL>"
```

Use Chrome cookies:

```bash
cli-anything-yt-dlp --json download --browser chrome "<URL>"
```

Search official options from the installed yt-dlp:

```bash
cli-anything-yt-dlp --json options search subtitles
```

Mirror official yt-dlp exactly:

```bash
cli-anything-yt-dlp --json raw -- --version
cli-anything-yt-dlp raw -- --list-extractors
```

## Failure Handling

- If `ffmpeg` is missing, stop and return the install hint.
- If YouTube says sign-in/bot challenge, suggest cookies; do not claim the URL is invalid.
- If Chrome/Chromium cookies fail on Linux, check `secretstorage` first.
- Xiaohongshu/Rednote support is unstable; report actual extractor stderr and do not promise support.

## Boundaries

Download only content the user is authorized to download. Do not help bypass DRM,
paid access controls, or account restrictions.

## Resources

- CLI harness: `agent-harness/`
- Migration initializer: `scripts/init_skill.py`
- Compatibility script: `scripts/yt_dlp_downloader.py`
- Official usage notes: `references/official-usage.md`
