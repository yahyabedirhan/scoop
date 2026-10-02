# Handoff — Scoop TypeScript rewrite

Date: 2026-09-05
Project: `personal-projects/scoop/` (inside the job-search vault, tracked there, no nested git repo)

## What this is

Not a new feature — a structural rewrite of the existing, working extension
(plain JS, no build step) into TypeScript with a Vite build, split module
boundaries, and a terminology cleanup. No behavior changes. Nothing has been
implemented yet; this session was entirely design (a `/grill-me` session
followed by several `/show-me` rounds that iterated on one specific
abstraction).

## Authoritative sources (do not re-derive)

- **Spec**: [`.specs/02-typescript-rewrite.md`](../.specs/02-typescript-rewrite.md)
  — the single source of truth for what to build: user stories, the full
  low-level design (entities, class design, key flows), the rename table, the
  directory layout, and the testing plan. Read it before doing anything else.
  This handoff does not repeat anything in it.
- **Prior specs** (unchanged by this rewrite): [`.specs/00-scoop.md`](../.specs/00-scoop.md),
  [`.specs/01-multi-format-copy.md`](../.specs/01-multi-format-copy.md) — still
  say "format" instead of "mode" and describe the current plain-JS
  implementation. This is intentional, not staleness — see "Explicitly
  deferred" below.
- **Prior architecture handoff**: [`.handoff/2026-09-03-architecture-review.md`](2026-09-03-architecture-review.md)
  — recorded "Keep plain JavaScript and the no-build packaging" as a settled
  decision. This session's spec explicitly supersedes that one line; nothing
  else in that handoff is invalidated.
- **Current code**: `background.js`, `content.js`, `lib/*.js`, `lib/formats/*.js`,
  `test/*.test.js` — this is what gets migrated. Read it before writing the
  TypeScript equivalent; several of the design decisions below only make sense
  in light of what the current code actually does (e.g. `lib/page-content.js`'s
  three genuinely-independent state fields).

## Explicitly deferred (do not touch this pass)

- `README.md` and `.specs/00-scoop.md`/`.specs/01-multi-format-copy.md` keep
  saying "format." The user will consolidate 00 + 01 + 02 into one cohesive
  current-state spec **after** implementation lands, and update the README
  then, in one pass. A natural instinct mid-implementation will be to "fix"
  these for consistency — don't. It was a deliberate call, made explicitly
  after being raised as a question.
- No second `Scroller` implementation. `AncestorScroller` in the spec is a
  sketch proving the interface is swap-friendly, not a work item.
- `src/lib/utils/` and `src/lib/scroll/` should only ever contain what's
  already named in the spec (`format-html.ts`; `scroller.ts`,
  `margin-scroller.ts`, `scroll-with-margin.ts`). Don't add speculative
  helpers there just because the folders exist.

## Rejected alternatives (so they don't get re-litigated)

- **Vite + CRXJS with HMR** — rejected in favor of a manual watch-and-reload
  dev loop. The user explicitly prefers avoiding "magic" tooling for a
  single-person project even though HMR was available; plain Vite (esbuild
  under the hood) was chosen partly *because* it stays useful without needing
  the HMR plugin.
- **webpack** — rejected as heavier config for no benefit at this project size.
- **Keeping `background.js` as plain JS in a `worker/` folder outside `src/`**
  — this was the agreed plan for one full round, specifically to make the
  JS/TS boundary explicit. The user then asked whether TS would work fine for
  a service worker too; once confirmed yes, they reversed course in favor of
  one uniform `src/entries/` folder, fully TypeScript. If you see any
  reference to a `worker/` folder in older context, it's stale.
- **`entries/content-entry.ts` / `entries/background-entry.ts`** — the
  `-entry` suffix was dropped; the folder name already says that. Files are
  `entries/content.ts` and `entries/background.ts`.
- **`entries/main.ts` instead of `entries/content.ts`** — proposed by the user,
  pushed back on and dropped. Reasoning worth preserving: "content script" is
  a specific, documented Chrome MV3 concept distinct from "background script,"
  and naming the file after that platform concept is more informative than a
  generic "main," which also wrongly implies one entry is more primary than
  the other.
- **TS `enum` for the message protocol** — rejected in favor of a
  `const {...} as const` object with a derived union type, to avoid enum's
  runtime/reverse-mapping baggage and keep the value a plain string type.
- **A separate `lib/capture.ts` orchestrator function** taking a list of
  "restorer" callbacks — this was the assistant's proposed fix for `capture()`
  needing to know about multiple kinds of page footprint. The user rejected
  introducing a second orchestrator; `capture()` stays a method on
  `Inspector` itself.
- **`Scroller` exposing a per-node `restoreInto(original, clone)`** that
  `Inspector.capture()` would call during its walk — this was the *second*
  attempt at wiring scroll cleanup into capture, and also rejected: it still
  made `Inspector` aware `Scroller` exists. The final design has `Scroller`
  expose `flush()` instead, called by `Robber` right before `capture()` (and
  on `stop()`), so the live page carries no residue before `Inspector` ever
  clones anything — `Inspector` and `Scroller` end up with zero references to
  each other.
- **`dist/` as build output only, repo root as the "Load unpacked" target**
  (referencing `dist/content.js` from a root `manifest.json`, nothing else
  copied) — proposed by the assistant to avoid needing `vite-plugin-static-copy`
  at all. Rejected: the user wants `dist/` to be the *entire* self-contained
  shippable folder, explicitly to avoid mixing uncompiled source with what's
  actually loaded.
- **Naming candidates for the `page-content.js` replacement**: `PageFootprint`,
  `PageMutations`, `PageSnapshot`, and `PageHost` were all discussed and
  superseded — see the design arc below. `PageHost` in particular was the
  leading candidate for one whole round before the class was split further
  and the name reverted to `Inspector` once the orchestrator became `Robber`
  (no more name collision to avoid).
- **`Inspection` as the orchestrator's name** — used for most of this
  session, but replaced with `Robber` once `Inspector` freed up (see below).
  If you see `Inspection`/`InspectController` anywhere in older context,
  it's stale — the class is `Robber`.

## The `page-content.js` design arc (context for why the final split looks the way it does)

This took four rounds of pushback and is worth understanding before touching
that code, since the reasoning isn't fully captured by just reading the final
class design in the spec:

1. Assistant initially argued `page-content.js` was a fine single abstraction
   because `capture()` needs one DOM walk touching all its state.
2. User challenged this concretely: `roots` (owned-node tracking) is never
   touched by the scrolling logic, and vice versa — table evidence, not
   principle-citing, is what won the argument. Assistant proposed a 3-way
   split (`OwnedNodes` / `InspectingClass` / `ScrollIntoView`) plus a new
   `capture()` orchestrator to recombine them.
3. User rejected the new orchestrator specifically, and proposed a shape
   where `scroll-into-view` logic becomes a **pure utility** (no class, no
   state) for the property-diffing math, while the **stateful coordination**
   (the `Map`, the re-entrancy/timing bookkeeping) moved inside the
   footprint-tracking class alongside `roots`/`inspectClass`.
4. Next turn: the user asked *why* scroll-margin-patching is the right
   scrolling algorithm at all, and wanted the scrolling *algorithm* itself
   swappable. That produced a `ScrollStrategy`/`Scroller` interface — but
   still owned *inside* the footprint class (named `PageHost` at that point),
   which composed one injected implementation.
5. Final turn: the user rejected that composition too — the class that tracks
   the page's DOM footprint (renamed `Inspector`) shouldn't own scroll logic
   *at all*, not even behind an interface. `Scroller` moved out to be a full
   sibling of `Inspector`, both owned directly by a new top-level
   orchestrator the user named `Robber` (playing on the extension's own name). This also meant `Scroller`'s per-node `restoreInto` hook (which
   still required `Inspector` to know `Scroller` existed) was replaced with a
   plain `flush()` that `Robber` calls before `capture()` and on `stop()` —
   `Inspector` now has zero awareness that scrolling exists.

Net effect: `Inspector` only ever deals with extension-node tracking, the
inspecting-class toggle, and clean capture. `Scroller` only ever deals with
bringing a target into view. `Robber` is the only entity that references both,
which is exactly what makes it the orchestrator rather than a bloated god
object — see the spec's Class Design for the current, final shape.

## Working-style notes for this codebase

- **Naming**: literal and descriptive over short or metaphorical, even when
  the short name is well-established (`DomNav` → `DomNavigator`,
  `isOwnNode` → `isExtensionNode`; not kept short "because everyone knows
  what it means"). Function/file names should match 1:1 (`format.ts`
  exporting `format()` was rejected in an earlier pass for exactly this
  reason before landing on `format-html.ts` / `formatHTML()`). Avoid suffixes
  that just repeat the folder they're in (`-entry`, `-controller` when the
  file is already named for its role). The one deliberate exception is
  `Robber` for the orchestrator — a pun on the extension's own name
  the user chose on purpose; don't "fix" it back to something
  literal like `Orchestrator` or `Controller`.
- **A useful naming test that came up repeatedly**: a class name should read
  naturally as the subject of its own methods (noun-verb fit). `PageFootprint`
  was rejected specifically because "a footprint captures something" doesn't
  parse — `PageHost`/`Inspector` (`host.capture()`, `inspector.capture()`) do.
  Worth applying this test to any new class introduced during implementation.
- **Mermaid doesn't render in this chat client** — use plain text/pseudocode
  diagrams in chat responses. It renders fine inside actual Markdown files
  (the spec and `00-scoop.md` both use it successfully), so this only affects
  what you show inline during a `/show-me`-style discussion, not what you
  write to disk.
- **Design-principle grounding**: when discussing whether something is a good
  abstraction, the user wants concrete evidence (which state is touched by
  which methods, tabulated) rather than principle names cited abstractly. The
  vault's own [low-level-design articles](../../../interview-prep/catalog-tracks/low-level-design/articles/)
  (`02-design-principles.md` for SRP/OCP/Separation of Concerns,
  `04-design-patterns.md` for Strategy) are the shared vocabulary being
  applied throughout — worth citing by name when a design choice maps onto
  one of them, as was done for the `Scroller` split (a Strategy pattern,
  even though the class itself avoids the word "Strategy" in its name — see
  the spec).

## Environment facts

- Node `v26.1.0` is available locally (has native TS type-stripping), but
  Vitest was chosen anyway over relying on that + `node --test`, since it
  shares Vite's config/transform pipeline as one toolchain — see the spec's
  Testing Decisions for the full reasoning.

## Suggested skills for the next session

- **`tdd`** — the spec's Testing Decisions section maps every existing test
  file to its new home before any implementation code exists; this rewrite is
  a good fit for building it test-first module by module.
- **`codebase-design`** — if any further module/interface question comes up
  during implementation that isn't already resolved in the spec.
- **`simplify`** — a pass after the initial implementation lands, before
  calling it done.
- **`code-review`** — to check the finished migration against
  `.specs/02-typescript-rewrite.md` once implementation is complete.
