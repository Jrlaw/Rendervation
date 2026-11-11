"""Unit tests: rooms on disk and the designs logic, without HTTP."""
import pytest

from server import db as dbm
from server.features.designs import make_card
from server.rooms import chosen, designs, find_rooms, read_room, room_path

from .conftest import DEN


@pytest.mark.parametrize("rel, want", [
    ("houses/ours/rooms/office", "houses/ours/rooms/office"),
    ("/houses/ours/rooms/office/", "houses/ours/rooms/office"),
    ("examples/demo-house/rooms/hall-bath", "examples/demo-house/rooms/hall-bath"),
    ("houses/ours/rooms/../../../etc", None),
    ("houses/ours/rooms", None),
    ("lib/web/rooms/x", None),
    ("houses/.git/rooms/x", None),
    ("houses/ours/rooms/office/web", None),
])
def test_room_path(rel, want):
    assert room_path(rel) == want


def test_read_room(root):
    r = read_room(str(root), DEN)
    assert r.own == [("asis", "As it is"), ("mcm", "Mid-century"), ("open", "Open corner")]
    assert r.camera == "photo1"
    assert read_room(str(root), "houses/test/rooms/nothere") is None


def test_room_with_one_design(root):
    r = read_room(str(root), "houses/test/rooms/attic")
    assert r.own == [] and r.camera == "photo1"


def test_find_rooms(root):
    assert [r.rel for r in find_rooms(str(root))] == ["houses/test/rooms/attic", DEN, "examples/demo/rooms/bath"]


@pytest.fixture
def session(root):
    _, sessions = dbm.connect(str(root / "t.db"))
    with sessions() as s:
        yield s


def test_designs_edits_on_top(root, session):
    r = read_room(str(root), DEN)
    session.add(dbm.DesignSetting(room=DEN, design="open", label="Open plan", position=1, hidden=False))
    session.add(dbm.DesignSetting(room=DEN, design="mcm", hidden=True))
    session.commit()
    assert designs(session, r) == [
        {"id": "asis", "label": "As it is", "hidden": False, "first": True},
        {"id": "open", "label": "Open plan", "hidden": False, "first": False},
        {"id": "mcm", "label": "Mid-century", "hidden": True, "first": False},
    ]


def test_first_stays_first_whatever_the_positions(root, session):
    r = read_room(str(root), DEN)
    session.add(dbm.DesignSetting(room=DEN, design="open", position=0, hidden=False))   # not allowed by the API
    session.commit()
    assert designs(session, r)[0]["id"] == "asis"


def test_chosen_taken_over_from_chosen_js(root, session):
    r = read_room(str(root), DEN)
    assert chosen(session, r) == "mcm"
    assert session.get(dbm.RoomRow, DEN).chosen == "mcm"


def test_hidden_choice_is_not_chosen(root, session):
    r = read_room(str(root), DEN)
    chosen(session, r)
    session.add(dbm.DesignSetting(room=DEN, design="mcm", hidden=True))
    session.commit()
    assert chosen(session, r) is None


def test_card_from_render(root):
    r = read_room(str(root), DEN)
    card = make_card(r, "mcm", False, "photo1", None)
    from PIL import Image
    img = Image.open(card)
    assert img.size == (800, 600)
    assert img.getpixel((10, 10))[1] > 100   # the mcm render's green, not the as-is brown


def test_card_from_snapshot_when_no_render(root):
    import base64
    import io

    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (1000, 500), (0, 0, 200)).save(buf, "JPEG")
    snap = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    card = make_card(read_room(str(root), DEN), "open", False, "photo1", snap)
    assert Image.open(card).size == (800, 400)


def test_no_card_without_render_or_snapshot(root):
    assert make_card(read_room(str(root), DEN), "open", False, "photo1", None) is None
    assert make_card(read_room(str(root), DEN), "open", False, "photo1", "data:text/html,<b>") is None


def test_card_camera_cant_leave_the_room(root):
    assert make_card(read_room(str(root), DEN), "asis", True, "../../../../../etc/passwd", None) is None
