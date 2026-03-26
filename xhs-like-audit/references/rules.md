# XHS Like Audit Rules

## Business rules

1. Count only entries with an active heart.
2. Match names only after confirming the active heart.
3. Treat quoted multi-line roster blocks as one alias group.
4. Merge all aliases in the same group into one canonical count.
5. Quoted blocks are the only hard merge rule; similar-looking names outside the same quoted block stay separate unless the roster is manually fixed.
6. Default to level-2 cautious confirmation (`二级谨慎确认`): allow fuzzy matching only when the visible name still maps uniquely to exactly one roster group.
7. Do not count entries that are too ambiguous to trust.
8. Prefer under-counting over over-counting.

## Batch and roster rules

- The logic is stable, but the roster may change between batches.
- Every batch must keep its own roster snapshot.
- Each state file stores `roster_hash`, `roster_group_count`, and the raw roster snapshot text.
- Only merge batches that come from the same roster version.
- If roster versions differ, do not merge directly.

## Duplicate-image rules

- Prefer to include `image_path` in each judged payload.
- When `image_path` is present and points to a file, `update_counts.py` computes a SHA-256 fingerprint.
- If the same fingerprint already exists in the batch, the update is rejected unless the operator intentionally replaces the original image judgment.
- `merge_batches.py` also rejects duplicate fingerprints across batches.

## Edge-case guidance

### Count
- `红蓝霸霸（又想改色版）` -> `红蓝霸霸`
- `小知乐（备孕中）` -> `小知乐✨（备孕中）` when the rest of the context is consistent
- truncated aliases that uniquely map to one roster group
- minor emoji or punctuation variation when the underlying name still uniquely identifies one roster group

### Do not count
- active hearts on accounts outside the roster
- inactive or unclear hearts
- prefix-only matches that could refer to different bloggers
- near-duplicate names that live in different roster groups unless the visible name uniquely resolves to one group
- overly cropped or blurry names
- conflicts where two roster groups could plausibly match the same visible fragment
- cases where the visible author line and active heart may belong to different partially shown cards

## Roster lint guidance

- Use `scripts/lint_roster.py` or `start_batch.py` to surface risky roster entries before counting.
- Treat lint as warning-only by default.
- Fix the roster with quoted blocks when two names are truly the same blogger.
- Do not let lint warnings silently change counting semantics.

## Batch discipline

- Use one state file per batch.
- Record one judged payload per image.
- Replace an image payload only when correcting an earlier judgment.
- Re-render reports from JSON instead of hand-editing summary text.
- For large batches, parallelize image judgment only; keep `state.json` updates single-writer and serial.
