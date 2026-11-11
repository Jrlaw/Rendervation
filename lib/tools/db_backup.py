"""Back up the server's database (data/home-render.db) into houses/ as JSON, so a copy of houses/
keeps it too. The server's worker does this by itself after every edit on the web (and, when
houses/ is a git repo with a remote, commits and pushes it); by hand:

    python3 lib/tools/db_backup.py                       # writes houses/backup/home-render.json

The JSON has every table's definition and rows (not the jobs table's rows: that's the worker's log,
not your data), sorted, so git keeps only what changed and its history shows each edit. To restore,
stop the server, then:

    python3 lib/tools/db_backup.py --restore             # houses/backup/home-render.json -> data/home-render.db

(an existing data/home-render.db is kept as data/home-render.db.before-restore). Standard library only.
"""
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = os.path.join(ROOT, "data", "home-render.db")
OUT = os.path.join(ROOT, "houses", "backup", "home-render.json")
SKIP_ROWS = {"jobs"}   # the worker's log: its table is kept, its rows aren't


def backup(db=DB, out=OUT):
    """Write the JSON; returns {table: rows written}."""
    src = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    schema = [r[0] for r in src.execute(
        "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY type DESC, name")]
    tables = {}
    for (t,) in src.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        if t in SKIP_ROWS:
            tables[t] = []
            continue
        cols = [r[1] for r in src.execute(f'PRAGMA table_info("{t}")')]
        order = ", ".join(f'"{c}"' for c in cols[:2])
        tables[t] = [dict(r) for r in src.execute(f'SELECT * FROM "{t}" ORDER BY {order}')]
    src.close()
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"schema": schema, "tables": tables}, f, indent=1, ensure_ascii=False, sort_keys=True, default=str)
        f.write("\n")
    os.replace(tmp, out)
    return {t: len(rows) for t, rows in tables.items()}


def restore(src=OUT, db=DB):
    """Rebuild the database from the JSON. The old file, if any, is moved aside first."""
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    if os.path.exists(db):
        os.replace(db, db + ".before-restore")
        for ext in ("-wal", "-shm"):
            if os.path.exists(db + ext):
                os.remove(db + ext)
    con = sqlite3.connect(db)
    with con:
        for sql in data["schema"]:
            con.execute(sql)
        for t, rows in data["tables"].items():
            for r in rows:   # values come back as SQLite stored them (JSON columns as text)
                cols = ", ".join(f'"{c}"' for c in r)
                con.execute(f'INSERT INTO "{t}" ({cols}) VALUES ({", ".join("?" for _ in r)})', list(r.values()))
    con.close()
    return {t: len(rows) for t, rows in data["tables"].items()}


if __name__ == "__main__":
    if sys.argv[1:2] == ["--restore"]:
        counts = restore(*sys.argv[2:4])
        print("restored " + ", ".join(f"{t} {n}" for t, n in counts.items()))
    else:
        counts = backup(*sys.argv[1:3])
        print("backed up " + ", ".join(f"{t} {n}" for t, n in counts.items()))
