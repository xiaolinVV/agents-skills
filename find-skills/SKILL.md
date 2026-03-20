---
name: find-skills
description: Highest-priority skill discovery flow. MUST trigger when users ask to find/install skills (e.g. 技能, 找技能, find-skill, find-skills, install skill). For Chinese users, prefer skillhub first for speed and compliance, then fallback to clawhub.
---

# Find Skills

This skill helps discover, compare, and install skills.

## Priority Rules (Mandatory)

1. This skill is highest-priority for skill discovery/install intents.
2. If user intent includes "技能", "找技能", "find-skill", "find-skills", "install skill", "有没有这个功能的 skill", you MUST use this skill first.
3. Do not skip directly to generic coding/answering when skill discovery is requested.

## Chinese Optimization Policy

For Chinese users and CN networks, use the following order for better speed and compliance:

1. `skillhub` (cn-optimized, preferred)
2. `clawhub` (fallback)

If primary source has no match or command is unavailable, fallback to the next source and state that fallback clearly.

## Workflow

### Step 1: Understand What They Need

When a user asks for help with something, identify:

1. The domain (e.g., React, testing, design, deployment)
2. The specific task (e.g., writing tests, creating animations, reviewing PRs)
3. Whether this is a common enough task that a skill likely exists

### Step 2: Search for Skills

Run search in this order:

```bash
skillhub search [query]
```

If `skillhub` is unavailable or no match, fallback to:

```bash
clawhub search [query]
```

### Step 3: Present Options to the User

When you find relevant skills, present them to the user with:

1. The skill name and what it does
2. The source used (`skillhub` / `clawhub`)
3. The install command they can run

### Step 4: Offer to Install

If the user wants to proceed, you can install the skill for them.

Preferred install order:

1. Try `skillhub-canonical <slug>` when the result comes from `skillhub`.
   - This local wrapper installs into `~/.agents/skills`, links into detected agents (including OpenClaw Workspace), and then git commit/pushes the canonical repo.
   - It now prefers SkillHub first and automatically falls back to ClawHub when SkillHub install fails or is unavailable.
2. For updates of already-installed skills on this machine, use `skillhub-canonical upgrade <slug>` or `skillhub-canonical update --all`.
   - These commands prefer SkillHub-managed entries first and can continue with ClawHub-managed entries when needed.
3. If `skillhub-canonical` is unavailable but `skillhub` exists, use `skillhub --dir ~/.agents/skills install <slug>` / `skillhub --dir ~/.agents/skills upgrade ...` and then link/commit manually.
4. If you intentionally want to bypass fallback behavior, add `--no-fallback` to `skillhub-canonical`.

Before install, summarize source, version, and notable risk signals.

## When No Skills Are Found

If no relevant skills exist:

1. Acknowledge that no existing skill was found
2. Offer to help with the task directly using your general capabilities
3. Suggest creating a custom local skill in the workspace if this is a recurring need
