# cli-anything-yt-dlp Test Plan

## Test Inventory Plan

- `test_core.py`: unit coverage for option parsing, command construction, path parsing, archive keys, result envelopes, session state, and platform detection.
- `test_full_e2e.py`: subprocess coverage for the installed CLI, compatibility shim, migration initializer, and a local HTTP download through the real `yt-dlp` backend.

## Unit Test Plan

- `core.options`: parse `yt-dlp --help` sections and option rows; search options by text.
- `core.results`: create stable JSON envelopes for success and error results.
- `core.session`: create named session directories, save/load JSON state, append history.
- `core.jobs`: build structured download commands without losing current skill defaults.
- `utils.yt_dlp_backend`: detect macOS app browsers, parse final paths from `after_move`, build JS runtime args, and preserve raw passthrough behavior.

## E2E Test Plan

- Validate `cli-anything-yt-dlp --help` and `--json system status` from a subprocess.
- Validate `cli-anything-yt-dlp --json raw -- --version` invokes the official executable.
- Validate old `scripts/yt_dlp_downloader.py preflight --json` still returns the old command name.
- Validate `scripts/init_skill.py --json --dry-run` exposes deterministic migration steps.
- Download a generated tiny MP4 from a local HTTP server and verify the final file path exists.

## Realistic Workflow Scenarios

- **Preflight and download**: inspect local dependencies, then download a simple URL with structured defaults.
- **Raw mirror**: pass arbitrary official `yt-dlp` arguments through without harness defaults.
- **Compatibility mode**: old skill commands keep working while the implementation lives in the harness.

## Test Results

Command:

```bash
CLI_ANYTHING_FORCE_INSTALLED=1 python3 -m pytest -q
```

Result:

```text
...............                                                          [100%]
15 passed in 23.86s
```

## Coverage Notes

- Covered installed CLI resolution, JSON system status, raw passthrough, legacy shim, migration initializer dry-run, option parsing, session state, macOS browser detection, and a real local HTTP MP4 download through official `yt-dlp`.
- External sites such as YouTube and Xiaohongshu are intentionally not used in tests because anti-bot behavior would make the suite nondeterministic.
