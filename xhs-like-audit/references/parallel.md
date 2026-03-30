# Parallel Processing for Large XHS Batches

Use this only when the batch is large or the user explicitly wants faster throughput.

## Goal

Speed up image judgment without corrupting the batch state.

## Safe rule

- Parallelize **judgment**
- Serialize **state updates**

Never let multiple subagents write to the same `state.json` at the same time.

## Recommended workflow

1. Main agent creates the batch once with `scripts/start_batch.py`
2. If zip import was used, main agent reads `images-manifest.json` and treats it as the source of truth for image order and paths
3. Main agent splits image paths into shards of 5-10 images
4. Main agent spawns one subagent per shard with `sessions_spawn`
5. Each subagent:
   - reads only its assigned images
   - judges them using the roster and current rules
   - writes one JSON payload per image into a shard-specific judged folder, or returns the payload text to the main agent
6. Main agent applies payloads to the shared state with `scripts/update_counts.py` **one by one**
7. Main agent renders the final report

When `start_batch.py` says the batch is large (20+ extracted images), follow this workflow by default.

## Why this matters

`update_counts.py` mutates shared state. Running it concurrently risks:
- lost updates
- conflicting writes
- duplicate handling mistakes
- hard-to-debug totals

## Shard sizing

Default: 5-10 images per subagent.

Use smaller shards when:
- images are hard to read
- multi-phone collages are common
- many names need fuzzy matching

Use larger shards when:
- screenshots are clean and consistent
- the layout is repetitive

## Prompt shape for subagents

Give each subagent:
- the roster snapshot or batch roster file path
- the exact image paths assigned to it
- the image index range or manifest slice used for the shard
- the current matching rule (`二级谨慎确认` when active)
- an output location or required JSON payload format
- a reminder: do not update shared `state.json`

## Merge discipline

After subagents finish:
- review payloads quickly for obvious conflicts
- apply them serially with `update_counts.py`
- only then compute totals or export reports

## Conflict rule

If two payloads appear to count the same image or the same file path twice:
- stop
- resolve duplication first
- then continue applying updates
