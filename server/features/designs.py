"""A room's designs on the web: list them, choose one, hide or show, rename, reorder.

  GET   /api/rooms/{room}/designs               {designs: [{id, label, hidden, first}], chosen}
  PUT   /api/rooms/{room}/choice                {design, camera?, snapshot?}
  PATCH /api/rooms/{room}/designs/{design}      {label?, hidden?, position?}

The first design (the room's own export: As it is, where the room has one) can't be hidden or moved,
and the chosen one can't be hidden. Choosing makes the design's card (web/cards/<id>.jpg) if it has none.
"""
import base64
import io
import os
import re

from fastapi import APIRouter, Depends, HTTPException
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..db import Change, DesignSetting, RoomRow
from ..deps import current_user, get_db
from ..rooms import card_url, chosen, designs, load_room

router = APIRouter(tags=["designs"])


class Choice(BaseModel):
    design: str
    camera: str | None = None
    snapshot: str | None = Field(None, max_length=8_000_000)   # data:image/jpeg;base64,...


class DesignEdit(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=80)
    hidden: bool | None = None
    position: int | None = Field(None, ge=1, le=99)


def make_card(room, design, first, camera, snapshot):
    """A design's home-page card, 800px wide: its day render from the room's first camera when it has
    one (web/renders, or web/variants/<id>/renders), else the walkthrough's snapshot of the 3D view."""
    card = os.path.join(room.dir, "web", "cards", design + ".jpg")
    base = os.path.join(room.dir, "web") if first else os.path.join(room.dir, "web", "variants", design)
    render = os.path.join(base, "renders", "day", f"{camera}.jpg")
    if camera and re.fullmatch(r"[\w-]+", camera) and os.path.isfile(render):
        src = render
    elif snapshot and snapshot.startswith("data:image/jpeg;base64,"):
        src = io.BytesIO(base64.b64decode(snapshot.split(",", 1)[1]))
    else:
        return None
    img = Image.open(src).convert("RGB")
    img.thumbnail((800, 800))
    os.makedirs(os.path.dirname(card), exist_ok=True)
    img.save(card, quality=85)
    return card


def one(db, room, design):
    d = next((d for d in designs(db, room) if d["id"] == design), None)
    if not d:
        raise HTTPException(404, "not one of this room's designs")
    return d


@router.get("/api/rooms/{room:path}/designs")
def get_designs(room=Depends(load_room), db=Depends(get_db)):
    return {"designs": designs(db, room), "chosen": chosen(db, room)}


@router.put("/api/rooms/{room:path}/choice")
def choose(body: Choice, room=Depends(load_room), db=Depends(get_db), user=Depends(current_user)):
    d = one(db, room, body.design)
    if d["hidden"]:
        raise HTTPException(409, "that design is hidden: show it first")
    camera = body.camera or room.camera
    made = None
    if not card_url(room, d["id"]):
        made = make_card(room, d["id"], d["first"], camera, body.snapshot)
    row = db.get(RoomRow, room.rel) or RoomRow(room=room.rel)
    row.chosen = d["id"]
    db.merge(row)
    db.add(Change(user=user, room=room.rel, what="choose", detail={"design": d["id"], "card_made": bool(made)}))
    db.commit()
    return {"ok": True, "chosen": d["id"], "card": card_url(room, d["id"])}


@router.patch("/api/rooms/{room:path}/designs/{design}")
def edit_design(design: str, body: DesignEdit, room=Depends(load_room), db=Depends(get_db),
                user=Depends(current_user)):
    d = one(db, room, design)
    if d["first"] and (body.hidden or body.position is not None):
        raise HTTPException(409, "the room's own design stays first and can't be hidden")
    if body.hidden and chosen(db, room) == design:
        raise HTTPException(409, "that's the chosen design: choose another first")
    s = db.get(DesignSetting, (room.rel, design)) or DesignSetting(room=room.rel, design=design, hidden=False)
    if body.label is not None:
        s.label = body.label.strip()
        db.add(Change(user=user, room=room.rel, what="rename", detail={"design": design, "label": s.label}))
    if body.hidden is not None:
        s.hidden = body.hidden
        db.add(Change(user=user, room=room.rel, what="hide" if body.hidden else "show", detail={"design": design}))
    if body.position is not None:
        s.position = body.position
        db.add(Change(user=user, room=room.rel, what="move", detail={"design": design, "position": body.position}))
    db.merge(s)
    db.commit()
    return {"designs": designs(db, room), "chosen": chosen(db, room)}


@router.get("/api/rooms/{room:path}/changes")
def changes(room=Depends(load_room), db=Depends(get_db)):
    rows = db.scalars(select(Change).where(Change.room == room.rel).order_by(Change.id.desc()).limit(200))
    return [{"at": c.at.isoformat() + "Z", "user": c.user, "what": c.what, "detail": c.detail} for c in rows]
