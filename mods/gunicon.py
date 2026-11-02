"""The Portal Gun's icon on the Weapons page and in the Quick Select, drawn here from code so that the
patch holds nothing of the games.

The game's item icons are 64 x 64 DXT5 with one grey and an alpha shape; the HUD tints them, cyan in a
tile and red when something is wrong. So this is a shape: the gun from the side, the claws to the left,
with the core, the window and the band cut out. Holes show the tile's colour, as the Clank Zapper's eyes do.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from dxt import encode  # noqa: E402

SIZE, SCALE = 64, 4
GREY, HIGHLIGHT = (101, 101, 101), (126, 126, 126)

SOLID = [
    ("ellipse", 43, 25, 19, 15),                                                            # the body
    ("polygon", (20, 18), (30, 15), (30, 35), (20, 32)),                                    # the neck
    ("polygon", (23, 17), (14, 8), (4, 6), (1, 10), (9, 13), (17, 21)),                     # the top claw
    ("polygon", (23, 33), (14, 42), (4, 44), (1, 40), (9, 37), (17, 29)),                   # the bottom claw
    ("polygon", (39, 37), (51, 37), (56, 59), (43, 60)),                                    # the grip
    ("circle", 12, 25, 6),                                                                  # the core
]
CUT = [
    ("polygon", (34, 8), (37, 8), (37, 42), (34, 42)),                                      # the band
    ("polygon", (42, 15), (55, 15), (55, 20), (42, 20)),                                    # the window
    ("circle", 12, 25, 2),                                                                  # the core's eye
    ("polygon", (17, 22), (19, 22), (19, 28), (17, 28)),                                    # between core and neck
]


def inside(shape, x, y):
    kind = shape[0]
    if kind == "ellipse":
        _, cx, cy, rx, ry = shape
        return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1
    if kind == "circle":
        _, cx, cy, r = shape
        return (x - cx) ** 2 + (y - cy) ** 2 <= r * r
    corners, odd = shape[1:], False
    for (x0, y0), (x1, y1) in zip(corners, corners[1:] + corners[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            odd = not odd
    return odd


def coverage(x, y):
    """How much of the pixel the shape covers, 0 to 255."""
    hits = 0
    for sy in range(SCALE):
        for sx in range(SCALE):
            px, py = x + (sx + 0.5) / SCALE, y + (sy + 0.5) / SCALE
            if any(inside(s, px, py) for s in SOLID) and not any(inside(s, px, py) for s in CUT):
                hits += 1
    return hits * 255 // SCALE ** 2


def rows():
    out = []
    for y in range(SIZE):
        row = []
        for x in range(SIZE):
            colour = HIGHLIGHT if 11 <= y < 16 and x > 40 else GREY              # light on the body's top
            row.append(colour + (coverage(x, y),))
        out.append(row)
    return out


def texture():
    return encode(rows())
