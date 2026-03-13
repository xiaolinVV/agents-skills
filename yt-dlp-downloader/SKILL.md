---
name: yt-dlp-downloader
description: Download one or more public video or audio URLs with yt-dlp, optionally using browser cookies for logged-in content. Use when the user gives links from sites supported by yt-dlp, asks to save videos into a local directory, wants playlist handling, or needs incremental batched downloads for large collections.
---

# YT-DLP Downloader

Use this skill to turn one or more URLs into downloaded media files on the local machine.

## Pitfalls already hit in real use

Record these and treat them as facts until reality proves otherwise:

- Ubuntu 24.04 style Python environments may reject normal pip installs with `externally-managed-environment`.
- Some machines also lack `python3-venv` / `ensurepip`, so a managed venv may fail before it starts.
- Recent yt-dlp + YouTube flows may still fail unless `--js-runtimes` is passed explicitly, even when `node` is already installed.
- Public YouTube downloads may hit `Sign in to confirm you’re not a bot`; in that case, switch to browser cookies instead of pretending the URL is bad.
- On Linux, Chrome/Chromium cookie decryption may fail unless the Python package `secretstorage` is installed.
- Xiaohongshu can work anonymously for some URLs and fail hard for others. Do not over-generalize from one success.

## Defaults

- Save files to `~/视频/yt-dlp` unless the user says otherwise.
- Prefer yt-dlp's best video + best audio selection: `-f bv*+ba/b`.
- Prefer MP4 when yt-dlp must merge streams: `--merge-output-format mp4`.
- Keep the original container when yt-dlp downloads a single ready-made file and no merge is needed.
- Ignore user/global yt-dlp config by always passing `--ignore-config`.
- If a supported JavaScript runtime exists, pass `--js-runtimes` automatically so YouTube does not silently degrade.
- Use `--print after_move:filepath` to report final paths after post-processing.
- For very large playlists, switch to archive-based batched downloads.

## Workflow

### 1. Check the machine first

Run:

```bash
python3 scripts/yt_dlp_downloader.py preflight
```

Use `preflight` to confirm:
- `yt-dlp` exists
- `ffmpeg` and `ffprobe` exist
- a JavaScript runtime exists for better YouTube support
- Chrome/Chromium/Firefox are available if the user wants browser cookies

If `yt-dlp` is missing, run:

```bash
python3 scripts/yt_dlp_downloader.py bootstrap --channel stable
```

If the user explicitly wants the nightly build, use `--channel nightly`.

Bootstrap behavior:
- try a managed virtual environment first
- if Ubuntu/Debian blocks that because `python3-venv` or `ensurepip` is missing, fall back to `pip install --user --break-system-packages`
- also install `secretstorage` so Chrome/Chromium cookies on Linux do not fail later

Do **not** pretend the environment is ready when `ffmpeg` is missing. Return the install hint instead.

### 2. Probe unclear URLs before downloading

Run `probe` when any of these are true:
- the user gave a playlist or channel/collection URL
- the platform support is unclear
- the user asked whether a site like Xiaohongshu currently works
- you need to estimate playlist size before downloading

Example:

```bash
python3 scripts/yt_dlp_downloader.py probe 'https://example.com/video'
```

`probe` returns extractor, title, playlist-like detection, and an estimated entry count when yt-dlp can provide it.

## Downloading

### Single or a few URLs

Use:

```bash
python3 scripts/yt_dlp_downloader.py download 'URL1' 'URL2'
```

### Force single-video behavior

If a URL may point to both a video and a playlist, and the user only wants the current item:

```bash
python3 scripts/yt_dlp_downloader.py download --playlist-mode single 'URL'
```

### Force playlist behavior

If the user explicitly says "download the whole playlist/合集/列表":

```bash
python3 scripts/yt_dlp_downloader.py download --playlist-mode playlist 'URL'
```

### Use browser cookies

Only use cookies when the user asks for logged-in content or age-restricted/private access.

Chrome:

```bash
python3 scripts/yt_dlp_downloader.py download --browser chrome 'URL'
```

On Linux, if Chrome/Chromium cookies are needed, make sure `preflight` shows `secretstorage: yes`. If not, run `bootstrap` again or install it manually.

Firefox:

```bash
python3 scripts/yt_dlp_downloader.py download --browser firefox 'URL'
```

Cookie file:

```bash
python3 scripts/yt_dlp_downloader.py download --cookies-file /path/to/cookies.txt 'URL'
```

Use either `--browser` or `--cookies-file`, never both.

## Large playlists and collections

When `probe` shows more than 100 items, or when the user clearly says the list is huge, let the script use incremental batched mode.

Behavior:
- create `OUTPUT_DIR/.archives/<playlist-key>.txt`
- reuse the archive on reruns to skip already-downloaded items
- download in chunks of 100 by default
- preserve final file paths from each chunk

This is the point: avoid redownloading hundreds of old items.

If needed, override the defaults:

```bash
python3 scripts/yt_dlp_downloader.py download \
  --chunk-size 50 \
  --huge-threshold 200 \
  --max-downloads 25 \
  'URL'
```

## Extra yt-dlp arguments

Use repeated `--extra-arg` values to pass through specific yt-dlp flags when the user explicitly needs them.

Example:

```bash
python3 scripts/yt_dlp_downloader.py download \
  --extra-arg=--sleep-interval \
  --extra-arg=5 \
  'URL'
```

Do not pile on random flags by default. Extra flags exist as an escape hatch.

## Failure handling

- If `ffmpeg` is missing, fail fast and return the install hint.
- If `probe` or `download` fails, return the extractor, stderr tail, and the exact final paths that were produced before failure.
- For YouTube, expect that public probing/downloading may still require cookies because of anti-bot checks even when `yt-dlp-ejs` and a JS runtime are installed.
- For Linux Chrome/Chromium cookies, expect a hard failure if `secretstorage` is missing. Fix that first instead of retrying blindly.
- For Xiaohongshu, state the truth: yt-dlp may have an extractor, but the site is unstable and frequently blocked by anti-bot or CAPTCHA.
- Do not claim fixed platform support if the extractor currently fails.

## Boundaries

- Download only content the user is authorized to download.
- Do not help bypass DRM, paid access controls, or account restrictions.
- Do not promise that any given site is stable just because yt-dlp lists it.

## Resources

- Script entrypoint: `scripts/yt_dlp_downloader.py`
- Official fact summary: `references/official-usage.md`
