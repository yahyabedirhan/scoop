# Handoff — Scoop: structured Plain Text + new Markdown mode

Date: 2026-09-05
Project: `personal-projects/scoop/` (inside the job-search vault, tracked there, no nested git repo)

## What this is

Two changes to the copy-mode feature, both decided in a `/grill-me` session and
written up as a spec. Nothing is implemented yet.

1. **Plain Text keeps structure** — drop `<style>`/`<script>` text, one block per
   line, `<pre>` verbatim, single `\n` between blocks. The list numbering/
   bulleting already shipped (commit `dcb973b`); this extends the same idea to
   every other block element.
2. **A new Markdown mode** — the 4th copy mode, digit key `4`. Best-effort
   HTML→Markdown from tags only (no CSS-class semantics), with one deliberate
   exception: the `mdx-code` class HelloInterview's MDX renderer puts on inline
   code.

Plus a small shared refactor: extract `formatHTML`'s private tag-name sets into
`src/lib/utils/html-tags.ts` so all three text-shaped walkers agree on
block/inline.

## Authoritative source (do not re-derive)

- **Spec**: [`.specs/03-text-and-markdown-modes.md`](../.specs/03-text-and-markdown-modes.md)
  — the single source of truth. User stories, every conversion rule, the
  escaping rule, the shared-refactor decision, a worked before/after example,
  the `transform` dispatch pseudocode, and the testing plan. Read it first;
  this handoff does not repeat it.
- **Prior specs** (context, unchanged by this work): [`00-scoop.md`](../.specs/00-scoop.md),
  [`01-multi-format-copy.md`](../.specs/01-multi-format-copy.md),
  [`02-typescript-rewrite.md`](../.specs/02-typescript-rewrite.md). Spec 01 still
  says Plain Text is "just the text, no tags" — that wording is reconciled in the
  planned 00+01+02+03 consolidation, **not** in this pass.
- **Current code**: `src/lib/modes/plain-text.ts` (rewrite target),
  `src/lib/modes/modes.ts` (add the 4th entry),
  `src/lib/utils/format-html.ts` (extract the tag sets from here),
  `src/lib/robber.ts` (`ICONS` map needs a `markdown` entry; nothing else),
  `test/modes.test.ts` and `test/robber.test.ts` (extend). Read
  `plain-text.ts` before rewriting — the list-rendering logic in it
  (`renderList`, ordered/unordered/nested) must be preserved and reused by the
  Markdown walker.

## Seam / testing

One seam, already established: `mode.transform(element)` — a pure DOM-element →
string function, tested by building an element from an HTML string and asserting
on the returned text. No new seam. `test/modes.test.ts` is the prior art for
every conversion assertion; `test/robber.test.ts` for the "digit `4` selects
Markdown" case. `html-tags.ts` has no behavior of its own; `format-html`'s
existing tests guard that the extraction changed nothing.

Recommended order: `html-tags.ts` extraction first (green tests prove it's
inert) → Plain Text rewrite → Markdown mode → Robber wiring + icon. Typecheck
throughout, full suite once at the end.

## Decided in the session (so it is not re-litigated)

All of this is in the spec; flagged here because an implementer will be tempted
to "improve" on it:

- **h4 ATX cap is deliberate.** `h5`/`h6` render as `**bold**` block lines, not
  `#####`. The user chose this explicitly.
- **`mdx-code` is the ONLY class ever inspected.** Not `mdx-p`, not `mdx-h2` —
  those sit on semantic tags already handled. Do not build a generic
  class→markdown map "while you're there"; the user rejected speculative
  generality here. One predicate, commented as recognizing the MDX renderer's
  inline-code marker.
- **No language on code fences.** The language lives in a `data-*`/class on an
  ancestor, not a tag. Bare ` ``` `.
- **Tables flatten.** No GFM table generation — certainty is too low.
- **Escaping is leading-token only.** `\#  \>  \-  \+  \*` and `1\.`, each only
  before a space, only at the start of an emitted paragraph line, never
  mid-line, never in fences, never on Scoop's own prefixed lines. `_` is never
  escaped (this content is full of `event_id`, `user_id`).
- **Plain Text separator is a single `\n`; Markdown is `\n\n`.** Different on
  purpose — Markdown needs the blank line to render.
- **Block/inline classification is `formatHTML`'s existing split**, now shared
  via `html-tags.ts`. Don't invent a second definition.
- **Markdown `transform` returns a string** and never calls `formatHTML`, same
  as Plain Text.

## Rejected alternatives

- **Keying Plain Text separation on the literal `<p>` tag** — rejected; the
  target content is `<div class="mdx-p">`, so `<p>`-only does nothing. Hence the
  block/inline approach.
- **A narrow "class name contains `code`" heuristic** (matching `mdx-code`,
  `inline-code`, …) — considered, then narrowed to the *exact* token `mdx-code`
  after the user confirmed they don't want fuzzy class rules.
- **Recognizing the whole `mdx-*` namespace** — investigated; every other
  `mdx-*` class is redundant with its tag, so there's nothing to gain.
- **GFM table conversion**, **fence language inference**, **full Markdown
  escaping** — all explicitly out of scope, see the spec.
- **A generic `lib/modes/shared.ts` walker** shared across modes — rejected;
  only the *tag sets* are shared (`html-tags.ts`), each walker stays separate
  because the outputs differ too much.

## Working-style notes for this codebase

- **No em dashes anywhere**, including code comments and commit messages (vault
  `CLAUDE.md` → Communication Style). The `/code-review` on the last pass caught
  21 that had to be scrubbed — don't add them back. Restructure the sentence.
- **Comments are `/** */` Markdown**, short lead sentence then a list/example
  only for genuinely multi-part rationale. Attach rationale to the type/const
  it explains.
- **Naming**: literal and descriptive over short or clever. The one sanctioned
  exception is `Robber` (a pun on the extension's own name).
- **`dist/` is gitignored**; `npm run build` (two Vite passes) must still be run
  and pass. `npm test` = Vitest, `npm run typecheck` = `tsc --noEmit`.
- Commit style: lowercase, multi-line, bullet body; `Co-Authored-By: Claude
  Sonnet 5 <noreply@anthropic.com>`. Commit only `personal-projects/scoop/`
  paths — the repo has unrelated staged changes elsewhere. Do not `git add`
  outside the project without being asked.
- After implementing: run `/code-review` (two-axis, Standards + Spec) against
  the diff before committing, same as the `02` pass. `/simplify` is a good
  final polish.
- The extension's real-browser behavior (clipboard, click suppression) can't be
  checked from here — that manual step stays open, as noted in the `01` and
  `02` handoffs.

## Suggested skills for the implementing session

- **`tdd`** — the spec maps every assertion to `test/modes.test.ts`; build each
  conversion rule test-first.
- **`code-review`** — two-axis review against `.specs/03` before the commit.
- **`simplify`** — a cleanup pass once it's green.
