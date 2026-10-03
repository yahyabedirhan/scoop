# Chrome Web Store listing

Everything the Chrome Web Store Developer Dashboard asks for when publishing
Scoop, ready to paste. Spec 07 explains how it came about. The store
requirements were checked against developer.chrome.com on 2026-10-03.

## Before you start

1. Register at the
   [Developer Dashboard](https://chrome.google.com/webstore/devconsole). Accept
   the developer agreement and pay the one-time registration fee ($5, plus any
   tax). The account email cannot be changed later.
2. On the dashboard's **Account** page, set a publisher name and verify a
   contact email. Both are required.
3. Merge this release to `main` and push, so the privacy policy link below
   resolves.

## Package

Run `npm run package`. It builds `dist/` and writes
`release/scoop-<version>.zip` with `manifest.json` at its root. In the
dashboard, choose **Add new item** and upload the zip. The name, version, icon
and short description come from `manifest.json` and cannot be edited in the
dashboard.

## Store listing tab

**Description**

```text
Scoop copies any element on a web page to your clipboard, in the shape you need.

Turn it on with the toolbar icon or Cmd+Shift+S (Ctrl+Shift+S on Windows and Linux), point at part of a page, and click. Scoop highlights the element under your pointer and shows what it is before you copy.

Four copy modes, switched with the number keys:
1. Full HTML, exactly as it is on the page, neatly indented.
2. Clean HTML, with styling attributes, icons and layout-only wrappers stripped away.
3. Plain Text, the words with their paragraphs and lists kept.
4. Markdown, ready to paste into your notes.

Fine-tune the selection with the arrow keys: Left for the parent, Right for the first child, Up and Down for the neighbours. Press Esc to leave without copying. Scoop remembers the mode you used last.

Private by design. Scoop only runs in the tab where you turn it on, never sends anything anywhere, and has no analytics. The only thing it stores is your last copy mode.

Open source at https://github.com/yahyabedirhan/scoop
```

**Category** Developer Tools

**Language** English

**Graphic assets**, all in `assets/store/` and rendered by `npm run store-assets`

| Field | File |
| --- | --- |
| Store icon (128x128) | `icons/icon128.png` |
| Screenshots (1280x800), in this order | `screenshot-1.png`, `screenshot-2.png`, `screenshot-3.png` |
| Small promo tile (440x280) | `promo-small.png` |
| Marquee promo tile (1400x560, optional) | `promo-marquee.png` |

**Homepage URL** `https://github.com/yahyabedirhan/scoop`

**Support URL** `https://github.com/yahyabedirhan/scoop/issues`

## Privacy tab

**Single purpose**

```text
Scoop copies a page element the user selects to the clipboard as HTML, clean HTML, plain text or Markdown.
```

**Permission justifications**

| Permission | Justification |
| --- | --- |
| `activeTab` | Scoop works only on the tab where the user clicks its toolbar icon or presses its shortcut. activeTab grants access to that one tab for that moment, so Scoop needs no host permissions. |
| `scripting` | When the user turns Scoop on, it injects its content script and stylesheet into the active tab to draw the highlight box and label and to copy the selected element. |
| `storage` | Scoop remembers which of its four copy modes the user picked last, so the next session starts in that mode. Nothing else is stored. |

**Remote code** No, I am not using remote code.

**Data usage** Tick none of the data types. Tick all three certifications
(no selling of user data, no use beyond the single purpose, no use for
creditworthiness or lending).

**Privacy policy URL**
`https://github.com/yahyabedirhan/scoop/blob/main/PRIVACY.md`

## Distribution tab

- **Payments** Free of charge.
- **Visibility** Public. Choose Unlisted instead for a quiet launch that only
  people with the link can find.
- **Regions** All regions.

## Test instructions tab

```text
No account or setup is needed. Open any web page, click the Scoop toolbar icon (or press Cmd+Shift+S / Ctrl+Shift+S), hover over an element and click it. The element is copied to the clipboard and a small "Copied" toast confirms it. Press 1-4 to switch the copy mode and Esc to leave.
```

## Submit

Click **Submit for review**. To choose the launch moment, untick publishing
automatically after review. An approved item must then be published within 30
days or it returns to draft. Reviews usually take a few days and can take up
to a few weeks, and a first item from a new developer tends to be looked at
more closely.

## After it is published

- TODO: add the listing URL to the README's Install section and record it in
  the Outcome of spec 07.
- Later versions go through the same review. Raise the version, run
  `npm run package`, and upload the new zip on the item's **Package** tab.
