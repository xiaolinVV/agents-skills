---
name: bmad-story-pipeline
description: Use when executing or resuming one BMAD story through its standard create, validate, dev, QA, and review gates in a single orchestrated flow, especially when QA or code review findings may require automatic fix loops before the story can be marked done.
---

# BMAD Story Pipeline

Orchestrate one BMAD story without inventing a second development methodology. This skill is a thin controller over the existing BMAD implementation skills.

## Required Loading

1. Read `./workflow.md` fully before acting.
2. Read `./references/status-contract.md` before interpreting or writing any story / epic state.
3. Read `./references/autodetection.md` before choosing repos, test frameworks, QA provider, or git sync targets.
4. Read `./references/worker-contract.md` before spawning any worker or interpreting worker results.
5. Read `./references/git-sync.md` before any automatic commit / push behavior.
6. Read `./references/progress-contract.md` before emitting progress or retry checkpoints.

## When to Use

Use this skill when the user wants one command to drive a full BMAD story lifecycle or to resume a story already in the BMAD implementation loop.

Use it for Story-level orchestration only.

Do **not** use it for direct Epic batch execution; that belongs to `bmad-epic-pipeline`, which reuses this skill in embedded mode.

## Core Rules

- Preserve BMAD's native intermediate states. Do not rewrite `bmad-create-story` or `bmad-dev-story` behavior.
- Use only BMAD standard formal status values in story and sprint-status files.
- Use the **current engine only**. Do not hand review or QA to another model family.
- Run steps **serially**. Never run create, validate, dev, QA, review, or git sync in parallel.
- Prefer a fresh worker for every step. If worker tools are unavailable, emulate fresh context by reloading only the minimum required files.
- Human-readable evidence Markdown must follow `document_output_language`. Keep machine-friendly ledger field names stable.
- Emit standardized progress and retry checkpoints using `references/progress-contract.md`.
- On ambiguity, ask. Do not guess between equally plausible repo, framework, test, or git-sync targets.
- The pipeline owns only the final `review -> done` transition and the post-finalize git sync summary.
