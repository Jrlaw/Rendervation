"""Back up the server's database (data/home-render.db) into the private houses repo, so it goes to
your remote with everything else:

    python3 lib/tools/db_backup.py            # then commit and push houses/

  houses/backup/home-render.db     an exact copy, made with SQLite's backup (safe while the server runs)
  houses/backup/home-render.json   every table as JSON, so the history shows what changed

To restore: stop the server, copy houses/backup/home-render.db to data/home-render.db, start it again.
Standard library only.
"""
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def backup(db, out):
    os.makedirs(out, exist_ok=True)
    src = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    copy = os.path.join(out, "home-render.db")
    tmp = copy + ".tmp"
    dst = sqlite3.connect(tmp)
    src.backup(dst)
    dst.close()
    os.replace(tmp, copy)
    src.row_factory = sqlite3.Row
    tables = [r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
    dump = {}
    for t in tables:
        cols = [r[1] for r in src.execute(f'PRAGMA table_info("{t}")')]
        dump[t] = [dict(r) for r in src.execute(f'SELECT * FROM "{t}" ORDER BY {", ".join(f'"{c}"' for c in cols[:2])}')]
    src.close()
    with open(os.path.join(out, "home-render.json"), "w", encoding="utf-8") as f:
        json.dump(dump, f, indent=1, ensure_ascii=False, sort_keys=True, default=str)
        f.write("\n")
    return {t: len(rows) for t, rows in dump.items()}


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "data", "home-render.db")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "houses", "backup")
    counts = backup(db, out)
    print(f"backed up {os.path.relpath(db, ROOT)} to {os.path.relpath(out, ROOT)}/: "
          + ", ".join(f"{t} {n}" for t, n in counts.items()))
