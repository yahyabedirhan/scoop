#!/usr/bin/env python3
"""Generate the Scoop extension icons (16/32/48/128) and README logo as RGBA PNGs.

The mark, `spoon-pointer`, is drawn once as a black SVG master at
assets/images/logo/scoop.svg. A page outline is missing a softened block from
its lower-right corner, and a spoon drawn as a mouse pointer (the bowl is the
arrowhead, the flared handle its tail) carries that block in its bowl, turned
to the spoon's axis. This script reads the master's paths and fills them, so
the master is the one place the shape is edited.

The extension icons are the mark in pistachio on a transparent canvas, a green
that keeps 3:1 contrast on Chrome's light and dark toolbars. The 48 and 128 px
icons keep Chrome's transparent margin; the 16 and 32 px icons crop to the mark
so it fills the canvas. The 512 px README logo sets the mark in cream on a
pistachio squircle tile with a soft vertical gradient and a white sheen, in the
format of Shipyard's logo, with the 128 px icon's margin. Icons below
DETAIL_MIN px are drawn from a second master, scoop-16.svg, the same mark
redrawn with heavier strokes and wider gaps so it holds at 16 px.

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
DETAIL_MIN = 32              # smallest icon drawn from the full master
ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
OUT_DIR = os.path.join(ROOT, "icons")
LOGO_SIZE = 512
LOGO_DIR = os.path.join(ROOT, "assets", "images", "logo")
LOGO_PATH = os.path.join(LOGO_DIR, "scoop.png")
MASTER_PATH = os.path.join(LOGO_DIR, "scoop.svg")
SMALL_MASTER_PATH = os.path.join(LOGO_DIR, "scoop-16.svg")

# Pistachio: Shipyard's khaki shifted to hue 140 in OKLCH (lightness +0.02,
# chroma x0.95). The README figure is Shipyard's cream. The icon green sits
# between the tile's two stops, the one shade with at least 3:1 contrast on
# white, #F1F3F4, #35363A and #202124 toolbars.
TILE_TOP = (0x6D, 0xA3, 0x61)     # #6da361
TILE_BOTTOM = (0x55, 0x7F, 0x4B)  # #557f4b
CREAM = (0xFB, 0xF6, 0xEA)        # #FBF6EA
ICON_GREEN = (0x5F, 0x96, 0x53)   # #5f9653
WHITE = (255, 255, 255)

SQUIRCLE_N = 5               # superellipse exponent of the tile
SHEEN_ALPHA = 0.14           # white at the tile's top, fading out at its middle
FIGURE_SPAN = 0.70           # the master's 256 box as a share of the tile
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


def _bounds(paths):
    xs = [p[0] for edges in paths for edge in edges for p in edge]
    ys = [p[1] for edges in paths for edge in edges for p in edge]
    return min(xs), min(ys), max(xs), max(ys)


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


def render_icon(paths, size):
    """RGBA bytes of the mark in ICON_GREEN on transparent, cropped to the mark inside the margin."""
    bx0, by0, bx1, by1 = _bounds(paths)
    margin = MARGIN.get(size, 0.0) * size
    room = size - 2 * margin
    k = room / max(bx1 - bx0, by1 - by0)
    ox = margin + (room - (bx1 - bx0) * k) / 2 - bx0 * k
    oy = margin + (room - (by1 - by0) * k) / 2 - by0 * k
    cover = mark_coverage(paths, size, _supersample(size), ox, oy, k)
    return b"".join(bytes((*ICON_GREEN, round(255 * c))) for c in cover)


def render_logo(paths, box, size=LOGO_SIZE):
    """RGBA bytes of the mark in cream on the pistachio squircle tile."""
    ss = _supersample(size)
    margin = MARGIN[size]
    half = 0.5 - margin                      # tile half-width, canvas units
    t0 = margin * size
    k = FIGURE_SPAN * 2 * half * size / box
    off = t0 + (2 * half * size - box * k) / 2
    figure = mark_coverage(paths, size, ss, off, off, k)

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

    px = bytearray()
    n = ss * ss
    for y in range(size):
        t = min(max(((y + 0.5) / size - margin) / (2 * half), 0), 1)  # 0 at the tile's top
        color = _mix(TILE_TOP, TILE_BOTTOM, t)
        if t < 0.5:
            color = _mix(color, WHITE, SHEEN_ALPHA * (1 - 2 * t))
        for x in range(size):
            cover = tile[y * size + x] / n
            if cover == 0:
                px += bytes(4)
                continue
            # The mark lies wholly inside the tile, so its share of the tile's
            # samples is how much cream covers the pixel's tile colour.
            c = _mix(color, CREAM, min(figure[y * size + x] / cover, 1))
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
    _, small = load_master(SMALL_MASTER_PATH)
    os.makedirs(OUT_DIR, exist_ok=True)
    for s in SIZES:
        p = os.path.join(OUT_DIR, f"icon{s}.png")
        write_png(p, s, render_icon(paths if s >= DETAIL_MIN else small, s))
        print("wrote", os.path.relpath(p))
    write_png(LOGO_PATH, LOGO_SIZE, render_logo(paths, box))
    print("wrote", os.path.relpath(LOGO_PATH))


if __name__ == "__main__":
    main()
