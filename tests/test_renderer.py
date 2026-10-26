"""Tests for the renderer's braille font check.

``_has_braille`` decides by rendering: a full cell and a single dot must come
out with different ink. A font with no braille draws its missing-glyph box for
both, and ``font.metrics`` answers for that box as if it were the glyph, which
is how this laptop's DejaVu Sans Mono (no braille in it) once passed and drew a
screen of empty boxes with no toast. Runs under pytest, or standalone with
``python tests/test_renderer.py``.
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))     # the project
sys.path.insert(0, str(HERE))            # _support
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame                             # noqa: E402

from _support import patched, run_all     # noqa: E402

from asciiviz import renderer             # noqa: E402
from asciiviz.renderer import Renderer, _has_braille   # noqa: E402

# pygame's own font ships inside the package and has no braille: every U+28xx
# draws the same box, so it is the missing-glyph case on any machine.
BOX_FONT = os.path.join(os.path.dirname(pygame.__file__),
                        pygame.font.get_default_font())

# Fonts that draw real braille, by file name: match_font answers a missing
# family with another of its group (no DejaVu Sans gives Arial), so the name
# is checked rather than trusted.
_REAL_BRAILLE = {"dejavusans": "dejavusans.ttf", "segoeuisymbol": "seguisym.ttf"}

# (column, row) of the dot for each bit of a braille codepoint, U+2800 + bits.
_DOTS = ((0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (0, 3), (1, 3))


class StandIn:
    """A font double: ``render`` draws what ``draw(surface, ch, colour)`` does."""

    def __init__(self, draw):
        self.draw = draw

    def render(self, ch, antialias, color):
        # Like pygame's own: the text colour everywhere, the glyph in alpha.
        s = pygame.Surface((10, 19), pygame.SRCALPHA)
        s.fill((*color[:3], 0))
        self.draw(s, ch, color)
        return s


def box(s, ch, color):            # a missing glyph: the same box for every ch
    pygame.draw.rect(s, color, (1, 2, 8, 15), 1)


def dots(s, ch, color):           # real braille: one dot per raised bit
    bits = ord(ch) - 0x2800
    for i, (col, row) in enumerate(_DOTS):
        if bits >> i & 1:
            s.fill(color, (2 + 4 * col, 2 + 4 * row, 2, 2))


def real_braille_paths():
    pygame.font.init()
    found = []
    for name, file in _REAL_BRAILLE.items():
        p = pygame.font.match_font(name)
        if p and Path(p).name.lower() == file:
            found.append(p)
    return found


def test_a_missing_glyph_box_fails_the_braille_check():
    pygame.font.init()
    for size in (6, 16, 32):
        f = pygame.font.Font(BOX_FONT, size)
        assert _has_braille(f) is False, f"pygame's own font passed at {size}"
    assert _has_braille(StandIn(box)) is False
    assert _has_braille(StandIn(lambda s, ch, color: None)) is False, "blank"


def test_real_braille_glyphs_pass_the_braille_check():
    assert _has_braille(StandIn(dots)) is True
    paths = real_braille_paths()
    for p in paths:
        for size in (6, 16, 32):
            assert _has_braille(pygame.font.Font(p, size)) is True, (p, size)
    if not paths:
        print("    (no DejaVu Sans or Segoe UI Symbol here: stand-in only)")


def test_no_braille_anywhere_means_braille_ok_is_false():
    # What makes the app toast "no braille-capable font": every font it can
    # find draws boxes, so it must say so rather than claim the mono font.
    pygame.font.init()
    with patched(pygame.font, "match_font", lambda *a, **k: BOX_FONT):
        r = Renderer(16)
    assert r.braille_ok is False
    assert r.braille_font is r.mono


def test_the_search_falls_through_to_a_font_with_real_braille():
    paths = real_braille_paths()
    if not paths:
        print("    (no DejaVu Sans or Segoe UI Symbol here: nothing to fall to)")
        return
    # The mono font and the first candidate draw boxes; the second is real.
    answers = {renderer._BRAILLE_CANDIDATES[1]: paths[0]}
    with patched(pygame.font, "match_font",
                 lambda name, *a, **k: answers.get(name, BOX_FONT)):
        r = Renderer(16)
    assert r.braille_ok is True
    assert r.braille_font is not r.mono and _has_braille(r.braille_font)


if __name__ == "__main__":
    sys.exit(run_all(dict(globals())))
