"""Square up a piece of a photo for use as a texture: real grain and color from the room itself.

    from photo_texture import crop_pts, rectify
    img = rectify("intake/IMG_1.HEIC", [top_left, top_right, bottom_right, bottom_left], w, h)

Corners are full-resolution pixels of the upright photo. Every cut is checked for a border that
doesn't match the rest (edge_check): a product photo's backdrop, the slab's own edge or the black
past the photo's frame caught in a corner. Those show up on the model as a stray wedge, so pull that
corner in and cut again. HEIC needs pillow-heif, so run scripts using this
with ~/.cache/home-render/heic-venv/bin/python (lib/tools/heic2jpg.sh creates that venv).
"""
import sys

from PIL import Image, ImageOps

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

_OPENED = {}


def photo(path):
    if path not in _OPENED:
        _OPENED[path] = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    return _OPENED[path]


def coeffs(quad, w, h):
    """The perspective mapping from an output w x h to the quad (TL, TR, BR, BL), solved by elimination."""
    dst = [(0, 0), (w, 0), (w, h), (0, h)]
    A, b = [], []
    for (x, y), (u, v) in zip(dst, quad):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        b.append(v)
    n = 8
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        A[i], A[p], b[i], b[p] = A[p], A[i], b[p], b[i]
        for r in range(n):
            if r != i:
                f = A[r][i] / A[i][i]
                A[r] = [a - f * c for a, c in zip(A[r], A[i])]
                b[r] -= f * b[i]
    return [b[i] / A[i][i] for i in range(n)]


def rectify(path, quad, w, h, check=True):
    img = photo(path).transform((w, h), Image.PERSPECTIVE, coeffs(quad, w, h), Image.BICUBIC)
    if check:
        for where in edge_check(img):
            print(f"photo_texture: {path}: the {where} doesn't match the rest of the cut "
                  "(backdrop or an edge caught in it?)", file=sys.stderr)
    return img


def source_point(quad, w, h, x, y):
    """Where the output pixel (x, y) of rectify(..., quad, w, h) comes from in the photo: to pull a
    corner in, move it in the output and map it back."""
    a, b, c, d, e, f, g, k = coeffs(quad, w, h)
    s = g * x + k * y + 1
    return ((a * x + b * y + c) / s, (d * x + e * y + f) / s)


def edge_check(img, strip=0.03, parts=8, limit=100):
    """The stretches of border (outer `strip` of each side, in `parts` pieces) whose average color is
    more than `limit` (RGB distance) from the middle of the picture's. Returns names like "top edge,
    right end". A real texture's border matches its middle; a backdrop or a slab edge doesn't."""
    w, h = img.size
    small = img.resize((max(8, w // 8), max(8, h // 8)), Image.BOX)
    sw, sh = small.size
    px = small.load()
    mid = [px[x, y] for x in range(sw // 4, sw * 3 // 4) for y in range(sh // 4, sh * 3 // 4)]
    ref = [sorted(c[i] for c in mid)[len(mid) // 2] for i in range(3)]
    t = max(1, round(min(sw, sh) * strip))
    sides = {"top edge": lambda u: (u, range(t)), "bottom edge": lambda u: (u, range(sh - t, sh)),
             "left edge": lambda u: (range(t), u), "right edge": lambda u: (range(sw - t, sw), u)}
    bad = []
    for side, region in sides.items():
        n = sw if side in ("top edge", "bottom edge") else sh
        for k in range(parts):
            xs, ys = region(range(n * k // parts, max(n * k // parts + 1, n * (k + 1) // parts)))
            cs = [px[x, y] for x in xs for y in ys]
            avg = [sum(c[i] for c in cs) / len(cs) for i in range(3)]
            if sum((avg[i] - ref[i]) ** 2 for i in range(3)) ** 0.5 > limit:
                end = "start" if k < parts / 3 else "end" if k >= parts * 2 / 3 else "middle"
                end = {"top edge": {"start": "left end", "end": "right end"},
                       "bottom edge": {"start": "left end", "end": "right end"},
                       "left edge": {"start": "top end", "end": "bottom end"},
                       "right edge": {"start": "top end", "end": "bottom end"}}[side].get(end, "middle")
                if f"{side}, {end}" not in bad:
                    bad.append(f"{side}, {end}")
    return bad


def crop_pts(pts, scale, ox, oy):
    """Corners read off a scaled crop, back to full-resolution pixels."""
    return [(x * scale + ox, y * scale + oy) for x, y in pts]
