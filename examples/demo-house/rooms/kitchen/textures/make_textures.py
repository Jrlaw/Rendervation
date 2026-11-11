"""Textures cut from the park's photos, squared up through the solved cameras (camera_marks.py):
the birch of the cabinets, the gray plank floor and the wood-grain laminate counter. Plus the new
design's walnut counter, cut from IKEA's KARLBY photo.

    python3 textures/make_textures.py   (needs Pillow and numpy)
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path[:0] = [os.path.join(ROOT, "lib", "tools")]
from PIL import Image, ImageEnhance  # noqa: E402
from photo_texture import rectify, source_point  # noqa: E402
from solve_cameras import basis  # noqa: E402

# the solved cameras (room.py) and the photos at full size: (file, crop x0, scale from the 1600 px 4:3 frame)
CAMS = {
    "photo1": dict(loc=(52.3, -183.0, 65.8), target=(48.7, -87.1, 37.4), roll=-0.0215, lens=18.0),
    "photo2": dict(loc=(42.4, 1.7, 62.9), target=(110.0, -64.7, 31.0), roll=-0.029, lens=15.5),
}
FULL = {"photo1": ("nps-before-1.jpg", 5120), "photo2": ("nps-before-2.jpg", 5464)}


def project(cam, pts):
    c = CAMS[cam]
    loc, d = np.array(c["loc"]), np.array(c["target"]) - np.array(c["loc"])
    f, x, y = basis(np.arctan2(d[1], d[0]), np.arctan2(d[2], np.hypot(d[0], d[1])), c["roll"])
    focal = c["lens"] / 36 * 1600
    out = []
    for p in pts:
        v = np.array(p, float) - loc
        z = v @ f
        out.append((800 + focal * (v @ x) / z, 600 - focal * (v @ y) / z))
    return out


def to_full(cam, uv):
    """1600 x 1200 frame pixels to the full-size intake photo (cut to 4:3 from its center)."""
    from PIL import Image
    name, h = FULL[cam]
    w = Image.open(os.path.join(HERE, "..", "intake", name)).size
    s = w[1] / 1200
    x0 = (w[0] - w[1] * 4 / 3) / 2
    return [(u * s + x0, v * s) for u, v in uv], os.path.join(HERE, "..", "intake", name)


# photo 1's white balance is cool (skylight from the eat-in window): its white ceiling reads (191, 201, 225).
# Scaling each channel so that ceiling is neutral gives the floor its real gray, not the camera's blue
WHITE1 = (191, 201, 225)


def balance(img, white):
    m = max(white)
    return img.point([min(255, round(v * m / white[i // 256])) for i, v in enumerate(list(range(256)) * 3)])


def cut(out, cam, quad3d, w, h, turn=False, white=None):
    uv, path = to_full(cam, project(cam, quad3d))
    img = rectify(path, uv, w, h)
    if white:   # and mostly gray: the skylight's blue is strongest in the light planks, so balancing alone leaves
        img = ImageEnhance.Color(balance(img, white)).enhance(0.2)   # them blue and the dark ones brown
    if turn:   # a quarter turn, so the planks run north-south once box-projected on the floor
        img = img.transpose(Image.Transpose.ROTATE_90)
    img.save(os.path.join(HERE, out), quality=92)
    print(out, [tuple(round(c) for c in p) for p in project(cam, quad3d)])


# the sink run's south end panel (24" x 30"), facing photo 1: birch, grain running up
cut("birch.jpg", "photo1", [(92, -106, 33), (115, -106, 33), (115, -106, 5), (92, -106, 5)], 460, 560)
# floor between the range and the sink run, in front of photo 1's camera (60" x 40"), white-balanced
cut("floor_plank.jpg", "photo1", [(34, -104, 0), (86, -104, 0), (86, -128, 0), (34, -128, 0)], 1040, 480, turn=True,
    white=WHITE1)
# the counter by the hall door in photo 2 (16" x 10"), front edge down
cut("laminate.jpg", "photo2", [(110, -3, 36), (110, -13, 36), (94, -13, 36), (94, -3, 36)], 400, 250)

# KARLBY walnut (intake/products), the top of the slab. The photo looks down it at an angle; the
# first cut caught a wedge of the white backdrop in its far right corner (a pale triangle on the
# counter behind the sink) and the slab's dark front edge along the bottom, so the corners are
# pulled in from that cut: x 40-1400, y 78-452 of its 1480 x 512.
KARLBY = [(300, 422), (1388, 652), (1196, 1036), (24, 600)]
inner = [source_point(KARLBY, 1480, 512, x, y) for x, y in ((40, 78), (1400, 78), (1400, 452), (40, 452))]
img = rectify(os.path.join(HERE, "..", "intake", "products", "ikea-karlby-walnut.jpg"), inner, 1480, 512)
img.save(os.path.join(HERE, "karlby_walnut.jpg"), quality=92)
print("karlby_walnut.jpg", [tuple(round(c) for c in p) for p in inner])
