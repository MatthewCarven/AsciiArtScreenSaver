"""The ASCII conversion engine.

Turns a brightness field (a 2D numpy array in [0, 1]) into rows of characters
for a given palette, and loads images into aspect-correct brightness/color
fields ready for conversion.

All the heavy lifting is vectorised with numpy.
"""

from __future__ import annotations

import numpy as np

from . import palettes

try:
    from PIL import Image
except Exception:  # pragma: no cover - Pillow is required for image mode only
    Image = None


# --------------------------------------------------------------------------- #
# Brightness field -> characters
# --------------------------------------------------------------------------- #

def field_to_ramp(field: np.ndarray, ramp: str):
    """Map a (rows, cols) brightness field to a non-braille palette.

    Returns (rows_of_text, char_grid) where char_grid is an (rows, cols) array
    of single-character strings (useful for per-cell colouring).
    """
    glyphs = np.array(list(ramp))
    n = len(ramp)
    idx = np.clip(np.round(field * (n - 1)).astype(np.int32), 0, n - 1)
    grid = glyphs[idx]
    rows = ["".join(row) for row in grid]
    return rows, grid


# Bit weights for the 2x4 braille cell. Layout (col, row) -> dot bit:
#   (0,0)=1   (1,0)=8
#   (0,1)=2   (1,1)=16
#   (0,2)=4   (1,2)=32
#   (0,3)=64  (1,3)=128
_BRAILLE_WEIGHTS = np.array(
    [[1, 8], [2, 16], [4, 32], [64, 128]], dtype=np.int32
)

_BAYER4 = (
    np.array(
        [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]],
        dtype=np.float32,
    )
    + 0.5
) / 16.0


def _bayer(h: int, w: int) -> np.ndarray:
    ty = (h + 3) // 4
    tx = (w + 3) // 4
    return np.tile(_BAYER4, (ty, tx))[:h, :w]


def field_to_braille(sub_field: np.ndarray, threshold: float = 0.5, dither: bool = False):
    """Map a (rows*4, cols*2) sub-resolution field to braille glyphs.

    With ``dither`` enabled an ordered (Bayer) dither is used instead of a hard
    threshold, which gives smooth tonal gradients — nice for images.

    Returns (rows_of_text, char_grid).
    """
    h, w = sub_field.shape
    rows_c = h // 4
    cols_c = w // 2
    if rows_c == 0 or cols_c == 0:
        return [], np.empty((0, 0), dtype="<U1")

    sub = sub_field[: rows_c * 4, : cols_c * 2]
    thresh = _bayer(rows_c * 4, cols_c * 2) if dither else threshold
    on = sub > thresh

    blocks = on.reshape(rows_c, 4, cols_c, 2)
    codes = 0x2800 + (blocks * _BRAILLE_WEIGHTS[None, :, None, :]).sum(axis=(1, 3))
    codes = codes.astype(np.int32)

    grid = np.empty((rows_c, cols_c), dtype="<U1")
    rows = []
    for r in range(rows_c):
        chars = [chr(int(c)) for c in codes[r]]
        grid[r] = chars
        rows.append("".join(chars))
    return rows, grid


# --------------------------------------------------------------------------- #
# Image loading
# --------------------------------------------------------------------------- #

def _placement(iw: int, ih: int, cols: int, rows: int, cell_aspect: float):
    """Fit an image of (iw, ih) px into a (cols, rows) cell grid, preserving
    aspect ratio while accounting for the cell being ``cell_aspect`` times
    taller than it is wide. Returns (ncols, nrows, ox, oy)."""
    img_ratio = iw / max(ih, 1)
    grid_ratio = cols / max(rows * cell_aspect, 1e-6)
    if img_ratio > grid_ratio:
        ncols = cols
        nrows = max(1, int(round(cols / img_ratio / cell_aspect)))
    else:
        nrows = rows
        ncols = max(1, int(round(rows * img_ratio * cell_aspect)))
    ncols = max(1, min(ncols, cols))
    nrows = max(1, min(nrows, rows))
    ox = (cols - ncols) // 2
    oy = (rows - nrows) // 2
    return ncols, nrows, ox, oy


def load_image_fields(path, cols: int, rows: int, cell_aspect: float, braille: bool):
    """Load an image into brightness + colour fields fitted to the grid.

    Returns a dict:
        kind        : "braille" | "simple"
        field       : brightness array. (rows, cols) for simple palettes,
                      (rows*4, cols*2) for braille. Zero (dark) outside the
                      fitted image region.
        color       : (rows, cols, 3) uint8 colour, black outside the region.
        region      : (ox, oy, ncols, nrows) cell placement.
    """
    if Image is None:
        raise RuntimeError("Pillow is not installed; image mode is unavailable.")

    img = Image.open(path).convert("RGB")
    iw, ih = img.size
    ncols, nrows, ox, oy = _placement(iw, ih, cols, rows, cell_aspect)

    color_small = np.asarray(img.resize((ncols, nrows), Image.LANCZOS), dtype=np.uint8)
    color = np.zeros((rows, cols, 3), dtype=np.uint8)
    color[oy : oy + nrows, ox : ox + ncols] = color_small

    if braille:
        sub_w, sub_h = ncols * 2, nrows * 4
        gray = img.convert("L").resize((sub_w, sub_h), Image.LANCZOS)
        gsmall = np.asarray(gray, dtype=np.float32) / 255.0
        field = np.zeros((rows * 4, cols * 2), dtype=np.float32)
        field[oy * 4 : oy * 4 + sub_h, ox * 2 : ox * 2 + sub_w] = gsmall
        kind = "braille"
    else:
        gray = img.convert("L").resize((ncols, nrows), Image.LANCZOS)
        gsmall = np.asarray(gray, dtype=np.float32) / 255.0
        field = np.zeros((rows, cols), dtype=np.float32)
        field[oy : oy + nrows, ox : ox + ncols] = gsmall
        kind = "simple"

    return {
        "kind": kind,
        "field": field,
        "color": color,
        "region": (ox, oy, ncols, nrows),
    }


def make_sample_image(path, w: int = 512, h: int = 512):
    """Generate a pleasant test image (radial gradient + rings) so image mode
    works out of the box without the user supplying a photo."""
    if Image is None:
        raise RuntimeError("Pillow is not installed.")
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2.0, h / 2.0
    r = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) / (0.5 * np.hypot(w, h))
    rings = 0.5 + 0.5 * np.sin(r * 18.0)
    glow = np.clip(1.0 - r, 0, 1) ** 1.5
    val = np.clip(0.35 * rings + 0.85 * glow, 0, 1)
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[..., 0] = (val * 255 * (0.55 + 0.45 * xs / w)).astype(np.uint8)
    rgb[..., 1] = (val * 255 * (0.45 + 0.45 * ys / h)).astype(np.uint8)
    rgb[..., 2] = (val * 255).astype(np.uint8)
    Image.fromarray(rgb, "RGB").save(path)
    return path
