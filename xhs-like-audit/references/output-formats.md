# Output Formats

## Per-image payload for update_counts.py

Prefer this shape:

```json
{
  "image": "batch1-001.jpg",
  "image_path": "/tmp/xhs-batch/images/batch1-001.jpg",
  "matches": [
    {
      "canonical": "红蓝霸霸",
      "display_name": "红蓝霸霸（又想改色版）",
      "liked": true,
      "counted": true,
      "notes": "fuzzy suffix ignored"
    },
    {
      "canonical": "小知乐✨（备孕中）",
      "display_name": "小知乐（备孕中）",
      "liked": true,
      "counted": true
    }
  ],
  "notes": "other visible cards were inactive or out of roster"
}
```

If `image_path` exists, the updater computes a fingerprint and rejects duplicates automatically.

## Quick batch start

```bash
python3 scripts/start_batch.py \
  --roster-file /path/to/roster.txt \
  --zip-file /path/to/screenshots.zip \
  --batch-root /tmp
```

When started from zip, `images-manifest.json` records stable image order and extracted file paths for sharding.

## Merge multiple batches

```bash
python3 scripts/merge_batches.py \
  --state-files /tmp/batch1/state.json /tmp/batch2/state.json \
  --output-file /tmp/merged/state.json \
  --session-name total
```

Batches must share the same roster version.

## Render examples

### Summary

```bash
python3 scripts/render_report.py --state-file /tmp/xhs-batch-1.json --preset summary
```

Output:

```txt
合计：101组
```

### Ordered roster with zeros

```bash
python3 scripts/render_report.py --state-file /tmp/xhs-batch-1.json --preset roster
```

Output style:

```txt
【丸子是个肉丸子 / 丸子麻麻育儿记📝 / 丸子甜不甜】 5
恒宝麻麻 0
红蓝霸霸 5
```

### Ordered non-zero only

```bash
python3 scripts/render_report.py --state-file /tmp/xhs-batch-1.json --preset compact
```

### Plain submit version with zeros

```bash
python3 scripts/render_report.py --state-file /tmp/xhs-batch-1.json --preset submit
```

Output style:

```txt
丸子是个肉丸子 / 丸子麻麻育儿记📝 / 丸子甜不甜 5
恒宝麻麻 0
红蓝霸霸 5
```

### Plain submit version, non-zero only

```bash
python3 scripts/render_report.py --state-file /tmp/xhs-batch-1.json --preset submit-nonzero
```

## Delivery pack export

```bash
python3 scripts/export_delivery_pack.py \
  --state-file /tmp/xhs-batch-1.json \
  --output-dir /tmp/xhs-batch-1/delivery \
  --name batch1 \
  --only-nonzero-submit
```

Exported files:
- `batch1-summary.txt`
- `batch1-roster.txt`
- `batch1-compact.txt`
- `batch1-submit.txt`
- `batch1-submit-nonzero.txt` (optional)
- `batch1-meta.json`
- `batch1-state.json`
