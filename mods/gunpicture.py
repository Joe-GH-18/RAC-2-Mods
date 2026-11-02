"""The Portal Gun's picture on the Weapons page: the gun's own mesh (gunmesh.py) drawn here from code, on
a blueprint in the style of the game's weapon pictures, so that the patch holds nothing of the games.
256 x 256 DXT1, where the game's are 512 x 512 DXT5 with mips, which would not fit in the mod's segment:
portal.py doubles it when the page asks for the picture.
"""
import functools
import math
import os
import sys

from . import gunmesh

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from dxt import encode1  # noqa: E402

SIZE, SAMPLE = 256, 3
BLUEPRINT = (56, 96, 170)
LINE, RING = (84, 124, 196), (120, 158, 222)
LIGHT = (-0.45, -0.35, 0.82)
OUTLINE = (10, 12, 18)
SCALE, CENTRE = 44.0, (1.0, -0.15)


def rotate(p):
    """Three quarters from the side, the claws to the left and the nose a little down, as the game's."""
    x, y, z = p
    a, b = math.radians(-68), math.radians(16)
    x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
    y, z = y * math.cos(b) - z * math.sin(b), y * math.sin(b) + z * math.cos(b)
    return x, y, z


def background(x, y):
    u, v = x / SIZE, y / SIZE
    colour = BLUEPRINT
    if int(x) % 26 < 1 or int(y) % 26 < 1:
        colour = LINE
    r = math.hypot(u - 0.42, v - 0.5)
    for radius, width in ((0.30, 0.014), (0.38, 0.006), (0.46, 0.02)):
        if abs(r - radius) < width and not 2.2 < math.atan2(v - 0.5, u - 0.42) + 3.2 < 3.0:
            colour = RING
    if u < 0.03 or u > 0.97 or v < 0.03 or v > 0.97:
        colour = RING
    return colour


def shade(triangle, m, normal):
    colour = gunmesh.COLOURS[list(gunmesh.COLOURS)[int(m.vertices[triangle[0]][2][0] * gunmesh.CELLS) + 4 * int(m.vertices[triangle[0]][2][1] * gunmesh.CELLS)]]
    n = rotate(normal)
    level = 0.45 + 0.65 * max(0.0, sum(a * b for a, b in zip(n, LIGHT)))
    return tuple(min(255, int(c * level)) for c in colour)


@functools.lru_cache(maxsize=None)
def rows():
    side = SIZE * SAMPLE
    m = gunmesh.build()
    depth, colour, face = {}, {}, {}
    points = []
    for position, _, _ in m.vertices:
        x, y, z = rotate(position)
        points.append(((x + CENTRE[0]) * SCALE * SAMPLE + side / 2, (-z + CENTRE[1]) * SCALE * SAMPLE + side / 2, y))
    for number, triangle in enumerate(m.triangles):
        a, b, c = (points[i] for i in triangle)
        area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if area == 0:
            continue
        tint = shade(triangle, m, m.vertices[triangle[0]][1])
        for py in range(max(0, int(min(a[1], b[1], c[1]))), min(side - 1, int(max(a[1], b[1], c[1])) + 1) + 1):
            for px in range(max(0, int(min(a[0], b[0], c[0]))), min(side - 1, int(max(a[0], b[0], c[0])) + 1) + 1):
                w0 = ((b[0] - px) * (c[1] - py) - (b[1] - py) * (c[0] - px)) / area
                w1 = ((c[0] - px) * (a[1] - py) - (c[1] - py) * (a[0] - px)) / area
                w2 = 1 - w0 - w1
                if w0 < 0 or w1 < 0 or w2 < 0:
                    continue
                d = w0 * a[2] + w1 * b[2] + w2 * c[2]
                if d < depth.get((px, py), 1e9):
                    depth[px, py], colour[px, py] = d, tint
                    face[px, py] = tint
    out = []
    ring = 2 * SAMPLE // 3 + 1
    for y in range(SIZE):
        row = []
        for x in range(SIZE):
            total = [0, 0, 0]
            for sy in range(SAMPLE):
                for sx in range(SAMPLE):
                    key = (x * SAMPLE + sx, y * SAMPLE + sy)
                    if key in colour:
                        shown = colour[key]
                        for dx, dy in ((ring, 0), (0, ring)):
                            other = (key[0] + dx, key[1] + dy)
                            if other in depth and abs(depth[other] - depth[key]) > 0.25:
                                shown = OUTLINE
                    elif any((key[0] + dx, key[1] + dy) in colour for dx, dy in ((ring, 0), (-ring, 0), (0, ring), (0, -ring))):
                        shown = OUTLINE
                    else:
                        shown = background(key[0] / SAMPLE, key[1] / SAMPLE)
                    for k in range(3):
                        total[k] += shown[k]
            row.append(tuple(v // SAMPLE ** 2 for v in total))
        out.append(row)
    return out


@functools.lru_cache(maxsize=None)
def texture():
    return encode1(rows())
