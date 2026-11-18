"""Lay each as-is render over the photo it matches, so a wrong size or position shows at a glance.

    python3 lib/tools/overlay.py houses/<house>/rooms/<room> [--design asis] [--night]

For each web/before/photoN.jpg with a render renders/<design>/<day|night>/photoN.jpg, it writes
renders/<design>/overlay/photoN.jpg: the photo, dimmed, with the render's edges drawn on it in red, next to a
50/50 blend. Edges that run parallel to the photo's but a few pixels off are a wrong dimension (a sill too
high, a shelf too long); edges with nothing under them are something the photo doesn't have.

It also prints a score per view: the share of the render's strong edges that land within 1% of the image
width of a photo edge. Clutter in the photo and the model's missing small things keep it below 100; compare
views against each other, and look hard at any view well below the rest. Run solve_cameras.py first: with
the camera off, every edge is off.
"""
import argparse
import os

import numpy as np
from PIL import Image, ImageFilter

W = 800    # working width, px


def edges(im, keep=0.08):
    """The strongest `keep` share of Sobel edges, as a bool array."""
    g = np.asarray(im.convert("L").filter(ImageFilter.GaussianBlur(1.2)), float)
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    gx[1:-1, 1:-1] = (g[:-2, 2:] + 2 * g[1:-1, 2:] + g[2:, 2:]) - (g[:-2, :-2] + 2 * g[1:-1, :-2] + g[2:, :-2])
    gy[1:-1, 1:-1] = (g[2:, :-2] + 2 * g[2:, 1:-1] + g[2:, 2:]) - (g[:-2, :-2] + 2 * g[:-2, 1:-1] + g[:-2, 2:])
    m = np.hypot(gx, gy)
    return m > np.quantile(m, 1 - keep)


def near(mask, r):
    """Grow a bool mask by r px."""
    im = Image.fromarray((mask * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.MaxFilter(2 * r + 1))) > 0


def overlay(photo_path, render_path, out_path):
    render = Image.open(render_path).convert("RGB")
    h = round(W * render.height / render.width)
    render = render.resize((W, h), Image.LANCZOS)
    photo = Image.open(photo_path).convert("RGB").resize((W, h), Image.LANCZOS)
    er, ep = edges(render), edges(photo)
    score = (er & near(ep, max(1, W // 100))).sum() / max(er.sum(), 1)
    base = np.asarray(photo, float) * 0.55
    base[near(er, 1)] = (255, 30, 30)
    blend = Image.blend(photo, render, 0.5)
    sheet = Image.new("RGB", (2 * W + 8, h), "white")
    sheet.paste(Image.fromarray(base.astype(np.uint8)), (0, 0))
    sheet.paste(blend, (W + 8, 0))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sheet.save(out_path, quality=90)
    return score


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("room")
    ap.add_argument("--design", default="asis")
    ap.add_argument("--night", action="store_true", help="compare the evening renders (for evening photos)")
    a = ap.parse_args()
    before = os.path.join(a.room, "web", "before")
    renders = os.path.join(a.room, "renders", a.design, "night" if a.night else "day")
    out = os.path.join(a.room, "renders", a.design, "overlay")
    names = sorted(f for f in os.listdir(before) if f.endswith(".jpg"))
    if not names:
        raise SystemExit(f"no photos in {before}")
    for f in names:
        r = os.path.join(renders, f)
        if not os.path.exists(r):
            print(f"{f[:-4]:10s} no render ({r})")
            continue
        s = overlay(os.path.join(before, f), r, os.path.join(out, f))
        print(f"{f[:-4]:10s} {s:4.0%} of the render's edges land on the photo's")
    print(f"sheets: {out}/")


if __name__ == "__main__":
    main()
