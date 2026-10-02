#!/usr/bin/env python3
"""Generate the Scoop extension icons (16/32/48/128) and README logo as RGBA PNGs.

Motif: a scoop of pistachio ice cream between two angle brackets, `<●>`, as a
flat figure on a pistachio squircle tile with a soft vertical gradient and a
white sheen, in the format of Shipyard's logo. The figure has no outline.
Below DETAIL_MIN px it drops its details and grows 10%, so the small icon is
the bare silhouette. The 48 and 128 px tiles keep Chrome's transparent margin;
the smaller tiles fill the canvas. The 512 px README logo keeps the 128 px
margin, so it matches the toolbar icon and Shipyard's logo on GitHub.

Each figure is a draw function in FIGURES, keyed by name, returning its
layers. Every size is rendered by the same `render`, so a new figure or a new
output size needs no change to the renderer. Pure standard library,
supersampled for clean edges, and deterministic. Re-run after tweaking
geometry or colours.
"""
import math
import os
import struct
import zlib

SIZES = (16, 32, 48, 128)
DETAIL_MIN = 32              # smallest size that gets the figure's details
ROOT = os.path.join(os.path.dirname(__file__), os.pardir)
OUT_DIR = os.path.join(ROOT, "icons")
LOGO_SIZE = 512
LOGO_PATH = os.path.join(ROOT, "assets", "images", "logo", "scoop.png")
SHIPPED_FIGURE = "brackets"

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


# ---------- figures ----------
# A figure is a list of (sdf, paint) layers, back to front. A paint is an RGB
# colour, or ("tile", alpha) for the tile's own colour at that opacity.

def draw_brackets(detailed):
    # Below DETAIL_MIN the brackets spread out, the strokes thicken and the
    # ball shrinks, tuned against the 16 px output so `<●>` keeps a tile-coloured
    # gap between ball and brackets instead of merging into one blob.
    tip, arm, width, r = (10, 27, 10, 19) if detailed else (8, 26, 12, 17)
    layers = [
        (_stroke([(arm, 30), (tip, 50), (arm, 70)], width), CREAM),
        (_stroke([(100 - arm, 30), (100 - tip, 50), (100 - arm, 70)], width), CREAM),
        (_circle((50, 46), r), TINT),
        (_stroke([(56, 60), (56, 72)], 8), TINT),
    ]
    if detailed:
        layers.append((_circle((43, 39), 3.5), ("tile", 0.35)))
    return layers


FIGURES = {
    "brackets": draw_brackets,
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


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for s in SIZES:
        p = os.path.join(OUT_DIR, f"icon{s}.png")
        write_png(p, s, render(SHIPPED_FIGURE, s))
        print("wrote", os.path.relpath(p))
    os.makedirs(os.path.dirname(LOGO_PATH), exist_ok=True)
    write_png(LOGO_PATH, LOGO_SIZE, render(SHIPPED_FIGURE, LOGO_SIZE))
    print("wrote", os.path.relpath(LOGO_PATH))


if __name__ == "__main__":
    main()
