# Epic Status Contract

## Formal BMAD Epic Status Values

Only these values are valid formal Epic statuses:

- `backlog`
- `in-progress`
- `done`

Only these values are valid formal retrospective statuses:

- `optional`
- `done`

Only these values are valid formal story statuses within Epic tracking:

- `backlog`
- `ready-for-dev`
- `in-progress`
- `review`
- `done`

No custom pipeline runtime outcome may be written into `development_status[...]`.

## Status Ownership

### Standard BMAD skills

- `bmad-create-story`
  - may move the Epic from `backlog` to `in-progress` when the first story is created
  - may move stories to `ready-for-dev`
- `bmad-dev-story`
  - may move stories into `in-progress`
  - may move stories to `review`
- `bmad-retrospective`
  - may move `epic-X-retrospective -> done`

### Pipeline extension layer

- `bmad-story-pipeline`
  - may move `review -> done`
- `bmad-epic-pipeline`
  - may move `epic-X -> done`

These are extension-layer finalize actions, but they still write only BMAD-standard formal status values.

## Runtime Outcomes vs Formal Status

These are pipeline runtime outcomes, not formal Epic or story statuses:

- `needs-clarification`
- `blocked-preflight`
- `blocked-execution`

They may appear in:
- aggregate results
- progress checkpoints
- evidence summaries
- run ledgers

They must not appear in:
- `development_status[epic-X]`
- `development_status[story-key]`
- story top-level `Status:`

## Formal Status While Paused or Blocked

If an Epic queue pauses for clarification or stops on a blocked story:

- keep `epic-X` at its current BMAD formal status (typically `in-progress`)
- keep the current story at whatever formal BMAD status the standard skills last wrote
- do not downgrade or invent a special pause / blocked formal status
