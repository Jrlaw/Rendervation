"""Generic kitchen parts: cabinet runs (base and wall), counters, a drop-in sink and faucets, and
the usual appliances (range, refrigerator, dishwasher, over-the-range microwave), plus ceiling
fixtures. A specific product goes in the person's catalog; these take its sizes as arguments.

Everything along a wall uses the parts.py frame: wall at y=0, room toward -y, x along the wall
(from the left as you face it), rot_z turning it onto the wall. Inches throughout.

Base fronts, as (width, kind) from x0: "door_l" / "door_r" (hinged on that side), "doors2",
"drawer_door" (a drawer over a door), "drawer_doors2", "drawers3", "sink" (false front over
two doors), "filler", "gap" (open: an appliance stands there; no box either).
Wall fronts: "door_l", "door_r", "doors2", "flap" (one lift-up door, its pull centered at the bottom),
"filler", "gap".
Door styles: "slab" (flat, eased edges: the 1950s-60s look), "shaker" (frame and flat panel).
Pulls: "wire" (a bent-wire bow pull), "knob", "bar", or None.
"""
import math

import bpy

from . import core
from .core import I, IN, box, cylinder, empty, link
from .materials import emission, principled

BASE_D = 24.0        # base carcass depth, without the doors
WALL_D = 12.0        # wall cabinet depth
KICK = 4.0           # toe kick height
KICK_SET = 3.0       # toe kick set back
FRONT_T = 0.75
KNOB_INSET = 1.6     # door pulls, edge to center; a room can set the stile's center (SEKTION shaker: 1 1/8")


def _mat(name, *args, **kw):
    if name not in core.MATS:
        principled(name, *args, **kw)


def appliance_materials():
    """Steel, black glass, enamel and the like, made the first time a part asks."""
    _mat("steel", (0.62, 0.62, 0.61), 0.28, 1.0)
    _mat("black_steel", (0.10, 0.10, 0.10), 0.3, 0.6)
    _mat("black_glass", (0.01, 0.01, 0.012), 0.04, **{"Coat Weight": 0.6})
    _mat("enamel_white", (0.86, 0.86, 0.84), 0.2, **{"Coat Weight": 0.4})
    _mat("enamel_black", (0.03, 0.03, 0.03), 0.25)
    _mat("rubber", (0.02, 0.02, 0.02), 0.8)
    _mat("display", (0.02, 0.06, 0.10), 0.2)


# ---------------------------------------------------------------- fronts
def pull(name, root, kind, x, z, yf, horizontal, mat, length=None):
    """A pull centered at (x, z) on the front whose face is at local y = yf - FRONT_T."""
    y = yf - FRONT_T
    if kind == "knob":
        cylinder(f"{name}_post", 0.25, 0.8, mat, (x, y - 0.4, z), rot=(math.pi / 2, 0, 0), segs=16, parent=root)
        cylinder(f"{name}_knob", 0.6, 0.45, mat, (x, y - 0.95, z), rot=(math.pi / 2, 0, 0), segs=24, parent=root)
    elif kind == "wire":      # a bent-wire bow: two feet and a bar standing 0.9" off the front
        L = length or 3.75
        a, b = (x - L / 2, x + L / 2) if horizontal else (z - L / 2, z + L / 2)
        for k, p in enumerate((a, b)):
            px, pz = (p, z) if horizontal else (x, p)
            box(f"{name}_foot{k}", px - 0.15, px + 0.15, y - 0.9, y, pz - 0.15, pz + 0.15, mat, root)
        if horizontal:
            box(f"{name}_bar", a, b, y - 1.05, y - 0.8, z - 0.14, z + 0.14, mat, root, bevel=0.06)
        else:
            box(f"{name}_bar", x - 0.14, x + 0.14, y - 1.05, y - 0.8, a, b, mat, root, bevel=0.06)
    elif kind == "bar":
        L = length or 6.3
        if horizontal:
            box(f"{name}_bar", x - L / 2, x + L / 2, y - 1.2, y - 0.85, z - 0.2, z + 0.2, mat, root, bevel=0.08)
            for k, px in enumerate((x - L / 2 + 0.4, x + L / 2 - 0.4)):
                box(f"{name}_foot{k}", px - 0.15, px + 0.15, y - 0.9, y, z - 0.15, z + 0.15, mat, root)
        else:
            box(f"{name}_bar", x - 0.2, x + 0.2, y - 1.2, y - 0.85, z - L / 2, z + L / 2, mat, root, bevel=0.08)
            for k, pz in enumerate((z - L / 2 + 0.4, z + L / 2 - 0.4)):
                box(f"{name}_foot{k}", x - 0.15, x + 0.15, y - 0.9, y, pz - 0.15, pz + 0.15, mat, root)


def front(name, root, x0, x1, z0, z1, yf, style, mat):
    """A door or drawer front from x0 to x1, z0 to z1, its back on the plane y = yf."""
    if style == "shaker":
        r = min(2.25, (x1 - x0) / 4, (z1 - z0) / 4)
        y0 = yf - FRONT_T
        box(f"{name}_panel", x0 + r - 0.1, x1 - r + 0.1, y0 + 0.25, yf, z0 + r - 0.1, z1 - r + 0.1, mat, root)
        box(f"{name}_stile_l", x0, x0 + r, y0, yf, z0, z1, mat, root, bevel=0.06)
        box(f"{name}_stile_r", x1 - r, x1, y0, yf, z0, z1, mat, root, bevel=0.06)
        box(f"{name}_rail_b", x0 + r, x1 - r, y0, yf, z0, z0 + r, mat, root, bevel=0.06)
        box(f"{name}_rail_t", x0 + r, x1 - r, y0, yf, z1 - r, z1, mat, root, bevel=0.06)
    else:
        box(name, x0, x1, yf - FRONT_T, yf, z0, z1, mat, root, bevel=0.15)


def _fronts(name, root, specs, x0, z0, z1, yf, style, mat, pull_kind, pull_mat, upper=False):
    """Lay out fronts [(width, kind)] from x0 between z0 and z1. Gaps of 1/8" between fronts."""
    g = 0.0625
    a = x0
    for i, (w, kind) in enumerate(specs):
        b = a + w
        nm = f"{name}_{i}"
        if kind == "filler":
            box(f"{nm}_fill", a, b, yf - FRONT_T, yf, z0, z1, mat, root)
        elif kind == "gap":
            pass
        else:
            drawer_h = 6.0
            rows = []          # (z0, z1, columns, is_drawer)
            if kind in ("drawer_door", "drawer_doors2", "sink"):
                rows = [(z1 - drawer_h, z1, 1, kind != "sink"), (z0, z1 - drawer_h, 2 if kind != "drawer_door" else 1, False)]
            elif kind == "drawers3":
                h = z1 - z0
                cuts = [z0, z0 + h * 0.42, z0 + h * 0.75, z1]
                rows = [(cuts[k], cuts[k + 1], 1, True) for k in range(3)]
            elif kind == "doors2":
                rows = [(z0, z1, 2, False)]
            elif kind == "flap":
                rows = [(z0, z1, 1, True)]
            else:
                rows = [(z0, z1, 1, False)]
            for r_, (ra, rb, n, drawer) in enumerate(rows):
                for c in range(n):
                    fa, fb = a + (b - a) * c / n + g, a + (b - a) * (c + 1) / n - g
                    fnm = f"{nm}_{r_}{c}"
                    if kind == "sink" and r_ == 0:     # false front: no pull
                        front(fnm, root, fa, fb, ra + g, rb - g, yf, style, mat)
                        continue
                    front(fnm, root, fa, fb, ra + g, rb - g, yf, style, mat)
                    if not pull_kind:
                        continue
                    if kind == "flap":
                        pull(f"{fnm}_pull", root, pull_kind, (fa + fb) / 2, ra + 1.5, yf, True, pull_mat)
                    elif drawer:
                        pull(f"{fnm}_pull", root, pull_kind, (fa + fb) / 2, rb - min(2.5, (rb - ra) / 2), yf, True, pull_mat)
                    else:
                        latch_right = (kind == "door_l") or (n == 2 and c == 0)
                        px = fb - KNOB_INSET if latch_right else fa + KNOB_INSET
                        pz = ra + 3.0 if upper else rb - 3.0
                        horizontal = pull_kind == "wire" and not upper and style == "slab"
                        pull(f"{fnm}_pull", root, pull_kind, px if not horizontal else (fa + fb) / 2 if (fb - fa) < 13 else px - (2.5 if latch_right else -2.5),
                             pz, yf, horizontal, pull_mat)
        a = b
    return a


def base_run(name, origin, rot_z, x0, specs, style="shaker", mat="cabinet", pull_kind="bar", pull_mat="nickel",
             depth=BASE_D, box_top=34.5, kick_mat="kick", sink_at=None):
    """Base cabinets along a wall: carcass, toe kick and fronts; "gap" leaves the floor open.
    sink_at: x of a sink's center, when its base isn't a "sink" kind, so its box is left open too.
    Returns the root (local frame) and x1, the run's end."""
    root = empty(name, origin, rot_z)
    a = x0
    for i, (w, kind) in enumerate(specs):
        if kind != "gap":
            # under a sink the box stops 10" down, so the bowls hang into open space
            top = box_top - 10 if kind == "sink" or (kind == "drawer_doors2" and sink_at is not None
                                                      and a <= sink_at <= a + w) else box_top
            box(f"{name}_box{i}", a, a + w, -depth, 0, KICK, top, mat, root)
            box(f"{name}_kick{i}", a, a + w, -depth + KICK_SET, 0, 0, KICK, kick_mat, root)
        a += w
    _fronts(name, root, specs, x0, KICK, box_top - 0.25, -depth, style, mat, pull_kind, pull_mat)
    return root, a


def wall_run(name, origin, rot_z, x0, specs, z0, z1, style="shaker", mat="cabinet", pull_kind="bar",
             pull_mat="nickel", depth=WALL_D, crown=False):
    """Wall cabinets from z0 to z1. crown: a simple crown at the top front."""
    root = empty(name, origin, rot_z)
    a = x0
    for i, (w, kind) in enumerate(specs):
        if kind != "gap":
            box(f"{name}_box{i}", a, a + w, -depth, 0, z0, z1, mat, root)
            if crown:
                box(f"{name}_crown{i}", a - (1.5 if i == 0 else 0), a + w + (1.5 if i == len(specs) - 1 else 0),
                    -depth - FRONT_T - 1.5, -0.5, z1, z1 + 2.5, mat, root, bevel=0.3)
        a += w
    _fronts(name, root, specs, x0, z0, z1, -depth, style, mat, pull_kind, pull_mat, upper=True)
    return root, a


def counter(name, root, x0, x1, depth=25.5, z=34.5, thick=1.5, mat="counter", splash=4.0, splash_mat=None,
            hole=None, ends=(True, True)):
    """A countertop on a run's root, from x0 to x1, its back at the wall, with a back splash (0: none).
    hole: (xa, xb, ya, yb) cut out for a drop-in sink (local, y negative). ends: exposed edges get a
    rounded nose (the laminate's bullnose)."""
    z1 = z + thick
    pieces = [(x0, x1, -depth, 0)]
    if hole:
        xa, xb, ya, yb = hole
        pieces = [(x0, xa, -depth, 0), (xb, x1, -depth, 0), (xa, xb, -depth, ya), (xa, xb, yb, 0)]
    for k, (a, b, c, d) in enumerate(pieces):
        if b - a > 0.01 and d - c > 0.01:
            box(f"{name}_{k}", a, b, c, d, z, z1, mat, root, bevel=0.2)
    box(f"{name}_nose", x0 + (0.0 if not ends[0] else 0.0), x1, -depth - 0.25, -depth + 0.5, z - 0.25, z1, mat, root, bevel=0.45)
    if splash:
        box(f"{name}_splash", x0, x1, -0.75, 0, z1, z1 + splash, splash_mat or mat, root, bevel=0.2)
    return z1


# ---------------------------------------------------------------- sink and faucets
def drop_in_sink(name, root, xc, yc, z_top, width=33, depth=22, bowls=2, bowl_d=8.0, mat="steel"):
    """A drop-in stainless sink: rim on the counter, bowls hanging below. (xc, yc): its center."""
    appliance_materials()
    x0, x1, y0, y1 = xc - width / 2, xc + width / 2, yc - depth / 2, yc + depth / 2
    rim = 1.25
    zt = z_top + 0.15
    box(f"{name}_rim_f", x0, x1, y0, y0 + rim, z_top, zt, mat, root, bevel=0.1)
    box(f"{name}_rim_b", x0, x1, y1 - rim - 1.5, y1, z_top, zt, mat, root, bevel=0.1)   # wider at the back: faucet deck
    box(f"{name}_rim_l", x0, x0 + rim, y0, y1, z_top, zt, mat, root, bevel=0.1)
    box(f"{name}_rim_r", x1 - rim, x1, y0, y1, z_top, zt, mat, root, bevel=0.1)
    inner = (x0 + rim, x1 - rim)
    by0, by1 = y0 + rim, y1 - rim - 1.5
    bw = (inner[1] - inner[0] - (bowls - 1) * 1.0) / bowls
    for k in range(bowls):
        a = inner[0] + k * (bw + 1.0)
        b = a + bw
        zb = zt - bowl_d
        t = 0.06
        box(f"{name}_b{k}_floor", a, b, by0, by1, zb, zb + t, mat, root)
        box(f"{name}_b{k}_wf", a, b, by0, by0 + t, zb, zt, mat, root)
        box(f"{name}_b{k}_wb", a, b, by1 - t, by1, zb, zt, mat, root)
        box(f"{name}_b{k}_wl", a, a + t, by0, by1, zb, zt, mat, root)
        box(f"{name}_b{k}_wr", b - t, b, by0, by1, zb, zt, mat, root)
        cylinder(f"{name}_b{k}_drain", 1.75, 0.1, "steel", ((a + b) / 2, (by0 + by1) / 2, zb + 0.08), segs=24, parent=root)
        if k:
            box(f"{name}_divide", a - 1.0, a, by0, by1, zt - 0.3, zt, mat, root, bevel=0.1)
    return zt


def kitchen_faucet(name, root, x, y, z, kind="pull_down", mat="nickel"):
    """A faucet on the deck at (x, y), z the deck top. kind: "pull_down" (tall gooseneck, one lever)
    or "two_handle" (a low spout between two handles, the 1960s-80s kind)."""
    if kind == "two_handle":
        box(f"{name}_base", x - 4, x + 4, y - 1.2, y + 1.2, z, z + 1.0, mat, root, bevel=0.4)
        cylinder(f"{name}_body", 0.9, 4.5, mat, (x, y, z + 3.2), segs=24, parent=root)
        # the spout reaches forward over the bowls
        sp = cylinder(f"{name}_spout", 0.45, 9, mat, (x, y - 4.5, z + 5.2), rot=(math.radians(90), 0, 0), segs=16, parent=root)
        sp.rotation_euler = (math.radians(80), 0, 0)
        for s in (-1, 1):
            cylinder(f"{name}_handle_{s}", 0.5, 2.0, mat, (x + s * 3.0, y, z + 2.0), segs=16, parent=root)
            box(f"{name}_lever_{s}", x + s * 3.0 - 0.3, x + s * 3.0 + 0.3, y - 2.2, y, z + 2.6, z + 3.1, mat, root, bevel=0.15)
        return
    cylinder(f"{name}_escutcheon", 1.4, 0.3, mat, (x, y, z + 0.15), segs=32, parent=root)
    cylinder(f"{name}_body", 0.75, 9, mat, (x, y, z + 4.8), segs=24, parent=root)
    # the gooseneck: a half circle forward from the top of the body, then the spray head down
    R, n, zc = 4.0, 12, z + 9.3
    for k in range(n):
        a0, a1 = math.pi * k / n, math.pi * (k + 1) / n
        p0 = (y - R + R * math.cos(a0), zc + R * math.sin(a0))
        p1 = (y - R + R * math.cos(a1), zc + R * math.sin(a1))
        mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
        seg = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        c = cylinder(f"{name}_neck{k}", 0.5, seg + 0.1, mat, (x, mid[0], mid[1]), segs=16, parent=root)
        c.rotation_euler = (math.pi / 2 - ang, 0, 0)
    cylinder(f"{name}_head", 0.75, 3.2, mat, (x, y - 2 * R, zc - 1.6), segs=24, parent=root)
    box(f"{name}_lever", x + 0.7, x + 3.4, y - 0.3, y + 0.3, z + 7.6, z + 8.1, mat, root, bevel=0.15)


# ---------------------------------------------------------------- appliances
def freestanding_range(name, origin, rot_z, x0, width=30, depth=27, mat="steel", doors=1, side_mat=None):
    """A freestanding electric range: glass cooktop, a back guard with the controls, oven door(s)
    with a window, a storage drawer (doors=1) or two oven doors (doors=2). Its back at the wall."""
    appliance_materials()
    root = empty(name, origin, rot_z)
    x1 = x0 + width
    side = side_mat or "black_steel"
    box(f"{name}_body", x0, x1, -depth + 1.0, -1.0, 0, 35.5, side, root)
    box(f"{name}_top", x0 + 0.1, x1 - 0.1, -depth + 0.6, -1.0, 35.5, 36.0, "black_glass", root, bevel=0.15)
    for k, (cx, cy, r) in enumerate(((x0 + 7.5, -depth + 7, 4.5), (x1 - 7.5, -depth + 7, 5.5),
                                     (x0 + 7.5, -9, 3.5), (x1 - 7.5, -9, 4.5))):
        cylinder(f"{name}_burner{k}", r, 0.02, "enamel_black", (cx, cy, 36.01), segs=40, parent=root)
    box(f"{name}_guard", x0, x1, -4.0, -1.0, 36.0, 43.5, mat, root, bevel=0.2)
    box(f"{name}_display", x0 + 9, x1 - 9, -4.05, -3.95, 39, 42, "display", root)
    for k, kx in enumerate((x0 + 2.5, x0 + 5.5, x1 - 5.5, x1 - 2.5)):
        cylinder(f"{name}_knob{k}", 1.0, 1.0, "black_steel", (kx, -4.5, 40.5), rot=(math.pi / 2, 0, 0), segs=24, parent=root)
    yf = -depth + 1.0
    if doors == 2:
        split = 20.5
        spans = [(split + 0.1, 35.0, "upper"), (5.0, split - 0.1, "lower")]
    else:
        spans = [(9.0, 35.0, "oven")]
        box(f"{name}_drawer", x0 + 0.2, x1 - 0.2, yf - 1.0, yf, 1.0, 8.8, mat, root, bevel=0.2)
        box(f"{name}_drawer_pull", x0 + 4, x1 - 4, yf - 1.8, yf - 1.0, 7.0, 7.6, mat, root, bevel=0.15)
    for k, (za, zb, _) in enumerate(spans):
        box(f"{name}_door{k}", x0 + 0.2, x1 - 0.2, yf - 1.2, yf, za, zb, mat, root, bevel=0.2)
        box(f"{name}_window{k}", x0 + 4, x1 - 4, yf - 1.25, yf - 1.15, za + 3.0, zb - 5.0, "black_glass", root)
        cylinder(f"{name}_handle{k}", 0.45, width - 6, mat, ((x0 + x1) / 2, yf - 2.6, zb - 2.0), rot=(0, math.pi / 2, 0), segs=16, parent=root)
        for s in (x0 + 3.5, x1 - 3.5):
            box(f"{name}_handle{k}_post{s:.0f}", s - 0.3, s + 0.3, yf - 2.6, yf - 1.2, zb - 2.3, zb - 1.7, mat, root)
    if doors == 2:
        box(f"{name}_kick", x0 + 0.5, x1 - 0.5, yf + 0.5, yf + 1.0, 0, 5.0, "rubber", root)
    return root


def refrigerator(name, origin, rot_z, x0, width=30, depth=31, height=66, kind="top_freezer", mat="enamel_white",
                 handle_mat=None, dispenser=False, handle="x0"):
    """A freestanding refrigerator, its back an inch off the wall. kind: "top_freezer" or
    "french_door" (two doors over a freezer drawer). handle: the top-freezer's handle side, "x0" or
    "x1" (the doors hinge on the other)."""
    appliance_materials()
    root = empty(name, origin, rot_z)
    x1 = x0 + width
    hm = handle_mat or mat
    body_d = depth - 2.0
    box(f"{name}_body", x0 + 0.2, x1 - 0.2, -1.0 - body_d, -1.0, 0.5, height, mat, root, bevel=0.6)
    yf = -1.0 - body_d
    if kind == "french_door":
        split = 0.36 * height
        box(f"{name}_drawer", x0 + 0.2, x1 - 0.2, yf - 2.0, yf, 1.5, split - 0.15, mat, root, bevel=0.5)
        box(f"{name}_drawer_handle", x0 + 5, x1 - 5, yf - 3.6, yf - 2.6, split - 3.0, split - 2.0, hm, root, bevel=0.3)
        mid = (x0 + x1) / 2
        for k, (a, b) in enumerate(((x0 + 0.2, mid - 0.1), (mid + 0.1, x1 - 0.2))):
            box(f"{name}_door{k}", a, b, yf - 2.0, yf, split + 0.15, height - 0.3, mat, root, bevel=0.5)
            hx = b - 1.6 if k == 0 else a + 1.6
            box(f"{name}_handle{k}", hx - 0.45, hx + 0.45, yf - 3.6, yf - 2.6, split + 6, split + 30, hm, root, bevel=0.3)
        if dispenser:
            box(f"{name}_dispenser", x0 + 4, mid - 4, yf - 2.1, yf - 1.9, split + 18, split + 32, "black_glass", root)
        return root
    split = height * 0.68
    box(f"{name}_fresh", x0 + 0.2, x1 - 0.2, yf - 2.0, yf, 1.5, split - 0.2, mat, root, bevel=0.5)
    box(f"{name}_freezer", x0 + 0.2, x1 - 0.2, yf - 2.0, yf, split + 0.2, height - 0.3, mat, root, bevel=0.5)
    hx = x0 + 1.6 if handle == "x0" else x1 - 1.6
    box(f"{name}_handle_f", hx - 0.5, hx + 0.5, yf - 3.4, yf - 2.0, split - 16, split - 4, hm, root, bevel=0.3)
    box(f"{name}_handle_z", hx - 0.5, hx + 0.5, yf - 3.4, yf - 2.0, split + 3, split + 11, hm, root, bevel=0.3)
    return root


def dishwasher(name, origin, rot_z, x0, width=24, mat="enamel_white", top=34.5, depth=BASE_D):
    """A built-in dishwasher under the counter: door with the controls on its top edge, a kick plate."""
    appliance_materials()
    root = empty(name, origin, rot_z)
    x1 = x0 + width
    box(f"{name}_tub", x0 + 0.1, x1 - 0.1, -depth + 0.5, -1.0, 4.0, top - 0.25, "steel", root)
    box(f"{name}_door", x0 + 0.1, x1 - 0.1, -depth - 0.75, -depth + 0.5, 4.0, top - 0.25, mat, root, bevel=0.25)
    box(f"{name}_panel", x0 + 0.6, x1 - 0.6, -depth - 0.8, -depth - 0.7, top - 4.5, top - 0.75, mat, root)
    box(f"{name}_handle", x0 + 6, x1 - 6, -depth - 1.6, -depth - 0.75, top - 4.0, top - 3.2, mat, root, bevel=0.15)
    box(f"{name}_kick", x0 + 0.1, x1 - 0.1, -depth + 2.0, -depth + 2.5, 0, 4.0, "rubber", root)
    return root


def otr_microwave(name, origin, rot_z, x0, z0, width=30, height=16.5, depth=15.5, mat="steel", side_mat="black_steel"):
    """An over-the-range microwave hung under a cabinet or on the wall, bottom at z0."""
    appliance_materials()
    root = empty(name, origin, rot_z)
    x1 = x0 + width
    box(f"{name}_body", x0, x1, -depth, 0, z0, z0 + height, side_mat, root, bevel=0.3)
    yf = -depth
    box(f"{name}_door", x0 + 0.3, x1 - 7.0, yf - 0.6, yf, z0 + 0.5, z0 + height - 0.5, mat, root, bevel=0.2)
    box(f"{name}_window", x0 + 2.5, x1 - 10.0, yf - 0.65, yf - 0.55, z0 + 3.0, z0 + height - 3.0, "black_glass", root)
    box(f"{name}_handle", x1 - 8.6, x1 - 7.6, yf - 2.2, yf - 0.6, z0 + 2.5, z0 + height - 2.5, mat, root, bevel=0.3)
    box(f"{name}_controls", x1 - 6.8, x1 - 0.3, yf - 0.6, yf, z0 + 0.5, z0 + height - 0.5, mat, root, bevel=0.2)
    box(f"{name}_pad", x1 - 6.0, x1 - 1.0, yf - 0.65, yf - 0.55, z0 + 4.0, z0 + height - 2.0, "black_glass", root)
    box(f"{name}_vent", x0 + 2, x1 - 2, yf + 0.5, yf + 2.5, z0 - 0.05, z0, "black_steel", root)
    return root


# ---------------------------------------------------------------- ceiling fixtures
def ceiling_fixture(name, x, y, kind="flush_drum", diameter=13.0, power=40.0, trim_mat="nickel"):
    """A ceiling light: "flush_drum" (a glass drum with a metal band), "flush_dome" (a frosted dome
    with a metal ring), "semi_flush" (a frosted bowl on a short stem), "led_disc" (a thin LED disk).
    Its point light is listed in scene.json for the walkthrough; evening dims it like the cans."""
    C = core.CEILING
    _mat("frosted", (0.95, 0.94, 0.92), 0.4, **{"Transmission Weight": 0.3})
    emission(f"{name}_glow", (1.0, 0.93, 0.82), 6.0 * core.CAN_DIM)
    r = diameter / 2
    drop = 2.0
    if kind == "flush_drum":
        cylinder(f"{name}_band", r + 0.15, 1.2, trim_mat, (x, y, C - 0.6), segs=48)
        cylinder(f"{name}_glass", r, 3.6, f"{name}_glow", (x, y, C - 3.0), segs=48)
        cylinder(f"{name}_cap", r - 0.8, 0.4, trim_mat, (x, y, C - 5.0), segs=48)
        drop = 5.3
    elif kind == "flush_dome":
        cylinder(f"{name}_ring", r + 0.3, 0.6, trim_mat, (x, y, C - 0.3), segs=48)
        dome = cylinder(f"{name}_dome", r, 4.0, f"{name}_glow", (x, y, C - 2.6), segs=48)
        dome.scale = (1, 1, 1)
        cylinder(f"{name}_finial", 0.6, 0.8, trim_mat, (x, y, C - 5.0), segs=16)
        drop = 5.0
    elif kind == "semi_flush":
        cylinder(f"{name}_canopy", 2.5, 1.0, trim_mat, (x, y, C - 0.5), segs=32)
        cylinder(f"{name}_stem", 0.25, 4.0, trim_mat, (x, y, C - 3.0), segs=12)
        cylinder(f"{name}_bowl", r, 2.2, f"{name}_glow", (x, y, C - 6.0), segs=48)
        cylinder(f"{name}_rim", r + 0.2, 0.3, trim_mat, (x, y, C - 4.9), segs=48)
        drop = 7.2
    else:   # led_disc
        cylinder(f"{name}_ring", r, 1.0, trim_mat, (x, y, C - 0.5), segs=48)
        cylinder(f"{name}_lens", r - 0.4, 0.1, f"{name}_glow", (x, y, C - 1.05), segs=48)
        drop = 1.1
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = power * core.CAN_DIM
    ld.color = (1.0, 0.88, 0.74)
    ld.shadow_soft_size = r * IN
    ob = bpy.data.objects.new(name, ld)
    ob.location = I(x, y, C - drop - 0.5)
    link(ob)
    core.LIGHTS.append(dict(name=name, x=x, y=y, z=C - drop - 0.5, power=power))
