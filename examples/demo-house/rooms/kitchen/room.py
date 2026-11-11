"""Kitchen (the repo's second example): a 1960s galley in Yellowstone National Park employee housing,
modeled from the park's two public-domain photos (--design asis), and redesigned with real
products (--design new).

Built from layout.py (inches) with the shared parts in lib/roomkit (kitchen.py for the
cabinets and appliances). Run through ./render.sh; options are listed in README.md. Plan
coordinates: x east, y north, origin at the room's interior NW corner.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
while not os.path.isdir(os.path.join(ROOT, "lib", "roomkit")):   # the repo root
    ROOT = os.path.dirname(ROOT)
CATALOG = HERE   # the folder holding catalog/: houses/ (your products and colors) or examples/
while CATALOG != ROOT and not os.path.isdir(os.path.join(CATALOG, "catalog")):
    CATALOG = os.path.dirname(CATALOG)
sys.path[:0] = [HERE, CATALOG, os.path.join(ROOT, "lib")]
import layout as L  # noqa: E402
import catalog  # noqa: E402,F401  (adds its colors to roomkit's tables)
from roomkit import core, kitchen as K  # noqa: E402
from roomkit.core import (IN, arg, box, camera, casing_frame, cut, cylinder, dim, prism, rect_walls,  # noqa: E402
                          sky, sun, to_plan, wall_cutter, wall_run, window_portal)
from roomkit.materials import PAINTS, basic_set, emission, image_box_material, principled, wall_tile_material  # noqa: E402
from roomkit.millwork import lathe  # noqa: E402
from roomkit.parts import can_light, six_panel_door, wall_plate  # noqa: E402

CAMS = arg("--cams", "photo1,photo2,sink,plan").split(",")
DESIGN = arg("--design", "asis")              # asis: the room in the park's photos
NEW = DESIGN != "asis"

scene = core.start(__file__, L.CEILING)

# ---------------------------------------------------------------- materials
basic_set()
K.appliance_materials()
if NEW:
    principled("paint", PAINTS["warmwhite"], 0.65)
    image_box_material("floor", "floor_plank.jpg", (24 * IN, 52 * IN, 24 * IN), 0.45)   # the gray vinyl plank stays
    principled("base", (0.90, 0.89, 0.86), 0.3)                            # white baseboard
    principled("cabinet", (0.23, 0.26, 0.17), 0.45)                        # AXSTAD gray-green, from IKEA's photo (lifted for the room's light)
    principled("kick", (0.23, 0.26, 0.17), 0.45)                           # SEKTION plinth in the door color
    image_box_material("counter", "karlby_walnut.jpg", (74 * IN, 25.6 * IN, 25.6 * IN), 0.35)   # KARLBY walnut
    principled("pull", (0.80, 0.62, 0.34), 0.25, 1.0)                     # BAGGANAS brass
    for ax in ("x", "y"):
        wall_tile_material(f"tile_{ax}", ax, 0.0, pattern="subway8", color="cloewhite", z0=0.0)
    STYLE, PULL, PULL_MAT = "shaker", "knob", "pull"
    K.KNOB_INSET = 1.125                                                  # centered on the AXSTAD stile
else:
    principled("paint", (0.33, 0.60, 0.50), 0.7)                          # sea green, from the photos
    # textures cut from the photos (textures/make_textures.py)
    image_box_material("floor", "floor_plank.jpg", (24 * IN, 52 * IN, 24 * IN), 0.45)   # gray wood-look vinyl plank
    principled("base", (0.10, 0.07, 0.06), 0.4)                            # dark brown vinyl cove base
    image_box_material("cabinet", "birch.jpg", (23 * IN, 23 * IN, 28 * IN), 0.35, tint=(1.6, 1.35, 1.0))   # honey birch slab doors
    principled("kick", (0.08, 0.06, 0.05), 0.6)
    image_box_material("counter", "laminate.jpg", (16 * IN, 10 * IN, 10 * IN), 0.3, tint=(1.9, 1.55, 1.1))   # wood-grain laminate
    principled("pull", (0.30, 0.20, 0.12), 0.35, 0.8)                      # oil-rubbed bronze wire pulls
    STYLE, PULL, PULL_MAT = "slab", "wire", "pull"

# ---------------------------------------------------------------- shell
C, W, D, T = L.CEILING, L.ROOM_W, L.ROOM_D, L.WALL_T
OUTLINE = [(0, 0), (W, 0), (W, -D), (0, -D)]          # interior, clockwise from the NW corner
WALLS = rect_walls(W, D)
walls = wall_run("walls", OUTLINE, T, 0, C, "paint", closed=True)
prism("floor", OUTLINE, -1, 0, "floor")
prism("ceiling", OUTLINE, C, C + 1, "ceiling")
base = wall_run("base", list(reversed(OUTLINE)), 0.25, 0, 4.0, "base", closed=True)


def inward(frame):
    r = frame[1]
    return (math.sin(r), -math.cos(r))


windows = []
for k, w in enumerate(L.WINDOWS):
    f = WALLS[w["wall"]]
    x0, x1, z0, z1 = w["at"], w["at"] + w["width"], w["sill"], w["sill"] + w["height"]
    cut(walls, wall_cutter(f"cut_window_{k}", f, x0, x1, z0, z1, T))
    casing_frame(f"case_window_{k}", to_plan(f, x0), to_plan(f, x1), inward(f), z1 - z0, z0=z0, sill=True)
    mid = T / 2
    prism(f"window_glass_{k}", [to_plan(f, x0, mid - 0.1), to_plan(f, x1, mid - 0.1),
                                to_plan(f, x1, mid + 0.1), to_plan(f, x0, mid + 0.1)], z0, z1, "glass")
    xs = sorted((to_plan(f, x0)[1], to_plan(f, x1)[1]))
    gx = to_plan(f, 0, mid)[0]
    box(f"window_rail_{k}", gx - 0.9, gx + 0.9, *xs, (z0 + z1) / 2 - 0.75, (z0 + z1) / 2 + 0.75, "trim")
    cx, cy = to_plan(f, (x0 + x1) / 2, T + 0.5)
    window_portal(f"window_portal_{k}", x1 - x0, z1 - z0, (cx, cy, (z0 + z1) / 2), (math.pi / 2, 0, f[1]))
    px, py = to_plan(f, (x0 + x1) / 2, mid)
    windows.append(dict(cx=px, cy=py, cz=(z0 + z1) / 2, w=x1 - x0, h=z1 - z0, into=list(inward(f))))

def jambs(name, f, a, b, z0, z1):
    """White painted jambs lining an opening through the wall's thickness (sides, and the head)."""
    for k, (u0, u1, za, zb) in enumerate(((a, a + 0.75, z0, z1), (b - 0.75, b, z0, z1), (a, b, z1 - 0.75, z1))):
        prism(f"{name}_{k}", [to_plan(f, u0, 0), to_plan(f, u1, 0), to_plan(f, u1, T), to_plan(f, u0, T)], za, zb, "trim")


for k, w in enumerate(L.WINDOWS):
    jambs(f"case_jamb_window_{k}", WALLS[w["wall"]], w["at"], w["at"] + w["width"], w["sill"], w["sill"] + w["height"])
for k, d in enumerate(L.DOORS):
    f = WALLS[d["wall"]]
    a, b = d["at"], d["at"] + d["width"]
    jambs(f"case_jamb_door_{k}", f, a, b, 0, d["height"])
    cut(walls, wall_cutter(f"cut_door_{k}", f, a, b, 0, d["height"], T))
    cut(base, wall_cutter(f"cut_door_base_{k}", f, a - 3.6, b + 3.6, -0.5, 5, T))
    casing_frame(f"case_door_{k}", to_plan(f, a), to_plan(f, b), inward(f), d["height"])
LR = L.DOORS[1]
if LR["door"]:   # open 90 degrees into the eat-in end, hinged on the south jamb
    slab = six_panel_door("door_living", LR["width"] - 0.25, LR["height"] - 0.5)
    hy = -(D - LR["at"])                     # the south jamb (at runs north from the south corner)
    slab.location = core.I(0.9, hy - 0.2, 0.25)
    slab.rotation_euler = (0, 0, 0)

WD = L.NEW_WALL_D if NEW else K.WALL_D              # wall cabinet box depth
SOD = L.NEW_SOFFIT_D if NEW else L.SOFFIT["depth"]  # soffits: flush with the wall cabinets' doors

# ---------------------------------------------------------------- sink wall (east)
EF = ((W, 0), -math.pi / 2)            # the east wall's frame: x south from the north corner
if NEW:
    E_BASE, DW_AT, SINK, CT, CD, BOX_TOP = L.NEW_EAST_BASE, L.NEW_DW_AT, L.NEW_SINK, L.NEW_COUNTER_T, L.NEW_COUNTER_D, L.NEW_BOX_TOP
    SPL = 0                            # the tile is the back splash
else:
    E_BASE, DW_AT, SINK, CT, CD = L.EAST_BASE, L.DISHWASHER_AT, dict(L.SINK, bowls=2, bowl_d=8), L.COUNTER_T, L.COUNTER_D
    BOX_TOP, SPL = L.COUNTER_H - L.COUNTER_T, L.SPLASH
east, east_x1 = K.base_run("east_base", *EF, 0, E_BASE, sink_at=SINK["center"], style=STYLE, pull_kind=PULL,
                           pull_mat=PULL_MAT, box_top=BOX_TOP)
K.dishwasher("dishwasher", *EF, DW_AT, top=BOX_TOP, mat="steel" if NEW else "enamel_white")
sc, sw, sd = SINK["center"], SINK["width"], SINK["depth"]
syc = -CD / 2 + 0.5
ztop = K.counter("counter_e", east, 0, east_x1, depth=CD, z=BOX_TOP, thick=CT, splash=SPL,
                 hole=(sc - sw / 2 + 1.5, sc + sw / 2 - 1.5, syc - sd / 2 + 1.5, syc + sd / 2 - 1.5))
K.drop_in_sink("sink", east, sc, syc, ztop, sw, sd, bowls=SINK["bowls"], bowl_d=SINK["bowl_d"])
K.kitchen_faucet("faucet", east, sc, syc + sd / 2 - 1.6, ztop + 0.15, kind="pull_down" if NEW else "two_handle",
                 mat="steel" if NEW else "chrome")
box("east_end", east_x1 - 0.75, east_x1, -CD + 1.0, 0, 0.5 if not NEW else 0, ztop - CT, "cabinet", east)
if NEW:
    for k, u in enumerate(L.NEW_EAST_UPPERS):
        root, _ = K.wall_run(f"east_upper_{k}", *EF, -u["y0"], u["fronts"], u["z0"], u["z1"],
                             style=STYLE, pull_kind=PULL, pull_mat=PULL_MAT, depth=WD)
        for f, ab in (("filler", u["filler"]), ("wall_filler", u.get("wall_filler"))):
            if ab:
                box(f"east_upper_{k}_{f}", -ab[0], -ab[1], -WD - K.FRONT_T, 0, u["z0"], u["z1"], "cabinet", root)
else:
    for k, u in enumerate(L.EAST_UPPERS):
        K.wall_run(f"east_upper_{k}", *EF, -u["y0"], [(u["y0"] - u["y1"], u["doors"])], u["z0"], u["z1"],
                   style=STYLE, pull_kind=PULL, pull_mat=PULL_MAT)

# ---------------------------------------------------------------- range wall (west)
WF = ((0, -D), math.pi / 2)            # the west wall's frame: x north from the south corner


def wx(y):
    """West-wall local x for plan y."""
    return D + y


fy0 = -L.FRIDGE_Y - L.FRIDGE["width"]          # fridge, then the base, then the range, going south
by0 = fy0 - (sum(w for w, _ in L.NEW_WEST_BASE) if NEW else L.WEST_BASE)
ry0 = by0 - L.RANGE_W
MZ = L.NEW_MICRO_Z if NEW else L.MICRO_Z
if NEW:
    K.refrigerator("fridge", *WF, wx(-L.FRIDGE_Y - L.NEW_FRIDGE["width"]), **L.NEW_FRIDGE, kind="top_freezer",
                   mat="steel", handle_mat="steel", handle="x1")     # hinged on the south side: the door clears the wall
    west, _ = K.base_run("west_base", *WF, wx(by0), L.NEW_WEST_BASE, style=STYLE, pull_kind=PULL,
                         pull_mat=PULL_MAT, box_top=BOX_TOP)
    u = L.NEW_WEST_UPPER
    root, _ = K.wall_run("west_upper", *WF, wx(u["y1"]), u["fronts"], u["z0"], u["z1"], style=STYLE, pull_kind=PULL,
                         pull_mat=PULL_MAT, depth=WD)
    box("west_upper_filler", wx(u["filler"][1]), wx(u["filler"][0]), -WD - K.FRONT_T, 0, u["z0"], u["z1"], "cabinet", root)
    f = L.NEW_FRIDGE_UPPER
    K.wall_run("fridge_upper", *WF, wx(f["y1"]), [(f["y0"] - f["y1"], "doors2")], f["z0"], f["z1"], style=STYLE,
               pull_kind=PULL, pull_mat=PULL_MAT, depth=24)
else:
    K.refrigerator("fridge", *WF, wx(fy0), **L.FRIDGE, kind="top_freezer")
    west, _ = K.base_run("west_base", *WF, wx(by0), L.WEST_FRONTS, style=STYLE, pull_kind=PULL,
                         pull_mat=PULL_MAT, box_top=BOX_TOP)
    u = L.WEST_UPPER
    K.wall_run("west_upper", *WF, wx(u["y1"]), [(u["y0"] - u["y1"], "doors2")], u["z0"], u["z1"],
               style=STYLE, pull_kind=PULL, pull_mat=PULL_MAT)
K.counter("counter_w", west, wx(by0), wx(fy0), depth=CD, z=BOX_TOP, thick=CT, splash=SPL)
K.freestanding_range("range", *WF, wx(ry0), width=L.RANGE_W, mat="steel", doors=2)    # stays
K.otr_microwave("microwave", *WF, wx(ry0), MZ)                                         # stays
if NEW:   # a lift-up cabinet over the microwave, which hangs from it
    m = L.NEW_MICRO_UPPER
    K.wall_run("micro_upper", *WF, wx(ry0), [(L.RANGE_W, "flap")], m["z0"], m["z1"], style=STYLE, pull_kind=PULL,
               pull_mat=PULL_MAT, depth=WD)

# drywall soffits over the wall cabinets, flush with the cabinet fronts. As it is, the west one stops
# at the old uppers (bare wall over the microwave); the new design runs both the length of their runs
SO = L.SOFFIT
box("soffit_e", W - SOD, W, (L.NEW_EAST_UPPERS if NEW else L.EAST_UPPERS)[-1]["y1"], 0, SO["z"], C, "paint")
if NEW:
    box("soffit_w", 0, SOD, ry0, 0, SO["z"], C, "paint")
else:
    box("soffit_w", 0, SOD, L.WEST_UPPER["y1"], L.WEST_UPPER["y0"], SO["z"], C, "paint")

if NEW:   # Cloe white subway from the counter to the wall cabinets, both runs
    z0 = BOX_TOP + CT
    box("tile_e", W - 0.375, W, -east_x1, 0, z0, L.SPLASH_TOP, "tile_y")
    box("tile_w", 0, 0.375, ry0 + L.RANGE_W, fy0, z0, L.SPLASH_TOP, "tile_y")
    box("tile_w_range", 0, 0.375, ry0, ry0 + L.RANGE_W, 36, MZ, "tile_y")
    for k, w in enumerate(L.WINDOWS[:1]):   # the tile stops at the sink window's casing
        trim = wall_cutter(f"cut_tile_window_{k}", WALLS[w["wall"]], w["at"] - 3.5, w["at"] + w["width"] + 3.5,
                           w["sill"] - 4.25, w["sill"] + w["height"] + 3.5, T)
        trim["opening"] = False
        cut(core.bpy.data.objects["tile_e"], trim)

# ---------------------------------------------------------------- outlets and switches
wall_plate("switch_hall", W - 26, -0.0, 48, 2, "switch", 0.0)
wall_plate("outlet_e1", W - (0.375 if NEW else 0), -20, 46, 1, "gfci", -math.pi / 2)
wall_plate("outlet_e2", W - (0.375 if NEW else 0), -80, 46, 1, "gfci", -math.pi / 2)
wall_plate("outlet_w1", 0.375 if NEW else 0, by0 + 6, 46, 1, "gfci", math.pi / 2)
if not NEW:   # the microwave's outlet, just over it at the north end (photo 1); the new one is in the cabinet
    wall_plate("outlet_micro", 0, ry0 + L.RANGE_W - 4, MZ + 18.5, 1, "gfci", math.pi / 2)

# ---------------------------------------------------------------- lights
principled("brass", (0.75, 0.58, 0.32), 0.3, 1.0)
if NEW:   # Halo canless wafers down the aisle and in the eat-in end
    principled("can_trim", (0.95, 0.95, 0.95), 0.4)
    emission("can_lens", (1.0, 0.92, 0.82), 25.0 * core.CAN_DIM)
    for k, (x, y) in enumerate(L.NEW_CANS):
        can_light(f"can_{k + 1}", x, y, 45)
    emission("led", (1.0, 0.84, 0.66), 14.0)           # IKEA MITTLED strips, under the wall cabinets' front edge
    for k, (wall, a, b) in enumerate(L.NEW_STRIPS):
        x0 = WD - 2.5 if wall == "W" else W - WD + 1.5
        box(f"strip_{k + 1}", x0, x0 + 1.0, b, a, 53.6, 54.0, "led")
    # the eat-in end: DOCKSTA (white tulip pedestal) and a brass dome pendant over it
    t, pd = L.NEW_TABLE, L.NEW_PENDANT
    principled("table_white", (0.86, 0.86, 0.84), 0.25)
    cylinder("table_top", t["d"] / 2, 1.0, "table_white", (t["x"], t["y"], t["h"] - 0.5), segs=64)
    lathe("table_base", [(9.5, 0), (9.0, 1.2), (3.0, 4.0), (2.2, 12), (2.2, 22), (5.5, 27.5), (6, t["h"] - 1)],
          (t["x"], t["y"], 0), "z", "table_white", segs=48)
    r = pd["d"] / 2
    lathe("pendant_shade", [(r, 0), (r - 0.4, 2.5), (r - 2.2, 6.0), (r - 5.0, 8.5), (1.2, 10.0), (0.6, 10.2)],
          (t["x"], t["y"], pd["bottom"]), "z", "brass", segs=48)
    cylinder("pendant_cord", 0.15, C - pd["bottom"] - 10.2, "black_steel", (t["x"], t["y"], (C + pd["bottom"] + 10.2) / 2), segs=8)
    cylinder("pendant_canopy", 2.5, 1.0, "brass", (t["x"], t["y"], C - 0.5), segs=32)
    emission("pendant_glow", (1.0, 0.9, 0.78), 6.0 * core.CAN_DIM)
    cylinder("pendant_lens", r - 1.0, 0.1, "pendant_glow", (t["x"], t["y"], pd["bottom"] + 1.5), segs=48)
    ld = core.bpy.data.lights.new("pendant", "POINT")
    ld.energy, ld.color, ld.shadow_soft_size = 60 * core.CAN_DIM, (1.0, 0.88, 0.74), 3 * IN
    ob = core.bpy.data.objects.new("pendant", ld)
    ob.location = core.I(t["x"], t["y"], pd["bottom"] + 2)
    core.link(ob)
    core.LIGHTS.append(dict(name="pendant", x=t["x"], y=t["y"], z=pd["bottom"] + 2, power=60))
else:
    for lt in L.LIGHTS:
        K.ceiling_fixture(lt["name"], lt["x"], lt["y"], kind=lt["kind"], diameter=lt["d"], power=45, trim_mat="brass")

# ---------------------------------------------------------------- the hall and living room beyond the doors
principled("hall_paint", (0.80, 0.70, 0.55), 0.7)
principled("living_paint", (0.78, 0.50, 0.20), 0.7)
principled("oak_floor", (0.50, 0.30, 0.15), 0.35)
HN = T                                   # the hall, north of the north wall
prism("hall_floor", [(-20, HN + 48), (W + 20, HN + 48), (W + 20, HN), (-20, HN)], -1, 0, "oak_floor")
prism("hall_ceiling", [(-20, HN + 48), (W + 20, HN + 48), (W + 20, HN), (-20, HN)], C, C + 1, "ceiling")
box("hall_wall_n", -24, W + 24, HN + 48, HN + 52, 0, C, "hall_paint")
LW = -T                                  # the living room, west of the west wall
prism("living_floor", [(LW - 160, 20), (LW, 20), (LW, -D - 20), (LW - 160, -D - 20)], -1, 0, "oak_floor")
prism("living_ceiling", [(LW - 160, 20), (LW, 20), (LW, -D - 20), (LW - 160, -D - 20)], C, C + 1, "ceiling")
box("living_wall_w", LW - 164, LW - 160, -D - 20, 20, 0, C, "living_paint")
box("living_wall_s", LW - 160, LW, -D - 24, -D - 20, 0, C, "living_paint")

# ---------------------------------------------------------------- daylight
sky()
SUN_DIR = (-0.55, 0.45, -0.55)          # late afternoon sun in through the east windows
sun(SUN_DIR, energy=1.6)
principled("lawn", (0.07, 0.11, 0.04), 0.95)
box("outside_ground", -1200, 1200, -1200, 1200, -31, -30, "lawn")
box("seal_floor", -T - 200, W + T + 50, -D - T - 50, T + 80, -3, -1.2, "ceiling")
box("ceiling_seal", -T - 200, W + T + 50, -D - T - 50, T + 80, C + 1.2, C + 3, "ceiling")

# ---------------------------------------------------------------- dimension lines
dim((0, 0), (W, 0), "photo", off=-14, key="room_w")
dim((W, 0), (W, -D), "photo", off=-8, key="room_d")
dim((W, 0), (W, -L.SINK["center"]), "photo", off=-30, key="sink_center")
dim((0, fy0), (0, by0), "photo", off=30, key="west_base")

# ---------------------------------------------------------------- cameras
# both solved with the room's sizes from camera_marks.py (lib/tools/solve_cameras.py): 10-13 px mean error
c1 = camera("photo1", (52.3, -183.0, 65.8), (48.7, -87.1, 37.4), lens=18.0)
c1.rotation_euler.rotate_axis("Z", -0.0215)
c2 = camera("photo2", (42.4, 1.7, 62.9), (110.0, -64.7, 31.0), lens=15.5)   # standing in the hall doorway
c2.rotation_euler.rotate_axis("Z", -0.029)
camera("sink", (34, -112, 62), (116, -38, 44), lens=16, level=True)     # the sink run, from across the aisle
camera("plan", (W / 2, -D / 2, 400), (W / 2, -D / 2, 0), ortho=max(W, D) + 40)

# ---------------------------------------------------------------- render / export
core.finish(
    CAMS,
    info=dict(windows=windows, sun=dict(dir=list(SUN_DIR)), walk=dict(x0=28, x1=W - 28, y0=-D + 12, y1=-8)),
    glass=("window_glass",),
)
