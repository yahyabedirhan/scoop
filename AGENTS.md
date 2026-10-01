# Scoop

`README.md` is the reference for what Scoop does, how it is used, the copy
modes, the install and reload workflow, and the `npm` commands. Read it first
and do not restate it here. Update it in the same commit whenever behavior
changes. `docs/scoop-v01.md` is the low-level design; `CHANGELOG.md` is the
version history, pre-release `0.0.x`.

## Layout

- `src/entries/` — the two build entry points, `content.ts` and `background.ts`.
- `src/lib/` — the logic: `inspector.ts` (hover, highlight, label),
  `dom-navigator.ts` (arrow-key traversal), `scooper.ts` (the copy itself),
  `modes/` (one module per copy mode), `scroll/`, `utils/`.
- `test/` — Vitest suites mirroring `src/lib/`.
- `.specs/` — numbered specs, `NN-<kebab-topic>.md`, one per feature increment.
  Written before the work and kept as the record of what was intended.
- `.handoff/` — session handoff documents, `YYYY-MM-DD-<kebab-topic>.md`. The
  `handoff` skill writes here, not to a temp directory. Keep them committed.

## Working rules

Run `npm run typecheck` and `npm test` before calling a change done. Loading the
built extension is manual and cannot be verified from here, so say so rather
than claiming a browser check happened.

Four behaviors have each already been the subject of a bug fix. Treat them as
regression-prone and cover them with tests when touching nearby code.

- Copies contain page content only, with Scoop's own overlay nodes excluded and
  any temporary change it made to the page undone first, including when copying
  `<body>` or `<html>`.
- Nothing leaves the machine. No network calls, no analytics, no storage beyond
  the remembered copy mode.
- Inspect mode is per-tab, and every exit path tears the overlay down at once.
- Traversal skips non-visible tags such as `head`, `script`, and `style`.

## Writing style

Applies to code comments, docs, specs, changelog entries, and commit messages.

- Do not fabricate. When something is unknown, mark it unknown or ask.
- Mark unfinished work with an explicit `TODO:` so a later session can resume.
- Do not overuse the em dash (—). Default to restructuring the sentence: split
  it in two, use a subordinate clause, reorder, or use a comma. Reach for one
  only when a sentence genuinely calls for that exact break.
- Avoid a colon introducing a list of items inside a prose sentence. Prefer a
  smoother clause or a separate sentence. Structural Markdown and metadata
  fields may still use colons.
- Match the comment density and idiom of the surrounding code.

## Git

Do not run `git add`, `git commit`, or `git stash` unless asked for that action.
Do not report uncommitted changes unless asked, or unless git status affects the
task at hand.

Commit messages use a conventional-commit prefix, are lowercase after it, and
carry a bulleted body explaining the change:

```text
feat: short imperative summary

- explanation 1
- explanation 2
```

Prefixes in use: `feat`, `fix`, `refactor`, `docs`, `chore`. Pick the one that
describes what the change does to the extension, not how much work it was. A
removal that changes behavior is still `refactor` only when the intent was
cleanup.

## Agent skills

Skills live in `.agents/skills/`, symlinked into `.claude/skills/`. All of them
are imported from upstream and tracked in `skills-lock.json`. **Do not modify
their content.** Update them only from upstream. To add one:

```bash
ln -s ../../.agents/skills/<skill-name> .claude/skills/<skill-name>
```

Stage the symlink itself, not the file inside it.

`CLAUDE.md` is a symlink to this file. Edit `AGENTS.md`.

### Issue tracker

Issues live in this repo's GitHub issues (`yahyabedirhan/scoop`), through the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default triage labels, each named after its role (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` at the root and ADRs in `docs/adr/`, both created when a term or decision is first settled. See `docs/agents/domain.md`.
