# BMAD Epic Pipeline Workflow

## Goal

Deliver the remaining stories of one Epic by sequentially invoking `bmad-story-pipeline`, and automatically mark the Epic `done` after all remaining stories succeed.

## Initialization

Load config from `{project-root}/_bmad/bmm/config.yaml` and resolve:

- `communication_language`
- `document_output_language`
- `implementation_artifacts`
- `project_context` if present

Derived paths:

- `sprint_status` = `{implementation_artifacts}/sprint-status.yaml`
- `epic_evidence_root` = `{implementation_artifacts}/evidence/epic-{{epic_num}}`

Language rules:

- Epic human-readable summaries must use `document_output_language`
- Epic ledger files keep stable machine-oriented keys

## Formal Status Contract

Apply `references/status-contract.md`.

Hard rules:

- only BMAD standard status values may be written into story and Epic status fields
- runtime outcomes such as `needs-clarification`, `blocked-preflight`, and `blocked-execution` are queue-control results, not formal Epic statuses
- runtime outcomes may appear in progress, evidence, and ledgers, but never in `development_status[epic-X]`

## Execution Interaction Modes

### Interactive mode (default)

Use interactive mode when the current session can ask the user a question and continue the same Epic queue after the answer arrives.

### Unattended mode (explicit)

Use unattended mode only when the user explicitly asks for hands-off / overnight execution.

Rules:
- unattended mode must not wait for clarification
- if the current story returns `needs-clarification`, stop the Epic as `blocked-preflight`
- never guess clarification answers automatically

## Epic Selection

### Accepted inputs

- `X` (example: `6`)
- `epic-X` (example: `epic-6`)

### No explicit input

Read `sprint_status` from top to bottom and identify Epics that have at least one incomplete story.

Incomplete story statuses are defined in `references/queue-rules.md`.

Select the smallest Epic number that still has incomplete stories.

If no Epic has incomplete stories, report that there is no pending Epic queue to run.

## Queue Discovery

Apply `references/queue-rules.md`.

For the selected Epic:

1. collect all story keys matching `{epic_num}-Y-story-name`
2. exclude `epic-{epic_num}` and `epic-{epic_num}-retrospective`
3. split into:
   - `done stories`
   - `remaining stories`
4. sort remaining stories by story number ascending

Default queue scope:
- process only `backlog`, `ready-for-dev`, `in-progress`, and `review`
- skip stories already marked `done`

If no remaining stories exist:
- if `epic-{epic_num}` is already `done`, report Epic already complete and stop
- otherwise reconcile `epic-{epic_num}` to `done`, write Epic summary / ledger, and stop

## Preflight

Before starting the first story, perform queue preflight.

Required checks:

- `sprint_status` is readable and parsable
- every queued story id maps cleanly to one story key
- for queued stories already in `ready-for-dev`, `in-progress`, or `review`, the story file exists and is readable
- no queue ambiguity exists for story ordering or story-file resolution

If any of these checks fail, stop immediately with `blocked-preflight` before running any story.

## Progress and Queue Checkpoints

Apply `references/progress-contract.md`.

Requirements:

- emit an Epic queue-start checkpoint once the queue is known
- emit a queue checkpoint before each story starts
- emit a queue completion checkpoint after each successful story
- surface a lightweight current-story step summary while embedded story execution is active
- emit a queue pause checkpoint when the current story needs clarification
- emit a queue resume checkpoint when the Epic continues after clarification
- emit a queue stop checkpoint immediately when the Epic halts on a failed story

## Execution Model

The Epic controller owns the queue.

For each queued story, invoke `bmad-story-pipeline` in **embedded Epic mode**:

- pass the explicit story id
- do not let the story pipeline re-run interactive story selection
- do not add an extra story-level wrapper worker
- let the story pipeline keep its normal step-level fresh workers

Interpret the returned result using `references/aggregate-contract.md`.

## Story Loop

For each remaining story in ascending order:

1. invoke embedded `bmad-story-pipeline`
2. wait for the structured result
3. if result is `done`, continue to next story
4. if result is `needs-clarification`:
   - in interactive mode, pause the Epic queue, ask the clarification, and then resume the same story
   - in unattended mode, stop the Epic as `blocked-preflight`
5. if result is `blocked-preflight` or `blocked-execution`, stop the Epic immediately

The Epic controller must never continue past the first failed story.

## Git Behavior

Per-story git sync remains owned by `bmad-story-pipeline`.

Rules:

- do not add an Epic-wide commit / push phase
- Epic controller only aggregates each story's git sync result
- completed stories are expected to have already attempted their own finalize-time git sync

## Epic Finalize

If every remaining story completed successfully:

1. re-read `sprint_status`
2. verify every story under the Epic is now `done`
3. update `development_status[epic-{epic_num}] = done`
4. do **not** change `epic-{epic_num}-retrospective`
5. write:
   - `epic-summary-*.md` under `epic_evidence_root` in `document_output_language`
   - `epic-run-*.yaml` under `epic_evidence_root`
6. report that retrospective can be run separately

## Epic Summary Requirements

The human-readable Epic summary must include:

- Epic id and title if available
- skipped already-done stories
- stories executed in this run
- first failed story if the queue stopped early
- per-story final result
- per-story git sync outcome summary
- whether `epic-{epic_num}` was updated to `done`
- note that retrospective was not auto-run

## Stop Conditions

Observable runtime outcomes may be one of:

- `done`
- `blocked-preflight`
- `blocked-execution`

These runtime outcomes are not formal Epic statuses.

Stop immediately when:

- Epic selection is ambiguous
- queue discovery is ambiguous
- preflight fails
- any story returns a true blocking outcome
