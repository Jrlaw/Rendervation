"""Retake a house's card picture on the home page (houses/<house>/web/map.jpg) from the live 3D map,
so newly modeled rooms show highlighted. Run after lib/tools/house_map.py, with lib/serve.sh running:
    <python with playwright> lib/tools/house_snapshot.py houses/<house>
Needs Playwright's Chromium with GPU flags; headless Firefox can't draw WebGL."""
import os
import sys

from playwright.sync_api import sync_playwright

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
house = os.path.relpath(os.path.abspath(sys.argv[1]), root)
url = f"http://127.0.0.1:8000/{house}/web/index.html?3d"
out = os.path.join(root, house, "web", "map.jpg")

with sync_playwright() as p:
    b = p.chromium.launch(args=["--enable-gpu", "--use-gl=angle", "--use-angle=gl-egl", "--ignore-gpu-blocklist"])
    pg = b.new_page(viewport={"width": 1600, "height": 860})
    pg.goto(url)
    pg.wait_for_timeout(8000)   # the dollhouse builds after the page loads
    pg.locator("#dollhouse").screenshot(path=out, type="jpeg", quality=85)
    b.close()
print(f"wrote {os.path.relpath(out, root)}")
