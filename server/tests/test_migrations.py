"""The schema migrations: a new database, and one made before migrations (2026-11-11), both end up on
the latest schema with nothing lost."""
import sqlite3

import sqlalchemy as sa

from server import db as dbm


def columns(path, table):
    with sqlite3.connect(path) as c:
        return [r[1] for r in c.execute(f"PRAGMA table_info({table})")]


def test_new_database(tmp_path):
    path = str(tmp_path / "new.db")
    dbm.connect(path)
    assert {"house", "name", "blurb", "position", "hidden", "missing", "chosen"} <= set(columns(path, "rooms"))
    assert columns(path, "houses") == ["house", "name", "blurb", "position", "missing"]
    with sqlite3.connect(path) as c:
        assert c.execute("SELECT version_num FROM alembic_version").fetchone() == ("0002",)


def test_database_from_before_migrations(tmp_path):
    """The first server made its tables with create_all and had no alembic_version."""
    path = str(tmp_path / "old.db")
    with sqlite3.connect(path) as c:
        c.executescript("""
            CREATE TABLE rooms (room VARCHAR PRIMARY KEY, chosen VARCHAR);
            CREATE TABLE design_settings (room VARCHAR, design VARCHAR, label VARCHAR, position INTEGER,
                                          hidden BOOLEAN NOT NULL, PRIMARY KEY (room, design));
            CREATE TABLE changes (id INTEGER PRIMARY KEY, at DATETIME NOT NULL, user VARCHAR NOT NULL,
                                  room VARCHAR NOT NULL, what VARCHAR NOT NULL, detail JSON NOT NULL);
            CREATE TABLE jobs (id INTEGER PRIMARY KEY, room VARCHAR NOT NULL, kind VARCHAR NOT NULL,
                               status VARCHAR NOT NULL, created DATETIME NOT NULL, started DATETIME,
                               finished DATETIME, seconds FLOAT, log TEXT NOT NULL, after INTEGER);
            INSERT INTO rooms VALUES ('houses/ours/rooms/office', 'layout_i');
            INSERT INTO design_settings VALUES ('houses/ours/rooms/office', 'asis', 'Before', NULL, 0);
        """)
    engine, sessions = dbm.connect(path)
    with sessions() as s:
        office = s.get(dbm.RoomRow, "houses/ours/rooms/office")
        assert office.chosen == "layout_i" and office.hidden is False and office.name is None
        assert s.get(dbm.DesignSetting, ("houses/ours/rooms/office", "asis")).label == "Before"
    assert "houses" in sa.inspect(engine).get_table_names()


def test_connecting_again_is_harmless(tmp_path):
    path = str(tmp_path / "again.db")
    _, sessions = dbm.connect(path)
    with sessions() as s:
        s.add(dbm.RoomRow(room="houses/a/rooms/b", chosen="x"))
        s.commit()
    _, sessions = dbm.connect(path)
    with sessions() as s:
        assert s.get(dbm.RoomRow, "houses/a/rooms/b").chosen == "x"
