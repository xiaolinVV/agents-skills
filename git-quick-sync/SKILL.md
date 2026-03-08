---
name: git-quick-sync
description: Automatically generate Chinese Conventional Commit messages and execute git add/commit/push plus quick pull sync for single repositories and multi-repo workspaces. Use when users ask to quickly commit and push changes, batch sync nested repos, or pull updates from tracking upstream or a specified remote like upstream.
---

# Git Quick Sync

## Overview

Use this skill to standardize and automate Git sync workflows:
- detect single repo vs multi-repo workspace
- use safe staging by default (`--stage-mode auto`)
- generate Conventional Commit message in Chinese
- commit and immediately push to current branch upstream
- pull updates from tracking upstream or a specified remote branch

## Default behavior

- Commit format: `type(scope): 中文一句话`
- BMad-aware commit format: when current repo is in a BMAD workspace and branch can extract a `story-id`, use `type(scope): [story-id] 中文一句话`
- Message language: Chinese (type remains English)
- Repo discovery: auto detect
  - if current path is a Git repo: treat as single repo
  - else scan child directories for `.git`
- Multi-repo commit selection: commit all dirty repos by default
- Stage mode default for this skill: `auto`
  - if staged changes already exist: preserve current index and do not auto-add more files
  - otherwise stage tracked changes only (`git add -u`)
  - untracked files are left out by default; use `--stage-mode all` only when user explicitly wants a full snapshot
- Push target: current branch upstream (`git push`)
- Pull strategy default: `merge`
- Dirty repo pull default: auto stash + pull + stash pop
- Multi-repo pull default: pull all repos that have upstream
- No upstream during pull: skip with warning (`skipped=true`, `skip_reason=no_upstream`)
- Reporting default: detailed per-repo summary; `--verbose` only adds fully expanded lists such as staged files and updated commits

## BMad detection

- Purpose: prefer BMAD commit convention only when current work is likely part of a BMAD task, instead of blindly changing all commits in a BMAD workspace
- Detection signals:
  - workspace contains `_bmad` or `_bmad-output`
  - `_bmad-output/project-context.md` contains BMAD Git/Story rules
  - current branch can extract a `story-id` (for example `feat/story-123-add-login`)
- Commit mode rule:
  - if BMAD context is detected and `story-id` is available: generate BMAD-aware subject
  - if BMAD context is detected but `story-id` is missing: fall back to normal Conventional Commit subject and note the fallback in body/summary
  - if BMAD context is not detected: use normal Conventional Commit subject

## Workflow

1. Discover candidate repositories.
2. Filter repositories based on action (dirty for commit, has-upstream for pull).
3. For each repository:
   - commit flow: summarize staged changes -> commit -> push
   - pull flow: optional auto stash -> pull -> optional stash restore
4. Report per-repo result; continue even if one repo fails.

## Commands

Use `scripts/git_quick_sync.py` for all operations.

### 1) Scan repos

```bash
python3 scripts/git_quick_sync.py scan \
  --root /path/to/workspace \
  --mode auto \
  --dirty-only \
  --json
```

Modes:
- `auto`: single repo if current root is a repo, otherwise scan child repos
- `single`: require root itself to be a repo
- `multi`: always scan child repos

### 2) Summarize one repo

```bash
python3 scripts/git_quick_sync.py summarize \
  --repo /path/to/repo \
  --stage-mode auto \
  --json
```

This command stages first, then returns:
- staged files
- name/status list
- shortstat summary
- suggested subject/body
- BMAD detection result / story-id / commit mode

### 3) Commit and push one repo

```bash
python3 scripts/git_quick_sync.py apply \
  --repo /path/to/repo \
  --stage-mode auto \
  --json
```

Optional overrides:
- `--subject "feat(scope): ..."`
- `--body "line1\nline2"`
- `--stage-mode all` when user explicitly asks to include untracked/new files in one shot
- `--verbose` (show fully expanded staged file list)

If subject/body are omitted, suggested values are used.

### 4) Pull updates for one repo

```bash
python3 scripts/git_quick_sync.py pull \
  --repo /path/to/repo \
  --strategy merge \
  --json
```

Framework upstream remote example:

```bash
python3 scripts/git_quick_sync.py pull \
  --repo /path/to/repo \
  --remote upstream \
  --remote-branch master \
  --json
```

Remote behavior:
- if `--remote` is omitted: pull tracking upstream (for example `origin/master`)
- if `--remote` is set and `--remote-branch` is omitted: use current local branch name
- default pull strategy is `merge`
- default output already includes pull result, updated commit count, latest updated commit, and next-action hint
- add `--verbose` to show `head_before/head_after` and full updated commit list

### 5) Batch apply for dirty repos

```bash
python3 scripts/git_quick_sync.py scan \
  --root /path/to/workspace \
  --mode auto \
  --dirty-only \
  --json |
jq -r '.[].repo_path' |
while read -r repo; do
  python3 scripts/git_quick_sync.py apply --repo "$repo" --stage-mode auto --json
done
```

### 6) Batch pull for repos with upstream

```bash
python3 scripts/git_quick_sync.py scan \
  --root /path/to/workspace \
  --mode auto \
  --json |
jq -r '.[] | select(.has_upstream==true) | .repo_path' |
while read -r repo; do
  python3 scripts/git_quick_sync.py pull --repo "$repo" --strategy merge --json
done
```

## Failure handling rules

- If merge/rebase/cherry-pick/revert state exists, fail fast for that repo.
- If unresolved conflicts exist, fail fast for that repo.
- In `auto` mode, untracked files are not staged automatically; surface a clear hint instead of silently committing them.
- If there is no staged change, `apply` returns success with `commit_created=false`.
- If commit succeeds but push fails, return:
  - `commit_created=true`
  - `push_succeeded=false`
  - actionable error text
- If pull has no upstream, return skip with:
  - `skipped=true`
  - `skip_reason=no_upstream`
- If pull remote does not exist, return skip with:
  - `skipped=true`
  - `skip_reason=remote_not_found`
- If pull succeeds but stash restore fails, return:
  - `pull_succeeded=false`
  - `stash_restore_succeeded=false`
  - actionable error text

## Message convention reference

Read `references/commit-conventions.md` when you need:
- exact type classification order
- BMAD subject/body rules and fallback behavior
- subject/body template details
- multi-repo message constraints
