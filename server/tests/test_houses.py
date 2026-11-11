"""Houses and rooms in the database: the sync with the folders, the old home page's import, and editing
them through the API."""
import shutil

from server import db as dbm
from server.catalog import old_home, sync

from .conftest import DEN

ATTIC = "houses/test/rooms/attic"


def test_old_home_is_read(root):
    houses, rooms = old_home(str(root))
    # the comment's <h2> is skipped, and the stale count is dropped (the page counts rooms itself)
    assert houses == {"houses/test": ("Test house", "Both floors & the yard · the rest placeholders", 0)}
    assert rooms == {DEN: ("The den", "Design settled · renders next", 0)}


def test_no_old_home(root):
    (root / "houses/index.html").unlink()
    assert old_home(str(root)) == ({}, {})


def test_houses_listed_with_their_rooms(client):
    houses = client.get("/api/houses").json()
    assert [h["house"] for h in houses] == ["houses/test", "examples/demo"]   # examples last
    test, demo = houses
    assert test["name"] == "Test house" and test["blurb"] == "Both floors & the yard · the rest placeholders"
    assert test["map"] == {"card": "/houses/test/web/map.jpg",
                           "links": [["Map", "/houses/test/web/index.html"], ["3D", "/houses/test/web/index.html?3d"]]}
    assert [(r["room"], r["name"], r["blurb"]) for r in test["rooms"]] == [
        (DEN, "The den", "Design settled · renders next"),   # from the old page, first
        (ATTIC, "Attic", None),                              # not on it: named from its folder, after
    ]
    assert test["modeled"] == 2
    assert demo["example"] and demo["name"] == "Demo" and demo["map"] is None


def test_room_card_and_links(client):
    den = client.get("/api/houses").json()[0]["rooms"][0]
    assert den["chosen"] == "mcm" and den["chosen_label"] == "Mid-century"
    assert den["card"] == "/houses/test/rooms/den/web/renders/day/photo1.jpg"   # no cards yet: a render
    assert den["links"] == [["Walk through", f"/{DEN}/web/index.html"], ["Renders", f"/{DEN}/web/index.html#gallery"]]
    client.put(f"/api/rooms/{DEN}/choice", json={"design": "mcm"})
    den = client.get("/api/houses").json()[0]["rooms"][0]
    assert den["card"] == f"/{DEN}/web/cards/mcm.jpg"


def test_example_card_falls_back_to_a_before_photo(client):
    bath = client.get("/api/houses").json()[1]["rooms"][0]
    assert bath["card"] == "/examples/demo/rooms/bath/web/before/photo1.jpg" and bath["chosen"] is None


def test_room_not_exported_yet_has_no_walkthrough_link(client):
    demo = client.get("/api/houses").json()[1]
    bath = demo["rooms"][0]
    assert bath["modeled"] is False and bath["links"] == [] and demo["modeled"] == 0
    den = client.get("/api/houses").json()[0]["rooms"][0]
    assert den["modeled"] is True and den["links"][0][0] == "Walk through"


def test_house_name_from_house_md_when_not_on_the_old_page(root, client):
    (root / "houses/index.html").unlink()
    (root / "houses/second/rooms/hall/web").mkdir(parents=True)
    (root / "houses/second/rooms/hall/web/index.html").write_text("<p>hall</p>")
    (root / "houses/second/house.md").write_text("# The second house\n")
    houses = {h["house"]: h for h in client.get("/api/houses").json()}
    assert houses["houses/second"]["name"] == "The second house"
    assert [r["name"] for r in houses["houses/second"]["rooms"]] == ["Hall"]


def test_new_room_shows_up_without_a_restart(root, client):
    (root / "houses/test/rooms/porch/web").mkdir(parents=True)
    (root / "houses/test/rooms/porch/web/index.html").write_text("<p>porch</p>")
    (root / "houses/test/rooms/porch/web/scene.json").write_text("{}")
    rooms = client.get("/api/houses").json()[0]["rooms"]
    assert [r["name"] for r in rooms] == ["The den", "Attic", "Porch"]


def test_gone_folder_is_flagged_not_deleted(root, client):
    shutil.rmtree(root / "houses/test/rooms/attic")
    attic = client.get("/api/houses").json()[0]["rooms"][1]
    assert attic["room"] == ATTIC and attic["missing"] is True and attic["name"] == "Attic"
    assert client.get("/api/houses").json()[0]["modeled"] == 1
    (root / "houses/test/rooms/attic/web").mkdir(parents=True)
    (root / "houses/test/rooms/attic/web/index.html").write_text("<p>back</p>")
    (root / "houses/test/rooms/attic/web/scene.json").write_text("{}")
    attic = client.get("/api/houses").json()[0]["rooms"][1]
    assert attic["missing"] is False and attic["name"] == "Attic"


def test_edits_survive_the_next_sync(client):
    client.patch(f"/api/rooms/{ATTIC}", json={"name": "Loft", "blurb": "Measured"})
    client.get("/api/houses")
    attic = client.get("/api/houses").json()[0]["rooms"][1]
    assert (attic["name"], attic["blurb"]) == ("Loft", "Measured")


def test_rename_room_and_house(client):
    r = client.patch(f"/api/rooms/{DEN}", json={"name": "Office (the den)", "blurb": "  Train room  "})
    assert r.status_code == 200 and (r.json()["name"], r.json()["blurb"]) == ("Office (the den)", "Train room")
    r = client.patch("/api/houses/houses/test", json={"name": "Our house", "blurb": ""})
    assert (r.json()["name"], r.json()["blurb"]) == ("Our house", None)


def test_hide_and_show_room(client):
    client.patch(f"/api/rooms/{ATTIC}", json={"hidden": True})
    test = client.get("/api/houses").json()[0]
    assert [r["hidden"] for r in test["rooms"]] == [False, True] and test["modeled"] == 1
    client.patch(f"/api/rooms/{ATTIC}", json={"hidden": False})
    assert client.get("/api/houses").json()[0]["modeled"] == 2


def test_move_room(client, root):
    (root / "houses/test/rooms/porch/web").mkdir(parents=True)
    (root / "houses/test/rooms/porch/web/index.html").write_text("<p>porch</p>")
    client.patch("/api/rooms/houses/test/rooms/porch", json={"position": 0})
    assert [r["name"] for r in client.get("/api/houses").json()[0]["rooms"]] == ["Porch", "The den", "Attic"]
    client.patch(f"/api/rooms/{DEN}", json={"position": 9})   # past the end: last
    assert [r["position"] for r in client.get("/api/houses").json()[0]["rooms"]] == [0, 1, 2]
    assert [r["name"] for r in client.get("/api/houses").json()[0]["rooms"]] == ["Porch", "Attic", "The den"]


def test_room_edits_are_logged(client):
    client.patch(f"/api/rooms/{ATTIC}", json={"hidden": True})
    client.patch(f"/api/rooms/{ATTIC}", json={"name": "Loft"})
    log = client.get(f"/api/rooms/{ATTIC}/changes").json()
    assert [(c["what"], c["detail"]) for c in log] == [("edit room", {"name": "Loft"}), ("hide room", {"hidden": True})]


def test_bad_room_edits(client):
    assert client.patch("/api/rooms/houses/test/rooms/nope", json={"name": "x"}).status_code == 404
    assert client.patch("/api/rooms/../../etc", json={"name": "x"}).status_code == 404
    assert client.patch(f"/api/rooms/{DEN}", json={"name": ""}).status_code == 422
    assert client.patch(f"/api/rooms/{DEN}", json={"position": -1}).status_code == 422
    assert client.patch("/api/houses/houses/nope", json={"name": "x"}).status_code == 404


def test_design_edits_still_reach_designs(client):
    """PATCH /api/rooms/{room}/designs/{design} isn't taken for a room called .../designs/open."""
    r = client.patch(f"/api/rooms/{DEN}/designs/open", json={"hidden": True})
    assert r.status_code == 200 and "designs" in r.json()


def test_sync_twice_changes_nothing(app, root):
    with app.state.sessions() as s:
        before = [(r.room, r.name, r.position) for r in s.query(dbm.RoomRow).order_by(dbm.RoomRow.room)]
        sync(s, str(root))
        sync(s, str(root))
        after = [(r.room, r.name, r.position) for r in s.query(dbm.RoomRow).order_by(dbm.RoomRow.room)]
    assert before == after


def test_home_page_is_served(client):
    r = client.get("/")
    assert r.status_code == 200 and r.text == "<h1>Home</h1>"   # the test house's own index.html


def test_the_real_home_page_draws_from_the_api():
    import os

    from server.config import REPO
    with open(os.path.join(REPO, "index.html"), encoding="utf-8") as f:
        page = f.read()
    with open(os.path.join(REPO, "lib/web/home.js"), encoding="utf-8") as f:
        script = f.read()
    assert '<script src="lib/web/home.js">' in page and 'api("/api/houses")' in script
