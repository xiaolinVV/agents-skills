# Quickstart

## Fastest way to start a new batch

Empty batch:

```bash
python3 scripts/start_batch.py \
  --roster-file /path/to/roster.txt \
  --batch-root /tmp
```

Directly from a zip screenshot archive:

```bash
python3 scripts/start_batch.py \
  --roster-file /path/to/roster.txt \
  --zip-file /path/to/screenshots.zip \
  --batch-root /tmp
```

This creates a folder like:

```txt
/tmp/xhs-batch-20260324-200000/
├── roster.txt
├── state.json
├── images-manifest.json   # zip mode only
├── next-steps.txt
├── images/
└── judged/
```

The state file also stores:
- roster hash
- roster group count
- raw roster snapshot text

If you started from zip:
- `images-manifest.json` stores stable image order and absolute paths
- `images/` keeps the zip's relative folder structure
- `next-steps.txt` will recommend parallel sharding when extracted image count is 20 or more

If the roster has risky names:
- `roster-lint.txt` will be created
- batch creation still succeeds
- warnings mean “review this before fuzzy matching”, not “these names were auto-merged”

## Recommended daily workflow

1. Put the confirmed roster text into `roster.txt`.
2. Start a fresh batch with `start_batch.py`, optionally with `--zip-file`.
3. Judge screenshots visually one by one.
4. Save one JSON payload per image into `judged/`.
5. Include `image_path` in the payload whenever possible so duplicate detection can fingerprint the file.
6. Update the state with `update_counts.py`.
7. Re-render whenever the user asks for:
   - 合计
   - 名单顺序版
   - 只要非零项
   - 提交版
8. Export a deliverable pack when the batch is done.

## Large zip batches

If zip import produces 20+ images:
- use `images-manifest.json` to split work into 5-10 image shards
- let subagents judge shards in parallel
- keep `state.json` single-writer only
- apply payloads serially with `update_counts.py`

## Roster risk review

If `roster-lint.txt` exists:
- read it before you start fuzzy matching
- keep similar-looking names separate unless the roster explicitly groups them in quotes
- when in doubt, require a visible active heart **and** a unique mapping

## Multi-batch workflow

When the user finishes 第一批 / 第二批 / 第三批, merge them into one total state:

```bash
python3 scripts/merge_batches.py \
  --state-files /tmp/batch1/state.json /tmp/batch2/state.json /tmp/batch3/state.json \
  --output-file /tmp/all-batches/merged.json \
  --session-name all-batches
```

Important:
- Merge only batches built from the same roster version.
- If the roster changed, keep the batches separate or explicitly re-run older batches with the new roster.

Then export with a preset:

```bash
# 名单顺序版（带 0）
python3 scripts/render_report.py --state-file /tmp/all-batches/merged.json --preset roster

# 纯提交版（带 0）
python3 scripts/render_report.py --state-file /tmp/all-batches/merged.json --preset submit

# 纯提交版（只保留非 0）
python3 scripts/render_report.py --state-file /tmp/all-batches/merged.json --preset submit-nonzero
```

## Export a delivery pack

```bash
python3 scripts/export_delivery_pack.py \
  --state-file /tmp/all-batches/merged.json \
  --output-dir /tmp/all-batches/delivery \
  --name total \
  --only-nonzero-submit
```

This writes:
- `total-summary.txt`
- `total-roster.txt`
- `total-compact.txt`
- `total-submit.txt`
- `total-submit-nonzero.txt`
- `total-meta.json`
- `total-state.json`

## If you only want the shortest guide

Read `references/cheatsheet.md`.

## Good prompts to use with this skill

- 按小红书点赞验收 skill 来做
- 新开一批小红书点赞统计
- 用名单顺序版导出这批结果
- 导出提交版
- 把第一批和第二批合并成总计
- 给我导出整套交付包
- 重新开始这一批，但沿用同一份名单
- 直接用 zip 压缩包新开一批
