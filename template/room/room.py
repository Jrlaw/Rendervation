"""ROOM NAME: the room as it is today, ready to grow into the new design.

Built from layout.py (inches) with the shared parts in lib/roomkit. Run through ./render.sh;
options are listed in README.md. Plan coordinates: x east, y north, origin at the room's
interior NW corner. Start from a plain box that matches the photos, then add what's in the
room (lib/roomkit/parts.py has doors, outlets, cans, shelves and generic fixtures; specific
products go in houses/catalog/). When the new design starts, keep this scene buildable behind
--design asis: the as-is renders are always kept (PROCESS.md step 2).
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.isdir(os.path.join(ROOT, "lib", "roomkit")):   # the repo root, above houses/
    ROOT = os.path.dirname(ROOT)
CATALOG = HERE   # the folder holding catalog/: houses/ (your products and colors) or examples/
while CATALOG != ROOT and not os.path.isdir(os.path.join(CATALOG, "catalog")):
    CATALOG = os.path.dirname(CATALOG)
sys.path[:0] = [HERE, CATALOG, os.path.join(ROOT, "lib")]
import layout as L  # noqa: E402
import catalog  # noqa: E402,F401  (adds its colors to roomkit's tables)
from roomkit import core  # noqa: E402
from roomkit.core import (arg, box, camera, casing_frame, cut, dim, prism, rect_walls, sky, sun,  # noqa: E402
                          to_plan, wall_cutter, wall_run, window_portal)
from roomkit.materials import PAINTS, basic_set, emission, principled  # noqa: E402
from roomkit.parts import can_light, six_panel_door, wall_plate  # noqa: E402

CAMS = arg("--cams", "photo1,plan").split(",")
PAINT = arg("--paint", "warmwhite")

scene = core.start(__file__, L.CEILING)

# ---------------------------------------------------------------- materials
principled("paint", PAINTS[PAINT], 0.65)
basic_set()
principled("floor", (0.45, 0.33, 0.22), 0.35)         # stand-in: swap for the real floor's texture
principled("can_trim", (0.95, 0.95, 0.95), 0.4)
emission("can_lens", (1.0, 0.92, 0.82), 25.0 * (0.35 if core.NIGHT else 1.0))

# ---------------------------------------------------------------- shell
C, W, D, T = L.CEILING, L.ROOM_W, L.ROOM_D, L.WALL_T
OUTLINE = [(0, 0), (W, 0), (W, -D), (0, -D)]          # interior, clockwise from the NW corner
WALLS = rect_walls(W, D)
walls = wall_run("walls", OUTLINE, T, 0, C, "paint", closed=True)
prism("floor", OUTLINE, -1, 0, "floor")
prism("ceiling", OUTLINE, C, C + 1, "ceiling")
base = wall_run("base", list(reversed(OUTLINE)), 0.6, 0, 4, "trim", closed=True)


def inward(frame):
    """Unit plan vector from a wall into the room."""
    r = frame[1]
    return (math.sin(r), -math.cos(r))


# ---------------------------------------------------------------- windows
windows = []
for k, w in enumerate(L.WINDOWS):
    f = WALLS[w["wall"]]
    x0, x1, z0, z1 = w["at"], w["at"] + w["width"], w["sill"], w["sill"] + w["height"]
    cut(walls, wall_cutter(f"cut_window_{k}", f, x0, x1, z0, z1, T))
    casing_frame(f"case_window_{k}", to_plan(f, x0), to_plan(f, x1), inward(f), z1 - z0, z0=z0, sill=True)
    mid = T / 2
    prism(f"window_glass_{k}", [to_plan(f, x0, mid - 0.1), to_plan(f, x1, mid - 0.1),
                                to_plan(f, x1, mid + 0.1), to_plan(f, x0, mid + 0.1)], z0, z1, "glass")
    cx, cy = to_plan(f, (x0 + x1) / 2, T + 0.5)
    window_portal(f"window_portal_{k}", x1 - x0, z1 - z0, (cx, cy, (z0 + z1) / 2), (math.pi / 2, 0, f[1]))
    gx, gy = to_plan(f, (x0 + x1) / 2, mid)
    windows.append(dict(cx=gx, cy=gy, cz=(z0 + z1) / 2, w=x1 - x0, h=z1 - z0, into=list(inward(f))))

# ---------------------------------------------------------------- doors
for k, d in enumerate(L.DOORS):
    f = WALLS[d["wall"]]
    x0, x1 = d["at"], d["at"] + d["width"]
    cut(walls, wall_cutter(f"cut_door_{k}", f, x0, x1, 0, d["height"], T))   # stop at the floor: below it the cut leaks light
    cut(base, wall_cutter(f"cut_door_base_{k}", f, x0 - 3.6, x1 + 3.6, -0.5, 5, T))
    casing_frame(f"case_door_{k}", to_plan(f, x0), to_plan(f, x1), inward(f), d["height"])
    # threshold across the wall, so the gap under the door doesn't show daylight
    prism(f"threshold_{k}", [to_plan(f, x0, 0), to_plan(f, x1, 0), to_plan(f, x1, T), to_plan(f, x0, T)],
          -1, 0.25, "trim")
    if d.get("door", True):     # closed 6-panel door in the middle of the wall
        slab = six_panel_door(f"door_{k}", d["width"] - 0.25, d["height"] - 0.5)
        sx, sy = to_plan(f, x0 + 0.125, T / 2)
        slab.location = core.I(sx, sy, 0.25)
        slab.rotation_euler = (0, 0, f[1])
    # light switch beside the latch side, at the usual 48"
    wall_plate(f"switch_{k}", *to_plan(f, x1 + 3.5 + 3), 48, 1, "switch", f[1])

# ---------------------------------------------------------------- lights and daylight
for k, (x, y) in enumerate(L.CANS):
    can_light(f"can_{k + 1}", x, y, 40)
sky()
SUN_DIR = (0.55, -0.75, -0.42)      # direction the sunlight travels (plan x, y, z); set from the photos
sun(SUN_DIR)
principled("lawn", (0.07, 0.11, 0.04), 0.95)
box("outside_ground", -1200, 1200, -1200, 1200, -31, -30, "lawn")
# one slab under the floor and one over the ceiling, so gaps can't leak daylight in
box("seal_floor", -T - 50, W + T + 50, -D - T - 50, T + 50, -3, -1.2, "ceiling")
box("ceiling_seal", -T - 50, W + T + 50, -D - T - 50, T + 50, C + 1.2, C + 3, "ceiling")

# ---------------------------------------------------------------- dimension lines
# key= ties a line to its dimensions.json entry (layout.py dimension()): editable in the walkthrough
dim((0, 0), (W, 0), "assumed", off=-8, key="room_w")
dim((0, 0), (0, -D), "assumed", off=8, key="room_d")

# ---------------------------------------------------------------- cameras
# photo1..N: one per intake photo, placed and aimed until the render lines up with the photo
camera("photo1", (W - 14, -D + 14, 62), (W * 0.25, -D * 0.25, 40), lens=16)
camera("plan", (W / 2, -D / 2, 400), (W / 2, -D / 2, 0), ortho=max(W, D) + 40)

# ---------------------------------------------------------------- render / export
core.finish(
    CAMS,
    info=dict(windows=windows, sun=dict(dir=list(SUN_DIR)), walk=dict(x0=12, x1=W - 12, y0=-D + 12, y1=-12)),
    glass=("window_glass",),
)
