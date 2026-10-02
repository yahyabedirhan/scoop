# Handoff — Scoop (Chrome inspect-and-copy extension)

Date: 2026-09-03 (last updated after the keyboard-shortcut change, commit `eab7697`)
Project: `personal-projects/scoop/` (inside the job-search vault, tracked there,
no nested git repo)

## What this is

A small Chrome MV3 extension. Toolbar icon or a keyboard shortcut toggles an
"inspect mode": hover highlights the element under the cursor, arrow keys walk
the DOM, click or Enter copies that element's raw `outerHTML` to the clipboard,
then inspect mode exits.

## Current status: done and working

The user confirmed the core behaviors work. Everything is implemented,
unit-tested where pure, and verified in a real browser via a local
`python3 -m http.server` + the in-app Browser pane (injecting `lib/dom-nav.js` +
`content.js` with a stubbed `window.chrome`). 12/12 unit tests pass
(`npm test` → `node --test`). The keyboard shortcut (`chrome.commands`) can only
be verified in a real Chrome load, not the Browser pane.

There is no outstanding task. This handoff exists only to carry context if the
user comes back with more changes.

## Authoritative sources (do not re-derive)

- **Spec**: [`.specs/00-scoop.md`](../.specs/00-scoop.md) — a clean latest-state
  spec (rewritten in `1da0611`, kept current since). The single source of truth
  for intended behavior; check it before changing anything.
- **README**: [`../README.md`](../README.md) — user-facing usage + unpacked
  install instructions.
- **Code**: `manifest.json`, `background.js` (service worker), `content.js`
  (inspect-mode controller), `content.css` (scoped `all: initial` styles),
  `lib/dom-nav.js` (pure `nextTarget` / `describeElement` / `isSkippable`),
  `tools/gen-icons.py` (pure-stdlib icon generator, 4x supersampled),
  `test/dom-nav.test.js`, `demo.html` (manual test page).
- **Git history** (`git log --oneline -- personal-projects/scoop/`): the
  requirement-by-requirement evolution lives here, starting `0f15a2c`. Notable:
  `bf5df3b` renamed `inspect-copy-extension/` → `scoop/` and replaced the icon.

## Key design decisions already made (see spec for detail)

- Plain JS, no build step. `activeTab` + `scripting` only, on-demand injection.
- Two entry points routed through one `toggleOnTab(tab)` in `background.js`: the
  toolbar icon (`chrome.action.onClicked`) and a `toggle-scoop` keyboard command
  (`chrome.commands.onCommand`), default `Ctrl+Shift+S` / `Command+Shift+S` on
  macOS. Chrome forbids a bare `Shift+S` (needs a Ctrl/Alt/Command modifier);
  user rebinds at `chrome://extensions/shortcuts`. `commands` needs no permission.
- Arrow traversal: Up = prev sibling else parent; Down = next sibling else
  nearest following element of an ancestor (lone-child gap-jump); Left = parent
  (stops at `<html>`); Right = first child. Skips `head`/`meta`/`title`/`script`/
  `link`/`style`/`base`/`noscript` and the extension's own overlay in every
  direction.
- Auto-scroll on arrow move: `scrollIntoView` on nearest scrollable ancestor +
  temporary 96px `scroll-margin`, aligned to whichever viewport edge the target
  passed (bottom-align when below the fold, top-align when above; tall elements
  always top-align).
- Copy: capture-phase suppression of mousedown/mouseup/click; `navigator.
  clipboard.writeText` with textarea+`execCommand` fallback. Exit is synchronous
  on Esc/toggle-off, deferred (~1.6s, after toast fade) on successful copy.

## Verification notes for the next session

- The Browser pane's `requestAnimationFrame` is throttled when the tab is
  backgrounded — `tabs_select` to foreground tab-3 before any test that awaits
  rAF, or use `setTimeout` waits instead.
- Loading `file://` or the hook-rendered `data:` snapshot is NOT scriptable for
  sibling `fetch()`. Serve the folder over HTTP and open that URL in a fresh
  Browser tab.
- Full end-to-end (real unpacked load, badge, `chrome://` restrictions) can only
  be done by the user in their own Chrome.

## Suggested skills for the next agent

- **wayfinder** / **to-spec** — only if the user asks for a substantial new
  capability that needs its own planning pass. Small tweaks: just edit and test.
- **code-review** — the user's `/implement` flow expects a review pass after
  non-trivial code changes. (This project has no issue tracker configured, so it
  runs as an inline self-review, not the two-subagent flow.)
- No skill needed for routine bug fixes or spec edits — follow the pattern in
  this conversation: edit → `node --test` → browser-verify via local HTTP server
  → update `.specs/00-scoop.md` and README → commit with a lowercase multi-line
  message ending `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

## Vault conventions that apply

- Commit messages: lowercase, multi-line, bullet explanations (see
  `CLAUDE.md`). Only `git add`/`commit` when the user asks (they have been
  asking each time here).
- Avoid em dashes in prose and notes.
