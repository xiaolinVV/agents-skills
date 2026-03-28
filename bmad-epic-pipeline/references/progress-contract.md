# Epic Progress Contract

## Purpose

Show long-running Epic queue execution clearly without forcing the Epic controller to retain every detail from every story step.

## Queue Units

Epic progress is tracked by **story queue position**, not by flattening every internal story step into one global percentage.

Primary unit:
- current story position `[i/N]`

Secondary information:
- completed stories count
- skipped already-done stories count
- current queue state
- current story step summary

## Required Checkpoints

### Queue start checkpoint

Emit once after queue discovery and preflight succeed, for example:

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☕ Epic Pipeline Started
   Epic: 6
   Remaining Stories: 8
   Skipped Already Done: 1
   Order: 6.2 -> 6.3 -> 6.4 -> ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Story start checkpoint

Emit before invoking each story pipeline:

```text
☕ Epic Pipeline Progress: [2/8]
   Epic: 6
   Current Story: 6.3
   Completed Stories: 1
   Skipped Already Done: 1
   Queue State: running
```

### Embedded story subprogress line

While the embedded story pipeline is active, surface a lightweight subprogress line derived from story-level checkpoints, for example:

```text
↳ Story 6.3 Step 3/5 | Cycle 1/3 | qa
```

This is an echo / summary of story progress, not a second independent story state machine.

### Story completion checkpoint

Emit after each successful story:

```text
✅ Epic Queue Checkpoint
   Epic: 6
   Story: 6.3
   Queue Position: [2/8]
   Result: done
```

### Queue stop checkpoint

Emit immediately when execution stops on the first failed story:

```text
❌ Epic Pipeline Stopped
   Epic: 6
   Failed Story: 6.4
   Queue Position: [3/8]
   Outcome: blocked-execution
   Summary: .../final-summary-....md
```

## Controller Memory Rule

The Epic controller should retain only per-story aggregate results:
- story id / key
- final result
- summary path
- git sync summary

It should not retain full step prose from every embedded story once that information has been checkpointed and written to evidence.
