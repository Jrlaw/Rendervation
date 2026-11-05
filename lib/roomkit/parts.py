"""Reusable building parts and fixtures: doors, wall plates, recessed cans, wainscot, shelves,
towel hardware, plants and generic bath fixtures. Specific products (a particular vanity or
toilet model) go in the person's own catalog (houses/catalog/), not here.

Fixtures that sit on a wall use one local frame: wall at y=0, room toward -y, x along the
wall; rot_z turns that frame onto the wall (0: north wall, pi: south wall, pi/2: west wall,
-pi/2: east wall). Inches throughout.
"""
import math
import random

import bmesh
import bpy
from mathutils import Vector

from . import core
from .core import I, IN, box, cut, cylinder, empty, link, mesh_obj, prism
from .materials import bark_material, leaf_material, principled, rug_material


def _mat(name, *args, **kw):
    """Create a material the first time a part needs it."""
    if name not in core.MATS:
        principled(name, *args, **kw)


# ---------------------------------------------------------------- doors and trim
def six_panel_door(name, width, height, mat="door", handle_side=1):
    """A 6-panel door slab in local space: x along width, y = thickness (outward +y), z up.
    Satin nickel lever both sides."""
    root = bpy.data.objects.new(name, None)
    link(root)
    t = 1.375
    box(f"{name}_slab", 0, width, -t / 2, t / 2, 0, height, mat, root, bevel=0.06)
    stile, rail = 4.5, 4.5
    pw = (width - 3 * stile) / 2
    rows = [(height - rail - 14, height - rail), (36 + rail, height - 2 * rail - 14), (rail, 36)]
    for face in (1, -1):
        for zr in rows:
            for col in range(2):
                x0 = stile + col * (pw + stile)
                y0, y1 = (t / 2, t / 2 + 0.12) if face > 0 else (-t / 2 - 0.12, -t / 2)
                box(f"{name}_panel", x0, x0 + pw, y0, y1, zr[0], zr[1], mat, root, bevel=0.1)
    hx = width - 2.5 if handle_side > 0 else 2.5
    for face in (1, -1):
        cylinder(f"{name}_rose", 1.2, 0.4, "nickel", (hx, face * (t / 2 + 0.2), 36),
                 rot=(math.pi / 2, 0, 0), parent=root)
        box(f"{name}_lever", hx - 4.5 if handle_side > 0 else hx, hx if handle_side > 0 else hx + 4.5,
            face * (t / 2 + 1.6) - 0.3, face * (t / 2 + 1.6) + 0.3, 35.6, 36.4, "nickel", root, bevel=0.15)
        box(f"{name}_neck", hx - 0.3, hx + 0.3, min(face * t / 2, face * (t / 2 + 1.6)),
            max(face * t / 2, face * (t / 2 + 1.6)), 35.7, 36.3, "nickel", root)
    return root


def wainscot_run(name, origin, rot_z, length, gaps=(), height=34):
    """Raised-panel wood wainscot with a white chair rail and dark baseboard on one wall
    (materials 'wainscot', 'wainscot_dark', 'trim'). x from 0..length; gaps: (x0, x1) left open."""
    root = empty(name, origin, rot_z)
    edges = [0.0] + [v for g in gaps for v in g] + [length]
    for a, b in zip(edges[::2], edges[1::2]):
        if b - a < 1:
            continue
        box(f"{name}_slab", a, b, -0.75, 0, 0, height, "wainscot", root)
        box(f"{name}_base", a, b, -1.1, 0, 0, 5, "wainscot_dark", root, bevel=0.1)
        box(f"{name}_rail", a, b, -1.6, 0, height, height + 2, "trim", root, bevel=0.2)
        n = max(1, round((b - a) / 26))            # ~2' panels between 3" stiles
        pw = (b - a - 3 * (n + 1)) / n
        for k in range(n):
            p0 = a + 3 + k * (pw + 3)
            for x0, x1, z0, z1 in ((p0, p0 + pw, 8, 9), (p0, p0 + pw, height - 4, height - 3),
                                   (p0, p0 + 1, 8, height - 3), (p0 + pw - 1, p0 + pw, 8, height - 3)):
                box(f"{name}_mold", x0, x1, -1.2, -0.75, z0, z1, "wainscot", root, bevel=0.15)
    return root


# ---------------------------------------------------------------- electrical and lights
def wall_plate(name, x, y, z, gangs, kind, rot_z, standoff=0.0):
    """White decora plate on a wall face at (x, y), center height z. kind: 'switch' or 'gfci'.
    standoff: thickness of tile on the wall there, so the plate sits on the tile face."""
    _mat("plate", (0.93, 0.92, 0.89), 0.35)
    root = bpy.data.objects.new(name, None)
    link(root)
    off = standoff
    root.location = I(x + off * math.sin(rot_z), y - off * math.cos(rot_z), 0)   # out toward the room
    root.rotation_euler = (0, 0, rot_z)
    w, h = 4.56 + 1.81 * (gangs - 1), 4.5
    box(f"{name}_plate", -w / 2, w / 2, -0.25, 0, z - h / 2, z + h / 2, "plate", root, bevel=0.08)
    for g in range(gangs):
        gx = -1.81 * (gangs - 1) / 2 + 1.81 * g
        if kind == "switch":      # decora rocker
            box(f"{name}_rocker", gx - 0.66, gx + 0.66, -0.45, -0.25, z - 1.3, z + 1.3, "plate", root, bevel=0.05)
            continue
        for dz in (-1.15, 1.15):  # GFCI: two receptacle faces, test/reset between
            box(f"{name}_face", gx - 0.66, gx + 0.66, -0.37, -0.25, z + dz - 0.55, z + dz + 0.55, "plate", root, bevel=0.05)
            for sx in (-0.25, 0.25):
                box(f"{name}_slot", gx + sx - 0.04, gx + sx + 0.04, -0.39, -0.35, z + dz - 0.2, z + dz + 0.2, "fixture", root)
    return root


def register(name, x0, x1, y0, y1):
    """Floor heating register (material 'register')."""
    return box(name, x0, x1, y0, y1, 0, 0.12, "register")


def can_light(name, x, y, power=60.0, trim=3.4, lens=2.6, spread=115, tilt=0.0):
    """Recessed can in the ceiling: trim ring, glowing lens and a warm spot light.
    Evening dims it to about a third, --hero further. Listed in scene.json for the walkthrough.
    trim, lens: radii, inches. spread: beam, degrees. tilt: radians about y, to lie on a sloped
    ceiling; the light still aims straight down, like a gimbal trim."""
    C = core.CEILING
    cylinder(f"{name}_trim", trim, 0.2, "can_trim", (x, y, C - 0.1), rot=(0, tilt, 0), segs=48)
    cylinder(f"{name}_lens", lens, 0.1, "can_lens", (x, y, C - 0.25), rot=(0, tilt, 0), segs=48)
    ld = bpy.data.lights.new(name, "SPOT")
    ld.energy = power * core.CAN_DIM
    ld.color = (1.0, 0.9, 0.8)
    ld.spot_size = math.radians(spread)
    ld.spot_blend = 0.6
    ld.shadow_soft_size = 2.5 * IN
    ob = bpy.data.objects.new(name, ld)
    ob.location = I(x, y, C - 0.6)
    link(ob)
    core.LIGHTS.append(dict(name=name, x=x, y=y, z=C - 0.6, power=power))


# ---------------------------------------------------------------- rounded fixtures
def plan_prism(name, pts, z0, z1, mat, parent=None, sub=2):
    """Prism from local inch points, smoothed with subdivision (for rounded fixtures)."""
    ob = prism(name, pts, z0, z1, mat, parent)
    ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))
    b = ob.modifiers.new("bevel", "BEVEL")
    b.width = 0.6 * IN
    b.segments = 3
    if sub:
        ob.modifiers.new("sub", "SUBSURF").levels = sub
    return ob


def egg(length, half_w, back_square=True, n_front=2.3, n_back=5.0, N=48):
    """Elongated-bowl plan: x from 0 (back) to length (front), y in +-half_w."""
    pts = []
    for j in range(N):
        th = 2 * math.pi * j / N
        c, s_ = math.cos(th), math.sin(th)
        n = n_front if c > 0 else (n_back if back_square else n_front)
        x = length / 2 + (length / 2) * math.copysign(abs(c) ** (2 / n), c)
        y = half_w * math.copysign(abs(s_) ** (2 / n), s_)
        pts.append((x, y))
    return pts


# ---------------------------------------------------------------- rugs
def rug(name, x0, x1, y0, y1, fname, flip=False):
    """Flat bath mat with a picture (textures/fname) across the top."""
    rug_material(name, fname, (x0, x1, y0, y1), flip)
    box(name, x0, x1, y0, y1, 0, 0.45, name, bevel=0.35)


# ---------------------------------------------------------------- ladders
def towel_ladder(name, origin, rot_z, width=16, height=66, lean_deg=11, mat="wood"):
    """Leaning ladder: rails at x=0 and x=width; the foot stands out from the wall, the top
    rests on it. Two towels folded over rungs."""
    root = empty(name, origin, rot_z)
    lean = math.radians(lean_deg)
    foot = height * math.sin(lean)
    rise = height * math.cos(lean)

    def out(h):      # distance from the wall at height h
        return foot * (1 - h / rise) + 0.8

    for xx in (0, width):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        rail = mesh_obj(f"{name}_rail", bm, mat, root)
        rail.scale = (0.8 * IN, 1.4 * IN, height * IN)
        rail.location = I(xx, -out(rise / 2), rise / 2)
        rail.rotation_euler = (-lean, 0, 0)
        rail.modifiers.new("bevel", "BEVEL").width = 0.15 * IN
    for k in range(5):
        h = 14 + k * 12
        cylinder(f"{name}_rung", 0.45, width, mat, (width / 2, -out(h), h), rot=(0, math.pi / 2, 0), parent=root)
    for h, wdt, drop in ((38, 12, 14), (50, 11, 18)):
        y = -out(h)
        for side in (-1, 1):
            box(f"{name}_towel", width / 2 - wdt / 2, width / 2 + wdt / 2, y + side * 0.55 - 0.35,
                y + side * 0.55 + 0.35, h - drop + (4 if side < 0 else 0), h + 0.45, "towel", root, bevel=0.3)
    return root


def shelf_ladder(name, origin, rot_z, width=18, height=66, lean_deg=12, mat="wood", props=True, hybrid=False):
    """Leaning shelf ladder: two rails like towel_ladder, with four flat shelves running back to
    the wall, deepest at the bottom. props: a few bottles, a rolled towel and a small plant.
    hybrid: two shelves up top for products, towel rungs below with two towels over them."""
    root = empty(name, origin, rot_z)
    lean = math.radians(lean_deg)
    foot = height * math.sin(lean)
    rise = height * math.cos(lean)

    def out(h):      # distance from the wall at height h
        return foot * (1 - h / rise) + 0.8

    for xx in (0, width):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        rail = mesh_obj(f"{name}_rail", bm, mat, root)
        rail.scale = (0.9 * IN, 1.6 * IN, height * IN)
        rail.location = I(xx, -out(rise / 2), rise / 2)
        rail.rotation_euler = (-lean, 0, 0)
        rail.modifiers.new("bevel", "BEVEL").width = 0.15 * IN
    heights = (44, 56) if hybrid else (12, 26, 40, 54)
    for h in heights:
        box(f"{name}_shelf", 0.45, width - 0.45, -out(h) - 0.6, -0.2, h - 0.75, h, mat, root, bevel=0.08)
    if hybrid:
        _mat("towel", (0.92, 0.91, 0.88), 0.95)
        for h in (12, 22, 32):
            cylinder(f"{name}_rung", 0.45, width, mat, (width / 2, -out(h), h), rot=(0, math.pi / 2, 0), parent=root)
        for h, wdt, drop in ((22, 13, 12), (32, 12, 15)):
            y = -out(h)
            for side in (-1, 1):
                box(f"{name}_towel", width / 2 - wdt / 2, width / 2 + wdt / 2, y + side * 0.55 - 0.35,
                    y + side * 0.55 + 0.35, h - drop + (4 if side < 0 else 0), h + 0.45, "towel", root, bevel=0.3)
        if props:
            for k, (xx, r, hh) in enumerate(((3.5, 1.1, 6), (6.5, 1.3, 4.5), (10, 0.9, 5.5), (14, 1.2, 4))):
                cylinder(f"{name}_bottle", r, hh, "ceramic" if k % 2 else "acrylic", (xx, -out(44) / 2, 44 + hh / 2), parent=root)
            cylinder(f"{name}_pot", 1.8, 3.2, "ceramic", (width - 4, -out(56) / 2, 56 + 1.6), parent=root)
        return root
    if props:
        _mat("towel", (0.92, 0.91, 0.88), 0.95)
        cylinder(f"{name}_towel_roll", 2.6, width - 4, "towel", (width / 2, -out(12) / 2 - 0.5, 12 + 2.6),
                 rot=(0, math.pi / 2, 0), parent=root)
        for k, (xx, r, hh) in enumerate(((3.5, 1.1, 6), (6.5, 1.3, 4.5), (9.5, 0.9, 5.5), (13.5, 1.2, 4))):
            cylinder(f"{name}_bottle", r, hh, "ceramic" if k % 2 else "acrylic", (xx, -out(40) / 2, 40 + hh / 2), parent=root)
        for k, (xx, r, hh) in enumerate(((4, 1.6, 3), (9, 1.4, 3.5))):
            cylinder(f"{name}_jar", r, hh, "ceramic", (xx, -out(26) / 2, 26 + hh / 2), parent=root)
        cylinder(f"{name}_pot", 1.8, 3.2, "ceramic", (width - 4, -out(54) / 2, 54 + 1.6), parent=root)
    return root


# ---------------------------------------------------------------- shelves (wood: material 'wood')
def board_shelf(name, origin, rot_z, z0, width=24, depth=7, thick=1.75):
    """Plain floating board with a rolled towel and a small potted plant.
    x from 0..width."""
    root = empty(name, origin, rot_z)
    box(f"{name}_board", 0, width, -depth, 0, z0, z0 + thick, "wood", root, bevel=0.08)
    top = z0 + thick
    tl = min(9, width * 0.45)                                # rolled towel sized to the board
    cylinder(f"{name}_towel", 1.9, tl, "towel", (1.5 + tl / 2, -depth / 2, top + 1.9), rot=(0, math.pi / 2, 0), parent=root)
    px = max(width - 4, 1.5 + tl + 2.3)                     # keep the pot clear of the towel on short boards
    cylinder(f"{name}_pot", 1.8, 3.4, "pot", (px, -depth / 2, top + 1.7), parent=root)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=2.6 * IN)
    pl = mesh_obj(f"{name}_plant", bm, "leaves", root, smooth=True)
    pl.location = I(px, -depth / 2, top + 5.6)
    return root


def open_box(name, origin, rot_z, x0, z0, w=10, h=10, d=6, t=0.75, prop=None):
    """Open cube shelf (no front or back); x0/z0 is the box's lower-left corner along the wall.
    prop: 'towel' or 'plant'."""
    root = empty(name, origin, rot_z)
    box(f"{name}_bottom", x0, x0 + w, -d, 0, z0, z0 + t, "wood", root, bevel=0.05)
    box(f"{name}_top", x0, x0 + w, -d, 0, z0 + h - t, z0 + h, "wood", root, bevel=0.05)
    box(f"{name}_left", x0, x0 + t, -d, 0, z0 + t, z0 + h - t, "wood", root, bevel=0.05)
    box(f"{name}_right", x0 + w - t, x0 + w, -d, 0, z0 + t, z0 + h - t, "wood", root, bevel=0.05)
    if prop == "towel":
        cylinder(f"{name}_towel", 1.8, w - 2.5, "towel", (x0 + w / 2, -d / 2, z0 + t + 1.8),
                 rot=(0, math.pi / 2, 0), parent=root)
    elif prop == "plant":
        cylinder(f"{name}_pot", 1.6, 3.0, "pot", (x0 + w / 2, -d / 2, z0 + t + 1.5), parent=root)
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=2.4 * IN)
        pl = mesh_obj(f"{name}_plant", bm, "leaves", root, smooth=True)
        pl.location = I(x0 + w / 2, -d / 2, z0 + t + 5.0)
    return root


# ---------------------------------------------------------------- outside
def black_walnut(tx, ty, gz, trunk_r):
    """A black walnut outside a window: the trunk and a few scaffold limbs (what shows through
    the glass). gz: ground height relative to the room floor."""
    rnd = random.Random(7)
    bark_material()
    leaf_material()
    tr = trunk_r
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=tr * IN, radius2=tr * 0.55 * IN, depth=260 * IN)
    trunk = mesh_obj("tree_trunk", bm, "bark", smooth=True)
    trunk.location = I(tx, ty, gz + 130)
    for k in range(3):
        ang = rnd.uniform(0, 2 * math.pi)
        z0 = rnd.uniform(160, 260)
        length = rnd.uniform(90, 150)
        lean = rnd.uniform(0.6, 1.0)
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=tr * 0.42 * IN, radius2=1.2 * IN, depth=length * IN)
        limb = mesh_obj("tree_limb", bm, "bark", smooth=True)
        d = Vector((math.cos(ang) * lean, math.sin(ang) * lean, 1.0)).normalized()
        limb.location = I(*(Vector((tx, ty, gz + z0)) + d * (length / 2)))
        limb.rotation_euler = d.to_track_quat("Z", "Y").to_euler()


def treeline(gz, x0=-900, x1=1100, y0=950, y1=1250, n=26, seed=11):
    """Distant tree line (soft green blobs) so the lawn doesn't run flat to the horizon."""
    principled("treeline", (0.05, 0.09, 0.035), 0.9)
    rnd = random.Random(seed)
    for k in range(n):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=rnd.uniform(140, 240) * IN)
        t = mesh_obj("treeline", bm, "treeline", smooth=True)
        t.location = I(rnd.uniform(x0, x1), rnd.uniform(y0, y1), gz + rnd.uniform(120, 220))
        t.scale = (1.3, 1, rnd.uniform(0.8, 1.2))


# ---------------------------------------------------------------- generic bath fixtures
# Sized from a dims dict so one part covers many products (spec sheet sizes in the room's
# layout.py). Wall fixtures use the usual local frame: wall at y=0, room toward -y.
def two_piece_toilet(name, x_wall, yc, rot_z, T):
    """Two-piece toilet, back against the wall at (x_wall, yc); rot_z turns local +x (forward)
    into the room (-pi/2: on a north wall). T: depth (overall, wall to bowl front), rim (rim
    height), tank_h (to the top of the lid), tank_w, tank_d, bowl_w, bowl_len (round about 17.5,
    elongated about 19.5), wall_gap (tank to wall), seat_up (show the seat and lid raised)."""
    _mat("lever", (0.85, 0.85, 0.85), 0.1, 1.0)
    root = empty(name, (x_wall, yc), rot_z)
    gap, d, rim = T.get("wall_gap", 1.25), T["depth"], T["rim"]
    td, tw = T["tank_d"], T["tank_w"]
    front = d - T["bowl_len"]                       # where the seat opening starts, from the wall
    back = gap + td - 3.0                           # the china runs back under the tank
    # base: a narrow pedestal under the bowl, then the bowl itself
    plan_prism(f"{name}_base", [(x + back + 1.5, y) for x, y in egg(d - back - 3.5, T["bowl_w"] / 2 - 2.2)],
               0, rim - 5.5, T.get("mat", "ceramic"), root)
    plan_prism(f"{name}_bowl", [(x + back, y) for x, y in egg(d - back, T["bowl_w"] / 2, n_back=3.0)],
               rim - 6.5, rim, T.get("mat", "ceramic"), root)
    # tank, standing on the back of the bowl, with its lid
    box(f"{name}_tank", gap, gap + td, -tw / 2, tw / 2, rim - 2, T["tank_h"] - 1.0, T.get("mat", "ceramic"), root, bevel=0.6)
    box(f"{name}_lid", gap - 0.3, gap + td + 0.3, -tw / 2 - 0.3, tw / 2 + 0.3, T["tank_h"] - 1.0, T["tank_h"],
        T.get("mat", "ceramic"), root, bevel=0.4)
    box(f"{name}_lever", gap + td - 0.2, gap + td + 0.8, tw / 2 - 3.5, tw / 2 - 1.0, T["tank_h"] - 3.3, T["tank_h"] - 2.6,
        "lever", root, bevel=0.15)
    seat_mat = T.get("seat_mat", T.get("mat", "ceramic"))
    if T.get("seat_up"):
        # seat and lid raised against the tank
        box(f"{name}_seat", gap + td + 0.2, gap + td + 1.2, -T["bowl_w"] / 2 + 0.5, T["bowl_w"] / 2 - 0.5,
            rim + 0.6, rim + T["bowl_len"] - 1, seat_mat, root, bevel=0.4)
    else:
        plan_prism(f"{name}_seat", [(x + front + 0.5, y) for x, y in egg(T["bowl_len"] - 0.5, T["bowl_w"] / 2 - 0.2, back_square=False)],
                   rim + 0.1, rim + 1.0, seat_mat, root)
        plan_prism(f"{name}_cover", [(x + front + 0.7, y) for x, y in egg(T["bowl_len"] - 1, T["bowl_w"] / 2 - 0.5, back_square=False)],
                   rim + 1.05, rim + 1.9, seat_mat, root)
    return root


def shaker_vanity(name, origin, rot_z, V):
    """Freestanding two-door shaker vanity with a one-piece top and integrated sink (the kind
    sold with a cultured-marble top). Local frame: wall at y=0, front toward -y, x 0..width.
    V: width, depth, height (to the top of the counter), top_t, kick (toe-kick height),
    paint (cabinet material), top (counter material), knob (hardware material)."""
    root = empty(name, origin, rot_z)
    w, d, h, tt, k = V["width"], V["depth"], V["height"], V["top_t"], V.get("kick", 3.5)
    cab_d = d - 1.0                                   # the top overhangs the doors by about an inch
    paint, knob = V.get("paint", "vanity_paint"), V.get("knob", "nickel")
    box(f"{name}_carcass", 0, w, -cab_d + 0.75, 0, k, h - tt, paint, root)
    # toe kick: recessed panel between two short side legs
    box(f"{name}_kick", 1.5, w - 1.5, -cab_d + 2.75, -2, 0, k, paint, root)
    for x0 in (0, w - 1.5):
        box(f"{name}_foot", x0, x0 + 1.5, -cab_d + 0.75, -1, 0, k, paint, root)
    # two shaker doors: flat frame around a recessed panel, a knob near the meeting edges
    rail, gap = 2.25, 0.125
    dw = (w - 3 * gap) / 2
    z0, z1 = k + 0.75, h - tt - 0.5
    for i in range(2):
        x0 = gap + i * (dw + gap)
        x1 = x0 + dw
        y0 = -cab_d
        box(f"{name}_door{i}_panel", x0 + rail, x1 - rail, y0 + 0.5, y0 + 0.75, z0 + rail, z1 - rail, paint, root)
        for (a, b, c, e) in ((x0, x1, z0, z0 + rail), (x0, x1, z1 - rail, z1),
                             (x0, x0 + rail, z0 + rail, z1 - rail), (x1 - rail, x1, z0 + rail, z1 - rail)):
            box(f"{name}_door{i}_frame", a, b, y0, y0 + 0.75, c, e, paint, root, bevel=0.06)
        kx = x1 - 1.6 if i == 0 else x0 + 1.6
        cylinder(f"{name}_knob{i}", 0.55, 1.1, knob, (kx, y0 - 0.55, z1 - 3.0), rot=(math.pi / 2, 0, 0), segs=24, parent=root)
    # counter with an integrated rectangular basin and a 4" centerset faucet deck
    top = box(f"{name}_top", -0.25, w + 0.25, -d, 0, h - tt, h, V.get("top", "vanity_top"), root, bevel=0.15)
    bw, bd = V.get("basin_w", min(19.0, w - 9)), V.get("basin_d", d - 7.5)
    bx0, by0 = w / 2 - bw / 2, -d + 2.25
    basin_cut = box(f"{name}_basincut", bx0, bx0 + bw, by0, by0 + bd, h - 5.5, h + 1, None, root, bevel=1.2)
    cut(top, basin_cut)
    top.modifiers.move(len(top.modifiers) - 1, 0)    # boolean before bevel
    box(f"{name}_basin", bx0 - 0.3, bx0 + bw + 0.3, by0 - 0.3, by0 + bd + 0.3, h - 5.8, h - 5.5,
        V.get("top", "vanity_top"), root)
    cylinder(f"{name}_drain", 0.8, 0.1, "chrome", (w / 2, by0 + bd / 2, h - 5.45), parent=root)
    return root


def centerset_faucet(name, origin, rot_z, z, F=None):
    """4" centerset bathroom faucet on a deck at height z: a low base plate, a curved spout from
    the middle, and one lever on top. Local frame: wall at y=0, room toward -y; origin is the
    faucet's center on the counter. F: spout_h, reach, mat."""
    F = F or {}
    root = empty(name, origin, rot_z)
    m = F.get("mat", "chrome")
    box(f"{name}_base", -3.0, 3.0, -1.1, 1.1, z, z + 0.9, m, root, bevel=0.45)
    sh, reach = F.get("spout_h", 4.5), F.get("reach", 4.5)
    cylinder(f"{name}_neck", 0.55, sh - 0.6, m, (0, 0, z + 0.9 + (sh - 0.6) / 2), parent=root)
    cylinder(f"{name}_spout", 0.45, reach, m, (0, -reach / 2, z + sh), rot=(math.pi / 2, 0, 0), parent=root)
    cylinder(f"{name}_tip", 0.5, 0.9, m, (0, -reach + 0.3, z + sh - 0.45), parent=root)
    box(f"{name}_lever", -0.35, 0.35, -0.2, 3.2, z + sh + 0.4, z + sh + 0.9, m, root, bevel=0.15)
    cylinder(f"{name}_cap", 0.65, 0.8, m, (0, 0, z + sh + 0.4), parent=root)
    return root


def wall_hung_sink(name, origin, rot_z, S):
    """Wall-hung lavatory: a deep rectangular china sink on a hanger, with a single-lever faucet
    and a chrome P-trap below. Local frame: wall at y=0, room toward -y, centered on x=0.
    S: width, depth, rim (rim height), thick (front apron height)."""
    root = empty(name, origin, rot_z)
    w, d, rim, t = S["width"], S["depth"], S["rim"], S.get("thick", 6.0)
    body = box(f"{name}_body", -w / 2, w / 2, -d, 0, rim - t, rim, "ceramic", root, bevel=0.9)
    bowl = box(f"{name}_bowlcut", -w / 2 + 2, w / 2 - 2, -d + 1.8, -4.5, rim - t + 1.2, rim + 1, None, root, bevel=1.5)
    cut(body, bowl)
    body.modifiers.move(len(body.modifiers) - 1, 0)
    box(f"{name}_back", -w / 2, w / 2, -4.5, 0, rim, rim + 1.6, "ceramic", root, bevel=0.5)   # faucet deck
    centerset_faucet(f"{name}_faucet", (0, -3.3), 0.0, rim + 1.6, dict(spout_h=3.8, reach=4.0)).parent = root
    cylinder(f"{name}_tail", 0.75, 8, "chrome", (0, -d / 2, rim - t - 4), parent=root)
    cylinder(f"{name}_arm", 0.75, d / 2, "chrome", (0, -d / 4, rim - t - 9), rot=(math.pi / 2, 0, 0), parent=root)
    return root


def alcove_tub(name, x0, x1, y0, y1, T=None):
    """Alcove bathtub filling the plan rectangle x0..x1, y0..y1, apron on the side that faces
    the room. T: height, wall (rim width), mat."""
    T = T or {}
    h, rw = T.get("height", 15.0), T.get("wall", 3.0)
    tub = box(name, x0, x1, y0, y1, 0, h, T.get("mat", "acrylic"), bevel=0.4)
    cut(tub, box(f"{name}_cut", x0 + rw, x1 - rw, y0 + rw + 2, y1 - rw, 2.0, h + 1, None, bevel=2.0))
    tub.modifiers.move(len(tub.modifiers) - 1, 0)
    return tub


def oval_mirror(name, origin, rot_z, M):
    """Frameless oval mirror on a wall, centered at x=0 of the local frame. M: width, height,
    center (height of its center), thick."""
    root = empty(name, origin, rot_z)
    w, h, t = M["width"], M["height"], M.get("thick", 0.25)
    m = cylinder(f"{name}_glass", w / 2, t, "mirror", (0, -t / 2 - 0.4, M["center"]), rot=(math.pi / 2, 0, 0), segs=96, parent=root)
    m.scale = (1, h / w, 1)
    m.data.polygons.foreach_set("use_smooth", [False] * len(m.data.polygons))   # flat glass, true reflection
    m["outline"] = "oval"     # the walkthrough draws its reflection as an oval, not a rectangle
    b = cylinder(f"{name}_mount", w / 2 - 1.5, 0.4, "mirror_back", (0, -0.2, M["center"]), rot=(math.pi / 2, 0, 0), segs=64, parent=root)
    b.scale = (1, (h - 3) / (w - 3), 1)
    return root


def medicine_cabinet(name, origin, rot_z, C):
    """Surface-mounted medicine cabinet: a shallow box with a mirror door. Local frame: wall at
    y=0, centered on x=0. C: width, height, depth, bottom."""
    root = empty(name, origin, rot_z)
    w, h, d, z0 = C["width"], C["height"], C["depth"], C["bottom"]
    box(f"{name}_box", -w / 2, w / 2, -d + 0.4, 0, z0, z0 + h, C.get("mat", "trim"), root, bevel=0.2)
    box(f"{name}_mirror", -w / 2 + 0.5, w / 2 - 0.5, -d, -d + 0.4, z0 + 0.5, z0 + h - 0.5, "mirror", root, bevel=0.15)
    return root


def towel_bar(name, origin, rot_z, length=24, z=40, mat="chrome"):
    """Straight towel bar: two posts and a round bar, centered at x=0 of the local frame."""
    root = empty(name, origin, rot_z)
    for sx in (-1, 1):
        box(f"{name}_post", sx * length / 2 - 0.6, sx * length / 2 + 0.6, -2.6, 0, z - 0.9, z + 0.9, mat, root, bevel=0.2)
    cylinder(f"{name}_bar", 0.35, length, mat, (0, -2.2, z), rot=(0, math.pi / 2, 0), parent=root)
    return root


def tub_shower_trim(name, origin, rot_z, valve_z=30, spout_z=19, head_z=80, T=None):
    """Tub and shower trim on the plumbing wall: a round escutcheon with one lever, a tub spout
    with a pull-up diverter below it, and a shower arm and head above. Local frame: wall at
    y=0, room toward -y, centered on x=0. T: escutcheon (diameter), spout_len, spout_h, arm
    (horizontal length), head (diameter), mat. Defaults are a typical single-handle set."""
    T = T or {}
    m = T.get("mat", "chrome")
    root = empty(name, origin, rot_z)
    er = T.get("escutcheon", 7.0) / 2
    cylinder(f"{name}_escutcheon", er, 0.5, m, (0, -0.25, valve_z), rot=(math.pi / 2, 0, 0), segs=48, parent=root)
    cylinder(f"{name}_hub", 0.8, 1.4, m, (0, -1.2, valve_z), rot=(math.pi / 2, 0, 0), parent=root)
    box(f"{name}_lever", -0.4, 0.4, -2.3, -1.5, valve_z - 0.4, valve_z + 3.8, m, root, bevel=0.2)
    sl, sh = T.get("spout_len", 5.4), T.get("spout_h", 2.4)
    cylinder(f"{name}_spout_flange", 1.2, 0.5, m, (0, -0.25, spout_z), rot=(math.pi / 2, 0, 0), parent=root)
    box(f"{name}_spout", -0.9, 0.9, -sl, -0.4, spout_z - sh / 2, spout_z + sh / 2, m, root, bevel=0.7)
    cylinder(f"{name}_diverter", 0.3, 0.9, m, (0, -sl + 0.9, spout_z + sh / 2 + 0.4), parent=root)
    arm = T.get("arm", 5.5)
    cylinder(f"{name}_arm_flange", 1.2, 0.4, m, (0, -0.2, head_z), rot=(math.pi / 2, 0, 0), parent=root)
    cylinder(f"{name}_arm", 0.42, arm, m, (0, -arm / 2, head_z), rot=(math.pi / 2, 0, 0), parent=root)
    hr = T.get("head", 2.5) / 2
    cylinder(f"{name}_head", hr, 1.6, m, (0, -arm - 0.4, head_z - 0.9), rot=(math.radians(60), 0, 0), segs=40,
             parent=root)
    return root


def shower_curtain(name, x, y0, y1, z0, z1, folds=9, mat="curtain"):
    """Shower curtain hanging in a plane x = const from y0 to y1 (bunched: short span, many
    folds), with a chrome rod above it running the tub's length."""
    bm = bmesh.new()
    n = folds * 8
    top, bot = [], []
    for i in range(n + 1):
        t = i / n
        y = y0 + (y1 - y0) * t
        dx = 1.2 * math.sin(t * folds * 2 * math.pi)
        bot.append(bm.verts.new(((x + dx) * IN, y * IN, z0 * IN)))
        top.append(bm.verts.new(((x + dx) * IN, y * IN, z1 * IN)))
    for i in range(n):
        bm.faces.new((bot[i], bot[i + 1], top[i + 1], top[i]))
    ob = mesh_obj(name, bm, mat, smooth=True)
    ob.modifiers.new("solid", "SOLIDIFY").thickness = 0.08 * IN
    return ob
