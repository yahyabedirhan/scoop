# 07 - Chrome Web Store Release

Status: implemented
Last updated: 2026-10-03

Covers releasing Scoop as 0.1.0 on the Chrome Web Store. Inspect mode and the
copy modes do not change.

## Problem Statement

Scoop is only installable as an unpacked extension from a local build. The
maintainer wants to publish 0.1.0 on the Chrome Web Store and does not want to
work out the store's requirements themselves. Everything that can be prepared
in the repository should be ready, so that the maintainer's part is only the
steps that need their Google account.

## Solution

- Move the version to 0.1.0 in `manifest.json`, `package.json` and
  `package-lock.json`, and record it in the changelog.
- Add `npm run package`, which builds `dist/` and zips its contents into
  `release/scoop-<version>.zip` with `manifest.json` at the zip's root, as the
  store requires. `release/` is gitignored.
- Add `PRIVACY.md`, a privacy policy stating that Scoop collects nothing. The
  store links to it on GitHub.
- Add `docs/store-listing.md`, every text field the Developer Dashboard asks
  for, ready to paste, followed by the maintainer's remaining steps.
- Add `npm run store-assets`, which renders the store's required images with
  headless Chrome from HTML sources in `tools/store-assets/`. That means the
  440x280 small promo tile, the optional 1400x560 marquee tile, and 1280x800
  screenshots. The screenshots run the built `content.js` against a sample
  page through a stub of the `chrome.*` APIs, so they show Scoop's real
  overlay rather than a mock-up.
- Update the README for the store install, keeping the unpacked install for
  development.

## Store requirements checked

From the Chrome Web Store docs on developer.chrome.com, read on 2026-10-03.

- One-time developer registration fee. The docs do not state the amount, and
  Google's older webstore-docs give it as $5.
- The manifest `description` is at most 132 characters.
- A 128 px icon with 96 px of artwork and 16 px of transparent padding per
  side. Scoop's 128 px icon already keeps a 16 px margin (`MARGIN` in
  `tools/gen-icons.py`).
- At least one 1280x800 screenshot and one 440x280 small promo tile.
- A single-purpose statement, a justification for each permission, a remote
  code declaration and the data-use certification on the Privacy tab.
- Every upload must carry a higher version than the last.

## Testing

`test/manifest.test.ts` checks that `manifest.json` and `package.json` carry
the same version, that the description fits the store's 132-character limit,
and that the manifest declares no host permissions or remotely loaded code.
`test/store-assets.test.ts` checks the rendered store images exist at the
sizes the store requires.

## Outcome

TODO: record the listing URL and the publish date once the store approves
0.1.0.
