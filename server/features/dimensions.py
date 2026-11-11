"""Correcting a size in the walkthrough.

  POST /api/dimension  {room, name, value, src, note}   (or reset: true)

Records the value in the room's dimensions.json (lib/roomkit/dimensions.py: it's the model's input,
so it stays with the room's files) and queues a re-export for the worker. The page then follows the
job (GET /api/jobs/{id}); when the export is done the worker bakes the lighting again (~8 min).
"""
import datetime
import json
import os
import sys

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..config import REPO
from ..db import Change, queue
from ..deps import current_user, get_db, get_settings
from ..rooms import read_room

sys.path.insert(0, os.path.join(REPO, "lib"))
from roomkit import dimensions  # noqa: E402

router = APIRouter(tags=["dimensions"])


class Dimension(BaseModel):
    room: str
    name: str
    value: float | None = None
    src: str = "measured"
    note: str = Field("", max_length=2000)
    reset: bool = False


@router.post("/api/dimension")
def set_dimension(body: Dimension, settings=Depends(get_settings), db=Depends(get_db), user=Depends(current_user)):
    room = read_room(settings.root, body.room)
    if not room or not os.path.isfile(os.path.join(room.dir, "render.sh")):
        raise HTTPException(400, "not a room")
    path = os.path.join(room.dir, dimensions.FILE)
    with open(path, encoding="utf-8") as f:
        known = json.load(f).get("dimensions", {})
    if body.name not in known:
        raise HTTPException(400, f"no dimension named {body.name}")
    if body.reset:
        known[body.name]["override"] = False
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"units": "inches", "dimensions": known}, f, indent=1)
            f.write("\n")
    else:
        if body.value is None or not 0 < body.value < 5000 or body.src not in dimensions.SOURCES:
            raise HTTPException(400, "value or source out of range")
        dimensions.set_override(path, body.name, body.value, body.src, body.note[:300],
                                datetime.date.today().isoformat())
    db.add(Change(user=user, room=room.rel, what="dimension",
                  detail={"name": body.name, "value": body.value, "src": body.src, "reset": body.reset}))
    job = queue(db, room.rel, "export")
    db.commit()
    return {"ok": True, "job": job.id}
