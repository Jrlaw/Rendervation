"""Integration tests: the API and pages through HTTP, on the test house."""
import json

from .conftest import DEN


def test_designs(client):
    r = client.get(f"/api/rooms/{DEN}/designs")
    assert r.status_code == 200
    body = r.json()
    assert [d["id"] for d in body["designs"]] == ["asis", "mcm", "open"]
    assert body["chosen"] == "mcm"   # from the old web/chosen.js


def test_unknown_room_404s(client):
    assert client.get("/api/rooms/houses/test/rooms/nope/designs").status_code == 404
    assert client.get("/api/rooms/houses/test/rooms/../../../etc/designs").status_code == 404


def test_choose_makes_a_card_and_lists_it(client, root):
    r = client.put(f"/api/rooms/{DEN}/choice", json={"design": "asis"})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "chosen": "asis", "card": "/houses/test/rooms/den/web/cards/asis.jpg"}
    assert (root / DEN / "web/cards/asis.jpg").is_file()
    rooms = {x["room"]: x for x in client.get("/api/rooms").json()}
    assert rooms[DEN]["chosen"] == "asis" and rooms[DEN]["card"].endswith("cards/asis.jpg")
    assert rooms["houses/test/rooms/attic"]["chosen"] is None


def test_choose_keeps_an_existing_card(client, root):
    from .conftest import jpg
    jpg(root / DEN / "web/cards/mcm.jpg", size=(800, 600), color=(1, 2, 3))
    before = (root / DEN / "web/cards/mcm.jpg").read_bytes()
    client.put(f"/api/rooms/{DEN}/choice", json={"design": "mcm"})
    assert (root / DEN / "web/cards/mcm.jpg").read_bytes() == before


def test_choose_unknown_design(client):
    assert client.put(f"/api/rooms/{DEN}/choice", json={"design": "nope"}).status_code == 404


def test_hide_and_show(client):
    r = client.patch(f"/api/rooms/{DEN}/designs/open", json={"hidden": True})
    assert r.status_code == 200
    assert [d["hidden"] for d in r.json()["designs"]] == [False, False, True]
    assert client.put(f"/api/rooms/{DEN}/choice", json={"design": "open"}).status_code == 409
    r = client.patch(f"/api/rooms/{DEN}/designs/open", json={"hidden": False})
    assert not any(d["hidden"] for d in r.json()["designs"])


def test_cant_hide_the_first_or_the_chosen(client):
    assert client.patch(f"/api/rooms/{DEN}/designs/asis", json={"hidden": True}).status_code == 409
    assert client.patch(f"/api/rooms/{DEN}/designs/mcm", json={"hidden": True}).status_code == 409   # chosen


def test_cant_move_the_first(client):
    assert client.patch(f"/api/rooms/{DEN}/designs/asis", json={"position": 2}).status_code == 409


def test_rename_and_move(client):
    client.patch(f"/api/rooms/{DEN}/designs/open", json={"label": "Open plan", "position": 1})
    ds = client.get(f"/api/rooms/{DEN}/designs").json()["designs"]
    assert [(d["id"], d["label"]) for d in ds] == [("asis", "As it is"), ("open", "Open plan"), ("mcm", "Mid-century")]


def test_bad_edits_are_422(client):
    assert client.patch(f"/api/rooms/{DEN}/designs/open", json={"label": ""}).status_code == 422
    assert client.patch(f"/api/rooms/{DEN}/designs/open", json={"position": "first"}).status_code == 422


def test_change_log(client):
    client.patch(f"/api/rooms/{DEN}/designs/open", json={"hidden": True})
    client.put(f"/api/rooms/{DEN}/choice", json={"design": "asis"})
    log = client.get(f"/api/rooms/{DEN}/changes").json()
    assert [(c["what"], c["user"]) for c in log] == [("choose", "local"), ("hide", "local")]
    assert log[1]["detail"] == {"design": "open"}


def test_status_updates_inventory_and_page(client, root):
    r = client.post("/api/status", json={"room": DEN, "group": 0, "item": 0, "name": "Lamp", "status": "ordered"})
    assert r.status_code == 200, r.text
    inv = json.loads((root / DEN / "inventory.json").read_text())
    assert inv["groups"][0]["items"][0]["status"] == "ordered"
    assert (root / DEN / "web/selections.html").is_file() and (root / DEN / "web/inventory.js").is_file()


def test_status_stale_page(client):
    r = client.post("/api/status", json={"room": DEN, "group": 0, "item": 0, "name": "Sconce", "status": "have"})
    assert r.status_code == 409


def test_status_bad_value(client):
    r = client.post("/api/status", json={"room": DEN, "group": 0, "item": 0, "name": "Lamp", "status": "lost"})
    assert r.status_code == 422


def test_dimension_queues_export_then_bake(client, worker, root):
    r = client.post("/api/dimension", json={"room": DEN, "name": "den_w", "value": 121.5, "src": "measured"})
    assert r.status_code == 200
    job = r.json()["job"]
    dims = json.loads((root / DEN / "dimensions.json").read_text())["dimensions"]["den_w"]
    assert dims["value"] == 121.5 and dims["override"] is True
    assert client.get(f"/api/jobs/{job}").json()["status"] == "queued"

    claimed = client.post("/api/jobs/claim?kind=export", headers=worker).json()
    assert claimed["id"] == job and claimed["status"] == "running"
    assert client.post("/api/jobs/claim?kind=export", headers=worker).status_code == 204
    done = client.post(f"/api/jobs/{job}/finish", json={"ok": True, "seconds": 3.2}, headers=worker).json()
    assert done["status"] == "done" and done["seconds"] == 3.2

    bake = client.post("/api/jobs/claim?kind=bake", headers=worker).json()
    assert bake["room"] == DEN and bake["kind"] == "bake"


def test_two_edits_share_one_queued_export(client):
    a = client.post("/api/dimension", json={"room": DEN, "name": "den_w", "value": 121, "src": "measured"}).json()
    b = client.post("/api/dimension", json={"room": DEN, "name": "den_w", "value": 122, "src": "measured"}).json()
    assert a["job"] == b["job"]


def test_failed_export_shows_its_log_and_queues_no_bake(client, worker):
    job = client.post("/api/dimension", json={"room": DEN, "name": "den_w", "value": 1, "src": "measured"}).json()["job"]
    client.post("/api/jobs/claim?kind=export", headers=worker)
    client.post(f"/api/jobs/{job}/finish", json={"ok": False, "seconds": 1, "log": "Blender fell over"}, headers=worker)
    assert client.get(f"/api/jobs/{job}").json() == {"id": job, "room": DEN, "kind": "export", "status": "failed",
                                                     "seconds": 1.0, "log": "Blender fell over"}
    assert client.post("/api/jobs/claim?kind=bake", headers=worker).status_code == 204


def test_dimension_checks(client):
    assert client.post("/api/dimension", json={"room": DEN, "name": "nope", "value": 1}).status_code == 400
    assert client.post("/api/dimension", json={"room": DEN, "name": "den_w", "value": -4}).status_code == 400
    assert client.post("/api/dimension", json={"room": DEN, "name": "den_w", "value": 4, "src": "vibes"}).status_code == 400
    assert client.post("/api/dimension", json={"room": "houses/test/rooms/attic", "name": "x", "value": 4}).status_code == 400


def test_worker_calls_need_the_token(client):
    assert client.post("/api/jobs/claim?kind=export").status_code == 403
    assert client.post("/api/jobs/claim?kind=export", headers={"X-Worker-Token": "guess"}).status_code == 403
    assert client.post("/api/jobs/1/finish", json={"ok": True, "seconds": 1}).status_code == 403


def test_pages_are_served(client):
    for path in ("/", "/houses/index.html", f"/{DEN}/web/index.html", "/lib/web/walkthrough.js",
                 f"/{DEN}/web/renders/day/photo1.jpg"):
        r = client.get(path)
        assert r.status_code == 200, path
        assert r.headers["cache-control"] == "no-cache"


def test_not_modified_is_never_answered(client):
    r = client.get(f"/{DEN}/web/renders/day/photo1.jpg")
    again = client.get(f"/{DEN}/web/renders/day/photo1.jpg",
                       headers={"If-None-Match": r.headers["etag"], "If-Modified-Since": r.headers["last-modified"]})
    assert again.status_code == 200 and again.content == r.content


def test_private_files_are_not_served(client):
    for path in ("/data/test.db", "/.git/config", "/houses/.git/config", "/lib/serve.sh", "/server/app.py",
                 f"/{DEN}/web/.bake/model.glb", f"/{DEN}/web/../../../../../data/test.db"):
        assert client.get(path).status_code == 404, path


def test_api_docs(client):
    assert client.get("/api/docs").status_code == 200
    paths = client.get("/api/openapi.json").json()["paths"]
    assert "/api/rooms/{room}/designs" in paths and "/api/dimension" in paths


def test_every_page_gets_the_nav_bar(client, root):
    (root / "houses/test/web/plans.html").write_text(
        '<!doctype html><html><head><title>Plans</title></head>\n<body class="doc"><h1>Plans</h1></body></html>')
    r = client.get("/houses/test/web/plans.html")
    nav = r.text.index('<nav class="rv-nav"')
    assert r.text.index('<body class="doc">') < nav < r.text.index("<h1>Plans</h1>")   # first in the body
    assert 'href="/"' in r.text and 'href="https://github.com/Jrlaw/Rendervation"' in r.text
    head = r.text[:r.text.index("</head>")]
    assert '/lib/web/nav.css' in head and 'rel="icon" href="/lib/web/logo.svg"' in head
    assert r.headers["cache-control"] == "no-cache"
    assert client.get("/lib/web/walkthrough.js").text == "// viewer"     # only pages


def test_nav_bar_once_and_a_page_keeps_its_own_icon():
    from server.app import with_nav
    page = '<html><head><link rel="icon" href="me.png"></head><body><p>Hi</p></body></html>'
    once = with_nav(page)
    assert with_nav(once) == once and once.count("rv-nav") == 1
    assert "logo.svg" not in once.split("<body>")[0]                     # its own tab icon stays


def test_the_nav_bar_files_exist():
    import os

    from server.config import REPO
    for f in ("lib/web/nav.css", "lib/web/logo.svg"):
        assert os.path.isfile(os.path.join(REPO, f)), f
