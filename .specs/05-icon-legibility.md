# 05 - Icon Legibility

Status: implemented
Last updated: 2026-10-03

Builds on the spoon-pointer icon from spec 04 and the green-on-white tile from
`feat: ship the icon as green on a white tile`. Covers only the icon, the two
README logos and their SVG masters. Inspect mode and copy modes do not change.

## Problem Statement

The maintainer likes the spoon-pointer concept, a spoon shaped like a mouse
pointer carrying a block it has scooped out of a page's corner. In Chrome's
toolbar, though, the icon is tiny. The mark fills only about the middle half of
the white tile, so at 16 and 32 px the page, its missing corner and the block in
the spoon's bowl cannot be told apart. A glance at the toolbar does not say
"this scoops something out of a page". The current 16 px cut also drops the
carried block altogether, which loses the meaning of the icon at the size where
it is seen most.

## Solution

Redesign the mark, keeping the concept and its two actors, the spoon-pointer
and the page it scoops from, so that the icon reads at toolbar size. This is a
design job, not a pixel scale-up. The objects grow, move, and may be redrawn in
a bolder, cartoon-like way so the action of scooping is obvious. Everything the
mark means today must still be there at 16 px, the spoon, the page, and the
piece taken from one and carried by the other.

The small icon and the README logo are both redrawn and stay recognisably the
same mark at a similar visual size. They may differ in detail. The small cut
can be simpler and bolder to read at 16 px, and the README logo can be more
balanced on its tile.

The work is delivered as five prototypes in one PR. The maintainer reviews them
there and picks one, and the same PR then ships the pick.

## User Stories

1. As a Scoop user, I want to recognise the toolbar icon at 16 px, so that I can find Scoop at a glance.
2. As a Scoop user, I want to see that the icon is a spoon scooping something out of a page, so that the icon tells me what the extension does.
3. As a Scoop user, I want the mark to fill its tile with a sensible margin, so that it does not look like a small sticker in an empty square.
4. As a Scoop user on a dark toolbar, I want the icon to stay legible, so that the white tile and green mark still read against a dark background.
5. As a Scoop user, I want the 16, 32, 48 and 128 px icons to look like one mark, so that the toolbar, the extensions page and the store listing agree.
6. As a README reader, I want the logo to look like the toolbar icon, so that I connect the project page with the extension I installed.
7. As a README reader, I want the logo to look balanced on its tile, so that the project page looks finished.
8. As the maintainer, I want five distinct prototypes, so that I can choose between real alternatives instead of one guess.
9. As the maintainer, I want every prototype shown at actual toolbar sizes on light and dark toolbars beside today's icon, so that I judge legibility where it matters.
10. As the maintainer, I want every prototype also shown at README size on both colourways, so that I judge the logo too.
11. As the maintainer, I want to review the prototypes in the PR, so that I do not need to check out the branch to compare them.
12. As the maintainer, I want switching the shipped prototype to be a one-option change in the generator, so that my pick can ship without redrawing anything.
13. As the maintainer, I want the rejected prototypes archived as renders after I pick, so that the record of what was tried survives.
14. As the maintainer, I want the concept kept, the spoon-pointer and the scooped page, so that the icon I liked is improved rather than replaced.
15. As a developer, I want the shape edited in SVG masters rather than in code, so that the masters stay the one place the mark is defined.
16. As a developer, I want the icon tests to keep checking what ships, so that a regenerated icon cannot silently break the manifest's sizes, colours or margins.

## Implementation Decisions

- **Use the logo-design skill.** The redesign follows the user-level
  `logo-design` skill, including its small-size, one-colour and reversed tests
  and its audit scripts. Its 16 px test is the bar every prototype must clear.
- **Concept and actors stay.** Each prototype keeps a spoon shaped like a mouse
  pointer, a page with a piece missing from it, and that piece carried in the
  spoon's bowl. Proportions, positions, stroke weights, gaps and the drawing
  style may change. A bolder, cartoon-like treatment is welcome where it helps
  the mark read.
- **Five directions.** The maintainer agreed to these as the five prototypes.
  Each takes the redesign brief above further in its own way, so the agent may
  adapt the details as the design calls for.
  1. **Scale-up.** Today's layout, enlarged so the mark fills most of the tile.
  2. **Tight diagonal.** Page and spoon pulled together along the diagonal with
     a smaller gap, so both can grow.
  3. **Spoon-led.** A larger spoon and a smaller page, so the scooping action
     dominates.
  4. **Heavy.** Bold, thick strokes and an enlarged notch and carried piece.
  5. **Compact glyph.** The spoon tucks into the page's notch, with only a
     separation gap between them, so the mark reads as one compact shape.
- **Two cuts per prototype, one mark.** Each prototype has a full master for
  the README logos and the larger icons, and a small cut for the smallest
  icons. The two cuts look like the same mark at a similar visual size. The
  small cut may simplify, but it keeps the carried piece.
- **Generator.** The existing icon generator keeps drawing every output from
  the SVG masters under the same path-command rules. Each prototype is a
  variant the generator can be told to draw, and the shipped variant is the
  default. Colours, tile, colourways, sheen and Chrome's transparent margin at
  48 and 128 px do not change.
- **Review material.** The PR shows, for each prototype and for today's icon,
  the 16, 32 and 48 px icons at actual size on a light and a dark toolbar, and
  the 512 px README logo in both colourways. The images live in the repo so the
  PR description can embed them.
- **After the pick.** The picked variant becomes the default and is written as
  the extension icons and both README logos. The other four are archived as
  512 px renders beside the earlier rejected concepts, and their masters and
  review images leave the tree. The spec, README, design doc and changelog
  record the outcome.
- **Release.** The change is a new patch entry in the changelog. Bumping the
  version is part of the eventual release, not this PR, unless the maintainer
  says otherwise at review.

## Testing Decisions

- A good test checks what ships, the icon files the manifest declares and the
  README logos, not how the generator draws them. The existing icon test suite
  is the seam and the prior art, and no new seam is needed.
- Keep the existing checks for sizes, the white tile, the green mark and
  Chrome's margin at 48 and 128 px.
- Add a check that the mark fills more of the tile than it does today, so the
  legibility gain cannot quietly regress. Measure it from the shipped PNGs, for
  example as the green mark's bounding box against the tile.
- Run `npm run typecheck` and `npm test` before calling the work done. Loading
  the extension in Chrome is manual and cannot be verified by an agent, so the
  PR says so.

## Out of Scope

- A new concept or motif. The spoon-pointer and the scooped page stay.
- Changing the palette, the tile shape, the colourways or the `ON` badge.
- Bumping the version or publishing a release.
- Changes to inspect mode, copy modes or anything outside the icon and logos.

## Further Notes

- The maintainer will not answer questions while this is built. Open questions
  are decided by the builder and listed in the PR description for review.
- Spec 04 records the earlier review rounds and the motifs that were rejected.
  None of them should come back.

## Outcome

Added 2026-10-03. It records the maintainer's pick on PR #36 and overrides the
sections above where they disagree.

- **Pick.** `scale-up` ships as the extension icons and both README logos.
  Once it shipped, its masters moved to `assets/images/logo/scoop.svg` and
  `scoop-16.svg`, replacing the masters of the icon before this spec, and the
  generator went back to spec 04's shape of one pair of masters. The variant
  folders, `SHIPPED`, `--variant` and the comparison variant `current` only
  served the pick and are gone. The masters' viewBox is the whole tile, so
  they alone decide how much of it the mark fills. Every shipped PNG stayed
  byte-identical through the move.
- **Archive.** `tight-diagonal`, `spoon-led`, `heavy` and `compact-glyph`
  leave the tree with their masters and review images. Each is kept as a
  512 px render of its README logo on the green tile in
  `assets/images/logo/archive/`.
- **Small cut redrawn.** The maintainer found Scale-up's pixel-stepped 16 px
  cut weird when magnified and preferred the softer look of the icon before
  this spec. The cut is redrawn in that style. It is smooth and antialiased,
  with an outlined page whose notch has a rounded inner corner, and a solid
  pointer. It keeps the carried piece as a rounded square turned to the
  spoon's axis and knocked out of the bowl, as in the full master. Its mark
  spans about 209 by 227 units of the 256 unit tile, against about 180 by 206
  for the 16 px cut before this spec.
- **Colourway changed.** At the maintainer's request the extension icons are
  now white on green, the cream mark on the pistachio tile of the README's
  green logo, instead of green on white. The colourways were out of scope
  above, and this changed at review. The generator's `ICON_TILE` is the one
  switch: setting it to `WHITE_TILE` and re-running `npm run gen-icons`
  restores green on white. The icon tests read the colourway from the shipped
  128 px icon, so they pass for either. Chrome's transparent margin at 48 and
  128 px is unchanged.
- **Size test.** The icon tests measure the mark's bounding box against the
  tile in the shipped 16, 48 and 128 px icons and require it to cover more
  than half. The icon before this spec covered 0.47 at 16 px and 0.32 at 48
  and 128 px. At 32 px it already drew its mark as large as Scale-up does, so
  that size is not checked.
- **Review images.** During review, `npm run icon-review` wrote toolbar and
  README-logo images for `current` and every prototype to
  `assets/screenshots/icon-legibility/`, in both colourways. They served the
  pick, so they and the script left the tree after it shipped. They remain in
  git history at `b1de1b5`.
- **Release.** A new patch entry under Unreleased in the changelog. The version
  stays `0.0.7`.
