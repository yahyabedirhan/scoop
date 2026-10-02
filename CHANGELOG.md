# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/2.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Scoop has not been released yet. The `0.0.x` entries below are development
milestones. `0.1.0` will be the first version considered ready to use.

## [Unreleased]

## [0.0.7] - 2026-10-02

### Added
- The `README` opens with the Scoop logo, a 512 px render of the icon at
  `assets/images/logo/scoop.png`, centred above the title.
- Two alternate icons, `pointer` and `ball`, kept as 512 px previews beside the
  logo. `npm run gen-icons -- --variant <name>` ships one of them instead of the
  default `brackets`.

### Changed
- A new icon replaces the ice-cream scoop. A pistachio ball sits between cream
  angle brackets, `<●>`, on a pistachio squircle tile with a soft gradient, so
  it reads as a flat, quiet mark in the toolbar rather than a sticker.
- The toolbar `ON` badge is deep pistachio (`#37692c`) instead of Chrome blue,
  to match the new icon.

## [0.0.6] - 2026-10-01

### Added
- `docs/scoop-v01.md`, a standalone description of the final project state
  (behavior and low-level design). JSDoc comments scrubbed of session-scoped
  phrasing ("shipped this pass", "from the design session") so they describe
  the code as it stands.
- A 32 px icon, for toolbars on high-density screens.

### Changed
- A new ice-cream-scoop icon replaces the cursor-snatch logo. It shows a
  smiling scoop of strawberry ice cream from 48 px up.
- The keyboard command id is now `toggle-scoop`. A custom shortcut set for the
  old id is dropped, so set it again in
  `chrome://extensions/shortcuts` if you changed it. The default stays
  `Cmd+Shift+S` / `Ctrl+Shift+S`.
- The orchestrator class `Robber` is now `Scooper`, in `src/lib/scooper.ts`.

## [0.0.5] - 2026-09-05

### Added
- **Markdown copy mode** (number key `4`), the fourth mode. Best-effort
  HTML-to-Markdown driven only by what a tag guarantees: `#`-`####` headings
  (`<h5>`/`<h6>` fall back to a bold line), `**bold**` / `*italic*` /
  `~~strike~~`, backtick code, fenced `<pre>` with no info string,
  `[text](href)` links, `![alt](src)` images, `-` / `1.` lists with nested
  indent, `> ` blockquotes, `---` rules, hard line breaks. Tables flatten to
  text. The one CSS class it reads is `mdx-code` (HelloInterview's MDX
  inline-code marker). Leading structural tokens in body text are
  backslash-escaped so prose is not promoted into a heading or list item.

### Changed
- **Plain Text keeps block structure.** Every block-level element starts on its
  own line, inline elements keep flowing with their text, `<pre>` is copied
  verbatim as its own block, and blocks are separated by a single newline.
  Previously every block collapsed onto one space-joined line.
- `<style>` and `<script>` text is now dropped from Plain Text output, the same
  rule Clean HTML already applied, so an inline base64 `@font-face` no longer
  buries the real text.
- The tag-classification sets (`INLINE_TAGS`, `VOID_TAGS`, `VERBATIM_TAGS`,
  `NEVER_CONTENT_TAGS`) moved into a shared `html-tags` utility so `formatHTML`
  and the Plain Text and Markdown walkers agree on block vs inline.

## [0.0.4] - 2026-09-05

### Changed
- **Rewritten in TypeScript with a Vite build.** `npm run build` produces a
  self-contained `dist/` folder that is the "Load unpacked" target; `dist/` is
  gitignored. The hand-rolled UMD module wrappers are gone. No user-facing
  behavior changed.
- **"format" renamed to "mode" throughout**, freeing "format" to mean HTML
  pretty-printing. The `chrome.storage.local` key changed from `activeFormatId`
  to `activeModeId`; `lib/formats/` became `src/lib/modes/`; `serialize()`
  became `formatHTML()`.
- The `page-content` module split into three collaborators with no reference to
  each other: `Robber` (orchestrator), `Inspector` (Scoop's DOM footprint and
  clean capture), and `Scroller` (bring-into-view, behind a swappable
  interface, implemented by `MarginScroller`).
- The three cross-file `chrome.runtime` message strings became a single typed
  `MessageType` const object.
- Test runner switched from `node --test` to Vitest, run against the TypeScript
  sources directly. Added `npm run typecheck` (`tsc --noEmit`, `strict`).

### Removed
- **The deprecated `document.execCommand("copy")` clipboard fallback.**
  `navigator.clipboard.writeText` is now the only write path. A click or Enter
  handler in a secure context already satisfies its user-gesture requirement,
  and a rejection still surfaces as the "Copy failed" toast.

## [0.0.3] - 2026-09-05

### Changed
- Plain Text mode keeps list structure: each `<li>` on its own line, numbered
  `1.` under `<ol>` and bulleted `-` under `<ul>`, nested lists indented two
  spaces per level. Non-list content was still collapsed at this point; that
  changed in 0.0.5.

## [0.0.2] - 2026-09-05

### Added
- **Multi-format copy.** Three copy formats chosen per-copy without leaving
  inspect mode, switched with number keys `1` / `2` / `3`:
  - **Full HTML** - the selected page HTML, now pretty-printed with 2-space
    indentation (inline elements kept flowing, `<pre>` / `<script>` / `<style>`
    / `<textarea>` left verbatim).
  - **Clean HTML** - the same subtree with styling and behavior attributes
    stripped to a small per-tag allowlist (`img[src,alt]`, `a[href]`), textless
    subtrees dropped, single-child textless wrappers unwrapped.
  - **Plain Text** - the text content of the selection.
- The active format persists in `chrome.storage.local` as a single global
  value, so a new inspection starts in the last-used format.
- The hover label became format-aware: a per-format icon, and format-specific
  detail (a live character count for Clean HTML and Plain Text instead of the
  class list).
- `storage` permission added to the manifest.

### Changed
- Clean HTML drops `<style>` and `<script>` subtrees entirely rather than
  treating their text as content, so an inline SVG carrying a base64 web font
  no longer bloats a capture by megabytes.

### Fixed
- Hover-label icon color, geometry, and font-size regressions against the
  `all: initial` style reset.

## [0.0.1] - 2026-09-03

### Added
- First working version. A local unpacked Chrome MV3 extension that toggles an
  "inspect mode" for the active tab from the toolbar icon or a keyboard
  shortcut (`Ctrl+Shift+S`, `Cmd+Shift+S` on macOS).
- Hover highlights the element under the cursor with a translucent overlay and
  a `tag#id.class` label; arrow keys walk the DOM tree (sibling / parent /
  child, with a lone-child gap-jump on Down and document-metadata tags
  skipped); click or Enter copies the element's page HTML to the clipboard;
  a toast confirms and inspect mode turns itself off.
- Arrow navigation auto-scrolls an offscreen target into view with a temporary
  `scroll-margin`, aligned to whichever viewport edge it passed.
- The `ON` toolbar badge tracks per-tab inspect state; state is cleared on
  navigation and never restored across it.
- Capture excludes Scoop's own overlay, label, and toast and restores any
  temporary class or style change before reading `outerHTML`, so the copy is
  page content only. Ownership follows node identity, so page elements that
  share Scoop's ids or classes stay selectable.
- Each pending copy belongs to the inspection that started it, so a stale
  clipboard result cannot end a newer inspection.

### Changed
- Renamed from "inspect-copy-extension" to **Scoop**, with a new
  cursor-snatch logo.
- Default shortcut set to `Cmd+Shift+S` / `Ctrl+Shift+S` (Chrome forbids a
  bare `Shift+S`).
