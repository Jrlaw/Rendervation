"""Retake a house's card picture on the home page (houses/<house>/web/map.jpg) from the live 3D map.
The server's worker runs it after rebuilding the map (lib/tools/house_map.py) whenever a room is
added or changed; by hand, with lib/serve.sh running:
    <python with playwright> lib/tools/house_snapshot.py houses/<house> [http://127.0.0.1:8000]
Needs Playwright's Chromium with GPU flags; headless Firefox can't draw WebGL. The floor switch is
left out, and the picture is cropped to the house (4:3, like the cards), so a small house fills it."""
import io
import os
import sys

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
house = os.path.relpath(os.path.abspath(sys.argv[1]), root)
server = sys.argv[2].rstrip("/") if len(sys.argv) > 2 else "http://127.0.0.1:8000"
out = os.path.join(root, house, "web", "map.jpg")


def crop(img, pad=0.08, aspect=4 / 3):
    """The house (everything that isn't the background), padded, widened or heightened to 4:3."""
    bg = Image.new("RGB", img.size, img.getpixel((img.width - 1, img.height - 1)))
    box = ImageChops.difference(img, bg).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
    if not box:
        return img
    x0, y0, x1, y1 = box
    w, h = (x1 - x0) * (1 + 2 * pad), (y1 - y0) * (1 + 2 * pad)
    w, h = max(w, h * aspect), max(h, w / aspect)
    w, h = min(w, img.width), min(h, img.height)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    left = min(max(0, cx - w / 2), img.width - w)
    top = min(max(0, cy - h / 2), img.height - h)
    return img.crop((round(left), round(top), round(left + w), round(top + h)))


with sync_playwright() as p:
    b = p.chromium.launch(args=["--enable-gpu", "--use-gl=angle", "--use-angle=gl-egl", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": 1600, "height": 860})
    pg.goto(f"{server}/{house}/web/index.html?3d")
    pg.wait_for_timeout(8000)   # the dollhouse builds after the page loads
    pg.add_style_tag(content=".map-tools { visibility: hidden !important; }")
    pg.wait_for_timeout(200)
    shot = Image.open(io.BytesIO(pg.locator("#dollhouse").screenshot(type="png"))).convert("RGB")
    b.close()
img = crop(shot)
img.thumbnail((1200, 900))
img.save(out, quality=85)
print(f"wrote {os.path.relpath(out, root)} ({img.width}x{img.height})")
