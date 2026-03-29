---
name: bmad-epic-pipeline
description: Use when delivering or resuming one BMAD Epic as a sequential queue of remaining story pipelines, especially when you want the Epic to stop on the first failed story, push each completed story immediately, and automatically mark the Epic done once all remaining stories succeed.
---

# BMAD Epic Pipeline

Batch one Epic by reusing `bmad-story-pipeline`. This skill is a queue controller, not a second story implementation workflow.

## Required Loading

1. Read `./workflow.md` fully before acting.
2. Read `./references/status-contract.md` before interpreting or writing any story / epic state.
3. Read `./references/queue-rules.md` before collecting or filtering the Epic queue.
4. Read `./references/aggregate-contract.md` before invoking or interpreting embedded story-pipeline results.
5. Read `./references/progress-contract.md` before emitting queue progress or stop checkpoints.
6. Read `./references/report-contract.md` before generating final Epic delivery reports.

## When to Use

Use this skill when the user wants to deliver the remaining stories of one Epic in order through the existing story pipeline.

Use it for Epic-level queue orchestration only.

Do **not** use it to replace `bmad-story-pipeline` for single-story work.

## Core Rules

- Reuse `bmad-story-pipeline`; do not duplicate create / validate / dev / QA / review logic here.
- Process stories strictly in ascending story-number order.
- Stop on the first failed story.
- Keep per-story git sync behavior inside the story pipeline; do not add a second Epic-wide commit phase.
- Auto-mark `epic-X` as `done` only when every story under that Epic is now `done`.
- Emit queue-level checkpoints using `references/progress-contract.md`.
- Use only BMAD standard formal story / Epic status values in persisted status fields.
- Generate a structured Epic delivery report using `references/report-contract.md`.
- Do not auto-run retrospective. Only report that retrospective is available.
