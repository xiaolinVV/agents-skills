# Story Status Contract

## Formal BMAD Story Status Values

Only these values are valid formal story statuses:

- `backlog`
- `ready-for-dev`
- `in-progress`
- `review`
- `done`

No custom pipeline runtime outcome may be written into story `Status:` or `sprint_status.development_status`.

## Status Ownership

### Standard BMAD skills

- `bmad-create-story`
  - may move the story to `ready-for-dev`
  - may move the Epic from `backlog` to `in-progress` when the first story is created
- `bmad-dev-story`
  - may move `ready-for-dev -> in-progress`
  - may move `in-progress -> review`

### Pipeline extension layer

- `bmad-story-pipeline`
  - may move `review -> done`
  - must not invent a new formal status

## Runtime Outcomes vs Formal Status

These are pipeline runtime outcomes, not formal story statuses:

- `needs-clarification`
- `blocked-preflight`
- `blocked-execution`

They may appear in:
- worker results
- aggregate results
- progress checkpoints
- evidence summaries
- pipeline ledgers

They must not appear in:
- story top-level `Status:`
- `sprint_status.development_status[...]`

## Formal Status While Paused

If the pipeline pauses for clarification, keep the latest BMAD formal status unchanged.

Typical examples:
- before create completes: `backlog`
- after create / validate, before dev starts: `ready-for-dev`
- during active dev or review-follow-up reentry: `in-progress`
- after dev completes and during qa / review / finalize: `review`
