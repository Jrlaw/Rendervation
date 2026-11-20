"""Measure the room from a photo whose camera is solved: cast a photo pixel onto a known plane, or project a model
point into the photo.

    python3 lib/tools/measure_photo.py <marks.py> <shot> PICK [PICK ...]

PICK is either
    px,py,x=13     the 3D point where pixel (px, py) meets the plane x = 13 (or y=..., z=...): a cabinet front, a
                   wall, the counter top. Read the pixel off a zoomed crop of the photo.
    @x,y,z         the pixel where the model point (x, y, z) lands, to compare with the photo by eye.

It solves the shot from its marks first (as solve_cameras.py does) and prints the fit, so a weak solve shows next
to the numbers it gives. Plan positions near the marks are reliable; heights depend on how far apart in height
the marks are (solve_cameras.py warns), so cast the same edge from a second photo before trusting it.
"""
import importlib.util
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve_cameras as sc  # noqa: E402

sys.dont_write_bytecode = True        # a marks file edited and re-run within a second must not load a stale .pyc


def main(path, name, picks):
    spec = importlib.util.spec_from_file_location("marks", path)
    marks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(marks)
    shot = marks.SHOTS[name]
    p, r = sc.solve(shot, marks.LENS)
    err = np.hypot(r[::2], r[1::2])
    print(f"{name}: err px mean {err.mean():.0f} max {err.max():.0f}")
    w, h = (1200, 1600) if shot["portrait"] else (1600, 1200)
    focal = shot.get("lens", marks.LENS) / 36 * 1600
    f, x, y = sc.basis(*p[3:])
    cam = p[:3]
    for pick in picks:
        if pick.startswith("@"):
            d = np.array([float(c) for c in pick[1:].split(",")]) - cam
            z = d @ f
            print(f"{pick} -> pixel ({w / 2 + focal * (d @ x) / z:.0f}, {h / 2 - focal * (d @ y) / z:.0f})")
            continue
        px, py, plane = pick.split(",")
        axis, val = plane.split("=")
        k, val = "xyz".index(axis.strip()), float(val)
        ray = f + (float(px) - w / 2) / focal * x - (float(py) - h / 2) / focal * y
        t = (val - cam[k]) / ray[k]
        pt = cam + t * ray
        print(f"{pick} -> ({pt[0]:.1f}, {pt[1]:.1f}, {pt[2]:.1f})" + ("  (behind the camera)" if t < 0 else ""))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
