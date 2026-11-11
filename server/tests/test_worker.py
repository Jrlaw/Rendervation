"""The worker (lib/worker.py) against the real API: it claims jobs, runs the room's render.sh and reports."""
import importlib.util
import os
import threading

import pytest

from server.config import REPO

from .conftest import DEN

spec = importlib.util.spec_from_file_location("worker", os.path.join(REPO, "lib/worker.py"))
worker_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker_mod)


class ClientApi:
    """The worker's Api, over the test client instead of a socket."""

    def __init__(self, client, token):
        self.client, self.token = client, token

    def call(self, path, body=None):
        r = self.client.post(path, json=body or {}, headers={"X-Worker-Token": self.token})
        return r.json() if r.status_code == 200 else None


def test_export_job_runs_render_sh(client, app, root):
    job = client.post("/api/dimension", json={"room": DEN, "name": "den_w", "value": 100, "src": "measured"}).json()["job"]
    api = ClientApi(client, app.state.worker_token)
    claimed = api.call("/api/jobs/claim?kind=export")
    ok, log = worker_mod.export(os.path.join(str(root), claimed["room"]))
    assert ok and "EXPORTED" in log
    api.call(f"/api/jobs/{job}/finish", {"ok": ok, "seconds": 0.1, "log": log})
    assert client.get(f"/api/jobs/{job}").json()["status"] == "done"


def test_bake_swaps_files_in(root):
    den = root / DEN   # render.sh --export web/.bake --bake
    (den / "render.sh").write_text('#!/bin/sh\nmkdir -p "$2"; echo baked > "$2/model.glb"; echo EXPORTED\n')
    (den / "web/model.glb").write_text("unbaked")
    ok, _ = worker_mod.bake(str(den))
    assert ok
    assert (den / "web/model.glb").read_text() == "baked\n"
    assert not (den / "web/.bake").exists()


def test_failed_bake_leaves_web_alone(root):
    den = root / DEN
    (den / "render.sh").write_text('#!/bin/sh\nmkdir -p "$2"; echo broken > "$2/model.glb"; echo oops\n')
    (den / "web/model.glb").write_text("unbaked")
    ok, log = worker_mod.bake(str(den))
    assert not ok and "oops" in log
    assert (den / "web/model.glb").read_text() == "unbaked"


def test_lane_reports_a_crash_and_keeps_going(client, app, root, monkeypatch):
    job = client.post("/api/dimension", json={"room": DEN, "name": "den_w", "value": 100, "src": "measured"}).json()["job"]

    def boom(rdir):
        raise RuntimeError("no Blender here")
    monkeypatch.setitem(worker_mod.RUN, "export", boom)
    stop = threading.Event()
    monkeypatch.setattr(worker_mod.time, "sleep", lambda s: stop.set() or (_ for _ in ()).throw(SystemExit))
    with pytest.raises(SystemExit):
        worker_mod.lane(ClientApi(client, app.state.worker_token), "export", str(root))
    j = client.get(f"/api/jobs/{job}").json()
    assert j["status"] == "failed" and "no Blender here" in j["log"]
