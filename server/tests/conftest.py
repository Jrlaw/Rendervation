"""A small test house, built fresh for each test in a temporary folder, and the app over it.

  houses/test/rooms/den   three designs (asis first, mcm, open), photo1 renders for asis and mcm,
                          a render.sh that "exports", dimensions, an inventory, an old web/chosen.js
  houses/test/rooms/attic one design (no variants), not on the old home page
  houses/test             house.md, a whole-house map, and the old hand-written houses/index.html
  examples/demo/rooms/bath an example room still at intake: a before photo, never exported
"""
import json
import os
import textwrap

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from server.app import create_app
from server.config import REPO, Settings

PAGE = """<!doctype html><title>Den</title><script>
Walkthrough.start({
  pairs: [["photo1", "From the hall", 1]],
  variants: [["asis", "As it is"], ["mcm", "Mid-century"], ["open", "Open corner"]],
  start: "photo1",
});
</script>"""


# the hand-written home page from before the database: names and card lines are taken from it once
OLD_HOME = """<main>
  <!-- one <h2> per house, one .room card per room -->
  <h2>Test house</h2>
  <div class="rooms">
    <article class="room"><img src="test/web/map.jpg" alt="map"><div><b>Whole house</b>
      <small>Both floors &amp; the yard · 1 modeled, the rest placeholders</small><nav><a href="test/web/index.html">Map</a></nav></div></article>
    <article class="room"><img src="test/rooms/den/web/cards/mcm.jpg" alt="den"><div><b>The den</b>
      <small>Design settled ·
        renders next</small><nav><a href="test/rooms/den/web/index.html">Walk through</a></nav></div></article>
  </div></main>"""


def jpg(path, size=(1600, 1200), color=(120, 90, 60)):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.new("RGB", size, color).save(path)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


@pytest.fixture
def root(tmp_path):
    den = tmp_path / "houses/test/rooms/den"
    write(den / "web/index.html", PAGE)
    write(den / "web/chosen.js", 'window.CHOSEN = "mcm";\n')
    jpg(den / "web/renders/day/photo1.jpg")
    jpg(den / "web/variants/mcm/renders/day/photo1.jpg", color=(20, 120, 60))
    write(den / "web/scene.json", "{}")
    write(tmp_path / "houses/test/rooms/attic/web/scene.json", "{}")
    write(den / "render.sh", "#!/bin/sh\necho EXPORTED\n")
    os.chmod(den / "render.sh", 0o755)
    write(den / "dimensions.json", json.dumps({"units": "inches", "dimensions": {
        "den_w": {"value": 120, "src": "plan", "note": "", "default": 120, "override": False, "updated": None}}}))
    write(den / "selections.md", "# Den\n\nNotes.\n")
    write(den / "inventory.json", json.dumps({"designs": [["asis", "As it is"]], "groups": [
        {"name": "Lights", "items": [{"name": "Lamp", "qty": 1, "status": "need"}]}]}))
    write(tmp_path / "houses/test/rooms/attic/web/index.html",
          '<script>Walkthrough.start({ views: [["photo1", "Up the stairs"]] });</script>')
    write(tmp_path / "houses/index.html", OLD_HOME)
    write(tmp_path / "houses/test/house.md", "# The test house\n\nTwo rooms.\n")
    write(tmp_path / "houses/test/web/index.html", "<h1>Map</h1>")
    jpg(tmp_path / "houses/test/web/map.jpg")
    write(tmp_path / "examples/demo/rooms/bath/web/index.html", '<script>Walkthrough.start({ views: [["photo1", "In"]] });</script>')
    jpg(tmp_path / "examples/demo/rooms/bath/web/before/photo1.jpg")
    write(tmp_path / "index.html", "<h1>Home</h1>")
    write(tmp_path / "lib/web/walkthrough.js", "// viewer")
    write(tmp_path / "lib/serve.sh", "#!/bin/sh")
    write(tmp_path / ".git/config", "[core]")
    write(tmp_path / "houses/.git/config", "[core]")
    write(tmp_path / "houses/test/rooms/den/web/.bake/model.glb", "half-baked")
    return tmp_path


@pytest.fixture
def app(root):
    return create_app(Settings(root=str(root), db=str(root / "data/test.db"), tools=os.path.join(REPO, "lib/tools")))


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def worker(client, app):
    """Headers for the worker's calls."""
    return {"X-Worker-Token": app.state.worker_token}


DEN = "houses/test/rooms/den"
dedent = textwrap.dedent
