"""Rooms on disk, and their designs as the web sees them: the room's own list (the `variants` in
web/index.html, the first being web/ itself) with the database's edits on top."""
import os
import re
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from sqlalchemy import select

from .db import DesignSetting, RoomRow
from .deps import get_db, get_settings

VARIANTS = re.compile(r"variants: (\[.*?\]\]),", re.S)
PAIR = re.compile(r'\["([\w-]+)", "([^"]*)"\]')
CAMERA = re.compile(r'(?:pairs|views): \[\["([\w-]+)"')
CHOSEN_JS = re.compile(r'window\.CHOSEN = "([\w-]+)"')


@dataclass
class Room:
    rel: str      # houses/<house>/rooms/<room>
    dir: str      # on disk
    own: list     # [(id, label)] from web/index.html, in order; [] for a room with one design
    camera: str | None   # the room's first camera (pairs, else views): the card's view


def room_path(rel):
    """houses/<house>/rooms/<room> (or examples/...) normalized, or None if it isn't one."""
    rel = os.path.normpath(rel.strip("/")).replace(os.sep, "/")
    parts = rel.split("/")
    if len(parts) != 4 or parts[0] not in ("houses", "examples") or parts[2] != "rooms":
        return None
    if any(p in ("", ".", "..") or p.startswith(".") for p in parts):
        return None
    return rel


def read_room(root, rel):
    rel = room_path(rel)
    page = os.path.join(root, rel or "", "web", "index.html")
    if not rel or not os.path.isfile(page):
        return None
    with open(page, encoding="utf-8") as f:
        text = f.read()
    m = VARIANTS.search(text)
    cam = CAMERA.search(text)
    return Room(rel=rel, dir=os.path.join(root, rel), own=PAIR.findall(m.group(1)) if m else [],
                camera=cam.group(1) if cam else None)


def find_rooms(root):
    """Every room with a walkthrough, houses first."""
    out = []
    for top in ("houses", "examples"):
        base = os.path.join(root, top)
        for house in sorted(os.listdir(base)) if os.path.isdir(base) else []:
            rooms = os.path.join(base, house, "rooms")
            for name in sorted(os.listdir(rooms)) if os.path.isdir(rooms) else []:
                r = read_room(root, f"{top}/{house}/rooms/{name}")
                if r:
                    out.append(r)
    return out


def load_room(room: str, settings=Depends(get_settings)):
    """The dependency every room route uses: 404 for anything that isn't a room."""
    r = read_room(settings.root, room)
    if not r:
        raise HTTPException(404, "no such room")
    return r


def designs(db, room):
    """The room's designs for the pages: [{id, label, hidden, first}], in order. The first (the room's
    own export, As it is where there is one) always stays first."""
    own = room.own or []
    edits = {s.design: s for s in db.scalars(select(DesignSetting).where(DesignSetting.room == room.rel))}
    out = []
    for k, (did, label) in enumerate(own):
        s = edits.get(did)
        out.append({"id": did, "label": (s and s.label) or label, "hidden": bool(s and s.hidden), "first": k == 0,
                    # a design moved to a place goes ahead of one that's there by the room's own order
                    "_pos": (0, 0, 0) if k == 0 else (1, s.position, 0) if s and s.position is not None else (1, k, 1)})
    out.sort(key=lambda d: d.pop("_pos"))
    return out


def chosen(db, room):
    """The room's chosen design, if it still has it and it isn't hidden. Rooms chosen before the
    database (web/chosen.js) are taken over the first time they're asked about."""
    row = db.get(RoomRow, room.rel)
    if row is None:
        row = RoomRow(room=room.rel, chosen=None)
        old = os.path.join(room.dir, "web", "chosen.js")
        if os.path.isfile(old):
            with open(old, encoding="utf-8") as f:
                m = CHOSEN_JS.search(f.read())
            row.chosen = m.group(1) if m else None
        db.add(row)
        db.commit()
    live = {d["id"] for d in designs(db, room) if not d["hidden"]}
    return row.chosen if row.chosen in live else None


def card_url(room, design):
    """The room's home-page picture for a design, if it has one."""
    if design and os.path.isfile(os.path.join(room.dir, "web", "cards", design + ".jpg")):
        return f"/{room.rel}/web/cards/{design}.jpg"
    return None
