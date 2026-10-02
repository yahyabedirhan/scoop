# Handoff — Scoop: docs consolidation + README refresh

Date: 2026-09-05
Project: `personal-projects/scoop/` (inside the job-search vault, tracked there, no nested git repo)

## Current status

- **Spec 03 (structured Plain Text + Markdown mode) is implemented and committed**
  as `87a2e3f` on `master`. 86 tests green, `npm run typecheck` clean,
  `npm run build` clean. The two-axis `/code-review` ran and its findings were
  applied in the same commit.
- Spec files `.specs/00`..`.specs/02` say `Status: implemented`. `.specs/03`
  still says `Status: proposed` — flip it to `implemented` as part of this next
  pass, or leave it for the consolidation to supersede (your call).
- Still open, unchanged from the `01` / `02` / text-and-markdown handoffs: the
  real-browser check (clipboard write, click suppression, the new digit `4`
  and Markdown output on a live HelloInterview page) cannot be done from here.
  Manual step for the user.

This session's work is fully described by:
- Spec: [`.specs/03-text-and-markdown-modes.md`](../.specs/03-text-and-markdown-modes.md)
- Implementation handoff for that work: [`.handoff/2026-09-05-text-and-markdown-modes.md`](./2026-09-05-text-and-markdown-modes.md)
- The commit `87a2e3f` and its message.

Do not re-derive any of that. This handoff only covers the two follow-on doc jobs.

## Job 1 — consolidate the session specs into one current-state document

Every spec under `.specs/` states the plan: `00` + `01` + `02` + `03` fold into
**one** current-state document once all four have landed. They now all have.
See `.specs/03` lines 11-13 and its "Out of Scope" / "Further Notes" sections
for the exact intent.

What the consolidation needs to do:

- Produce a single spec that describes Scoop **as it is now**, not as a chain of
  diffs. Candidate: a rewritten `.specs/00-scoop.md`, or a new
  `.specs/scoop.md` that the numbered four link to as superseded. Decide the
  filing convention with the user if unsure; the project has no external issue
  tracker, hence the numbered-spec chain.
- **Reconcile the stale wording.** `.specs/01` still says Plain Text is "just
  the text, no tags". Since the `dcb973b` list work and `87a2e3f` structural
  rewrite that is wrong. Plain Text now keeps block structure, lists, and
  `<pre>`. `.specs/03` flags this explicitly as "reconciled in the
  consolidation, not here."
- Carry forward, do not lose: the inspect lifecycle and page-content ownership
  rules (from `00`), the mode registry mechanism and `format` -> `mode`
  terminology (from `01` and `02`), `formatHTML`'s block/inline model, the
  TypeScript/Vite build and the seam list (from `02`), and the four modes with
  the `mdx-code` rule and the escaping rule (from `03`).
- The four numbered specs can then be marked superseded (keep them for history,
  add a one-line pointer at the top of each to the consolidated doc).

The current authoritative code map, for reference while writing:

| Area | Files |
| --- | --- |
| Entry points | `src/entries/content.ts`, `src/entries/background.ts` |
| Orchestrator | `src/lib/robber.ts` (the `Robber` class, `ICONS` map) |
| Inspect / capture | `src/lib/inspector.ts` |
| Navigation | `src/lib/dom-navigator.ts` |
| Scrolling | `src/lib/scroll/scroller.ts`, `src/lib/scroll/margin-scroller.ts` |
| Messaging | `src/lib/messages.ts` |
| Modes | `src/lib/modes/{modes,full-html,clean-html,plain-text,markdown}.ts` |
| Shared utils | `src/lib/utils/format-html.ts`, `src/lib/utils/html-tags.ts` |
| Tests | `test/*.test.ts` (vitest + jsdom) |

## Job 2 — update `README.md`

`README.md` is badly stale. It still describes the pre-TypeScript extension and
never mentions Markdown mode. Concretely wrong today:

- **"No build step. The source files are the shipped files."** False since
  `bcc400b`. There is a two-pass Vite build (`npm run build`, content + background
  modes); `dist/` is the "Load unpacked" folder and is gitignored. `npm run dev`
  is the watch build.
- **Test runner.** Says "Node's built-in runner". It is now Vitest
  (`npm test` = `vitest run`), plus `npm run typecheck` = `tsc --noEmit`.
- **The whole "Layout" table** lists `.js` files that no longer exist
  (`lib/dom-nav.js`, `lib/page-content.js`, `lib/serialize.js`, `content.js`,
  `test/*.test.js`, `background.js`). Replace with the `src/` tree above and the
  `dist/` output. Note the renames: `dom-nav` -> `dom-navigator`,
  `page-content` -> `inspector`, `serialize` -> `utils/format-html`,
  `content.js` controller -> `robber.ts` (`Robber`), `lib/formats/` ->
  `lib/modes/`.
- **"Copy formats" section.** Says three, keys 1-3. There are now **four**:

  | Key | Mode | Module | One-liner |
  | --- | --- | --- | --- |
  | 1 | Full HTML | `full-html.ts` | selected HTML, pretty-printed |
  | 2 | Clean HTML | `clean-html.ts` | attributes stripped to an allowlist, textless subtrees dropped, plain wrappers unwrapped |
  | 3 | Plain Text | `plain-text.ts` | text with structure kept: one block per line, lists numbered/bulleted, `<pre>` verbatim, `<style>`/`<script>` dropped |
  | 4 | Markdown | `markdown.ts` | best-effort tag-driven HTML to Markdown; `mdx-code` is the only CSS class it reads |

  Terminology is now "mode" not "format" everywhere in code (`MODES`,
  `src/lib/modes/`, `mode.transform`). The README still says "format". Pick one
  (code says "mode") and make the doc match.
- **"Use" step 4** mentions "Press 1, 2, or 3". Update to 1-4 and name Markdown.
- **`gen-icons` / `demo.html`** references may still be accurate — verify
  against the repo (`tools/gen-icons.py`, `demo.html`) before keeping or cutting.
- The Mermaid inspect-lifecycle diagram and the "Not included" section are
  still broadly correct; check wording against the consolidated spec once Job 1
  is done so they do not drift again.

Sequencing: do Job 1 first (it settles the vocabulary and the current-state
description), then Job 2 can point `README.md` at the single consolidated spec
instead of the four numbered ones.

## Working-style notes (unchanged, but easy to trip on)

- **No em dashes anywhere**, including prose docs, code comments, commit
  messages. The `/code-review` on the `02` pass caught 21. Restructure the
  sentence instead. See vault `CLAUDE.md` -> Communication Style.
- In polished prose, no colon introducing an in-sentence list. Structural
  Markdown (tables, headers) and copied source text are fine.
- Commit style: lowercase, multi-line, bullet body, trailer
  `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`. Commit only
  `personal-projects/scoop/` paths; the repo has unrelated staged changes
  under `interview-prep/` that must not be added.
- These are doc-only jobs, so no build/test impact is expected, but run
  `npm test` and `npm run build` once at the end anyway to be sure a stray
  edit to a fenced code sample in a spec did not break a doctest-style
  assumption (there are none today, but cheap to confirm).
- After the doc rewrites, a `/code-review` pass is lower value than for code,
  but a read-through for the em-dash rule and for broken relative links is
  worth doing.

## Suggested skills

- **`writing-for-agents`** — only if you touch `CLAUDE.md`; not expected here.
- **`update-refs`** — run it as the pre-commit pass. Both jobs rename or
  supersede files that other Markdown links point at (`.specs/00`..`03`,
  `README.md`'s layout table, the `.handoff/` cross-links). This skill fixes
  stale references after renames and deletions.
- **`code-review`** — optional final read-through of the consolidated spec and
  README against the actual `src/` tree, mainly to catch any remaining
  "format" vs "mode" drift or a file path that no longer exists.
