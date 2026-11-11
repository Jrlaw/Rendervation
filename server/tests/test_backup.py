"""lib/tools/db_backup.py: an exact copy and a JSON export of the database, which restores."""
import importlib.util
import json
import os

from server import db as dbm
from server.config import REPO

spec = importlib.util.spec_from_file_location("db_backup", os.path.join(REPO, "lib/tools/db_backup.py"))
backup_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup_mod)


def test_backup_and_restore(tmp_path):
    path = str(tmp_path / "live.db")
    _, sessions = dbm.connect(path)
    with sessions() as s:
        s.add(dbm.House(house="houses/ours", name="Our house", position=0))
        s.add(dbm.RoomRow(room="houses/ours/rooms/office", house="houses/ours", name="Office", chosen="layout_i"))
        s.add(dbm.Change(user="local", room="houses/ours/rooms/office", what="choose", detail={"design": "layout_i"}))
        s.commit()
    counts = backup_mod.backup(path, str(tmp_path / "backup"))
    assert counts["rooms"] == 1 and counts["houses"] == 1 and counts["changes"] == 1

    dump = json.loads((tmp_path / "backup/home-render.json").read_text())
    assert dump["rooms"][0]["chosen"] == "layout_i" and dump["alembic_version"] == [{"version_num": "0002"}]

    _, restored = dbm.connect(str(tmp_path / "backup/home-render.db"))   # opens and migrates cleanly
    with restored() as s:
        assert s.get(dbm.RoomRow, "houses/ours/rooms/office").name == "Office"
    assert not (tmp_path / "backup/home-render.db.tmp").exists()
