# 01 - Multi-Format Copy

Status: implemented
Last updated: 2026-09-05

Builds on [00-scoop.md](./00-scoop.md). This spec only covers what changes or adds
to that baseline; the inspect lifecycle, navigation rules, scrolling, overlay
mechanics, and clipboard-write fallback described there are unchanged except
where noted below.

## Problem Statement

When I point Scoop at an element, I always get its exact page HTML: every
Tailwind class, every `data-*` and `aria-*` attribute, every icon SVG. That is
right when I actually want the markup, but most of the time I am pulling a
snippet off a page to remind myself what it said, not how it was built. The
class soup and icon noise bury the one or two lines of real content I wanted,
and there is no way to ask Scoop for anything less than the whole raw element.

## Solution

Scoop gains multiple copy formats, chosen per-copy without leaving inspect
mode. Three formats ship in this pass:

- **Full HTML** - today's behavior, unchanged in content, now pretty-printed.
- **Clean HTML** - the same subtree with styling/behavior attributes and
  no-text subtrees removed, keeping the tag structure and a small allowlist of
  content-bearing attributes (image sources, link targets).
- **Plain Text** - just the text content of the selection, no tags at all.

The active format is switched with number keys (`1`/`2`/`3`) while inspect
mode is on, the same way arrow keys already change the target. It persists
across toggles (`chrome.storage.local`) so the last format used is what a new
inspection starts with. The hover label gains a small icon and format-specific
detail (a length instead of a class list, once classes are no longer part of
what gets copied) so it is obvious which format is about to be copied without
opening anything.

Formats are added as independent modules behind one small registry, so a
fourth format (e.g. a future screenshot-to-clipboard mode) is a new module and
one array entry, not a change to `content.js`'s copy or keyboard-handling
logic.

## User Stories

1. As a user, I want to copy an element as Clean HTML, so that I get its text
   and structure without the styling classes that made the raw HTML noisy.
2. As a user, I want to copy an element as Plain Text, so that I can grab just
   the words with no markup at all.
3. As a user, I want Full HTML to keep working exactly as it does today, so
   that switching to the new formats never puts the existing behavior at risk.
4. As a user, I want to switch the active format with a number key while
   inspecting, so that I don't have to leave inspect mode, click something
   else, and re-select my target to change formats.
5. As a user, I want the format I last used to still be selected the next
   time I turn on inspect mode, so that I am not resetting to Full HTML every
   single time when I mostly use one format.
6. As a user, I want the hover label to show me which format is active and a
   preview of what I am about to copy, so that I can tell at a glance whether
   I am in the right mode before I click.
7. As a user, I want Clean HTML to drop an element's classes, ids, ARIA
   attributes, roles, and inline styles, so that only content-relevant
   information remains.
8. As a user, I want Clean HTML to still keep an image's source and alt text,
   and a link's destination, so that I don't lose information that is content,
   not styling.
9. As a user, I want Clean HTML to drop any part of the subtree that has no
   text in it at all (icon-only buttons, empty layout containers, decorative
   SVGs), so that the result reads like an outline of the real content instead
   of being full of empty husks.
10. As a user, I want Clean HTML to collapse a wrapper element that has no
    text of its own and exactly one child, so that deeply nested
    styling-only `div`s don't obscure the actual structure.
11. As a user, I want Full HTML and Clean HTML to be pretty-printed with
    2-space indentation, so that the copied markup is immediately readable
    when pasted into an editor, instead of landing as one long line.
12. As a user, I want pretty-printing to keep inline elements (links, bold,
    italics, spans, code, etc.) flowing with their surrounding text rather
    than breaking each one onto its own line, so that prose-like content
    still reads naturally.
13. As a user, I want pretty-printing to never alter the content of a
    `<pre>`, `<script>`, `<style>`, or `<textarea>`, so that whitespace-
    significant content is never silently corrupted by formatting.
14. As a user, I want a distinct icon per format in the hover label, so that
    I can recognize the active format without reading text.
15. As a user, I want the Full HTML label to keep showing tag, id, classes,
    and dimensions exactly as it does today, so that nothing regresses for
    the format I already rely on.
16. As a user, I want the Clean HTML label to show the tag and dimensions but
    not the class list, and to show the character length of what would
    actually be copied, so that I can judge scope without seeing information
    that will not end up in the copy anyway.
17. As a user, I want the Plain Text label to show only the character length
    of the text I am about to copy, so that I am not shown DOM shape
    information that is irrelevant once I've dropped down to raw text.
18. As a user, I want the format registry designed so that adding a future
    format (e.g. screenshot-to-clipboard) does not require changing the
    keyboard handling, the label rendering, or any existing format's code, so
    that the extension can keep growing without regression risk to what
    already works.
19. As a user, I want my selected format to be remembered globally (not
    per-tab), so that the behavior is consistent no matter which page I'm on.
20. As a user, I want switching format with a number key to never itself
    trigger a copy or exit inspect mode, so that I can freely preview
    different formats on the same target before committing to one.

## Implementation Decisions

- **New modules, following the existing `lib/` convention**
  (`lib/dom-nav.js`, `lib/page-content.js` are pure helpers injected before
  `content.js`): a `lib/formats/` directory holding exactly one small module
  per format (`full-html.js`, `clean-html.js`, `plain-text.js`) plus
  `formats.js`, which exports the ordered array consumed by both
  `content.js` and the label renderer. `lib/formats/` stays homogeneous —
  every file in it is a format, so the directory doubles as its own registry
  listing; the shared HTML serializer described below lives as a sibling
  utility, `lib/serialize.js`, alongside `dom-nav.js` and `page-content.js`,
  not inside `formats/`, since it isn't itself a format and adding it there
  would break that one-file-per-format consistency. `background.js`'s
  `ensureInjected` gains all of these files in its `executeScript` file list,
  in the same no-build-step, no-bundler style as today.

- **Format interface**: each module is a plain object (duck-typed Strategy,
  no base class or formal interface needed for three modules), documented
  with a brief JSDoc comment rather than a full typedef contract:
  `{ id, key, label, transform(clonedEl) }` (the hover-label icon is keyed by
  `id`, see Label rendering below). `key` is the digit
  (`"1"`/`"2"`/`"3"`) it's bound to. `transform` receives a fresh clone of the
  selected element (the same kind of clone `page-content.js`'s `capture`
  already produces) and returns either a DOM node (Full HTML, Clean HTML) or
  a string (Plain Text) — the caller decides what to do with the result based
  on which shape comes back, there is no separate `kind` field.

- **Shared HTML serialization**: Full HTML and Clean HTML both return a DOM
  node from `transform`; one shared `serialize(node)` step, in the new
  `lib/serialize.js` utility (a sibling of `lib/formats/`, not a member of
  it), turns that into the final indented string. It walks the tree, indents
  2 spaces per depth, and treats a small
  hardcoded list of inline tag names (`a, b, i, em, strong, span, code,
  small, sub, sup, br`) as flowing with surrounding text rather than forcing
  them onto their own line; anything not on that list, including unknown/
  custom elements, is treated as block-level. `pre`, `script`, `style`, and
  `textarea` subtrees are copied through untouched, with no reindentation
  applied inside them. Plain Text's `transform` returns its string directly
  and never touches `serialize`.

- **Clean HTML transform**: given a cloned element, recursively remove any
  descendant subtree whose text content (trimmed) is empty, then recursively
  unwrap any remaining element that has no direct text of its own and exactly
  one remaining child (splice the child into the parent's position), then
  strip every attribute from every remaining element except ones in a small
  per-tag allowlist: `img` keeps `src` and `alt`; `a` keeps `href`. The
  allowlist is a simple tag-to-attribute-list lookup so adding another
  case (e.g. `time` → `datetime`, if that comes up later) is a one-line
  addition, not a logic change. SVG elements are always removed as part of
  the no-text-subtree rule (or explicitly, if they ever contain non-empty
  `<title>`/`<text>`); no SVG-specific allowlisting exists yet. `<style>` and
  `<script>` elements never count as text content even though their
  `textContent` is non-empty (an inline `<svg><style>` with embedded
  `@font-face` base64 fonts was bloating captures by megabytes), so a
  `<style>`-only SVG or wrapper is still dropped as textless.

- **Format switching**: `content.js`'s `onKeyDown` gains a check for digit
  keys matching a format's `key`; on match it sets the session's active
  format and re-renders the label (via the existing `drawOverlay` path), does
  not touch `target`, does not trigger a copy, and does not exit inspect
  mode. This sits alongside the existing Escape/arrow/Enter handling, not
  inside `doCopy`.

- **Persistence**: the active format id is read from and written to
  `chrome.storage.local` (new permission needed in `manifest.json`) as a
  single global value, not per-tab. `start()` in `content.js` reads it (or
  falls back to the first format in the registry, i.e. Full HTML, if unset)
  when building the session; every switch via number key writes it back.

- **Label rendering**: `drawOverlay`'s label construction becomes
  format-aware, driven entirely by which format object is currently active
  and the shape its `transform` returns — no `if (format === "clean-html")`
  branching lives in `content.js` beyond selecting the right format object
  from the registry by id/key. Full HTML keeps `describeElement(target)` (tag,
  id, classes) plus rounded `WxH`. Clean HTML shows tag plus `WxH` plus a
  computed character length of the serialized Clean HTML output for the
  current target (classes dropped from the string, since they aren't part of
  what gets copied). Plain Text shows only a character length. The
  length is computed by running that format's own `transform` (and
  `serialize` where applicable) against the current target — the same
  computation `doCopy` would use, not a separate estimate — but only when the
  hovered target actually changes (i.e. inside `setTarget`/`drawOverlay`'s
  existing re-render path), not on every raw `mousemove` event, since that
  path already only fires on a genuine target change. No debounce is added
  up front; this is deferred to a follow-up only if hovering over very large
  subtrees is observably slow in practice.

- **Icons**: three small inline SVGs (no new asset files, consistent with
  the extension shipping no external dependencies), one per format, added to
  `content.css`/`content.js` alongside the existing overlay/label/toast
  styles. Full HTML and Clean HTML share a visually related "tag" glyph with
  a deliberate distinguishing mark on Clean HTML's version; Plain Text gets a
  "T" glyph. Exact visual design is an implementation detail, not spec'd
  further here.

- **Manifest change**: `manifest.json`'s `permissions` gains `"storage"`
  alongside the existing `activeTab` and `scripting`.

## Testing Decisions

- Tests should assert observable behavior (the string/node a format produces
  for a given input, or the key press that switches format and what the label
  shows afterward), not internal implementation details like which private
  helper a format happens to call.
- **`test/formats.test.js` (new)**, mirroring the existing
  `test/dom-nav.test.js` pattern (pure functions, fake/minimal DOM trees, no
  jsdom needed since these operate on already-cloned nodes): unit tests per
  format's `transform` covering attribute stripping, the allowlist, no-text
  subtree removal, wrapper collapsing, and the `serialize` step's inline-vs-
  block indentation and its `pre`/`script`/`style`/`textarea` passthrough.
- **`test/content.test.js` (extended)**, following its existing jsdom-based,
  input-driven style (load the shipped scripts, dispatch real key/pointer
  events, assert on the resulting DOM/label/clipboard state): add coverage
  for digit-key format switching (label updates, no copy triggered, target
  unchanged), the persisted-format read on `start()`, and that `doCopy` picks
  up whichever format is currently active.
- The unpacked extension and `demo.html` remain the manual check for visual
  label/icon rendering and real `chrome.storage` behavior, same as the
  existing spec's reliance on manual checks for real clipboard/visual
  placement guarantees that simulated DOM tests can't establish.

## Out of Scope

- A screenshot-to-clipboard format and any image-producing clipboard path
  (`navigator.clipboard.write` with a `ClipboardItem`, `captureVisibleTab`,
  or similar). The format interface is designed so this can be added later
  without touching existing formats, but nothing image-shaped is built now.
- A toolbar `default_popup` for visual format selection and keyboard-shortcut
  customization. Deferred as a separate, later addition; this pass is
  keyboard-only (number keys during inspect mode) plus the persisted default.
- SVG-aware cleaning (e.g. a mode that extracts or simplifies icon SVGs
  instead of dropping them). Clean HTML always drops SVG content for now.
- Any change to arrow-key navigation, scrolling, overlay drawing beyond the
  label content itself, the click-suppression model, or the clipboard-write
  fallback chain described in `00-scoop.md`. All of that stays as-is.
- Debounce/throttling of the live label preview computation. Only added if
  the naive "recompute on target change" approach is observed to be slow.
- Per-tab format state. The active/persisted format is a single global
  value.

## Further Notes

- This spec assumes `page.capture`-style cloning (from `lib/page-content.js`)
  is reused or paralleled for the fresh clone each format's `transform`
  receives, so that Scoop's own overlay/label/toast nodes and any temporary
  page mutations it applied are already excluded before a format ever sees
  the subtree, exactly as they are for today's single-format `capture`.
- This project has no issue tracker; per its own conventions (see
  `CLAUDE.md` at the vault root and the existing `00-scoop.md`), this spec
  lives as a numbered Markdown file under `.specs/` rather than being filed
  and triage-labeled externally.
