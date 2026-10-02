# Handoff: Scoop documentation system, changelog, and versioning reset

Date: 2026-09-05
Project: `personal-projects/scoop/` (inside the job-search vault, tracked there, no nested git repo)

Continues from [`2026-09-05-docs-consolidation-and-readme.md`](./2026-09-05-docs-consolidation-and-readme.md).
Both jobs in that handoff (consolidate the specs, refresh the README) are now
done, plus follow-on work the user asked for during the session.

## Status: done, uncommitted

Everything below is on disk, not committed. `npm run typecheck`, `npm test`
(86 passing), and `npm run build` are all clean. The user has not asked for a
commit yet. When they do: commit only `personal-projects/scoop/` paths (the repo
has unrelated staged changes under `interview-prep/`).

The one thing still open from earlier handoffs is unchanged: the real-browser
check (clipboard write, click suppression, the digit `4` / Markdown output on a
live page) cannot be done from here. Manual step for the user.

## What changed this session

Documentation and versioning only. No feature or bugfix work. The concrete
edits are visible in the working tree; do not re-derive them. Summary:

- **New `docs/scoop-v01.md`**, a standalone description of the final project
  state (behavior + low-level design), replacing the plan to rewrite
  `.specs/00-scoop.md` in place. It was briefly at `.specs/scoop.md`, then the
  user moved it to `docs/` and reframed it as a doc, not a spec.
- **`.specs/00`–`03` left as historical records.** An earlier draft added
  "superseded by" banners to each; the user rejected that. They are back to
  their committed content, with one correction: `.specs/03` status
  `proposed` → `implemented` (it was stale; commit `87a2e3f` shipped it).
- **New `CHANGELOG.md`**, Keep a Changelog format. Kept lean, no links out to
  the other docs.
- **Versioning reset to pre-release.** Nothing is released. `manifest.json`,
  `package.json`, `package-lock.json` all moved `1.4.0` → `0.0.5`. The changelog
  milestones are `0.0.1`–`0.0.5`. `0.1.0` is the intended first real release.
- **JSDoc cleanup**, removed session-scoped phrasing ("shipped this pass",
  "from the design session", "the old fallback is gone") from `src/lib/` so
  comments describe the code as it stands. Touched `robber.ts`,
  `scroll/margin-scroller.ts`, `scroll/scroller.ts`, `modes/modes.ts`,
  `modes/plain-text.ts`, `modes/markdown.ts`.
- **Handoff filename consistency**, `00-handoff-scoop-extension.md` and
  `01-architecture.md` renamed to the dated `YYYY-MM-DD-<topic>.md` scheme
  (the vault convention, see root `CLAUDE.md`) as
  `2026-09-03-initial-extension.md` and `2026-09-03-architecture-review.md`.
  The one cross-reference in `2026-09-05-typescript-rewrite.md` was updated.
- One pre-existing em dash removed from `package.json`'s `description`.

## The documentation system (the rules the user settled on)

This is the part to carry forward. Four artifacts, each with one job. They do
**not** cross-link into a web; each stands on its own.

```text
personal-projects/scoop/
├── README.md              # what it is + how to use it, for someone landing on the repo
├── CHANGELOG.md           # what changed, version by version
├── docs/
│   └── scoop-v01.md       # how the final state works: behavior + low-level design
└── .specs/
    └── 00..03             # the design record: decisions + rejected alternatives,
                           #   one file per stage of the work, frozen
```

Scope, per artifact:

- **README.md**, explains the project: what it is, why, the feature set at a
  high level, how it works from the user's side, install, dev commands. **Not**
  how it is designed: no module tables, no lifecycle diagram. May point to
  `docs/` and `CHANGELOG.md` briefly.
- **docs/scoop-v01.md**, the **final state only**: how it behaves and how it is
  built now. Not a diff, not a history. Reads standalone. Carries the low-level
  design in the Hello Interview delivery-framework shape (requirements /
  entities and relationships / class design / implementation / extensibility;
  see `interview-prep/catalog-tracks/low-level-design/articles/01-delivery-framework.md`).
  "v01" is a document-revision marker, unrelated to the version number.
- **CHANGELOG.md**, lean. Keep a Changelog + SemVer. One entry per version,
  what changed and why it mattered. Pre-release `0.0.x` climbing to `0.1.0` as
  the first real release. Does not reference the specs or the doc (logging that
  a file was *added* is still fine).
- **.specs/00..03**, frozen historical design records, one per stage. Hold the
  reasoning and the roads not taken. Not updated to current state, no back-links
  to `docs/`.

Cross-cutting:

```text
- how it works now   -> docs/  or  README
- why it is this way  -> .specs/
- what changed        -> CHANGELOG
- JSDoc describes the code as it stands, never "this pass" / "the design session"
- no em dashes anywhere: prose, code comments, commit messages, package.json
- don't over-link documents to each other; each stands on its own
- version numbers: pre-release 0.0.x; bump manifest + package.json + package-lock together
```

## Working-style notes (unchanged, easy to trip on)

- **No em dashes anywhere.** Restructure the sentence. The `/code-review` on the
  `02` pass caught 21.
- In polished prose, no colon introducing an in-sentence list. Structural
  Markdown and copied source text are fine.
- Commit style: lowercase, multi-line, bullet body, trailer
  `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.
- `dist/` is gitignored; the build must still pass. `npm test` = Vitest,
  `npm run typecheck` = `tsc --noEmit`.

## Suggested skills

- **`update-refs`**, run as the pre-commit pass. This session renamed two
  handoff files and moved the consolidated doc; that skill catches any stale
  Markdown reference left behind (the known ones were fixed, but it is the
  right net).
- **`schedule-planner`**, only if interview-prep progress needs recording;
  `interview-prep/data/catalogs/personal-project.yaml` is modified in the wider
  working tree and may be tracking this project. Not this session's concern.
- No skill needed for a straight commit. Follow the commit style above and
  stage only `personal-projects/scoop/` paths.
