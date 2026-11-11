"""Backups: an edit on the web queues one, lib/tools/db_backup.py writes the JSON and restores from it,
and the worker commits only the backup in the houses repo and pushes it."""
import importlib.util
import json
import os
import subprocess

from server import db as dbm
from server.config import REPO

from .conftest import DEN


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(REPO, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


backup_mod = load("db_backup", "lib/tools/db_backup.py")
worker_mod = load("worker", "lib/worker.py")


def backups(app):
    with app.state.sessions() as s:
        return [j.status for j in s.query(dbm.Job).filter(dbm.Job.kind == "backup")]


def live_db(tmp_path):
    path = str(tmp_path / "live.db")
    _, sessions = dbm.connect(path)
    with sessions() as s:
        s.add(dbm.House(house="houses/ours", name="Our house", position=0))
        s.add(dbm.RoomRow(room="houses/ours/rooms/office", house="houses/ours", name="Office", chosen="layout_i"))
        s.add(dbm.Change(user="local", room="houses/ours/rooms/office", what="choose", detail={"design": "layout_i"}))
        s.add(dbm.Job(room="houses/ours/rooms/office", kind="export", status="done"))
        s.commit()
    return path


def test_an_edit_queues_one_backup(root):
    from fastapi.testclient import TestClient

    from server.app import create_app
    from server.config import Settings
    app = create_app(Settings(root=str(root), db=str(root / "data/b.db"), tools="", watch=0, backup=True))
    with TestClient(app) as client:
        client.get("/api/houses")
        assert backups(app) == []                                  # reading isn't an edit
        client.patch(f"/api/rooms/{DEN}", json={"name": "Den"})
        client.put(f"/api/rooms/{DEN}/choice", json={"design": "asis"})
        assert backups(app) == ["queued"]                          # two edits, one backup waiting


def test_backups_off(client, app):
    client.patch(f"/api/rooms/{DEN}", json={"name": "Den"})
    assert backups(app) == []                                      # the test app has HR_BACKUP off


def test_json_backup_and_restore(tmp_path):
    path = live_db(tmp_path)
    out = str(tmp_path / "backup/home-render.json")
    counts = backup_mod.backup(path, out)
    assert counts["rooms"] == 1 and counts["jobs"] == 0             # the worker's log isn't backed up
    data = json.loads(open(out).read())
    assert data["tables"]["rooms"][0]["chosen"] == "layout_i"
    assert any(sql.startswith("CREATE TABLE jobs") for sql in data["schema"])

    restored = str(tmp_path / "restored.db")
    open(restored, "w").write("old")
    backup_mod.restore(out, restored)
    assert open(restored + ".before-restore").read() == "old"
    _, sessions = dbm.connect(restored)                            # opens, and migrations find it current
    with sessions() as s:
        office = s.get(dbm.RoomRow, "houses/ours/rooms/office")
        assert office.name == "Office" and office.hidden is False
        assert s.query(dbm.Change).one().detail == {"design": "layout_i"}


def test_backup_twice_is_identical(tmp_path):
    path = live_db(tmp_path)
    a, b = str(tmp_path / "a.json"), str(tmp_path / "b.json")
    backup_mod.backup(path, a)
    backup_mod.backup(path, b)
    assert open(a).read() == open(b).read()                        # nothing changed: nothing to commit


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True).stdout


def houses_repo(tmp_path):
    remote, houses = tmp_path / "remote.git", tmp_path / "houses"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(houses)], check=True, capture_output=True)
    for k, v in (("user.name", "Test"), ("user.email", "test@example.com")):
        git(houses, "config", k, v)
    (houses / "notes.md").write_text("first\n")
    git(houses, "add", "notes.md")
    git(houses, "commit", "-q", "-m", "first")
    git(houses, "push", "-q", "-u", "origin", "main")
    return remote, houses


def test_worker_commits_only_the_backup_and_pushes(tmp_path):
    remote, houses = houses_repo(tmp_path)
    (houses / "notes.md").write_text("work in progress\n")         # someone's uncommitted work
    ok, log = worker_mod.backup(str(houses), db=live_db(tmp_path), wait=0)
    assert ok, log
    assert git(remote, "log", "--format=%s", "-1") == "Backup: the database after edits on the web (automatic)\n"
    assert git(houses, "show", "--name-only", "--format=", "HEAD").split() == ["backup/home-render.json"]
    assert git(houses, "status", "--short") == " M notes.md\n"     # left as it was

    ok, log = worker_mod.backup(str(houses), db=str(tmp_path / "live.db"), wait=0)
    assert ok and "no change" in log
    assert git(remote, "rev-list", "--count", "HEAD") == "2\n"     # no empty commit


def test_worker_backup_push_failure_is_reported(tmp_path):
    remote, houses = houses_repo(tmp_path)
    git(houses, "remote", "set-url", "origin", str(tmp_path / "nowhere.git"))
    ok, log = worker_mod.backup(str(houses), db=live_db(tmp_path), wait=0)
    assert not ok
    assert git(houses, "log", "--format=%s", "-1").startswith("Backup:")   # committed; pushed next time


def test_worker_backup_without_git(tmp_path):
    """Most people's houses/ isn't a git repo: the JSON is written and that's the backup."""
    houses = tmp_path / "houses"
    houses.mkdir()
    ok, log = worker_mod.backup(str(houses), db=live_db(tmp_path), wait=0)
    assert ok and "isn't a git repo" in log
    assert json.loads((houses / "backup/home-render.json").read_text())["tables"]["rooms"][0]["name"] == "Office"


def test_worker_backup_git_without_remote(tmp_path):
    houses = tmp_path / "houses"
    houses.mkdir()
    subprocess.run(["git", "init", "-q", str(houses)], check=True)
    ok, log = worker_mod.backup(str(houses), db=live_db(tmp_path), wait=0)
    assert ok and "no remote" in log
