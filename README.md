<p align="center"><img src="assets/images/logo/scoop.png" width="128" alt="Scoop's logo: a pistachio scoop of ice cream with a cream mouse pointer over its lower right, on a pistachio green tile"></p>

<h1 align="center">Scoop</h1>

Point at any element on a web page and copy it straight to your clipboard, in
whatever shape you need it: the full HTML, a cleaned-up version, plain text, or
Markdown. Like an ice-cream scoop, it lifts out just the part you want. Scoop
only ever writes to your clipboard and sends nothing anywhere.

It is a local, unpacked Chrome extension. There is no store listing and no
account.

## Why

Getting one specific element off a page usually means opening DevTools, picking
the node, and choosing Copy element, and what you get back is every class, every
`data-*`, and every icon SVG. Most of the time you just want to remember what a
section said, or paste it into your notes, not reproduce how it was built. Scoop
is a one-key way to grab an element and choose how much of it comes across.

## How it works

1. Click the **Scoop** toolbar icon, or press **Cmd+Shift+S** (macOS) /
   **Ctrl+Shift+S** (Windows/Linux). An `ON` badge appears on the icon and the
   page switches to a crosshair cursor. This only affects the tab you turned it
   on in.
2. Move the mouse. The element under the cursor is highlighted with a blue box,
   and a floating label names it and previews what would be copied.
3. Fine-tune the selection with the arrow keys, without moving the mouse:
   - **Up / Down** previous / next element (falls back to the parent, or to the
     next element further up, so a lone child still steps somewhere)
   - **Left** parent element
   - **Right** first child element

   Traversal skips `head`, `script`, `style` and friends, so **Right** on
   `<html>` lands on `<body>`. Moving the mouse again always re-selects whatever
   is under the cursor.
4. Press **1**–**4** to pick the copy mode (see below). The label updates to
   show the active mode's icon and a live preview. Your choice is remembered for
   next time.
5. **Click** the element, or press **Enter**, to copy it. A small toast confirms
   what was copied, and inspect mode turns itself off.
6. Press **Esc**, press the shortcut again, or click the toolbar icon to leave
   inspect mode without copying.

The copy is page content only. Scoop's own highlight box, label, and toast are
never included, and any temporary change Scoop made to the page is undone before
the copy is taken, even when you copy `<body>` or the whole `<html>`.

Chrome does not allow a bare `Shift+S` for extension shortcuts, so the default
needs a `Ctrl` / `Alt` / `Command` modifier. Rebind it at
`chrome://extensions/shortcuts`.

## Copy modes

Press the number key while inspecting to switch. The choice persists across
sessions, so a new inspection starts in the mode you last used.

| Key | Mode | What you get |
| --- | --- | --- |
| **1** | Full HTML | The selected HTML exactly as it is on the page, pretty-printed with 2-space indentation. Nothing removed. |
| **2** | Clean HTML | The same structure with the noise stripped: styling and behavior attributes gone (only things like image sources and link targets kept), empty and icon-only subtrees dropped, layout-only wrappers unwrapped. |
| **3** | Plain Text | The words, with their block structure but no markup. Each paragraph, heading, and list item on its own line; lists numbered or bulleted; code blocks kept verbatim; inline scripts and style blocks dropped. |
| **4** | Markdown | A best-effort Markdown version for pasting into notes: headings, bold / italic / strikethrough, inline and fenced code, links, images, lists, blockquotes, and rules. Only what the HTML tags say is converted; styling classes are ignored. Tables are flattened to text. |

The hover label shows a live character count of what would actually be copied
for Clean HTML, Plain Text, and Markdown, so you can judge scope before you
click.

## Install

1. Run `npm install`, then `npm run build`. This produces a `dist/` folder,
   which is the complete, self-contained extension.
2. Open `chrome://extensions` and enable **Developer mode** (top right).
3. Click **Load unpacked** and choose the `dist/` folder.
4. Pin the icon from the puzzle-piece menu.

The extension stays installed across restarts as long as the folder stays put.

### After changing the code

- Run `npm run build` again, or leave `npm run dev` running for a watch build.
- Click the reload icon on the extension card in `chrome://extensions`.
- Reload any page you want to test on. The content script is injected fresh on
  each activation and does not hot-update an already-open page.

## Development

| Command | What it does |
| --- | --- |
| `npm run build` | Build `dist/` (two passes: the content script and the service worker). |
| `npm run dev` | The same build in watch mode. |
| `npm run typecheck` | `tsc --noEmit` in strict mode. |
| `npm test` | Run the test suite with Vitest (jsdom, with the icon-file suite in Node). |
| `npm run gen-icons` | Regenerate the toolbar and extension icons at 16, 32, 48 and 128 px, a pistachio ice-cream ball with a scalloped base and a cream mouse pointer over its lower right, on a pistachio squircle tile, plus the 512 px README logo at `assets/images/logo/scoop.png` and a 512 px preview beside it of each prototype icon (`tools/gen-icons.py`, standard library only). |

The source is TypeScript under `src/`, built by Vite. `dist/` is generated and
gitignored. `demo.html` is a manual test page with nested lists, links, and
buttons.

- **[`docs/scoop-v01.md`](docs/scoop-v01.md)** is the full reference: how every
  piece works, the module layout, and the low-level design.
- **[`CHANGELOG.md`](CHANGELOG.md)** is the version history.

### Alternate icons

TODO: the maintainer picks the final icon at review. Remove the figures not
picked from `tools/gen-icons.py`, with their previews and this section.

`pointer` ships as the icon, the logo at the top of this file. Each other
figure in `tools/gen-icons.py` is a prototype, written as a 512 px preview
`scoop-<figure>.png` beside the README logo. The two candidates are these.

| Figure | Preview | Description |
|---|---|---|
| `pointer` | <img src="assets/images/logo/scoop.png" width="64" alt="pointer icon"> | A pistachio ball with a scalloped base and a cream mouse pointer over its lower right. The icon that ships. |
| `clipboard` | <img src="assets/images/logo/scoop-clipboard.png" width="64" alt="clipboard icon"> | A cream clipboard with its clip and a round pistachio scoop on the board. |

To ship a prototype instead, run `npm run gen-icons -- --variant <figure>`.
That writes the chosen figure as the extension icons and README logo, and a
preview of each figure not shipped. `npm run gen-icons` on its own restores
`pointer`.

The rejected `brackets`, `ball`, `cone-cursor`, `bite`, `monogram` and
`window-cup` icons are kept as a record in
[`assets/images/logo/archive/`](assets/images/logo/archive/), which the
generator never touches. Git history keeps their code.

## Not included

Iframes and cross-origin frames (Scoop works on the top document only), CSS
selectors or XPath, computed styles, screenshots, a toolbar popup or options
page, SVG-aware cleaning, GFM tables in Markdown mode, and non-Chromium
browsers. See [`docs/scoop-v01.md`](docs/scoop-v01.md) for the complete list.
