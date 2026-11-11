"""The whole-house map is kept up to date: a house with a map (house_layout.py) gets a `house` job
whenever its map data or picture is missing or older than what they're made from, and the worker's
house lane rebuilds both."""
import importlib.util
import os
import sys
import time

from server.catalog import map_stale, sync
from server.config import REPO
from server.db import Job

spec = importlib.util.spec_from_file_location("worker", os.path.join(REPO, "lib/worker.py"))
worker_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker_mod)

HOUSE = "houses/test"


def touch(path, when):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("x")
    os.utime(path, (when, when))


def built(root, when):
    """The map as house_map.py and house_snapshot.py leave it, at time `when`."""
    touch(root / HOUSE / "web/house.js", when)
    touch(root / HOUSE / "web/map.jpg", when + 1)


def house_jobs(app):
    with app.state.sessions() as s:
        return [(j.room, j.status) for j in s.query(Job).filter(Job.kind == "house").order_by(Job.id)]


def test_no_map_no_job(root, app):
    assert not map_stale(str(root), HOUSE)   # no house_layout.py in the test house
    assert house_jobs(app) == []


def test_new_map_is_built(root, app):
    touch(root / HOUSE / "house_layout.py", time.time() - 100)
    assert map_stale(str(root), HOUSE)
    with app.state.sessions() as s:
        sync(s, str(root))
    assert house_jobs(app) == [(HOUSE, "queued")]


def test_up_to_date_map_is_left_alone(root, app):
    now = time.time()
    for p in [root / HOUSE / "house_layout.py", root / HOUSE / "rooms", root / HOUSE / "rooms/den/web",
              root / HOUSE / "rooms/attic/web"]:
        os.utime(p, (now - 100, now - 100)) if p.exists() else touch(p, now - 100)
    built(root, now)
    assert not map_stale(str(root), HOUSE)


def test_a_room_change_makes_it_stale(root):
    now = time.time()
    touch(root / HOUSE / "house_layout.py", now - 100)
    for p in [root / HOUSE / "rooms", root / HOUSE / "rooms/den/web", root / HOUSE / "rooms/attic/web"]:
        os.utime(p, (now - 100, now - 100))
    built(root, now - 50)
    assert not map_stale(str(root), HOUSE)
    touch(root / HOUSE / "rooms/den/README.md", now)          # its status line changed
    assert map_stale(str(root), HOUSE)


def test_a_new_room_makes_it_stale(root):
    now = time.time()
    touch(root / HOUSE / "house_layout.py", now - 100)
    built(root, now - 50)
    (root / HOUSE / "rooms/porch/web").mkdir(parents=True)   # the rooms folder changes
    os.utime(root / HOUSE / "rooms", (now, now))
    assert map_stale(str(root), HOUSE)


def test_old_picture_makes_it_stale(root):
    now = time.time()
    touch(root / HOUSE / "house_layout.py", now - 100)
    for p in [root / HOUSE / "rooms", root / HOUSE / "rooms/den/web", root / HOUSE / "rooms/attic/web"]:
        os.utime(p, (now - 100, now - 100))
    touch(root / HOUSE / "web/house.js", now)
    touch(root / HOUSE / "web/map.jpg", now - 10)   # the data was rebuilt, the picture wasn't
    assert map_stale(str(root), HOUSE)


def test_one_job_until_something_changes(root, app, client, worker):
    touch(root / HOUSE / "house_layout.py", time.time() - 100)
    client.get("/api/houses")
    client.get("/api/houses")
    assert house_jobs(app) == [(HOUSE, "queued")]               # not queued twice
    job = client.post("/api/jobs/claim?kind=house", headers=worker).json()
    client.post(f"/api/jobs/{job['id']}/finish", json={"ok": False, "seconds": 1, "log": "no"}, headers=worker)
    client.get("/api/houses")
    assert house_jobs(app) == [(HOUSE, "failed")]               # a failure isn't retried in a loop
    time.sleep(0.01)
    touch(root / HOUSE / "house_layout.py", time.time() + 5)   # ... until the house changes
    client.get("/api/houses")
    assert house_jobs(app) == [(HOUSE, "failed"), (HOUSE, "queued")]


def test_worker_house_lane(root, tmp_path):
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "house_map.py").write_text(
        "import os, sys\nopen(os.path.join(sys.argv[1], 'web', 'house.js'), 'w').write('window.HOUSE = {};')\n")
    (tools / "house_snapshot.py").write_text(
        "import os, sys\nopen(os.path.join(sys.argv[1], 'web', 'map.jpg'), 'w').write('jpg ' + sys.argv[2])\n")
    hdir = str(root / HOUSE)
    ok, log = worker_mod.house(hdir, tools=str(tools), snap_py=sys.executable)
    assert ok, log
    assert (root / HOUSE / "web/house.js").read_text() == "window.HOUSE = {};"
    assert (root / HOUSE / "web/map.jpg").read_text() == "jpg " + worker_mod.URL


def test_worker_house_lane_stops_on_a_bad_map(root, tmp_path):
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "house_map.py").write_text("import sys\nsys.exit('porch: rooms/porch does not exist')\n")
    (tools / "house_snapshot.py").write_text("raise SystemExit('should not run')\n")
    ok, log = worker_mod.house(str(root / HOUSE), tools=str(tools), snap_py=sys.executable)
    assert not ok and "porch" in log and "should not run" not in log


def test_watch_setting(root):
    from server.app import create_app
    from server.config import Settings
    app = create_app(Settings(root=str(root), db=str(root / "data/w.db"), tools="", watch=0.05))
    from fastapi.testclient import TestClient
    with TestClient(app):
        assert house_jobs(app) == []
        touch(root / HOUSE / "house_layout.py", time.time() + 5)   # the house gets a map while it runs
        time.sleep(0.3)   # the watch syncs by itself, no page asked
        assert house_jobs(app) == [(HOUSE, "queued")]
