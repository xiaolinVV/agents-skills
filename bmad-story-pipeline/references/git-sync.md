# Git Sync Rules

Use this reference only after the story has already passed Finalize.

## Purpose

Automatically commit and push the current story's finished changes without mixing in unrelated workspace noise.

## Default Behavior

After the pipeline marks the story `done`, it should attempt automatic git sync.

Rules:
- sync only story-attributable dirty repos
- never sweep every dirty repo in the workspace
- never include unrelated dirty files from the same repo silently
- one repo -> one commit -> one push attempt

## Repo Selection

Select repos in this order:

1. repos named by the story `File List`
2. repos implied by story `References` / `Dev Notes`
3. repos containing current dirty files that are attributable to the story

If a repo is dirty but its dirty paths cannot be tied confidently to the story, do not auto-commit it.
Report it as skipped or ask the user.

If multiple attributable dirty repos remain, sync all of them.

## Safe Staging Rule

Before using any repo-level sync helper, compare:

- all dirty tracked/untracked paths in the repo
- the subset of paths confidently attributable to the current story

Behavior:

- if **all** dirty paths in the repo are attributable to the story, repo-level staging is allowed
- if the repo contains a mix of story and non-story dirty paths, do **not** use a repo-wide stage-all flow
- in mixed cases, either:
  - stage only the story-attributable paths manually, then commit/push, or
  - skip that repo and report the ambiguity

Never silently commit unrelated dirty files just because they share the same repo.

## Commit Message Rule

The commit subject must explicitly include the story id, even if branch naming does not expose it.

Required format:

`type(scope): [story-id] 中文一句话`

Example:

`feat(companion): [6.1] 完成桌面壳启动骨架与验证收口`

## Scope Derivation Rule

Default scope priority:

1. stable repo responsibility label already inferred by the pipeline
2. repo basename, normalized to a short lowercase scope
3. fallback generic scope such as `story`

Do not leave scope empty.

## Preferred Implementation

Prefer the existing `git-quick-sync` capability when available, but only when its staging behavior is safe for the current repo state.

Recommended flow per repo:

1. inspect dirty paths and story-attributable paths
2. choose safe staging strategy
3. derive or override the final subject so `[story-id]` is guaranteed
4. commit
5. push to current branch upstream

If `git-quick-sync` can safely handle the repo and can auto-generate a compliant BMAD subject, reuse it.
If not, override the subject explicitly or fall back to manual path-scoped git commands.

## Push Failure Policy

Push failure is a git sync problem, not a story gate failure.

If commit succeeds but push fails:
- keep the story `done`
- report which repo failed to push
- record the error and next action in the final summary and pipeline ledger
- do not roll the story back to `review`

## Final Reporting

The final summary should include a git sync section with:
- synced repos
- skipped repos
- commit subjects
- push success / failure per repo
- exact next-step commands when manual recovery is needed
