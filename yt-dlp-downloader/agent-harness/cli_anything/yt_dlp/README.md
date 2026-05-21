# cli-anything-yt-dlp

Agent-native CLI-Anything harness for the official `yt-dlp` executable.

## Install

```bash
cd ~/.agents/skills/yt-dlp-downloader/agent-harness
pip install -e .
```

When the whole skill has just been copied to a new machine, prefer the bundled
initializer from the skill root:

```bash
python3 scripts/init_skill.py --json
python3 scripts/init_skill.py --json --bootstrap-yt-dlp
```

## Core Commands

```bash
cli-anything-yt-dlp system status
cli-anything-yt-dlp --json system status
cli-anything-yt-dlp raw -- --version
cli-anything-yt-dlp options search cookies
cli-anything-yt-dlp inspect probe "https://example.com/video"
cli-anything-yt-dlp download --playlist-mode single "https://example.com/video"
```

Run `cli-anything-yt-dlp` without a subcommand to enter the REPL.

## Design

- `raw -- <args>` mirrors official `yt-dlp` behavior without harness defaults.
- Structured commands use safer agent defaults: `--ignore-config`, explicit JS
  runtime selection, MP4 merge preference, and `after_move:filepath`.
- The default structured output directory is platform-aware: macOS checks
  `~/影片`, then `~/Movies`; Linux checks `~/视频`, `~/Videos`, then `~/影片`;
  Windows checks `~/Videos`, `~/视频`, then `~/影片`.
- The harness never reimplements extractors. It invokes the official executable.
