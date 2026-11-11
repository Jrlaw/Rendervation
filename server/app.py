"""create_app(): the API (one router per feature, server/features) and the pages.

Pages are the repo's own files, served as they are: the home page, houses/ and examples/, the shared
lib/web/ and template/. Nothing else (data/, the code, dot-folders like .git) is served.
Run it with lib/serve.sh (the container), or for a quick look without one:
    uvicorn server.app:app --host 127.0.0.1 --port 8000
"""
import asyncio
import contextlib
import os
import secrets

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import catalog, config, db
from .features import FEATURES

SERVED = ("index.html", "houses/", "examples/", "lib/web/", "template/")


class Pages(StaticFiles):
    """The repo's pages, always sent in full. A renders symlink re-pointed at an older folder serves an
    older file at the same URL, so "not modified" answers would keep a browser on the old picture."""

    async def get_response(self, path, scope):
        p = path.replace(os.sep, "/").lstrip("/")
        if p not in ("", ".") and (not any(p == s.rstrip("/") or p.startswith(s) for s in SERVED)
                                   or any(part.startswith(".") for part in p.split("/"))):
            raise StarletteHTTPException(404)
        res = await super().get_response(path, scope)
        res.headers["Cache-Control"] = "no-cache"
        return res

    def is_not_modified(self, response_headers, request_headers):
        return False


def watch(app):
    """Every few seconds: sync houses and rooms with the folders, so a room added or changed on disk
    (by hand, or by Claude) shows on the home page and gets its house's map rebuilt (catalog.sync's
    house jobs), whether or not anyone has a page open."""
    @contextlib.asynccontextmanager
    async def lifespan(_):
        async def loop():
            while True:
                await asyncio.sleep(app.state.settings.watch)
                try:
                    await asyncio.to_thread(sync_now, app)
                except Exception as e:   # noqa: BLE001 -- a bad folder mustn't stop the watching
                    print(f"watch: {e!r}", flush=True)
        task = asyncio.create_task(loop()) if app.state.settings.watch else None
        yield
        if task:
            task.cancel()
    return lifespan


def sync_now(app):
    with app.state.sessions() as session:
        catalog.sync(session, app.state.settings.root)


def create_app(settings=None):
    settings = settings or config.from_env()
    os.makedirs(settings.data, exist_ok=True)
    app = FastAPI(title="Rendervation", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.router.lifespan_context = watch(app)
    app.state.settings = settings
    app.state.engine, app.state.sessions = db.connect(settings.db)
    # the worker (lib/worker.py) reads this to claim jobs; a new one each start
    app.state.worker_token = secrets.token_urlsafe(24)
    token = os.path.join(settings.data, "worker.token")
    with open(token, "w") as f:
        f.write(app.state.worker_token)
    os.chmod(token, 0o600)
    sync_now(app)   # houses and rooms: the folders' list, in the database (then every settings.watch s)
    for feature in FEATURES:
        app.include_router(feature.router)
    app.mount("/", Pages(directory=settings.root, html=True), name="pages")
    return app


def __getattr__(name):   # `uvicorn server.app:app` builds it on first use, not on import
    if name == "app":
        globals()["app"] = create_app()
        return globals()["app"]
    raise AttributeError(name)
