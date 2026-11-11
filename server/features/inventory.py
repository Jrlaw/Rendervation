"""Ticking a product off on the Selections checklist.

  POST /api/status  {room, group, item, name, status: need | ordered | have}

Sets that product's status in the room's inventory.json (the name must match, so a stale page can't
change the wrong one) and rebuilds the Selections page and web/inventory.js. (inventory.json moves into
the database in a later step; the checklist's request stays the same.)
"""
import json
import os
import subprocess
import sys
import threading
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..db import Change
from ..deps import current_user, get_db, get_settings
from ..rooms import read_room

router = APIRouter(tags=["selections"])
LOCK = threading.Lock()


class Status(BaseModel):
    room: str
    group: int
    item: int
    name: str
    status: Literal["need", "ordered", "have"]


@router.post("/api/status")
def set_status(body: Status, settings=Depends(get_settings), db=Depends(get_db), user=Depends(current_user)):
    room = read_room(settings.root, body.room)
    path = room and os.path.join(room.dir, "inventory.json")
    if not room or not os.path.isfile(path):
        raise HTTPException(400, "not a room with an inventory")
    with LOCK:
        with open(path, encoding="utf-8") as f:
            inv = json.load(f)
        try:
            it = inv["groups"][body.group]["items"][body.item]
        except (KeyError, IndexError) as e:
            raise HTTPException(400, f"no such item: {e}") from e
        if it["name"] != body.name:
            raise HTTPException(409, "the list changed: reload the page")
        it["status"] = body.status
        with open(path, "w", encoding="utf-8") as f:
            json.dump(inv, f, indent=1, ensure_ascii=False)
            f.write("\n")
        run = subprocess.run([sys.executable, os.path.join(settings.tools, "selections_page.py"), room.dir],
                             capture_output=True, text=True, timeout=60)
    db.add(Change(user=user, room=room.rel, what="status", detail={"name": body.name, "status": body.status}))
    db.commit()
    if run.returncode:
        raise HTTPException(500, "the Selections page didn't rebuild: " + run.stderr[-2000:])
    return {"ok": True}
