"""Tests for the generative patterns — the pattern contract.

Every pattern must return a clean brightness field at any grid size, including
braille sub-resolution and the 1x1 grid the app briefly holds at startup. The
R2a batch and R2d's zoom must stay *pure* functions of ``(X, Y, t, gf)``;
R2b's stateful pair are callable objects with ``reset()`` (their sim behaviour
is in ``test_stateful.py``, the zoom's dives in ``test_zoom.py``). Runs under
pytest, or standalone with ``python tests/test_patterns.py``.
"""

import os
import sys
import types
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
R2B = ("fire", "life")
R2D = ("mandelbrot",)
ORIGINALS = ("dotfield", "plasma", "ripples", "flow", "starfield")


def field(name, t=7.0, cols=48, rows=18, aspect=1.9, density=0.6, sub=1):
    gf = GenerativeField(cols, rows, aspect, density)
    assert gf.set_pattern(name), f"unknown pattern {name}"
    return gf.frame(t, rows * (4 if sub == 2 else 1),
                    cols * (2 if sub == 2 else 1))


def running(name, seconds=3.0, fps=60, cols=48, rows=18, sub=1):
    """A stateful pattern's frame after ``seconds`` driven at ``fps``."""
    gf = GenerativeField(cols, rows, 1.9, 0.6)
    assert gf.set_pattern(name)
    h, w = rows * (4 if sub == 2 else 1), cols * (2 if sub == 2 else 1)
    f = None
    for i in range(int(seconds * fps) + 1):
        f = gf.frame(i / fps, h, w)
    return f


# --------------------------------------------------------------------------- #
# The pattern list itself
# --------------------------------------------------------------------------- #

def test_names_are_unique_and_dotfield_still_first():
    names = [n for n, _ in patterns.PATTERNS]
    assert len(names) == len(set(names))
    assert names[0] == "dotfield"          # the default the app starts on


def test_r2a_r2b_and_r2d_are_present_and_originals_survived():
    names = {n for n, _ in patterns.PATTERNS}
    for n in R2A + R2B + R2D + ORIGINALS:
        assert n in names, f"{n} missing from PATTERNS"
    assert len(patterns.PATTERNS) == 14


def test_only_the_stateful_pair_is_stateful():
    # R2b widened the contract without touching the eleven existing patterns:
    # those stay plain functions, and only fire and life carry a reset().
    # R2d's zoom is a plain function again.
    for name, fn in patterns.PATTERNS:
        if name in R2B:
            assert callable(fn) and callable(getattr(fn, "reset", None)), name
        else:
            assert isinstance(fn, types.FunctionType), f"{name} changed shape"
            assert not hasattr(fn, "reset"), name


def test_each_field_runs_its_own_copy_of_a_sim():
    a, b = GenerativeField(8, 4), GenerativeField(8, 4)
    proto = dict(patterns.PATTERNS)
    for name in R2B:
        sa, sb = dict(a.patterns)[name], dict(b.patterns)[name]
        assert sa is not sb and sa is not proto[name], name
    for name in R2A + R2D + ORIGINALS:        # plain functions are just shared
        assert dict(a.patterns)[name] is proto[name]


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
    for name in R2A + R2D:
        f = field(name, 9.0)
        assert (f > 0.02).any(), f"{name} rendered an empty frame"


def test_the_sims_draw_something_once_running():
    for name in R2B:
        for sub in (1, 2):
            f = running(name, 3.0, sub=sub)
            assert np.isfinite(f).all() and f.min() >= 0.0 and f.max() <= 1.0
            assert (f > 0.02).any(), f"{name} rendered an empty frame"
            assert (f == 0.0).any(), f"{name} lit every cell"


def test_the_sims_draw_on_their_very_first_frame():
    # No ticks have run yet, but fire's coals glow and life's soup is there.
    for name in R2B:
        assert (field(name, 7.0) > 0.02).any(), name


# --------------------------------------------------------------------------- #
# Purity: same t, same frame — no hidden state
# --------------------------------------------------------------------------- #

def test_patterns_are_pure_functions_of_time():
    for name in R2A + R2D:
        a = field(name, 12.34)
        b = field(name, 12.34)
        assert np.array_equal(a, b), f"{name} is not deterministic in t"
        c = field(name, 12.34 + 3.0)
        assert not np.array_equal(a, c), f"{name} ignores t entirely"


def test_the_sims_are_deterministic_for_the_same_timestamps():
    # Not pure — but the same frame times always give the same frames.
    for name in R2B:
        a, b = running(name, 2.0), running(name, 2.0)
        assert np.array_equal(a, b), f"{name} is not repeatable"
        assert not np.array_equal(a, running(name, 2.5)), f"{name} never moved"


def test_density_still_thins_the_new_patterns():
    # The shared density shaping must keep working across the batch. A sim's
    # frame is redrawn here at the same t, so it doesn't advance in between.
    for name in ("rain", "tunnel", "electric") + R2B + R2D:
        gf = GenerativeField(48, 18, 1.9, density=0.9)
        gf.set_pattern(name)
        for i in range(181):
            gf.frame(i / 60, 18, 48)
        dense = (gf.frame(3.0, 18, 48) > 0.0).sum()
        gf.density = 0.2
        sparse = (gf.frame(3.0, 18, 48) > 0.0).sum()
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
    values, problems = config.validate(
        {"pattern": "fire", "cycle_patterns": ["fire", "life"]})
    assert problems == [] and values["cycle_patterns"] == ["fire", "life"]
    assert "fire" in config.pattern_names() and "life" in config.pattern_names()
    values, problems = config.validate(
        {"pattern": "mandelbrot", "cycle_patterns": ["mandelbrot", "electric"]})
    assert problems == [] and values["pattern"] == "mandelbrot"
    assert "mandelbrot" in config.pattern_names()


def test_config_still_rejects_unknown_pattern_names():
    values, problems = config.validate({"pattern": "melons"})
    assert "pattern" not in values and len(problems) == 1


if __name__ == "__main__":
    sys.exit(run_all(globals()))
