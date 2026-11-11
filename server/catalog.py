"""Houses and rooms: the database is the list (names, card text, order, hidden), and each room's
folder holds its files. sync() keeps the two in step, on start and whenever the list is asked for:

- a folder that isn't listed yet is added: its name and card text from the old hand-written home page
  (houses/index.html, read once per room), else from the house's house.md or the folder's name
- a listed room or house whose folder is gone is flagged `missing` (never deleted: it may come back)
- a house whose whole-house map is out of date gets a `house` job: the worker rebuilds the map
  (lib/tools/house_map.py) and retakes its picture on the home page (lib/tools/house_snapshot.py)

Rooms are folders houses/<house>/rooms/<room> (or examples/...) with a web/index.html.
"""
import datetime
import html
import os
import re

from sqlalchemy import func, select

from .db import House, Job, RoomRow, queue
from .rooms import chosen, designs, find_rooms, read_room

TOPS = ("houses", "examples")


def titled(slug):
    return slug.replace("-", " ").replace("_", " ").capitalize()


def old_home(root):
    """What the hand-written houses/index.html says: {house: (name, map blurb, place)} and
    {room: (name, blurb, place)}, in page order. Empty if there's no such page."""
    path = os.path.join(root, "houses", "index.html")
    houses, rooms = {}, {}
    if not os.path.isfile(path):
        return houses, rooms
    with open(path, encoding="utf-8") as f:
        page = re.sub(r"<!--.*?-->", "", f.read(), flags=re.S)   # its how-to comment has an <h2> in it
    current = None
    for m in re.finditer(r"<h2>(.*?)</h2>|<article class=\"room\">(.*?)</article>", page, re.S):
        if m.group(1) is not None:
            current = [html.unescape(m.group(1)).strip(), None, len(houses)]
            continue
        art = m.group(2)
        href = re.search(r'href="([^"]+)"', art)
        name = re.search(r"<b>(.*?)</b>", art, re.S)
        blurb = re.search(r"<small>(.*?)</small>", art, re.S)
        if not href or not current:
            continue
        clean = lambda x: html.unescape(re.sub(r"\s+", " ", x.group(1))).strip() if x else None  # noqa: E731
        parts = href.group(1).split("/")
        if len(parts) > 2 and parts[1] == "rooms":                    # ours/rooms/office/web/...
            rooms[f"houses/{parts[0]}/rooms/{parts[2]}"] = (clean(name), clean(blurb), len(rooms))
        elif len(parts) > 1 and parts[1] == "web":                    # ours/web/index.html: the house map
            # without its "· 3 modeled": the page counts them itself now
            current[1] = re.sub(r"\s*·?\s*\d+ modeled,?\s*", " · ", clean(blurb) or "").strip(" ·") or None
        houses[f"houses/{parts[0]}"] = tuple(current)
    return houses, rooms


def house_name(root, hid):
    md = os.path.join(root, hid, "house.md")
    if os.path.isfile(md):
        with open(md, encoding="utf-8") as f:
            m = re.match(r"#\s+(.+)", f.read())
        if m:
            return m.group(1).strip()
    return titled(hid.split("/")[1])


def find_houses(root):
    out = []
    for top in TOPS:
        base = os.path.join(root, top)
        for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
            d = os.path.join(base, name)
            if not name.startswith(".") and (os.path.isdir(os.path.join(d, "rooms")) or os.path.isfile(os.path.join(d, "house.md"))):
                out.append(f"{top}/{name}")
    return out


def sync(db, root):
    legacy = None
    here_houses = find_houses(root)
    here_rooms = find_rooms(root)
    next_house = (db.scalar(select(func.max(House.position))) or 0) + 1
    for hid in here_houses:
        row = db.get(House, hid)
        if row is None:
            legacy = legacy or old_home(root)
            name, blurb, place = legacy[0].get(hid, (None, None, None))
            example = hid.startswith("examples/")
            row = House(house=hid, name=name or house_name(root, hid), blurb=blurb,
                        position=(1000 if example else 0) + (place if place is not None else next_house))
            next_house += 1
            db.add(row)
        row.missing = False
    for row in db.scalars(select(House).where(House.house.not_in(here_houses))):
        row.missing = True
    db.flush()
    new = []
    for r in here_rooms:
        row = db.get(RoomRow, r.rel)
        if row is None:   # chosen() makes the row, taking over an old web/chosen.js
            chosen(db, r)
            row = db.get(RoomRow, r.rel)
        if row.name is None:
            new.append((r, row))
        row.missing = False
    if new:
        # the old page's rooms first, in its order, then the rest after whatever's there
        legacy = legacy or old_home(root)
        new.sort(key=lambda x: (x[0].rel not in legacy[1], legacy[1].get(x[0].rel, (0, 0, 0))[2], x[0].rel))
        for r, row in new:
            name, blurb, place = legacy[1].get(r.rel, (None, None, None))
            hid = r.rel.rsplit("/rooms/", 1)[0]
            db.flush()
            last = db.scalar(select(func.max(RoomRow.position)).where(RoomRow.house == hid))
            row.house, row.name, row.blurb = hid, name or titled(r.rel.rsplit("/", 1)[1]), blurb
            row.position = place if place is not None else (last + 1 if last is not None else 0)
    for row in db.scalars(select(RoomRow).where(RoomRow.room.not_in([r.rel for r in here_rooms]))):
        row.missing = True
    for hid in here_houses:
        if map_stale(root, hid) and not map_job_since(db, hid, map_sources(root, hid)):
            queue(db, hid, "house")
    db.commit()


def mtime(path):
    try:
        return os.stat(path).st_mtime
    except OSError:
        return 0


def map_sources(root, hid):
    """When the newest thing house_map.py reads last changed: house_layout.py, the rooms folder (a room
    added or removed), and each room's layout.py, README.md (its status line) and web/ (its pages)."""
    house = os.path.join(root, hid)
    rooms = os.path.join(house, "rooms")
    times = [mtime(os.path.join(house, "house_layout.py")), mtime(rooms)]
    for name in os.listdir(rooms) if os.path.isdir(rooms) else []:
        times += [mtime(os.path.join(rooms, name, f)) for f in ("layout.py", "README.md", "web")]
    return max(times)


def map_stale(root, hid):
    """The house has a map (house_layout.py) and its data (web/house.js) or picture (web/map.jpg) is
    missing or older than what they're made from."""
    house = os.path.join(root, hid)
    if not os.path.isfile(os.path.join(house, "house_layout.py")):
        return False
    data, pic = mtime(os.path.join(house, "web", "house.js")), mtime(os.path.join(house, "web", "map.jpg"))
    return not data or data < map_sources(root, hid) or not pic or pic < data


def map_job_since(db, hid, since):
    """A house job made after the last change: waiting, running or finished (even failed: it's not
    tried again until something changes)."""
    last = db.scalars(select(Job).where(Job.room == hid, Job.kind == "house").order_by(Job.id.desc())).first()
    return bool(last) and last.created.replace(tzinfo=datetime.timezone.utc).timestamp() >= since


def card(room, chosen_id):
    """The room's picture on the home page: the chosen design's card, else the first design's, else a
    render or before photo from its first camera."""
    web = os.path.join(room.dir, "web")
    first = room.own[0][0] if room.own else None
    for rel in ([f"cards/{chosen_id}.jpg"] if chosen_id else []) + ([f"cards/{first}.jpg"] if first else []) + \
               ([f"renders/day/{room.camera}.jpg"] if room.camera else []) + ["before/photo1.jpg"]:
        if os.path.isfile(os.path.join(web, rel)):
            return f"/{room.rel}/web/{rel}"
    return None


def modeled(room):
    """Exported for the walkthrough (render.sh --export web): a room still at intake has its pages but
    no model, so its walkthrough and Plans have nothing to draw."""
    return os.path.isfile(os.path.join(room.dir, "web", "scene.json"))


def links(room):
    web = os.path.join(room.dir, "web")
    base = f"/{room.rel}/web/"
    if not modeled(room):
        return [["Selections", base + "selections.html"]] if os.path.isfile(os.path.join(web, "selections.html")) else []
    out = [["Walk through", base + "index.html"], ["Renders", base + "index.html#gallery"]]
    for page, label in (("plans.html", "Plans"), ("selections.html", "Selections")):
        if os.path.isfile(os.path.join(web, page)):
            out.append([label, base + page])
    return out


def room_out(db, root, row):
    r = read_room(root, row.room)
    c = chosen(db, r) if r else None
    return {"room": row.room, "name": row.name, "blurb": row.blurb, "hidden": row.hidden, "missing": row.missing,
            "position": row.position, "modeled": bool(r and modeled(r)), "chosen": c,
            "chosen_label": next((d["label"] for d in designs(db, r) if d["id"] == c), None) if r and c else None,
            "card": card(r, c) if r else None, "links": links(r) if r else []}


def house_out(db, root, row):
    rooms = db.scalars(select(RoomRow).where(RoomRow.house == row.house).order_by(RoomRow.position, RoomRow.room))
    out = [room_out(db, root, x) for x in rooms]
    web = os.path.join(root, row.house, "web")
    mapcard = None
    if os.path.isfile(os.path.join(web, "index.html")):
        mapcard = {"card": f"/{row.house}/web/map.jpg" if os.path.isfile(os.path.join(web, "map.jpg")) else None,
                   "links": [["Map", f"/{row.house}/web/index.html"], ["3D", f"/{row.house}/web/index.html?3d"]]}
    return {"house": row.house, "name": row.name, "blurb": row.blurb, "position": row.position,
            "example": row.house.startswith("examples/"), "missing": row.missing, "map": mapcard,
            "modeled": sum(1 for x in out if x["modeled"] and not x["hidden"] and not x["missing"]), "rooms": out}


def renumber(db, house, room, to):
    """Move a room to place `to` among its house's rooms (0 = first), renumbering the rest 0, 1, 2..."""
    rows = list(db.scalars(select(RoomRow).where(RoomRow.house == house).order_by(RoomRow.position, RoomRow.room)))
    moving = next(x for x in rows if x.room == room)
    rows.remove(moving)
    rows.insert(max(0, min(to, len(rows))), moving)
    for k, x in enumerate(rows):
        x.position = k

