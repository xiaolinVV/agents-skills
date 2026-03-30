---
name: xhs-like-audit
description: Use when Claude needs to verify Xiaohongshu (小红书) like/heart screenshots against a roster, ingest screenshot batches from folders or zip 压缩包, do 名单核对 / 验收统计 / 批量图片统计, merge 第一批/第二批/总计 results, or output roster-order counts such as 名字后面跟数字.
---

# XHS Like Audit

Use this skill for roster-based Xiaohongshu like verification.

## Core rules

Apply these rules in order:

1. Treat the roster as the only source of truth for the current batch.
2. Treat every non-empty unquoted line as one standalone blogger.
3. Treat every quoted multi-line block as one blogger alias group.
4. Check whether the heart/like is visibly active first.
5. Only attempt name matching for entries with an active heart.
6. Default to level-2 cautious confirmation (`二级谨慎确认`): allow fuzzy matching only when the visible name still maps uniquely to exactly one roster entry or alias group.
7. Merge all aliases in the same quoted block into one canonical count.
8. Treat quoted blocks as the only hard merge rule; similar-looking names outside the same quoted block stay separate unless the human fixes the roster.
9. Prefer under-counting over risky over-counting when a name is too ambiguous.
10. Treat the roster as variable across batches; persist the roster snapshot inside each batch state.

## Workflow

### 1) Initialize a batch

Prefer `scripts/start_batch.py` for day-to-day use.

Example: start an empty batch workspace

```bash
python3 scripts/start_batch.py \
  --roster-file /path/to/roster.txt \
  --batch-root /tmp
```

Example: start a batch directly from a zip screenshot archive

```bash
python3 scripts/start_batch.py \
  --roster-file /path/to/roster.txt \
  --zip-file /path/to/screenshots.zip \
  --batch-root /tmp
```

This creates a ready-to-use batch folder with:
- copied `roster.txt`
- initialized `state.json`
- `images/` for raw screenshots or extracted zip contents
- `judged/` for per-image JSON payloads
- `next-steps.txt` with command reminders

When `--zip-file` is used, it also creates:
- `images-manifest.json` with stable image order and absolute paths
- extracted images inside `images/`, preserving relative folders from the zip

When the roster itself looks risky, it also creates:
- `roster-lint.txt` with warning-only findings such as cross-group near-duplicates or malformed names

Zip import rules:
- only common image files are extracted
- `__MACOSX/` and non-image junk are ignored
- unsafe paths such as absolute paths or `..` traversal are rejected
- if the zip has no supported images, batch creation fails instead of leaving a half-broken folder

Each state also stores:
- `roster_hash`
- `roster_group_count`
- `roster_snapshot_name`
- full raw roster snapshot text

Roster lint rules:
- quoted blocks are the only hard alias merge rule
- similar names outside the same quoted block are **not** auto-merged
- roster lint warnings do not block batch creation
- warnings are there to tell the operator where fuzzy matching may become dangerous

Use `scripts/reset_session.py` only when you want to initialize a state file directly without creating the extra batch structure.

### 2) Judge screenshots

For each screenshot or collage:
- inspect the image visually
- identify only entries whose heart is clearly active
- map each counted entry to a canonical roster group
- use level-2 cautious confirmation by default:
  - count exact matches
  - count fuzzy matches only when the visible name still maps uniquely to one roster group
  - move unclear or non-unique matches into notes instead of counting them
- ignore entries with inactive hearts
- ignore entries outside the roster
- ignore entries that are too ambiguous to trust

Hard order of operations:
1. confirm the heart is active
2. only then match the visible name
3. if the visible fragment could map to multiple roster groups, do not count it

### 2a) Parallelize large batches safely

When the batch is large (for example 20+ images) or the user explicitly asks to speed up processing:
- if the batch came from zip import, use `images-manifest.json` as the image source of truth for sharding
- split the batch into small shards, usually 5-10 images per shard
- use subagents via `sessions_spawn` to judge shards in parallel
- keep one shared roster and one shared batch root
- do **not** let multiple subagents write to the same `state.json` concurrently
- instead, have each subagent produce per-image JSON payloads only
- then let the main agent apply `scripts/update_counts.py` serially to the shared state file

Use this pattern:
1. main agent initializes the batch once
2. main agent assigns shard image paths from `images-manifest.json` and target judged filenames
3. subagents inspect images and write only judgment payload JSON
4. main agent runs `update_counts.py` one payload at a time
5. main agent renders the final report after all payloads are applied

Important:
- shared `state.json` is single-writer only
- parallelism is for image judgment, not for concurrent state updates
- if you need more detail, read `references/parallel.md`

### 3) Persist results

After judging a screenshot, write the resolved matches into the batch state with `scripts/update_counts.py`.

Use one JSON payload per image.

Prefer this payload shape:

```json
{
  "image": "image-01.jpg",
  "image_path": "/tmp/xhs-batch/images/image-01.jpg",
  "matches": [
    {
      "canonical": "红蓝霸霸",
      "display_name": "红蓝霸霸（又想改色版）",
      "liked": true,
      "counted": true,
      "notes": "suffix ignored as fuzzy match"
    }
  ],
  "notes": "other visible cards not counted"
}
```

Write it with:

```bash
python3 scripts/update_counts.py \
  --state-file /tmp/xhs-batch-1.json \
  --matches-file /tmp/image-01.json
```

If `image_path` exists, the updater computes a SHA-256 fingerprint and rejects duplicates automatically.

If the same image must be corrected later, use `--replace-image`.

### 4) Export results

Render the current batch with `scripts/render_report.py`.

Recommended presets:

```bash
# summary total only
python3 scripts/render_report.py --state-file /tmp/xhs-batch-1.json --preset summary

# 名单顺序版（带 0）
python3 scripts/render_report.py --state-file /tmp/xhs-batch-1.json --preset roster

# 紧凑版（只看非 0）
python3 scripts/render_report.py --state-file /tmp/xhs-batch-1.json --preset compact

# 提交版（纯名字 + 数字，带 0）
python3 scripts/render_report.py --state-file /tmp/xhs-batch-1.json --preset submit

# 提交版（纯名字 + 数字，只保留非 0）
python3 scripts/render_report.py --state-file /tmp/xhs-batch-1.json --preset submit-nonzero
```

Use roster-style output when the user asks for:
- 名单顺序版
- 名字后面跟数字
- 按名单顺序输出

Use submit-style output when the user asks for:
- 提交版
- 纯净版
- 只要名字和数字
- 可复制提交

### 5) Merge multiple batches safely

When the user has 第一批 / 第二批 / 第三批, merge them with `scripts/merge_batches.py`.

```bash
python3 scripts/merge_batches.py \
  --state-files /tmp/batch1/state.json /tmp/batch2/state.json /tmp/batch3/state.json \
  --output-file /tmp/merged/total.json \
  --session-name total
```

This validates roster compatibility, merges image judgments, recalculates counts, and creates one combined state file for final export.

Important:
- Merge only batches from the same roster version.
- If `roster_hash` or canonical order differs, do not merge directly.
- If the roster changed, keep batches separate or explicitly re-run old batches with the new roster.

### 6) Export a delivery pack

When the user wants a ready-to-hand-off result bundle, export with `scripts/export_delivery_pack.py`.

```bash
python3 scripts/export_delivery_pack.py \
  --state-file /tmp/merged/total.json \
  --output-dir /tmp/merged/delivery \
  --name total \
  --only-nonzero-submit
```

This writes a set of files such as:
- `total-summary.txt`
- `total-roster.txt`
- `total-compact.txt`
- `total-submit.txt`
- `total-submit-nonzero.txt`
- `total-meta.json`
- `total-state.json`

Use this when the user asks for:
- 导出整套交付包
- 给我一个提交文件夹
- 一次性导出所有版本

## State model

The batch state file stores:
- roster order
- alias groups
- roster version metadata
- per-image resolved matches
- image fingerprint when available
- canonical counts
- total valid groups

Use JSON state as the source of truth. Do not rely on long markdown find/replace logs as the only database.

## Matching guidance

Default matching mode: level-2 cautious confirmation (`二级谨慎确认`).

Count a match only when all of the following are true:
- the heart is visibly active
- the visible name can be mapped to a roster entry or alias group
- the mapping is specific enough to trust
- any fuzzy match is still unique across the whole roster

Count under level-2 cautious confirmation when:
- the name is exact
- the name is truncated but still uniquely identifies one roster group
- the visible difference is limited to emoji, brackets, pregnancy/breastfeeding suffixes, or minor punctuation/style variation

Do not count when:
- the heart is inactive or unclear
- the visible name is not on the roster
- the name only shares a vague prefix and could map to multiple people
- the screenshot is too cropped or blurry to support a reliable match
- the author line and heart area cannot be confidently tied to the same card

## Recommended defaults

- Use one state file per batch.
- Keep screenshot-level notes in the image payload.
- Include `image_path` whenever possible for duplicate-image protection.
- Run roster lint before large batches and read any warnings before judging screenshots.
- Re-render from JSON whenever the user asks for a new format.
- Prefer `--preset roster` for audit handoff.
- Prefer `--preset submit` for copy-ready submission.
- Prefer `--preset submit-nonzero` for concise delivery.
- Prefer `export_delivery_pack.py` when the user wants all formats at once.
- If you only need the shortest reminder, read `references/cheatsheet.md`.

## Resources

- For one-command batch initialization: `scripts/start_batch.py`
- For roster risk warnings without changing group semantics: `scripts/lint_roster.py`
- For merging multiple batches: `scripts/merge_batches.py`
- For delivery bundle export: `scripts/export_delivery_pack.py`
- For roster parsing and state initialization only: `scripts/reset_session.py`
- For roster parsing only: `scripts/parse_roster.py`
- For per-image count updates and duplicate protection: `scripts/update_counts.py`
- For export formats: `scripts/render_report.py`
- For rule explanations and edge cases: `references/rules.md`
- For quick start flow: `references/quickstart.md`
- For shortest reminder sheet: `references/cheatsheet.md`
- For payload and output examples: `references/output-formats.md`
- For parallel shard orchestration: `references/parallel.md`
- For a starter roster file: `assets/roster-template.txt`
