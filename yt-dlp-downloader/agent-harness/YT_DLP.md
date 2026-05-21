# yt-dlp CLI-Anything Harness SOP

## Backend

The harness wraps the official `yt-dlp` executable. It does not copy extractor
logic or use private Python internals. The backend boundary is subprocess calls
plus structured command construction and JSON/error normalization.

## Data Model

- `DownloadJob`: structured download request with URLs, output directory,
  playlist mode, auth source, archive policy, and extra official arguments.
- `ResultEnvelope`: uniform command output for agents.
- `SessionStore`: lightweight state/history under
  `~/.local/share/cli-anything-yt-dlp`.
- `OptionCatalog`: runtime parse of `yt-dlp --help`, so upstream options are not
  duplicated manually.

## Command Strategy

- `raw -- <args>` mirrors official `yt-dlp` behavior without harness defaults.
- Structured commands add agent-safe defaults such as `--ignore-config`,
  explicit JS runtime selection, MP4 merge preference, archive handling, and
  `after_move:filepath` reporting.
- The legacy skill script stays as a shim for existing calls.
