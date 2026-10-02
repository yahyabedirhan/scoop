#!/usr/bin/env python3
"""Generate the Scoop extension icons (16/32/48/128) and README logo as RGBA PNGs.

Shipped motif, `pointer`: a scoop of pistachio ice cream with a scalloped
base and a cream mouse pointer over its lower right, as a flat figure on a
pistachio squircle tile with a soft vertical gradient and a white sheen, in
the format of Shipyard's logo. The figure has no outline.
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


def _offset(sdf, d):
    """`sdf` grown outward by `d`, or shrunk where `d` is negative."""
    return lambda x, y: sdf(x, y) - d


def _rounded_rect(x0, y0, x1, y1, r):
    """A rectangle with corners rounded to radius `r`."""
    return _offset(_rect(x0 + r, y0 + r, x1 - r, y1 - r), r)


def _scalloped_ball(cx, cy, r, base, scallops, scallop_r):
    """A ball whose lower half drops straight to `base`, edged with scallops.

    The scallops are circles centred on `base` at the `scallops` x positions.
    """
    return _union(
        _circle((cx, cy), r),
        _rect(cx - r, cy, cx + r, base),
        *(_circle((x, base), scallop_r) for x in scallops),
    )


def _natural_scoop(cx, cy, r, lumps):
    """A round scoop with a soft, lumpy lower edge instead of straight sides.

    `lumps` are (dx, dy, radius) circles relative to the centre, unioned on.
    """
    return _union(_circle((cx, cy), r), *(_circle((cx + dx, cy + dy), lr) for dx, dy, lr in lumps))


def _separated(sdf, paint, gap):
    """Layers drawing `sdf` over earlier parts, ringed by a `gap` of tile colour.

    The figure has no outline, so this gap is what keeps an overlapping part
    readable against the part beneath it.
    """
    return [(_offset(sdf, gap), ("tile", 1.0)), (sdf, paint)]


# ---------- figures ----------
# A figure is a list of (sdf, paint) layers, back to front. A paint is an RGB
# colour, or ("tile", alpha) for the tile's own colour at that opacity.

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


def _stroke(points, width):
    """A polyline stroked with round caps and joins."""
    segs = list(zip(points, points[1:]))
    return lambda x, y: min(_seg_dist(x, y, a, b) for a, b in segs) - width / 2


def _intersect(*sdfs):
    return lambda x, y: max(f(x, y) for f in sdfs)


def _below(y0):
    """The half-plane below the line y = `y0` (y down)."""
    return lambda x, y: y0 - y


def draw_scooper(detailed):
    # The ice-cream scoop tool on its own, a round pistachio ball heaped in
    # its bowl. The bowl is a solid half disc opening upward, so the ball sits
    # in it instead of being ringed like a magnifier's lens, and the handle
    # leaves the bowl's side below the rim at a shallow angle, aimed below the
    # ball's centre. A narrow neck widens into a thick, round-ended grip, and a
    # thumb lever rises from the neck. Below DETAIL_MIN the lever goes, the
    # bowl deepens, the handle thickens and the gap widens, tuned against the
    # 16 px output so the gap under the ball fills one whole pixel row.
    if detailed:
        cx, cup_r, rim, ball_y, gap = 64, 27, 56, 39, 2.5
    else:
        cx, cup_r, rim, ball_y, gap = 64, 30, 56, 36.5, 7.5
    cup = _intersect(_circle((cx, rim), cup_r), _below(rim))
    ball = _circle((cx, ball_y), 21)
    neck = _stroke([(cx - 22, rim + 6), (cx - 36, rim + 14)], 8 if detailed else 10)
    grip = _stroke([(cx - 36, rim + 14), (cx - 52, rim + 24)], 14 if detailed else 15)
    lever = _stroke([(cx - 28, rim + 6), (cx - 32, rim - 3)], 7)
    layers = [(_union(cup, neck, grip), CREAM)]
    if detailed:
        layers.append((lever, CREAM))
    layers += _separated(ball, TINT, gap)
    return layers


def _tub_bowl(c, r, opening):
    """A scoop's bowl seen from the side: the half of a disc away from `opening`.

    `opening` is the unit vector the bowl's mouth faces.
    """
    nx, ny = opening
    disc = _circle(c, r)
    return lambda x, y: max(disc(x, y), (x - c[0]) * nx + (y - c[1]) * ny)


def draw_scoop_tub(detailed):
    # A cream ice-cream scoop, seen from the side, pulling a round pistachio
    # ball up out of a tub heaped with more. The bowl's near wall hides the
    # lower part of the ball, so the ice cream sits visibly in the bowl rather
    # than behind a ring, which is what made the first scoop read as a
    # magnifier. The handle narrows at its neck, ends in a thicker grip and
    # carries a thumb lever, so the tool cannot pass for a ladle or a spoon.
    # Below DETAIL_MIN the ball rides higher in the bowl, the tub's ice cream
    # heaps higher, the grip thickens and the lever joins the handle as a bump
    # instead of a separate loop, tuned against the 16 px output so the handle
    # stays one piece.
    c, r = (46, 42), 27
    opening = (-0.3, -0.95)
    nx, ny = opening
    rim = (c[0] - ny * r, c[1] + nx * r)
    bowl = _tub_bowl(c, r, opening)
    if detailed:
        lift, br, lump, gap = 8, 21, 11, 2.5
        handle = _union(_stroke([(rim[0] - 6, rim[1] + 4), (86, 27)], 8), _stroke([(84, 27), (106, 17)], 15))
        lever = _stroke([(68, 30), (72, 18), (79, 15)], 5)
    else:
        lift, br, lump, gap = 11, 22, 14, 5
        handle = _union(_stroke([(rim[0] - 6, rim[1] + 4), (82, 28)], 10), _stroke([(82, 27), (98, 20)], 18),
                        _stroke([(66, 32), (69, 21)], 8))
        lever = None
    ball = _circle((c[0] + nx * lift, c[1] + ny * lift), br)
    tub = _polygon([(-4, 78), (52, 78), (46, 104), (2, 104)])
    contents = _union(*(_circle((x, 77), lump) for x in (6, 24, 42)))
    layers = [(contents, TINT)]
    layers += _separated(tub, CREAM, gap)
    layers += _separated(ball, TINT, gap)
    layers += _separated(_union(bowl, handle), CREAM, gap)
    if lever:
        layers += _separated(lever, CREAM, gap)
    return layers


def _cup(c, r, d, depth):
    """The bowl of a scoop: a disc cut by a chord, open toward unit vector `d`.

    The chord sits `depth` past the centre along `d`, so a positive `depth`
    makes the bowl deeper than a half disc.
    """
    disc = _circle(c, r)
    return lambda x, y: max(disc(x, y), (x - c[0]) * d[0] + (y - c[1]) * d[1] - depth)


def draw_scoop_cone(detailed):
    # An ice-cream scoop tipping a round pistachio ball onto a cream cone. The
    # bowl's mouth faces down and left, toward the cone, with the ball half out
    # of it. The handle rises up and right, thin at the neck and thick at the
    # grip, with a thumb lever arching over the neck, so the tool reads as a
    # scoop rather than a magnifier or a ladle. The bowl sits in front of the
    # ball, so the ball shows heaped in its mouth instead of the bowl showing
    # as a ring. Below DETAIL_MIN the lever goes, the ball and bowl grow, and
    # the gap widens to about one pixel, tuned against the 16 px output so the
    # bowl, ball and cone stay three separate shapes.
    a, m = math.radians(-25), math.radians(120)
    u = (math.cos(a), math.sin(a))          # along the handle, right and up
    d = (math.cos(m), math.sin(m))          # the bowl's mouth, down and left
    n = (-u[1], u[0])                        # across the handle
    if detailed:
        bowl_c, bowl_r, ball_r, sink, cone_top, gap = (37, 28), 24, 21, 13, 60, 3
    else:
        bowl_c, bowl_r, ball_r, sink, cone_top, gap = (37, 26), 26, 24, 11, 62, 7
    ball_c = (bowl_c[0] + d[0] * sink, bowl_c[1] + d[1] * sink)

    def at(t, s=0):
        return (bowl_c[0] + u[0] * t + n[0] * s, bowl_c[1] + u[1] * t + n[1] * s)

    cx = ball_c[0]
    cone = _polygon([(cx - 21, cone_top), (cx + 21, cone_top), (cx, 100)])
    bowl = _cup(bowl_c, bowl_r, d, 2)
    neck = _stroke([at(bowl_r - 8), at(bowl_r + 12)], 8)
    grip = _stroke([at(bowl_r + 12), at(bowl_r + 38)], 14)
    ball = _circle(ball_c, ball_r)
    layers = [(cone, CREAM)]
    layers += _separated(ball, TINT, gap)
    tool = [bowl, neck, grip]
    if detailed:
        tool.append(_stroke([at(bowl_r - 8, -17), at(bowl_r + 6, -13), at(bowl_r + 22, -7)], 4.5))
    layers += _separated(_union(*tool), CREAM, gap)
    return layers


def _rotated(sdf, c, deg):
    """`sdf` turned by `deg` degrees about `c`, clockwise on screen (y down)."""
    co, si = math.cos(math.radians(deg)), math.sin(math.radians(deg))

    def sdf_turned(x, y):
        dx, dy = x - c[0], y - c[1]
        return sdf(c[0] + dx * co + dy * si, c[1] - dx * si + dy * co)
    return sdf_turned


def _ellipse(c, rx, ry):
    """An ellipse. Its distance is approximated by scaling, close enough for fills and gaps."""
    return lambda x, y: (math.hypot((x - c[0]) / rx, (y - c[1]) / ry) - 1) * min(rx, ry)


def draw_cursor_scoop(detailed):
    # An ice-cream scoop tool holding a round pistachio ball, with a cream mouse
    # pointer below its bowl, so the icon says "point at it and scoop it". The
    # bowl is a deep half-ellipse whose front lip is drawn over the ball, set
    # off by a gap, so the ball sits heaped in the bowl instead of inside a ring
    # that would read as a magnifier. The handle leaves the bowl's back down
    # to the left and thickens into a grip. Detailed sizes add the thumb lever
    # as a tab off the bowl's back. Below DETAIL_MIN the lever goes, the ball
    # rises further out of a deeper bowl, the scoop moves up and left, and the
    # pointer grows 20% with a wider gap, tuned against the 16 px output so the
    # ball stays round and the pointer reads as an arrow.
    if detailed:
        c, rx, ry, kr, kh = (50, 42), 27, 22, 21, 12
        handle = _union(_stroke([(34, 54), (8, 90)], 10), _stroke([(19, 76), (8, 90)], 16),
                        _stroke([(30, 56), (24, 49), (19, 48)], 8))
        arrow = [(70 + (x - 60) * 0.9, 58 + (y - 48) * 0.9) for x, y in ARROW]
        gap = 2.5
    else:
        c, rx, ry, kr, kh = (40, 40), 27, 27, 20, 15
        handle = _union(_stroke([(24, 49), (5, 84)], 11), _stroke([(11, 72), (5, 84)], 17))
        arrow = [(65 + (x - 60) * 1.2, 50 + (y - 48) * 1.2) for x, y in ARROW]
        gap = 5
    tilt = -12                                # the bowl's opening leans up and right
    bowl = _rotated(lambda x, y: max(_ellipse(c, rx, ry)(x, y), c[1] - y), c, tilt)
    ball = _rotated(_circle((c[0], c[1] - kh), kr), c, tilt)
    layers = [(ball, TINT)]
    layers += _separated(_union(bowl, handle), CREAM, gap)
    layers += _separated(_polygon(arrow), CREAM, gap)
    return layers


def draw_clipboard_scoop(detailed):
    # The cream clipboard of `clipboard` with an ice-cream scoop tool laid on
    # the board, cut out in tile colour, holding a round pistachio ball, so the
    # icon says "scoop it to the clipboard". A round bowl on a straight handle
    # reads as a magnifier, so the bowl is a wide, flat-topped half ellipse,
    # broader than the ball heaped three quarters out of it, and the handle
    # has a thin neck and a thick grip. The ball is ringed by a gap of tile
    # colour, since the pistachio tint barely shows on cream. The detailed
    # figure adds the thumb lever rising from the neck. Below DETAIL_MIN the
    # clip is shorter, the gaps widen, the bowl is deeper and the handle is
    # shorter and steeper, tuned against the 16 px output, where a level
    # handle read as a stripe cutting the board in two and a shallow bowl lost
    # its round bottom. At every size the grip stops short of the board's edge
    # for the same reason.
    def capsule(a, b, r):
        return lambda x, y: _seg_dist(x, y, a, b) - r

    def bowl(cx, rim, rx, ry):
        # Lower half of an ellipse centred on the rim. An approximate distance,
        # exact enough at this size.
        return lambda x, y: max((math.hypot((x - cx) / rx, (y - rim) / ry) - 1) * min(rx, ry), rim - y)

    board = _rounded_rect(12, 17, 88, 97, 9)
    clip = _rounded_rect(34, 7, 66, 25 if detailed else 22, 5)
    if detailed:
        gap, ring = 3, 3
        ball = _circle((37, 54), 14)
        tool = _union(
            bowl(37, 61, 22, 21),
            capsule((57, 70), (65, 68), 4),     # neck
            capsule((67, 67), (77, 61), 7),     # grip
            capsule((58, 66), (62, 58), 2.5),   # thumb lever
        )
    else:
        gap, ring = 6, 5
        ball = _circle((36, 54), 13)
        tool = _union(
            bowl(36, 62, 21, 22),
            capsule((52, 74), (60, 70), 4),     # neck
            capsule((61, 69), (74, 60), 6.5),   # grip
        )
    layers = [(board, CREAM)]
    layers += _separated(clip, CREAM, gap)
    layers += [(_offset(ball, ring), ("tile", 1.0)), (ball, TINT), (tool, ("tile", 1.0))]
    return layers


FIGURES = {
    "pointer": draw_pointer,
    "clipboard": draw_clipboard,
    "scooper": draw_scooper,
    "scoop-tub": draw_scoop_tub,
    "scoop-cone": draw_scoop_cone,
    "cursor-scoop": draw_cursor_scoop,
    "clipboard-scoop": draw_clipboard_scoop,
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
