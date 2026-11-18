"""Geometry check for a built room (./render.sh --check): the mistakes a render hides or a
person only spots later. Prints one line per problem and writes check.json next to room.py.

- opening: something (tile, a shelf, a fixture) crosses a door or window opening
- overlap: two things sit inside each other more than OVERLAP_MAX
- floating: something touches nothing (floor, ceiling, a wall or another object)

Shared parts and room code both stay unaware of it: it looks only at the finished scene.
"""
import json
import os

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from . import core
from .core import IN

OVERLAP_MAX = 0.5    # inches two things may sit inside each other (a vanity tight to its tile)
SUPPORT_GAP = 1.0    # inches from something else that still counts as resting on or fixed to it
# name prefixes allowed inside an opening: the opening's own trim, glass and door
IN_OPENING = ("window", "case_", "door", "threshold", "curtain")


def _mesh(objs, depsgraph):
    """World-space vertices (inches) and faces of evaluated objects (booleans and bevels
    applied), all together, plus a BVH of each closed one for inside tests."""
    verts, faces, solids = [], [], []
    to_in = Matrix.Scale(1 / IN, 4)
    for o in objs:
        ev = o.evaluated_get(depsgraph)
        me = ev.to_mesh()
        m = to_in @ o.matrix_world
        vs = [m @ v.co for v in me.vertices]
        fs = [list(p.vertices) for p in me.polygons]
        uses = {}
        for f in fs:
            for e in zip(f, f[1:] + f[:1]):
                k = tuple(sorted(e))
                uses[k] = uses.get(k, 0) + 1
        if fs and all(u == 2 for u in uses.values()):     # closed: inside and outside make sense
            solids.append(BVHTree.FromPolygons(vs, fs))
        n = len(verts)
        verts += vs
        faces += [[n + i for i in f] for f in fs]
        ev.to_mesh_clear()
    return verts, faces, solids


def _box(lo, hi):
    """BVH of an axis-aligned box (inches)."""
    v = [Vector((hi[0] if i & 1 else lo[0], hi[1] if i & 2 else lo[1], hi[2] if i & 4 else lo[2])) for i in range(8)]
    return BVHTree.FromPolygons(v, [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])


RAY = Vector((0.123, 0.271, 0.954)).normalized()   # off-axis, so it doesn't run along an edge


def _inside(bvh, p, reach):
    """Depth of point p inside the closed surface in bvh: odd ray crossings mean inside; the
    depth is the distance to the nearest surface (0 if outside)."""
    hit = bvh.find_nearest(p, reach)
    if hit[0] is None:
        return 0.0
    crossings, o = 0, p
    while True:
        loc = bvh.ray_cast(o, RAY)[0]
        if loc is None:
            break
        crossings += 1
        o = loc + RAY * 1e-3
    return hit[3] if crossings % 2 else 0.0


def family(name):
    """A fixture's parts share a name stem: tp_post and tp_roll, vanity_bar_cup_-8 and
    vanity_bar_plate, can_1_lens and can_2_trim."""
    def num(t):
        return t.lstrip("-").isdigit()
    t = name.split("_")
    while len(t) > 1 and num(t[-1]):
        t.pop()
    if len(t) > 1:
        t.pop()
    while len(t) > 1 and num(t[-1]):
        t.pop()
    return "_".join(t)


def _bounds(o):
    """World-space box of an object (inches)."""
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [min(p[i] for p in pts) / IN for i in range(3)], [max(p[i] for p in pts) / IN for i in range(3)]


def _clusters(objs):
    """Split one name stem's meshes into pieces whose boxes come within SUPPORT_GAP of each
    other, so two switches on different walls (switch_stair, switch_kitchen) are two fixtures,
    not one that hides the floating one. Largest first."""
    b = [_bounds(o) for o in objs]
    parent = list(range(len(objs)))

    def top(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(objs)):
        for j in range(i + 1, len(objs)):
            if all(b[i][0][k] - SUPPORT_GAP <= b[j][1][k] and b[j][0][k] - SUPPORT_GAP <= b[i][1][k] for k in range(3)):
                parent[top(i)] = top(j)
    out = {}
    for i, o in enumerate(objs):
        out.setdefault(top(i), []).append(o)
    return sorted(out.values(), key=len, reverse=True)


def groups():
    """Visible meshes grouped into fixtures: by top-level parent, then by name stem, then split
    where a stem's parts don't touch. The largest piece keeps the stem's name; the others are
    named after their first top-level object."""
    stems, roots = {}, {}
    for o in core.scene.objects:
        if o.type != "MESH" or o.hide_render:
            continue
        root = o
        while root.parent:
            root = root.parent
        stems.setdefault(family(root.name), []).append(o)
        roots[o] = root.name
    out = {}
    for stem, objs in stems.items():
        for n, part in enumerate(_clusters(objs)):
            key = stem if n == 0 else min(roots[o] for o in part)
            while key in out or (n and key in stems):
                key += "+"
            out[key] = part
    return out


def openings():
    """Door and window cutters: wall cutters taller than a foot (short ones trim a baseboard)."""
    out = []
    for o in core.scene.objects:
        if o.get("opening") and o.dimensions.z / IN > 12:
            lo = [min((o.matrix_world @ Vector(c))[i] for c in o.bound_box) / IN for i in range(3)]
            hi = [max((o.matrix_world @ Vector(c))[i] for c in o.bound_box) / IN for i in range(3)]
            out.append((o.name.replace("cut_", ""), lo, hi))
    return out


def run(ignore=()):
    """Check the scene; ignore: extra name prefixes to leave out (a room's deliberate overlaps)."""
    dg = bpy.context.evaluated_depsgraph_get()
    G = {k: v for k, v in groups().items() if not k.startswith(tuple(ignore))}
    mesh = {k: _mesh(v, dg) for k, v in G.items()}
    bvh = {k: BVHTree.FromPolygons(m[0], m[1]) for k, m in mesh.items() if m[0]}
    box = {k: ([min(v[i] for v in m[0]) for i in range(3)], [max(v[i] for v in m[0]) for i in range(3)])
           for k, m in mesh.items() if m[0]}
    floor = box.get("floor")
    room_lo, room_hi = (floor if floor else ([-1e9] * 3, [1e9] * 3))
    ceiling = core.CEILING
    problems = []

    def in_room(k):
        lo, hi = box[k]
        return all(lo[i] < room_hi[i] - 0.1 and hi[i] > room_lo[i] + 0.1 for i in (0, 1))

    # openings: anything else crossing a door or window (shrunk 1/4" so trim at the edge passes)
    for name, lo, hi in openings():
        lo = [lo[0] + 0.25, lo[1] + 0.25, lo[2] + 0.25]
        hi = [hi[0] - 0.25, hi[1] - 0.25, hi[2] - 0.25]
        tunnel = _box(lo, hi)
        for k in box:
            if k.startswith(IN_OPENING) or any(m.type == "BOOLEAN" and m.object and m.object.name == "cut_" + name
                                               for o in G[k] for m in o.modifiers):
                continue            # the opening's own trim and door, and whatever it's cut through
            blo, bhi = box[k]
            if any(bhi[i] <= lo[i] or blo[i] >= hi[i] for i in range(3)):
                continue
            hits = bvh[k].overlap(tunnel)
            inside = any(all(lo[i] < v[i] < hi[i] for i in range(3)) for v in mesh[k][0])
            if hits or inside:
                problems.append(dict(kind="opening", what=k, where=name,
                                     note=f"{k} crosses the {name} opening"))

    # overlaps: one thing inside another, deeper than OVERLAP_MAX
    keys = [k for k in box if in_room(k)]
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            alo, ahi = box[a]
            blo, bhi = box[b]
            if any(min(ahi[j], bhi[j]) - max(alo[j], blo[j]) <= OVERLAP_MAX for j in range(3)):
                continue
            depth, at = 0.0, None
            for x, y in ((a, b), (b, a)):
                verts = mesh[x][0]
                for v in verts[::max(1, len(verts) // 400)]:
                    d = max((_inside(b, v, 24.0) for b in mesh[y][2]), default=0.0)
                    if d > depth:
                        depth, at = d, v
            if depth > OVERLAP_MAX:
                at = [round(c, 1) for c in at]
                problems.append(dict(kind="overlap", what=a, where=b, depth=round(depth, 2), at=at,
                                     note=f"{a} and {b} sit {depth:.1f}\" inside each other, deepest at {tuple(at)}"))

    # floating: touches nothing at all
    for k in keys:
        lo, hi = box[k]
        if lo[2] <= 0.5 or hi[2] >= ceiling - 0.5:
            continue
        verts = mesh[k][0][::max(1, len(mesh[k][0]) // 200)]
        near = any(bvh[o].find_nearest(v, SUPPORT_GAP)[0] is not None for o in box if o != k for v in verts)
        if not near:
            problems.append(dict(kind="floating", what=k, z=round(lo[2], 1),
                                 note=f"{k} touches nothing (bottom at {lo[2]:.1f}\")"))

    for p in problems:
        print("CHECK", p["kind"], "|", p["note"])
    print(f"CHECK done: {len(problems)} problem(s), {len(keys)} objects in the room")
    with open(os.path.join(core.ROOM_DIR, "check.json"), "w") as f:
        json.dump(dict(problems=problems, objects={k: dict(min=[round(x, 2) for x in box[k][0]],
                                                             max=[round(x, 2) for x in box[k][1]])
                                                     for k in keys}), f, indent=1)
    return problems
