#!/usr/bin/env python3
"""Generate the Scoop extension icons (16/32/48/128) and README logo as RGBA PNGs.

Motif: a scoop of pistachio ice cream with a scalloped base and a cream mouse
pointer over its lower right, as a flat figure on a pistachio squircle tile
with a soft vertical gradient and a white sheen, in the format of Shipyard's
logo. The figure has no outline.
Below DETAIL_MIN px it drops its details and grows 10%, so the small icon is
the bare silhouette. The 48 and 128 px tiles keep Chrome's transparent margin;
the smaller tiles fill the canvas. The 512 px README logo keeps the 128 px
margin, so it matches the toolbar icon and Shipyard's logo on GitHub.

Each figure is a draw function in FIGURES, keyed by name, returning its
layers. Every size is rendered by the same `render`, so a new figure or a new
output size needs no change to the renderer. Pure standard library,
supersampled for clean edges, and deterministic. Re-run after tweaking
geometry or colours.

`--variant` picks the figure shipped as the icons and README logo, `pointer`
by default. Every other figure is written as a 512 px preview beside the
logo, `scoop-<figure>.png`, never into icons/, which the build copies into
dist/ whole. The shipped figure's own preview is deleted, so switching back
and forth leaves no stale file. Rejected figures are kept as PNGs under
assets/images/logo/archive/, which this script never writes or deletes.
"""
import argparse
import math
import os
import struct
import zlib

SIZES = (16, 32, 48, 128)
DETAIL_MIN = 32              # smallest size that gets the figure's details
ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
OUT_DIR = os.path.join(ROOT, "icons")
LOGO_SIZE = 512
LOGO_DIR = os.path.join(ROOT, "assets", "images", "logo")
LOGO_PATH = os.path.join(LOGO_DIR, "scoop.png")
DEFAULT_FIGURE = "pointer"

# Pistachio: Shipyard's khaki shifted to hue 140 in OKLCH (lightness +0.02,
# chroma x0.95). The figure is Shipyard's cream, the ball a light tint.
TILE_TOP = (0x6D, 0xA3, 0x61)     # #6da361
TILE_BOTTOM = (0x55, 0x7F, 0x4B)  # #557f4b
CREAM = (0xFB, 0xF6, 0xEA)        # #FBF6EA
TINT = (0xCE, 0xEB, 0xC8)         # #ceebc8
WHITE = (255, 255, 255)

SQUIRCLE_N = 5               # superellipse exponent of the tile
SHEEN_ALPHA = 0.14           # white at the tile's top, fading out at its middle
FIGURE_SPAN = 0.76           # figure box as a share of the tile
SMALL_GROWTH = 1.1           # extra figure scale below DETAIL_MIN
MARGIN = {48: 0.06, 128: 0.125, LOGO_SIZE: 0.125}  # transparent margin per side; 0 elsewhere


def _supersample(size):
    # Small icons have few pixels, so they can afford finer edges. The logo's
    # pixels are already fine, and 4x would make it slow to render.
    return 8 if size < 48 else 4 if size < LOGO_SIZE else 2


# ---------- shapes: signed distances in the 100 x 100 figure box ----------

def _seg_dist(px, py, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _circle(c, r):
    return lambda x, y: math.hypot(x - c[0], y - c[1]) - r


def _stroke(points, width):
    """A polyline stroked with round caps and joins."""
    segs = list(zip(points, points[1:]))
    return lambda x, y: min(_seg_dist(x, y, a, b) for a, b in segs) - width / 2


def _rect(x0, y0, x1, y1):
    cx, cy, hx, hy = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2

    def sdf(x, y):
        dx, dy = abs(x - cx) - hx, abs(y - cy) - hy
        return math.hypot(max(dx, 0), max(dy, 0)) + min(max(dx, dy), 0)
    return sdf


def _polygon(points):
    """A filled polygon: distance to its edges, negative inside (even-odd)."""
    edges = list(zip(points, points[1:] + points[:1]))

    def sdf(x, y):
        d = min(_seg_dist(x, y, a, b) for a, b in edges)
        inside = False
        for (ax, ay), (bx, by) in edges:
            if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
                inside = not inside
        return -d if inside else d
    return sdf


def _union(*sdfs):
    return lambda x, y: min(f(x, y) for f in sdfs)


def _moved(sdf, dx, dy):
    return lambda x, y: sdf(x - dx, y - dy)


def _quad(p0, p1, p2, steps=16):
    """Points along a quadratic Bezier curve, for stroking as a polyline."""
    return [tuple((1 - t) ** 2 * a + 2 * (1 - t) * t * b + t * t * c for a, b, c in zip(p0, p1, p2))
            for t in (i / steps for i in range(steps + 1))]


def _separated(sdf, paint, gap):
    """Layers drawing `sdf` over earlier parts, ringed by a `gap` of tile colour.

    The figure has no outline, so this gap is what keeps an overlapping part
    readable against the part beneath it.
    """
    return [(lambda x, y: sdf(x, y) - gap, ("tile", 1.0)), (sdf, paint)]


# ---------- figures ----------
# A figure is a list of (sdf, paint) layers, back to front. A paint is an RGB
# colour, or ("tile", alpha) for the tile's own colour at that opacity.

def _scalloped_ball(cx, cy, r, base, scallops, scallop_r, drop=0):
    """A ball whose lower half drops straight to `base`, edged with scallops.

    The scallops are circles centred at the `scallops` x positions, `drop`
    below `base`.
    """
    return _union(
        _circle((cx, cy), r),
        _rect(cx - r, cy, cx + r, base),
        *(_circle((x, base + drop), scallop_r) for x in scallops),
    )


ARROW = [(60, 48), (60, 86), (69, 77), (76, 92), (83, 89), (76, 74), (88, 74)]


def draw_pointer(detailed):
    # The prototype's "Ball + pointer", shifted by (-4, -3): the ball with a
    # scalloped base and a cream mouse pointer over its lower right, set off
    # from the ball by a gap. Below DETAIL_MIN the ball moves up and left with
    # three bigger scallops, the pointer grows 25% about a tip moved up-left, and
    # the gap widens, tuned against the 16 px output so the pointer reads as an
    # arrow instead of a smudge on the ball.
    ox, oy = -4, -3
    if detailed:
        ball = _scalloped_ball(46, 40, 26, 56, (26, 39, 52, 65), 6.5)
        arrow, gap = ARROW, 2
    else:
        ball = _scalloped_ball(42, 38, 26, 54, (24, 42, 60), 8.5)
        arrow = [(56 + (x - 60) * 1.25, 40 + (y - 48) * 1.25) for x, y in ARROW]
        gap = 5
    layers = [(_moved(ball, ox, oy), TINT)]
    if detailed:
        layers.append((_circle((36 + ox, 28 + oy), 4.5), ("tile", 0.35)))
    layers += _separated(_moved(_polygon(arrow), ox, oy), CREAM, gap)
    return layers


def _rounded_rect(x0, y0, x1, y1, r):
    """A rectangle with corners rounded to radius `r`."""
    inner = _rect(x0 + r, y0 + r, x1 - r, y1 - r)
    return lambda x, y: inner(x, y) - r


def _natural_scoop(cx, cy, r, lumps):
    """A round scoop with a soft, lumpy lower edge instead of straight sides.

    `lumps` are (dx, dy, radius) circles relative to the centre, unioned on.
    """
    return _union(_circle((cx, cy), r), *(_circle((cx + dx, cy + dy), lr) for dx, dy, lr in lumps))


def draw_clipboard(detailed):
    # A cream clipboard whose clip holds a round pistachio scoop on the board,
    # since Scoop copies what you point at to the clipboard. The clip sits over
    # the board's top edge and the scoop in its middle, each set off by a gap
    # of tile colour. The scoop is a round ball with a soft, lumpy underside
    # rather than a straight-sided dome. Below DETAIL_MIN the scoop is a plain
    # circle, the clip is shorter and the gap doubles, tuned against the 16 px
    # output so the gap under the clip lands on a whole pixel row.
    board = _rounded_rect(17, 17, 83, 97, 9)
    clip = _rounded_rect(33, 7, 67, 25 if detailed else 20, 5)
    if detailed:
        scoop = _natural_scoop(50, 59, 21, ((-14, 12, 6.5), (-5, 16, 6.5), (5, 16, 6.5), (14, 12, 6.5)))
    else:
        scoop = _circle((50, 62), 19)
    layers = [(board, CREAM)]
    gap = 3 if detailed else 6
    layers += _separated(clip, CREAM, gap)
    layers += _separated(scoop, TINT, gap)
    return layers


def draw_window_cup(detailed):
    # A browser window used as a cup: the window tapers like an ice-cream cup,
    # its header bar is the rim, and a round pistachio scoop sits in its open
    # top, the scoop's lower part hidden behind the window and set off from it
    # by a gap. A line of tile colour parts the header bar, with three window
    # controls, from the page, with two lines of text. The scoop shows more than
    # its upper half, so it stays round rather than a straight-sided dome.
    # Edges fall on pixel rows at 32 px. Below DETAIL_MIN the scoop grows, and
    # the figure moves down one pixel with its rim, line and base on whole
    # pixel rows, tuned against the 16 px output so the header line stays a
    # crisp row instead of a blur.
    if detailed:
        ball = _circle((50, 32), 27)
        cup = _polygon([(14, 54.1), (86, 54.1), (78, 91.1), (22, 91.1)])
        header = _rect(6, 62.3, 94, 66.4)
        gap = 2.5
    else:
        ball = _circle((50, 33.5), 29)
        cup = _polygon([(10, 57.5), (90, 57.5), (80, 94.85), (20, 94.85)])
        header = _rect(6, 64.95, 94, 72.4)
        gap = 6
    layers = [(ball, TINT)]
    if detailed:
        layers.append((_circle((39, 20), 5), ("tile", 0.35)))
    layers += _separated(cup, CREAM, gap)
    layers.append((header, ("tile", 1.0)))
    if detailed:
        layers += [(_circle((x, 58.2), 2), ("tile", 1.0)) for x in (22, 29, 36)]
        layers += [(_stroke([(28, 75), (66, 75)], 3), ("tile", 0.35)),
                   (_stroke([(32, 83), (56, 83)], 3), ("tile", 0.35))]
    return layers


def _arc(c, r, a0, a1, steps=24):
    """Points along a circular arc from angle `a0` to `a1` in degrees, y down."""
    return [(c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a)))
            for a in (a0 + (a1 - a0) * i / steps for i in range(steps + 1))]


def draw_monogram(detailed):
    # A cream letter S whose lower curl is the bowl of a scoop, cradling a
    # round pistachio ball set off from the letter by a gap. The upper bowl's
    # terminal turns down so its counter stays open, and the lower curl runs
    # on past the left to make a lip under the ball. Below DETAIL_MIN the
    # stroke thickens and the gap widens, tuned against the 16 px output so
    # the upper counter and the ball stay apart from the letter.
    s, gap = (12, 3) if detailed else (13, 4)
    top = _arc((41, 25), 15, -15, -270)
    low = _arc((52, 64), 24, -90, 158)
    layers = [(_stroke(top + low, s), CREAM)]
    layers += _separated(_circle((45, 62), 15.5), TINT, gap)
    if detailed:
        layers.append((_circle((39, 56), 3.5), ("tile", 0.35)))
    return layers


FIGURES = {
    "pointer": draw_pointer,
    "clipboard": draw_clipboard,
    "window-cup": draw_window_cup,
    "monogram": draw_monogram,
}


# ---------- rendering ----------

def _mix(base, over, alpha):
    return tuple(b + (o - b) * alpha for b, o in zip(base, over))


def render(figure, size):
    """RGBA bytes of `figure` on the tile at `size` x `size` px."""
    detailed = size >= DETAIL_MIN
    layers = FIGURES[figure](detailed)
    margin = MARGIN.get(size, 0.0)
    half = 0.5 - margin                       # tile half-width, canvas units
    scale = FIGURE_SPAN * (1 if detailed else SMALL_GROWTH) * 2 * half
    ss = _supersample(size)
    hi = size * ss

    def sample(u, v):
        """Straight RGB and coverage (0 or 1) at canvas coords (u, v)."""
        dx, dy = abs(u - 0.5) / half, abs(v - 0.5) / half
        if dx >= 1 or dy >= 1 or dx ** SQUIRCLE_N + dy ** SQUIRCLE_N > 1:
            return None
        t = (v - (0.5 - half)) / (2 * half)   # 0 at the tile's top, 1 at its bottom
        tile = _mix(TILE_TOP, TILE_BOTTOM, t)
        color = _mix(tile, WHITE, SHEEN_ALPHA * (1 - 2 * t)) if t < 0.5 else tile
        fx = 50 + (u - 0.5) * 100 / scale
        fy = 50 + (v - 0.5) * 100 / scale
        for sdf, paint in layers:
            if sdf(fx, fy) <= 0:
                color = _mix(color, tile, paint[1]) if isinstance(paint[0], str) else paint
        return color

    px = bytearray()
    for y in range(size):
        for x in range(size):
            r = g = b = n = 0
            for sy in range(ss):
                v = (y * ss + sy + 0.5) / hi
                for sx in range(ss):
                    c = sample((x * ss + sx + 0.5) / hi, v)
                    if c is not None:
                        r += c[0]
                        g += c[1]
                        b += c[2]
                        n += 1
            if n == 0:
                px += bytes(4)
            else:
                # Every covered sample is opaque, so averaging them is the
                # un-premultiplied colour.
                px += bytes((round(r / n), round(g / n), round(b / n), round(255 * n / (ss * ss))))
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


def preview_path(figure):
    return os.path.join(LOGO_DIR, f"scoop-{figure}.png")


def main():
    parser = argparse.ArgumentParser(description="Generate the Scoop icons, README logo and previews.")
    parser.add_argument("--variant", choices=FIGURES, default=DEFAULT_FIGURE,
                        help=f"figure shipped as the icons and README logo (default: {DEFAULT_FIGURE})")
    shipped = parser.parse_args().variant

    os.makedirs(OUT_DIR, exist_ok=True)
    for s in SIZES:
        p = os.path.join(OUT_DIR, f"icon{s}.png")
        write_png(p, s, render(shipped, s))
        print("wrote", os.path.relpath(p))
    os.makedirs(LOGO_DIR, exist_ok=True)
    write_png(LOGO_PATH, LOGO_SIZE, render(shipped, LOGO_SIZE))
    print("wrote", os.path.relpath(LOGO_PATH))

    # The shipped figure is the logo, so its preview from an earlier run with
    # another variant would be stale.
    if os.path.exists(preview_path(shipped)):
        os.remove(preview_path(shipped))
        print("removed", os.path.relpath(preview_path(shipped)))
    for figure in FIGURES:
        if figure != shipped:
            write_png(preview_path(figure), LOGO_SIZE, render(figure, LOGO_SIZE))
            print("wrote", os.path.relpath(preview_path(figure)))


if __name__ == "__main__":
    main()
