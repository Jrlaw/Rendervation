"""Shader materials shared by every room, plus a few generic paint and tile colors.

Colors measured from a specific product go in the person's catalog (houses/catalog/), which
adds them to PAINTS, TILE_COLORS and TILE_FINISHES.

Every material is registered in core.MATS under its name, so geometry helpers can take
the name. Image textures load from the room's textures/ folder.
"""
import math
import os

import bpy

from . import core
from .core import IN

# wall paint concepts (approximate on-screen colors; get real samples before choosing)
PAINTS = {
    "warmwhite": (0.83, 0.81, 0.77),    # Alabaster-like
    "sage": (0.36, 0.38, 0.31),         # soft sage-grey, Evergreen Fog family
    "plaster": (0.66, 0.49, 0.39),      # dusty clay-pink beige, Setting Plaster family
    "olive": (0.10, 0.105, 0.06),       # deep olive
    "deepsage": (0.15, 0.175, 0.12),    # muted deep sage-green
    # from a "sage green + ivory + natural oak" swatch photo (measured, shadows skipped)
    "ivory": (0.863, 0.799, 0.693),     # ~#EFE7D9 creamy warm white
    "swatchsage": (0.29, 0.30, 0.20),   # ~#93947A soft warm khaki-sage
}
# glazed wall tile colors: (darker, lighter) linear RGB; tiles vary between the two
TILE_COLORS = {
    "offwhite": ((0.84, 0.82, 0.76), (0.89, 0.87, 0.81)),
    "sage": ((0.56, 0.61, 0.48), (0.62, 0.67, 0.54)),      # pale celadon sage ~#C9CFBC
    "blue": ((0.49, 0.57, 0.62), (0.55, 0.63, 0.68)),      # dusty, greyed light blue ~#BCC9D0
    "bone": ((0.78, 0.71, 0.57), (0.84, 0.77, 0.63)),      # warm glossy cream ~#E6DCC8
    "teal": ((0.03, 0.20, 0.21), (0.06, 0.27, 0.28)),      # deep glossy mid-century teal ~#2F6F72
    "deepblue": ((0.010, 0.032, 0.090), (0.024, 0.062, 0.150)),   # glossy deep blue ~#1E3A5C-#2A4F72, varied
    "terracotta": ((0.36, 0.070, 0.024), (0.55, 0.140, 0.052)),   # glossy burnt-orange terracotta ~#A34B2A-#C4693E, varied
    "plum": ((0.060, 0.025, 0.085), (0.110, 0.050, 0.150)),   # glossy muted plum/aubergine ~#47304F-#5E3F6B, varied
    "ochre": ((0.58, 0.40, 0.16), (0.70, 0.52, 0.25)),     # warm handmade mustard / ochre ~#C8973F
}
# finish per color: (roughness, strong tile-to-tile variation, wavy glaze); default glossy glazed
TILE_FINISHES = {
    "deepblue": (0.08, True, False),
    "plum": (0.08, True, False),
    "terracotta": (0.12, True, False),   # glossy, with a clear tile-to-tile shade spread
}
# tile pattern: (width along the wall, height, row offset, handmade look)
TILE_PATTERNS = {
    "subway": (6.0, 3.0, 0.5, False),      # 3x6 horizontal running bond
    "vstack": (2.0, 8.0, 0.0, False),      # 2x8 vertical stack
    "zellige": (4.0, 4.0, 0.0, True),      # 4x4 handmade-look squares, stacked grid
    "vstack12": (3.0, 12.0, 0.0, False),   # 3x12 vertical stack
    "vstack6": (2.0, 6.25, 0.0, False),    # 2x6 vertical stack
    "vstack16": (4.0, 16.0, 0.0, False),   # 4x16 vertical stack
    "subway8": (8.0, 2.5, 0.5, True),      # 2.5x8 horizontal running bond
    "square4": (4.25, 4.25, 0.0, False),   # 4-1/4" squares, stacked grid (classic wall tile)
}


def principled(name, color, rough=0.5, metal=0.0, **extra):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for k, v in extra.items():
        b.inputs[k].default_value = v
    core.MATS[name] = m
    return m


def tex_node(nt, fname, colorspace="sRGB"):
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = bpy.data.images.load(os.path.join(core.TEX, fname), check_existing=True)
    n.image.colorspace_settings.name = colorspace
    return n


def mix_rgb(nt, fac, a, b):
    """Mix two color sockets by fac; returns the result socket."""
    n = nt.nodes.new("ShaderNodeMix")
    n.data_type = "RGBA"
    nt.links.new(fac, n.inputs[0])
    nt.links.new(a, n.inputs[6])
    nt.links.new(b, n.inputs[7])
    return n.outputs[2]


def math_node(nt, op, a, b=None):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def wall_tile_material(name, axis, origin, sign=1.0, pattern="vstack", color="offwhite", z0=0.0):
    """Glazed wall tile laid out in world space, from TILE_PATTERNS / TILE_COLORS / TILE_FINISHES.
    axis: world axis along the wall ('x' or 'y'); origin: where the first full tile starts
    (inches); sign: +1/-1 for the direction the courses run; z0: height of the first course.
    Odd rows shift by the pattern's row offset."""
    tw, th, offset, handmade = TILE_PATTERNS[pattern]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    along = sep.outputs[0] if axis == "x" else sep.outputs[1]
    u = math_node(nt, "DIVIDE", math_node(nt, "MULTIPLY", math_node(nt, "SUBTRACT", along, origin * IN), sign), tw * IN)
    v = math_node(nt, "DIVIDE", math_node(nt, "SUBTRACT", sep.outputs[2], z0 * IN), th * IN)
    row = math_node(nt, "FLOOR", v)
    u2 = math_node(nt, "ADD", u, math_node(nt, "MULTIPLY", math_node(nt, "FLOORED_MODULO", row, 2.0), offset))
    fu = math_node(nt, "SUBTRACT", u2, math_node(nt, "FLOOR", u2))
    fv = math_node(nt, "SUBTRACT", v, row)
    gu, gv = 0.0625 / tw, 0.0625 / th          # 1/8" joints

    def edge(f, g):
        return math_node(nt, "MAXIMUM", math_node(nt, "LESS_THAN", f, g), math_node(nt, "GREATER_THAN", f, 1 - g))

    grout = math_node(nt, "MAXIMUM", edge(fu, gu), edge(fv, gv))
    # slight tile-to-tile shade variation, like real glazed tile
    cmb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(math_node(nt, "FLOOR", u2), cmb.inputs[0])
    nt.links.new(row, cmb.inputs[1])
    wn = nt.nodes.new("ShaderNodeTexWhiteNoise")
    wn.noise_dimensions = "3D"
    nt.links.new(cmb.outputs[0], wn.inputs[0])
    lo, hi = TILE_COLORS[color]
    c1 = nt.nodes.new("ShaderNodeRGB"); c1.outputs[0].default_value = (*lo, 1)
    c2 = nt.nodes.new("ShaderNodeRGB"); c2.outputs[0].default_value = (*hi, 1)
    rough0, varied, wavy = TILE_FINISHES.get(color, (0.08, handmade, handmade))
    shade = wn.outputs["Value"]
    if varied:     # zellige, cement, artisan glaze: stronger tile-to-tile variation
        shade = math_node(nt, "SUBTRACT", math_node(nt, "MULTIPLY", shade, 1.8), 0.4)
    face = mix_rgb(nt, shade, c1.outputs[0], c2.outputs[0])
    gc = nt.nodes.new("ShaderNodeRGB"); gc.outputs[0].default_value = (0.90, 0.89, 0.86, 1)   # white grout
    nt.links.new(mix_rgb(nt, grout, face, gc.outputs[0]), bsdf.inputs["Base Color"])
    rough = math_node(nt, "ADD", rough0, math_node(nt, "MULTIPLY", grout, 0.6))
    nt.links.new(rough, bsdf.inputs["Roughness"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.8         # with white grout the joints read by their shadow
    bump.inputs["Distance"].default_value = 0.002
    height = math_node(nt, "SUBTRACT", 1.0, grout)
    if wavy:         # uneven, wavy glaze surface
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 60.0
        nt.links.new(geo.outputs["Position"], nz.inputs[0])
        height = math_node(nt, "ADD", height, math_node(nt, "MULTIPLY", nz.outputs["Fac"], 0.35))
    nt.links.new(height, bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    core.MATS[name] = m
    return m


def image_tile_material(name, axes, size, grout, faces):
    """Large-format tiles with grout, laid out in world space, faced with product photos.

    axes: the two world axes the surface spans, e.g. 'xy' (floor), 'xz', 'yz'.
    size, grout: tile size and joint width (inches). faces: two texture files, alternated in a
    checker, every other tile turned 180° so the pattern doesn't read as a repeat.
    """
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    size_m = size * IN
    comps = {"x": sep.outputs[0], "y": sep.outputs[1], "z": sep.outputs[2]}
    u_w = math_node(nt, "DIVIDE", comps[axes[0]], size_m)
    v_w = math_node(nt, "DIVIDE", comps[axes[1]], size_m)
    iu, iv = math_node(nt, "FLOOR", u_w), math_node(nt, "FLOOR", v_w)
    fu, fv = math_node(nt, "SUBTRACT", u_w, iu), math_node(nt, "SUBTRACT", v_w, iv)
    # parity of the tile index picks face A/B; parity of iu rotates 180°
    par = math_node(nt, "FLOORED_MODULO", math_node(nt, "ADD", iu, iv), 2.0)
    rot = math_node(nt, "FLOORED_MODULO", iu, 2.0)
    ru = math_node(nt, "ADD", fu, math_node(nt, "MULTIPLY", rot,
                                             math_node(nt, "SUBTRACT", 1.0, math_node(nt, "MULTIPLY", fu, 2.0))))
    rv = math_node(nt, "ADD", fv, math_node(nt, "MULTIPLY", rot,
                                             math_node(nt, "SUBTRACT", 1.0, math_node(nt, "MULTIPLY", fv, 2.0))))
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(ru, comb.inputs[0])
    nt.links.new(rv, comb.inputs[1])
    ta, tb = tex_node(nt, faces[0]), tex_node(nt, faces[1])
    for t in (ta, tb):
        t.extension = "EXTEND"
        nt.links.new(comb.outputs[0], t.inputs[0])
    face = mix_rgb(nt, par, ta.outputs[0], tb.outputs[0])
    # grout mask: 1 inside the joint
    g = (grout / 2) / size

    def edge(f):
        lo = math_node(nt, "LESS_THAN", f, g)
        hi = math_node(nt, "GREATER_THAN", f, 1 - g)
        return math_node(nt, "MAXIMUM", lo, hi)

    joint = math_node(nt, "MAXIMUM", edge(fu), edge(fv))
    gcol = nt.nodes.new("ShaderNodeRGB")
    gcol.outputs[0].default_value = (0.70, 0.68, 0.64, 1)
    nt.links.new(mix_rgb(nt, joint, face, gcol.outputs[0]), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.6
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.4
    bump.inputs["Distance"].default_value = 0.001
    nt.links.new(math_node(nt, "SUBTRACT", 1.0, joint), bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    core.MATS[name] = m
    return m


def image_box_material(name, fname, repeat_m, rough, bump=0.0, tint=None):
    """Image texture box-projected in object space; repeat_m = (x, y, z) meters per repeat."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = [1 / r for r in repeat_m]
    nt.links.new(tc.outputs["Object"], mp.inputs[0])
    t = tex_node(nt, fname)
    t.projection = "BOX"
    t.projection_blend = 0.15
    t.extension = "MIRROR"
    nt.links.new(mp.outputs[0], t.inputs[0])
    col = t.outputs[0]
    if tint:
        tn = nt.nodes.new("ShaderNodeRGB")
        tn.outputs[0].default_value = (*tint, 1)
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        nt.links.new(col, mul.inputs[6])
        nt.links.new(tn.outputs[0], mul.inputs[7])
        col = mul.outputs[2]
    nt.links.new(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    if bump:
        b = nt.nodes.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        b.inputs["Distance"].default_value = 0.0005
        nt.links.new(t.outputs[0], b.inputs["Height"])
        nt.links.new(b.outputs[0], bsdf.inputs["Normal"])
    core.MATS[name] = m
    return m


def emission(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.remove(nt.nodes["Principled BSDF"])
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs[0].default_value = (*color, 1)
    e.inputs[1].default_value = strength
    nt.links.new(e.outputs[0], nt.nodes["Material Output"].inputs[0])
    core.MATS[name] = m
    return m


def veined_stone_material(name="travertine", cream=(0.74, 0.67, 0.57), vein=(0.58, 0.50, 0.40), rough=0.45):
    """Pale stone with long horizontal veins (defaults: a cream travertine). Procedural so a 48"
    slab shows no repeat."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.2, 22.0, 22.0)     # stretched along the slab's length
    nt.links.new(tc.outputs["Object"], mp.inputs[0])
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.inputs["Scale"].default_value = 2.0
    n1.inputs["Detail"].default_value = 8.0
    n1.inputs["Distortion"].default_value = 0.4
    nt.links.new(mp.outputs[0], n1.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (*cream, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (*vein, 1)
    nt.links.new(n1.outputs["Fac"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.05
    nt.links.new(n1.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    core.MATS[name] = m
    return m


def marble_material(name="marble", base=(0.88, 0.87, 0.85), vein=(0.04, 0.04, 0.045), rough=0.15,
                    scale=0.6):
    """White marble with thin, wandering dark veins (Panda/Nero Marquina-style when vein is black):
    the veins are where a distorted noise crosses its midpoint, plus fainter grey secondary ones.
    Procedural so an island-size slab shows no repeat. scale: veins per meter, roughly."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")

    def veins(sc, distortion, width):   # 0 on a vein, 1 away from it
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = sc
        n.inputs["Detail"].default_value = 6.0
        n.inputs["Distortion"].default_value = distortion
        nt.links.new(tc.outputs["Object"], n.inputs[0])
        d = math_node(nt, "ABSOLUTE", math_node(nt, "SUBTRACT", n.outputs["Fac"], 0.5))
        return math_node(nt, "MINIMUM", math_node(nt, "DIVIDE", d, width), 1.0)

    main = veins(scale, 3.0, 0.012)
    minor = veins(scale * 2.7, 2.0, 0.006)
    grey = tuple((b + v) / 2 for b, v in zip(base, vein))
    cb = nt.nodes.new("ShaderNodeRGB"); cb.outputs[0].default_value = (*base, 1)
    cv = nt.nodes.new("ShaderNodeRGB"); cv.outputs[0].default_value = (*vein, 1)
    cg = nt.nodes.new("ShaderNodeRGB"); cg.outputs[0].default_value = (*grey, 1)
    col = mix_rgb(nt, minor, cg.outputs[0], cb.outputs[0])     # faint grey veins on white
    col = mix_rgb(nt, main, cv.outputs[0], col)                # then the dark main veins
    nt.links.new(col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    core.MATS[name] = m
    return m


def bark_material():
    """Black walnut bark: dark, deeply furrowed."""
    m = bpy.data.materials.new("bark")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (14, 14, 2.5)          # furrows run vertically
    nt.links.new(tc.outputs["Object"], mp.inputs[0])
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    nt.links.new(mp.outputs[0], vor.inputs[0])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.9
    nt.links.new(vor.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    bsdf.inputs["Base Color"].default_value = (0.075, 0.062, 0.055, 1)
    bsdf.inputs["Roughness"].default_value = 0.95
    core.MATS["bark"] = m


def wicker_material(name="wicker", color=(0.58, 0.42, 0.24), strand=0.5):
    """Woven rattan: a basket weave of strand-wide (inches) bands, alternating horizontal and
    vertical cell by cell, raised by bump, darker in the gaps between strands."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    xyz = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], xyz.inputs[0])
    cell = strand * core.IN
    cu = math_node(nt, "DIVIDE", math_node(nt, "ADD", xyz.outputs[0], xyz.outputs[1]), cell)   # around
    cv = math_node(nt, "DIVIDE", xyz.outputs[2], cell)                                         # up
    parity = math_node(nt, "ABSOLUTE", math_node(nt, "MODULO", math_node(nt, "ADD", math_node(nt, "FLOOR", cu),
                                                                          math_node(nt, "FLOOR", cv)), 2))
    across_h = math_node(nt, "SINE", math_node(nt, "MULTIPLY", math_node(nt, "FRACT", cv), math.pi))
    across_v = math_node(nt, "SINE", math_node(nt, "MULTIPLY", math_node(nt, "FRACT", cu), math.pi))
    h = math_node(nt, "ADD", across_h, math_node(nt, "MULTIPLY", parity, math_node(nt, "SUBTRACT", across_v, across_h)))
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.7
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(h, bump.inputs["Height"])
    nt.links.new(bump.outputs[0], bsdf.inputs["Normal"])
    c1 = nt.nodes.new("ShaderNodeRGB"); c1.outputs[0].default_value = tuple(c * 0.35 for c in color) + (1,)
    c2 = nt.nodes.new("ShaderNodeRGB"); c2.outputs[0].default_value = (*color, 1)
    nt.links.new(mix_rgb(nt, math_node(nt, "POWER", h, 0.5), c1.outputs[0], c2.outputs[0]), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.75
    core.MATS[name] = m


def leaf_material():
    """Clumps of leaves: a Voronoi cutout gives the leafy edge (also used for potted plants)."""
    m = bpy.data.materials.new("leaves")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (16, 16, 16)
    nt.links.new(tc.outputs["Object"], mp.inputs[0])
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    nt.links.new(mp.outputs[0], vor.inputs[0])
    cut = math_node(nt, "LESS_THAN", vor.outputs["Distance"], 0.27)
    nt.links.new(cut, bsdf.inputs["Alpha"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], noise.inputs[0])
    c1 = nt.nodes.new("ShaderNodeRGB"); c1.outputs[0].default_value = (0.11, 0.20, 0.035, 1)
    c2 = nt.nodes.new("ShaderNodeRGB"); c2.outputs[0].default_value = (0.25, 0.36, 0.07, 1)
    nt.links.new(mix_rgb(nt, noise.outputs["Fac"], c1.outputs[0], c2.outputs[0]), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.6
    bsdf.inputs["Transmission Weight"].default_value = 0.0
    bsdf.inputs["Subsurface Weight"].default_value = 0.25
    core.MATS["leaves"] = m


def rug_material(name, fname, bounds, flip=False):
    """Bath mat with its picture mapped across the top. bounds = (x0, x1, y0, y1) in inches, in
    world space, not Generated coords: those follow the object's bounding box, and the bake joins
    every object into one, which would stretch the picture across the room. flip turns the
    picture to read from the other side."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    mp = nt.nodes.new("ShaderNodeMapping")
    x0, x1, y0, y1 = (v * IN for v in bounds)
    sx, sy = 1 / (x1 - x0), 1 / (y1 - y0)
    if flip:
        mp.inputs["Location"].default_value = (1 + x0 * sx, 1 + y0 * sy, 0)
        mp.inputs["Scale"].default_value = (-sx, -sy, 1)
    else:
        mp.inputs["Location"].default_value = (-x0 * sx, -y0 * sy, 0)
        mp.inputs["Scale"].default_value = (sx, sy, 1)
    nt.links.new(geo.outputs["Position"], mp.inputs[0])
    t = tex_node(nt, fname)
    t.extension = "EXTEND"
    nt.links.new(mp.outputs[0], t.inputs[0])
    nt.links.new(t.outputs[0], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    bsdf.inputs["Sheen Weight"].default_value = 0.8
    core.MATS[name] = m
    return m


def basic_set():
    """Materials nearly every room uses: ceiling, trim, doors, metals, glass, mirror, can lights."""
    principled("ceiling", (0.88, 0.87, 0.85), 0.8)
    principled("trim", (0.90, 0.89, 0.86), 0.3)
    principled("door", (0.90, 0.89, 0.86), 0.35)
    principled("chrome", (0.90, 0.90, 0.90), 0.06, 1.0)
    principled("fixture", (0.025, 0.025, 0.025), 0.4)      # matte black: faucets, shower, drains
    principled("nickel", (0.80, 0.78, 0.74), 0.3, 1.0)
    principled("ceramic", (0.93, 0.93, 0.92), 0.08, **{"Coat Weight": 0.6})
    principled("acrylic", (0.94, 0.94, 0.93), 0.12, **{"Coat Weight": 0.8, "Coat Roughness": 0.03})
    principled("sink_basin", (0.88, 0.86, 0.80), 0.25)
    principled("glass", (0.95, 0.98, 0.97), 0.0, **{"Transmission Weight": 1.0, "IOR": 1.5})
    principled("mirror", (0.93, 0.93, 0.92), 0.01, 1.0)
    principled("mirror_back", (0.15, 0.15, 0.15), 0.5)
    # neutral scattering: Blender's default radius is skin-like (red travels farthest), which
    # turned backlit shades salmon pink
    principled("shade", (0.92, 0.90, 0.85), 0.9, **{"Subsurface Weight": 0.3, "Subsurface Radius": (1.0, 1.0, 1.0),
                                                    "Subsurface Scale": 0.005})
