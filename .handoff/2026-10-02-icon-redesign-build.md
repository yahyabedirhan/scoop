# Handoff: build the icon redesign

Date: 2026-10-02

Follows `.handoff/2026-10-02-icon-redesign.md`, which started the effort. The
thinking is done. The next session orchestrates the build and opens the PR.

## Where things are

- Effort: `icon-redesign`, issue label `effort:icon-redesign`.
- Worktree: `/Users/yahyabedirhanpak/.treehouse/scoop-abb122/1/scoop`, leased
  through `treehouse` (holder `icon-redesign`).
- Branch: `feat/icon-redesign`, pushed to `origin`. It holds the spec at
  `.specs/04-icon-redesign.md` and both handoffs. No code has changed yet.
- Spec: "Spec: icon redesign",
  https://github.com/yahyabedirhan/scoop/issues/9. It is the source of truth
  for colours, geometry, sizes and tests. Do not restate it.
- Tickets (native GitHub blocking links, all `ready-for-agent`):
  - #10 Draw the brackets icon on a pistachio tile. No blockers.
  - #11 Colour the ON badge deep pistachio. No blockers.
  - #12 Open the README with the Scoop logo. Blocked by #10.
  - #13 Keep the pointer and ball icons as alternates. Blocked by #12.
  - #14 Release 0.0.7. Blocked by #10–#13.
- Prototype: branch `prototype/icon-redesign` (pushed), file
  `tools/icon-prototype.html`. It is the reference drawing for all three
  variants (`brackets`, `pointer`, `ball`). Read the motif code there with
  `git show prototype/icon-redesign:tools/icon-prototype.html`. Never merge
  that branch into the effort branch.

## Decisions settled with the maintainer

- Shipyard's format is the baseline, a flat figure on a squircle tile.
- Pistachio was chosen and mint was rejected. The ball is in a light tint of
  the tile hue.
- The maintainer delegated the remaining choices. The shipped motif is the
  ball in `<tag>` brackets, and the badge goes deep pistachio. The pointer and
  ball variants ship as alternates until PR review.
- Release as `0.0.7`.
- The maintainer gives feedback on the icon after seeing it, so swapping the
  shipped variant must stay a one-option change in the generator.

## Notes for the build

- The SVG prototype and the Python SDF rasterizer will not match pixel for
  pixel. Tune the 16 px icon against the generator's real output, not the
  prototype. The 16 px silhouette must still read as `<●>`.
- The build copies `icons/` into `dist/` whole, so the alternates live beside
  the README logo under `assets/images/logo/`, never in `icons/`.
- Loading the extension in Chrome is manual. The PR must say no browser check
  happened. Headless Chrome screenshots of the PNGs are fine for self-review.
- Project rules in `AGENTS.md` cover commit style, writing style, and
  `npm run typecheck` plus `npm test` before done.

## Reaching the thinking session

The session that wrote this runs in Herdr, pane `w1Q:p1`, and can be prompted
there with a question about intent. Prefer deciding small open questions
yourself and listing them in the PR description.

## Suggested skills

- `orchestrate-effort` / `orchestrating`: run the tickets through delegates
  and deliver the PR.
- `implement` and `tdd`: for delegates working a ticket.
- `to-pr`: open the pull request.
- `herdr`: only to message the thinking session.
