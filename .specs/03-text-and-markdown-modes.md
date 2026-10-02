# 03 - Structured Text and Markdown Modes

Status: implemented
Last updated: 2026-09-05

Builds on [00-scoop.md](./00-scoop.md), [01-multi-format-copy.md](./01-multi-format-copy.md),
and [02-typescript-rewrite.md](./02-typescript-rewrite.md). Covers only what
changes. The inspect lifecycle, the mode registry mechanism (a mode is a module
plus one `MODES` entry), the `format` -> `mode` terminology, and `formatHTML`'s
block/inline model are all described in the earlier specs and are not repeated
here. `README.md` and `.specs/00`/`01`/`02` are deliberately **not** updated by
this spec; the planned consolidation pass folds 00+01+02+03 into one
current-state document.

## Problem Statement

When copying a content-heavy element as Plain Text, two things go wrong:

- An inline `<style>` or `<script>` (for example an SVG's `@font-face` rule
  carrying a base64 web font) dumps kilobytes of gibberish into the output. This
  is the exact noise Clean HTML already learned to drop, but Plain Text still
  emits it.
- Every block runs together. Paragraphs, headings, list items, and code samples
  all collapse onto one line joined by single spaces, so a copied article
  section is an unreadable wall of text.

There is also no middle ground between "all the raw HTML" and "no structure at
all." Much of the time the user is pulling a section out of a docs or course
page (HelloInterview, rendered from MDX) into their notes and wants it to *stay*
structured. Headings as headings, code as code blocks, lists as lists, without
the class soup that Full HTML carries.

## Solution

Two changes.

1. **Plain Text keeps structure.** It drops `<style>` / `<script>` text the way
   Clean HTML does, puts every block-level element on its own line, keeps inline
   elements flowing with their text, and preserves `<pre>` content verbatim. The
   list numbering and bulleting that shipped as a follow-on to 01 is unchanged;
   this extends the same idea to every other block element.

2. **A new Markdown mode**, the fourth copy mode, selected with the `4` key
   while inspecting. Best-effort HTML-to-Markdown that converts only what an HTML
   *tag* guarantees with certainty (headings, emphasis, code, links, images,
   lists, blockquotes, rules) and drops information that lives only in CSS
   classes. The one deliberate exception is the `mdx-code` class that
   HelloInterview's MDX renderer puts on inline-code spans.

## User Stories

Plain Text:

1. As a user, I want inline `<style>` and `<script>` content excluded from a Plain Text copy, so that an element containing a base64 web font or an inline script does not bury the real text under kilobytes of noise.
2. As a user, I want each block-level element (paragraph, heading, list item, container) to start on its own line in Plain Text, so that a copied article section reads as separate lines instead of one run-on paragraph.
3. As a user, I want inline elements (links, bold, spans, inline code) to keep flowing with their surrounding text in Plain Text, so that a sentence with a link in the middle stays one sentence.
4. As a user, I want `<pre>` blocks copied verbatim in Plain Text with their internal line breaks intact, so that a copied code sample or endpoint list stays multi-line instead of collapsing to one line.
5. As a user, I want blocks in Plain Text separated by a single newline and never by a growing stack of blank lines, so that the output is compact but legible.
6. As a user, I want headings in Plain Text to appear as plain lines with no prefix, so that the mode stays true to "just the text."
7. As a user, I want the existing Plain Text list behavior (ordered `1.`, unordered `-`, nested indent) to keep working unchanged.

Markdown mode:

8. As a user, I want a Markdown copy mode I can select with the `4` key while inspecting, so that I can pull a page section into my notes as Markdown without leaving inspect mode.
9. As a user, I want Markdown mode to persist as my default like the other modes, so that if I mostly copy as Markdown I am not reselecting it every time.
10. As a user, I want the hover label in Markdown mode to show the tag, dimensions, and character count, so that I can judge scope the same way I can in Clean HTML.
11. As a user, I want `<h1>`-`<h4>` converted to `#`-`####`, so that the document outline survives the copy.
12. As a user, I want `<h5>` and `<h6>` rendered as a bold line, so that deeper headings still stand out even though ATX depth is capped at 4.
13. As a user, I want `<strong>`/`<b>` as `**bold**`, `<em>`/`<i>` as `*italic*`, and `<del>`/`<s>` as `~~strikethrough~~`, so that inline emphasis is preserved.
14. As a user, I want `<code>`, `<kbd>`, `<samp>`, and `<var>` wrapped in backticks, so that inline code stays distinguishable.
15. As a user, I want an inline element carrying the `mdx-code` class also treated as inline code, so that HelloInterview's `event_id`-style inline code (a `<span>`, not a `<code>`) is wrapped in backticks.
16. As a user, I want no other CSS class inspected, so that the conversion stays predictable and does not drift into guessing at arbitrary styling.
17. As a user, I want `<pre>` (and `<pre><code>`) emitted as a fenced block with its content verbatim and no language tag, so that code samples paste as real code blocks. The language lives in a class or attribute, not a tag, so it is not inferred.
18. As a user, I want `<a href>` as `[text](href)` and `<img>` as `![alt](src)`, so that links and images survive.
19. As a user, I want `<ul>`/`<ol>`/`<li>` rendered as Markdown lists (`-` / `1.`) with nested lists indented, so that list structure is preserved, matching Plain Text's list handling.
20. As a user, I want `<blockquote>` prefixed with `> `, `<hr>` as `---`, and `<br>` as a hard line break, so that these structural tags convert losslessly.
21. As a user, I want `<table>` flattened to plain text rather than converted to a GFM table, so that the mode does not produce broken table markup in the cases where conversion is unreliable.
22. As a user, I want `<style>` and `<script>` text dropped in Markdown mode too, for the same reason as Plain Text.
23. As a user, I want blocks in Markdown mode separated by a blank line, so that paragraphs do not glue together and fenced blocks render correctly.
24. As a user, I want a paragraph line that happens to start with `#`, `>`, `-`, `+`, `*`, or `1.` (each followed by a space) to be backslash-escaped, so that body text is not silently promoted into a heading, quote, or list item.
25. As a user, I want no other escaping, so that technical prose full of `_` and `*` mid-sentence is not peppered with backslashes.
26. As a user, I want Markdown mode's transform to return a string directly and never be routed through the HTML pretty-printer, like Plain Text.
27. As a user, I want Full HTML and Clean HTML unchanged, so that adding two text-shaped modes carries no risk to the modes I already rely on.
28. As a user, I want the mode registry to stay "add a module plus one entry," so that a future fifth mode is still cheap.

## Implementation Decisions

- **Shared tag classification.** The tag-name sets that currently live privately
  inside `formatHTML` (which tags are inline, which are verbatim, which are
  void) move into a small shared module in the utils area. `formatHTML` imports
  them with no behavior change; its existing tests guard that. Plain Text and
  Markdown import the same sets, so all three agree on what "block" and "inline"
  mean.

- **Plain Text walker.** Rewritten around the shared inline/block distinction.
  Block elements emit on their own line; inline elements concatenate; text nodes
  have their internal whitespace collapsed to single spaces so source formatting
  never becomes a line break. `<style>` / `<script>` subtrees contribute no
  text, the same "never content" rule Clean HTML uses. `<pre>` emits its
  `textContent` verbatim with internal newlines kept, trimmed at the ends, as
  its own block. Blocks are joined with a single `\n`; runs of three or more
  newlines collapse to two. The existing list rendering (ordered `1.`, unordered
  `-`, two-space nested indent) is retained.

- **Markdown mode is a new mode module**, appended to the ordered registry as
  the fourth entry, bound to digit key `4`, with its own icon glyph (a Markdown
  "M plus down-caret" in the same stroke style as the existing icons). Label
  metadata matches Clean HTML: tag descriptor, dimensions, and live character
  length. Its transform returns a string and never calls `formatHTML`.

- **Markdown conversion is tag-driven.** Element handling is a switch on tag
  name:
  - `h1`-`h4` take a `#`-`####` prefix; `h5`/`h6` render as `**...**` on their
    own block line.
  - `strong`/`b` -> `**...**`; `em`/`i` -> `*...*`; `del`/`s` -> `~~...~~`.
  - `code`/`kbd`/`samp`/`var` when not inside a `pre` -> `` `...` ``.
    Additionally, an inline element whose class list contains the exact token
    `mdx-code` is treated the same way. This is the single deliberate
    class-based rule, documented as recognizing the HelloInterview / MDX
    renderer's inline-code marker. No other class is read.
  - `pre` (including `pre > code`) -> a fenced block delimited by triple
    backticks with the element's `textContent` verbatim and no info string.
  - `a` with `href` -> `[text](href)`; `img` -> `![alt](src)` using the `alt`
    attribute, which may be empty.
  - `ul`/`ol`/`li` -> Markdown list items (`-` / `N.`), nested lists indented,
    reusing the same structure as Plain Text's list handling.
  - `blockquote` -> each line prefixed `> `; `hr` -> `---` on its own block;
    `br` -> hard line break.
  - `table` and its descendants -> treated as ordinary blocks and inlines
    (flattened text), not converted to GFM table syntax.
  - `style`/`script` -> no text emitted.
  - Unknown or other elements -> transparent: block if the shared set says
    block, inline otherwise.

- **Markdown escaping** is limited to structural promotion at the start of an
  emitted paragraph line. Before emitting a text line that Markdown mode did not
  itself prefix (its own headings, list markers, blockquote lines) and that is
  not inside a fence, a leading `#`, `>`, `-`, `+`, or `*` (each only when
  followed by a space) or a leading run of digits then `.` then a space is
  backslash-escaped (`\#`, `\>`, `\-`, `\+`, `\*`, and the dot in `1\.`).
  Nothing mid-line, nothing else. In particular `_` and mid-sentence `*` are
  never escaped.

- **Markdown block separation** is a blank line (`\n\n`) between blocks; runs of
  three or more newlines collapse to two; leading and trailing whitespace is
  trimmed.

- **No change** to Full HTML, Clean HTML, `formatHTML`'s output, the inspect
  lifecycle, arrow navigation, scrolling, the clipboard write, or persistence.
  The new mode id persists through the same `chrome.storage.local` key as the
  other modes.

- **Renderer provenance (context, not a dependency).** The `mdx-*` classes on
  the target pages come from HelloInterview's own MDX component mapping;
  standard MDX emits bare tags. Code blocks are highlighted by Shiki. Only
  `mdx-code` is acted on; the other `mdx-*` classes sit on semantic tags that
  are already handled.

## Worked Example

Input: the "API Types" section of a HelloInterview lesson (an `<ol>` of three
`<li>`, each an `mdx-p` `<div>` with a bold lead-in, inline `mdx-code` spans, and
an `mdx-a` link), preceded by an `<h2>` and a paragraph, with a Shiki `<pre>`
code block and an inline SVG whose `<style>` carries a base64 `@font-face`.

### Plain Text, before this spec

```text
Course · 02 FoundationsAPI DesignAPI design principles and patterns for system
design interviews… In an interview, you'll typically choose between three main
API protocols: REST (Representational State Transfer) - REST uses standard HTTP
methods… @font-face { font-family: Excalifont; src: url(data:font/woff2;base64,
d09GMgABAAAAAABZAAA4AAAAAJlw…   ← kilobytes of base64
…GET /events # Get all events GET /events/{id} # Get a specific event GET…
                                ← the <pre> collapsed onto one line
```

### Plain Text, after this spec

```text
Course · 02 Foundations
API Design
API design principles and patterns for system design interviews…
In an interview, you'll typically choose between three main API protocols:
1. REST (Representational State Transfer) - REST uses standard HTTP methods…
2. GraphQL - Unlike REST's fixed endpoints…
3. RPC (Remote Procedure Call) - RPC protocols like gRPC…
                                ← <style>/<script> text gone
GET /events                    # Get all events
GET /events/{id}               # Get a specific event
                                ← <pre> kept verbatim, its own block
```

### Markdown mode, same input

(outer fence shown as `~~~` so the inner code fence is literal)

~~~markdown
## API Types

In an interview, you'll typically choose between three main API protocols:

1. **REST (Representational State Transfer)** - REST uses standard HTTP methods (GET, POST, PUT, DELETE)…
2. **GraphQL** - Unlike REST's fixed endpoints, GraphQL uses a single endpoint…
3. **RPC (Remote Procedure Call)** - …an RPC call like `checkPermission(userId, resource)` is more natural… (see [Networking Essentials](/learn/courses/system-design/lesson/foundations/networking-essentials)…).

### REST

#### Resource Modeling

```
GET /events                    # Get all events
GET /events/{id}               # Get a specific event
```

##### API Keys
~~~

The last line shows `<h5>` rendering as `**API Keys**` on its own block rather
than `#####`, per the h4 ATX cap.

### Markdown `transform` dispatch

From the design session, the walk is a switch on tag name; block results join
with `\n\n`, inline results concatenate:

```text
walk(el)
  block:
    h1–h4        -> "#"…"####" + text
    h5–h6        -> "**" + text + "**"
    pre          -> ``` fence, textContent verbatim, no info string
    ul/ol/li     -> "-" / "N."  (nested lists indented two spaces)
    blockquote   -> "> " per line
    hr           -> "---"
    table        -> flattened (no GFM table syntax)
    style/script -> ""  (dropped)
    div/p/other  -> transparent; block per the shared tag sets
  inline:
    strong/b     -> **…**
    em/i         -> *…*
    del/s        -> ~~…~~
    code/kbd/samp/var  OR  class token "mdx-code"  (not inside pre)  -> `…`
    a[href]      -> [text](href)
    img          -> ![alt](src)
    br           -> hard line break
    span/other   -> transparent; inline per the shared tag sets
  text node:
    collapse internal whitespace to single spaces
    at line start only, before a following space: escape a leading
      #  >  -  +  *   and a leading "<digits>." (escape the dot)
```

## Testing Decisions

- **Seam.** The existing `mode.transform(element)` boundary, a pure function
  from a DOM element to a string, is the single seam. It is exercised exactly as
  the current mode tests are: build an element from an HTML string, call
  `transform`, assert on the returned text. No new seam is introduced. The
  shared tag-set module has no behavior of its own to test; `formatHTML`'s
  existing tests confirm the extraction did not change it.

- **What a good test asserts.** The output string for a given input subtree, not
  which private helper produced it and not traversal order. Each test reads as
  "this HTML copies as this text / this Markdown."

- **Modules tested.**
  - Plain Text: `<style>` / `<script>` exclusion; one-block-per-line
    separation; inline flow; `<pre>` verbatim; single-newline separation and the
    three-or-more collapse; headings as bare lines; the existing list behavior
    still correct. Prior art: the current Plain Text and list cases in the mode
    test file.
  - Markdown: heading-depth mapping including the `h5`/`h6` bold fallback; the
    three emphasis conversions; inline code including the `mdx-code` class case;
    fenced `<pre>` verbatim with no language; links and images; list conversion
    with nesting; blockquote, hr, br; table flattening; the leading-token
    escapes and that mid-line `*` / `_` are left alone; blank-line block
    separation. Prior art: the same file, the same style as Clean HTML's
    serializer tests.
  - Mode registry: the ordered list now has four entries with keys `1`-`4`.
    Prior art: the existing "registry lists exactly the shipped modes, in key
    order" test.
  - Mode switching: pressing `4` during inspection selects Markdown (label icon
    updates, no copy triggered, target unchanged). Prior art: the existing
    digit-key switching test in the Robber test file.

- The full suite runs once at the end; typechecking runs throughout.

## Out of Scope

- GFM table conversion. Tables flatten to text.
- Syntax-highlight language detection for fenced blocks. It lives in a class or
  attribute, not a tag.
- Any CSS-class-driven conversion other than the single `mdx-code` inline-code
  rule.
- Full Markdown escaping (mid-line `*`, `_`, backtick, `[`, `]`, `|`, HTML
  entities). Only leading structural tokens are escaped.
- A fifth screenshot or image-producing mode (already out of scope in 01).
- Rewriting `README.md` or `.specs/00`/`01`/`02`. Deferred to the consolidation
  pass. Spec 01 still says Plain Text is "just the text, no tags"; that wording
  is reconciled in the consolidation, not here.
- Changes to Full HTML or Clean HTML.

## Further Notes

- This continues the pattern from 02: a small change decided in a `/grill-me`
  session, filed as the next numbered spec under `.specs/` because the project
  has no external issue tracker. It folds into the 00+01+02+03 consolidation
  once that happens.
- The Plain Text list numbering and bulleting shipped as a follow-on to 01
  before this spec. This spec extends the same structural idea to non-list
  blocks and does not re-describe the list rules.
- Markdown mode is explicitly best-effort. The guiding rule from the design
  session: convert only what an HTML tag guarantees with certainty, drop what
  only a CSS class would tell you, with `mdx-code` as the one pragmatic
  exception because the target content is MDX-rendered and that class is a
  reliable inline-code marker.
