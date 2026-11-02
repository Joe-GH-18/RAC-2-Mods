"""The Portal Gun's model: low-poly prisms with flat normals and a flat-colour texture, in RC2's
model format, drawn here from code so that the patch holds nothing of the games.

Vertices are 0x28 bytes (+0 position, +0xc normal, +0x18 u, v, +0x20 four weights, +0x24 four bones)
and all bound to bone 0. The Lancer's numbers are the guide: its barrel points along -y, about 3.1
units ahead of the grip and 1 behind, about 1.5 wide, and the model's scale makes that 0.86 of the
world's units. The texture is 128 x 128 DXT5 with one flat colour per cell of a 4 x 4 grid.
"""
import math
import struct

SIZE, CELLS = 128, 4
COLOURS = dict(white=(238, 238, 232), light=(196, 199, 196), grey=(120, 124, 128), dark=(38, 38, 42),
               black=(16, 16, 18), blue=(60, 170, 255), glow=(190, 235, 255), orange=(255, 130, 20))
CELL = {name: i for i, name in enumerate(COLOURS)}


class Mesh:
    def __init__(self):
        self.vertices, self.triangles = [], []

    def face(self, corners, colour):
        """A flat polygon, corners counter-clockwise seen from outside."""
        a, b, c = corners[0], corners[1], corners[2]
        u = [b[i] - a[i] for i in range(3)]
        v = [c[i] - a[i] for i in range(3)]
        n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
        length = math.sqrt(sum(x * x for x in n)) or 1.0
        n = [x / length for x in n]
        cell = CELL[colour]
        uv = ((cell % CELLS + 0.5) / CELLS, (cell // CELLS + 0.5) / CELLS)
        first = len(self.vertices)
        self.vertices += [(tuple(p), tuple(n), uv) for p in corners]
        for i in range(1, len(corners) - 1):
            self.triangles.append((first, first + i, first + i + 1))

    def prism(self, ring_a, ring_b, colour, caps=(True, True), side=None):
        """Sides between two rings of the same size, the rings counter-clockwise seen from ring_b's
        side looking back at ring_a, and flat caps."""
        n = len(ring_a)
        for i in range(n):
            j = (i + 1) % n
            self.face([ring_a[i], ring_a[j], ring_b[j], ring_b[i]], side or colour)
        if caps[0]:
            self.face(list(reversed(ring_a)), colour)
        if caps[1]:
            self.face(list(ring_b), colour)

    def tube(self, y0, y1, r0, r1, colour, sides=8, x=0.0, z=0.0, squash=1.0, caps=(True, True), side=None, turn=0.0):
        """A tube along y, from y0 (the front) to y1, radii r0 and r1, squash = height / width."""
        def ring(y, r):
            return [(x + r * math.cos(turn + 2 * math.pi * i / sides), y, z + squash * r * math.sin(turn + 2 * math.pi * i / sides))
                    for i in range(sides)]
        a, b = ring(y0, r0), ring(y1, r1)
        if y1 > y0:
            a, b = list(reversed(a)), list(reversed(b))
        self.prism(a, b, colour, caps, side)

    def box(self, low, high, colour):
        x0, y0, z0 = low
        x1, y1, z1 = high
        ring_a = [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]
        ring_b = [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)]
        self.prism(list(reversed(ring_a)), list(reversed(ring_b)), colour)


def build():
    m = Mesh()
    # the shell: fat at the back, narrowing to the neck, as the real thing's white body
    m.tube(0.75, 0.15, 0.62, 0.86, "white", squash=0.92, caps=(False, True), turn=math.pi / 8)
    m.tube(0.15, -0.75, 0.86, 0.80, "white", squash=0.92, caps=(False, False), turn=math.pi / 8)
    m.tube(-0.75, -1.45, 0.80, 0.50, "light", squash=0.92, caps=(False, False), turn=math.pi / 8)
    m.tube(0.95, 0.75, 0.30, 0.62, "dark", squash=0.92, caps=(True, False), turn=math.pi / 8)
    # the black band and the blue window on its top
    m.tube(-0.30, -0.42, 0.885, 0.875, "black", squash=0.94, caps=(False, False), turn=math.pi / 8)
    m.box((-0.16, -0.20, 0.72), (0.16, 0.42, 0.86), "blue")
    m.box((-0.05, 0.42, 0.74), (0.05, 0.62, 0.80), "orange")
    # the neck and the glowing core inside the claws
    m.tube(-1.45, -1.72, 0.34, 0.28, "dark", caps=(False, False))
    m.tube(-1.72, -2.05, 0.27, 0.22, "blue", caps=(True, True), side="blue")
    m.tube(-2.05, -2.16, 0.14, 0.14, "glow", sides=6)
    # three claws, each three bent segments
    for angle in (math.pi / 2, math.pi * 7 / 6, math.pi * 11 / 6):
        c, s = math.cos(angle), math.sin(angle)

        def at(radius, y, half):
            px, pz = radius * c, radius * s
            ax, az = -s * half, c * half
            bx, bz = c * half * 0.8, s * half * 0.8
            return [(px - ax - bx, y, pz - az - bz), (px + ax - bx, y, pz + az - bz),
                    (px + ax + bx, y, pz + az + bz), (px - ax + bx, y, pz - az + bz)]
        stations = [(0.42, -1.42, 0.17), (0.74, -1.92, 0.15), (0.70, -2.50, 0.12), (0.42, -2.98, 0.05)]
        for (r0, y0, h0), (r1, y1, h1) in zip(stations, stations[1:]):
            m.prism(at(r0, y0, h0), at(r1, y1, h1), "black", caps=(False, False))
        m.face(at(*stations[-1]), "black")
    # the grip, the trigger guard and the tube along the left side
    m.box((-0.20, 0.00, -1.42), (0.20, 0.42, -0.66), "dark")
    m.box((-0.23, -0.04, -1.50), (0.23, 0.46, -1.40), "black")
    m.box((-0.07, -0.32, -0.92), (0.07, -0.02, -0.82), "black")
    m.tube(0.55, -1.30, 0.08, 0.08, "black", sides=6, x=-0.92, z=-0.10, caps=(True, True))
    return m


def buffers():
    m = build()
    vertices = bytearray()
    for position, normal, uv in m.vertices:
        vertices += struct.pack(">3f3f2f", *position, *normal, *uv) + b"\xff\0\0\0\0\0\0\0"
    indices = struct.pack(f">{3 * len(m.triangles)}H", *[v for t in m.triangles for v in t])
    return bytes(vertices), indices, len(m.vertices), 3 * len(m.triangles)


def rgb565(colour):
    r, g, b = colour
    return (r >> 3) << 11 | (g >> 2) << 5 | b >> 3


def texture():
    """128 x 128 DXT5: every 4 x 4 block one flat colour, fully opaque. RSX DXT data is little-endian
    in each 16-bit colour, like a DDS file."""
    names = list(COLOURS)
    out = bytearray()
    blocks = SIZE // 4
    for y in range(blocks):
        for x in range(blocks):
            cell = (y * CELLS // blocks) * CELLS + x * CELLS // blocks
            colour = rgb565(COLOURS[names[cell % len(names)]])
            out += bytes((255, 255, 0, 0, 0, 0, 0, 0))                 # alpha: 255 everywhere
            out += struct.pack("<HHI", colour, colour, 0)              # colour 0 everywhere
    return bytes(out)
