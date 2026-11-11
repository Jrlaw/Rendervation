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
"""
import datetime
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
import time

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


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def end_headers(self):        # walkthrough files change on every export
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

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

    def do_POST(self):
        if self.path == "/api/status":
            return self.status()
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
