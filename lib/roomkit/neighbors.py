"""The rest of the floor in a room's renders: the other modeled rooms on its floor, appended in place.

A house's house_layout.py lists where each modeled room sits (PLACEMENTS: origin in house inches, rotation,
floor, and the design its neighbors show, with the room.py flags that build it). For a render, each neighbor
is built by its own room.py into a saved scene (renders/.neighbor/<design>.blend in that room, rebuilt when
anything it's built from is newer) and its objects are appended, moved to where that room is. Its cans come
too, so light spills through the doors as it does in the house; its sun and cameras don't. Objects named
standin_* (a room's simple stand-in for a neighbor, or its copy of a door the neighbor owns) are hidden in
this room and in every neighbor once the neighbors are there. The walkthrough does the same from the
exported models (lib/web/walkthrough.js).
"""
import glob
import importlib.util
import math
import os
import subprocess

import bpy

from . import core


def _placements(room_dir):
    house = os.path.dirname(os.path.dirname(room_dir))       # houses/<house>/rooms/<room> -> houses/<house>
    path = os.path.join(house, "house_layout.py")
    if not os.path.exists(path):
        return {}
    spec = importlib.util.spec_from_file_location("house_layout_for_neighbors", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "PLACEMENTS", {})


def _newest(room_dir):
    """The newest modification time among the files a room's model is built from."""
    lib = os.path.dirname(os.path.abspath(__file__))
    house = os.path.dirname(os.path.dirname(room_dir))
    files = (glob.glob(os.path.join(room_dir, "*.py")) + glob.glob(os.path.join(room_dir, "textures", "*"))
             + glob.glob(os.path.join(lib, "*.py")) + glob.glob(os.path.join(os.path.dirname(house), "catalog", "*.py")))
    return max(os.path.getmtime(f) for f in files)


def _blend(room_dir, p):
    """The neighbor's saved scene for its design, rebuilt by its own render.sh when it's stale."""
    path = os.path.join(room_dir, "renders", ".neighbor", f"{p.get('design', 'asis')}.blend")
    if not os.path.exists(path) or os.path.getmtime(path) < _newest(room_dir):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        flags = p.get("flags", ["--design", p.get("design", "asis")])
        print("NEIGHBOR building", os.path.basename(room_dir), " ".join(flags))
        subprocess.run([os.path.join(room_dir, "render.sh"), *flags, "--neighbor-blend", path, "--neighbors", "off"],
                       cwd=room_dir, check=True, stdout=subprocess.DEVNULL)
    return path


def _hide_standins(objs):
    def standin(o):
        while o:
            if o.name.startswith("standin_"):
                return True
            o = o.parent
        return False
    for o in objs:
        if standin(o):
            o.hide_render = o.hide_viewport = True


def add(room_dir):
    """Append the other modeled rooms on this room's floor, in place; hide every stand-in. Returns how many."""
    P = _placements(room_dir)
    key = os.path.basename(os.path.normpath(room_dir))
    here = P.get(key)
    if not here:
        return 0
    n = 0
    for other, p in P.items():
        if other == key or p.get("floor") != here.get("floor"):
            continue
        other_dir = os.path.join(os.path.dirname(room_dir), other)
        if not os.path.exists(os.path.join(other_dir, "room.py")):
            continue
        with bpy.data.libraries.load(_blend(other_dir, p)) as (src, dst):
            dst.objects = list(src.objects)
        objs = [o for o in dst.objects if o and not (o.type == "CAMERA" or (o.type == "LIGHT" and o.data.type == "SUN"))]
        # where it sits in this room's plan inches (placements turn counter-clockwise, in degrees)
        a = math.radians(-here.get("rot", 0))
        dx, dy = p["origin"][0] - here["origin"][0], p["origin"][1] - here["origin"][1]
        root = bpy.data.objects.new(f"neighbor_{other}", None)
        core.link(root)
        root.location = core.I(dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a), 0)
        root.rotation_euler = (0, 0, math.radians(p.get("rot", 0) - here.get("rot", 0)))
        for o in objs:
            bpy.context.scene.collection.objects.link(o)
            if o.parent is None:
                o.parent = root
        _hide_standins(objs)
        n += 1
    if n:
        _hide_standins(list(bpy.context.scene.objects))
    print("NEIGHBORS", n)
    return n
