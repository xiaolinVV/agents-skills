# BMAD Story Pipeline Workflow

## Goal

Drive a single BMAD story from its current implementation state to the next valid gate, and only mark it `done` after QA and code review have both cleared.

## Initialization

Load config from `{project-root}/_bmad/bmm/config.yaml` and resolve:

- `communication_language`
- `document_output_language`
- `planning_artifacts`
- `implementation_artifacts`
- `project_context` if present

Derived paths:

- `sprint_status` = `{implementation_artifacts}/sprint-status.yaml`
- `evidence_root` = `{implementation_artifacts}/evidence/story-{{story_id}}`

Language rules:

- all human-readable pipeline summaries and findings Markdown must use `document_output_language`
- the lightweight `pipeline-run-*.yaml` ledger keeps stable machine-oriented keys

## Formal Status Contract

Apply `references/status-contract.md`.

Hard rules:

- only BMAD standard status values may be written into story files and `sprint_status`
- pipeline runtime outcomes such as `needs-clarification`, `blocked-preflight`, and `blocked-execution` are **not** formal story statuses
- runtime outcomes may appear in progress, evidence, and ledgers, but never in `Status:` or `development_status[...]`

## Execution Interaction Modes

### Interactive mode (default)

Use interactive mode when the current session can ask the user follow-up questions and continue after the answer arrives.

### Unattended mode (explicit)

Use unattended mode only when the user explicitly wants hands-off execution, for example a sleep / overnight run.

Rules:
- unattended mode must not wait indefinitely for clarification
- if a step needs user clarification and no safe continuation exists, write clarification evidence and stop as `blocked-preflight`
- do not guess a default answer just to keep the queue moving

## Invocation Modes

### Normal mode

Use the normal mode when the user directly invokes this skill for a single story.

### Embedded Epic mode

When invoked internally by `bmad-epic-pipeline`:

- a story id must already be explicit
- skip autonomous story discovery dialogue
- do not wrap the whole story run in an extra story-level worker
- keep the same gate logic and step ordering
- still use fresh **step-level** workers for create / validate / dev / qa / review when worker tooling exists
- preserve the same step-level progress checkpoints; Epic mode must not suppress story-level progress output
- return a structured story-level aggregate result back to the epic controller

The structured embedded result must include at least:
- `story_id`
- `story_key`
- `result`
- `final_status`
- `cycle_count`
- `current_or_final_step`
- `evidence_root`
- `summary_path`
- `git_sync` summary
- `clarification_scope` when applicable
- `clarification_prompt` when applicable
- `resume_step` when applicable

## Story Selection

### Accepted inputs

- `X-Y` (example: `6-1`)
- `X.Y` (example: `6.1`)
- Story file path

### No explicit input

Read `sprint_status` from top to bottom and auto-select in this order:

1. first story with status `backlog`
2. else first story with status `ready-for-dev`
3. else first story with status `in-progress`

Never auto-select a story already in `review`. Ask the user to specify it explicitly.

## Current-State Entry Rules

- `backlog` -> start with `create`
- `ready-for-dev` -> start with `validate`
- `in-progress` -> start with `dev`
- explicit `review` story -> start with `qa` unless the story is clearly docs-only or has no executable test surface

Reruns must rely on the current story file state and `sprint_status`, not on any previous pipeline ledger.

## Step Execution Model

Use a **fresh worker** for each step whenever subagent/worker tools are available.

Worker rules:

- one step per worker
- serial execution only
- pass only the minimum required context
- worker output must follow `references/worker-contract.md`
- worker-written Markdown summaries and findings must use `document_output_language`
- never let QA or review workers repair code directly; fixes always flow back to `dev`

If worker tooling is unavailable, emulate a fresh worker by re-reading only the required files and not reusing large prior outputs.

## Progress and Checkpoints

Apply `references/progress-contract.md`.

Requirements:

- emit a run-start checkpoint before the first logical step
- emit a standardized step progress block after each completed step
- emit a retry checkpoint whenever execution loops back from QA or Review to Dev
- emit a clarification checkpoint whenever execution pauses for user input
- emit a clarification-resume checkpoint when execution resumes after user input
- emit a standardized failure block when the story stops in `blocked-preflight` or `blocked-execution`
- in embedded Epic mode, keep these story-level checkpoints visible; Epic mode may add queue checkpoints around them but must not replace them

## Repo / Framework / QA Detection

Before `qa`, and earlier if needed, apply `references/autodetection.md`.

Requirements:

- infer code-bearing repos from the story file first
- detect existing test frameworks from the affected repos
- reuse the same story-first repo detection when selecting post-finalize git sync targets
- default QA provider is `bmad-qa-generate-e2e-tests` (Quinn)
- only switch to a TEA/Test Architect path if the user explicitly requests it **and** a matching skill is actually installed
- if multiple equally plausible repo or framework candidates remain, stop and ask the user

## Step Definitions

### Step `create`

Run a fresh worker instructed to use **`bmad-create-story` in Create mode** for the target story.

Expected use:
- create the story file if it does not exist
- preserve BMAD-native status movement from `backlog` toward `ready-for-dev`
- write a timestamped create summary under `evidence_root` in `document_output_language`

### Step `validate`

Run a fresh worker instructed to use **`bmad-create-story` in Validate Story mode** for the same story.

Rules:
- `validate` is a gate, not a repair step
- if it does not pass, stop with `blocked-preflight`
- write a timestamped validate summary under `evidence_root` in `document_output_language`

### Step `dev`

Run a fresh worker instructed to use **`bmad-dev-story`** for the target story file.

Rules:
- preserve BMAD-native movement into `in-progress` and then `review`
- if review follow-ups already exist, let `bmad-dev-story` consume them naturally
- use story file debug log / completion notes as the primary dev evidence source unless extra evidence files are explicitly needed

### Step `qa`

Run a fresh worker instructed to use the active QA provider.

Default provider:
- **`bmad-qa-generate-e2e-tests`**

Rules:
- tests must be written inside the affected code repo, never to workspace root `/tests`
- frontend tests belong in the detected frontend repo
- backend tests belong in the detected backend repo/module
- if the story has no executable test surface, return `skipped` with a written summary explaining why
- QA findings and summaries must be written to timestamped evidence files under `evidence_root` in `document_output_language`

### Step `review`

Run a fresh worker instructed to use **`bmad-code-review`** scoped to the current story.

Rules:
- stay in the current engine family
- fresh context is required
- if review produces fixable High/Medium/Blocking findings, return `needs-fix` and route back to `dev`
- review summaries and findings written under `evidence_root` must use `document_output_language`

## Clarification Handling

A step should return `needs-clarification` when:

- a high-impact ambiguity remains
- the ambiguity can be resolved by a short user answer
- the story can continue safely once that answer is provided

A clarification result is **not** the same as a hard block and is never a formal story status.

Required behavior:

- write a timestamped `needs-clarification-*.md` summary under `evidence_root`
- include `clarification_scope`, `clarification_prompt`, and `resume_step` in the structured result
- preserve the current BMAD formal story status while paused

Mode-specific behavior:

- standalone interactive story run:
  - ask the user the required clarification
  - once answered, resume the same story from `resume_step`
- embedded Epic interactive run:
  - return `needs-clarification` to the Epic controller
  - let the Epic controller pause the queue and own the user interaction
- unattended mode:
  - do not wait for an answer
  - convert the pause into `blocked-preflight` after writing clarification evidence

## Retry / Loop Policy

- start `cycle = 0`
- default `retry_limit = 3`

Transitions:

- `create: passed|skipped -> validate`
- `create: needs-clarification -> pause current story`
- `create: blocked -> blocked-preflight`
- `validate: passed -> dev`
- `validate: needs-clarification -> pause current story`
- `validate: blocked -> blocked-preflight`
- `dev: passed -> qa`
- `dev: needs-clarification -> pause current story`
- `dev: blocked -> blocked-execution`
- `qa: passed|skipped -> review`
- `qa: needs-fix -> cycle + 1 -> dev`
- `qa: needs-clarification -> pause current story`
- `qa: blocked -> blocked-execution`
- `review: passed -> finalize`
- `review: needs-fix -> cycle + 1 -> dev`
- `review: needs-clarification -> pause current story`
- `review: blocked -> blocked-execution`

If `cycle` would exceed `retry_limit`, stop with `blocked-execution` and report the unresolved gate.

## Finalize

Only the pipeline controller may execute the final `review -> done` transition.

Before finalizing, verify:

- latest `validate` passed if validation was required
- latest `dev` finished cleanly
- latest `qa` is `passed` or an explicit `skipped` with reason
- latest `review` is `passed`
- no unresolved `Review Follow-ups (AI)` remain in the story
- story is currently in `review`

Then:

1. update story top-level `Status:` to `done`
2. update the matching `development_status` entry in `sprint_status` from `review` to `done`
3. write a timestamped `final-summary-*.md` under `evidence_root` in `document_output_language`
4. write a timestamped lightweight `pipeline-run-*.yaml` ledger under `evidence_root`
5. perform automatic git sync using `references/git-sync.md`

The ledger is audit evidence only. It must not become a second source of truth for resume behavior.

## Automatic Git Sync

After a successful finalize, the pipeline should automatically attempt repo sync.

Rules:

- only sync story-attributable dirty repos
- never include unrelated dirty files or unrelated dirty repos
- commit subject must explicitly include `[story-id]`, even if branch naming does not provide it automatically
- push failure must not roll story state back from `done`
- final summary and pipeline ledger must record git sync success/failure and next actions

## Stop Conditions

Observable runtime outcomes may be one of:

- `done`
- `needs-clarification`
- `blocked-preflight`
- `blocked-execution`

These runtime outcomes are not formal BMAD story statuses.

Use `needs-clarification` only for interactive, recoverable pauses.

Use `blocked-preflight` when:

- story identity cannot be determined reliably
- repo/framework autodetection is ambiguous and cannot be resolved inside the current execution model
- validation fails
- unattended execution hits a clarification requirement

Use `blocked-execution` when:

- QA cannot produce a trustworthy result
- review cannot produce a trustworthy result
- retry limit is exceeded
