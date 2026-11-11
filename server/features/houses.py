"""Houses and rooms for the home page, and editing them there.

  GET   /api/houses             every house in order, each with its rooms (hidden and missing ones
                                flagged), cards and links: what the home page draws
  GET   /api/rooms              every room, flat
  PATCH /api/houses/{house}     {name?, blurb?, position?}
  PATCH /api/rooms/{room}       {name?, blurb?, hidden?, position?}   position: place in its house, 0 first

Both lists sync with the folders first (server/catalog.py), so a new room shows up without a restart.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..catalog import house_out, renumber, room_out, sync
from ..db import Change, House, RoomRow
from ..deps import current_user, get_db, get_settings
from ..rooms import room_path

router = APIRouter(tags=["houses"])


class HouseEdit(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=80)
    blurb: str | None = Field(None, max_length=200)
    position: int | None = Field(None, ge=0, le=9999)


class RoomEdit(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=80)
    blurb: str | None = Field(None, max_length=200)
    hidden: bool | None = None
    position: int | None = Field(None, ge=0, le=999)


def log(db, user, where, what, detail):
    db.add(Change(user=user, room=where, what=what, detail=detail))


@router.get("/api/houses")
def list_houses(settings=Depends(get_settings), db=Depends(get_db)):
    sync(db, settings.root)
    rows = db.scalars(select(House).order_by(House.position, House.house))
    return [house_out(db, settings.root, h) for h in rows]


@router.get("/api/rooms")
def list_rooms(settings=Depends(get_settings), db=Depends(get_db)):
    sync(db, settings.root)
    rows = db.scalars(select(RoomRow).where(RoomRow.house.is_not(None)).order_by(RoomRow.house, RoomRow.position))
    return [room_out(db, settings.root, r) for r in rows]


@router.patch("/api/houses/{house:path}")
def edit_house(house: str, body: HouseEdit, settings=Depends(get_settings), db=Depends(get_db),
               user=Depends(current_user)):
    sync(db, settings.root)
    row = db.get(House, house.strip("/"))
    if not row:
        raise HTTPException(404, "no such house")
    changed = body.model_dump(exclude_none=True)
    if "name" in changed:
        row.name = body.name.strip()
    if "blurb" in changed:
        row.blurb = body.blurb.strip() or None
    if "position" in changed:
        row.position = body.position
    log(db, user, row.house, "edit house", changed)
    db.commit()
    return house_out(db, settings.root, row)


@router.patch("/api/rooms/{room:path}")
def edit_room(room: str, body: RoomEdit, settings=Depends(get_settings), db=Depends(get_db),
              user=Depends(current_user)):
    sync(db, settings.root)
    rel = room_path(room)
    row = rel and db.get(RoomRow, rel)
    if not row or row.house is None:
        raise HTTPException(404, "no such room")
    changed = body.model_dump(exclude_none=True)
    if "name" in changed:
        row.name = body.name.strip()
    if "blurb" in changed:
        row.blurb = body.blurb.strip() or None
    if "hidden" in changed:
        row.hidden = body.hidden
    if "position" in changed:
        renumber(db, row.house, row.room, body.position)
    what = "hide room" if body.hidden else "show room" if body.hidden is False else "edit room"
    log(db, user, row.room, what, changed)
    db.commit()
    return room_out(db, settings.root, row)
