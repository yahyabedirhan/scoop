#!/usr/bin/env python3
"""Generate the Scoop extension icons (16/32/48/128) as RGBA PNGs.

Motif: an ice-cream scoop lifting one round, smiling scoop of strawberry ice
cream. Each shape is a signed distance function painted back to front with a
dark outline, so it reads on light and dark toolbars. The face, sprinkles
and shine only appear from DETAIL_MIN px up; at 16 px the icon is
the bare silhouette. Pure standard library, 4x supersampled for clean edges.
Re-run after tweaking geometry or colors.
"""
import math
import os
import struct
import zlib

SS = 4                       # supersampling factor
SIZES = (16, 32, 48, 128)
DETAIL_MIN = 48              # smallest size that gets the face and decorations
OUT_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "icons")

OUTLINE = (46, 16, 101)      # #2e1065 deep violet
SCOOP = (124, 58, 237)       # #7c3aed violet, the old accent kept for the tool
SCOOP_SHADE = (91, 33, 182)  # #5b21b6 the handle, a step darker than the bowl
ICE_CREAM = (244, 114, 182)  # #f472b6 strawberry pink
SHINE = (255, 255, 255)
SPRINKLES = [(250, 204, 21), (34, 211, 238), (255, 255, 255)]

# All geometry in a 0..1 unit square, y pointing down.

OUTLINE_W = 0.035

BALL_C, BALL_R = (0.42, 0.36), 0.22
BOWL_C, BOWL_R = (0.42, 0.52), 0.30   # only the half below BOWL_C[1] is drawn
HANDLE = ((0.62, 0.70), (0.90, 0.92))
HANDLE_W = 0.15

# Decorations, drawn only at DETAIL_MIN px and up.
EYES = [(0.35, 0.33), (0.49, 0.33)]
EYE_R = 0.028
SMILE_C, SMILE_R, SMILE_W = (0.42, 0.38), 0.065, 0.028
SHINE_C, SHINE_R = (0.33, 0.23), 0.035
SPRINKLE_SEGS = [
    ((0.43, 0.18), (0.47, 0.20)),
    ((0.53, 0.24), (0.55, 0.28)),
    ((0.26, 0.31), (0.27, 0.35)),
]
SPRINKLE_W = 0.03


def _seg_dist(px, py, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _circle(px, py, c, r):
    return math.hypot(px - c[0], py - c[1]) - r


def _capsule(px, py, a, b, w):
    return _seg_dist(px, py, a, b) - w / 2


def _bowl(px, py):
    # Lower half-disc: inside the circle and below its centre line.
    return max(_circle(px, py, BOWL_C, BOWL_R), BOWL_C[1] - py)


def _smile(px, py):
    # The lower arc of a circle, between 25 and 155 degrees.
    ang = math.degrees(math.atan2(py - SMILE_C[1], px - SMILE_C[0]))
    if 25 <= ang <= 155:
        return abs(math.hypot(px - SMILE_C[0], py - SMILE_C[1]) - SMILE_R) - SMILE_W / 2
    ends = [(SMILE_C[0] + SMILE_R * math.cos(math.radians(a)),
             SMILE_C[1] + SMILE_R * math.sin(math.radians(a))) for a in (25, 155)]
    return min(math.hypot(px - ex, py - ey) for ex, ey in ends) - SMILE_W / 2


def _layers(detailed):
    """(sdf, fill, outlined) from back to front."""
    layers = [
        (lambda u, v: _capsule(u, v, *HANDLE, HANDLE_W), SCOOP_SHADE, True),
        (lambda u, v: _circle(u, v, BALL_C, BALL_R), ICE_CREAM, True),
        (_bowl, SCOOP, True),
    ]
    if detailed:
        layers += [
            (lambda u, v: _circle(u, v, SHINE_C, SHINE_R), SHINE, False),
        ]
        layers += [(lambda u, v, s=s: _capsule(u, v, *s, SPRINKLE_W), SPRINKLES[i % len(SPRINKLES)], False)
                   for i, s in enumerate(SPRINKLE_SEGS)]
        layers += [(lambda u, v, e=e: _circle(u, v, e, EYE_R), OUTLINE, False) for e in EYES]
        layers.append((_smile, OUTLINE, False))
    return layers


def _sample(u, v, layers):
    """RGBA at unit coords (u, v): the front-most layer, or its outline, wins."""
    color = None
    for sdf, fill, outlined in layers:
        d = sdf(u, v)
        if d <= 0:
            color = fill
        elif outlined and d <= OUTLINE_W:
            color = OUTLINE
    return (0, 0, 0, 0) if color is None else (*color, 255)


def make_pixels(size):
    layers = _layers(size >= DETAIL_MIN)
    hi = size * SS
    px = bytearray()
    for y in range(size):
        for x in range(size):
            # Average premultiplied samples, then un-premultiply.
            r = g = b = a = 0
            for dy in range(SS):
                v = (y * SS + dy + 0.5) / hi
                for dx in range(SS):
                    u = (x * SS + dx + 0.5) / hi
                    sr, sg, sb, sa = _sample(u, v, layers)
                    r += sr * sa
                    g += sg * sa
                    b += sb * sa
                    a += sa
            if a == 0:
                px += bytes(4)
            else:
                px += bytes((round(r / a), round(g / a), round(b / a), round(a / (SS * SS))))
    return bytes(px)


def write_png(path, size):
    raw = make_pixels(size)
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
        write_png(p, s)
        print("wrote", os.path.relpath(p))


if __name__ == "__main__":
    main()
