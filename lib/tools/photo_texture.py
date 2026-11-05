"""Square up a piece of a photo for use as a texture: real grain and color from the room itself.

    from photo_texture import crop_pts, rectify
    img = rectify("intake/IMG_1.HEIC", [top_left, top_right, bottom_right, bottom_left], w, h)

Corners are full-resolution pixels of the upright photo. HEIC needs pillow-heif, so run scripts using this
with ~/.cache/home-render/heic-venv/bin/python (lib/tools/heic2jpg.sh creates that venv).
"""
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


def rectify(path, quad, w, h):
    return photo(path).transform((w, h), Image.PERSPECTIVE, coeffs(quad, w, h), Image.BICUBIC)


def crop_pts(pts, scale, ox, oy):
    """Corners read off a scaled crop, back to full-resolution pixels."""
    return [(x * scale + ox, y * scale + oy) for x, y in pts]
