"""Real trim: profiles swept along a path, and turned parts. Inches, like layout.py.

A profile is [(w, d), ...]: w across the trim, d out from the surface it's fixed to. Both ends sit at
d = 0, so the back closes against the wall. These are common shapes; adjust one to match a crop of the
room's own trim, or pass your own list.
"""
import math

import bmesh

from roomkit.core import IN, mesh_obj


def ogee(w0, w1, d0, d1, n=6):
    """An S-curve from (w0, d0) to (w1, d1), excluding the start point."""
    out = []
    for k in range(1, n + 1):
        t = k / n
        s = t * t * (3 - 2 * t)
        out.append((w0 + (w1 - w0) * t, d0 + (d1 - d0) * s))
    return out


def bead(w0, w1, d, h, n=6):
    """A half-round from (w0, d) to (w1, d), rising h, excluding the start point."""
    return [(w0 + (w1 - w0) * (1 - math.cos(math.pi * k / n)) / 2, d + h * math.sin(math.pi * k / n)) for k in range(1, n + 1)]


def casing(w):
    """Colonial casing: flat at the opening (w = 0), ogee up to a back band at the outer edge."""
    return [(0, 0), (0, 0.5), (w * 0.45, 0.56), *ogee(w * 0.45, w * 0.68, 0.56, 0.72),
            *bead(w * 0.68, w * 0.84, 0.72, 0.1), (w * 0.88, 0.86), (w, 0.86), (w, 0)]


def panel_mold(w):
    """Applied panel molding: the ogee drops into the panel."""
    return [(0, 0), (0, 0.08), *ogee(0, w * 0.65, 0.08, 0.42), *bead(w * 0.65, w, 0.42, 0.08, 4), (w, 0)]


def chair_cap(h=2.0):
    """The wainscot's cap: a bed mold under a rounded nose."""
    return [(0, 0), *ogee(0, h * 0.42, 0, 0.55, 4), (h * 0.46, 0.5), *bead(h * 0.46, h, 0.82, 0.36), (h, 0)]


def base(h=4.5):
    """Base: tall flat with a small ogee cap."""
    return [(0, 0), (0, 0.72), (h * 0.76, 0.72), *ogee(h * 0.76, h, 0.72, 0.1, 5), (h, 0)]


def crown(h=3.6, out=2.2):
    """The hutch crown: fascia, cove, then a square lip."""
    return [(0, 0), (0, 0.45), (h * 0.22, 0.45), (h * 0.24, 0.72),
            *[(h * (0.24 + 0.52 * t), 0.72 + (out - 0.85 - 0.72) * (1 - math.cos(t * math.pi / 2))) for t in (0.17, 0.33, 0.5, 0.67, 0.83, 1.0)],
            (h * 0.78, out - 0.55), *bead(h * 0.78, h * 0.88, out - 0.55, 0.12, 3), (h * 0.9, out), (h, out), (h, 0)]


def nosing(h=1.5):
    """Counter edge: thumbnail over a small cove."""
    return [(0, 0), *ogee(0, h * 0.3, 0, 0.4, 3), (h * 0.34, 0.55), *bead(h * 0.34, h, 0.55, 0.32), (h, 0)]


def _offsets(path, closed):
    """Left normal at each path point, scaled so the offset stays parallel through a miter."""
    n = len(path)
    out = []
    for i in range(n):
        a = path[(i - 1) % n] if closed or i > 0 else None
        b = path[(i + 1) % n] if closed or i < n - 1 else None
        p = path[i]
        d0 = (p[0] - a[0], p[1] - a[1]) if a else None
        d1 = (b[0] - p[0], b[1] - p[1]) if b else None
        d0 = d0 or d1
        d1 = d1 or d0
        l0, l1 = math.hypot(*d0), math.hypot(*d1)
        n0 = (-d0[1] / l0, d0[0] / l0)
        n1 = (-d1[1] / l1, d1[0] / l1)
        mx, my = n0[0] + n1[0], n0[1] + n1[1]
        ml = math.hypot(mx, my)
        mx, my = mx / ml, my / ml
        k = 1 / max(0.2, mx * n0[0] + my * n0[1])
        out.append((mx * k, my * k))
    return out


def sweep(name, path, profile, mapper, mat, closed=False):
    """Sweep profile along path, a polyline in a surface's plane. Trim grows to the path's left.

    mapper(u, v, d) gives plan inches. Sharp edges stay sharp; curved runs shade smooth.
    """
    bm = bmesh.new()
    rows = []
    normals = _offsets(path, closed)
    for p, m in zip(path, normals):
        rows.append([bm.verts.new([c * IN for c in mapper(p[0] + m[0] * w, p[1] + m[1] * w, d)]) for w, d in profile])
    n = len(profile)
    count = len(rows)
    for i in range(count if closed else count - 1):
        a, b = rows[i], rows[(i + 1) % count]
        for j in range(n):
            k = (j + 1) % n
            bm.faces.new((a[j], b[j], b[k], a[k]))
    if not closed:
        bm.faces.new(rows[0])
        bm.faces.new(rows[-1])
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], ngon_method="BEAUTY")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return finish(name, bm, mat)


def finish(name, bm, mat, sharp_deg=32):
    bm.normal_update()
    limit = math.radians(sharp_deg)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > limit:
            e.smooth = False
    return mesh_obj(name, bm, mat)


def plan_sweep(name, pts, z0, profile, mat):
    """Sweep around a plan polyline, horizontally: w is up from z0, d goes to the path's left."""
    bm = bmesh.new()
    rows = []
    for p, m in zip(pts, _offsets(pts, False)):
        rows.append([bm.verts.new(((p[0] + m[0] * d) * IN, (p[1] + m[1] * d) * IN, (z0 + w) * IN)) for w, d in profile])
    n = len(profile)
    for a, b in zip(rows, rows[1:]):
        for j in range(n):
            k = (j + 1) % n
            bm.faces.new((a[j], b[j], b[k], a[k]))
    bm.faces.new(rows[0])
    bm.faces.new(rows[-1])
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], ngon_method="BEAUTY")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return finish(name, bm, mat)


def rect_inner(u0, u1, v0, v1, w):
    """Clockwise path inset by w from a rectangle, so a swept trim's outer edge lands on the rectangle."""
    return [(u0 + w, v0 + w), (u0 + w, v1 - w), (u1 - w, v1 - w), (u1 - w, v0 + w)]


def arc_path(cx, cz, r, a0, a1, n=32):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


def lathe(name, pts, loc, axis, mat, segs=32):
    """Turn a (radius, along) outline about an axis through loc. axis is 'x', 'y' or 'z'; along runs in its + direction."""
    bm = bmesh.new()
    rows = []
    for r, a in pts:
        row = []
        for k in range(segs):
            t = 2 * math.pi * k / segs
            c, s = r * math.cos(t), r * math.sin(t)
            v = {"x": (a, c, s), "y": (c, a, s), "z": (c, s, a)}[axis]
            row.append(bm.verts.new(((loc[0] + v[0]) * IN, (loc[1] + v[1]) * IN, (loc[2] + v[2]) * IN)))
        rows.append(row)
    for a, b in zip(rows, rows[1:]):
        for k in range(segs):
            j = (k + 1) % segs
            bm.faces.new((a[k], a[j], b[j], b[k]))
    if pts[0][0] > 1e-4:
        bm.faces.new(rows[0])
    if pts[-1][0] > 1e-4:
        bm.faces.new(rows[-1])
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return finish(name, bm, mat, sharp_deg=40)
