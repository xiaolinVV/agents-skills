#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SYNC_SCRIPT="$SCRIPT_DIR/sync_iterm2_ssh_to_codex.py"

PREVIEW_ONLY=0
ASSUME_YES=0
PRUNE_MISSING=0
JSON_OUTPUT=0
ALIAS_MAP=""
ITERM2_PLIST=""
TARGET=""
STATE=""

usage() {
  cat <<'USAGE'
Usage:
  sync-now.sh [options]

Default behavior:
  1. Run a dry-run preview
  2. If running in a TTY, ask for confirmation
  3. Write changes only after confirmation

Options:
  --preview            Only show dry-run preview, do not write
  --yes                Skip confirmation and write after preview
  --prune              Delete stale tracked entries missing from iTerm2
  --json               Show preview in JSON format
  --alias-map PATH     Alias map JSON passed to the Python sync script
  --iterm2-plist PATH  Override iTerm2 plist path
  --target PATH        Override target ssh-config.toml path
  --state PATH         Override sync state file path
  -h, --help           Show this help message

Examples:
  ./scripts/sync-now.sh
  ./scripts/sync-now.sh --yes
  ./scripts/sync-now.sh --preview --json
  ./scripts/sync-now.sh --yes --prune
  ./scripts/sync-now.sh --alias-map references/alias-map.example.json --yes
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --preview)
      PREVIEW_ONLY=1
      shift
      ;;
    --yes)
      ASSUME_YES=1
      shift
      ;;
    --prune)
      PRUNE_MISSING=1
      shift
      ;;
    --json)
      JSON_OUTPUT=1
      shift
      ;;
    --alias-map)
      ALIAS_MAP="${2:-}"
      [[ -n "$ALIAS_MAP" ]] || { echo "error: --alias-map requires a path" >&2; exit 1; }
      shift 2
      ;;
    --iterm2-plist)
      ITERM2_PLIST="${2:-}"
      [[ -n "$ITERM2_PLIST" ]] || { echo "error: --iterm2-plist requires a path" >&2; exit 1; }
      shift 2
      ;;
    --target)
      TARGET="${2:-}"
      [[ -n "$TARGET" ]] || { echo "error: --target requires a path" >&2; exit 1; }
      shift 2
      ;;
    --state)
      STATE="${2:-}"
      [[ -n "$STATE" ]] || { echo "error: --state requires a path" >&2; exit 1; }
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

COMMON_ARGS=(sync)
if [[ -n "$ITERM2_PLIST" ]]; then
  COMMON_ARGS+=(--iterm2-plist "$ITERM2_PLIST")
fi
if [[ -n "$TARGET" ]]; then
  COMMON_ARGS+=(--target "$TARGET")
fi
if [[ -n "$STATE" ]]; then
  COMMON_ARGS+=(--state "$STATE")
fi
if [[ -n "$ALIAS_MAP" ]]; then
  COMMON_ARGS+=(--alias-map "$ALIAS_MAP")
fi
if [[ "$PRUNE_MISSING" -eq 1 ]]; then
  COMMON_ARGS+=(--prune-missing)
fi

PREVIEW_ARGS=("${COMMON_ARGS[@]}" --dry-run)
if [[ "$JSON_OUTPUT" -eq 1 ]]; then
  PREVIEW_ARGS+=(--json)
fi

WRITE_ARGS=("${COMMON_ARGS[@]}" --write)

echo '== Preview ==' >&2
"$PYTHON_BIN" "$SYNC_SCRIPT" "${PREVIEW_ARGS[@]}"

if [[ "$PREVIEW_ONLY" -eq 1 ]]; then
  exit 0
fi

if [[ "$ASSUME_YES" -ne 1 ]]; then
  if [[ ! -t 0 ]]; then
    echo >&2
    echo 'Non-interactive shell detected. Re-run with --yes to apply changes.' >&2
    exit 0
  fi
  echo >&2
  read -r -p 'Apply these changes? [y/N] ' answer
  case "$answer" in
    y|Y|yes|YES)
      ;;
    *)
      echo 'Aborted.' >&2
      exit 0
      ;;
  esac
fi

echo >&2
if [[ "$PRUNE_MISSING" -eq 1 ]]; then
  echo '== Applying sync with prune ==' >&2
else
  echo '== Applying sync ==' >&2
fi
"$PYTHON_BIN" "$SYNC_SCRIPT" "${WRITE_ARGS[@]}"
