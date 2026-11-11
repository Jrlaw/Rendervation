"""Scene setup, geometry helpers, cameras, render and web export shared by every room.

A room script (houses/<house>/rooms/<room>/room.py) calls start(), builds its walls and
fixtures with these helpers, then finish(). Units: room layouts are in inches; I() and IN
convert to Blender meters.

Command-line options read here (after Blender's `--`): --cams a,b,c  --samples N  --res N
--out DIR  --night  --hero  --export DIR  --save  --cpu  --bake [PX]  --bake-samples N.
Rooms read their own options with arg().
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

IN = 0.0254


def I(*v):
    return [x * IN for x in v]


# ---------------------------------------------------------------- args
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    if name in argv:
        return argv[argv.index(name) + 1]
    return default


SAMPLES = int(arg("--samples", "128"))
RES = int(arg("--res", "1600"))
SAVE = "--save" in argv
CHECK = "--check" in argv          # build the room, run roomkit.check and stop (no render)
EXPORT = arg("--export", "")      # directory: write model.glb + scene.json + bundle.js, skip rendering
# --bake: with --export, bake the Cycles lighting into one texture atlas (out/textures/bake.jpg)
# so the walkthrough looks like the renders; PX is the atlas size (default 8192)
BAKE = "--bake" in argv
BAKE_PX = int(argv[argv.index("--bake") + 1]) if BAKE and argv.index("--bake") + 1 < len(argv) \
    and argv[argv.index("--bake") + 1].isdigit() else 8192
BAKE_SAMPLES = int(arg("--bake-samples", "96"))
# left live in the walkthrough (view-dependent reflections, transparency); everything else is baked
BAKE_SKIP = ("glass", "window_glass", "chrome", "nickel", "steel", "mirror", "leaves", "black_glass", "brass",
             "acrylic")   # the tub: a curved shell baked in pieces shows their seams as cracks
NIGHT = "--night" in argv         # evening: room lights dimmed, dark sky, no sun
# hero: lit like a real-estate photo. Daylight does the work (brighter sky and sun, so the
# window is the brightest thing in the shot and light falls off across the room), the cans are
# turned way down, and the exposure is set for the daylit room. Tune with the factors below.
HERO = "--hero" in argv and not NIGHT
HERO_SKY = float(arg("--hero-sky", "2.5"))       # sky strength x
HERO_SUN = float(arg("--hero-sun", "1.6"))       # sun energy x
HERO_CANS = float(arg("--hero-cans", "0.15"))    # can power x
HERO_EXPOSURE = float(arg("--hero-exposure", "1.2"))   # stops, on top of AgX
CAN_DIM = 0.35 if NIGHT else HERO_CANS if HERO else 1.0   # room-light factor for cans and their lenses

# set by start()
ROOM_DIR = TEX = OUT = ""
CEILING = 96.0
scene = COL = None
MATS = {}
LIGHTS = []
CAM_DATA = {}
CAMERAS = {}


def start(room_file, ceiling):
    """Empty scene for the room whose script is room_file; textures come from its textures/."""
    global ROOM_DIR, TEX, OUT, CEILING, scene, COL
    ROOM_DIR = os.path.dirname(os.path.abspath(room_file))
    TEX = os.path.join(ROOM_DIR, "textures")
    OUT = arg("--out", os.path.join(ROOM_DIR, "renders"))
    CEILING = ceiling
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "IMPERIAL"
    COL = scene.collection
    return scene


def link(obj, parent=None):
    COL.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def empty(name, origin=(0, 0), rot_z=0.0):
    """Parent for a fixture built in its own local frame (inches), placed at origin."""
    root = bpy.data.objects.new(name, None)
    link(root)
    root.location = I(*origin, 0)
    root.rotation_euler = (0, 0, rot_z)
    return root


# ---------------------------------------------------------------- geometry helpers
def mesh_obj(name, bm, mat, parent=None, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    if mat:
        ob.data.materials.append(MATS[mat] if isinstance(mat, str) else mat)
    return link(ob, parent)


def box(name, x0, x1, y0, y1, z0, z1, mat, parent=None, bevel=0.0):
    """Axis-aligned box from inch extents (in parent space if parented)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = (x0 if v.co.x < 0 else x1) * IN
        v.co.y = (y0 if v.co.y < 0 else y1) * IN
        v.co.z = (z0 if v.co.z < 0 else z1) * IN
    ob = mesh_obj(name, bm, mat, parent)
    if bevel:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = bevel * IN
        mod.segments = 2
        mod.limit_method = "ANGLE"
    return ob


def outward(bm):
    """Point a closed mesh's faces outward. recalc_face_normals alone can turn a thin concave
    slab inside out (the kitchen's 0.4" tile floor came out top-down), which renders hide but
    a bake doesn't: it lights the side a face points to, so the top bakes black. A negative
    signed volume means inside out: flip every face."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    vol = 0.0
    for f in bm.faces:
        v = [lp.vert.co for lp in f.loops]
        for i in range(1, len(v) - 1):
            vol += v[0].dot(v[i].cross(v[i + 1]))
    if vol < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)


def prism(name, pts, z0, z1, mat, parent=None):
    """Vertical prism from a CCW-or-CW polygon of inch (x, y) points."""
    bm = bmesh.new()
    bot = [bm.verts.new((x * IN, y * IN, z0 * IN)) for x, y in pts]
    top = [bm.verts.new((x * IN, y * IN, z1 * IN)) for x, y in pts]
    bm.faces.new(bot)
    bm.faces.new(top)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    # explicit ear-clip triangulation: concave caps (the room outline) otherwise lose a triangle
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], ngon_method="EAR_CLIP")
    outward(bm)
    return mesh_obj(name, bm, mat, parent)


def cylinder(name, r, depth, mat, loc, rot=(0, 0, 0), segs=32, parent=None):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r * IN, radius2=r * IN, depth=depth * IN)
    ob = mesh_obj(name, bm, mat, parent, smooth=True)
    ob.location = I(*loc)
    ob.rotation_euler = rot
    return ob


def cutter_box(name, x0, x1, y0, y1, z0, z1):
    return box(name, x0, x1, y0, y1, z0, z1, None)


def cut(target, cutter):
    """Boolean-difference cutter out of target; cutter is hidden from renders."""
    mod = target.modifiers.new("cut_" + cutter.name, "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    mod.solver = "MANIFOLD" if "MANIFOLD" in [i.identifier for i in mod.bl_rna.properties["solver"].enum_items] else "EXACT"
    cutter.hide_render = True
    cutter.display_type = "WIRE"


def wall_run(name, pts, thick, z0, z1, mat, closed=False):
    """One mitered solid along an inch polyline, built on the LEFT of travel
    (the outside of a clockwise outline). A single mesh with no overlapping
    pieces: coplanar overlaps render as black streaks in Cycles."""
    pts = [Vector(p) for p in pts]
    n = len(pts)

    def left(a, b):
        d = (b - a).normalized()
        return Vector((-d.y, d.x))

    off = []
    for i, p in enumerate(pts):
        prev_n = left(pts[i - 1], p) if (closed or i > 0) else None
        next_n = left(p, pts[(i + 1) % n]) if (closed or i < n - 1) else None
        if prev_n is None or next_n is None:
            off.append(p + (prev_n or next_n) * thick)
            continue
        m = (prev_n + next_n).normalized()
        off.append(p + m * (thick / m.dot(next_n)))
    bm = bmesh.new()
    lo_in = [bm.verts.new((p.x * IN, p.y * IN, z0 * IN)) for p in pts]
    hi_in = [bm.verts.new((p.x * IN, p.y * IN, z1 * IN)) for p in pts]
    lo_out = [bm.verts.new((p.x * IN, p.y * IN, z0 * IN)) for p in off]
    hi_out = [bm.verts.new((p.x * IN, p.y * IN, z1 * IN)) for p in off]
    for i in range(n if closed else n - 1):
        j = (i + 1) % n
        bm.faces.new((lo_in[i], lo_in[j], hi_in[j], hi_in[i]))
        bm.faces.new((lo_out[i], hi_out[i], hi_out[j], lo_out[j]))
        bm.faces.new((hi_in[i], hi_in[j], hi_out[j], hi_out[i]))
        bm.faces.new((lo_in[i], lo_out[i], lo_out[j], lo_in[j]))
    if not closed:
        for k in (0, n - 1):
            bm.faces.new((lo_in[k], lo_out[k], hi_out[k], hi_in[k]))
    outward(bm)
    return mesh_obj(name, bm, mat)


def casing_frame(name, a, b, normal, height, z0=0.0, width=3.5, depth=0.75, sill=False):
    """Trim around an opening on one face. a/b: jamb points (inch xy) on the wall face."""
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    n = Vector(normal)
    parts = []
    for side, p in (("l", a - d * width), ("r", b)):
        q = [p, p + d * width, p + d * width + n * depth, p + n * depth]
        parts.append(prism(f"{name}_{side}", [tuple(v) for v in q], z0, z0 + height, "trim"))
    q = [a - d * width, b + d * width, b + d * width + n * depth, a - d * width + n * depth]
    parts.append(prism(f"{name}_head", [tuple(v) for v in q], z0 + height, z0 + height + width, "trim"))
    if sill:   # apron under the stool, which is 0.75" thick
        parts.append(prism(f"{name}_apron", [tuple(v) for v in q], z0 - 0.75 - width, z0 - 0.75, "trim"))
    return parts


# ---------------------------------------------------------------- walls of a rectangular room
def rect_walls(width, depth):
    """The four walls of a rectangular room (interior x 0..width east, y -depth..0), as
    frames {name: (origin, rot_z, length)}. On each wall, x runs from the left corner as you
    face the wall from inside, and y points out through the wall (the room is toward -y);
    the same frame the wall fixtures in parts.py use."""
    return {"N": ((0, 0), 0.0, width), "E": ((width, 0), -math.pi / 2, depth),
            "S": ((width, -depth), math.pi, width), "W": ((0, -depth), math.pi / 2, depth)}


def to_plan(frame, x, y=0.0):
    """A point on a wall frame (x along the wall, y out through it) in plan coordinates."""
    (ox, oy), r, _ = frame
    return (ox + x * math.cos(r) - y * math.sin(r), oy + x * math.sin(r) + y * math.cos(r))


def wall_cutter(name, frame, x0, x1, z0, z1, thick):
    """Boolean cutter for an opening x0..x1 along a wall frame, through a wall `thick` deep."""
    pts = [to_plan(frame, x0, -1), to_plan(frame, x1, -1), to_plan(frame, x1, thick + 2), to_plan(frame, x0, thick + 2)]
    ob = prism(name, pts, z0, z1, None)
    ob.data.materials.clear()
    ob["opening"] = True      # roomkit.check: nothing else may cross a door or window
    return ob


# ---------------------------------------------------------------- dimensions for the plan page
DIMS = []


def dim(a, b, src, off=8.0, label=None, key=None, z=None):
    """A dimension line from plan point a to b (inches) for the web Plans page and the
    walkthrough, drawn `off` inches to the left of a->b (negative: to the right). src says where
    the number came from: 'measured', 'plan', 'photo', 'design' (a chosen new size) or
    'assumed'. key: the dimensions.json name this line shows (its src then comes from there),
    which makes it editable in the walkthrough. z: height to draw it at in 3D (default 4")."""
    if key:
        from . import dimensions
        if key in dimensions.REG:
            src = dimensions.REG[key]["src"]
    n = math.hypot(b[0] - a[0], b[1] - a[1])
    if label is None:      # inches, plus feet-inches for longer runs: 145" (12'1")
        n = round(n * 2) / 2
        ft, inch = divmod(n, 12)
        label = f'{n:g}"' + (f" ({int(ft)}'{inch:g}\")" if n >= 48 else "")
    DIMS.append(dict(a=list(a), b=list(b), src=src, off=off, label=label, key=key, z=z))


# ---------------------------------------------------------------- light
def window_portal(name, w, h, loc, rot):
    """Cycles light portal over a window opening (inches) so sky light finds its way in.
    rot: (pi/2, 0, 0) faces -y; (pi/2, 0, pi/2) faces +x."""
    pd = bpy.data.lights.new(name, "AREA")
    pd.shape = "RECTANGLE"
    pd.size, pd.size_y = w * IN, h * IN
    pd.cycles.is_portal = True
    ob = bpy.data.objects.new(name, pd)
    ob.location = I(*loc)
    ob.rotation_euler = rot
    return link(ob)


def sky(color=(0.70, 0.80, 0.95), strength=2.0):
    """Daylight sky (dark in the evening)."""
    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (*color, 1)
    bg.inputs[1].default_value = 0.03 if NIGHT else strength * (HERO_SKY if HERO else 1.0)
    return world


def sun(direction, energy=3.0):
    """Sun lamp shining along direction (plan x, y, z); none in the evening."""
    if NIGHT:
        return None
    sund = bpy.data.lights.new("sun", "SUN")
    sund.energy = energy * (HERO_SUN if HERO else 1.0)
    sund.angle = math.radians(1.5)
    sund.color = (1.0, 0.93, 0.82)
    ob = bpy.data.objects.new("sun", sund)
    ob.rotation_euler = Vector(direction).to_track_quat("-Z", "Y").to_euler()
    return link(ob)


# ---------------------------------------------------------------- cameras
def camera(name, loc, target, lens=13.0, ortho=None, portrait=False, level=False):
    """Camera at loc looking at target (inches). Also a jump point in the web walkthrough.
    portrait: render 3:4 upright, to match a phone photo held upright.
    level: keep the camera level and frame the target's height with lens shift instead of
    tilting, so walls stay vertical (how interiors are photographed)."""
    CAM_DATA[name] = dict(loc=loc, target=target, lens=lens, **({"ortho": ortho} if ortho else {}),
                          **({"portrait": True} if portrait else {}))
    cd = bpy.data.cameras.new(name)
    cd.sensor_width = 36
    cd.lens = lens
    cd.clip_start = 0.05
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho * IN
    ob = bpy.data.objects.new(name, cd)
    ob.location = I(*loc)
    d = Vector(I(*target)) - Vector(I(*loc))
    if level:
        flat = math.hypot(d.x, d.y)
        # a point at angle a above the horizon lands f*tan(a) up the sensor; shift is in
        # sensor widths (the frame's long side, portrait or not)
        cd.shift_y = lens * (d.z / flat) / cd.sensor_width
        d.z = 0
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    link(ob)
    CAMERAS[name] = ob
    return ob


# ---------------------------------------------------------------- render / export
def finish(cams, info=None, glass=(), plan_hide=("ceiling", "can_")):
    """Render the named cameras to OUT, or write the walkthrough model when --export is given.
    info: extra scene.json data for the walkthrough (windows, sun, walk area);
    glass: name prefixes of window panes, which must not block sun and sky light;
    plan_hide: name prefixes hidden in the top-down 'plan' view."""
    # window panes let light through when Cycles traces shadows (sun, sky), so daylight lands inside
    for o in scene.objects:
        if glass and o.name.startswith(tuple(glass)):
            o.visible_shadow = False
    scene.render.engine = "CYCLES"
    # GPU when Blender can see one (Metal on a Mac, OptiX/CUDA on NVIDIA, HIP on AMD, oneAPI on
    # Intel), else CPU;
    # --cpu forces the CPU
    scene.cycles.device = "CPU"
    if "--cpu" not in argv:
        cprefs = bpy.context.preferences.addons["cycles"].preferences
        for dev_type in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
            try:
                cprefs.compute_device_type = dev_type
            except TypeError:
                continue
            cprefs.get_devices()
            gpus = [d for d in cprefs.devices if d.type == dev_type]
            if gpus:
                for d in cprefs.devices:
                    d.use = d.type == dev_type
                scene.cycles.device = "GPU"
                print("RENDER DEVICE", dev_type, [d.name for d in gpus])
                break
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    scene.render.resolution_x = RES
    scene.render.resolution_y = int(RES * 0.75)
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    if HERO:
        scene.view_settings.exposure = HERO_EXPOSURE
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 92
    os.makedirs(OUT, exist_ok=True)

    if CHECK:
        from . import check
        check.run()
        sys.exit(0)
    if EXPORT:
        export_web(EXPORT, info or {})
        sys.exit(0)

    if SAVE:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOM_DIR, "room.blend"))

    hidden = [o for o in scene.objects if o.name.startswith(tuple(plan_hide))]
    for name in cams:
        scene.camera = CAMERAS[name]
        for o in hidden:
            o.hide_render = name == "plan"
        scene.render.resolution_x = RES
        if name == "plan":
            scene.render.resolution_y = RES
        elif CAM_DATA[name].get("portrait"):
            scene.render.resolution_x, scene.render.resolution_y = int(RES * 0.75), RES
        else:
            scene.render.resolution_y = int(RES * 0.75)
        scene.render.filepath = os.path.join(OUT, f"{name}.jpg")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", scene.render.filepath)


def pack_atlas(obj, px, dark=frozenset(), pad=3, min_tex=0, min_side=0):
    """UVs for baking: faces merged into charts (connected faces facing within ~18 degrees of
    each other, so a wall cut up by its doorways or a ceiling slope is one piece with no seams
    inside it, and a curved tub a few pieces), each laid
    flat at its real size and packed into one px-square atlas on shelves, at one texel density
    (the largest that fits). Far faster than Smart UV Project on hundreds of objects.
    Faces in `dark` (never lit, never seen) all share one black texel in the corner.
    min_tex: every chart at least this many texels across (the low-res pre-pass, so small
    faces get sampled). min_side: each chart stretched to at least this many texels in each
    direction, so a thin face (a ladder rung, a rug's edge) still has texels baked inside it.
    Returns {face index: (x, y, w, h)} in texels (its chart's rectangle)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv = bm.loops.layers.uv.verify()
    mw, nm = obj.matrix_world, obj.matrix_world.to_3x3().inverted().transposed()
    bm.faces.ensure_lookup_table()
    norm = {}
    for f in bm.faces:
        n = (nm @ f.normal).normalized()
        norm[f.index] = n if n.length > 0.5 else Vector((0, 0, 1))
    # grow each chart from a seed face over edges to faces within ~18 degrees of the seed, so a
    # flat wall is one chart and a curved tub a few, not one per facet
    seen, groups = set(dark), {}
    for f0 in bm.faces:
        if f0.index in seen:
            continue
        n0, stack, fs = norm[f0.index], [f0], []
        seen.add(f0.index)
        while stack:
            f = stack.pop()
            fs.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in seen and norm[g.index].dot(n0) > 0.95:
                        seen.add(g.index)
                        stack.append(g)
        groups[f0.index] = fs
    charts = []           # [faces, {face: [(u, v) per loop]}, x0, y0, w, h]
    for fs in groups.values():
        n = norm[fs[0].index]
        a_ = Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))
        u = n.cross(a_).normalized()
        v = n.cross(u)
        pts = {f.index: [((mw @ lp.vert.co).dot(u), (mw @ lp.vert.co).dot(v)) for lp in f.loops] for f in fs}
        allp = [p for ps in pts.values() for p in ps]
        x0, y0 = min(p[0] for p in allp), min(p[1] for p in allp)
        charts.append([fs, pts, x0, y0, max(p[0] for p in allp) - x0, max(p[1] for p in allp) - y0])

    def place(d):      # shelf-pack at d texels/m; None if it doesn't fit
        rects = []
        for k, ch in enumerate(charts):
            dd = d * min(1.0, (px - 2 * pad - 2) / max(ch[4] * d, ch[5] * d, 1e-9))   # huge charts: shrink
            if min_tex:
                dd = max(dd, min_tex / max(ch[4], ch[5], 1e-6))
            du = max(dd, min_side / max(ch[4], 1e-6))
            dv = max(dd, min_side / max(ch[5], 1e-6))
            rects.append((math.ceil(ch[5] * dv) + 2 * pad, math.ceil(ch[4] * du) + 2 * pad, (du, dv), k))
        rects.sort(key=lambda r: -r[0])
        x, y, shelf, out = 8, 0, 0, {}             # 8x8 texels at the origin: the shared black
        for rh, rw, dd, k in rects:
            if x + rw > px:
                x, y, shelf = 0, y + shelf, 0
            if y + rh > px:
                return None
            out[k] = (x, y, rw, rh, dd)
            x += rw
            shelf = max(shelf, rh)
        return out

    area = sum(ch[4] * ch[5] for ch in charts) or 1.0
    lo, hi = 1.0, math.sqrt(px * px / area)
    best = place(lo)
    while best is None and lo > 1e-3:            # very many charts: drop the density until it fits
        lo /= 2
        hi = lo * 2
        best = place(lo)
    for _ in range(14):                            # largest density that still fits
        mid = (lo + hi) / 2
        got = place(mid)
        if got:
            lo, best = mid, got
        else:
            hi = mid
    print("ATLAS", len(bm.faces), "faces in", len(charts), "charts,", len(dark), "dark,", round(lo), "texels/m", flush=True)
    rect_of = {}
    for k, (fs, pts, x0, y0, _, _) in enumerate(charts):
        ax, ay, rw, rh, (du, dv) = best[k]
        for f in fs:
            rect_of[f.index] = (ax, ay, rw, rh)
            for lp, (pu, pv) in zip(f.loops, pts[f.index]):
                lp[uv].uv = ((ax + pad + (pu - x0) * du) / px, (ay + pad + (pv - y0) * dv) / px)
    for fi in dark:
        for lp in bm.faces[fi].loops:
            lp[uv].uv = (4 / px, 4 / px)
    bm.to_mesh(obj.data)
    bm.free()
    return rect_of


def fill_gutters(img, grow=8):
    """Clean up a bake made with no margin before the walkthrough shows it. The outermost row
    of each chart is baked at points on or past the face's edge, partly inside the neighboring
    geometry, so it comes out dark: a dotted outline around every chart (cracks across a curved
    tub's charts). That row takes its color from the texels just inside it, each chart is then
    grown `grow` texels into the gap around it, and the rest of the atlas is filled push-pull
    (averaged down a pyramid, holes filled from the level above), so texture filtering and
    mipmaps never blend black in."""
    import numpy as np
    w_, h_ = img.size
    a = np.empty(w_ * h_ * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    a = a.reshape(h_, w_, 4)
    cov = a[:, :, 3] > 0.5
    rgb = a[:, :, :3]

    def shifts(x):            # the 8 neighbors of every texel (edges padded empty)
        p = np.pad(x, ((1, 1), (1, 1)) + ((0, 0),) * (x.ndim - 2))
        return [p[1 + dy:1 + dy + h_, 1 + dx:1 + dx + w_]
                for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]

    def spread(col, ok):      # each texel not ok: the mean of its ok neighbors, if any
        n = np.zeros((h_, w_), np.float32)
        acc = np.zeros_like(col)
        for c, k in zip(shifts(col), shifts(ok)):
            n += k
            acc += c * k[:, :, None]
        got = (~ok) & (n > 0)
        col[got] = acc[got] / n[got][:, None]
        return ok | got

    inner = cov.copy()
    for k in shifts(cov):
        inner &= k
    col = np.where(inner[:, :, None], rgb, 0.0).astype(np.float32)
    ok = spread(col, inner)                 # edge row: from the texels inside it
    keep = cov & ~ok                         # charts too thin to have an inside keep their own
    col[keep] = rgb[keep]
    ok |= keep
    for _ in range(grow):
        ok = spread(col, ok)
    wt = ok.astype(np.float32)
    levels = [(col * wt[:, :, None], wt)]
    while max(levels[-1][1].shape) > 1:
        c, w = levels[-1]
        if c.shape[0] % 2 or c.shape[1] % 2:                 # odd sizes: pad with empty texels
            py, px_ = c.shape[0] % 2, c.shape[1] % 2
            c = np.pad(c, ((0, py), (0, px_), (0, 0)))
            w = np.pad(w, ((0, py), (0, px_)))
        levels.append((c[0::2, 0::2] + c[1::2, 0::2] + c[0::2, 1::2] + c[1::2, 1::2],
                       w[0::2, 0::2] + w[1::2, 0::2] + w[0::2, 1::2] + w[1::2, 1::2]))
    fill = None
    for c, w in reversed(levels):
        mean = c / np.maximum(w, 1e-9)[:, :, None]
        if fill is not None:
            up = fill.repeat(2, axis=0).repeat(2, axis=1)[:c.shape[0], :c.shape[1]]
            mean = np.where((w > 0)[:, :, None], mean, up)
        fill = mean
    a[:, :, :3] = np.where(ok[:, :, None], col, fill)
    a[:8, :8, :3] = 0.0                      # the shared black of pack_atlas's never-lit faces
    a[:, :, 3] = 1.0
    img.pixels.foreach_set(a.ravel())
    print("FILLED", int((~cov).sum()), "empty texels,", int((cov & ~inner).sum()), "edge texels redone", flush=True)


def bake_lighting(out):
    """Bake Cycles lighting (direct, bounce and emission; no glossy, which depends on the view)
    into one atlas over every static surface, saved through the renders' AgX view so the
    walkthrough can show it as-is. A quick low-res pass first finds the faces no light reaches
    (box bottoms, wall insides, the backs of ceiling sheets), which then take no atlas space.
    Returns the baked material names."""
    import numpy as np
    dg = bpy.context.evaluated_depsgraph_get()
    targets = []
    for o in scene.objects:
        if o.type != "MESH" or o.hide_render or not o.data.polygons:
            continue
        names = [s_.material.name if s_.material else "" for s_ in o.material_slots]
        if not names or any(n == "" or n.startswith(BAKE_SKIP) for n in names):
            continue
        if max(o.dimensions) > 25:     # outdoor ground planes: would eat the atlas; left live
            continue
        c = o.matrix_world @ (sum((Vector(b) for b in o.bound_box), Vector()) / 8)
        if c.length > 20:              # far scenery (tree lines 25-30 m out): left live too
            continue
        targets.append(o)
    # booleans applied (their cut faces need UVs of their own); each object its own mesh
    meshes = {o: (bpy.data.meshes.new_from_object(o.evaluated_get(dg)), [s_.material for s_ in o.material_slots])
              for o in targets}
    for o, (m, slot_mats) in meshes.items():
        o.modifiers.clear()
        o.data = m
        for i, s_ in enumerate(o.material_slots):   # boolean cuts add an empty slot for their faces
            s_.material = slot_mats[i] if i < len(slot_mats) and slot_mats[i] else slot_mats[0]
        for uv in list(m.uv_layers):
            m.uv_layers.remove(uv)
        m.uv_layers.new(name="bake")
        # closed solids: faces pointing outward. A prism drawn clockwise has its top facing down;
        # renders shade either side, but a bake lights the side the face points to (black)
        bm = bmesh.new()
        bm.from_mesh(m)
        if bm.edges and all(e.is_manifold for e in bm.edges):
            outward(bm)
            bm.to_mesh(m)
        bm.free()
        # textures projected in object space would lose their origin in the join below: keep each object's coordinates
        attr = m.attributes.new("object_co", "FLOAT_VECTOR", "POINT")
        attr.data.foreach_set("vector", [c for v in m.vertices for c in v.co])
    # one object: Cycles bakes each selected object in its own pass (a full scene sync each),
    # which for hundreds of objects takes far longer than the bake itself
    bpy.ops.object.select_all(action="DESELECT")
    for o in targets:
        o.select_set(True)
    bpy.context.view_layer.objects.active = targets[0]
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = "baked"
    mats = {s_.material for s_ in obj.material_slots}
    for m in mats:
        if m.use_nodes:
            for tc in [n for n in m.node_tree.nodes if n.type == "TEX_COORD"]:
                co = None
                for link in list(tc.outputs["Object"].links):
                    if co is None:
                        co = m.node_tree.nodes.new("ShaderNodeAttribute")
                        co.attribute_name = "object_co"
                    m.node_tree.links.new(co.outputs["Vector"], link.to_socket)
    scene.render.bake.margin = 6

    def bake(px, samples, margin=6):
        # alpha: the bake clears to transparent and writes opaque texels, so alpha marks coverage
        img = bpy.data.images.new(f"bake_{px}", px, px, alpha=True, float_buffer=True)
        for m in mats:
            m.use_nodes = True
            n = m.node_tree.nodes.get("bake_target") or m.node_tree.nodes.new("ShaderNodeTexImage")
            n.name = "bake_target"
            n.image = img
            m.node_tree.nodes.active = n
        scene.cycles.samples = samples
        print("BAKING", px, "px,", samples, "samples", flush=True)
        bpy.ops.object.bake(type="COMBINED", pass_filter={"EMIT", "DIRECT", "INDIRECT", "DIFFUSE", "TRANSMISSION"},
                            margin=margin, use_clear=True)
        return img

    pre = 2048
    rects = pack_atlas(obj, pre, pad=1, min_tex=3, min_side=3)
    img = bake(pre, 8)
    px_ = np.array(img.pixels[:], dtype=np.float32).reshape(pre, pre, 4)[:, :, :3].max(axis=2)
    dark = frozenset(fi for fi, (x, y, w, h) in rects.items() if px_[y:y + h, x:x + w].max(initial=0.0) < 0.002)
    pack_atlas(obj, BAKE_PX, dark, min_side=4)
    img = bake(BAKE_PX, BAKE_SAMPLES, margin=0)   # no margin: alpha marks exactly the baked texels
    fill_gutters(img)
    tex_dir = os.path.join(out, "textures")
    os.makedirs(tex_dir, exist_ok=True)
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 88
    img.save_render(os.path.join(tex_dir, "bake.jpg"), scene=scene)   # through AgX, like the renders
    for m in mats:                    # the exporter keeps procedural materials as flat colors
        m.node_tree.nodes.remove(m.node_tree.nodes["bake_target"])
    return sorted(m.name for m in mats)


# shell pieces: not "objects" for the walkthrough's hover sizes (walls get measured by ray instead).
# A room adds its own name prefixes: core.SHELL += ("sun_floor", "stairwell")
SHELL = ("walls", "base", "floor", "ceiling", "surface", "outside", "recess", "soffit", "case_", "cut_",
         "can_", "grille", "threshold", "baked", "hall_")


def object_boxes():
    """Each top-level object's size for the walkthrough's hover readout: [{name, min, max}] in
    plan inches (x east, y north, z up), its children's meshes included. Taken before a bake,
    which merges the static meshes into one."""
    bpy.context.view_layer.update()   # world matrices of parented parts are stale until then
    boxes = {}
    for o in scene.objects:
        if o.type != "MESH" or o.hide_render:
            continue
        root = o
        while root.parent:
            root = root.parent
        if root.name.startswith(SHELL) or o.name.startswith(SHELL) \
                or {"wall", "walls", "ceiling"} & set(o.name.split("_")) or o.name.endswith("_floor"):
            continue                  # walls of stand-in rooms (bed_wall_n, closet_ceiling...)
        key = root.name
        parts = key.split("_")
        if root is o and len(parts) >= 3 and parts[1].isdigit():   # loose parts of one fixture: fan_0_blade0
            key = "_".join(parts[:2])
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            p = (w.x / IN, w.y / IN, w.z / IN)
            b = boxes.setdefault(key, [list(p), list(p)])
            b[0] = [min(b[0][i], p[i]) for i in range(3)]
            b[1] = [max(b[1][i], p[i]) for i in range(3)]
    return [dict(name=k, min=[round(v, 2) for v in a], max=[round(v, 2) for v in b])
            for k, (a, b) in boxes.items() if max(b[i] - a[i] for i in range(3)) < 400]


def export_web(out, extra):
    """model.glb + scene.json for the walkthrough, and bundle.js (both plus the textures in
    out/textures) so the page also opens straight from disk."""
    os.makedirs(out, exist_ok=True)
    extra = dict(extra, objects=object_boxes())
    if BAKE:
        extra = dict(extra, bake="bake.jpg", baked=bake_lighting(out))
    elif os.path.exists(os.path.join(out, "textures", "bake.jpg")):
        os.remove(os.path.join(out, "textures", "bake.jpg"))   # stale: this export isn't baked
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, "model.glb"), export_format="GLB",
                              use_renderable=True, export_apply=True, export_cameras=False,
                              export_lights=False, export_image_format="NONE", export_yup=True,
                              export_extras=True)   # custom properties, e.g. a mirror's "outline"
    from . import dimensions
    info = dict(units="inches; plan x east, y north, z up", ceiling=CEILING,
                cameras=CAM_DATA, lights=LIGHTS, dims=DIMS, dimensions=dimensions.entries(),
                room=os.path.relpath(ROOM_DIR, os.path.join(os.path.dirname(__file__), "..", "..")), **extra)
    variant = "variants" in os.path.normpath(out).split(os.sep)   # another design for the picker
    if not variant:                   # the room's own export: refresh its size sheet
        dimensions.write()
    with open(os.path.join(out, "scene.json"), "w") as f:
        json.dump(info, f, indent=1)
    # the same data as a script, for the Plans page (works opened from disk, without the model)
    with open(os.path.join(out, "scene.js"), "w") as f:
        f.write("window.SCENE = " + json.dumps(info) + ";\n")
    # browsers block file:// pages from loading these as separate files
    import base64
    mime = {".jpg": "image/jpeg", ".png": "image/png"}
    tex_dir = os.path.join(out, "textures")
    tex = {}
    for fn in sorted(os.listdir(tex_dir)) if os.path.isdir(tex_dir) else []:
        ext = os.path.splitext(fn)[1].lower()
        if ext in mime:
            with open(os.path.join(tex_dir, fn), "rb") as tf:
                tex[fn] = f"data:{mime[ext]};base64," + base64.b64encode(tf.read()).decode()
    if variant:                       # design variants load over http only
        print("EXPORTED", out)
        return
    with open(os.path.join(out, "model.glb"), "rb") as gf:
        glb = base64.b64encode(gf.read()).decode()
    with open(os.path.join(out, "bundle.js"), "w") as f:
        f.write("window.BUNDLE = " + json.dumps({"scene": info, "glb": glb, "tex": tex}) + ";\n")
    print("EXPORTED", out)
