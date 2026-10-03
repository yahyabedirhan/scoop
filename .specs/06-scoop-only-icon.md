# 06 - Scoop-Only Icon

Status: implemented
Last updated: 2026-10-03

Builds on the `scale-up` spoon-pointer icon from spec 05. Covers only the icon,
the two README logos and the SVG master. Inspect mode and copy modes do not
change.

## Problem Statement

The maintainer was still not satisfied with the spec 05 icon. It has two
objects, a page outline at the top left and the spoon-pointer at the bottom
right. The spoon-pointer is the part that carries the idea, and the page beside
it makes the mark busy. The mark also sat off-centre on its tile, and the 16 px
icon was drawn from a separate, simpler master, so it looked different from the
large icon.

## Solution

- Keep only the spoon-pointer and drop the page outline.
- Centre the spoon-pointer on the tile by its exact outline, arcs included, and
  scale it so it spans 160 of the tile's 256 units at its longest side.
- Replace the rounded block in the spoon's bowl with a pair of bold angle
  brackets, `< >`, cut out of the bowl and turned to the spoon's 30° axis, so
  the mark reads as scooping up an HTML element.
- Draw every size from the one master. `scoop-16.svg` is retired.
- Ship the extension icon green on white (`ICON_TILE = WHITE_TILE`). The README
  keeps both colourways side by side.

The maintainer picked the brackets from prototypes of an upright `</>`, a tilted
`</>`, bold `< >`, a hexagon tag chip, `[ ]`, and a solid tag with a slash.
Those prototypes were scratch renders and are not archived.

## Known limits

At 16 px the brackets are only a few pixels wide and read as soft detail inside
the bowl. The spoon-pointer's silhouette is what carries the icon at that size.

## Testing

`test/icons.test.ts` checks that the mark spans more than half of its tile's
height at every size and that it is centred on its tile to within one pixel.
The other icon and logo tests from spec 05 still apply.

## Outcome

Released in 0.0.9 on 2026-10-03.
