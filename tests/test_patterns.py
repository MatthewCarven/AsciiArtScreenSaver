"""Tests for the generative patterns — the R2a contract.

Every pattern must be a *pure* function of ``(X, Y, t, gf)`` that returns a
clean brightness field at any grid size, including braille sub-resolution and
the 1x1 grid the app briefly holds at startup. Runs under pytest, or
standalone with ``python tests/test_patterns.py``.
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))     # the project
sys.path.insert(0, str(HERE))            # _support
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np                        # noqa: E402

from _support import run_all              # noqa: E402

from asciiviz import config, patterns     # noqa: E402
from asciiviz.generative import GenerativeField  # noqa: E402

R2A = ("rain", "lava", "tunnel", "galaxy", "fireflies", "electric")
ORIGINALS = ("dotfield", "plasma", "ripples", "flow", "starfield")


def field(name, t=7.0, cols=48, rows=18, aspect=1.9, density=0.6, sub=1):
    gf = GenerativeField(cols, rows, aspect, density)
    assert gf.set_pattern(name), f"unknown pattern {name}"
    return gf.frame(t, rows * (4 if sub == 2 else 1),
                    cols * (2 if sub == 2 else 1))


# --------------------------------------------------------------------------- #
# The pattern list itself
# --------------------------------------------------------------------------- #

def test_names_are_unique_and_dotfield_still_first():
    names = [n for n, _ in patterns.PATTERNS]
    assert len(names) == len(set(names))
    assert names[0] == "dotfield"          # the default the app starts on


def test_r2a_batch_is_present_and_originals_survived():
    names = {n for n, _ in patterns.PATTERNS}
    for n in R2A + ORIGINALS:
        assert n in names, f"{n} missing from PATTERNS"
    assert len(patterns.PATTERNS) == 11


# --------------------------------------------------------------------------- #
# Field contract: shape, range, finiteness — at cell and braille resolution
# --------------------------------------------------------------------------- #

def test_every_pattern_returns_a_clean_cell_field():
    for name, _ in patterns.PATTERNS:
        for t in (0.0, 5.5, 31.0):
            f = field(name, t)
            assert f.shape == (18, 48), (name, f.shape)
            assert np.isfinite(f).all(), f"{name} produced non-finite values"
            assert f.min() >= 0.0 and f.max() <= 1.0, (name, f.min(), f.max())


def test_every_pattern_survives_braille_subresolution():
    for name, _ in patterns.PATTERNS:
        f = field(name, 9.0, sub=2)
        assert f.shape == (72, 96), (name, f.shape)
        assert np.isfinite(f).all() and f.min() >= 0.0 and f.max() <= 1.0


def test_every_pattern_survives_a_1x1_grid():
    # app.py holds a 1x1 GenerativeField between init and the first resize.
    for name, _ in patterns.PATTERNS:
        f = field(name, 3.0, cols=1, rows=1)
        assert f.shape == (1, 1) and np.isfinite(f).all()


def test_new_patterns_actually_draw_something():
    for name in R2A:
        f = field(name, 9.0)
        assert (f > 0.02).any(), f"{name} rendered an empty frame"


# --------------------------------------------------------------------------- #
# Purity: same t, same frame — no hidden state
# --------------------------------------------------------------------------- #

def test_patterns_are_pure_functions_of_time():
    for name in R2A:
        a = field(name, 12.34)
        b = field(name, 12.34)
        assert np.array_equal(a, b), f"{name} is not deterministic in t"
        c = field(name, 12.34 + 3.0)
        assert not np.array_equal(a, c), f"{name} ignores t entirely"


def test_density_still_thins_the_new_patterns():
    # The shared density shaping must keep working across the batch.
    for name in ("rain", "tunnel", "electric"):
        gf = GenerativeField(48, 18, 1.9, density=0.9)
        gf.set_pattern(name)
        dense = (gf.frame(9.0, 18, 48) > 0.0).sum()
        gf.density = 0.2
        sparse = (gf.frame(9.0, 18, 48) > 0.0).sum()
        assert sparse < dense, f"{name}: density had no thinning effect"


# --------------------------------------------------------------------------- #
# Config integration: the new names are valid everywhere pattern names go
# --------------------------------------------------------------------------- #

def test_config_accepts_the_new_names():
    values, problems = config.validate(
        {"pattern": "electric", "cycle_patterns": ["rain", "tunnel", "galaxy"]})
    assert problems == []
    assert values["pattern"] == "electric"
    assert values["cycle_patterns"] == ["rain", "tunnel", "galaxy"]


def test_config_still_rejects_unknown_pattern_names():
    values, problems = config.validate({"pattern": "melons"})
    assert "pattern" not in values and len(problems) == 1


if __name__ == "__main__":
    sys.exit(run_all(globals()))
