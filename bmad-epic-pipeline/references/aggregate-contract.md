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
  "current_or_final_step": "finalize",
  "cycle_count": 0,
  "evidence_root": ".../evidence/story-6.2",
  "summary_path": ".../final-summary-2026-03-29T10-00-00+0800.md",
  "git_sync": {
    "synced_repos": ["discord-auth-companion"],
    "skipped_repos": [],
    "push_failures": []
  },
  "clarification_scope": null,
  "clarification_prompt": null,
  "resume_step": null,
  "formal_story_status": "done",
  "qa_metrics": {
    "tests_total": 31,
    "tests_passed": 31,
    "tests_failed": 0,
    "qa_mode": "executable",
    "qa_skipped": false,
    "skip_reason": null
  },
  "delivery_summary": [
    "完成 profile service 与状态持久化"
  ]
}
```

Valid `result` values for the Epic controller are:

- `done`
- `needs-clarification`
- `blocked-preflight`
- `blocked-execution`

The Epic controller must not infer success from prose alone.

## Clarification Contract

When `result = needs-clarification`, the embedded story result must include:

- `clarification_scope`
- `clarification_prompt`
- `resume_step`
- `summary_path` pointing to the clarification evidence summary
- `formal_story_status` showing the unchanged BMAD formal story status while paused

Interactive Epic behavior:
- pause the queue
- ask the clarification
- resume the same story after the answer

Unattended Epic behavior:
- do not wait
- treat the queue as `blocked-preflight`
- stop and report the clarification need as the stop reason

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
- `qa_totals`
  - `tests_total`
  - `tests_passed`
  - `tests_failed`
  - `stories_skipped_qa`

Each executed story entry should include:
- `story_id`
- `story_key`
- `result`
- `summary_path`
- `git_sync`
- `formal_story_status`
- `qa_metrics`
- `delivery_summary`

## Controller Rules

The Epic controller should:
- continue only on `done`
- pause and wait on `needs-clarification` in interactive mode
- stop immediately on `blocked-preflight`
- stop immediately on `blocked-execution`
- aggregate per-story git sync results but never re-run git sync itself at Epic scope
- never persist runtime outcome names into formal story or Epic status fields
