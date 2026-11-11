"""Does the server's Blender jobs on this computer (the server's container has no Blender or GPU).
lib/serve.sh starts it next to the server; by itself:
    python3 lib/worker.py [http://127.0.0.1:8000]

Two lanes, so a size typed in the walkthrough isn't stuck behind an 8-minute bake:
  export  the room's walkthrough model, unbaked (a few seconds), straight into web/
  bake    the lighting baked again (~8 min) into web/.bake, then swapped into web/
Standard library only.
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWAP = ("model.glb", "scene.json", "scene.js", "bundle.js", os.path.join("textures", "bake.jpg"))
FILES = threading.Lock()     # an export and a bake's swap don't write web/ at the same time


class Api:
    def __init__(self, url, data):
        self.url, self.data = url.rstrip("/"), data

    def call(self, path, body=None):
        with open(os.path.join(self.data, "worker.token")) as f:   # new each server start
            token = f.read().strip()
        req = urllib.request.Request(self.url + path, method="POST", data=json.dumps(body or {}).encode(),
                                     headers={"Content-Type": "application/json", "X-Worker-Token": token})
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read()) if res.status == 200 else None


def export(rdir):
    with FILES:
        r = subprocess.run([os.path.join(rdir, "render.sh"), "--export", "web"], cwd=rdir,
                           capture_output=True, text=True, timeout=600)
    return "EXPORTED" in r.stdout, (r.stdout + r.stderr)[-4000:]


def bake(rdir):
    tmp = os.path.join(rdir, "web", ".bake")
    try:
        r = subprocess.run([os.path.join(rdir, "render.sh"), "--export", tmp, "--bake"], cwd=rdir,
                           capture_output=True, text=True, timeout=3600)
        ok = "EXPORTED" in r.stdout
        if ok:
            with FILES:
                for fn in SWAP:
                    if os.path.exists(os.path.join(tmp, fn)):
                        os.replace(os.path.join(tmp, fn), os.path.join(rdir, "web", fn))
        return ok, (r.stdout + r.stderr)[-4000:]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


RUN = {"export": export, "bake": bake}


def lane(api, kind, root, idle=2.0):
    while True:
        try:
            job = api.call(f"/api/jobs/claim?kind={kind}")
        except (OSError, urllib.error.URLError):   # server starting or restarting
            job = None
        if not job:
            time.sleep(idle)
            continue
        t0 = time.time()
        try:
            ok, log = RUN[kind](os.path.join(root, job["room"]))
        except Exception as e:   # noqa: BLE001 -- report it on the job, keep the lane going
            ok, log = False, repr(e)
        print(f"{kind} {job['room']}: {'done' if ok else 'FAILED'} in {time.time() - t0:.0f}s", flush=True)
        api.call(f"/api/jobs/{job['id']}/finish", {"ok": ok, "seconds": time.time() - t0, "log": log})


if __name__ == "__main__":
    api = Api(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000", os.path.join(ROOT, "data"))
    for kind in RUN:
        threading.Thread(target=lane, args=(api, kind, ROOT), daemon=True).start()
    print("worker: waiting for export and bake jobs", flush=True)
    threading.Event().wait()
