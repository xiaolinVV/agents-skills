# Aggregate Result Contract

## Embedded Story Pipeline Result

When `bmad-epic-pipeline` invokes `bmad-story-pipeline` in embedded mode, it must receive a structured story-level result.

Minimum required shape:

```json
{
  "story_id": "6.2",
  "story_key": "6-2-control-plane-contract-reuse",
  "result": "done",
  "final_status": "done",
  "cycle_count": 0,
  "evidence_root": ".../evidence/story-6.2",
  "summary_path": ".../final-summary-2026-03-29T10-00-00+0800.md",
  "git_sync": {
    "synced_repos": ["discord-auth-companion"],
    "skipped_repos": [],
    "push_failures": []
  }
}
```

Valid `result` values for the Epic controller are:

- `done`
- `blocked-preflight`
- `blocked-execution`

The Epic controller must not infer success from prose alone.

## Epic Run Ledger

`epic-run-*.yaml` should keep stable machine-oriented keys.

Minimum fields:

- `epic_num`
- `run_timestamp`
- `outcome`
- `skipped_done_stories`
- `executed_stories`
- `failed_story` (nullable)
- `epic_status_updated_to_done`

Each executed story entry should include:
- `story_id`
- `story_key`
- `result`
- `summary_path`
- `git_sync`

## Controller Rules

The Epic controller should:
- continue only on `done`
- stop immediately on `blocked-preflight`
- stop immediately on `blocked-execution`
- aggregate per-story git sync results but never re-run git sync itself at Epic scope
