"""The Portal Gun: two portals on the level's surfaces, seen through and walked through.

The gun takes the Clank Zapper's place: its tile on the Weapons page, its slot in the Quick Select, its
name, icon and picture (pt_item, pt_text, pt_pick, pt_read_*). The Zapper never goes into his hand: picking
it fires a zap from Clank. So pt_pick takes that pick for the gun, and any other pick puts the gun away;
pt_switch does the same for the Weapons page and for Triangle twice.
Everything runs from hooks in shared code, so the mod needs none in the per-level copies of the hero:
the pad read, which hides Circle and Square from the game while the gun is in hand, and the entry of
PRE_DRAW, once a frame:

  input    Circle shoots the blue portal, Square the orange one: the level's ray (RAY) along the
           camera's view axis. A portal is a position, the wall's normal and two axes in the wall.
           It is worked out at once and comes into being when the shot, flying from his hand, gets there.
  model    The moby in his hand gets a copy of its model's header with our mesh in it (gunmesh.py),
           and its own model back when the gun is put away. Nothing of the game's model changes.
  travel   Ratchet inside a portal's ellipse, moving into it: he comes out of the other one with
           position and motion turned by the pair's rotation, and flies on (FLING) until he lands.
           Between two walls the wall is gone for him inside the opening (pt_wall_*), he crosses when
           his middle reaches the plane, and he can stop there or go back: half of him is seen on
           each side (pt_copy_*), as a hidden frame draws him where that view needs him. A floor
           and a ceiling work the same way, except that nothing holds him up in a floor portal.
  mobys    Enemies and shots go through as well, from the moby table (pt_mobys): a moby about to
           meet a portal comes out of the other one, and anything in its variables along its motion
           is turned with it, as each weapon keeps its heading somewhere else.
  view     With both portals up, one of them per frame gets a new picture: a whole hidden frame
           (see NOTES.md) from the camera mirrored through the pair, into that portal's surface.
           The renderer's matrices get the exit's plane as an oblique near plane, or the wall behind
           it would hide the view, and baked visibility is looked up from the room it shows.
  draw     Each portal is a fan of quads through QUAD, textured by screen position: a pixel of the
           portal shows the same pixel of the hidden frame, which is what looking through it means.

The pair's rotation: a vector with parts (a, b, c) along a portal's right, up and normal becomes
-a right + b up - c normal of the other one, half a turn about its up axis.

State block (tools/peek.py reads and writes it in a running game); +0x180.. are tuning values,
filled in on the first frame from TUNING:
    +0x00 frames, +0x04 non-zero: no hidden frames, +0x08 cooldown of travel, +0x0c fling frames
    +0x10 hidden camera's position, +0x20 its matrix, +0x60/+0x70 the real ones
    +0xe0 kept HUD buffer position, +0xe4/+0xe8 the surfaces kept, +0xec the renderer's frame count
    +0xf0 buttons last frame, +0xf4 frame last time, +0xf8 initialised
    +0x100, +0x130 the textures (TEXTURE_SIZE each)
    +0x160 Ratchet's position last frame, +0x170 scratch
    +0x180 tuning; +0x1c0 motion of the fling, +0x1d0.. scratch
    +0x200, +0x280 the blue and orange portal: +0 up, +0x10 position, +0x20 normal, +0x30 right, +0x40 up
    +0x300 the quad for QUAD, +0x3a0/+0x3a4 the colours, +0x3a8 the view's colour, +0x800 the last ray's result (0x60 bytes)
    +0x400 the pad's buttons, Circle and Square as on the pad, +0x404 the gun is in hand,
    +0x408 the buttons last frame, +0x40c non-zero: no gun here (ship, Giant Clank), +0x410 the mesh's place
    and the main heap's new end, +0x414 the level last frame, +0x418 the tools' buttons (digital 1 << 16 | digital 2),
    +0x41c their sticks (right x, y, left x, y), +0x420 booted without the Trilogy's menu, +0x440 the white texture, +0x4f0 the moby in his hand and
    +0x4e8 the row of the weapon behind the gun, +0x4ec its ammunition a pack, +0x4f4 its model, +0x4f8 its scale, +0x500 the copy of the model's header, +0x700 the mesh, +0x740 its groups,
    +0x760 its texture, +0x900.. scratch of the mobys that go through (+0x900 place, +0x910 motion,
    +0x920 where it meets the portal, +0x930, +0x940, +0x950), +0xa00.. the camera of a transit and
    +0xb00..0xc7f what is falling through a floor portal (their comments below), +0xd00 the real camera's matrix
    +0xe00 tuning of the walls (WALLS); +0xf00 the pose a transit is showing, before the side is chosen,
    +0xf40 the right stick has let the camera go in this transit,
    +0x1300 the moon: +4 the portal out there, or 0, +8 frames left, +0xc that shot was at it,
    +0x1310 the step, +0x1320 and +0x1330 the ends of its ray, +0x1340 frames he is left alone,
    +0x1400 what has gone out, +0x1500 MOONS, +0x1700 the shots in the air, +0x1780 the portals they carry,
    +0x1880 the block their blobs are drawn with, +0x18f0 mobys that went through, +0x18f4 the last one's class, +0x18f8 rays that went on, +0x1900 a ray's ends,
    +0x1a00 pt_switch: the game mode last time, +0x1a04 frames into the pause, +0x1a08 the gun was out last time,
    +0x1a0c the weapon the gun was out over when put away (Triangle twice to it brings the gun), or 0,
    +0x1a10 the weapon it was put away for, +0x1a14 the weapon under the gun, +0x1a18 the request dealt with already,
    +0x1a1c the weapon in hand last time,
    +0xe60 the portal Ratchet stands in, or 0, +0xe64 the other one, +0xe68 the camera is shown behind the
    exit, +0xe6c the pair: 1 two walls, 2 a floor and a ceiling, 3 anything else, +0xe78 how he went through: 1 on the
    ground, 2 by the floor and ceiling,
    +0x1000 the mobys drawn on the other side, as they were (0x60 each: moby, +0x10 their +0, +0x20 their
    position, +0x30 their rows)
"""
import math
import struct

from .game import *  # noqa: F403
from . import gunicon, gunmesh, gunpicture
from .game import CAMERA, FRAME_COUNTER, GAME_MODE, HERO, Hook, PRE_DRAW, STATE, pair

NAME = "portal"
TITLE = "Portal Gun"
ABOUT = "Blue and orange portals you can see through and walk through, keeping your momentum."

MEMCPY = 0x10D504C                 # (r3 destination, r4 source, r5 bytes)
PRE_DRAW_WORD = 0xF821FF41         # stdu r1, -0xc0(r1), the hook's place
PRE_DRAW_BODY = PRE_DRAW + 4
RENDERER = 0x1410D78               # -> the renderer
NO_FLIP = 0x1720                   # renderer: presentations to skip
VIEW_PROJECTION = 0xE0             # renderer: what the RSX draws with, near 0.1 always; +0x60 its projection
OCCLUSION_DATA = 0x156B200          # -> the level's baked visibility, or 0
OCCLUSION_LOOKUP = 0xB06960        # fills the mask of what can be seen from CAMERA_POS; BeginFrame calls it
FRAMES = 0x14                      # renderer: its frame count
SURFACE_A, SURFACE_B = 0x1B28, 0x1C7C   # renderer: the colour offsets of the two surface descriptors
BEGIN_FRAME = 0xB085E0             # (r3 = 1)
END_FRAME = 0xB08698
HUD_PASS = 0x1410C40               # -> the HUD's command buffer, +8 its write position
FRUSTUM_NEAR = 0x1466F98            # the last of six planes from 0x1466f48: a, b, c, d, world units
PASS_BUFFERS, PASSES = 0x1410C1C, 10    # -> each pass's command buffer, +8 its write position
RAY = 0x25468                      # (r3 from, r4 to, r5 = 2, r6 = 0, r7 = 0) -> hit
RAY_RESULT = 0x156B340             # +0x20 where it hit, +0x30/+0x40 vectors of the surface
QUAD = 0x2ED20                     # (r3 quad, r4 = 0, r5 = 0): a textured quad in the world
BLEND_STATE = 0x10D7D98            # the three encoders of the render states QUAD takes
DEPTH_STATE = 0x10D7DF8
TEXTURE_STATE = 0x10D7EC4
TAN_X, TAN_Y = 0x1472130, 0x1472134     # the tangents of half the field of view
GFX_HEAP_END = 0x1425554           # the graphics heap's end, twice; lowered to keep it off the surfaces
GFX_HEAP_LIMIT = 0xCF0B0000
MAIN_HEAP_END = 0x1425530          # the main heap's end, twice; kept off the gun's mesh
GCM_IO_ADDRESS = 0x1ABA204         # -> main memory seen by the RSX; buffers are offsets from it
# The main heap's place differs from boot to boot (0x40000000 or 0x50000000 seen), so the mesh goes
# into its last megabyte, worked out when the game runs. The RSX's own memory is always at 0xc0000000.
GUN_TEXTURE = 0xCF0C0000           # its texture, in the RSX's memory
PAD_READ = 0x10BFCF8               # bl PAD_GET, in shared code, with r3 the port and r4 the data
PAD_GET = 0x122479C                # cellPadGetData
HAND = HERO + 0x1220               # -> the moby in his hand; 0 as Giant Clank
ITEM_GUN, ITEM_GUN_UP = 0x09, 0x49 # the Clank Zapper and the Clank Shocker it upgrades to
ITEM_ROW, ITEM_ROW_SIZE = 0x1322A90, 0xD0     # item -> row by 0x1329a40, which is the same number
ROW_AMMO_PACK, ROW_AMMO_MOST = 0x84, 0x8A     # u16; 0 in the first: a weapon with no ammunition
OWNED, EVER = 0x1481A80, 0x1481AB8 # a byte per item
GUN_SCALE = 0x3E555555             # model +0x24, the Lancer's: the model his hand holds is filled in place
                                   # by each weapon, and a rocket launcher's scale makes the gun a quarter of its size
HAND_ITEM = HERO + 0x1248          # the item in his hand. Its row with no ammunition hides the HUD's weapon panel
SHOT_SLOT, SHOT_SLOT_2, SHOT_SLOT_SIZE = 0x1700, 0x1740, 0x40    # per colour: +0 frames left, +4 the portal, +8 at the moon, +0x10 where, +0x20 the step
SHOT_PENDING, SHOT_PENDING_SIZE = 0x1780, 0x80   # the portal as it will be when the shot gets there
SHOT_BLOB = 0x1880                 # a portal's block for pt_fan, to draw the shot with
SHOT_MOST = 60                     # frames in flight at the longest
MOON_SAFE = 600                    # frames he is left alone after going out (+0x1340)
MISSILE_CLASS, RYNO_CLASS, MISSILE_HEADING = 0x5DA, 0xED7, 0x30   # rocket tube, RYNO; in their variables a unit vector
HOVERBOMB_CLASS = 0x5D8
PULSE_CLASS = 0x5D6                # a shot with no model at all
SHOT_CLASSES = (MISSILE_CLASS, RYNO_CLASS, HOVERBOMB_CLASS, 0x87A, 0xA9B, 0xCE4,    # chopper, plasma, gravity bomb
                0x79, 0xAC, 0xCB, 0x1366, 0xB58)    # bomb glove, visibomb, decoy, miniturret, spiderbot
RAY_OUT = 0.1                      # a ray going on from the far portal starts this far off it
# Weapons that find what they hit with a ray: the return address of each RAY. A ray of these crossing an
# opening goes on from the other portal, and what it finds there is what the weapon hit.
WEAPON_RAYS = (0xCE81C8, 0xCE40E4,     # pulse rifle, blitz gun: these name his moby
               0xCD4728, 0xCF8D14,     # lava gun, tesla claw: these name the hand
               0xC2A7A4, 0xC2AFD0, 0xC2B238, 0xC2B7CC)   # sheepinator
RAY_LAVA = 0xCD4728                # from a droplet, +0 where it is and +0x10 its motion, to where it is going
   # model kind -1: missile, hoverbomb, chopper, plasma, gravity bomb
QUICK = 0x1481C40                  # eight words: the items of the Quick Select
HUD_ICONS = 0x15784B0              # +0x1c {u16 id, versions, first sprite, 0}.., +0x20 sprite -> texture number
HUD_TEXTURES = 0x1571938           # -> the texture entries, 0x24 each, +0 the offset in the RSX's memory
ICON_GUN = 0xEA99                  # the Clank Zapper's icon
TEXT_LOOKUP, TEXT_WORD = 0xB28F38, 0x3C800134 # (r3 id) -> the string; lis r4, 0x134, the hook's place
TEXT_BODY = TEXT_LOOKUP + 4
TEXT_NAME, TEXT_NAME_UP, TEXT_ABOUT, TEXT_GOT, TEXT_UPGRADED, TEXT_AMMO = 0xAA9, 0x1BDF, 0x2FBF, 0x12B4, 0x12B6, 0x12E3
PICK, PICK_WORD = 0xB30C24, 0x907A22C8        # stw r3, 0x22c8(r26): the Quick Select's choice, r26 the hero
WANTED = 0x22C8                    # hero: the item he goes on to take out, a request; 0 once it is done
WANTED_ITEM = HERO + WANTED
# The Weapons page (pause menu): its choice, which it gives WANTED as the menu closes; on opening the
# menu it is the weapon in hand. The page takes only weapons (row +8 = 0): the Zapper's is 3.
SELECTION = 0x15B2F90
ROW_TYPE, GADGET_TYPE = 8, 3
ROW_TYPE_GUN = ITEM_ROW + ITEM_GUN * ITEM_ROW_SIZE + ROW_TYPE
ROW_TYPE_GUN_UP = ITEM_ROW + ITEM_GUN_UP * ITEM_ROW_SIZE + ROW_TYPE
MODE_PAUSE = 3                     # GAME_MODE in the pause menu, where PRE_DRAW does not run
PAUSE_FRAMES = 30                  # how long into a pause the page's choice is still the game's own
READ_FILE = 0x10D8D4C              # (r3 path, r4 where, r5 most bytes) -> above 0 if it worked
PICTURE_READS = ((0xBCFA3C, 0xBCFA7C), (0xBD04B8, 0xBD04E8), (0xBD06A4, 0xBD06D4), (0xBD0868, 0xBD0898))   # header, pixels
PICTURES_WEAPONS, PICTURES_HELP = 4, 10   # screen_weapons, help_weapons, in the table at 0x1345870
PICTURE_ZAPPER, PICTURE_SHOCKER = 38, 39
HERO_STATE = HERO + 0x2294
GLIDE_STATE = 8                    # the Heli-Pack's glide (Cross held in the air, Clank on his back)
SHIP_STATE = 0x31                  # in the starship levels
LEVEL = 0x1329A3C                  # the level loaded
HERO_MOBY = HERO + 0x2290
APP_NAME = 0x10D9930               # (r3 the app, r4 its name), where the name is taken
APP_NAME_BODY = APP_NAME + 4
APP_NAME_WORD = 0xF821FF71         # stdu r1, -0x90(r1), the hook's place
REGION_SET = 0x10D9B30             # where all the tests of the region meet, r30 the app
REGION_BODY = REGION_SET + 4
REGION_WORD = 0x3C600124           # lis r3, 0x124, the hook's place
APP_REGION, REGION_EUROPE = 0xC0, 1
PASTE = 0xB0AE6C                   # (x, y, w, h, source x, y, w, h; sp+0x74 colour, sp+0x7c texture)
HUD_DIM = 0x3000                   # alpha, high half: a portal not placed
L1 = 4                             # in the state block's button word
MOBY_TABLE = 0x156B278             # -> the first moby (Ratchet), then -> the end, 0x100 each
MOBY_TABLE_END = MOBY_TABLE + 4
MAIN_HEAP = 0x1425528              # the main heap's base; its end is MAIN_HEAP_END
OPD_FIRST, OPD_LAST = 0x12E3688, 0x13150F0   # an update function's pointer is in here
KIND_ENEMY, KIND_SHOT = 5, 4       # model +0x46
LANCER_SHOT = 0x1304740            # moby +0x64 of class 0xbfe
LANCER_TARGET = 0x1C               # in its variables; the game writes 0 there itself
MOBY_DYING = 0xFD                  # state byte +0x20: from here on it is dead or spent
MOBY_VARS, MOBY_VARS_LAST = 0x80, 0x74       # a moby's variables at +0x68, and the last vector's place
MOBY_TRACK_HIGH = 8                # behind the mesh: the last position of each moby, at +0x80000
MOBY_TRACK_SIZE = 0x20             # +0 place, +0xc frame seen, +0x10 frame it may go through again
MOBY_COOLDOWN = 12
CARRIED = 8                        # mobys falling through at a time
SINK_FRAMES, CARRY_CLEAR, CARRY_FRAMES = 22, 34, 300   # frames of sinking; until the ray is safe; at most
CARRY_COOLDOWN = 120
CAM_FRAMES = 300                   # a transit at the longest
CAM_STICK = 70                     # the right stick past this, off its middle
CAM_LATE = 240                     # frames left: the camera eases over whatever way the game's faces
HERO_YAW, HERO_YAW_WANTED, HERO_HEADING = 0x98, 0x1A0, 0x1458
WALL_SPHERE, WALL_SPHERE_WORD = 0x278A8, 0xF821D751     # (r3 centre, f1 radius, r6 moby), against the level
WALL_CAPSULE, WALL_CAPSULE_WORD = 0x2A3B8, 0xF821D741   # (r3 centre, f1 radius, f2 height, r7 moby)
WALL_SPHERE_BODY, WALL_CAPSULE_BODY = WALL_SPHERE + 4, WALL_CAPSULE + 4
RAY_WORD, RAY_BODY = 0xf821d801, RAY + 4
HERO_VELOCITY, HERO_MOVED = 0xF0, 0x110      # from RC1's +0xe0 and +0x100
HERO_VEL_Z = HERO + HERO_VELOCITY + 8   # the game's own up and down speed: gravity about 0.006 a frame, falls top out at 0.43
HELD_STEP, HELD_COUNT = 0x50, 7     # the table of what hangs on him, from HAND
HELD_END = HERO + 0x1220 + HELD_STEP * HELD_COUNT
COPY_MOBYS = 1 + HELD_COUNT        # drawn on the other side at most
COPY_SAVED, COPY_LAST = 0x1000, 0x1000 + 0x60 * HELD_COUNT    # as they were, 0x60 each
# The moons: level -> their height over the horizon and how far from it counts, in degrees. A height and
# no direction, as some skies turn (the moon of level 2 goes round at about 0.4 degrees a second, and
# what drives that was not found): a turning sky keeps its height. Open sky at that height counts too.
MOONS = {2: (55, 7), 7: (16, 11), 19: (19, 10), 20: (41, 15), 26: (22, 8)}
MOON_LEVELS = 27
SHOT_BLOBS, SHOT_MIDDLE = 4, 3     # how far behind the head (in steps of flight) and its radius; the last is its white middle
RINGS = (0.93, 0.74, 0.54, 0.3, 0.0)         # the inside of a portal, as parts of its radius
TEXT_GUN = b"Portal Gun"
TEXT_GUN_ABOUT = b"\x0cPortal Gun\x08: \x11 shoots a blue portal, \x13 an orange one. Go in one and out of the other."
TEXT_GUN_GOT = b"You got the \x0cPortal Gun\x08!"
MOON_FRAMES = 600                  # the opening stays this long, if nothing ends it first
MOON_KIND_CRATE = 9                # model +0x46, with the enemies and shots
PARKED = 64                        # what has been sucked out, at most
WHITE = 0xCF0FFF00                 # four by four white pixels, behind the heap
SURFACE_0, SURFACE_1 = 0x0F100000, 0x0F500000
TEXTURE_SIZE = 0x24
CAMERA_POS = CAMERA + 0x140
CAMERA_MATRIX = CAMERA + 0x370
HERO_POS = HERO + 0x80
HERO_GROUND = HERO + 0x318          # the height of the ground under him
BLUE, ORANGE = 0x20, 0x80          # pad bits of Circle and Square
SEGMENTS_RING = 24                 # the fan's quads

# Tuning: name -> state offset, default
TUNING = dict(RADIUS_X=(0x180, 1.0), RADIUS_Y=(0x184, 1.45), TRIGGER=(0x188, 0.75), BEHIND=(0x18C, 0.9),
              CENTRE_Z=(0x190, 0.6), PUSH=(0x194, 0.95), WALL_LOOK=(0x19C, 6.0),
              RAY_START=(0x1A0, 5.0), RAY_LENGTH=(0x1A4, 150.0), LIFT=(0x1A8, 0.02), GROUND_GAP=(0x1AC, 0.12),
              SCALE_U=(0x1B0, 1.0), SCALE_V=(0x1B4, 1.0))
NORMAL_AT = 0x1B8                  # the offset of the normal in RAY_RESULT
SEE_THROUGH = 0x1BC                # for tuning: non-zero shows the insides as solid colour
FLING_FRAMES, COOLDOWN = 240, 40
locals().update({k: v[0] for k, v in TUNING.items()})
# The same for a pair of walls, read by code that has no register for the pool (pt_wall_gone)
WALLS = dict(WALL_FRONT=(0xE00, 1.0), WALL_BACK=(0xE04, 0.6), CROSS_GAP=(0xE08, 0.03), COPY_ZONE=(0xE0C, 1.3),
             CAM_GLIDE=(0xE10, 0.15), WALL_FLAT=(0xE14, 0.3), CROSS_GROUND=(0xE18, 0.3), WALL_ONE=(0xE1C, 1.0),
             CLIP_SCALE=(0xE20, 1.4), CULL_FROM=(0xE24, 1.0), STACK_FLAT=(0xE28, 0.9), STACK_BEHIND=(0xE2C, 5.0),
             MOON_PULL=(0xE30, 1.1), MOON_RANGE=(0xE34, 22.0), MOON_EAT=(0xE38, 1.5), MOON_FAR=(0xE3C, 400.0),
             MOON_MOST=(0xE40, 0.32), MOON_OFF=(0xE44, 0.3), MOON_PARK=(0xE48, 4000.0), MOON_DEATH=(0xE4C, -60.0),
             MOON_RAMP=(0xE50, 150.0), MOON_EAT_MOBY=(0xE54, 3.0), MOON_CLEAR=(0xE58, 1.6), FLOOR_CROSS=(0xE5C, 0.85))
locals().update({k: v[0] for k, v in WALLS.items()})
INITIAL_NORMAL_AT = 0x40


def texture(offset, size=0x050002D0, pitch=0x1400):
    return struct.pack(">8I", offset, 0x0001A529, 0x00030303, 0x80010000, 0x0000AAE4, 0x02062000, size, 0x00100000 | pitch) + b"\0\xff\0\0"


def dot(out, a_reg, a_at, b_reg, b_at, scratch):
    """f<out> = dot product of two vectors in memory."""
    return f"""
    lfs {out}, {a_at}({a_reg})
    lfs {scratch}, {b_at}({b_reg})
    fmuls {out}, {out}, {scratch}
    lfs {scratch}, {a_at + 4}({a_reg})
    lfs {scratch + 1}, {b_at + 4}({b_reg})
    fmadds {out}, {scratch}, {scratch + 1}, {out}
    lfs {scratch}, {a_at + 8}({a_reg})
    lfs {scratch + 1}, {b_at + 8}({b_reg})
    fmadds {out}, {scratch}, {scratch + 1}, {out}
"""


def sub(a_reg, a_at, b_reg, b_at, out_reg, out_at):
    """out = a - b, three floats."""
    return "".join(f"""
    lfs 1, {a_at + i}({a_reg})
    lfs 2, {b_at + i}({b_reg})
    fsubs 1, 1, 2
    stfs 1, {out_at + i}({out_reg})
""" for i in (0, 4, 8))


def add_scaled(a_reg, a_at, f, b_reg, b_at, out_reg, out_at):
    """out = a + f<f> * b, three floats."""
    return "".join(f"""
    lfs 1, {a_at + i}({a_reg})
    lfs 2, {b_at + i}({b_reg})
    fmadds 1, 2, {f}, 1
    stfs 1, {out_at + i}({out_reg})
""" for i in (0, 4, 8))


def load(reg, address_name):
    return f"""
    lis {reg}, {{{address_name}_HA}}
    addi {reg}, {reg}, {{{address_name}_LO}}
"""


def opening(point, lift, portal, base, front, back, miss):
    """Goes on when a point in memory is inside a portal's ellipse and between front and back of
    the wall (tuning offsets), and branches to miss when not. f3-f8; base holds the state block."""
    return "".join(f"""
    lfs {3 + n}, {n * 4}({point})
    lfs 6, {0x10 + n * 4}({portal})
    fsubs {3 + n}, {3 + n}, 6
""" for n in range(3)) + (f"""
    lfs 6, {CENTRE_Z}({base})
    fadds 5, 5, 6
""" if lift else "") + f"""
    lfs 6, 0x20({portal})
    fmuls 6, 6, 3
    lfs 7, 0x24({portal})
    fmadds 6, 7, 4, 6
    lfs 7, 0x28({portal})
    fmadds 6, 7, 5, 6
    lfs 7, {front}({base})
    fcmpu 0, 6, 7
    bge {miss}
    lfs 7, {back}({base})
    fneg 7, 7
    fcmpu 0, 6, 7
    blt {miss}
    lfs 6, 0x30({portal})
    fmuls 6, 6, 3
    lfs 7, 0x34({portal})
    fmadds 6, 7, 4, 6
    lfs 7, 0x38({portal})
    fmadds 6, 7, 5, 6
    lfs 7, {RADIUS_X}({base})
    fdivs 6, 6, 7
    fmuls 6, 6, 6
    lfs 8, 0x40({portal})
    fmuls 8, 8, 3
    lfs 7, 0x44({portal})
    fmadds 8, 7, 4, 8
    lfs 7, 0x48({portal})
    fmadds 8, 7, 5, 8
    lfs 7, {RADIUS_Y}({base})
    fdivs 8, 8, 7
    fmadds 6, 8, 8, 6
    lfs 7, {WALL_ONE}({base})
    fcmpu 0, 6, 7
    bge {miss}
"""


def through_opening(miss):
    """Goes on when the segment r3 -> r4 crosses the plane of the portal r11 inside its ellipse, either
    way: coming out of a ceiling his ground ray starts above it. Branches to miss when not. r10 the
    state block. f3-f13."""
    return "".join(f"""
    lfs {3 + n}, {n * 4}(3)
    lfs 9, {0x10 + n * 4}(11)
    fsubs {3 + n}, {3 + n}, 9
    lfs {6 + n}, {n * 4}(4)
    fsubs {6 + n}, {6 + n}, 9
""" for n in range(3)) + f"""
    lfs 11, 0x20(11)
    lfs 12, 0x24(11)
    lfs 13, 0x28(11)
    fmuls 9, 3, 11
    fmadds 9, 4, 12, 9
    fmadds 9, 5, 13, 9
    fmuls 10, 6, 11
    fmadds 10, 7, 12, 10
    fmadds 10, 8, 13, 10
    fsubs 11, 11, 11
    fmuls 12, 9, 10
    fcmpu 0, 12, 11
    bge {miss}
    fsubs 10, 9, 10
    fdivs 9, 9, 10
""" + "".join(f"""
    fsubs {6 + n}, {6 + n}, {3 + n}
    fmadds {3 + n}, {6 + n}, 9, {3 + n}
""" for n in range(3)) + f"""
    lfs 6, 0x30(11)
    fmuls 6, 6, 3
    lfs 7, 0x34(11)
    fmadds 6, 7, 4, 6
    lfs 7, 0x38(11)
    fmadds 6, 7, 5, 6
    lfs 7, {RADIUS_X}(10)
    fdivs 6, 6, 7
    fmuls 6, 6, 6
    lfs 8, 0x40(11)
    fmuls 8, 8, 3
    lfs 7, 0x44(11)
    fmadds 8, 7, 4, 8
    lfs 7, 0x48(11)
    fmadds 8, 7, 5, 8
    lfs 7, {RADIUS_Y}(10)
    fdivs 8, 8, 7
    fmadds 6, 8, 8, 6
    lfs 7, {WALL_ONE}(10)
    fcmpu 0, 6, 7
    bge {miss}
"""


CODE = """
pt_draw_hook:
    stdu 1, -0x120(1)
    mflr 0
    std 0, 0x130(1)
    std 31, 0x118(1)
    std 30, 0x110(1)
    std 29, 0x108(1)
    std 28, 0x100(1)
    std 27, 0xf8(1)
    std 26, 0xf0(1)
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    lwz 3, 0(31)
    addi 3, 3, 1
    stw 3, 0(31)
    lis 5, {GAME_MODE_HA}
    lwz 5, {GAME_MODE_LO}(5)
    cmpwi 5, 0
    bne pt_plain
    bl pt_init
    bl pt_input
    bl pt_near
    bl pt_travel
    bl pt_cam_apply
    bl pt_carry
    bl pt_moon
    lwz 3, 0x200(31)
    lwz 4, 0x280(31)
    and. 3, 3, 4
    beq pt_shown
    lwz 3, 0x1304(31)                # with the moon nothing goes through: it all goes out
    cmpwi 3, 0
    bne pt_no_mobys
    bl pt_mobys
pt_no_mobys:
    lwz 3, 4(31)
    cmpwi 3, 0
    bne pt_shown

    # the portal looked through this frame, and the one its view comes out of
    lwz 3, 0(31)
    clrlwi 3, 3, 31
    # with Ratchet in one, that one gets the view every frame: half of him is in it
    lwz 4, 0xe60(31)
    cmpwi 4, 0
    beq pt_view_turn
    lwz 5, 0xe68(31)
    cmpwi 5, 0
    beq pt_view_his
    lwz 4, 0xa08(31)
pt_view_his:
    li 3, 0
    addi 5, 31, 0x200
    cmpw 4, 5
    beq pt_view_turn
    li 3, 1
pt_view_turn:
    addi 30, 31, 0x200
    addi 29, 31, 0x280
    cmpwi 3, 0
    beq pt_chosen
    addi 30, 31, 0x280
    addi 29, 31, 0x200
pt_chosen:
    mr 28, 3
    # A portal nobody can see needs no picture. Not while he is in one or the camera is going through.
    lwz 3, 0xe60(31)
    cmpwi 3, 0
    bne pt_view_wanted
    lwz 3, 0xa00(31)
    cmpwi 3, 0
    bne pt_view_wanted
    lis 3, {CAMERA_POS_HA}
    addi 3, 3, {CAMERA_POS_LO}
    lis 4, {CAMERA_MATRIX_HA}
    addi 4, 4, {CAMERA_MATRIX_LO}
""" + sub(30, 0x10, 3, 0, 31, 0x170) + dot(1, 31, 0x170, 30, 0x20, 2) + """
    fsubs 2, 2, 2
    fcmpu 0, 1, 2
    bge pt_shown                     # seen from behind its wall
""" + dot(3, 31, 0x170, 4, 0, 5) + dot(6, 31, 0x170, 31, 0x170, 7) + """
    fsqrts 6, 6
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 7, {P_view_near}(3)
    fcmpu 0, 6, 7
    blt pt_view_wanted
    lfs 7, {P_view_cone}(3)
    fmuls 6, 6, 7
    fcmpu 0, 3, 6
    blt pt_shown                     # off to the side of the view, or behind it
pt_view_wanted:
    bl pt_hidden_camera
    bl pt_swap_in
    lis 27, {HUD_PASS_HA}
    lwz 27, {HUD_PASS_LO}(27)
    lwz 26, 8(27)
    lwz 3, 0xe60(31)                 # he stands in the portal looked through: this view has his other half
    cmpw 3, 30
    bne pt_hidden_draw
    mr 3, 30
    mr 4, 29
    bl pt_copy_on
pt_hidden_draw:
    # The baked visibility BeginFrame looked up is the game camera's, and from behind a wall there
    # is none: it is looked up again from the room this view shows. The next BeginFrame puts it back.
    # Some levels have none at all (24), and the lookup does not test for that.
    lis 3, {OCCLUSION_DATA_HA}
    lwz 3, {OCCLUSION_DATA_LO}(3)
    cmpwi 3, 0
    beq pt_hidden_seen
    lfs 3, {CULL_FROM}(31)
    lis 3, {CAMERA_POS_HA}
    addi 3, 3, {CAMERA_POS_LO}
""" + add_scaled(29, 0x10, 3, 29, 0x20, 3, 0) + """
    bl {OCCLUSION_LOOKUP}
    lis 3, {CAMERA_POS_HA}
    addi 3, 3, {CAMERA_POS_LO}
    lwz 4, 0x10(31)
    stw 4, 0(3)
    lwz 4, 0x14(31)
    stw 4, 4(3)
    lwz 4, 0x18(31)
    stw 4, 8(3)
pt_hidden_seen:
    bl pt_original
    bl pt_copy_off
    stw 26, 8(27)
    bl pt_swap_out

    lis 30, {RENDERER_HA}
    lwz 30, {RENDERER_LO}(30)
    li 3, 1
    stw 3, {NO_FLIP}(30)
    lwz 3, {SURFACE_A}(30)
    stw 3, 0xe4(31)
    lwz 3, {SURFACE_B}(30)
    stw 3, 0xe8(31)
    mulli 3, 28, 0x30
    add 3, 3, 31
    lwz 3, 0x100(3)
    stw 3, {SURFACE_A}(30)
    stw 3, {SURFACE_B}(30)
    lwz 3, {FRAMES}(30)
    stw 3, 0xec(31)
    bl {END_FRAME}
    lwz 3, 0xe4(31)
    stw 3, {SURFACE_A}(30)
    lwz 3, 0xe8(31)
    stw 3, {SURFACE_B}(30)
    # The frame count goes on past the hidden frame: per-object work is stamped with it, and on the
    # same number the real frame would reuse results from the hidden camera. Two ahead keeps the
    # next hidden frame's parity alternating, and the flip's buffer comes from that parity.
    lwz 3, 0xec(31)
    addi 3, 3, 2
    stw 3, {FRAMES}(30)
    li 3, 1
    bl {BEGIN_FRAME}

pt_shown:
    # he has crossed, and the camera has not: it sees him come out of the portal on its own side
    lwz 3, 0xe68(31)
    cmpwi 3, 0
    beq pt_shown_here
    lwz 3, 0xe60(31)
    lwz 4, 0xa04(31)
    cmpw 3, 4
    bne pt_shown_here
    lwz 4, 0xa08(31)
    bl pt_copy_on
pt_shown_here:
    bl pt_original
    bl pt_copy_off
    bl pt_draw
    bl pt_hud
    b pt_done

pt_plain:
    li 3, 0
    stw 3, 0xa00(31)                 # a transit does not outlast the game leaving play
    bl pt_original
pt_done:
    bl pt_cam_restore
    ld 26, 0xf0(1)
    ld 27, 0xf8(1)
    ld 28, 0x100(1)
    ld 29, 0x108(1)
    ld 30, 0x110(1)
    ld 31, 0x118(1)
    ld 0, 0x130(1)
    mtlr 0
    addi 1, 1, 0x120
    blr

pt_original:
    stdu 1, -0xc0(1)
    b {PRE_DRAW_BODY}

# once: the tuning values, the textures, the graphics heap kept off the surfaces
pt_init:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 3, 0x410(31)
    cmpwi 3, 0
    bne pt_have_room
    lis 4, {MAIN_HEAP_END_HA}
    lwz 3, {MAIN_HEAP_END_LO}(4)
    rlwinm 3, 3, 0, 0, 11
    lis 4, 0x10
    subf 3, 4, 3
    stw 3, 0x410(31)
pt_have_room:
    lis 4, {MAIN_HEAP_END_HA}
    addi 4, 4, {MAIN_HEAP_END_LO}
    stw 3, 0(4)
    stw 3, 4(4)
    lis 3, {GFX_HEAP_LIMIT_HA}
    addi 3, 3, {GFX_HEAP_LIMIT_LO}
    lis 4, {GFX_HEAP_END_HA}
    addi 4, 4, {GFX_HEAP_END_LO}
    stw 3, 0(4)
    stw 3, 4(4)
    lwz 3, 0xf8(31)
    cmpwi 3, 0
    bne pt_init_done
    li 3, 1
    stw 3, 0xf8(31)
    li 3, {INITIAL_NORMAL_AT}
    stw 3, {NORMAL_AT}(31)
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    addi 3, 3, {P_tuning}
    addi 4, 31, 0x180
    li 5, {TUNING_WORDS}
    mtctr 5
pt_init_tuning:
    lwz 5, 0(3)
    stw 5, 0(4)
    addi 3, 3, 4
    addi 4, 4, 4
    bdnz pt_init_tuning
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    addi 3, 3, {P_walls}
    addi 4, 31, 0xe00
    li 5, {WALL_WORDS}
    mtctr 5
pt_init_walls:
    lwz 5, 0(3)
    stw 5, 0(4)
    addi 3, 3, 4
    addi 4, 4, 4
    bdnz pt_init_walls
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    addi 3, 3, {P_moons}
    addi 4, 31, 0x1500
    li 5, {MOON_WORDS}
    mtctr 5
pt_init_moons:
    lwz 5, 0(3)
    stw 5, 0(4)
    addi 3, 3, 4
    addi 4, 4, 4
    bdnz pt_init_moons
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    addi 3, 3, {P_textures}
    addi 4, 31, 0x100
    li 5, 24
    mtctr 5
pt_init_textures:
    lwz 5, 0(3)
    stw 5, 0(4)
    addi 3, 3, 4
    addi 4, 4, 4
    bdnz pt_init_textures
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    addi 3, 3, {P_white}
    addi 4, 31, 0x440
    li 5, 9
    mtctr 5
pt_init_white:
    lwz 5, 0(3)
    stw 5, 0(4)
    addi 3, 3, 4
    addi 4, 4, 4
    bdnz pt_init_white
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lwz 4, {P_blue}(3)
    stw 4, 0x3a0(31)
    lwz 4, {P_orange}(3)
    stw 4, 0x3a4(31)
    lwz 4, {P_clear}(3)
    stw 4, 0x3a8(31)
    lis 3, {WHITE_HA}
    addi 3, 3, {WHITE_LO}
    clrldi 3, 3, 32                  # lis sign-extends, and this address has the top bit set
    li 4, -1
    li 5, 16
    mtctr 5
pt_init_pixels:
    stw 4, 0(3)
    addi 3, 3, 4
    bdnz pt_init_pixels
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    addi 3, 3, {P_mesh}
    addi 4, 31, 0x700
    li 5, {MESH_WORDS}
    mtctr 5
pt_init_mesh:
    lwz 5, 0(3)
    stw 5, 0(4)
    addi 3, 3, 4
    addi 4, 4, 4
    bdnz pt_init_mesh
    lwz 3, 0x410(31)
    lis 4, {GCM_IO_ADDRESS_HA}
    lwz 4, {GCM_IO_ADDRESS_LO}(4)
    subf 4, 4, 3
    stw 4, 0x710(31)
    addi 4, 4, {GUN_VERTICES}
    stw 4, 0x714(31)
    lis 4, {GUN_HA}
    addi 4, 4, {GUN_LO}
    li 5, {GUN_SIZE}
    bl {MEMCPY}
    lis 3, {GUN_TEXTURE_HA}
    addi 3, 3, {GUN_TEXTURE_LO}
    clrldi 3, 3, 32
    lis 4, {GUN_HA}
    addi 4, 4, {GUN_LO}
    addi 4, 4, {GUN_SIZE}
    li 5, {GUN_PIXELS}
    bl {MEMCPY}
pt_init_done:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

# the buttons, and clearing the portals when a level starts
pt_input:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lis 3, {FRAME_COUNTER_HA}
    lwz 3, {FRAME_COUNTER_LO}(3)
    lwz 4, 0xf4(31)
    stw 3, 0xf4(31)
    lis 5, {LEVEL_HA}
    lwz 5, {LEVEL_LO}(5)
    lwz 6, 0x414(31)
    stw 5, 0x414(31)
    cmpw 5, 6
    bne pt_new_level
    cmplw 3, 4
    bge pt_same_level
    b pt_respawned                   # the count starts again when he dies: the portals stay for that
pt_new_level:
    li 3, 0
    stw 3, 0x200(31)
    stw 3, 0x280(31)
    stw 3, 0x1304(31)
    stw 3, 0x1308(31)
    stw 3, 0x1340(31)
pt_respawned:
    li 3, 0
    stw 3, 0xc(31)
    stw 3, 0x4f0(31)                 # the moby in his hand went with the level
    stw 3, 0xa00(31)                 # a transit's way means nothing here
    stw 3, 8(31)
    stw 3, {SHOT_SLOT}(31)
    stw 3, {SHOT_SLOT_2}(31)
    bl pt_item
    li 3, 0
    addi 4, 31, 0x1400
    li 5, {PARKED}
    mtctr 5
pt_new_level_parked:
    stw 3, 0(4)
    addi 4, 4, 4
    bdnz pt_new_level_parked
pt_same_level:
    # no gun without Ratchet's hand or in the ship: Circle and Square are theirs then
    li 5, 0
    lis 3, {HAND_HA}
    lwz 3, {HAND_LO}(3)
    cmpwi 3, 0
    bne pt_has_hand
    li 5, 1
pt_has_hand:
    lis 3, {HERO_STATE_HA}
    lwz 3, {HERO_STATE_LO}(3)
    cmpwi 3, {SHIP_STATE}
    bne pt_not_ship
    li 5, 1
pt_not_ship:
    stw 5, 0x40c(31)
    lwz 3, 0x400(31)
    lwz 4, 0x408(31)
    stw 3, 0x408(31)
    andc 26, 3, 4
    bl pt_model
    lwz 3, 0x404(31)
    cmpwi 3, 0
    beq pt_input_done
    lwz 3, 0x40c(31)
    cmpwi 3, 0
    bne pt_input_done
    andi. 3, 26, {BLUE}
    beq pt_not_blue
    addi 3, 31, 0x200
    bl pt_fire
pt_not_blue:
    andi. 3, 26, {ORANGE}
    beq pt_input_done
    addi 3, 31, 0x280
    bl pt_fire
pt_input_done:
    bl pt_shots_step
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

# Every level: the gun is owned, on the Quick Select if there is room, and shows its icon. The icon's
# pixels are the level's own, so the Clank Zapper's are written over in each.
pt_item:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    li 4, 1
    lis 3, {OWNED_HA}
    addi 3, 3, {OWNED_LO}
    stb 4, {ITEM_GUN}(3)
    lis 3, {EVER_HA}
    addi 3, 3, {EVER_LO}
    stb 4, {ITEM_GUN}(3)
    lis 3, {QUICK_HA}
    addi 3, 3, {QUICK_LO}
    li 5, 8
    mtctr 5
    li 6, 0
pt_item_slot:
    lwz 4, 0(3)
    cmpwi 4, {ITEM_GUN}
    beq pt_item_icon
    cmpwi 4, {ITEM_GUN_UP}
    beq pt_item_icon
    cmpwi 4, 0
    bne pt_item_next
    cmpwi 6, 0
    bne pt_item_next
    mr 6, 3
pt_item_next:
    addi 3, 3, 4
    bdnz pt_item_slot
    cmpwi 6, 0
    beq pt_item_icon
    li 4, {ITEM_GUN}
    stw 4, 0(6)
pt_item_icon:
    lis 3, {HUD_ICONS_HA}
    addi 3, 3, {HUD_ICONS_LO}
    lwz 4, 0x1c(3)
    lwz 5, 0x20(3)
    lis 6, {HUD_TEXTURES_HA}
    lwz 6, {HUD_TEXTURES_LO}(6)
    cmpwi 4, 0
    beq pt_item_done
    cmpwi 5, 0
    beq pt_item_done
    cmpwi 6, 0
    beq pt_item_done
    li 7, 0x200
    mtctr 7
pt_item_find:
    lhz 7, 0(4)
    cmplwi 7, {ICON_GUN}
    beq pt_item_found
    cmplwi 7, 0xffff
    beq pt_item_done
    addi 4, 4, 8
    bdnz pt_item_find
    b pt_item_done
pt_item_found:
    lhz 7, 4(4)
    slwi 7, 7, 2
    lwzx 7, 5, 7
    mulli 7, 7, 0x24
    lwzx 3, 6, 7
    oris 3, 3, 0xc000
    lis 4, {ICON_HA}
    addi 4, 4, {ICON_LO}
    li 5, {ICON_BYTES}
    bl {MEMCPY}
pt_item_done:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

# the game's text lookup: the Zapper's lines in every language are the gun's (a leaf: r3 to r8 are free)
pt_text:
    li 4, {P_text_name}
    cmpwi 3, {TEXT_NAME}
    beq pt_text_ours
    cmpwi 3, {TEXT_NAME_UP}
    beq pt_text_ours
    li 4, {P_text_about}
    cmpwi 3, {TEXT_ABOUT}
    beq pt_text_ours
    li 4, {P_text_got}
    cmpwi 3, {TEXT_GOT}
    beq pt_text_ours
    cmpwi 3, {TEXT_UPGRADED}
    beq pt_text_ours
    cmpwi 3, {TEXT_AMMO}
    beq pt_text_ours
    lis 4, 0x134
    b {TEXT_BODY}
pt_text_ours:
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    add 3, 3, 4
    blr

# What the Quick Select chose, in place of stw r3, 0x22c8(r26). Only r11, r12 are free here.
pt_pick:
    lis 12, {STATE_HA}
    addi 12, 12, {STATE_LO}
    cmpwi 3, {ITEM_GUN}
    beq pt_pick_gun
    cmpwi 3, {ITEM_GUN_UP}
    beq pt_pick_gun
    li 11, 0
    stw 11, 0x404(12)
    stw 11, 0x1a0c(12)               # chosen here: the gun no longer stands behind the last weapon
    stw 3, {WANTED}(26)
    blr
pt_pick_gun:
    li 11, 1
    stw 11, 0x404(12)
    lwz 11, {WANTED}(26)             # a switch under way is not a new choice for pt_switch
    stw 11, 0x1a18(12)
    blr

# Weapon switches pt_pick does not see: the Weapons page and Triangle twice (the game's last weapon,
# 0x1329a9c, read in the per-level copies). The page ends in a request in WANTED; Triangle twice only
# shows in the weapon in hand, the gun's own weapon standing for the gun as the last one. It runs
# from the pad read, which goes on in the pause menu, where PRE_DRAW does not. r31 the state block;
# r3..r12 only.
pt_switch:
    lis 3, {GAME_MODE_HA}
    lwz 3, {GAME_MODE_LO}(3)
    cmpwi 3, {MODE_PAUSE}            # the Weapons page shows the weapon under the gun with its ammunition:
    bne pt_switch_rows               # the row gets it back, and pt_switch_gun or pt_model takes it again.
    lis 4, {WANTED_ITEM_HA}          # Only once the page has opened (it asks for the weapon in hand): the
    lwz 4, {WANTED_ITEM_LO}(4)       # HUD's weapon panel is decided as the pause begins, and stays
    cmpwi 4, 0
    beq pt_switch_rows
    lwz 4, 0x4e8(31)
    cmpwi 4, 0
    beq pt_switch_rows
    lwz 5, 0x4ec(31)
    sth 5, {ROW_AMMO_PACK}(4)
    li 5, 0
    stw 5, 0x4e8(31)
pt_switch_rows:
    li 6, {GADGET_TYPE}              # the page takes the gun as a weapon, everything else as a gadget
    cmpwi 3, {MODE_PAUSE}
    bne pt_switch_type
    li 6, 0
pt_switch_type:
    lis 4, {ROW_TYPE_GUN_HA}
    stw 6, {ROW_TYPE_GUN_LO}(4)
    lis 4, {ROW_TYPE_GUN_UP_HA}
    stw 6, {ROW_TYPE_GUN_UP_LO}(4)
    lis 4, {HAND_ITEM_HA}
    lwz 7, {HAND_ITEM_LO}(4)         # r7 the weapon in hand, under the gun if it is out
    lwz 8, 0x404(31)                 # r8 the gun is out
    lis 4, {SELECTION_HA}
    lwz 9, {SELECTION_LO}(4)         # r9 the page's choice
    li 10, {ITEM_GUN}                # r10 the gun's item
    lis 4, {OWNED_HA}
    addi 4, 4, {OWNED_LO}
    lbz 4, {ITEM_GUN_UP}(4)
    cmpwi 4, 0
    beq pt_switch_item
    li 10, {ITEM_GUN_UP}
pt_switch_item:
    # early in a pause, with the gun out: the page shows the gun chosen, not the weapon under it
    cmpwi 3, {MODE_PAUSE}
    bne pt_switch_frames
    lwz 4, 0x1a00(31)
    cmpwi 4, {MODE_PAUSE}
    beq pt_switch_paused
    li 4, 0
    stw 4, 0x1a04(31)
pt_switch_paused:
    lwz 4, 0x1a04(31)
    cmpwi 4, {PAUSE_FRAMES}
    bge pt_switch_frames
    addi 4, 4, 1
    stw 4, 0x1a04(31)
    cmpwi 8, 0
    beq pt_switch_frames
    cmpw 9, 7
    bne pt_switch_frames
    mr 9, 10
    lis 4, {SELECTION_HA}
    stw 9, {SELECTION_LO}(4)
pt_switch_frames:
    stw 3, 0x1a00(31)
    lis 4, {WANTED_ITEM_HA}
    lwz 5, {WANTED_ITEM_LO}(4)       # r5 the request
    lwz 6, 0x1a18(31)                # r6 a request dealt with already
    lwz 11, 0x1a0c(31)               # r11 the weapon that stands for the gun as the last weapon, or 0
    cmpwi 5, 0
    bne pt_switch_asked
    li 6, 0
    b pt_switch_held
pt_switch_asked:
    cmpwi 5, {ITEM_GUN}
    beq pt_switch_gun
    cmpwi 5, {ITEM_GUN_UP}
    bne pt_switch_other
pt_switch_gun:                       # the page chose the gun: it comes out over what he holds, nothing is switched
    li 8, 1
    li 5, 0
    stw 5, {WANTED_ITEM_LO}(4)
    li 6, 0
    # the HUD's weapon panel is decided as the menu closes: by then the weapon under the gun has to
    # show no ammunition again (pt_model does the same, too late for this)
    lwz 9, 0x4e8(31)
    cmpwi 9, 0
    bne pt_switch_held
    lwz 9, 0x40c(31)
    cmpwi 9, 0
    bne pt_switch_held
    cmpwi 7, 0
    beq pt_switch_held
    mulli 9, 7, {ITEM_ROW_SIZE}
    lis 10, {ITEM_ROW_HA}
    addi 10, 10, {ITEM_ROW_LO}
    add 9, 9, 10
    lhz 10, {ROW_AMMO_PACK}(9)
    stw 10, 0x4ec(31)
    li 10, 0
    sth 10, {ROW_AMMO_PACK}(9)
    stw 9, 0x4e8(31)
    b pt_switch_held
pt_switch_other:
    cmpw 5, 6
    beq pt_switch_held
    cmpwi 3, {MODE_PAUSE}
    bne pt_switch_play
    # paused: the page asks for its choice as it closes (it asks for the weapon in hand on opening)
    cmpw 5, 9
    bne pt_switch_held
    mr 6, 5                          # dealt with: it stays there until the game goes on
    li 8, 0
    cmpw 5, 7
    beq pt_switch_held
    li 11, 0                         # another weapon chosen: Triangle twice is the game's own again
    b pt_switch_held
pt_switch_play:
    mr 6, 5
    cmpwi 8, 0
    beq pt_switch_forget
    li 8, 0                          # a request for another weapon puts the gun away
    b pt_switch_held
pt_switch_forget:
    lwz 12, 0x1a10(31)
    cmpw 5, 12
    beq pt_switch_held
    li 11, 0                         # a switch to anything else: the gun is no longer the last weapon
pt_switch_held:
    # Triangle twice switches with no request in WANTED: the weapon in hand tells
    lwz 4, 0x1a1c(31)                # r4 in hand last time
    stw 7, 0x1a1c(31)
    lwz 12, 0x1a14(31)               # r12 the weapon under the gun
    cmpwi 7, 0
    beq pt_switch_edge
    cmpwi 8, 0
    beq pt_switch_back
    cmpwi 12, 0
    bne pt_switch_under
    mr 12, 7
    b pt_switch_edge
pt_switch_under:
    cmpw 7, 12
    beq pt_switch_edge
    li 8, 0                          # another weapon came under the gun: it was switched to
    b pt_switch_edge
pt_switch_back:
    cmpw 7, 4
    beq pt_switch_edge
    cmpwi 11, 0
    beq pt_switch_edge
    cmpw 7, 11
    bne pt_switch_edge
    li 8, 1                          # switched to the weapon that stands for the gun: the gun
    mr 12, 7
    li 11, 0
pt_switch_edge:
    stw 6, 0x1a18(31)
    stw 8, 0x404(31)
    lwz 4, 0x1a08(31)
    stw 8, 0x1a08(31)
    cmpwi 8, 0
    bne pt_switch_keep
    cmpwi 4, 0
    beq pt_switch_none
    # just put away for another weapon: the game's last weapon is now the one that was under the gun,
    # which stands for the gun until something else is chosen
    mr 4, 5                          # what it was put away for: the request, or what he holds already
    cmpwi 4, 0
    bne pt_switch_target
    mr 4, 7
pt_switch_target:
    li 11, 0
    cmpwi 4, 0
    beq pt_switch_none
    cmpw 4, 12
    beq pt_switch_none
    mr 11, 12
    stw 4, 0x1a10(31)
pt_switch_none:
    li 12, 0
pt_switch_keep:
    stw 12, 0x1a14(31)
    stw 11, 0x1a0c(31)
    blr

# The weapon pages' still pictures come from two files, read one after the other into memory the game
# then shows (widget r31: +0x30 the set of pictures; r30 the picture): for the Zapper's, ours in their place.
pt_read_game:
    b {READ_FILE}

pt_read_header:
    lwz 6, 0x30(31)
    cmpwi 6, {PICTURES_WEAPONS}
    beq pt_read_header_set
    cmpwi 6, {PICTURES_HELP}
    bne pt_read_game
pt_read_header_set:
    cmpwi 30, {PICTURE_ZAPPER}
    beq pt_read_header_ours
    cmpwi 30, {PICTURE_SHOCKER}
    bne pt_read_game
pt_read_header_ours:
    lis 5, {POOL_HA}
    addi 5, 5, {POOL_LO}
    addi 5, 5, {P_picture_entry}
    addi 5, 5, -4
    addi 4, 4, -4
    li 6, 9
    mtctr 6
pt_read_header_copy:
    lwzu 6, 4(5)
    stwu 6, 4(4)
    bdnz pt_read_header_copy
    li 3, 1
    blr

pt_read_pixels:
    lwz 6, 0x30(31)
    cmpwi 6, {PICTURES_WEAPONS}
    beq pt_read_pixels_set
    cmpwi 6, {PICTURES_HELP}
    bne pt_read_game
pt_read_pixels_set:
    cmpwi 30, {PICTURE_ZAPPER}
    beq pt_read_pixels_ours
    cmpwi 30, {PICTURE_SHOCKER}
    bne pt_read_game
pt_read_pixels_ours:
    # The page shows a 512 x 512 texture and ours is half that: each DXT1 block (two colours, then two
    # bits a pixel, little-endian) becomes four, with the same colours and each pixel doubled.
    clrldi 3, 4, 32
    lis 4, {PICTURE_DATA_HA}
    addi 4, 4, {PICTURE_DATA_LO}
    li 6, 0
pt_picture_row:
    li 7, 0
pt_picture_block:
    slwi 12, 6, 6
    add 12, 12, 7
    slwi 12, 12, 3
    add 12, 12, 4
    lwz 11, 0(12)
    addi 12, 12, 4
    lwbrx 10, 0, 12
    li 8, 0
pt_picture_half_y:
    li 9, 0
pt_picture_half_x:
    slwi 5, 8, 4
    srw 0, 10, 5
    slwi 5, 9, 2
    srw 0, 0, 5
    andi. 5, 0, 3
    mulli 5, 5, 5
    rlwinm 12, 0, 30, 30, 31
    mulli 12, 12, 0x50
    or 5, 5, 12
    mulli 5, 5, 0x101
    rlwinm 12, 0, 24, 30, 31
    mulli 12, 12, 5
    rlwinm 0, 0, 22, 30, 31
    mulli 0, 0, 0x50
    or 12, 12, 0
    mulli 12, 12, 0x101
    slwi 12, 12, 16
    or 5, 5, 12
    slwi 12, 6, 1
    add 12, 12, 8
    slwi 12, 12, 7
    slwi 0, 7, 1
    add 0, 0, 9
    add 12, 12, 0
    slwi 12, 12, 3
    add 12, 12, 3
    stw 11, 0(12)
    addi 12, 12, 4
    stwbrx 5, 0, 12
    addi 9, 9, 1
    cmpwi 9, 2
    blt pt_picture_half_x
    addi 8, 8, 1
    cmpwi 8, 2
    blt pt_picture_half_y
    addi 7, 7, 1
    cmpwi 7, {PICTURE_BLOCKS}
    blt pt_picture_block
    addi 6, 6, 1
    cmpwi 6, {PICTURE_BLOCKS}
    blt pt_picture_row
    li 3, 1
    blr

# the gun in his hand, or his own model back
pt_model:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 3, 0x404(31)
    cmpwi 3, 0
    beq pt_model_off
    lwz 3, 0x40c(31)
    cmpwi 3, 0
    beq pt_model_on
pt_model_off:
    lwz 4, 0x4e8(31)
    cmpwi 4, 0
    beq pt_model_row_back
    lwz 5, 0x4ec(31)
    sth 5, {ROW_AMMO_PACK}(4)
    li 5, 0
    stw 5, 0x4e8(31)
pt_model_row_back:
    lwz 3, 0x4f0(31)
    cmpwi 3, 0
    beq pt_model_done
    lis 5, {HAND_HA}
    lwz 5, {HAND_LO}(5)
    cmpw 5, 3
    bne pt_model_forget              # not in his hand any more: that memory may be something else now
    lwz 4, 0x4f4(31)
    stw 4, 0x24(3)
    lwz 4, 0x4f8(31)
    stw 4, 0x2c(3)
pt_model_forget:
    li 3, 0
    stw 3, 0x4f0(31)
    b pt_model_done
pt_model_on:
    lis 3, {HAND_HA}
    lwz 3, {HAND_LO}(3)
    cmpwi 3, 0
    beq pt_model_done
    lwz 4, 0x24(3)
    addi 5, 31, 0x500
    cmpw 4, 5
    beq pt_model_held
    cmpwi 4, 0
    beq pt_model_done
    stw 3, 0x4f0(31)
    stw 4, 0x4f4(31)
    lwz 6, 0x2c(3)
    stw 6, 0x4f8(31)
    addi 3, 31, 0x500
    li 5, 0x200
    bl {MEMCPY}
    addi 3, 31, 0x700
    stw 3, 0x500(31)
    lis 3, {GUN_SCALE_HI}
    ori 3, 3, {GUN_SCALE_LO}
    stw 3, 0x524(31)
    lwz 3, 0x4f0(31)
    addi 4, 31, 0x500
    stw 4, 0x24(3)
pt_model_held:                       # the moby has the scale as well, as each weapon set it
    lis 4, {GUN_SCALE_HI}
    ori 4, 4, {GUN_SCALE_LO}
    stw 4, 0x2c(3)
    # the weapon he is not holding shows nothing in the HUD: its row says it has no ammunition until he does
    lwz 4, 0x4e8(31)
    cmpwi 4, 0
    bne pt_model_done
    lis 4, {HAND_ITEM_HA}
    lwz 4, {HAND_ITEM_LO}(4)
    mulli 4, 4, {ITEM_ROW_SIZE}
    lis 5, {ITEM_ROW_HA}
    addi 5, 5, {ITEM_ROW_LO}
    add 4, 4, 5
    lhz 5, {ROW_AMMO_PACK}(4)
    stw 5, 0x4ec(31)
    li 5, 0
    sth 5, {ROW_AMMO_PACK}(4)
    stw 4, 0x4e8(31)
pt_model_done:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

# During a transit the view does not look the way the game's camera does. The right stick brings the
# game's camera round, with the game's own turning, as its angle is kept nowhere it could be set;
# the left stick is turned by the rest, so forward stays forward on the screen. (r30 the pad's data)
pt_pad_transit:
    lwz 3, 0xa80(31)
    stw 3, 8(30)
    lwz 3, 0xa84(31)
    stw 3, 12(30)
    lwz 3, 0xa88(31)
    stw 3, 16(30)
    lhz 3, 16(30)                    # left x
    lhz 4, 18(30)                    # left y, which is down
    addi 3, 3, -128
    addi 4, 4, -128
    subfic 4, 4, 0
    extsw 3, 3
    extsw 4, 4
    std 3, -0x10(1)
    lfd 1, -0x10(1)
    fcfid 1, 1
    std 4, -0x10(1)
    lfd 2, -0x10(1)
    fcfid 2, 2
    lfs 3, 0xa98(31)                 # cosine and sine of the angle from the game's camera to the view
    lfs 4, 0xa9c(31)
    fmuls 5, 1, 3
    fnmsubs 5, 2, 4, 5               # x cos - y sin
    fmuls 6, 1, 4
    fmadds 6, 2, 3, 6                # x sin + y cos
    fctiwz 5, 5
    stfd 5, -0x10(1)
    lwz 3, -0xc(1)
    fctiwz 6, 6
    stfd 6, -0x10(1)
    lwz 4, -0xc(1)
    addi 3, 3, 128
    subfic 4, 4, 128
""" + "".join(f"""
    cmpwi {r}, 0
    bge pt_pad_low{r}
    li {r}, 0
pt_pad_low{r}:
    cmpwi {r}, 255
    ble pt_pad_high{r}
    li {r}, 255
pt_pad_high{r}:
""" for r in (3, 4)) + """
    sth 3, 16(30)
    sth 4, 18(30)
    # the right stick: towards the view, until it is reached
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 1, 0xa9c(31)
    lfs 2, 0xa98(31)
    lfs 5, {P_zero}(3)
    fcmpu 0, 2, 5
    ble pt_pad_turn
    fmuls 6, 1, 1
    lfs 7, {P_cam_aligned}(3)
    fcmpu 0, 6, 7
    ble pt_pad_turned
pt_pad_turn:
    li 4, 255
    fcmpu 0, 1, 5
    bge pt_pad_right
    li 4, 0
pt_pad_right:
    sth 4, 12(30)
pt_pad_turned:
    li 3, 24
    stw 3, 0(30)
    blr

# the pad read: (r3 port, r4 data) as cellPadGetData; keeps the buttons and hides the gun's two
pt_pad:
    mflr 0
    std 0, 0x10(1)
    std 2, 0x28(1)
    stdu 1, -0x80(1)
    std 31, 0x70(1)
    std 30, 0x68(1)
    mr 31, 3
    mr 30, 4
    bl {PAD_GET}
    ld 2, 0x28(1)
    std 3, 0x60(1)
    cmpwi 31, 0
    bne pt_pad_done
    lis 31, {STATE_HA}
    addi 31, 31, {STATE_LO}
    bl pt_switch
    # a pad of the tools' own (tools/press.py), inside the game: nothing else on the machine sees it
    lwz 3, 0x418(31)
    lwz 4, 0x41c(31)
    or. 5, 3, 4
    beq pt_pad_real
    srwi 5, 3, 16
    sth 5, 8(30)
    sth 3, 10(30)
    srwi 5, 4, 24
    sth 5, 12(30)
    rlwinm 5, 4, 16, 24, 31
    sth 5, 14(30)
    rlwinm 5, 4, 24, 24, 31
    sth 5, 16(30)
    clrlwi 5, 4, 24
    sth 5, 18(30)
    li 5, 24
    stw 5, 0(30)
pt_pad_real:
    lwz 3, 0(30)
    cmpwi 3, 0
    beq pt_pad_kept
    lwz 3, 8(30)                     # the pad as it last was: buttons, then the four stick values
    stw 3, 0xa80(31)
    lwz 3, 12(30)
    stw 3, 0xa84(31)
    lwz 3, 16(30)
    stw 3, 0xa88(31)
pt_pad_kept:
    lwz 3, 0xa00(31)
    cmpwi 3, 0
    beq pt_pad_plain
    bl pt_pad_transit
pt_pad_plain:
    lwz 3, 0(30)
    cmpwi 3, 0
    beq pt_pad_done
    lhz 3, 8(30)
    lhz 4, 10(30)
    slwi 3, 3, 8
    or 3, 3, 4
    stw 3, 0x400(31)
    lwz 3, 0x404(31)
    cmpwi 3, 0
    beq pt_pad_done
    lwz 3, 0x40c(31)
    cmpwi 3, 0
    bne pt_pad_done
    lis 3, {GAME_MODE_HA}
    lwz 3, {GAME_MODE_LO}(3)
    cmpwi 3, 0
    bne pt_pad_done
    andi. 4, 4, 0xff5f
    sth 4, 10(30)
    li 4, 0
    sth 4, 30(30)
    sth 4, 34(30)
pt_pad_done:
    ld 3, 0x60(1)
    ld 30, 0x68(1)
    ld 31, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

# (r3 portal) a shot along the camera's view axis
pt_shoot:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    std 25, 0x60(1)
    mr 25, 3
    li 3, 0
    stw 3, 0(25)
    lis 3, {CAMERA_POS_HA}
    addi 3, 3, {CAMERA_POS_LO}
    lis 4, {CAMERA_MATRIX_HA}
    addi 4, 4, {CAMERA_MATRIX_LO}
    lfs 3, {RAY_START}(31)
    lwz 5, 0x400(31)                 # aiming with L1 there is no Ratchet in the way to start past
    andi. 5, 5, {L1}
    beq pt_ray_past_him
    lis 5, {POOL_HA}
    addi 5, 5, {POOL_LO}
    lfs 3, {P_ray_aiming}(5)
pt_ray_past_him:
""" + add_scaled(3, 0, 3, 4, 0, 31, 0x170) + """
    # A ray ending outside the level finds nothing, not even the floor under him: straight down from
    # z 100 it would end at -50. It stops at the level's edge.
    lfs 3, {RAY_LENGTH}(31)
    lis 5, {POOL_HA}
    addi 5, 5, {POOL_LO}
    lfs 6, {P_ray_edge}(5)
""" + "".join(f"""
    lfs 1, {i}(3)
    fcmpu 0, 1, 6
    blt pt_ray_inside{i}
    lfs 2, {i}(4)
    fmadds 5, 2, 3, 1
    fcmpu 0, 5, 6
    bge pt_ray_inside{i}
    fsubs 1, 6, 1
    fdivs 3, 1, 2
pt_ray_inside{i}:
""" for i in (0, 4, 8)) + add_scaled(3, 0, 3, 4, 0, 31, 0x1d0) + """
    addi 3, 31, 0x170
    addi 4, 31, 0x1d0
    li 5, 2
    li 6, 0
    li 7, 0
    bl {RAY}
    nop
    cmpwi 3, 0
    beq pt_shoot_sky
    addi 3, 31, 0x800
    lis 4, {RAY_RESULT_HA}
    addi 4, 4, {RAY_RESULT_LO}
    li 5, 0x60
    bl {MEMCPY}
pt_shoot_place:
    addi 4, 31, 0x800
    lwz 5, {NORMAL_AT}(31)
    add 5, 4, 5
    # the normal, of length one and towards the shooter
    lfs 1, 0(5)
    lfs 2, 4(5)
    lfs 3, 8(5)
    fmuls 4, 1, 1
    fmadds 4, 2, 2, 4
    fmadds 4, 3, 3, 4
    fsqrts 4, 4
    fdivs 1, 1, 4
    fdivs 2, 2, 4
    fdivs 3, 3, 4
    lis 6, {CAMERA_MATRIX_HA}
    addi 6, 6, {CAMERA_MATRIX_LO}
    lfs 5, 0(6)
    fmuls 5, 5, 1
    lfs 6, 4(6)
    fmadds 5, 6, 2, 5
    lfs 6, 8(6)
    fmadds 5, 6, 3, 5
    fsubs 6, 6, 6
    fcmpu 0, 5, 6
    blt pt_normal_faces
    fneg 1, 1
    fneg 2, 2
    fneg 3, 3
pt_normal_faces:
    stfs 1, 0x20(25)
    stfs 2, 0x24(25)
    stfs 3, 0x28(25)
    # the portal's up: world up on a wall, the view on a floor or ceiling
    fabs 4, 3
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 5, {P_steep}(3)
    fcmpu 0, 4, 5
    addi 4, 3, {P_world_up}
    blt pt_have_reference
    mr 4, 6
pt_have_reference:
""" + dot(4, 25, 0x20, 4, 0, 5) + """
    fneg 4, 4
""" + add_scaled(4, 0, 4, 25, 0x20, 25, 0x40) + """
    lfs 1, 0x40(25)
    lfs 2, 0x44(25)
    lfs 3, 0x48(25)
    fmuls 4, 1, 1
    fmadds 4, 2, 2, 4
    fmadds 4, 3, 3, 4
    fsqrts 4, 4
    fdivs 1, 1, 4
    fdivs 2, 2, 4
    fdivs 3, 3, 4
    stfs 1, 0x40(25)
    stfs 2, 0x44(25)
    stfs 3, 0x48(25)
    # right = up x normal
    lfs 4, 0x20(25)
    lfs 5, 0x24(25)
    lfs 6, 0x28(25)
    fmuls 7, 2, 6
    fnmsubs 7, 3, 5, 7
    stfs 7, 0x30(25)
    fmuls 7, 3, 4
    fnmsubs 7, 1, 6, 7
    stfs 7, 0x34(25)
    fmuls 7, 1, 5
    fnmsubs 7, 2, 4, 7
    stfs 7, 0x38(25)
    # the position, a little off the wall
    addi 4, 31, 0x800
    lfs 3, {LIFT}(31)
""" + add_scaled(4, 0x20, 3, 25, 0x20, 25, 0x10) + """
    li 3, 1
    stw 3, 0(25)
    b pt_shoot_done
    # Nothing hit: the sky, and in some levels the moon. A portal there is a portal far out on the
    # line to it, facing back, so that the other one looks down on the level from out there.
pt_shoot_sky:
    lis 5, {LEVEL_HA}
    lwz 5, {LEVEL_LO}(5)
    cmplwi 5, {MOON_LEVELS}
    bge pt_shoot_done
    slwi 5, 5, 4
    add 5, 5, 31
    addi 5, 5, 0x1500
    lfs 4, 12(5)
    fsubs 6, 6, 6
    fcmpu 0, 4, 6
    ble pt_shoot_done
    lis 6, {CAMERA_MATRIX_HA}
    addi 6, 6, {CAMERA_MATRIX_LO}
    lfs 1, 8(6)
    lfs 2, 0(5)
    fcmpu 0, 1, 2
    blt pt_shoot_done
    lfs 2, 4(5)
    fcmpu 0, 1, 2
    bgt pt_shoot_done
    lfs 3, {MOON_FAR}(31)
    lis 7, {CAMERA_POS_HA}
    addi 7, 7, {CAMERA_POS_LO}
""" + "".join(f"""
    lfs 1, {i}(7)
    lfs 2, {i}(6)
    fmadds 1, 2, 3, 1
    stfs 1, {0x820 + i}(31)
    fneg 2, 2
    stfs 2, {0x840 + i}(31)
""" for i in (0, 4, 8)) + """
    li 3, 1
    stw 3, 0x130c(31)
    b pt_shoot_place
pt_shoot_done:
    ld 25, 0x60(1)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

# (r3 the portal) the shot leaves his hand: where it will end is known now, the portal comes when it gets there
pt_fire:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 24, 0x60(1)
    std 25, 0x68(1)
    std 23, 0x70(1)
    mr 25, 3
    addi 24, 31, {SHOT_SLOT}
    addi 23, 31, {SHOT_PENDING}
    addi 3, 31, 0x200
    cmpw 3, 25
    beq pt_fire_slot
    addi 24, 24, {SHOT_SLOT_SIZE}
    addi 23, 23, {SHOT_PENDING_SIZE}
pt_fire_slot:
    mr 3, 23
    bl pt_shoot
    stw 25, 4(24)
    lwz 3, 0x130c(31)
    stw 3, 8(24)
    li 3, 0
    stw 3, 0x130c(31)
    lwz 3, 0(23)
    cmpwi 3, 0
    beq pt_fire_nowhere
""" + "".join(f"""
    lwz 3, {0x10 + i}(23)
    stw 3, {0x20 + i}(24)
""" for i in (0, 4, 8)) + """
    b pt_fire_from
pt_fire_nowhere:                     # the sky: it just goes on until it is gone
    lis 3, {CAMERA_POS_HA}
    addi 3, 3, {CAMERA_POS_LO}
    lis 4, {CAMERA_MATRIX_HA}
    addi 4, 4, {CAMERA_MATRIX_LO}
    lfs 3, {RAY_LENGTH}(31)
""" + add_scaled(3, 0, 3, 4, 0, 24, 0x20) + """
pt_fire_from:
    lis 3, {HAND_HA}
    lwz 3, {HAND_LO}(3)
    cmpwi 3, 0
    bne pt_fire_hand
    lis 3, {HERO_MOBY_HA}
    lwz 3, {HERO_MOBY_LO}(3)
pt_fire_hand:
""" + "".join(f"""
    lfs 1, {0x10 + i}(3)
    stfs 1, {0x10 + i}(24)
    lfs 2, {0x20 + i}(24)
    fsubs 2, 2, 1
    stfs 2, {0x20 + i}(24)
""" for i in (0, 4, 8)) + dot(3, 24, 0x20, 24, 0x20, 4) + """
    fsqrts 3, 3
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 4, {P_shot_speed}(3)
    fdivs 4, 3, 4
    fctiwz 4, 4
    stfd 4, -0x10(1)
    lwz 3, -0xc(1)
    addi 3, 3, 1
    cmpwi 3, {SHOT_MOST}
    ble pt_fire_frames
    li 3, {SHOT_MOST}
pt_fire_frames:
    stw 3, 0(24)
    extsw 3, 3
    std 3, -0x10(1)
    lfd 4, -0x10(1)
    fcfid 4, 4
    frsp 4, 4
""" + "".join(f"""
    lfs 1, {0x20 + i}(24)
    fdivs 1, 1, 4
    stfs 1, {0x20 + i}(24)
""" for i in (0, 4, 8)) + """
    ld 23, 0x70(1)
    ld 24, 0x60(1)
    ld 25, 0x68(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

# the shots in the air, and a portal for each that got there
pt_shots_step:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 23, 0x60(1)
    std 24, 0x68(1)
    std 25, 0x70(1)
    addi 24, 31, {SHOT_SLOT}
    addi 23, 31, {SHOT_PENDING}
    bl pt_shot_step
    addi 24, 24, {SHOT_SLOT_SIZE}
    addi 23, 23, {SHOT_PENDING_SIZE}
    bl pt_shot_step
    ld 23, 0x60(1)
    ld 24, 0x68(1)
    ld 25, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

pt_shot_step:
    lwz 3, 0(24)
    cmpwi 3, 0
    beqlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    addi 3, 3, -1
    stw 3, 0(24)
""" + add_scaled(24, 0x10, 0, 24, 0x20, 24, 0x10).replace("fmadds 1, 2, 0, 1", "fadds 1, 1, 2") + """
    cmpwi 3, 0
    bne pt_shot_stepped
    lwz 3, 0(23)
    cmpwi 3, 0
    beq pt_shot_stepped
    lwz 25, 4(24)
    mr 3, 25
    mr 4, 23
    li 5, 0x50
    bl {MEMCPY}
    li 3, 0                          # the way of a transit went through the portal that moved
    stw 3, 0xa00(31)
    lwz 3, 8(24)
    cmpwi 3, 0
    beq pt_shot_wall
    li 3, 0
    stw 3, 0x1308(31)
    stw 3, 0x1340(31)
    stw 25, 0x1304(31)
    b pt_shot_stepped
pt_shot_wall:
    lwz 3, 0x1304(31)                # the portal on the moon was shot somewhere else: that is the end
    cmpw 3, 25
    bne pt_shot_stepped
    li 3, 0
    stw 3, 0x1304(31)
    stw 3, 0x1308(31)
pt_shot_stepped:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

# (r3 vector, r4 result, r5 portal in, r6 portal out) a vector through the pair; keeps f1-f3 free
pt_map:
    lfs 1, 0(3)
    lfs 2, 4(3)
    lfs 3, 8(3)
    lfs 4, 0x30(5)
    fmuls 4, 4, 1
    lfs 5, 0x34(5)
    fmadds 4, 5, 2, 4
    lfs 5, 0x38(5)
    fmadds 4, 5, 3, 4
    lfs 6, 0x40(5)
    fmuls 6, 6, 1
    lfs 5, 0x44(5)
    fmadds 6, 5, 2, 6
    lfs 5, 0x48(5)
    fmadds 6, 5, 3, 6
    lfs 7, 0x20(5)
    fmuls 7, 7, 1
    lfs 5, 0x24(5)
    fmadds 7, 5, 2, 7
    lfs 5, 0x28(5)
    fmadds 7, 5, 3, 7
    stfs 7, 0x1dc(31)
    lfs 8, 0x30(6)
    fneg 8, 8
    fmuls 8, 8, 4
    lfs 9, 0x40(6)
    fmadds 8, 9, 6, 8
    lfs 9, 0x20(6)
    fnmsubs 8, 9, 7, 8
    stfs 8, 0(4)
    lfs 8, 0x34(6)
    fneg 8, 8
    fmuls 8, 8, 4
    lfs 9, 0x44(6)
    fmadds 8, 9, 6, 8
    lfs 9, 0x24(6)
    fnmsubs 8, 9, 7, 8
    stfs 8, 4(4)
    lfs 8, 0x38(6)
    fneg 8, 8
    fmuls 8, 8, 4
    lfs 9, 0x48(6)
    fmadds 8, 9, 6, 8
    lfs 9, 0x28(6)
    fnmsubs 8, 9, 7, 8
    stfs 8, 8(4)
    li 3, 0
    stw 3, 0xc(4)
    blr

# (r30 portal looked through, r29 the other) the hidden camera
pt_hidden_camera:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lis 3, {CAMERA_POS_HA}
    addi 3, 3, {CAMERA_POS_LO}
""" + sub(3, 0, 30, 0x10, 31, 0x170) + """
    addi 3, 31, 0x170
    addi 4, 31, 0x170
    mr 5, 30
    mr 6, 29
    bl pt_map
    lfs 3, 0x1dc(31)
    fabs 3, 3
    stfs 3, 0xdc(31)
    li 3, 1
    lis 4, 0
""" + add_scaled(29, 0x10, 10, 31, 0x170, 31, 0x10).replace("fmadds 1, 2, 10, 1", "fadds 1, 1, 2") + """
    li 3, 0
    stw 3, 0x1c(31)
    lis 3, {CAMERA_MATRIX_HA}
    addi 3, 3, {CAMERA_MATRIX_LO}
    addi 4, 31, 0x20
    mr 5, 30
    mr 6, 29
    bl pt_map
    lis 3, {CAMERA_MATRIX_HA}
    addi 3, 3, {CAMERA_MATRIX_LO}
    addi 3, 3, 0x10
    addi 4, 31, 0x30
    mr 5, 30
    mr 6, 29
    bl pt_map
    lis 3, {CAMERA_MATRIX_HA}
    addi 3, 3, {CAMERA_MATRIX_LO}
    addi 3, 3, 0x20
    addi 4, 31, 0x40
    mr 5, 30
    mr 6, 29
    bl pt_map
    li 3, 0
    stw 3, 0x50(31)
    stw 3, 0x54(31)
    stw 3, 0x58(31)
    stw 3, 0x5c(31)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

pt_swap_in:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    addi 3, 31, 0x60
    lis 4, {CAMERA_POS_HA}
    addi 4, 4, {CAMERA_POS_LO}
    li 5, 0x10
    bl {MEMCPY}
    addi 3, 31, 0x70
    lis 4, {CAMERA_MATRIX_HA}
    addi 4, 4, {CAMERA_MATRIX_LO}
    li 5, 0x40
    bl {MEMCPY}
    lis 3, {CAMERA_POS_HA}
    addi 3, 3, {CAMERA_POS_LO}
    addi 4, 31, 0x10
    li 5, 0x10
    bl {MEMCPY}
    lis 3, {CAMERA_MATRIX_HA}
    addi 3, 3, {CAMERA_MATRIX_LO}
    addi 4, 31, 0x20
    li 5, 0x40
    bl {MEMCPY}
    bl {BUILD_VIEW}
    # The hidden camera stands behind the exit's wall, and what is there has to go, at any angle:
    # the depth column of the renderer's view * projection becomes the exit's plane, so that plane
    # is the near plane (Lengyel's oblique near plane). z' = scale * distance from the plane - w.
    lis 3, {RENDERER_HA}
    lwz 3, {RENDERER_LO}(3)
    addi 3, 3, {VIEW_PROJECTION}
    lfs 5, 0x20(29)
    lfs 6, 0x24(29)
    lfs 7, 0x28(29)
    lfs 1, 0x10(29)
    fmuls 8, 1, 5
    lfs 1, 0x14(29)
    fmadds 8, 1, 6, 8
    lfs 1, 0x18(29)
    fmadds 8, 1, 7, 8
    fneg 8, 8
    # the same plane for the culling: what is behind the exit costs nothing. Mobys test only the
    # planes before it, so nothing of his can be lost here.
    lis 4, {FRUSTUM_NEAR_HA}
    addi 4, 4, {FRUSTUM_NEAR_LO}
    stfs 5, 0(4)
    stfs 6, 4(4)
    stfs 7, 8(4)
    stfs 8, 12(4)
    lfs 9, {CLIP_SCALE}(31)
""" + "".join(f"""
    lfs 1, {row * 0x10 + 0xC}(3)
    fmsubs 2, {5 + row}, 9, 1
    stfs 2, {row * 0x10 + 8}(3)
""" for row in range(4)) + """
    # BUILD_VIEW has sent the plain matrix to every pass already, as constant 0, and what does not
    # send it again (the mobys) draws with that: the new one goes after it
    lis 3, {RENDERER_HA}
    lwz 3, {RENDERER_LO}(3)
    addi 3, 3, {VIEW_PROJECTION}
    lis 8, {PASS_BUFFERS_HA}
    addi 8, 8, {PASS_BUFFERS_LO}
    li 9, {PASSES}
    mtctr 9
    lis 10, 0x44
    ori 10, 10, 0x1efc
pt_view_pass:
    lwz 4, 0(8)
    lwz 5, 8(4)
    stw 10, 0(5)
    li 6, 0
    stw 6, 4(5)
""" + "".join(f"""
    lwz 6, {row * 0x10 + column * 4}(3)
    stw 6, {8 + (column * 4 + row) * 4}(5)
""" for column in range(4) for row in range(4)) + """
    addi 5, 5, 72
    stw 5, 8(4)
    addi 8, 8, 4
    bdnz pt_view_pass
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

pt_swap_out:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lis 3, {CAMERA_POS_HA}
    addi 3, 3, {CAMERA_POS_LO}
    addi 4, 31, 0x60
    li 5, 0x10
    bl {MEMCPY}
    lis 3, {CAMERA_MATRIX_HA}
    addi 3, 3, {CAMERA_MATRIX_LO}
    addi 4, 31, 0x70
    li 5, 0x40
    bl {MEMCPY}
    bl {BUILD_VIEW}
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

# Ratchet through a portal, and his flight behind it
pt_travel:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lis 28, {HERO_POS_HA}
    addi 28, 28, {HERO_POS_LO}
""" + sub(28, 0, 31, 0x160, 31, 0x1e0) + """
    # the flight: the game keeps gravity and landing, this adds the motion he came in with
    lwz 3, 0xc(31)
    cmpwi 3, 0
    beq pt_no_fling
    addi 3, 3, -1
    stw 3, 0xc(31)
    # Up and down: the game keeps its own fall speed, which tops out at about the speed he went in
    # with, so a carried rise and the game's fall cancelled and he hung in the air for the whole
    # flight (and rose while gliding). While a carried rise lasts, the game's fall is held at 0 and
    # gravity takes the rise away instead (faster in the Heli-Pack's glide); a carried fall is the game's.
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 1, 0x1c8(31)
    lfs 3, {P_zero}(3)
    lis 4, {HERO_VEL_Z_HA}
    fcmpu 0, 1, 3
    bgt pt_fling_rising
    beq pt_fling_level
    stfs 1, {HERO_VEL_Z_LO}(4)
    stfs 3, 0x1c8(31)
    b pt_fling_level
pt_fling_rising:
    stfs 3, {HERO_VEL_Z_LO}(4)
    lfs 2, {P_hero_gravity}(3)
    lis 5, {HERO_STATE_HA}
    lwz 5, {HERO_STATE_LO}(5)
    cmpwi 5, {GLIDE_STATE}
    bne pt_fling_brake
    lfs 2, {P_glide_brake}(3)
pt_fling_brake:
    fsubs 1, 1, 2
    fcmpu 0, 1, 3
    bge pt_fling_rise_set
    fmr 1, 3
pt_fling_rise_set:
    stfs 1, 0x1c8(31)
pt_fling_level:
    # a wall ahead ends the sideways part
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 3, {P_chest}(3)
    lfs 1, 0(28)
    stfs 1, 0x170(31)
    lfs 1, 4(28)
    stfs 1, 0x174(31)
    lfs 1, 8(28)
    fadds 1, 1, 3
    stfs 1, 0x178(31)
    stfs 1, 0x1d8(31)
    lfs 3, {WALL_LOOK}(31)
    lfs 1, 0x170(31)
    lfs 2, 0x1c0(31)
    fmadds 1, 2, 3, 1
    stfs 1, 0x1d0(31)
    lfs 1, 0x174(31)
    lfs 2, 0x1c4(31)
    fmadds 1, 2, 3, 1
    stfs 1, 0x1d4(31)
    addi 3, 31, 0x170
    addi 4, 31, 0x1d0
    li 5, 2
    li 6, 0
    li 7, 0
    bl {RAY}
    nop
    cmpwi 3, 0
    beq pt_clear
    li 3, 0
    stw 3, 0x1c0(31)
    stw 3, 0x1c4(31)
pt_clear:
    # the ground ends the flight, once he is away from the portal
    lwz 3, 8(31)
    cmpwi 3, {COOLDOWN_LATE}
    bgt pt_fly
    lis 3, {HERO_GROUND_HA}
    lfs 2, {HERO_GROUND_LO}(3)
    lfs 1, 8(28)
    lfs 3, 0x1c8(31)
    fadds 1, 1, 3
    fsubs 1, 1, 2
    lfs 2, {GROUND_GAP}(31)
    fcmpu 0, 1, 2
    bge pt_fly
    li 3, 0
    stw 3, 0xc(31)
    b pt_no_fling
pt_fly:

    lfs 1, 0(28)
    lfs 2, 448(31)
    fadds 1, 1, 2
    stfs 1, 0(28)

    lfs 1, 4(28)
    lfs 2, 452(31)
    fadds 1, 1, 2
    stfs 1, 4(28)

    lfs 1, 8(28)
    lfs 2, 456(31)
    fadds 1, 1, 2
    stfs 1, 8(28)

pt_no_fling:
    lwz 3, 8(31)
    cmpwi 3, 0
    beq pt_check
    addi 3, 3, -1
    stw 3, 8(31)
    b pt_travel_done
pt_check:
    lwz 3, 0x1304(31)
    cmpwi 3, 0
    bne pt_travel_done
    lwz 3, 0x200(31)
    lwz 4, 0x280(31)
    and. 3, 3, 4
    beq pt_travel_done
    addi 29, 31, 0x200
    addi 30, 31, 0x280
    bl pt_through
    cmpwi 3, 0
    bne pt_travel_done
    addi 29, 31, 0x280
    addi 30, 31, 0x200
    bl pt_through
pt_travel_done:
""" + "".join(f"""
    lwz 3, {i}(28)
    stw 3, {0x160 + i}(31)
""" for i in (0, 4, 8)) + """
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

# (r29 portal in, r30 portal out, r28 his position) -> r3 = 1 when he went through
pt_through:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
""" + sub(28, 0, 29, 0x10, 31, 0x170) + """
    lfs 1, 0x178(31)
    lfs 2, {CENTRE_Z}(31)
    fadds 1, 1, 2
    stfs 1, 0x178(31)
""" + dot(3, 31, 0x170, 29, 0x20, 4) + """
    lfs 4, {TRIGGER}(31)
    lwz 3, 0xe6c(31)                 # between walls he goes when his middle reaches the plane
    cmpwi 3, 0
    beq pt_trigger_set
    fsubs 4, 4, 4
    cmpwi 3, 2
    blt pt_trigger_set
    lis 3, {POOL_HA}                 # a floor takes him as soon as he sinks in: walking over it he
    addi 3, 3, {POOL_LO}             # would be across before his middle got to the plane
    lfs 5, 0x28(29)
    lfs 6, {P_steep}(3)
    fcmpu 0, 5, 6
    ble pt_trigger_set
    lfs 4, {FLOOR_CROSS}(31)
pt_trigger_set:
    fcmpu 0, 3, 4
    bge pt_outside
    lfs 4, {BEHIND}(31)
    lwz 3, 0xe6c(31)                 # falling he can be well past the plane in one frame
    cmpwi 3, 2
    blt pt_behind_set
    lfs 4, {STACK_BEHIND}(31)
pt_behind_set:
    fneg 4, 4
    fcmpu 0, 3, 4
    blt pt_outside
""" + dot(3, 31, 0x170, 29, 0x30, 4) + """
    lfs 4, {RADIUS_X}(31)
    fdivs 3, 3, 4
    fmuls 3, 3, 3
""" + dot(5, 31, 0x170, 29, 0x40, 6) + """
    lfs 4, {RADIUS_Y}(31)
    fdivs 5, 5, 4
    fmadds 3, 5, 5, 3
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 4, {P_one}(3)
    fcmpu 0, 3, 4
    bge pt_outside
    lwz 3, 0xe6c(31)
    cmpwi 3, 1
    beq pt_going_in
    cmpwi 3, 2
    beq pt_going_in
    # moving into it, or standing on a floor portal: there is no floor under him there
""" + dot(3, 31, 0x1e0, 29, 0x20, 4) + """
    fsubs 4, 4, 4
    fcmpu 0, 3, 4
    blt pt_going_in
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 1, 0x28(29)
    lfs 2, {P_steep}(3)
    fcmpu 0, 1, 2
    ble pt_outside
    lfs 3, {P_fall_start}(3)         # he comes out of it falling, not standing
""" + add_scaled(31, 0x1e0, 3, 29, 0x20, 31, 0x1e0) + """
pt_going_in:
    # on the ground between two walls he walks on by himself and may stop or turn back; in the air
    # he has only the flight
    li 3, 0
    stw 3, 0xe78(31)
    lwz 3, 0xe6c(31)
    cmpwi 3, 0
    beq pt_walk_set
    cmpwi 3, 3
    beq pt_walk_set
    cmpwi 3, 2
    bne pt_walk_ground
    stw 3, 0xe78(31)                 # floor and ceiling: the game's own fall simply goes on
    b pt_walk_set
pt_walk_ground:
    lfs 1, 8(28)
    lis 3, {HERO_GROUND_HA}
    lfs 2, {HERO_GROUND_LO}(3)
    fsubs 1, 1, 2
    lfs 2, {CROSS_GROUND}(31)
    fcmpu 0, 1, 2
    bge pt_walk_set
    li 3, 1
    stw 3, 0xe78(31)
pt_walk_set:
""" + dot(3, 31, 0x170, 29, 0x20, 4) + """
    fsubs 4, 4, 4
    fcmpu 0, 3, 4
    ble pt_on_plane
    fneg 3, 3                        # taken early from a floor: he goes on from the plane
""" + add_scaled(31, 0x170, 3, 29, 0x20, 31, 0x170) + """
pt_on_plane:

    # through: position and motion turned by the pair
    addi 3, 31, 0x170
    addi 4, 31, 0x170
    mr 5, 29
    mr 6, 30
    bl pt_map
    addi 3, 31, 0x1e0
    addi 4, 31, 0x1c0
    mr 5, 29
    mr 6, 30
    bl pt_map
    lfs 3, {PUSH}(31)
    lwz 3, 0xe6c(31)
    cmpwi 3, 0
    beq pt_push_set
    cmpwi 3, 3
    beq pt_push_set
    lfs 3, {CROSS_GAP}(31)
pt_push_set:
""" + add_scaled(31, 0x170, 3, 30, 0x20, 31, 0x170) + """
    lfs 3, {CENTRE_Z}(31)
    fneg 3, 3
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    addi 3, 3, {P_world_up}
""" + add_scaled(31, 0x170, 3, 3, 0, 31, 0x170) + "".join(f"""
    lfs 1, {0x10 + i}(30)
    lfs 2, {0x170 + i}(31)
    fadds 1, 1, 2
    stfs 1, {i}(28)
""" for i in (0, 4, 8)) + """
    bl pt_cam_start
    lwz 3, 0xe78(31)
    cmpwi 3, 0
    bne pt_walked_through
    li 3, {COOLDOWN}
    stw 3, 8(31)
    li 3, {FLING_FRAMES}
    stw 3, 0xc(31)
    li 3, 1
    b pt_through_done
pt_walked_through:
    li 3, 0
    stw 3, 8(31)
    stw 3, 0xc(31)
""" + "".join(f"""
    lis 3, {{HERO_HA}}
    addi 3, 3, {{HERO_LO}}
    addi 3, 3, {at}
    mr 4, 3
    mr 5, 29
    mr 6, 30
    bl pt_map
""" for at in (HERO_VELOCITY, HERO_MOVED)) + """
    lwz 3, 0xe78(31)
    cmpwi 3, 2
    beq pt_walked_clear
    # an exit lower on its wall must not leave his feet under the floor there
    lwz 3, 0(28)
    stw 3, 0x170(31)
    stw 3, 0x1d0(31)
    lwz 3, 4(28)
    stw 3, 0x174(31)
    stw 3, 0x1d4(31)
    lfs 1, 8(28)
    stfs 1, 0x1d8(31)
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 2, {P_chest}(3)
    fadds 1, 1, 2
    stfs 1, 0x178(31)
    addi 3, 31, 0x170
    addi 4, 31, 0x1d0
    li 5, 2
    li 6, 0
    li 7, 0
    bl {RAY}
    nop
    cmpwi 3, 0
    beq pt_walked_clear
    lis 3, {RAY_RESULT_HA}
    addi 3, 3, {RAY_RESULT_LO}
    lwz 3, 0x28(3)
    stw 3, 8(28)
pt_walked_clear:
    li 3, 1
    b pt_through_done
pt_outside:
    li 3, 0
pt_through_done:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

# (r3 world position, r4 result u, v) where a point of the world is on the screen, as texture place
pt_screen:
    lis 5, {CAMERA_POS_HA}
    addi 5, 5, {CAMERA_POS_LO}
    lfs 1, 0(3)
    lfs 2, 0(5)
    fsubs 1, 1, 2
    lfs 2, 4(3)
    lfs 3, 4(5)
    fsubs 2, 2, 3
    lfs 3, 8(3)
    lfs 4, 8(5)
    fsubs 3, 3, 4
    lis 5, {CAMERA_MATRIX_HA}
    addi 5, 5, {CAMERA_MATRIX_LO}
    lfs 4, 0(5)
    fmuls 4, 4, 1
    lfs 5, 4(5)
    fmadds 4, 5, 2, 4
    lfs 5, 8(5)
    fmadds 4, 5, 3, 4
    lfs 6, 0x10(5)
    fmuls 6, 6, 1
    lfs 5, 0x14(5)
    fmadds 6, 5, 2, 6
    lfs 5, 0x18(5)
    fmadds 6, 5, 3, 6
    lfs 7, 0x20(5)
    fmuls 7, 7, 1
    lfs 5, 0x24(5)
    fmadds 7, 5, 2, 7
    lfs 5, 0x28(5)
    fmadds 7, 5, 3, 7
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 5, {P_near_least}(3)
    fcmpu 0, 4, 5
    bge pt_in_front
    fmr 4, 5
pt_in_front:
    lfs 8, {P_half}(3)
    lis 5, {TAN_X_HA}
    lfs 5, {TAN_X_LO}(5)
    fmuls 5, 5, 4
    fdivs 6, 6, 5
    lis 5, {TAN_Y_HA}
    lfs 5, {TAN_Y_LO}(5)
    fmuls 5, 5, 4
    fdivs 7, 7, 5
    lfs 1, {SCALE_U}(31)
    lfs 2, {SCALE_V}(31)
    fnmsubs 6, 6, 8, 8
    fnmsubs 7, 7, 8, 8
    fmuls 6, 6, 1
    fmuls 7, 7, 2
    stfs 6, 0(4)
    stfs 7, 4(4)
    blr

# one point of the rim into the quad: r3 where in the quad (vertex number), f10/f11 cos, sin
pt_rim_point:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    std 24, 0x60(1)
    mr 24, 3
    lfs 1, {RADIUS_X}(31)
    lfs 2, {RADIUS_Y}(31)
    fmuls 1, 1, 12
    fmuls 2, 2, 12
    fmuls 8, 1, 10
    fmuls 9, 2, 11
    slwi 3, 24, 4
    add 3, 3, 31
    addi 3, 3, 0x300
""" + "".join(f"""
    lfs 1, {0x10 + i}(30)
    lfs 2, {0x30 + i}(30)
    fmadds 1, 2, 8, 1
    lfs 2, {0x40 + i}(30)
    fmadds 1, 2, 9, 1
    stfs 1, {i}(3)
""" for i in (0, 4, 8)) + """
    slwi 4, 24, 3
    add 4, 4, 31
    addi 4, 4, 0x350
    bl pt_screen
    ld 24, 0x60(1)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

# both portals
pt_draw:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    std 24, 0x60(1)
    lwz 3, 0x200(31)
    cmpwi 3, 0
    beq pt_draw_orange
    addi 30, 31, 0x200
    addi 29, 31, 0x100
    lwz 28, 0x3a0(31)
    bl pt_portal
pt_draw_orange:
    lwz 3, 0x280(31)
    cmpwi 3, 0
    beq pt_draw_done
    addi 30, 31, 0x280
    addi 29, 31, 0x130
    lwz 28, 0x3a4(31)
    bl pt_portal
pt_draw_done:
    addi 24, 31, {SHOT_SLOT}
    lwz 28, 0x3a0(31)
    bl pt_shot_draw
    addi 24, 24, {SHOT_SLOT_SIZE}
    lwz 28, 0x3a4(31)
    bl pt_shot_draw
    ld 24, 0x60(1)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

# (r24 the shot, r28 its colour) a round blob facing the camera with a white middle, and two behind it.
# pt_fan draws a portal's disc, so this is a little portal block.
pt_shot_draw:
    lwz 3, 0(24)
    cmpwi 3, 0
    beqlr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    addi 30, 31, {SHOT_BLOB}
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 1, {P_one}(3)
    stfs 1, 0x1f4(31)
    lfs 1, {P_zero}(3)
    stfs 1, 0x1f8(31)
    li 27, 0
pt_shot_blobs:
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    addi 3, 3, {P_shot_blobs}
    slwi 4, 27, 3
    add 3, 3, 4
    lfs 8, 0(3)
    lfs 9, 4(3)
    stfs 9, 0x1fc(31)
""" + add_scaled(24, 0x10, 8, 24, 0x20, 30, 0x10) + """
    lfs 9, 0x1fc(31)
    lis 3, {CAMERA_MATRIX_HA}
    addi 3, 3, {CAMERA_MATRIX_LO}
    lis 4, {POOL_HA}
    addi 4, 4, {POOL_LO}
    lfs 8, {P_shot_tall}(4)
    fmuls 8, 8, 9
""" + "".join(f"""
    lfs 1, {0x10 + i}(3)
    fmuls 1, 1, 9
    stfs 1, {0x30 + i}(30)
    lfs 1, {0x20 + i}(3)
    fmuls 1, 1, 8
    stfs 1, {0x40 + i}(30)
""" for i in (0, 4, 8)) + """
    addi 3, 31, 0x440
    mr 4, 28
    cmpwi 27, {SHOT_MIDDLE}
    bne pt_shot_colour
    lwz 4, 0x3a8(31)                 # the middle is white
pt_shot_colour:
    bl pt_fan
    addi 27, 27, 1
    cmpwi 27, {SHOT_BLOBS}
    blt pt_shot_blobs
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

# (r30 portal, r29 its view, r28 its colour) the inside, then the rim
pt_portal:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lwz 3, 0x200(31)
    lwz 4, 0x280(31)
    and. 3, 3, 4
    beq pt_solid
    lwz 3, {SEE_THROUGH}(31)
    cmpwi 3, 0
    bne pt_solid
    lwz 4, 0x3a8(31)
    mr 3, 29
    b pt_inside
pt_solid:
    mr 4, 28
    addi 3, 31, 0x440
pt_inside:
    # In rings and not one fan from the middle: seen close and from the side a point of the rim is
    # beside the camera, its place on the screen is far off, and the whole wedge would smear with it.
    std 3, 0x60(1)
    std 4, 0x68(1)
""" + "".join(f"""
    lis 3, {{POOL_HA}}
    addi 3, 3, {{POOL_LO}}
    lfs 1, {{P_rings}} + {4 * n}(3)
    stfs 1, 0x1f4(31)
    lfs 1, {{P_rings}} + {4 * (n + 1)}(3)
    stfs 1, 0x1f8(31)
    ld 3, 0x60(1)
    ld 4, 0x68(1)
    bl pt_fan
""" for n in range(len(RINGS) - 1)) + """
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 1, {P_outer}(3)
    stfs 1, 0x1f4(31)
    lfs 1, {P_inner}(3)
    stfs 1, 0x1f8(31)
    mr 4, 28
    addi 3, 31, 0x440
    bl pt_fan
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

# QUAD takes its corners as a triangle strip: outer, inner, outer, inner.
# (r3 texture, r4 colour, +0x1f4 outer and +0x1f8 inner radius as parts of the portal's)
pt_fan:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    std 27, 0x60(1)
    std 26, 0x58(1)
    stw 3, 0x378(31)
    stw 4, 0x340(31)
    stw 4, 0x344(31)
    stw 4, 0x348(31)
    stw 4, 0x34c(31)
    li 3, 0
    li 4, 0
    li 5, 1
    li 6, 1
    li 7, 1
    li 8, 0
    li 9, 0
    ori 9, 9, 0xff90
    bl {TEXTURE_STATE}
    nop
    std 3, 0x380(31)
    li 3, 1
    li 4, 1
    li 5, 0
    li 6, 0
    li 7, 0
    li 8, 0
    bl {DEPTH_STATE}
    nop
    std 3, 0x370(31)
    li 3, 0
    li 4, 1
    li 5, 0
    li 6, 1
    li 7, 0x80
    bl {BLEND_STATE}
    nop
    std 3, 0x388(31)
    lis 26, {POOL_HA}
    addi 26, 26, {POOL_LO}
    addi 26, 26, {P_ring}
    li 27, {SEGMENTS_RING}
pt_fan_next:
    lfs 12, 0x1f4(31)
    lfs 10, 0(26)
    lfs 11, 4(26)
    li 3, 0
    bl pt_rim_point
    lfs 12, 0x1f8(31)
    lfs 10, 0(26)
    lfs 11, 4(26)
    li 3, 1
    bl pt_rim_point
    lfs 12, 0x1f4(31)
    lfs 10, 8(26)
    lfs 11, 12(26)
    li 3, 2
    bl pt_rim_point
    lfs 12, 0x1f8(31)
    lfs 10, 8(26)
    lfs 11, 12(26)
    li 3, 3
    bl pt_rim_point
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 1, {P_one}(3)
    stfs 1, 0x30c(31)
    stfs 1, 0x31c(31)
    stfs 1, 0x32c(31)
    stfs 1, 0x33c(31)
    addi 3, 31, 0x300
    li 4, 0
    li 5, 0
    bl {QUAD}
    nop
    addi 26, 26, 8
    addi 27, 27, -1
    cmpwi 27, 0
    bgt pt_fan_next
    ld 26, 0x58(1)
    ld 27, 0x60(1)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr
"""


# Everything else that goes through: enemies and shots, whichever weapon or owner they have.
CODE += """
# Each moby's last position is kept behind the gun's mesh, as a shot lives too shortly to wait for.
pt_mobys:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xa0(1)
    std 23, 0x60(1)
    std 24, 0x68(1)
    std 25, 0x70(1)
    std 26, 0x78(1)
    std 27, 0x80(1)
    std 28, 0x88(1)
    std 29, 0x90(1)
    std 30, 0x98(1)
    lis 3, {MOBY_TABLE_HA}
    lwz 30, {MOBY_TABLE_LO}(3)
    lis 3, {MOBY_TABLE_END_HA}
    lwz 29, {MOBY_TABLE_END_LO}(3)
    lwz 28, 0x410(31)
    addis 28, 28, {MOBY_TRACK_HIGH}
    lwz 27, 0(31)
pt_moby_loop:                       # the first slot is Ratchet, and he has his own way through
    addi 30, 30, 0x100
    addi 28, 28, {MOBY_TRACK_SIZE}
    cmplw 30, 29
    bge pt_mobys_done
    lbz 3, 0x20(30)
    cmplwi 3, {MOBY_DYING}
    bge pt_moby_loop
    # empty slots hold anything, so nothing is followed before it is seen to be a pointer
    lwz 3, 0x64(30)
    lis 4, {OPD_FIRST_HA}
    addi 4, 4, {OPD_FIRST_LO}
    cmplw 3, 4
    blt pt_moby_loop
    lis 4, {OPD_LAST_HA}
    addi 4, 4, {OPD_LAST_LO}
    cmplw 3, 4
    bge pt_moby_loop
    lwz 4, 0x24(30)
    cmpwi 4, 0
    bne pt_moby_model
    lhz 3, 0xaa(30)
    cmpwi 3, {PULSE_CLASS}
    bne pt_moby_loop
    b pt_moby_class
pt_moby_model:
    lis 5, {MAIN_HEAP_HA}
    lwz 6, {MAIN_HEAP_LO}(5)
    cmplw 4, 6
    blt pt_moby_loop
    lwz 6, {MAIN_HEAP_END_LO}(5)
    addi 6, 6, -0x50
    cmplw 4, 6
    bge pt_moby_loop
    lha 26, 0x46(4)                  # only these: a bolt has an owner too, and dies of being moved
    cmpwi 26, {KIND_ENEMY}
    beq pt_moby_take
    cmpwi 26, {KIND_SHOT}
    beq pt_moby_take
    lhz 3, 0xaa(30)                  # and the shots with no kind in their model, by class
""" + "".join(f"""
    cmpwi 3, {c}
    beq pt_moby_class
""" for c in SHOT_CLASSES) + """
    b pt_moby_loop
pt_moby_class:
    li 26, {KIND_SHOT}
pt_moby_take:
    lwz 3, 0xc(28)
    stw 27, 0xc(28)
    addi 3, 3, 1
    cmpw 3, 27
    bne pt_moby_keep                 # not seen last frame: no motion to go by
    lwz 3, 0x10(28)
    cmpw 3, 27
    bgt pt_moby_keep
""" + sub(30, 0x10, 28, 0, 31, 0x910) + """
    addi 25, 31, 0x200
    addi 24, 31, 0x280
    bl pt_moby_portal
    cmpwi 3, 0
    bne pt_moby_keep
    addi 25, 31, 0x280
    addi 24, 31, 0x200
    bl pt_moby_portal
pt_moby_keep:
    lwz 3, 0x10(30)
    stw 3, 0(28)
    lwz 3, 0x14(30)
    stw 3, 4(28)
    lwz 3, 0x18(30)
    stw 3, 8(28)
    b pt_moby_loop
pt_mobys_done:
    ld 23, 0x60(1)
    ld 24, 0x68(1)
    ld 25, 0x70(1)
    ld 26, 0x78(1)
    ld 27, 0x80(1)
    ld 28, 0x88(1)
    ld 29, 0x90(1)
    ld 30, 0x98(1)
    addi 1, 1, 0xa0
    ld 0, 0x10(1)
    mtlr 0
    blr

# (r30 moby, +0x910 its motion, r25 this portal, r24 the other) -> r3 = 1 when it went through.
# A shot tests the wall on the frame it meets it, so it has to go a frame before.
pt_moby_portal:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    std 21, 0x60(1)
""" + sub(30, 0x10, 25, 0x10, 31, 0x900) + dot(10, 31, 0x900, 25, 0x20, 4) + dot(11, 31, 0x910, 25, 0x20, 4) + """
    li 21, 0
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 9, {P_zero}(3)
    fmr 12, 9                        # how far along its step it meets the portal
    cmpwi 26, {KIND_ENEMY}
    bne pt_moby_moving
    lfs 1, 0x28(25)
    lfs 2, {P_steep}(3)
    fcmpu 0, 1, 2
    ble pt_moby_moving
    lfs 1, {P_mob_floor}(3)          # an enemy walks over a floor portal without moving into it
    fcmpu 0, 10, 1
    bgt pt_moby_no
    li 21, 1                         # and falls in
    b pt_moby_inside
pt_moby_moving:
    fcmpu 0, 11, 9
    bge pt_moby_no
    lfs 1, {P_mob_behind}(3)
    fcmpu 0, 10, 1
    blt pt_moby_no
    lfs 1, {P_mob_reach}(3)
    lhz 4, 0xaa(30)                  # these look well ahead and blow up before they get to a wall
    cmpwi 4, {MISSILE_CLASS}
    beq pt_moby_far
    cmpwi 4, {RYNO_CLASS}
    beq pt_moby_far
    cmpwi 4, {HOVERBOMB_CLASS}
    bne pt_moby_near
pt_moby_far:
    lfs 1, {P_mob_reach_far}(3)
pt_moby_near:
    fsubs 1, 1, 11
    fcmpu 0, 10, 1
    bgt pt_moby_no
    fneg 1, 11
    fdivs 12, 10, 1
    fcmpu 0, 12, 9
    bge pt_moby_ahead
    fmr 12, 9
pt_moby_ahead:
    lhz 4, 0xaa(30)                  # and go from the plane, however many steps away it is
    cmpwi 4, {MISSILE_CLASS}
    beq pt_moby_inside
    cmpwi 4, {RYNO_CLASS}
    beq pt_moby_inside
    cmpwi 4, {HOVERBOMB_CLASS}
    beq pt_moby_inside
    lfs 1, {P_one}(3)
    fcmpu 0, 12, 1
    ble pt_moby_inside
    fmr 12, 1
pt_moby_inside:
""" + add_scaled(31, 0x900, 12, 31, 0x910, 31, 0x920) + dot(10, 31, 0x920, 25, 0x30, 4) + dot(11, 31, 0x920, 25, 0x40, 4) + """
    lfs 1, {RADIUS_X}(31)
    lfs 2, {RADIUS_Y}(31)
    fdivs 10, 10, 1
    fdivs 11, 11, 2
    fmuls 10, 10, 10
    fmadds 10, 11, 11, 10
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 1, {P_one}(3)
    fcmpu 0, 10, 1
    bgt pt_moby_no
    cmpwi 21, 0
    beq pt_moby_jump
    bl pt_carry_add
    addi 3, 27, {CARRY_COOLDOWN}
    stw 3, 0x10(28)
    li 3, 1
    b pt_moby_done
pt_moby_jump:
    lwz 3, 0x18f0(31)                # for the tests: how many went through, and the last one's class
    addi 3, 3, 1
    stw 3, 0x18f0(31)
    lhz 3, 0xaa(30)
    stw 3, 0x18f4(31)

    addi 3, 31, 0x920
    addi 4, 31, 0x940
    mr 5, 25
    mr 6, 24
    bl pt_map
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 11, {P_mob_out}(3)
    lfs 12, {P_near_scale}(3)
    lfs 1, 0x1dc(31)
    fadds 11, 11, 1
""" + "".join(f"""
    lfs 1, {0x10 + i}(24)
    lfs 2, {0x940 + i}(31)
    fadds 1, 1, 2
    lfs 2, {0x20 + i}(24)
    fmadds 1, 2, 11, 1
    stfs 1, {0x10 + i}(30)
    fmuls 1, 1, 12
    stfs 1, {i}(30)
""" for i in (0, 4, 8)) + """
    cmpwi 26, {KIND_ENEMY}
    beq pt_moby_turned
""" + "".join(f"""
    addi 3, 30, {row}
    addi 4, 31, 0x950
    mr 5, 25
    mr 6, 24
    bl pt_map
""" + "".join(f"""
    lwz 3, {0x950 + i}(31)
    stw 3, {row + i}(30)
""" for i in (0, 4, 8)) for row in (0xc0, 0xd0, 0xe0)) + """
pt_moby_turned:
    bl pt_moby_vars
    addi 3, 27, {MOBY_COOLDOWN}
    stw 3, 0x10(28)
    li 3, 1
    b pt_moby_done
pt_moby_no:
    li 3, 0
pt_moby_done:
    ld 21, 0x60(1)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

# Where a moby keeps its heading depends on its class, so any copy of its motion is turned.
pt_moby_vars:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 22, 0x60(1)
    std 23, 0x68(1)
    lwz 23, 0x68(30)
    lis 5, {MAIN_HEAP_HA}
    lwz 6, {MAIN_HEAP_LO}(5)
    cmplw 23, 6
    blt pt_vars_done
    lwz 6, {MAIN_HEAP_END_LO}(5)
    addi 6, 6, -{MOBY_VARS}
    cmplw 23, 6
    bge pt_vars_done
    cmpwi 26, {KIND_ENEMY}
    beq pt_vars_scan
    # a Lancer shot homing on something would turn back through the wall to reach it. Only its
    # target goes: what other classes keep in their variables is not known, and a bolt's target
    # is read with no test for 0.
    lwz 3, 0x64(30)
    lis 4, {LANCER_SHOT_HA}
    addi 4, 4, {LANCER_SHOT_LO}
    cmplw 3, 4
    bne pt_vars_not_lancer
    li 3, 0
    stw 3, {LANCER_TARGET}(23)
    b pt_vars_scan
pt_vars_not_lancer:
    # a missile flies along a unit vector, which no test of its motion can tell
    lhz 3, 0xaa(30)
    cmpwi 3, {MISSILE_CLASS}
    beq pt_vars_missile
    cmpwi 3, {RYNO_CLASS}
    bne pt_vars_scan
pt_vars_missile:
    addi 3, 23, {MISSILE_HEADING}
    addi 4, 31, 0x950
    mr 5, 25
    mr 6, 24
    bl pt_map
""" + "".join(f"""
    lwz 4, {0x950 + i}(31)
    stw 4, {MISSILE_HEADING + i}(23)
""" for i in (0, 4, 8)) + """
    b pt_vars_done
pt_vars_scan:
    li 22, 0
pt_vars_next:
    cmpwi 22, {MOBY_VARS_LAST}
    bgt pt_vars_done
    # Only a real copy of its motion counts, as that is all that can be told about these words:
    # floats all three, at most one of them 0, and equal to the motion per frame or per second.
    # (A shot's speed, then 0, then a handle looks like a vector along x and is none.)
    add 3, 23, 22
    li 7, 0
""" + "".join(f"""
    lwz 4, {i}(3)
    rlwinm. 5, 4, 0, 1, 31
    bne pt_vars_word{i}
    addi 7, 7, 1
    b pt_vars_ok{i}
pt_vars_word{i}:
    rlwinm 5, 4, 9, 24, 31
    cmpwi 5, 0
    beq pt_vars_on
    cmpwi 5, 0xff
    beq pt_vars_on
pt_vars_ok{i}:
""" for i in (0, 4, 8)) + """
    cmpwi 7, 1
    bgt pt_vars_on
    lfs 1, 0(3)
    lfs 2, 4(3)
    lfs 3, 8(3)
    lfs 4, 0x910(31)
    lfs 5, 0x914(31)
    lfs 6, 0x918(31)
    lis 4, {POOL_HA}
    addi 4, 4, {POOL_LO}
    lfs 10, {P_vec_near}(4)
    fmuls 9, 4, 4
    fmadds 9, 5, 5, 9
    fmadds 9, 6, 6, 9
    fmuls 9, 9, 10                   # the error allowed, squared
    fsubs 7, 1, 4
    fsubs 8, 2, 5
    fsubs 10, 3, 6
    fmuls 7, 7, 7
    fmadds 7, 8, 8, 7
    fmadds 7, 10, 10, 7
    fcmpu 0, 7, 9
    blt pt_vars_hit                  # a NaN passes neither of these
    lfs 10, {P_per_second}(4)
    fmuls 4, 4, 10
    fmuls 5, 5, 10
    fmuls 6, 6, 10
    fmuls 9, 9, 10
    fmuls 9, 9, 10
    fsubs 7, 1, 4
    fsubs 8, 2, 5
    fsubs 10, 3, 6
    fmuls 7, 7, 7
    fmadds 7, 8, 8, 7
    fmadds 7, 10, 10, 7
    fcmpu 0, 7, 9
    blt pt_vars_hit
pt_vars_on:
    addi 22, 22, 4
    b pt_vars_next
pt_vars_hit:
    add 3, 23, 22
    addi 4, 31, 0x950
    mr 5, 25
    mr 6, 24
    bl pt_map
    add 3, 23, 22
    lwz 4, 0x950(31)
    stw 4, 0(3)
    lwz 4, 0x954(31)
    stw 4, 4(3)
    lwz 4, 0x958(31)
    stw 4, 8(3)
    addi 22, 22, 12
    b pt_vars_next
pt_vars_done:
    ld 22, 0x60(1)
    ld 23, 0x68(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr
"""


def vec_lerp(a_reg, a_at, b_reg, b_at, out_at):
    """+out = a + f1 * (b - a), three floats"""
    return "".join(f"""
    lfs 2, {a_at + i}({a_reg})
    lfs 3, {b_at + i}({b_reg})
    fsubs 3, 3, 2
    fmadds 2, 3, 13, 2
    stfs 2, {out_at + i}(31)
""" for i in (0, 4, 8))


def normalise(at):
    return dot(1, 31, at, 31, at, 2) + f"""
    fsqrts 1, 1
""" + "".join(f"""
    lfs 2, {at + i}(31)
    fdivs 2, 2, 1
    stfs 2, {at + i}(31)
""" for i in (0, 4, 8))


# A transit of Ratchet's. The camera behind him is carried along his way as one path: it stays where
# it was relative to him, and eases into what the game's own camera is doing by then. While that
# path is still behind the exit portal, the view comes from the same place on the entry side, so the
# camera is in the first room looking at him through the portal, and crosses later with no jump.
# State block: +0xa00 frames left, +0xa04 the exit, +0xa08 the entry, +0xa0c the real camera is kept,
# +0xa10 the camera from Ratchet, +0xa20 its matrix, +0xa60 the real position, +0xa80 the pad as it
# last was, +0xa98 / +0xa9c cosine and sine from the game's camera to the view, +0xaa0 the place
# shown, +0xab0 its matrix, +0xaf0 how far it has eased, +0xd00 the real matrix.
CODE += """
pt_cam_start:                       # (r28 his position, r29 entry, r30 exit), he has moved already
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    lis 3, {CAMERA_POS_HA}
    addi 3, 3, {CAMERA_POS_LO}
    lwz 4, 0xa00(31)
    cmpwi 4, 0
    beq pt_cam_from_game
    addi 3, 31, 0xf00                # back through during a transit: on from what is on the screen
pt_cam_from_game:
""" + sub(3, 0, 29, 0x10, 31, 0x170) + """
    addi 3, 31, 0x170
    addi 4, 31, 0x170
    mr 5, 29
    mr 6, 30
    bl pt_map
""" + "".join(f"""
    lfs 1, {0x170 + i}(31)
    lfs 2, {0x10 + i}(30)
    fadds 1, 1, 2
    lfs 2, {i}(28)
    fsubs 1, 1, 2
    stfs 1, {0xa10 + i}(31)
""" for i in (0, 4, 8)) + "".join(f"""
    bl pt_cam_rows
    addi 3, 3, {row}
    addi 4, 31, {0xa20 + row}
    mr 5, 29
    mr 6, 30
    bl pt_map
""" for row in (0, 0x10, 0x20)) + """
    # his body: the heading he had, turned by the pair
    lis 3, {HERO_MOBY_HA}
    lwz 3, {HERO_MOBY_LO}(3)
    addi 3, 3, 0xc0
    addi 4, 31, 0x170
    mr 5, 29
    mr 6, 30
    bl pt_map
    lfs 1, 0x174(31)
    lfs 2, 0x170(31)
    bl pt_atan2
    lis 3, {HERO_HA}
    addi 3, 3, {HERO_LO}
    stfs 1, {HERO_YAW}(3)
    stfs 1, {HERO_YAW_WANTED}(3)
    stfs 1, {HERO_HEADING}(3)
    stw 29, 0xa08(31)
    stw 30, 0xa04(31)
    li 3, {CAM_FRAMES}
    stw 3, 0xa00(31)
    li 3, 0
    stw 3, 0xf40(31)
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 1, {P_zero}(3)
    stfs 1, 0xaf0(31)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

pt_cam_rows:
    lis 3, {CAMERA_MATRIX_HA}
    addi 3, 3, {CAMERA_MATRIX_LO}
    lwz 4, 0xa00(31)
    cmpwi 4, 0
    beqlr
    addi 3, 31, 0xf10
    blr

# (f1 y, f2 x) -> f1 the angle, good to a thousandth of a radian or so
pt_atan2:
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    fabs 3, 1
    fabs 4, 2
    fcmpu 0, 3, 4
    ble pt_atan_low
    fdivs 5, 4, 3
    li 4, 1
    b pt_atan_ratio
pt_atan_low:
    lfs 6, {P_zero}(3)
    fcmpu 0, 4, 6
    beq pt_atan_flat
    fdivs 5, 3, 4
    li 4, 0
pt_atan_ratio:
    lfs 6, {P_at_b}(3)
    fmuls 6, 6, 5
    lfs 7, {P_at_a}(3)
    fadds 6, 6, 7
    lfs 7, {P_one}(3)
    fsubs 7, 7, 5
    fmuls 6, 6, 7
    lfs 7, {P_quarter_pi}(3)
    fadds 6, 6, 7
    fmuls 5, 5, 6
    cmpwi 4, 0
    beq pt_atan_near
    lfs 6, {P_half_pi}(3)
    fsubs 5, 6, 5
pt_atan_near:
    lfs 6, {P_zero}(3)
    fcmpu 0, 2, 6
    bge pt_atan_right
    lfs 7, {P_pi}(3)
    fsubs 5, 7, 5
pt_atan_right:
    fcmpu 0, 1, 6
    bge pt_atan_up
    fneg 5, 5
pt_atan_up:
    fmr 1, 5
    blr
pt_atan_flat:
    lfs 1, {P_zero}(3)
    blr

pt_cam_apply:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    li 3, 0
    stw 3, 0xe68(31)
    lwz 3, 0xa00(31)
    cmpwi 3, 0
    beq pt_cam_applied
    addi 3, 3, -1
    stw 3, 0xa00(31)
    lis 4, {POOL_HA}
    addi 4, 4, {POOL_LO}
    lfs 13, 0xaf0(31)
    # the smooth step of how far it has eased
    lfs 1, {P_three}(4)
    fadds 2, 13, 13
    fsubs 2, 1, 2
    fmuls 1, 13, 13
    fmuls 13, 1, 2
    # the real camera is kept, and goes back after the frame is drawn
    lis 5, {CAMERA_POS_HA}
    addi 5, 5, {CAMERA_POS_LO}
    lis 6, {CAMERA_MATRIX_HA}
    addi 6, 6, {CAMERA_MATRIX_LO}
""" + "".join(f"""
    lwz 3, {i}(5)
    stw 3, {0xa60 + i}(31)
""" for i in (0, 4, 8, 0xc)) + "".join(f"""
    lwz 3, {i}(6)
    stw 3, {0xd00 + i}(31)
""" for i in range(0, 0x40, 4)) + """
    li 3, 1
    stw 3, 0xa0c(31)
    lis 4, {HERO_POS_HA}
    addi 4, 4, {HERO_POS_LO}
""" + "".join(f"""
    lfs 1, {i}(4)
    lfs 2, {0xa10 + i}(31)
    fadds 1, 1, 2
    stfs 1, {0x930 + i}(31)
""" for i in (0, 4, 8)) + vec_lerp(31, 0x930, 5, 0, 0xaa0) + vec_lerp(31, 0xa20, 6, 0, 0xab0) + vec_lerp(31, 0xa30, 6, 0x10, 0xac0) + vec_lerp(31, 0xa40, 6, 0x20, 0xad0) + normalise(0xab0) + dot(3, 31, 0xad0, 31, 0xab0, 4) + "".join(f"""
    lfs 1, {0xad0 + i}(31)
    lfs 2, {0xab0 + i}(31)
    fnmsubs 1, 3, 2, 1
    stfs 1, {0xad0 + i}(31)
""" for i in (0, 4, 8)) + normalise(0xad0) + """
    # left = up x view
    lfs 1, 0xad0(31)
    lfs 2, 0xad4(31)
    lfs 3, 0xad8(31)
    lfs 4, 0xab0(31)
    lfs 5, 0xab4(31)
    lfs 6, 0xab8(31)
    fmuls 7, 2, 6
    fnmsubs 7, 3, 5, 7
    stfs 7, 0xac0(31)
    fmuls 7, 3, 4
    fnmsubs 7, 1, 6, 7
    stfs 7, 0xac4(31)
    fmuls 7, 1, 5
    fnmsubs 7, 2, 4, 7
    stfs 7, 0xac8(31)
""" + "".join(f"""
    lwz 3, {0xaa0 + i}(31)
    stw 3, {0xf00 + i}(31)
""" for i in range(0, 0x40, 4)) + """
    # how far the game's own camera is from the way the view looks, for the pad (pt_pad_transit)
    # (out of a floor portal the view is straight up with no heading: its up is one)
    lfs 1, 0xd00(31)
    lfs 2, 0xd04(31)
    lfs 3, 0xa20(31)
    lfs 4, 0xa40(31)
    fadds 3, 3, 4
    lfs 4, 0xa24(31)
    lfs 5, 0xa44(31)
    fadds 4, 4, 5
    fmuls 5, 3, 3
    fmadds 5, 4, 4, 5
    fsqrts 5, 5
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 6, {P_vec_tiny}(3)
    fadds 5, 5, 6
    lfs 3, 0xa20(31)
    lfs 4, 0xa40(31)
    fadds 3, 3, 4
    lfs 4, 0xa24(31)
    lfs 6, 0xa44(31)
    fadds 4, 4, 6
    fdivs 3, 3, 5
    fdivs 4, 4, 5
    fmuls 6, 1, 1
    fmadds 6, 2, 2, 6
    fsqrts 6, 6
    lis 5, {POOL_HA}
    addi 5, 5, {POOL_LO}
    lfs 5, {P_vec_tiny}(5)
    fadds 6, 6, 5
    fdivs 1, 1, 6
    fdivs 2, 2, 6
    fmuls 5, 1, 3
    fmadds 5, 2, 4, 5
    stfs 5, 0xa98(31)
    fmuls 6, 1, 4
    fnmsubs 6, 2, 3, 6
    stfs 6, 0xa9c(31)
    # behind the exit: the same place on the entry side
    lwz 29, 0xa04(31)
""" + sub(31, 0xaa0, 29, 0x10, 31, 0x170) + dot(3, 31, 0x170, 29, 0x20, 4) + """
    lis 4, {POOL_HA}
    addi 4, 4, {POOL_LO}
    lfs 4, {P_zero}(4)
    fcmpu 0, 3, 4
    bge pt_cam_crossed
    lfs 5, 0xaf0(31)                 # once easing it finishes, wherever the game's camera is
    fcmpu 0, 5, 4
    bgt pt_cam_crossed
    # Right at the entry the near plane cuts the disc away and the wall behind it fills the screen for
    # a frame, so it goes over that last bit at once.
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 5, {P_cam_skip}(3)
    fneg 6, 3
    fcmpu 0, 6, 5
    bge pt_cam_short
""" + add_scaled(31, 0xaa0, 6, 29, 0x20, 31, 0xaa0) + """
    b pt_cam_crossed
pt_cam_short:
    li 3, 1
    stw 3, 0xe68(31)
    # While he stands in this portal it waits, for as long as he does. Otherwise it goes by the way
    # he goes out, and glides on by itself should he stop.
    fmr 11, 4
    lwz 3, 0xe6c(31)                 # only in a wall can he stand still half way
    cmpwi 3, 1
    bne pt_cam_free
    lwz 3, 0xe60(31)
    cmpw 3, 29
    bne pt_cam_free
    lwz 3, 0xf40(31)
    cmpwi 3, 0
    bne pt_cam_free
    lhz 3, 0xa84(31)                 # the right stick moves the camera: it goes on, to the game's,
    addi 3, 3, -128                  # for the rest of this transit
    cmpwi 3, {CAM_STICK}
    bgt pt_cam_released
    cmpwi 3, -{CAM_STICK}
    blt pt_cam_released
    li 3, {CAM_FRAMES}
    stw 3, 0xa00(31)
    b pt_cam_step
pt_cam_released:
    li 3, 1
    stw 3, 0xf40(31)
pt_cam_free:
    lfs 11, {CAM_GLIDE}(31)
pt_cam_step:
""" + dot(5, 31, 0x1e0, 29, 0x20, 6) + """
    fcmpu 0, 5, 4
    bge pt_cam_going
    fmr 5, 4
pt_cam_going:
    fadds 5, 5, 11
    # it has to go through the opening and not the wall around it, looking through it by the time
    # it gets there: this frame's part of what is left of both, as its part of the way there
    fabs 6, 3
    fdivs 5, 5, 6
    lfs 6, {P_one}(4)
    fcmpu 0, 5, 6
    ble pt_cam_part
    fmr 5, 6
pt_cam_part:
""" + "".join(f"""
    lfs 1, {0x170 + i}(31)
    lfs 2, {0x20 + i}(29)
    fnmsubs 1, 3, 2, 1
    lfs 2, {0xa10 + i}(31)
    fnmsubs 2, 1, 5, 2
    stfs 2, {0xa10 + i}(31)
""" for i in (0, 4, 8)) + """
    # upright to the exit: a view along the wall behind it shows nothing, and the portal's up is
    # square to its normal as the world's may not be
""" + "".join(f"""
    lfs 1, {0xa20 + i}(31)
    lfs 2, {0x20 + i}(29)
    fsubs 2, 2, 1
    fmadds 1, 2, 5, 1
    stfs 1, {0xa20 + i}(31)
    lfs 1, {0xa40 + i}(31)
    lfs 2, {0x40 + i}(29)
    fsubs 2, 2, 1
    fmadds 1, 2, 5, 1
    stfs 1, {0xa40 + i}(31)
""" for i in (0, 4, 8)) + """
""" + add_scaled(31, 0xa10, 11, 29, 0x20, 31, 0xa10) + """
    addi 3, 31, 0x170
    addi 4, 31, 0x170
    lwz 5, 0xa04(31)
    lwz 6, 0xa08(31)
    bl pt_map
    lwz 29, 0xa08(31)
""" + "".join(f"""
    lfs 1, {0x170 + i}(31)
    lfs 2, {0x10 + i}(29)
    fadds 1, 1, 2
    stfs 1, {0xaa0 + i}(31)
""" for i in (0, 4, 8)) + "".join(f"""
    addi 3, 31, {row}
    addi 4, 31, {row}
    lwz 5, 0xa04(31)
    lwz 6, 0xa08(31)
    bl pt_map
""" for row in (0xab0, 0xac0, 0xad0)) + """
    b pt_cam_side
pt_cam_crossed:
    # the way through may have pulled it far below him: back over him, or it ends up under the floor
    lfs 1, 0xa18(31)
    lfs 2, {P_cam_height}(4)
    fsubs 2, 2, 1
    lfs 3, {P_cam_rise}(4)
    fmadds 1, 2, 3, 1
    stfs 1, 0xa18(31)
    # on the far side: it eases over to the game's camera. Exactly the same way it may never face:
    # with him close to a wall the game cannot get its camera behind him. Under a quarter turn is
    # enough, and a late transit goes anyway, as it would end in a cut.
    lwz 3, 0xa00(31)
    cmpwi 3, {CAM_LATE}
    blt pt_cam_ease
    lfs 5, 0xa98(31)
    fcmpu 0, 5, 4
    ble pt_cam_side
pt_cam_ease:
    lfs 1, {P_cam_step}(4)
    lfs 2, 0xaf0(31)
    fadds 2, 2, 1
    stfs 2, 0xaf0(31)
    lfs 1, {P_one}(4)
    fcmpu 0, 2, 1
    blt pt_cam_side
    li 3, 0
    stw 3, 0xa00(31)
pt_cam_side:
    lis 5, {CAMERA_POS_HA}
    addi 5, 5, {CAMERA_POS_LO}
    lis 6, {CAMERA_MATRIX_HA}
    addi 6, 6, {CAMERA_MATRIX_LO}
""" + "".join(f"""
    lwz 3, {0xaa0 + i}(31)
    stw 3, {i}(5)
""" for i in (0, 4, 8)) + "".join(f"""
    lwz 3, {0xab0 + i}(31)
    stw 3, {i}(6)
""" for i in range(0, 0x30, 4)) + """
    bl {BUILD_VIEW}
    nop
pt_cam_applied:
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

pt_cam_restore:
    lwz 3, 0xa0c(31)
    cmpwi 3, 0
    beqlr
    li 3, 0
    stw 3, 0xa0c(31)
    lis 5, {CAMERA_POS_HA}
    addi 5, 5, {CAMERA_POS_LO}
    lis 6, {CAMERA_MATRIX_HA}
    addi 6, 6, {CAMERA_MATRIX_LO}
""" + "".join(f"""
    lwz 3, {0xa60 + i}(31)
    stw 3, {i}(5)
""" for i in (0, 4, 8, 0xc)) + "".join(f"""
    lwz 3, {0xd00 + i}(31)
    stw 3, {i}(6)
""" for i in range(0, 0x40, 4)) + """
    blr
"""


# Between two walls Ratchet can stand in a portal. His walls are a sphere (in the air) or a capsule
# (on the ground) pushed out of the level by two shared functions, called from his collision code in
# each level's copy, with his moby. Inside an opening they find nothing for him. The ground under him
# is a ray of its own and stays. pt_near runs before any of this frame's moves: his moby, what is
# drawn, is where the last update left him.
CODE += """
pt_near:
    li 3, 0
    stw 3, 0xe60(31)
    stw 3, 0xe6c(31)
    lwz 3, 0x1304(31)                # the moon's portal is no wall, and nobody walks through it
    cmpwi 3, 0
    bnelr
    lwz 3, 0x200(31)
    lwz 4, 0x280(31)
    and. 3, 3, 4
    beqlr
    # 1: two walls. 2: a floor and a ceiling, where up stays up and he falls on through the pair.
    # 3: anything else. He goes into the opening just the same, but up changes on the way, so he comes
    # out flying (FLING), and only walls have a place to stand half way.
    lfs 1, {WALL_FLAT}(31)
    lfs 2, 0x228(31)
    lfs 3, 0x2a8(31)
    fabs 4, 2
    fabs 5, 3
    li 3, 1
    fcmpu 0, 4, 1
    bge pt_near_not_walls
    fcmpu 0, 5, 1
    blt pt_near_kind
pt_near_not_walls:
    lfs 1, {STACK_FLAT}(31)
    li 3, 3
    fcmpu 0, 4, 1
    blt pt_near_kind
    fcmpu 0, 5, 1
    blt pt_near_kind
    fmuls 2, 2, 3
    fsubs 1, 1, 1
    fcmpu 0, 2, 1
    bge pt_near_kind
    li 3, 2
pt_near_kind:
    stw 3, 0xe6c(31)
    lis 3, {HERO_MOBY_HA}
    lwz 3, {HERO_MOBY_LO}(3)
    cmpwi 3, 0
    beqlr
    addi 3, 3, 0x10
    addi 5, 31, 0x200
    addi 6, 31, 0x280
""" + opening(3, True, 5, 31, COPY_ZONE, BEHIND, "pt_near_orange") + """
    stw 5, 0xe60(31)
    stw 6, 0xe64(31)
    blr
pt_near_orange:
    addi 5, 31, 0x280
    addi 6, 31, 0x200
""" + opening(3, True, 5, 31, COPY_ZONE, BEHIND, "pt_near_none") + """
    stw 5, 0xe60(31)
    stw 6, 0xe64(31)
pt_near_none:
    blr

# (r3 centre, r8 moby) -> r9 = 1: no wall here. Keeps r3-r7, f1 and f2, the arguments.
pt_wall_gone:
    li 9, 0
    lis 10, {STATE_HA}
    addi 10, 10, {STATE_LO}
    lwz 11, 0xe6c(10)
    cmpwi 11, 0
    beqlr
    lis 11, {HERO_MOBY_HA}
    lwz 11, {HERO_MOBY_LO}(11)
    cmpw 11, 8
    bnelr
    addi 11, 10, 0x200
""" + opening(3, False, 11, 10, WALL_FRONT, WALL_BACK, "pt_wall_orange") + """
    li 9, 1
    blr
pt_wall_orange:
    addi 11, 10, 0x280
""" + opening(3, False, 11, 10, WALL_FRONT, WALL_BACK, "pt_wall_kept") + """
    li 9, 1
pt_wall_kept:
    blr

pt_wall_sphere:
    mr 8, 6
    mflr 12
    bl pt_wall_gone
    mtlr 12
    cmpwi 9, 0
    beq pt_wall_sphere_on
    li 3, 0
    blr
pt_wall_sphere_on:
    stdu 1, -0x28b0(1)
    b {WALL_SPHERE_BODY}

pt_wall_capsule:
    mr 8, 7
    mflr 12
    bl pt_wall_gone
    mtlr 12
    cmpwi 9, 0
    beq pt_wall_capsule_on
    li 3, 0
    blr
pt_wall_capsule_on:
    stdu 1, -0x28c0(1)
    b {WALL_CAPSULE_BODY}

# His rays as well: the one ahead of him turns his walk along the wall. A ray of his through an
# opening finds nothing, as through a real hole. The ground's ray does not cross a wall; over a floor
# portal of a floor and ceiling pair it does, so he drops into it by himself. The mod's
# own rays name no moby. (r3 from, r4 to, r6 moby; nothing in the floating point registers)
pt_wall_ray:
    lis 10, {STATE_HA}
    addi 10, 10, {STATE_LO}
    lwz 11, 0xe6c(10)
    cmpwi 11, 0
    beq pt_wall_ray_on
    lis 11, {HERO_MOBY_HA}
    lwz 11, {HERO_MOBY_LO}(11)
    cmpw 11, 6
    bne pt_ray_other                 # (r3 from, r4 to, r6 moby)
    addi 11, 10, 0x200
""" + through_opening("pt_wall_ray_orange") + """
    b pt_ray_his
pt_wall_ray_orange:
    addi 11, 10, 0x280
""" + through_opening("pt_wall_ray_on") + """
pt_ray_his:
    mflr 12
""" + "".join(f"""
    lis 9, {r >> 16}
    ori 9, 9, {r & 0xFFFF}
    cmpw 12, 9
    beq pt_ray_carry
""" for r in WEAPON_RAYS) + """
    li 3, 0
    blr
pt_wall_ray_on:
    stdu 1, -0x2800(1)
    b {RAY_BODY}

# The rays of other things: only the weapons', as a level's own ray through a portal would make a moby's
# ground the floor of another room.
pt_ray_other:
    mflr 12
""" + "".join(f"""
    lis 9, {r >> 16}
    ori 9, 9, {r & 0xFFFF}
    cmpw 12, 9
    beq pt_ray_weapon
""" for r in WEAPON_RAYS) + """
    b pt_wall_ray_on
pt_ray_weapon:
    addi 11, 10, 0x200
""" + through_opening("pt_ray_weapon_orange") + """
    b pt_ray_carry
pt_ray_weapon_orange:
    addi 11, 10, 0x280
""" + through_opening("pt_wall_ray_on") + """
# (r3 from, r4 to, r5-r7 as for RAY, r10 the state, r11 the portal, f3-f5 where it crosses, from the
# portal's middle) the rest of the ray, from the other portal
pt_ray_carry:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    std 31, 0x60(1)
    std 30, 0x68(1)
    std 29, 0x70(1)
    stw 5, 0x80(1)
    stw 6, 0x84(1)
    stw 7, 0x88(1)
    stw 3, 0x78(1)
    stw 4, 0x7c(1)
    mr 31, 10
    mr 30, 11
    addi 29, 31, 0x200
    cmpw 29, 30
    bne pt_ray_far
    addi 29, 31, 0x280
pt_ray_far:
    stfs 3, 0x1900(31)
    stfs 4, 0x1904(31)
    stfs 5, 0x1908(31)
""" + sub(4, 0, 30, 0x10, 31, 0x1910) + """
    addi 3, 31, 0x1900
    addi 4, 31, 0x1920
    mr 5, 30
    mr 6, 29
    bl pt_map
    addi 3, 31, 0x1910
    addi 4, 31, 0x1930
    mr 5, 30
    mr 6, 29
    bl pt_map
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 3, {P_ray_out}(3)
""" + "".join(f"""
    lfs 1, {0x10 + i}(29)
    lfs 2, {0x1920 + i}(31)
    fadds 1, 1, 2
    lfs 2, {0x20 + i}(29)
    fmadds 1, 2, 3, 1
    stfs 1, {0x1920 + i}(31)
    lfs 1, {0x10 + i}(29)
    lfs 2, {0x1930 + i}(31)
    fadds 1, 1, 2
    stfs 1, {0x1930 + i}(31)
""" for i in (0, 4, 8)) + """
    li 3, 0
    stw 3, 0x192c(31)
    stw 3, 0x193c(31)
    lwz 3, 0x18f8(31)                # for the tests: how many went on
    addi 3, 3, 1
    stw 3, 0x18f8(31)
    addi 3, 31, 0x1920
    addi 4, 31, 0x1930
    lwz 5, 0x80(1)
    lwz 6, 0x84(1)
    lwz 7, 0x88(1)
    bl pt_wall_ray_on
    cmpwi 3, 0
    beq pt_ray_missed
    lis 4, {RAY_RESULT_HA}           # for the tests: where the last one that went on ended, and on what
    addi 4, 4, {RAY_RESULT_LO}
""" + "".join(f"""
    lwz 5, {0x20 + i}(4)
    stw 5, {0x1940 + i}(31)
""" for i in (0, 4, 8)) + """
    lwz 5, 0x18(4)
    cmpwi 5, 0
    beq pt_ray_carried
    stw 5, 0x194c(31)
    b pt_ray_carried
pt_ray_missed:
    # A droplet that met nothing goes on over there: its place and motion follow the ray, and its own
    # code finds the enemies on the far side.
    lis 4, {RAY_LAVA_HI}
    ori 4, 4, {RAY_LAVA_LO}
    ld 5, 0xa0(1)
    cmpw 4, 5
    bne pt_ray_carried
    lwz 3, 0x78(1)
    addi 3, 3, 0x10
    addi 4, 31, 0x1950
    mr 5, 30
    mr 6, 29
    bl pt_map
    lwz 3, 0x78(1)
    lwz 4, 0x7c(1)
""" + "".join(f"""
    lfs 1, {0x1930 + i}(31)
    stfs 1, {i}(4)
    lfs 2, {0x1950 + i}(31)
    stfs 2, {0x10 + i}(3)
    fsubs 1, 1, 2
    stfs 1, {i}(3)
""" for i in (0, 4, 8)) + """
    li 3, 0
pt_ray_carried:
    ld 31, 0x60(1)
    ld 30, 0x68(1)
    ld 29, 0x70(1)
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

# (r3 portal he is at, r4 the other) his mobys, for one draw, where the view needs them
pt_copy_on:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 23, 0x60(1)
    std 24, 0x68(1)
    std 25, 0x70(1)
    mr 25, 3
    mr 24, 4
    std 21, 0x78(1)
    addi 23, 31, {COPY_SAVED}
    lis 3, {HERO_MOBY_HA}
    lwz 3, {HERO_MOBY_LO}(3)
    bl pt_copy_moby
    # and what hangs on him, Clank as well: the engine's table of them, the hand first
    lis 21, {HAND_HA}
    addi 21, 21, {HAND_LO}
pt_copy_held:
    lwz 3, 0(21)
    bl pt_copy_moby
    addi 21, 21, {HELD_STEP}
    lis 3, {HELD_END_HA}
    addi 3, 3, {HELD_END_LO}
    cmpw 21, 3
    blt pt_copy_held
    ld 21, 0x78(1)
    ld 23, 0x60(1)
    ld 24, 0x68(1)
    ld 25, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

pt_copy_moby:                       # (r3 moby, r23 its entry, r25 from, r24 to)
    lis 4, {MOBY_TABLE_HA}
    lwz 5, {MOBY_TABLE_LO}(4)
    cmplw 3, 5
    bltlr
    lis 4, {MOBY_TABLE_END_HA}
    lwz 5, {MOBY_TABLE_END_LO}(4)
    cmplw 3, 5
    bgelr
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    std 22, 0x60(1)
    mr 22, 3
    stw 22, 0(23)
""" + "".join(f"""
    lwz 3, {i}(22)
    stw 3, {0x10 + i}(23)
    lwz 3, {0x10 + i}(22)
    stw 3, {0x20 + i}(23)
""" for i in range(0, 0x10, 4)) + "".join(f"""
    lwz 3, {0xC0 + i}(22)
    stw 3, {0x30 + i}(23)
""" for i in range(0, 0x30, 4)) + sub(22, 0x10, 25, 0x10, 31, 0x900) + """
    addi 3, 31, 0x900
    addi 4, 31, 0x940
    mr 5, 25
    mr 6, 24
    bl pt_map
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 12, {P_near_scale}(3)
""" + "".join(f"""
    lfs 1, {0x10 + i}(24)
    lfs 2, {0x940 + i}(31)
    fadds 1, 1, 2
    stfs 1, {0x10 + i}(22)
    fmuls 1, 1, 12
    stfs 1, {i}(22)
""" for i in (0, 4, 8)) + "".join(f"""
    addi 3, 22, {row}
    addi 4, 31, 0x950
    mr 5, 25
    mr 6, 24
    bl pt_map
""" + "".join(f"""
    lwz 3, {0x950 + i}(31)
    stw 3, {row + i}(22)
""" for i in (0, 4, 8)) for row in (0xc0, 0xd0, 0xe0)) + """
    addi 23, 23, 0x60
    ld 22, 0x60(1)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr

pt_copy_off:                        # last first: a moby in the table twice ends as it began
    addi 3, 31, {COPY_LAST}
    li 4, {COPY_MOBYS}
    mtctr 4
pt_copy_back:
    lwz 4, 0(3)
    cmpwi 4, 0
    beq pt_copy_next
""" + "".join(f"""
    lwz 5, {0x10 + i}(3)
    stw 5, {i}(4)
    lwz 5, {0x20 + i}(3)
    stw 5, {0x10 + i}(4)
""" for i in range(0, 0x10, 4)) + "".join(f"""
    lwz 5, {0x30 + i}(3)
    stw 5, {0xC0 + i}(4)
""" for i in range(0, 0x30, 4)) + """
    li 4, 0
    stw 4, 0(3)
pt_copy_next:
    addi 3, 3, -0x60
    bdnz pt_copy_back
    blr
"""


# The moon. With one portal out there the other one opens on space and pulls in what it can see:
# Ratchet, enemies, shots and crates, faster the closer they are, until a new portal replaces either of
# them or the level ends. He dies of it, as of a fall. Nothing is freed, as what a moby's owner expects of it is not known: what
# goes out is hidden and held far away (pt_moon_parked). Bolts stay: they die of being moved.
CODE += """
pt_moon:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0xa0(1)
    std 24, 0x60(1)
    std 25, 0x68(1)
    std 26, 0x70(1)
    std 27, 0x78(1)
    std 28, 0x80(1)
    std 29, 0x88(1)
    std 30, 0x90(1)
    bl pt_moon_parked
    lwz 30, 0x1304(31)
    cmpwi 30, 0
    beq pt_moon_done
    addi 29, 31, 0x200
    cmpw 29, 30
    bne pt_moon_other
    addi 29, 31, 0x280
pt_moon_other:
    lwz 3, 0(29)
    cmpwi 3, 0
    beq pt_moon_done                 # only the moon's so far: nothing to go through
    lwz 3, 0x1308(31)                # counted down only for the pull to build up: it stays open
    cmpwi 3, 0
    bgt pt_moon_running
    li 3, {MOON_FRAMES}
pt_moon_running:
    cmpwi 3, 1
    ble pt_moon_open
    addi 3, 3, -1
pt_moon_open:
    stw 3, 0x1308(31)
    lwz 3, 0x1340(31)                # just out, he comes back near it: not straight in again
    cmpwi 3, 0
    beq pt_moon_him
    addi 3, 3, -1
    stw 3, 0x1340(31)
    b pt_moon_mobys
pt_moon_him:
    # him
    lis 3, {HERO_POS_HA}
    addi 3, 3, {HERO_POS_LO}
    lis 4, {HERO_MOBY_HA}
    lwz 4, {HERO_MOBY_LO}(4)
    bl pt_moon_pull
    cmpwi 3, 0
    beq pt_moon_mobys
    cmpwi 3, 1
    lis 28, {HERO_POS_HA}
    addi 28, 28, {HERO_POS_LO}
    bne pt_moon_he_is_out
""" + "".join(f"""
    lfs 1, {i}(28)
    lfs 2, {0x1310 + i}(31)
    fadds 1, 1, 2
    stfs 1, {i}(28)
""" for i in (0, 4, 8)) + """
    b pt_moon_mobys
pt_moon_he_is_out:
    lfs 1, {MOON_DEATH}(31)
    stfs 1, 8(28)
    li 3, {MOON_SAFE}
    stw 3, 0x1340(31)
    # the rest: the same care as pt_mobys, as empty slots hold anything
pt_moon_mobys:
    lis 3, {MOBY_TABLE_HA}
    lwz 28, {MOBY_TABLE_LO}(3)
    lis 3, {MOBY_TABLE_END_HA}
    lwz 27, {MOBY_TABLE_END_LO}(3)
    lwz 26, 0x410(31)                # their slots behind the mesh, as for pt_mobys: +0x14 frame held
    addis 26, 26, {MOBY_TRACK_HIGH}
    lwz 25, 0(31)
pt_moon_next:
    addi 28, 28, 0x100
    addi 26, 26, {MOBY_TRACK_SIZE}
    cmplw 28, 27
    bge pt_moon_done
    lbz 3, 0x20(28)
    cmplwi 3, {MOBY_DYING}
    bge pt_moon_next
    lwz 3, 0x64(28)
    lis 4, {OPD_FIRST_HA}
    addi 4, 4, {OPD_FIRST_LO}
    cmplw 3, 4
    blt pt_moon_next
    lis 4, {OPD_LAST_HA}
    addi 4, 4, {OPD_LAST_LO}
    cmplw 3, 4
    bge pt_moon_next
    lwz 4, 0x24(28)
    lis 5, {MAIN_HEAP_HA}
    lwz 6, {MAIN_HEAP_LO}(5)
    cmplw 4, 6
    blt pt_moon_next
    lwz 6, {MAIN_HEAP_END_LO}(5)
    addi 6, 6, -0x50
    cmplw 4, 6
    bge pt_moon_next
    lha 5, 0x46(4)
    cmpwi 5, {KIND_ENEMY}
    beq pt_moon_take
    cmpwi 5, {KIND_SHOT}
    beq pt_moon_take
    cmpwi 5, {MOON_KIND_CRATE}
    bne pt_moon_next
pt_moon_take:
    lhz 3, 0x34(28)                  # gone already
    andi. 3, 3, 1
    bne pt_moon_next
    # Once caught its place is ours: an enemy's own update would walk it back every frame.
    lwz 3, 0x14(26)
    addi 3, 3, 1
    cmpw 3, 25
    beq pt_moon_caught
""" + "".join(f"""
    lwz 3, {0x10 + i}(28)
    stw 3, {i}(26)
""" for i in (0, 4, 8)) + """
pt_moon_caught:
    mr 3, 26
    mr 4, 28
    bl pt_moon_pull
    cmpwi 3, 0
    beq pt_moon_next
    cmpwi 3, 1
    bne pt_moon_gone
    stw 25, 0x14(26)
    lis 4, {POOL_HA}
    addi 4, 4, {POOL_LO}
    lfs 4, {P_near_scale}(4)
""" + "".join(f"""
    lfs 1, {i}(26)
    lfs 2, {0x1310 + i}(31)
    fadds 1, 1, 2
    stfs 1, {i}(26)
    lfs 2, {0x10 + i}(28)
    stfs 1, {0x10 + i}(28)
    fsubs 1, 1, 2
    fmuls 1, 1, 4
    lfs 2, {i}(28)
    fadds 2, 2, 1
    stfs 2, {i}(28)
""" for i in (0, 4, 8)) + """
    b pt_moon_next
pt_moon_gone:
    addi 4, 31, 0x1400
    li 5, {PARKED}
    mtctr 5
pt_moon_free:
    lwz 6, 0(4)
    cmpwi 6, 0
    beq pt_moon_park
    addi 4, 4, 4
    bdnz pt_moon_free
    b pt_moon_next
pt_moon_park:
    stw 28, 0(4)
    lhz 3, 0x34(28)
    ori 3, 3, 1
    sth 3, 0x34(28)
    b pt_moon_next
pt_moon_done:
    ld 24, 0x60(1)
    ld 25, 0x68(1)
    ld 26, 0x70(1)
    ld 27, 0x78(1)
    ld 28, 0x80(1)
    ld 29, 0x88(1)
    ld 30, 0x90(1)
    addi 1, 1, 0xa0
    ld 0, 0x10(1)
    mtlr 0
    blr

# (r3 its place, r4 the moby, r29 the opening) -> r3: 0 nothing, 1 +0x1310 is this frame's step, 2 out
pt_moon_pull:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 22, 0x60(1)
    std 23, 0x68(1)
    mr 22, 3
    mr 23, 4
""" + "".join(f"""
    lwz 3, {i}(22)
    stw 3, {0x1320 + i}(31)
""" for i in (0, 4, 8)) + """
    lis 3, {POOL_HA}
    addi 3, 3, {POOL_LO}
    lfs 1, 0x1328(31)
    lfs 2, {P_chest}(3)
    fadds 1, 1, 2
    stfs 1, 0x1328(31)
    lfs 3, {MOON_OFF}(31)
""" + add_scaled(29, 0x10, 3, 29, 0x20, 31, 0x1330) + sub(31, 0x1330, 31, 0x1320, 31, 0x1310) + dot(3, 31, 0x1310, 31, 0x1310, 4) + """
    fsqrts 3, 3
    stfs 3, 0x131c(31)
    lfs 4, {MOON_RANGE}(31)
    fcmpu 0, 3, 4
    bge pt_moon_nothing
""" + dot(5, 31, 0x1310, 29, 0x20, 6) + """
    fsubs 6, 6, 6                    # behind the wall it is not out in the open
    fcmpu 0, 5, 6
    bge pt_moon_nothing
    # Walls hold it back, the other things in the crowd do not. The ray starts clear of its body:
    # the moby it is told to leave out only counts with some flags.
    lfs 3, 0x131c(31)
    lfs 4, {MOON_CLEAR}(31)
    fcmpu 0, 3, 4
    ble pt_moon_seen
    fdivs 4, 4, 3
""" + add_scaled(31, 0x1320, 4, 31, 0x1310, 31, 0x1320) + """
    addi 3, 31, 0x1320
    addi 4, 31, 0x1330
    li 5, 0
    mr 6, 23
    li 7, 0
    bl {RAY}
    nop
    cmpwi 3, 0
    bne pt_moon_nothing
pt_moon_seen:
    lfs 3, 0x131c(31)
    lfs 4, {MOON_EAT}(31)
    lis 3, {HERO_MOBY_HA}
    lwz 3, {HERO_MOBY_LO}(3)
    cmpw 3, 23
    beq pt_moon_reach
    lfs 4, {MOON_EAT_MOBY}(31)       # enemies are big, and their middle never gets that close
pt_moon_reach:
    fcmpu 0, 3, 4
    blt pt_moon_out
    lfs 4, {MOON_PULL}(31)
    fdivs 4, 4, 3
    lfs 5, {MOON_MOST}(31)
    fcmpu 0, 4, 5
    ble pt_moon_step
    fmr 4, 5
pt_moon_step:
    # it builds up, so there is a moment to see what is happening and run
    lwz 3, 0x1308(31)
    subfic 3, 3, {MOON_FRAMES}
    extsw 3, 3
    std 3, -0x10(1)
    lfd 6, -0x10(1)
    fcfid 6, 6
    lfs 7, {MOON_RAMP}(31)
    fdivs 6, 6, 7
    lfs 7, {WALL_ONE}(31)
    fcmpu 0, 6, 7
    ble pt_moon_ramped
    fmr 6, 7
pt_moon_ramped:
    fmuls 4, 4, 6
    fdivs 4, 4, 3
""" + "".join(f"""
    lfs 1, {0x1310 + i}(31)
    fmuls 1, 1, 4
    stfs 1, {0x1310 + i}(31)
""" for i in (0, 4, 8)) + """
    li 3, 1
    b pt_moon_pulled
pt_moon_out:
    li 3, 2
    b pt_moon_pulled
pt_moon_nothing:
    li 3, 0
pt_moon_pulled:
    ld 22, 0x60(1)
    ld 23, 0x68(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr

# What went out stays out: hidden, and put back far up every frame, whatever its update does.
pt_moon_parked:
    addi 3, 31, 0x1400
    li 4, {PARKED}
    mtctr 4
    lfs 1, {MOON_PARK}(31)
    lis 4, {POOL_HA}
    addi 4, 4, {POOL_LO}
    lfs 2, {P_near_scale}(4)
    fmuls 2, 1, 2
pt_moon_hold:
    lwz 4, 0(3)
    cmpwi 4, 0
    beq pt_moon_held
    lbz 5, 0x20(4)
    cmplwi 5, {MOBY_DYING}
    blt pt_moon_keep
    li 5, 0
    stw 5, 0(3)
    b pt_moon_held
pt_moon_keep:
    stfs 1, 0x18(4)
    stfs 2, 8(4)
    lhz 5, 0x34(4)
    ori 5, 5, 1
    sth 5, 0x34(4)
pt_moon_held:
    addi 3, 3, 4
    bdnz pt_moon_hold
    blr
"""


# What falls into a floor portal: it sinks through the opening, comes out of the other portal with
# the speed it has by then, and flies on under gravity until it lands. Entries of +0xb00, 0x30 each:
# +0 moby (0 free), +4 2 once out, +8 entry, +0xc exit, +0x10 motion, +0x1c frames, +0x20 how deep.
CODE += """
pt_carry_add:                       # (r30 moby, r25 entry, r24 exit)
    addi 3, 31, 0xb00
    li 4, {CARRIED}
    mtctr 4
pt_carry_free:
    lwz 4, 0(3)
    cmpwi 4, 0
    beq pt_carry_found
    addi 3, 3, 0x30
    bdnz pt_carry_free
    blr
pt_carry_found:
    stw 30, 0(3)
    li 4, 1
    stw 4, 4(3)
    stw 25, 8(3)
    stw 24, 0xc(3)
    li 4, 0
    stw 4, 0x10(3)
    stw 4, 0x14(3)
    stw 4, 0x18(3)
    stw 4, 0x1c(3)
    stw 4, 0x20(3)
    blr

pt_carry:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x80(1)
    std 28, 0x60(1)
    std 29, 0x68(1)
    std 30, 0x70(1)
    addi 28, 31, 0xb00
    li 29, {CARRIED}
pt_carry_next:
    lwz 30, 0(28)
    cmpwi 30, 0
    beq pt_carry_on
    lbz 3, 0x20(30)
    cmplwi 3, {MOBY_DYING}
    bge pt_carry_end
    lwz 3, 0x1c(28)
    addi 3, 3, 1
    stw 3, 0x1c(28)
    cmpwi 3, {CARRY_FRAMES}
    bgt pt_carry_end
    lis 4, {POOL_HA}
    addi 4, 4, {POOL_LO}
    lwz 3, 4(28)
    cmpwi 3, 1
    bne pt_carry_flying
    # sinking: faster and faster along the portal's normal
    lfs 1, 0x20(28)
    lfs 2, {P_fall_gain}(4)
    fadds 1, 1, 2
    stfs 1, 0x20(28)
    lwz 5, 8(28)
""" + "".join(f"""
    lfs 2, {0x20 + i}(5)
    fneg 2, 2
    fmuls 2, 2, 1
    stfs 2, {0x10 + i}(28)
    lfs 3, {0x10 + i}(30)
    fadds 3, 3, 2
    stfs 3, {0x10 + i}(30)
""" for i in (0, 4, 8)) + """
    lwz 3, 0x1c(28)
    cmpwi 3, {SINK_FRAMES}
    blt pt_carry_place
    # through: place and motion turned by the pair
""" + sub(30, 0x10, 5, 0x10, 31, 0x170) + """
    addi 3, 31, 0x170
    addi 4, 31, 0x170
    lwz 5, 8(28)
    lwz 6, 0xc(28)
    bl pt_map
    addi 3, 28, 0x10
    addi 4, 31, 0x950
    lwz 5, 8(28)
    lwz 6, 0xc(28)
    bl pt_map
    lwz 6, 0xc(28)
""" + "".join(f"""
    lfs 1, {0x170 + i}(31)
    lfs 2, {0x10 + i}(6)
    fadds 1, 1, 2
    stfs 1, {0x10 + i}(30)
    lwz 3, {0x950 + i}(31)
    stw 3, {0x10 + i}(28)
""" for i in (0, 4, 8)) + """
    li 3, 2
    stw 3, 4(28)
    b pt_carry_place
pt_carry_flying:
""" + "".join(f"""
    lfs 1, {0x10 + i}(30)
    lfs 2, {0x10 + i}(28)
    fadds 1, 1, 2
    stfs 1, {0x10 + i}(30)
""" for i in (0, 4, 8)) + """
    lfs 1, 0x18(28)
    lfs 2, {P_mob_gravity}(4)
    fsubs 1, 1, 2
    stfs 1, 0x18(28)
    lwz 3, 0x1c(28)
    cmpwi 3, {CARRY_CLEAR}
    blt pt_carry_place               # still coming out of the wall behind the exit
    # the ground under it ends the flight
    lfs 1, 0x18(28)
    lfs 2, {P_zero}(4)
    fcmpu 0, 1, 2
    bge pt_carry_place
    lfs 2, {P_mob_foot}(4)
    fsubs 1, 1, 2
    lfs 2, 0x18(30)
    fadds 2, 2, 1
    lwz 3, 0x10(30)
    stw 3, 0x170(31)
    lwz 3, 0x14(30)
    stw 3, 0x174(31)
    lfs 1, {P_mob_foot}(4)
    lfs 3, 0x18(30)
    fadds 3, 3, 1
    stfs 3, 0x178(31)
    lwz 3, 0x10(30)
    stw 3, 0x1d0(31)
    lwz 3, 0x14(30)
    stw 3, 0x1d4(31)
    stfs 2, 0x1d8(31)
    addi 3, 31, 0x170
    addi 4, 31, 0x1d0
    li 5, 2
    li 6, 0
    li 7, 0
    bl {RAY}
    nop
    cmpwi 3, 0
    beq pt_carry_place
    lis 3, {RAY_RESULT_HA}
    addi 3, 3, {RAY_RESULT_LO}
    lwz 3, 0x28(3)
    stw 3, 0x18(30)
    b pt_carry_end
pt_carry_place:
    lis 4, {POOL_HA}
    addi 4, 4, {POOL_LO}
    lfs 2, {P_near_scale}(4)
""" + "".join(f"""
    lfs 1, {0x10 + i}(30)
    fmuls 1, 1, 2
    stfs 1, {i}(30)
""" for i in (0, 4, 8)) + """
    b pt_carry_on
pt_carry_end:
    li 3, 0
    stw 3, 0(28)
pt_carry_on:
    addi 28, 28, 0x30
    addic. 29, 29, -1
    bne pt_carry_next
    ld 28, 0x60(1)
    ld 29, 0x68(1)
    ld 30, 0x70(1)
    addi 1, 1, 0x80
    ld 0, 0x10(1)
    mtlr 0
    blr
"""


# The HUD, while the gun is in hand: a bar for each portal, bright once it is placed. Aiming with L1
# the game draws no crosshair for the gun, so there is one in the same colours: the shot goes through
# the middle of the screen. Screen space is 512 x 416.
def rect(x, y, w, h, colour):
    return f"""
    li 3, {x}
    li 4, {y}
    li 5, {w}
    li 6, {h}
    {colour}
    bl pt_rect
"""


BLUE_REG, ORANGE_REG, WHITE_LOAD = "mr 7, 30", "mr 7, 29", "lwz 7, 0x3a8(31)"
CODE += """
pt_rect:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x90(1)
    li 8, 0
    stw 8, 0x70(1)
    stw 7, 0x74(1)
    addi 8, 31, 0x440
    stw 8, 0x7c(1)
    li 7, 0
    li 8, 0
    li 9, 4
    li 10, 4
    bl {PASTE}
    addi 1, 1, 0x90
    ld 0, 0x10(1)
    mtlr 0
    blr

pt_hud:
    mflr 0
    std 0, 0x10(1)
    stdu 1, -0x70(1)
    std 29, 0x60(1)
    std 30, 0x68(1)
    lwz 3, 0x404(31)
    cmpwi 3, 0
    beq pt_hud_done
    lwz 3, 0x40c(31)
    cmpwi 3, 0
    bne pt_hud_done
    lwz 30, 0x3a0(31)
    lwz 3, 0x200(31)
    cmpwi 3, 0
    bne pt_hud_blue
    clrlwi 30, 30, 8
    oris 30, 30, {HUD_DIM}
pt_hud_blue:
    lwz 29, 0x3a4(31)
    lwz 3, 0x280(31)
    cmpwi 3, 0
    bne pt_hud_orange
    clrlwi 29, 29, 8
    oris 29, 29, {HUD_DIM}
pt_hud_orange:
""" + rect(222, 386, 30, 8, BLUE_REG) + rect(260, 386, 30, 8, ORANGE_REG) + """
    lwz 3, 0x400(31)
    andi. 3, 3, {L1}
    beq pt_hud_done
""" + rect(240, 198, 3, 20, BLUE_REG) + rect(240, 198, 8, 2, BLUE_REG) + rect(240, 216, 8, 2, BLUE_REG)
CODE += rect(269, 198, 3, 20, ORANGE_REG) + rect(264, 198, 8, 2, ORANGE_REG) + rect(264, 216, 8, 2, ORANGE_REG)
CODE += rect(255, 207, 2, 3, WHITE_LOAD) + """
pt_hud_done:
    ld 29, 0x60(1)
    ld 30, 0x68(1)
    addi 1, 1, 0x70
    ld 0, 0x10(1)
    mtlr 0
    blr
"""


# Booted without the Trilogy's menu RC2 has no name, and the check of the disc fails. With the menu
# this does nothing. tools/ingame.py boots that way, as the menu cannot be pressed from inside RC2.
CODE += """
pt_name:
    cmpwi 4, 0
    beq pt_name_none
    lbz 0, 0(4)
    cmpwi 0, 0
    bne pt_name_kept
pt_name_none:
    lis 4, {POOL_HA}
    addi 4, 4, {POOL_LO}
    addi 4, 4, {P_app_name}
    lis 6, {STATE_HA}
    addi 6, 6, {STATE_LO}
    li 7, 1
    stw 7, 0x420(6)
pt_name_kept:
    stdu 1, -0x90(1)
    b {APP_NAME_BODY}

# The region comes with the menu as well, and it picks the saves' names and the level data.
pt_region:
    lis 6, {STATE_HA}
    addi 6, 6, {STATE_LO}
    lwz 7, 0x420(6)
    cmpwi 7, 0
    beq pt_region_kept
    li 7, {REGION_EUROPE}
    stw 7, {APP_REGION}(30)
pt_region_kept:
    lis 3, 0x124
    b {REGION_BODY}
"""


def parts(args):
    return [CODE]


def fields(args, addr):
    vertices, indices, _, _ = gunmesh.buffers()
    return dict(TUNING_WORDS=(max(v[0] for v in TUNING.values()) - 0x180) // 4 + 1, COOLDOWN_LATE=COOLDOWN - 10,
                WALL_WORDS=len(WALLS), MOON_WORDS=MOON_LEVELS * 4,
                GUN_SIZE=gun_size(), GUN_VERTICES=len(vertices), GUN_PIXELS=len(gunmesh.texture()), MESH_WORDS=len(mesh_block()) // 4,
                RAY_LAVA_HI=RAY_LAVA >> 16, RAY_LAVA_LO=RAY_LAVA & 0xFFFF, GUN_SCALE_HI=GUN_SCALE >> 16, GUN_SCALE_LO=GUN_SCALE & 0xFFFF, ICON_BYTES=len(gunicon.texture()), PICTURE_BLOCKS=gunpicture.SIZE // 4, **pair("GUN", addr["gun"]), **pair("ICON", addr["icon"]),
                **pair("PICTURE_DATA", addr["picture"]))


def gun_size():
    vertices, indices, _, _ = gunmesh.buffers()
    return (len(vertices) + len(indices) + 15) & ~15


def mesh_block():
    """The mesh, its groups and its texture entry as they are at STATE + 0x700, fixed up the way
    the game's loader leaves them."""
    vertices, indices, count, triples = gunmesh.buffers()
    mesh = struct.pack(">8I", 1, 0, STATE + 0x740, STATE + 0x750, 0, 0, count << 16, count << 16)   # the buffers: at run time
    groups = struct.pack(">4I", STATE + 0x760, 0, triples, 0x05000000) + struct.pack(">4I", STATE + 0x760, triples, 0, 0x0F000000)
    entry = struct.pack(">9I", GUN_TEXTURE - 0xC0000000, 0x00018829, 0x00010303, 0x80040000, 0x0000AAE4, 0x02063E80,
                        gunmesh.SIZE << 16 | gunmesh.SIZE, 0x00100000, 0x00FF0000)
    return mesh.ljust(0x40, b"\0") + groups + entry


def data(args):
    def gun(address):
        vertices, indices, _, _ = gunmesh.buffers()
        return (vertices + indices).ljust(gun_size(), b"\0") + gunmesh.texture()
    return [("ro", "gun", gun), ("ro", "icon", lambda address: gunicon.texture()), ("ro", "picture", lambda address: gunpicture.texture())]


def words(args, addr):
    """The Zapper's rows: no ammunition, so the tile and the Quick Select show none and nothing runs out."""
    out = {}
    for item, pack, most in ((ITEM_GUN, 100, 30), (ITEM_GUN_UP, 100, 30)):
        row = ITEM_ROW + item * ITEM_ROW_SIZE
        out[row + ROW_AMMO_PACK] = (struct.pack(">H", pack), bytes(2))
        out[row + ROW_AMMO_MOST] = (struct.pack(">H", most), bytes(2))
    return out


def hooks(args):
    return [Hook(PRE_DRAW, "pt_draw_hook", PRE_DRAW_WORD, jump=True), Hook(PAD_READ, "pt_pad", PAD_GET),
            Hook(APP_NAME, "pt_name", APP_NAME_WORD, jump=True), Hook(REGION_SET, "pt_region", REGION_WORD, jump=True),
            Hook(WALL_SPHERE, "pt_wall_sphere", WALL_SPHERE_WORD, jump=True),
            Hook(WALL_CAPSULE, "pt_wall_capsule", WALL_CAPSULE_WORD, jump=True),
            Hook(RAY, "pt_wall_ray", RAY_WORD, jump=True),
            Hook(TEXT_LOOKUP, "pt_text", TEXT_WORD, jump=True), Hook(PICK, "pt_pick", PICK_WORD),
            *[Hook(site, label, READ_FILE) for sites in PICTURE_READS
              for site, label in zip(sites, ("pt_read_header", "pt_read_pixels"))]]


def moons():
    out = []
    for level in range(MOON_LEVELS):
        height, spread = MOONS.get(level, (0, 0))
        out += [math.sin(math.radians(height - spread)), math.sin(math.radians(height + spread)), 0.0, 1.0 if spread else 0.0]
    return tuple(out)


def pool(args):
    ring = []
    for i in range(SEGMENTS_RING + 1):
        angle = 2 * math.pi * i / SEGMENTS_RING
        ring += [math.cos(angle), math.sin(angle)]
    tuning = bytearray((max(v[0] for v in TUNING.values()) - 0x180) + 4)
    for at, value in TUNING.values():
        struct.pack_into(">f", tuning, at - 0x180, value)
    return dict(tuning=bytes(tuning), moons=moons(), walls=tuple(v[1] for v in WALLS.values()), textures=texture(SURFACE_0) + bytes(12) + texture(SURFACE_1) + bytes(12),
                ring=tuple(ring), world_up=(0.0, 0.0, 1.0, 0.0), steep=0.9, near_least=0.5, near_scale=1024.0,
                white=texture(WHITE - 0xC0000000, 0x00040004, 16), one=1.0, half=0.5, zero=0.0, inner=0.93, outer=1.07,
                chest=0.7, mesh=mesh_block(), ray_aiming=0.5, ray_edge=1.0, three=3.0, cam_step=1.0 / 30, cam_height=2.0, cam_rise=0.12, cam_aligned=0.01, vec_tiny=0.0001, at_a=0.2447, at_b=0.0663,
                quarter_pi=math.pi / 4, half_pi=math.pi / 2, pi=math.pi, fall_start=-0.3, fall_gain=0.012, mob_gravity=0.012, hero_gravity=0.006, glide_brake=0.012,
                mob_foot=0.6, mob_reach=0.7, mob_reach_far=3.5, mob_behind=-0.5, mob_floor=1.4, mob_out=1.0,
                vec_near=0.09, per_second=60.0,
                # colours are AABBGGRR, 0x80 being full strength
                blue=struct.pack(">I", 0xFF803810), orange=struct.pack(">I", 0xFF104880),
                clear=struct.pack(">I", 0xFF808080),
                app_name=b"/dev_bdvd/PS3_GAME/USRDIR/RC2.ppu.self".ljust(40, b"\0"),
                shot_speed=1.6, shot_blobs=(-1.4, 0.13, -0.7, 0.2, 0.0, 0.28, 0.0, 0.13), shot_tall=1.0 / 1.45,
                ray_out=RAY_OUT, rings=RINGS, cam_skip=0.2, view_near=4.0, view_cone=0.45,      # cosine of a little over half the view's diagonal
                picture_entry=struct.pack(">9I", 0, 0x00018629, 0x00010303, 0x80040000, 0x0000AAE4, 0x02063E80,
                                          2 * gunpicture.SIZE << 16 | 2 * gunpicture.SIZE, 0x00100000, 0x00FF0000),
                text_name=TEXT_GUN.ljust(16, b"\0"), text_about=TEXT_GUN_ABOUT.ljust(128, b"\0"), text_got=TEXT_GUN_GOT.ljust(48, b"\0"))
