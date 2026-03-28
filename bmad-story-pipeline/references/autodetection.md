# Autodetection Rules

Use autodetection first. Do not require a project profile file.

## BMAD Truth Sources

Detect these first:

- `_bmad/bmm/config.yaml`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/project-context.md` if present
- target story file under `implementation_artifacts`

If these cannot be found reliably, stop and report the missing BMAD state.

## Story-First Repo Detection

Infer affected repos from the story before scanning the entire workspace.

Priority order:

1. Story `File List`
2. Story `Dev Notes`
3. Story `References`
4. existing changed files that clearly belong to the story
5. workspace scan heuristics

If the story already names concrete file paths, map those paths back to repo roots and prefer those roots over broad guessing.

The same story-first repo detection is reused for:
- QA target selection
- post-finalize git sync target selection

## Repo Heuristics

### Frontend repo candidates

Strong signals:
- `package.json`
- `src/`
- frontend framework dependencies or build scripts
- existing UI/E2E tests

### Java backend candidates

Strong signals:
- `pom.xml`
- `src/main/java`
- `src/test/java`

### Python service candidates

Strong signals:
- `pyproject.toml`
- `src/` or importable package layout
- `tests/`

## Test Framework Detection

Prefer existing frameworks already present in the affected repo.

Common frontend signals:
- Playwright
- Jest
- Vitest
- Cypress

Common backend/service signals:
- JUnit / Surefire / Mockito
- pytest

Do not invent a second parallel framework when a stable one already exists.

## QA Provider Detection

Default provider:
- `bmad-qa-generate-e2e-tests` (Quinn)

Only choose a TEA/Test Architect path when **both** are true:
- the user explicitly asks for it
- a matching skill is actually installed and available

Otherwise stay on Quinn.

## Docs-Only / No-Test-Surface Detection

A story may skip executable QA only when it is clearly docs-only or has no executable code surface.

Evidence for docs-only / no-test-surface may include:
- affected files are only documentation or planning artifacts
- no code-bearing repo is implicated by the story
- QA provider cannot identify a meaningful executable target after story-first detection

Even then, QA must still produce a timestamped summary explaining the skip.

## Story-Scoped Dirty Repo Selection

Use story evidence to limit automatic git sync.

Eligible repos must satisfy both:
- the repo is dirty now
- the repo is attributable to the current story from story-first detection

If multiple attributable dirty repos remain, sync all of them.

If a repo is dirty but the dirty paths cannot be tied confidently to the story, do **not** silently include it in automatic sync.
Treat that as unsafe / ambiguous and ask the user or report that repo as skipped from git sync.

If no attributable dirty repo remains after filtering, git sync becomes a reported skip, not a failure of story completion.

## Ambiguity Policy

If more than one repo, dirty repo set, or framework candidate remains equally plausible:

- stop
- present the candidates succinctly
- ask the user which target to use

Never silently pick one “best guess” when the evidence is tied.
