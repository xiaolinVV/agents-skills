# Worker Result Contract

Every step worker must return a compact, structured result. Do not return only prose.

## Required Fields

```json
{
  "step": "qa",
  "story_id": "6.1",
  "story_key": "6-1-example-story",
  "cycle": 1,
  "result": "needs-fix",
  "blocking": true,
  "retryable": true,
  "summary": "前端 E2E 发现 2 个阻断问题",
  "artifacts": {
    "summary_path": ".../qa-summary-2026-03-28T14-33-00+0800.md",
    "findings_path": ".../qa-findings-2026-03-28T14-33-00+0800.md"
  },
  "metrics": {
    "blocking_findings": 2,
    "major_findings": 0,
    "minor_findings": 1
  },
  "next_hint": "dev",
  "clarification_scope": null,
  "clarification_prompt": null,
  "resume_step": null
}
```

## Required Clarification Fields

When `result = needs-clarification`, these fields must be non-null:

- `clarification_scope`
- `clarification_prompt`
- `resume_step`

The summary artifact for such a result should normally be a `needs-clarification-*.md` file.

## Allowed `result` Values

Only these values are valid:

- `passed`
- `needs-fix`
- `needs-clarification`
- `blocked`
- `skipped`

No other synonyms or free-form statuses are allowed.

## Step-Specific Allowed Results

- `create`: `passed | needs-clarification | blocked | skipped`
- `validate`: `passed | needs-clarification | blocked`
- `dev`: `passed | needs-clarification | blocked`
- `qa`: `passed | needs-fix | needs-clarification | blocked | skipped`
- `review`: `passed | needs-fix | needs-clarification | blocked | skipped`

## Result Meanings

### `passed`
The step completed successfully and the pipeline may move forward.

### `needs-fix`
The step completed with actionable findings that should route back to `dev`.

Use only when the problem is real, attributable to the current story, and suitable for an automatic repair loop.

### `needs-clarification`
The step found a high-impact ambiguity that needs a short user answer, but execution can continue once that answer is provided.

This is a recoverable pause state, not a hard block.

### `blocked`
The step could not produce a trustworthy gate decision.

Examples:
- missing or broken prerequisite state
- framework/tooling failure that prevents reliable evaluation
- incomplete review outcome
- ambiguity that cannot be resolved safely within the current execution mode

### `skipped`
The step was intentionally not executed for a valid, explicit reason.

`skipped` is mainly expected for:
- `create` when the story already exists and create is not needed
- `qa` when the story is clearly docs-only or has no executable test surface

A `skipped` result must still produce a written summary.

## Language Rules

- the `summary` field should be concise and human-readable in `document_output_language`
- worker-written Markdown summaries and findings must use `document_output_language`
- machine-oriented field names remain stable English identifiers

## Metrics Guidance

Include only metrics relevant to the step.

Examples:
- `create`: files created/updated
- `validate`: must-fix count
- `dev`: files modified, tasks completed
- `qa`: tests passed/failed, blocking/major/minor findings
- `review`: critical/high/medium/low counts

## Artifact Rules

Every worker must write at least one timestamped summary artifact.

If findings exist, write a separate findings artifact.

Artifact paths should live under:
- `{implementation_artifacts}/evidence/story-{{story_id}}/`

## Controller Interpretation

The controller must use structured fields, not prose, to decide what happens next.

Required controller behavior:
- `needs-fix` from QA or review -> go to `dev`
- `needs-clarification` -> pause current story and request clarification, or escalate to `blocked-preflight` in unattended mode
- `blocked` -> stop immediately
- `skipped` -> only continue if that step type allows it
- `passed` -> advance normally
