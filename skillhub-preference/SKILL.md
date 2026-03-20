---
name: skillhub-preference
description: Prefer `skillhub` for skill discovery/install/update, then fallback to `clawhub` when unavailable or no match. Use when users ask about skills, 插件, or capability extension.
---

# Skillhub Preference

Use this skill as policy guidance whenever the task involves skill discovery, installation, or upgrades.

## Policy

1. Try `skillhub` first for search/install/update.
2. For local installation on this machine, prefer `skillhub-canonical <slug>` so the skill lands in `~/.agents/skills`, gets linked into detected agents (including OpenClaw Workspace), and is git committed/pushed.
3. For updates of installed SkillHub skills on this machine, prefer `skillhub-canonical upgrade <slug>` or `skillhub-canonical update --all`.
4. `skillhub-canonical` should prefer SkillHub first and automatically fallback to ClawHub when SkillHub install/upgrade is unavailable or fails, unless `--no-fallback` is explicitly used.
5. Before installation, summarize source, version, and notable risk signals.
6. Do not claim exclusivity; both registries are allowed.
7. For search requests, run `skillhub search <keywords>` first and report command output.
