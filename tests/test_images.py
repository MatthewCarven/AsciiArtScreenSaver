"""Tests for loading photos the right way up.

Phones store the sensor's pixels as they came and add an EXIF orientation tag
saying how to turn them for viewing. ``load_image_fields`` used to ignore the
tag, so an upright phone photo was drawn sideways (found during R2c). Each
test photo here is stored landscape, white on the left and black on the right,
so where the white ends up shows which way it was turned. Runs under pytest,
or standalone with ``python tests/test_images.py``.
"""

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))     # the project
sys.path.insert(0, str(HERE))            # _support

from PIL import Image                     # noqa: E402

from _support import patched, run_all     # noqa: E402

from asciiviz import engine               # noqa: E402
from asciiviz.engine import load_image_fields   # noqa: E402

ORIENTATION = 0x0112                      # the EXIF tag's number


def photo(folder, orientation=None):
    """A 40x20 JPEG, white left half and black right half, optionally tagged."""
    img = Image.new("RGB", (40, 20), (0, 0, 0))
    img.paste((255, 255, 255), (0, 0, 20, 20))
    path = Path(folder) / f"photo-{orientation}.jpg"
    exif = Image.Exif()
    if orientation is not None:
        exif[ORIENTATION] = orientation
    img.save(path, quality=95, exif=exif)
    return path


def loaded(path, braille):
    """The fitted picture's brightness, without the dark margins, and its
    size in cells. A square grid of square cells, so a landscape photo comes
    out 40x20 cells and a portrait one 20x40."""
    data = load_image_fields(str(path), 40, 40, 1.0, braille)
    ox, oy, ncols, nrows = data["region"]
    sy, sx = (4, 2) if braille else (1, 1)
    field = data["field"][oy * sy:(oy + nrows) * sy, ox * sx:(ox + ncols) * sx]
    return field, (ncols, nrows)


def white_side(field):
    """Which edge the white half lies against."""
    h, w = field.shape
    sides = {"left": field[:, :w // 2], "right": field[:, w // 2:],
             "top": field[:h // 2], "bottom": field[h // 2:]}
    side = max(sides, key=lambda k: sides[k].mean())
    assert sides[side].mean() > 0.9, f"white side too dim: {sides[side].mean():.2f}"
    return side


def check(orientation, size, side):
    with tempfile.TemporaryDirectory() as d:
        path = photo(d, orientation)
        for braille in (False, True):
            field, cells = loaded(path, braille)
            assert cells == size, (orientation, braille, cells)
            assert white_side(field) == side, (orientation, braille)


def test_untagged_photo_loads_as_stored():
    check(None, (40, 20), "left")


def test_orientation_1_means_as_stored():
    check(1, (40, 20), "left")


def test_phone_portrait_tag_6_turns_it_upright():
    # 6: turn 90 degrees clockwise to view, so the stored left edge goes on top.
    check(6, (20, 40), "top")


def test_tag_8_turns_it_the_other_way():
    # 8: turn 90 degrees anticlockwise, so the stored left edge goes to the bottom.
    check(8, (20, 40), "bottom")


def test_tag_3_turns_it_upside_down():
    check(3, (40, 20), "right")


def test_a_broken_tag_shows_the_photo_as_stored():
    def broken(img, **kwargs):
        raise SyntaxError("not a TIFF file")    # what a mangled EXIF block raises

    with patched(engine.ImageOps, "exif_transpose", broken):
        check(6, (40, 20), "left")


if __name__ == "__main__":
    sys.exit(run_all(dict(globals())))
