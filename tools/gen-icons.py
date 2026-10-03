#!/usr/bin/env python3
"""Generate the Scoop extension icons (16/32/48/128) and README logos as RGBA PNGs.

The mark is drawn once as a black SVG master at
assets/images/logo/scoop.svg. It is a spoon drawn as a mouse pointer (the bowl
is the arrowhead, the flared handle its tail) with a pair of angle brackets,
`< >`, cut out of its bowl and turned to the spoon's axis. The mark is centred
on the tile. This script reads the master's paths and fills them, so the
master is the one place the shape is edited. The master's viewBox is the
tile itself, so the master alone decides how much of the tile the mark fills.

The mark is set on a squircle tile with a soft vertical gradient, in the
format of Shipyard's logo, in two colourways. The green tile carries the mark
in cream under a white sheen. The white tile carries the mark in pistachio
inside a hairline edge from 48 px up, so it keeps its outline on a white page.
ICON_TILE picks the extension icons' colourway, the white tile, and setting it
to GREEN_TILE and re-running switches them to white on green. The 48 and
128 px icons keep Chrome's transparent margin, and the 16 and 32 px tiles fill
the canvas. Both colourways are written at 512 px for the README. Every size is drawn
from the same master, so the small icons are the large mark scaled down.

The master may use only absolute M, L, H, V, A and Z path commands, with each
path filled even-odd. Pure standard library, supersampled for clean edges, and
deterministic. Re-run after editing the master or the colours. Rejected icons
are kept as PNGs under assets/images/logo/archive/, which this script never
writes or deletes.
"""
import math
import os
import re
import struct
import zlib

SIZES = (16, 32, 48, 128)
ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
OUT_DIR = os.path.join(ROOT, "icons")
LOGO_SIZE = 512
LOGO_DIR = os.path.join(ROOT, "assets", "images", "logo")
LOGO_PATH = os.path.join(LOGO_DIR, "scoop.png")
LOGO_WHITE_PATH = os.path.join(LOGO_DIR, "scoop-on-white.png")
MASTER_PATH = os.path.join(LOGO_DIR, "scoop.svg")

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
# The extension icons' colourway, the one switch between white on green
# (GREEN_TILE) and green on white (WHITE_TILE). Re-run after changing it.
ICON_TILE = WHITE_TILE

SQUIRCLE_N = 5               # superellipse exponent of the tile
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


def render_tile(paths, box, size, colourway):
    """RGBA bytes of the mark on a squircle tile in `colourway`, inside the size's margin.

    The master's `box` spans the tile.
    """
    top, bottom, ink, sheen, edge = colourway
    ss = _supersample(size)
    margin = MARGIN.get(size, 0.0)
    half = 0.5 - margin                      # tile half-width, canvas units
    t0 = margin * size
    k = 2 * half * size / box
    figure = mark_coverage(paths, size, ss, t0, t0, k)
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


def write_png(path, size, raw):
    stride = size * 4
    scan = bytearray()
    for y in range(size):
        scan.append(0)
        scan += raw[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(scan), 9)
    with open(path, "wb") as f:
        f.write(sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def main():
    box, paths = load_master()
    os.makedirs(OUT_DIR, exist_ok=True)
    for s in SIZES:
        p = os.path.join(OUT_DIR, f"icon{s}.png")
        write_png(p, s, render_tile(paths, box, s, ICON_TILE))
        print("wrote", os.path.relpath(p))
    for p, colourway in ((LOGO_PATH, GREEN_TILE), (LOGO_WHITE_PATH, WHITE_TILE)):
        write_png(p, LOGO_SIZE, render_tile(paths, box, LOGO_SIZE, colourway))
        print("wrote", os.path.relpath(p))


if __name__ == "__main__":
    main()
