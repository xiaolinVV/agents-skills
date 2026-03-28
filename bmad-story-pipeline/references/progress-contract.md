# Story Progress Contract

## Purpose

Keep long-running story execution visible without bloating controller state.

## Canonical Step Units

Progress is tracked by logical story steps, not by internal tool chatter.

Canonical step orders by entry mode:

- `backlog` start: `create -> validate -> dev -> qa -> review -> finalize` (`6` steps)
- `ready-for-dev` start: `validate -> dev -> qa -> review -> finalize` (`5` steps)
- `in-progress` start: `dev -> qa -> review -> finalize` (`4` steps)
- explicit `review` start: `qa -> review -> finalize` (`3` steps)

## Required Checkpoints

### Run start checkpoint

Emit once before the first logical step, for example:

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Story Pipeline Started
   Story: 6.2
   Mode: normal | embedded-epic
   Plan: dev -> qa -> review -> finalize
   Cycle: 0/3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step completion checkpoint

Emit after every completed logical step:

```text
📊 Story Pipeline Progress: [2/5] 40%
   Story: 6.2
   Cycle: 0/3
   ✅ Step: qa
   Result: 关键验证通过
```

Requirements:
- show `[X/N]`
- show current story id
- show current cycle / retry count
- show step name and brief result

### Retry checkpoint

Emit whenever QA or Review routes back to Dev:

```text
🔁 Story Pipeline Retry
   Story: 6.2
   Trigger: review -> needs-fix
   Next: dev
   New Cycle: 1/3
```

### Failure checkpoint

Emit whenever the story stops in a blocking state:

```text
❌ Story Pipeline Failed
   Story: 6.2
   Step: qa
   Cycle: 2/3
   Outcome: blocked-execution
   Evidence: .../qa-summary-....md
```

## Embedded Mode Rule

In `embedded-epic` mode, story-level checkpoints must still be emitted.

Epic orchestration may add queue-level progress around them, but must not suppress story-level checkpoints.

## Controller Memory Rule

The controller should retain only the compact aggregate state needed to continue:
- story id
- current step
- cycle count
- final result
- summary/evidence paths

Do not retain full step prose in controller state when compact checkpoints and artifacts already exist.
