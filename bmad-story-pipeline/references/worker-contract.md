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
  "next_hint": "dev"
}
```

## Allowed `result` Values

Only these values are valid:

- `passed`
- `needs-fix`
- `blocked`
- `skipped`

No other synonyms or free-form statuses are allowed.

## Step-Specific Allowed Results

- `create`: `passed | blocked | skipped`
- `validate`: `passed | blocked`
- `dev`: `passed | blocked`
- `qa`: `passed | needs-fix | blocked | skipped`
- `review`: `passed | needs-fix | blocked | skipped`

## Result Meanings

### `passed`
The step completed successfully and the pipeline may move forward.

### `needs-fix`
The step completed with actionable findings that should route back to `dev`.

Use only when the problem is real, attributable to the current story, and suitable for an automatic repair loop.

### `blocked`
The step could not produce a trustworthy gate decision.

Examples:
- missing or broken prerequisite state
- ambiguous target selection
- framework/tooling failure that prevents reliable evaluation
- incomplete review outcome

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
- `blocked` -> stop immediately
- `skipped` -> only continue if that step type allows it
- `passed` -> advance normally
