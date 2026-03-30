# Epic Queue Rules

## Story Key Scope

Include only keys matching the pattern:

- `{epic_num}-Y-story-name`

Exclude:

- `epic-{epic_num}`
- `epic-{epic_num}-retrospective`

## Included Story Statuses

The default remaining queue contains only stories with status:

- `backlog`
- `ready-for-dev`
- `in-progress`
- `review`

Stories already in `done` are not re-executed.

## Sorting

Sort remaining stories by numeric story number ascending.

Examples:
- `6-2-*` before `6-10-*`
- compare the numeric `Y`, not simple string order

## Already-Done Stories

Done stories should be recorded as:
- `skipped-already-done`

They are included in Epic reporting but not re-run.

## No Remaining Stories Case

If an Epic has no remaining stories:

- if `epic-{epic_num}` is already `done`, report Epic already complete and do nothing else
- if all stories are `done` but the Epic status is not yet `done`, reconcile the Epic status to `done` and write Epic-level evidence

Do not re-run already done stories by default.

## Preflight File Expectations

For queued stories already beyond `backlog`:
- the story file must exist
- it must be readable
- it must map cleanly to a single story artifact

For `backlog` stories:
- absence of a story file is acceptable, because `create` is expected to generate it
