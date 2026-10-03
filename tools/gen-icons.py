#!/usr/bin/env python3
"""Generate the Scoop extension icons (16/32/48/128) and README logos as RGBA PNGs.

The mark, `spoon-pointer`, is drawn once as a black SVG master at
assets/images/logo/scoop.svg. A page outline is missing a softened block from
its lower-right corner, and a spoon drawn as a mouse pointer (the bowl is the
arrowhead, the flared handle its tail) carries that block in its bowl, turned
to the spoon's axis. This script reads the master's paths and fills them, so
the master is the one place the shape is edited.

The mark is set on a squircle tile with a soft vertical gradient, in the
format of Shipyard's logo, in two colourways. The green tile carries the mark
in cream under a white sheen. The white tile carries the mark in pistachio
inside a hairline edge from 48 px up, so it keeps its outline on a white page. The extension
icons use the white tile. The 48 and 128 px icons keep Chrome's transparent
margin, and the 16 and 32 px tiles fill the canvas with the mark drawn larger
on them. Both colourways are written at 512 px for the README. Icons below
DETAIL_MIN px are drawn from a second master, scoop-16.svg, the same mark
redrawn with heavier strokes and wider gaps so it holds at 16 px.

The master may use only absolute M, L, H, V, A and Z path commands, with each
path filled even-odd. Pure standard library, supersampled for clean edges, and
deterministic. Re-run after editing the master or the colours. Rejected icons
are kept as PNGs under assets/images/logo/archive/, which this script never
writes or deletes.

Variants. The masters above are the variant `current`, today's icon, and
SHIPPED names the variant written as the icons and README logos. Every folder
under assets/images/logo/variants/ is another variant, named after the folder,
with its own scoop.svg and scoop-16.svg. A variant's viewBox is the tile
itself, so its masters alone decide how much of the tile the mark fills.
`--variant NAME` draws that variant instead of SHIPPED. `--review` writes
review images instead of the shipped files, into
assets/screenshots/icon-legibility/<name>/. Its toolbar.png shows the 16, 32
and 48 px icons at actual size on a light and a dark toolbar, then the 16 px
icon magnified, and its logo.png shows both 512 px README logos. With
`--variant` it writes only that variant's two images. Without it, it writes
them for every variant and adds overview.png, one row per variant.
"""
import argparse
import math
import os
import re
import struct
import zlib

SIZES = (16, 32, 48, 128)
DETAIL_MIN = 32              # smallest icon drawn from the full master
ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
OUT_DIR = os.path.join(ROOT, "icons")
LOGO_SIZE = 512
LOGO_DIR = os.path.join(ROOT, "assets", "images", "logo")
LOGO_PATH = os.path.join(LOGO_DIR, "scoop.png")
LOGO_WHITE_PATH = os.path.join(LOGO_DIR, "scoop-on-white.png")
MASTER_PATH = os.path.join(LOGO_DIR, "scoop.svg")
SMALL_MASTER_PATH = os.path.join(LOGO_DIR, "scoop-16.svg")
VARIANT_DIR = os.path.join(LOGO_DIR, "variants")  # one folder of masters per prototype
REVIEW_DIR = os.path.join(ROOT, "assets", "screenshots", "icon-legibility")
CURRENT = "current"          # the variant drawn from the masters above, today's icon
SHIPPED = CURRENT            # the variant written as the extension icons and README logos

# Pistachio: Shipyard's khaki shifted to hue 140 in OKLCH (lightness +0.02,
# chroma x0.95). The green tile's figure is Shipyard's cream. The white tile's
# figure green sits between the green tile's two stops, and its bottom stop and
# edge are a faint pistachio grey.
TILE_TOP = (0x6D, 0xA3, 0x61)     # #6da361
TILE_BOTTOM = (0x55, 0x7F, 0x4B)  # #557f4b
CREAM = (0xFB, 0xF6, 0xEA)        # #FBF6EA
ICON_GREEN = (0x5F, 0x96, 0x53)   # #5f9653
WHITE = (255, 255, 255)
WHITE_BOTTOM = (0xEE, 0xF2, 0xEC)  # #eef2ec
WHITE_EDGE = (0xD3, 0xDB, 0xD0)   # #d3dbd0

# One colourway: tile gradient stops, figure colour, sheen opacity, edge colour.
GREEN_TILE = (TILE_TOP, TILE_BOTTOM, CREAM, 0.14, None)
WHITE_TILE = (WHITE, WHITE_BOTTOM, ICON_GREEN, 0.0, WHITE_EDGE)
ICON_TILE = WHITE_TILE        # the colourway the extension icons use

SQUIRCLE_N = 5               # superellipse exponent of the tile
FIGURE_SPAN = 0.70           # the master's 256 box as a share of the tile
SMALL_FIGURE_SPAN = 0.92     # the same below 48 px, where the mark needs every pixel
MARGIN = {48: 0.06, 128: 0.125, LOGO_SIZE: 0.125}  # transparent margin per side; 0 elsewhere
ARC_STEP = math.radians(3)   # arcs are flattened into chords of at most this angle


def _supersample(size):
    # Small icons have few pixels, so they can afford finer edges.
    return 8 if size < 48 else 4


# ---------- the master ----------

def _arc_points(x0, y0, rx, ry, large, sweep, x1, y1):
    """Points along an unrotated SVG arc from (x0, y0) to (x1, y1), end included.

    Converts the endpoint form to a centre and angles (SVG 1.1, F.6.5).
    """
    hx, hy = (x0 - x1) / 2, (y0 - y1) / 2
    scale = math.sqrt(hx * hx / (rx * rx) + hy * hy / (ry * ry))
    if scale > 1:                 # radii too small for the chord: grow them
        rx, ry = rx * scale, ry * scale
    num = rx * rx * ry * ry - rx * rx * hy * hy - ry * ry * hx * hx
    den = rx * rx * hy * hy + ry * ry * hx * hx
    k = math.sqrt(max(num, 0) / den) * (-1 if large == sweep else 1)
    cx, cy = k * rx * hy / ry + (x0 + x1) / 2, -k * ry * hx / rx + (y0 + y1) / 2
    a0 = math.atan2((y0 - cy) / ry, (x0 - cx) / rx)
    a1 = math.atan2((y1 - cy) / ry, (x1 - cx) / rx)
    delta = a1 - a0
    if sweep and delta < 0:
        delta += 2 * math.pi
    elif not sweep and delta > 0:
        delta -= 2 * math.pi
    steps = max(1, math.ceil(abs(delta) / ARC_STEP))
    return [(cx + rx * math.cos(a0 + delta * i / steps), cy + ry * math.sin(a0 + delta * i / steps))
            for i in range(1, steps + 1)]


def _parse_path(d):
    """The edges of path data `d`, as ((x0, y0), (x1, y1)) pairs over all subpaths."""
    if re.search(r"[^MLHVAZ\d\s.,eE-]", d):
        raise ValueError("the master may use only absolute M, L, H, V, A and Z commands")
    tokens = re.findall(r"[MLHVAZ]|-?\d*\.?\d+(?:[eE]-?\d+)?", d)
    edges, x, y, start, i = [], 0.0, 0.0, None, 0
    points = []

    def close():
        if len(points) > 1:
            edges.extend(zip(points, points[1:] + points[:1]))

    cmd = None
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd == "Z":
                close()
                points = []
                x, y = start
                continue
        args = lambda n: [float(t) for t in tokens[i:i + n]]
        if cmd == "M":
            close()
            x, y = args(2)
            i += 2
            start, points = (x, y), [(x, y)]
            cmd = "L"             # coordinates after M are implicit lines
            continue
        if cmd == "L":
            x, y = args(2)
            i += 2
            points.append((x, y))
        elif cmd == "H":
            (x,) = args(1)
            i += 1
            points.append((x, y))
        elif cmd == "V":
            (y,) = args(1)
            i += 1
            points.append((x, y))
        elif cmd == "A":
            rx, ry, rotation, large, sweep, nx, ny = args(7)
            i += 7
            if rotation:
                raise ValueError("the master's arcs must be unrotated")
            points.extend(_arc_points(x, y, rx, ry, int(large), int(sweep), nx, ny))
            x, y = nx, ny
    close()
    return edges


def load_master(path=MASTER_PATH):
    """The master's viewBox size and one edge list per <path>."""
    src = open(path).read()
    box = float(re.search(r'viewBox="0 0 ([\d.]+) [\d.]+"', src).group(1))
    return box, [_parse_path(d) for d in re.findall(r'<path\b[^>]*\bd="([^"]+)"', src)]


# ---------- rasterising ----------

def _spans(edges, y):
    """Even-odd inside intervals of one path along the horizontal line at `y`."""
    xs = sorted(x0 + (y - y0) * (x1 - x0) / (y1 - y0)
                for (x0, y0), (x1, y1) in edges if (y0 > y) != (y1 > y))
    return zip(xs[0::2], xs[1::2])


def mark_coverage(paths, size, ss, x0, y0, k):
    """Per-pixel share of subsamples inside the mark, drawn at `k` px per unit from (x0, y0) px.

    Paths are filled even-odd each, then united, so a hole in one path is not
    filled by another.
    """
    hi = size * ss
    cover = [0] * (size * size)
    for sy in range(hi):
        y = ((sy + 0.5) / ss - y0) / k
        row = bytearray(hi)
        for edges in paths:
            for a, b in _spans(edges, y):
                lo = max(0, math.ceil((x0 + a * k) * ss - 0.5))
                up = min(hi, math.ceil((x0 + b * k) * ss - 0.5))
                row[lo:up] = b"\x01" * max(0, up - lo)
        base = (sy // ss) * size
        for sx in range(hi):
            if row[sx]:
                cover[base + sx // ss] += 1
    n = ss * ss
    return [c / n for c in cover]


def _mix(base, over, alpha):
    return tuple(b + (o - b) * alpha for b, o in zip(base, over))


def _squircle_coverage(size, ss, half):
    """Per-pixel subsample count inside the centred squircle of half-width `half` canvas units."""
    hi = size * ss
    tile = [0] * (size * size)
    for sy in range(hi):
        dy = abs((sy + 0.5) / hi - 0.5) / half
        if dy >= 1:
            continue
        reach = (1 - dy ** SQUIRCLE_N) ** (1 / SQUIRCLE_N) * half
        lo = max(0, math.ceil((0.5 - reach) * hi - 0.5))
        up = min(hi, math.ceil((0.5 + reach) * hi - 0.5))
        base = (sy // ss) * size
        for sx in range(lo, up):
            tile[base + sx // ss] += 1
    return tile


def render_tile(paths, box, size, colourway, span):
    """RGBA bytes of the mark on a squircle tile in `colourway`, inside the size's margin.

    The master's `box` spans `span` of the tile's width, centred on it.
    """
    top, bottom, ink, sheen, edge = colourway
    ss = _supersample(size)
    margin = MARGIN.get(size, 0.0)
    half = 0.5 - margin                      # tile half-width, canvas units
    t0 = margin * size
    k = span * 2 * half * size / box
    off = t0 + (2 * half * size - box * k) / 2
    figure = mark_coverage(paths, size, ss, off, off, k)
    tile = _squircle_coverage(size, ss, half)
    # The edge is the ring between the tile and a squircle one hairline inside
    # it. Below 48 px a 1 px ring would muddy the tile, so it is left off.
    edge = edge if size >= 48 else None
    inner = _squircle_coverage(size, ss, half - max(1, size / 256) / size) if edge else tile

    px = bytearray()
    n = ss * ss
    for y in range(size):
        t = min(max(((y + 0.5) / size - margin) / (2 * half), 0), 1)  # 0 at the tile's top
        color = _mix(top, bottom, t)
        if t < 0.5:
            color = _mix(color, WHITE, sheen * (1 - 2 * t))
        for x in range(size):
            i = y * size + x
            cover = tile[i] / n
            if cover == 0:
                px += bytes(4)
                continue
            c = color
            if edge:
                c = _mix(c, edge, (tile[i] - inner[i]) / tile[i])
            # The mark lies wholly inside the tile, so its share of the tile's
            # samples is how much of the figure colour covers the pixel.
            c = _mix(c, ink, min(figure[i] / cover, 1))
            px += bytes((round(c[0]), round(c[1]), round(c[2]), round(255 * cover)))
    return bytes(px)


def write_png(path, width, raw, height=None):
    """Write 8-bit RGBA `raw` as a PNG `width` px wide and `height` (default `width`) px tall."""
    height = height or width
    stride = width * 4
    scan = bytearray()
    for y in range(height):
        scan.append(0)
        scan += raw[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(scan), 9)
    with open(path, "wb") as f:
        f.write(sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


# ---------- variants ----------

class Variant:
    """One drawing of the mark, its two masters and the share of the tile each master's box spans."""

    def __init__(self, name, master, small_master, span, small_span):
        self.name = name
        self.box, self.paths = load_master(master)
        small_box, self.small = load_master(small_master)
        # Both cuts are scaled by the full master's box, so they must share it.
        if small_box != self.box:
            raise SystemExit(f"{os.path.relpath(small_master)}: viewBox {small_box:g} differs from "
                             f"{os.path.relpath(master)}'s {self.box:g}")
        self.span, self.small_span = span, small_span

    def icon(self, size, colourway=ICON_TILE):
        """RGBA bytes of the mark at `size` px in `colourway`."""
        paths = self.paths if size >= DETAIL_MIN else self.small
        span = self.span if size >= 48 else self.small_span
        return render_tile(paths, self.box, size, colourway, span)


def variant_names():
    """`current` first, then every folder under VARIANT_DIR in name order."""
    if not os.path.isdir(VARIANT_DIR):
        return [CURRENT]
    return [CURRENT] + sorted(n for n in os.listdir(VARIANT_DIR) if os.path.isdir(os.path.join(VARIANT_DIR, n)))


def load_variant(name):
    if name == CURRENT:
        return Variant(name, MASTER_PATH, SMALL_MASTER_PATH, FIGURE_SPAN, SMALL_FIGURE_SPAN)
    if name not in variant_names():
        raise SystemExit(f"unknown variant {name!r}; known: {', '.join(variant_names())}")
    if not re.fullmatch(r"[a-z0-9-]+", name):
        raise SystemExit(f"variant {name!r} must be named in lowercase kebab-case, as the review labels are")
    folder = os.path.join(VARIANT_DIR, name)
    # A variant's viewBox is the tile itself, so its masters alone decide how
    # much of the tile the mark fills.
    return Variant(name, os.path.join(folder, "scoop.svg"), os.path.join(folder, "scoop-16.svg"), 1.0, 1.0)


# ---------- review images ----------

LIGHT_TOOLBAR = (0xF1, 0xF3, 0xF4)  # Chrome's light toolbar
DARK_TOOLBAR = (0x35, 0x36, 0x3A)   # Chrome's dark toolbar
PAGE = (0xFF, 0xFF, 0xFF)           # GitHub's light page, behind the sheets
INK = (0x3C, 0x40, 0x43)            # label text
TOOLBAR_SIZES = (16, 32, 48)
ZOOM = 4                            # magnification of the 16 px icon after the actual sizes
GAP = 16

# A 3 x 5 bitmap font for the labels, one string of bits per row.
FONT = {c: g.split() for c, g in {
    "a": "010 101 111 101 101", "b": "110 101 110 101 110", "c": "011 100 100 100 011",
    "d": "110 101 101 101 110", "e": "111 100 110 100 111", "f": "111 100 110 100 100",
    "g": "011 100 101 101 011", "h": "101 101 111 101 101", "i": "111 010 010 010 111",
    "j": "001 001 001 101 010", "k": "101 101 110 101 101", "l": "100 100 100 100 111",
    "m": "101 111 111 101 101", "n": "110 101 101 101 101", "o": "010 101 101 101 010",
    "p": "110 101 110 100 100", "q": "010 101 101 110 011", "r": "110 101 110 101 101",
    "s": "011 100 010 001 110", "t": "111 010 010 010 010", "u": "101 101 101 101 111",
    "v": "101 101 101 101 010", "w": "101 101 111 111 101", "x": "101 101 010 101 101",
    "y": "101 101 010 010 010", "z": "111 001 010 100 111", "0": "111 101 101 101 111",
    "1": "010 110 010 010 111", "2": "110 001 010 100 111", "3": "110 001 010 001 110",
    "4": "101 101 111 001 001", "5": "111 100 110 001 110", "6": "011 100 111 101 111",
    "7": "111 001 010 010 010", "8": "111 101 111 101 111", "9": "111 101 111 001 110",
    "-": "000 000 111 000 000", " ": "000 000 000 000 000",
}.items()}
TEXT_SCALE = 2
TEXT_HEIGHT = 5 * TEXT_SCALE
STRIP = 16 * ZOOM + 2 * GAP          # height of one toolbar strip
STRIP_WIDTH = GAP + sum(s + GAP for s in TOOLBAR_SIZES) + 16 * ZOOM + GAP


class Sheet:
    """An opaque RGB canvas that icons are laid onto at whole-pixel positions."""

    def __init__(self, width, height, color):
        self.width, self.height = width, height
        self.px = bytearray(bytes(color) * (width * height))

    def rect(self, x, y, w, h, color):
        for row in range(y, y + h):
            at = (row * self.width + x) * 3
            self.px[at:at + w * 3] = bytes(color) * w

    def paste(self, raw, size, x, y, zoom=1):
        """Lay RGBA bytes `size` px square over the canvas at (x, y), each pixel `zoom` px wide."""
        for row in range(size * zoom):
            for col in range(size * zoom):
                i = ((row // zoom) * size + col // zoom) * 4
                a = raw[i + 3] / 255
                at = ((y + row) * self.width + x + col) * 3
                for c in range(3):
                    self.px[at + c] = round(self.px[at + c] * (1 - a) + raw[i + c] * a)

    def text(self, x, y, label):
        for ch in label.lower():
            for r, bits in enumerate(FONT[ch]):
                for c, bit in enumerate(bits):
                    if bit == "1":
                        self.rect(x + c * TEXT_SCALE, y + r * TEXT_SCALE, TEXT_SCALE, TEXT_SCALE, INK)
            x += 4 * TEXT_SCALE

    def save(self, path):
        raw = bytearray()
        for i in range(0, len(self.px), 3):
            raw += self.px[i:i + 3] + b"\xff"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        write_png(path, self.width, bytes(raw), self.height)
        print("wrote", os.path.relpath(path))


def _strip(sheet, icons, x, y, color):
    """Draw a toolbar strip in `color` with the 16, 32 and 48 px icons at actual size and the 16 px one zoomed."""
    sheet.rect(x, y, STRIP_WIDTH, STRIP, color)
    for s in TOOLBAR_SIZES:
        x += GAP
        sheet.paste(icons[s], s, x, y + (STRIP - s) // 2)
        x += s
    sheet.paste(icons[16], 16, x + GAP, y + GAP, ZOOM)


def review(variant):
    """Write the variant's two review images, `toolbar.png` and `logo.png`, to its own folder."""
    folder = os.path.join(REVIEW_DIR, variant.name)
    icons = {s: variant.icon(s) for s in TOOLBAR_SIZES}
    sheet = Sheet(STRIP_WIDTH + 2 * GAP, 2 * GAP + TEXT_HEIGHT + 2 * STRIP + GAP, PAGE)
    sheet.text(GAP, GAP, f"{variant.name} 16 32 48 px")
    _strip(sheet, icons, GAP, 2 * GAP + TEXT_HEIGHT, LIGHT_TOOLBAR)
    _strip(sheet, icons, GAP, 2 * GAP + TEXT_HEIGHT + STRIP, DARK_TOOLBAR)
    sheet.save(os.path.join(folder, "toolbar.png"))

    # Both README logos at 512 px, green tile then white tile.
    sheet = Sheet(2 * LOGO_SIZE, LOGO_SIZE, PAGE)
    for i, colourway in enumerate((GREEN_TILE, WHITE_TILE)):
        sheet.paste(variant.icon(LOGO_SIZE, colourway), LOGO_SIZE, i * LOGO_SIZE, 0)
    sheet.save(os.path.join(folder, "logo.png"))


def overview(variants):
    """Write one sheet with a row per variant, showing its name, both toolbars and both README logos at 128 px.

    It is 800 px wide, narrow enough for a PR description to show it at actual size.
    """
    row = TEXT_HEIGHT + GAP // 2 + 128 + GAP   # the logos are the tallest item in a row
    sheet = Sheet(GAP + 2 * (STRIP_WIDTH + GAP) + 2 * 128 + GAP, GAP + row * len(variants), PAGE)
    for i, variant in enumerate(variants):
        y = GAP + i * row
        icons = {s: variant.icon(s) for s in TOOLBAR_SIZES}
        sheet.text(GAP, y, variant.name)
        y += TEXT_HEIGHT + GAP // 2
        x = GAP
        for color in (LIGHT_TOOLBAR, DARK_TOOLBAR):
            _strip(sheet, icons, x, y + (128 - STRIP) // 2, color)
            x += STRIP_WIDTH + GAP
        for colourway in (GREEN_TILE, WHITE_TILE):
            sheet.paste(variant.icon(128, colourway), 128, x, y)
            x += 128
    sheet.save(os.path.join(REVIEW_DIR, "overview.png"))


def ship(variant):
    """Write the extension icons and both README logos from `variant`."""
    os.makedirs(OUT_DIR, exist_ok=True)
    for s in SIZES:
        p = os.path.join(OUT_DIR, f"icon{s}.png")
        write_png(p, s, variant.icon(s))
        print("wrote", os.path.relpath(p))
    for p, colourway in ((LOGO_PATH, GREEN_TILE), (LOGO_WHITE_PATH, WHITE_TILE)):
        write_png(p, LOGO_SIZE, variant.icon(LOGO_SIZE, colourway))
        print("wrote", os.path.relpath(p))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--variant", help=f"the variant to draw (default {SHIPPED!r}, the shipped icon)")
    parser.add_argument("--review", action="store_true",
                        help="write review images instead of the shipped files, for --variant alone "
                             "or, without it, for every variant plus the overview sheet")
    args = parser.parse_args()
    if not args.review:
        ship(load_variant(args.variant or SHIPPED))
    elif args.variant:
        review(load_variant(args.variant))
    else:
        variants = [load_variant(n) for n in variant_names()]
        for v in variants:
            review(v)
        overview(variants)


if __name__ == "__main__":
    main()
