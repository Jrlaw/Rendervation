"""Local web server for every house and room (http://127.0.0.1:8000, this machine only).

Serves the repo's files like `python3 -m http.server`, plus one endpoint the walkthrough uses
to correct a size:

  POST /api/dimension  {"room": "houses/<house>/rooms/<room>", "name": "kitchen_w",
                        "value": 110.5, "src": "measured", "note": "..."}   (or "reset": true)

It records the value in that room's dimensions.json (lib/roomkit/dimensions.py), then
re-exports the room's walkthrough model (quick, unbaked: a few seconds) and answers when done;
then it bakes the lighting again in the background (~8 min) and swaps that in (reload to see it).

And one the Selections checklist uses to tick a product off:

  POST /api/status  {"room": "houses/<house>/rooms/<room>", "group": 0, "item": 3,
                     "name": "Kato 2-861 ...", "status": "need" | "ordered" | "have"}

It sets that product's status in the room's inventory.json (the name must match, so a stale page
can't change the wrong one) and rebuilds the Selections page and web/inventory.js.

And one the walkthrough's "Make this the choice" button uses:

  POST /api/choose  {"room": "houses/<house>/rooms/<room>", "design": "layout_i"}

It writes the room's web/chosen.js (the walkthrough and Plans open on that design) and makes
web/cards/<design>.jpg the room's picture on the house's home page, first making that card from the
design's render, or from the walkthrough's snapshot of the 3D view, when it has none (needs Pillow).
"""
import base64
import datetime
import http.server
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))
from roomkit import dimensions  # noqa: E402

LOCK = threading.Lock()           # one export at a time
BAKES = {}                        # room dir -> {"thread", "dirty"}: the background re-bake after edits
SWAP = ("model.glb", "scene.json", "scene.js", "bundle.js", os.path.join("textures", "bake.jpg"))


def bake_later(rdir):
    """After an edit: bake the room's walkthrough again (~8 min) into web/.bake, then swap it in.
    Another edit meanwhile marks it dirty and the bake starts over on the newer model."""
    st = BAKES.setdefault(rdir, {"thread": None, "dirty": False})
    st["dirty"] = True
    if st["thread"] and st["thread"].is_alive():
        return

    def run():
        tmp = os.path.join(rdir, "web", ".bake")
        while st["dirty"]:
            st["dirty"] = False
            r = subprocess.run([os.path.join(rdir, "render.sh"), "--export", tmp, "--bake"], cwd=rdir,
                               capture_output=True, text=True, timeout=3600)
            with LOCK:
                if st["dirty"] or "EXPORTED" not in r.stdout:
                    continue
                for fn in SWAP:
                    if os.path.exists(os.path.join(tmp, fn)):
                        os.replace(os.path.join(tmp, fn), os.path.join(rdir, "web", fn))
                print(f"baked lighting back in {os.path.relpath(rdir, ROOT)}", flush=True)
        shutil.rmtree(tmp, ignore_errors=True)
    st["thread"] = threading.Thread(target=run, daemon=True)
    st["thread"].start()


def make_card(card, rdir, design, first, camera, snapshot):
    """A design's home-page card, 800px wide: its day render from the room's first camera when it has
    one (web/renders, or web/variants/<id>/renders), else the walkthrough's snapshot of the 3D view."""
    base = os.path.join(rdir, "web") if first else os.path.join(rdir, "web", "variants", design)
    render = os.path.join(base, "renders", "day", f"{camera}.jpg")
    if camera and re.fullmatch(r"[\w-]+", camera) and os.path.isfile(render):
        src = render
    elif snapshot and snapshot.startswith("data:image/jpeg;base64,"):
        src = io.BytesIO(base64.b64decode(snapshot.split(",", 1)[1]))
    else:
        return
    img = Image.open(src).convert("RGB")
    img.thumbnail((800, 800))
    os.makedirs(os.path.dirname(card), exist_ok=True)
    img.save(card, quality=85)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def end_headers(self):        # walkthrough files change on every export
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def send_head(self):
        # Always send the file. A renders symlink re-pointed at an older folder serves an older file
        # at the same URL, so "not modified since" would keep the browser on the old picture.
        if "If-Modified-Since" in self.headers:
            del self.headers["If-Modified-Since"]
        return super().send_head()

    def reply(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def room_dir(self, req):
        room = os.path.normpath(req["room"])
        rdir = os.path.join(ROOT, room)
        ok = room.split(os.sep)[0] in ("houses", "examples") and os.path.isfile(os.path.join(rdir, "render.sh"))
        return room, rdir, ok

    def status(self):
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            room, rdir, ok = self.room_dir(req)
            path = os.path.join(rdir, "inventory.json")
            if not ok or not os.path.isfile(path):
                return self.reply(400, {"error": "not a room with an inventory"})
            if req["status"] not in ("need", "ordered", "have"):
                return self.reply(400, {"error": "status is need, ordered or have"})
            with LOCK:
                with open(path) as f:
                    inv = json.load(f)
                it = inv["groups"][int(req["group"])]["items"][int(req["item"])]
                if it["name"] != req["name"]:
                    return self.reply(409, {"error": "the list changed: reload the page"})
                it["status"] = req["status"]
                with open(path, "w") as f:
                    json.dump(inv, f, indent=1, ensure_ascii=False)
                    f.write("\n")
                run = subprocess.run([sys.executable, os.path.join(ROOT, "lib", "tools", "selections_page.py"), rdir],
                                     capture_output=True, text=True, timeout=60)
        except (KeyError, ValueError, IndexError, TypeError, OSError) as e:
            return self.reply(400, {"error": str(e)})
        print(f"status {room}: {req['name']} -> {req['status']}", flush=True)
        self.reply(200 if run.returncode == 0 else 500, {"ok": run.returncode == 0, "log": run.stderr[-2000:]})

    def choose(self):
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            room, rdir, ok = self.room_dir(req)
            design = str(req["design"])
            with open(os.path.join(rdir, "web", "index.html")) as f:
                ids = re.findall(r'\["([\w-]+)", "[^"]*"\]', re.search(r"variants: (\[.*?\]\]),", f.read(), re.S).group(1))
            if not ok or design not in ids:
                return self.reply(400, {"error": "not one of this room's designs"})
            with LOCK:
                with open(os.path.join(rdir, "web", "chosen.js"), "w") as f:
                    f.write("// the room's chosen design: the walkthrough and Plans open on it. Written by lib/serve.py\n"
                            f"window.CHOSEN = {json.dumps(design)};\n")
                card = os.path.join(rdir, "web", "cards", design + ".jpg")
                if not os.path.isfile(card):
                    make_card(card, rdir, design, design == ids[0], req.get("camera"), req.get("snapshot"))
                home = os.path.join(ROOT, room.split(os.sep)[0], "index.html")   # houses/index.html
                if os.path.isfile(card) and os.path.isfile(home):
                    rel = os.path.relpath(rdir, os.path.dirname(home))
                    with open(home) as f:
                        page = f.read()
                    m = re.search(r'<article class="room">(?:(?!</article>).)*?href="%s/web/index.html".*?</article>' % re.escape(rel), page, re.S)
                    if m:
                        new = re.sub(r'<img src="[^"]*"', f'<img src="{rel}/web/cards/{design}.jpg"', m.group(0), count=1)
                        with open(home, "w") as f:
                            f.write(page.replace(m.group(0), new))
        except (KeyError, ValueError, AttributeError, OSError) as e:
            return self.reply(400, {"error": str(e)})
        print(f"chose {room}: {design}", flush=True)
        self.reply(200, {"ok": True})

    def do_POST(self):
        if self.path == "/api/status":
            return self.status()
        if self.path == "/api/choose":
            return self.choose()
        if self.path != "/api/dimension":
            return self.reply(404, {"error": "unknown endpoint"})
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            room, rdir, ok = self.room_dir(req)
            if not ok:
                return self.reply(400, {"error": "not a room"})
            path = os.path.join(rdir, dimensions.FILE)
            with open(path) as f:
                known = json.load(f).get("dimensions", {})
            name = req["name"]
            if name not in known:
                return self.reply(400, {"error": f"no dimension named {name}"})
            if req.get("reset"):
                data = {"units": "inches", "dimensions": known}
                known[name]["override"] = False
                with open(path, "w") as f:
                    json.dump(data, f, indent=1)
                    f.write("\n")
            else:
                value = float(req["value"])
                src = req.get("src", "measured")
                if not 0 < value < 5000 or src not in dimensions.SOURCES:
                    return self.reply(400, {"error": "value or source out of range"})
                dimensions.set_override(path, name, value, src, str(req.get("note", ""))[:300],
                                        datetime.date.today().isoformat())
        except (KeyError, ValueError, OSError) as e:
            return self.reply(400, {"error": str(e)})
        t0 = time.time()
        with LOCK:
            run = subprocess.run([os.path.join(rdir, "render.sh"), "--export", "web"], cwd=rdir,
                                 capture_output=True, text=True, timeout=600)
        ok = "EXPORTED" in run.stdout
        print(f"dimension {room} {name}: export {'ok' if ok else 'FAILED'} in {time.time() - t0:.0f}s", flush=True)
        if ok:
            bake_later(rdir)
        self.reply(200 if ok else 500, {"ok": ok, "seconds": round(time.time() - t0),
                                        "log": "" if ok else (run.stdout + run.stderr)[-2000:]})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Open http://127.0.0.1:{port} in your browser (Ctrl+C to stop)", flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
