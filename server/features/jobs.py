"""Blender work. The server (in its container) has no Blender, so edits that need one queue a job here
and lib/worker.py, running on this computer next to Blender and the GPU, does it.

  GET  /api/jobs/{id}              the page follows its job: {id, kind, status, seconds, log}
  POST /api/jobs/claim?kind=...    worker: the oldest queued job of that kind, now running (204: none):
                                   export, bake (a room), house (rebuild a house's map and its picture), or
                                   backup (the database into houses/backup/, committed and pushed)
  POST /api/jobs/{id}/finish       worker: {ok, seconds, log}. A finished export queues the room's bake.

The worker's calls carry the token in data/worker.token (X-Worker-Token), which the server writes on start.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select

from ..db import Job, now, queue
from ..deps import get_db

router = APIRouter(tags=["jobs"])


def public(job):
    return {"id": job.id, "room": job.room, "kind": job.kind, "status": job.status,
            "seconds": job.seconds, "log": job.log if job.status == "failed" else ""}


def worker(request: Request, x_worker_token: str = Header("")):
    if x_worker_token != request.app.state.worker_token:
        raise HTTPException(403, "worker only")


class Finish(BaseModel):
    ok: bool
    seconds: float
    log: str = ""


@router.get("/api/jobs/{job_id}")
def get_job(job_id: int, db=Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "no such job")
    return public(job)


@router.post("/api/jobs/claim", dependencies=[Depends(worker)])
def claim(kind: Literal["export", "bake", "house", "backup"], db=Depends(get_db)):
    job = db.scalars(select(Job).where(Job.kind == kind, Job.status == "queued").order_by(Job.id)).first()
    if not job:
        return Response(status_code=204)
    job.status, job.started = "running", now()
    db.commit()
    return public(job)


@router.post("/api/jobs/{job_id}/finish", dependencies=[Depends(worker)])
def finish(job_id: int, body: Finish, db=Depends(get_db)):
    job = db.get(Job, job_id)
    if not job or job.status != "running":
        raise HTTPException(409, "not a running job")
    job.status = "done" if body.ok else "failed"
    job.finished, job.seconds, job.log = now(), round(body.seconds, 1), body.log[-4000:]
    if body.ok and job.kind == "export":
        queue(db, job.room, "bake", after=job.id)
    db.commit()
    return public(job)
