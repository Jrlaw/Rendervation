"""Solve each photo's camera from landmarks: known model points against the pixels where the photo shows them.

    python3 lib/tools/solve_cameras.py houses/<house>/rooms/<room>/camera_marks.py

The marks file defines LENS (from EXIF: mm-equivalent x 36 / 34.6 at 4:3) and SHOTS, a dict of
name: dict(start=loc, aim=target, portrait=bool, marks=[((x, y, z), (px, py)), ...]), with pixels in the
1600 px photo. It prints loc, target and roll for camera(...).rotation_euler.rotate_axis("Z", roll).
A large error means the model's dimensions or the picked pixels are off. Also check that the solved spot
isn't inside a wall: with marks on one wall only, position along the view is weakly fixed.
"""
import importlib.util
import sys

import numpy as np


def basis(yaw, pitch, roll):
    f = np.array([np.cos(pitch) * np.cos(yaw), np.cos(pitch) * np.sin(yaw), np.sin(pitch)])
    x = np.cross(f, (0, 0, 1))
    x /= np.linalg.norm(x)
    y = np.cross(x, f)
    return f, x * np.cos(roll) + y * np.sin(roll), -x * np.sin(roll) + y * np.cos(roll)


def residual(p, marks, focal, cx, cy):
    f, x, y = basis(*p[3:])
    out = []
    for pt, (u, v) in marks:
        d = np.array(pt, float) - p[:3]
        z = d @ f
        out += [cx + focal * (d @ x) / z - u, cy - focal * (d @ y) / z - v]
    return np.array(out)


def solve(shot, lens):
    w, h = (1200, 1600) if shot["portrait"] else (1600, 1200)
    focal = shot.get("lens", lens) / 36 * 1600        # the 36 mm sensor spans the long side
    s, a = np.array(shot["start"], float), np.array(shot["aim"], float)
    d = a - s
    p = np.array([*s, np.arctan2(d[1], d[0]), np.arctan2(d[2], np.hypot(d[0], d[1])), 0.0])
    lam = 1e-3
    r = residual(p, shot["marks"], focal, w / 2, h / 2)
    for _ in range(400):
        J = np.zeros((len(r), 6))
        for i in range(6):
            q = p.copy()
            q[i] += 1e-4
            J[:, i] = (residual(q, shot["marks"], focal, w / 2, h / 2) - r) / 1e-4
        step = np.linalg.solve(J.T @ J + lam * np.eye(6), -J.T @ r)
        r2 = residual(p + step, shot["marks"], focal, w / 2, h / 2)
        if r2 @ r2 < r @ r:
            p, r, lam = p + step, r2, lam * 0.5
        else:
            lam *= 4
    return p, r


def main(path):
    spec = importlib.util.spec_from_file_location("marks", path)
    marks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(marks)
    for name, shot in marks.SHOTS.items():
        p, r = solve(shot, marks.LENS)
        target = p[:3] + basis(*p[3:])[0] * 100
        err = np.hypot(r[::2], r[1::2])
        loc = ", ".join(f"{c:.1f}" for c in p[:3])
        aim = ", ".join(f"{c:.1f}" for c in target)
        print(f"{name}: loc=({loc}) target=({aim}) roll={p[5]:.4f}  err px mean {err.mean():.0f} max {err.max():.0f}  per mark {[int(e) for e in err]}")


if __name__ == "__main__":
    main(sys.argv[1])
