# yt-dlp official usage notes

This file is a compact fact sheet for the `yt-dlp-downloader` skill. It keeps only the parts of the official docs that affect implementation.

## Primary sources

- Repository: <https://github.com/yt-dlp/yt-dlp>
- README: <https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/README.md>
- Installation wiki: <https://raw.githubusercontent.com/wiki/yt-dlp/yt-dlp/Installation.md>
- Supported sites: <https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/supportedsites.md>
- FAQ: <https://github.com/yt-dlp/yt-dlp/wiki/FAQ>

## Facts used by this skill

### Installation

Official installation guidance includes:

```bash
python3 -m pip install -U "yt-dlp[default]"
```

Nightly installation guidance includes:

```bash
python3 -m pip install -U --pre "yt-dlp[default]"
```

### Dependencies that matter here

The README says these are highly recommended:
- `ffmpeg`
- `ffprobe`
- `yt-dlp-ejs`
- a supported JavaScript runtime such as `deno`, `node.js`, `bun`, or `QuickJS`

The README also explicitly states:
- `ffmpeg`/`ffprobe` are required for merging separate audio/video streams and for many post-processing tasks
- what you need is the **ffmpeg binary**, not the unrelated Python package named `ffmpeg`
- `yt-dlp-ejs` plus a JS runtime is required for full YouTube support
- recent yt-dlp behavior may still need an explicit `--js-runtimes RUNTIME[:PATH]` selection when `deno` is not the runtime in use

### URL input

The CLI usage form is:

```text
yt-dlp [OPTIONS] [--] URL [URL...]
```

So the skill can pass one or more URLs directly.

For batch files, yt-dlp also supports:

```text
-a, --batch-file FILE
```

This skill does not use batch files by default because direct URL arguments are simpler for agent-driven use.

### Config isolation

The README documents:

```text
--ignore-config
```

This skill always passes `--ignore-config` to avoid user/global config from silently changing behavior.

### Cookies and login state

The README documents:

```text
--cookies-from-browser
```

On Linux, Chromium-based browser cookie decryption may require `secretstorage` for keyring access. Browser cookies are optional and should only be used when the user explicitly wants logged-in content.

### Playlist control

The README documents:
- `--no-playlist`
- `--yes-playlist`
- `--download-archive FILE`
- `--max-downloads NUMBER`

The FAQ recommends `--download-archive` to avoid redownloading items that were already downloaded from a playlist.

This is why the skill uses archive files for large playlists.

### Output paths and filenames

The README documents:
- `-P, --paths [TYPES:]PATH`
- `-o, --output [TYPES:]TEMPLATE`
- `-O, --print [WHEN:]TEMPLATE`

The README also warns that post-processing can change the final filename, and recommends:

```text
--print after_move:filepath
```

This is why the skill reports final file paths from `after_move:filepath` instead of guessing.

### Merge container choice

The README documents:

```text
--merge-output-format FORMAT
```

Supported merge containers include: `avi`, `flv`, `mkv`, `mov`, `mp4`, and `webm`.

This skill prefers MP4 when a merge is needed, but does not force unnecessary remux/transcode when yt-dlp downloads a single file that is already complete.

### Platform support reality

`supportedsites.md` lists many built-in extractors, but the same file warns that:
- not all listed sites are guaranteed to work
- websites change constantly
- the only reliable way to check support is to try

That means the skill must report actual probe/download results, not make fake guarantees.

## Local implementation notes

These are implementation decisions for this skill, not upstream API guarantees:

- try a managed venv first to avoid polluting the system interpreter
- if Ubuntu/Debian blocks venv bootstrapping because `python3-venv` or `ensurepip` is missing, fall back to:

```bash
python3 -m pip install --user --break-system-packages -U "yt-dlp[default]"
```

- when a JS runtime is available, pass `--js-runtimes` explicitly so YouTube probing/downloading does not rely on defaults

### Xiaohongshu

The skill should treat Xiaohongshu as "try it, but do not promise stability".

Reason:
- yt-dlp has extractor support in the codebase
- but real-world extraction can fail because of anti-bot changes, CAPTCHA, or site-side response changes

So the correct behavior is to attempt the download, then surface extractor and stderr details if it fails.
