"""Tests for R2d's Mandelbrot zoom: where the dives go, when they reset, and
that the shortcuts it takes to stay fast change nothing you could see. Those
shortcuts are an escape check only every few iterations, a budget the frame
sets for itself, and braille computed once per cell.

Runs under pytest, or standalone with ``python tests/test_zoom.py``.
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))     # the project
sys.path.insert(0, str(HERE))            # _support
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")   # app.py imports pygame
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np                        # noqa: E402

from _support import env, patched, run_all, sandbox   # noqa: E402

from asciiviz import patterns as P        # noqa: E402
from asciiviz.app import main as app_main # noqa: E402
from asciiviz.generative import GenerativeField  # noqa: E402

CYCLE, FADE = P._ZOOM_CYCLE, P._ZOOM_FADE
TARGETS = P._ZOOM_TARGETS
KP = [(18, 4), (16, 4), (10, 2), (2, 2), (3, 1)]   # as the comments in patterns.py say
COLS, ROWS = 96, 28


def frame(t, cols=COLS, rows=ROWS, sub=1, density=0.6):
    gf = GenerativeField(cols, rows, 1.9, density)
    assert gf.set_pattern("mandelbrot")
    return gf.frame(t, rows * (4 if sub == 2 else 1), cols * (2 if sub == 2 else 1))


def spied(t, cols=COLS, rows=ROWS, sub=1):
    """The frame at ``t``, plus every (c, cap) mandelbrot handed to _escape."""
    seen, real = [], P._escape

    def spy(c, cap):
        seen.append((c.copy(), cap))
        return real(c, cap)

    with patched(P, "_escape", spy):
        f = frame(t, cols, rows, sub)
    return f, seen


def unfaded(t):
    tau = t % CYCLE
    return FADE + 0.3 < tau < CYCLE - FADE - 0.3


# --------------------------------------------------------------------------- #
# The targets: on the boundary, for good
# --------------------------------------------------------------------------- #

def critical_orbit(c, n):
    z = [0j]
    for _ in range(n):
        z.append(z[-1] * z[-1] + c)
    return z


def newton_root(c, k, p):
    """Polish ``c`` as a root of z_{k+p}(c) - z_k(c) by Newton's method."""
    for _ in range(8):
        z, dz, zk, dzk = 0j, 0j, 0j, 0j
        for n in range(k + p):
            z, dz = z * z + c, 2.0 * z * dz + 1.0
            if n + 1 == k:
                zk, dzk = z, dz
        c -= (z - zk) / (dz - dzk)
    return c


def test_every_target_is_a_misiurewicz_point():
    # The critical orbit lands on a repelling cycle after exactly k steps, so
    # c is on the boundary and the set stays busy around it at every scale.
    for c, (k, p) in zip(TARGETS, KP):
        z = critical_orbit(c, 40)
        hits = [(kk, pp) for kk in range(30) for pp in range(1, 9)
                if abs(z[kk + pp] - z[kk]) < 1e-7]
        assert hits and hits[0] == (k, p), (c, hits[:1])
        assert min(abs(v) for v in z[1:k + p + 1]) > 1e-3, f"{c} is a centre"
        lam = np.prod([2.0 * z[n] for n in range(k, k + p)])
        assert abs(lam) > 1.0, f"{c}: the cycle must repel"
        # And it is that root to float64 precision, not just near one: the
        # dive ends a trillion times closer in than the first view.
        assert abs(newton_root(c, k, p) - c) < 1e-15, c


def test_there_are_five_distinct_targets():
    assert len(TARGETS) == len(KP) == len(set(TARGETS)) == 5


# --------------------------------------------------------------------------- #
# The dive and its reset
# --------------------------------------------------------------------------- #

def test_each_dive_starts_on_the_whole_set_and_bottoms_out_on_its_target():
    for lap in range(len(TARGETS) + 2):
        centre, height, fade, depth = P._zoom_view(lap * CYCLE)
        assert height == P._ZOOM_TOP and depth == 0.0 and fade == 0.0
        assert abs(centre - P._ZOOM_HOME) < 1e-12
        centre, height, fade, depth = P._zoom_view((lap + 1) * CYCLE - 1e-9)
        assert abs(height / P._ZOOM_BOTTOM - 1.0) < 1e-6
        assert abs(depth - np.log10(P._ZOOM_TOP / P._ZOOM_BOTTOM)) < 1e-6
        target = TARGETS[lap % len(TARGETS)]
        assert abs(centre - target) < 1e-3 * height, "should have panned in"
        heights = [P._zoom_view(lap * CYCLE + tau)[1]
                   for tau in np.linspace(0.0, CYCLE, 300, endpoint=False)]
        assert (np.diff(heights) < 0).all(), "the dive must never back out"


def test_the_target_is_mid_screen_within_the_first_few_decades():
    for lap, target in enumerate(TARGETS):
        for tau in np.arange(20.0, CYCLE, 5.0):
            centre, height, _, depth = P._zoom_view(lap * CYCLE + tau)
            assert depth > 2.0
            assert abs(centre - target) < 0.05 * height, (lap, tau)


def test_the_reset_falls_on_the_lap_boundary_inside_a_fade():
    for lap in (1, 2, 5, 37):
        b = lap * CYCLE
        before, after = P._zoom_view(b - 1e-6), P._zoom_view(b + 1e-6)
        assert before[1] < 1.01 * P._ZOOM_BOTTOM, "should be at the floor"
        assert after[1] > 0.99 * P._ZOOM_TOP, "should be back on the whole set"
        assert before[2] < 1e-5 and after[2] < 1e-5, "the cut must be faded out"
        # Black across the cut, and a full picture either side of the fade.
        assert frame(b - 1e-3).max() == 0.0 and frame(b + 1e-3).max() == 0.0
        assert (frame(b - 2.0 * FADE) > 0.0).mean() > 0.2
        assert (frame(b + 2.0 * FADE) > 0.0).mean() > 0.2


def test_the_dive_resets_while_float64_still_has_headroom():
    # Neighbouring samples at the bottom of every dive, for a full-screen
    # 1920x1080 window at the default font (192 x 56 cells), stay dozens of
    # ulps apart. The picture visibly breaks down near one ulp a sample, a
    # hundred times deeper than this (WORKLOG 2026-10-26).
    for lap in range(len(TARGETS)):
        _, seen = spied((lap + 1) * CYCLE - 1e-6, 192, 56)
        c = seen[0][0].reshape(56, 192)
        step = min(np.abs(np.diff(c, axis=0)).min(), np.abs(np.diff(c, axis=1)).min())
        ulps = step / np.spacing(np.abs(c).max())
        assert ulps > 32, (lap, ulps)


# --------------------------------------------------------------------------- #
# Never flat, never broken, always the same for the same t
# --------------------------------------------------------------------------- #

def test_finite_in_range_and_never_flat_long_after_many_resets():
    for t0 in (1e4, 1e6):                  # 125 and 12,500 dives in
        laps = set()
        for t in t0 + np.arange(0.0, len(TARGETS) * CYCLE, 6.1):
            if not unfaded(t):
                continue
            laps.add(int(t // CYCLE) % len(TARGETS))
            for sub in (1, 2):
                f = frame(t, sub=sub)
                assert np.isfinite(f).all() and f.min() >= 0.0 and f.max() <= 1.0
                lit = (f > 0.0).mean()
                assert 0.15 < lit < 0.9, f"flat at t={t} (lit {lit:.0%})"
                assert f.std() > 0.1, f"featureless at t={t}"
        assert laps == set(range(len(TARGETS))), "every target should be visited"


def test_the_set_itself_is_drawn_solid():
    # Three seconds in, the whole set is in view and the fade-in is done:
    # points deep in the main cardioid and the period-2 bulb never escape and
    # must come out at full brightness, while the open sky around is banded.
    for lap in range(len(TARGETS)):
        f, seen = spied(lap * CYCLE + 3.0, 192, 56)
        c, f = seen[0][0], f.ravel()
        for inside in (-0.2 + 0.0j, -1.0 + 0.0j):
            assert f[np.argmin(np.abs(c - inside))] == 1.0, (lap, inside)
        assert (f < 1.0).mean() > 0.3


def test_the_same_t_gives_the_same_frame_whatever_came_before():
    a = frame(500.0)
    gf = GenerativeField(COLS, ROWS, 1.9, 0.6)
    gf.set_pattern("mandelbrot")
    for t in (10.0, 900.0, 3.0):
        gf.frame(t, ROWS, COLS)
    assert np.array_equal(gf.frame(500.0, ROWS, COLS), a)
    assert not np.array_equal(frame(500.5), a), "it should be moving"


def test_at_2fps_every_frame_is_a_whole_picture():
    # The screensaver throttle just samples the dive more sparsely.
    prev = None
    for t in np.arange(3 * CYCLE, 4 * CYCLE, 0.5):
        f = frame(t)
        assert np.isfinite(f).all() and f.min() >= 0.0 and f.max() <= 1.0
        if unfaded(t):
            assert 0.15 < (f > 0.0).mean() < 0.9, t
            assert prev is None or not np.array_equal(f, prev), t
        prev = f


# --------------------------------------------------------------------------- #
# The shortcuts change nothing you could see
# --------------------------------------------------------------------------- #

def plain_escape(c, budget):
    """The textbook loop: every point, every iteration, checked every time."""
    mu = np.full(c.shape, np.inf)
    z = np.zeros_like(c)
    alive = np.ones(c.shape, dtype=bool)
    for n in range(1, budget + 1):
        z[alive] = z[alive] ** 2 + c[alive]
        m2 = np.abs(z) ** 2
        out = alive & (m2 > P._ZOOM_BAIL ** 2)
        mu[out] = n + 1 - np.log2(0.5 * np.log(m2[out]))
        alive &= ~out
    return mu


def test_escape_counts_match_the_textbook_loop():
    for lap in range(len(TARGETS)):
        for tau in (5.0, 40.0, 77.0):
            _, seen = spied(lap * CYCLE + tau, 40, 12)
            c, cap = seen[0]
            fast, slow = P._escape(c, cap), plain_escape(c, 1000)
            both = np.isfinite(fast) & np.isfinite(slow)
            assert both.any()
            # Checking every sixth iteration reads the smooth count late,
            # which is the point: it barely moves once |z| is large.
            assert np.abs(fast[both] - slow[both]).max() < 1e-3, (lap, tau)
            # Points the frame's own budget gave up on would have been drawn
            # as solid set anyway.
            lo = fast[np.isfinite(fast)].min()
            gave_up = ~np.isfinite(fast)
            assert (slow[gave_up] - lo >= 2.0 * P._ZOOM_SOLID).all(), (lap, tau)


def test_the_budget_cap_rises_with_depth():
    caps = [spied(2 * CYCLE + tau)[1][0][1] for tau in range(0, int(CYCLE), 8)]
    assert caps == sorted(caps) and caps[-1] > caps[0] + 200, caps


def test_braille_is_computed_once_per_cell_and_interpolated():
    # Full-screen braille at 2x4 samples a cell can't hold 60 fps, so the
    # zoom computes per cell and interpolates (WORKLOG 2026-10-26).
    t = 2 * CYCLE + 33.0
    braille, seen = spied(t, sub=2)
    assert braille.shape == (ROWS * 4, COLS * 2)
    assert seen[0][0].size == ROWS * COLS
    cells = frame(t)
    for y, x in ((0, 0), (0, -1), (-1, 0), (-1, -1)):   # corners line up
        assert braille[y, x] == cells[y, x]


def test_upsampling_is_bilinear_with_the_corners_pinned():
    a = np.add.outer(np.arange(4.0) * 3.0, np.arange(5.0))   # linear both ways
    up = P._upsample(a, 13, 17)
    assert np.allclose(up, np.add.outer(np.linspace(0, 9, 13), np.linspace(0, 4, 17)))
    assert np.array_equal(P._upsample(np.full((1, 1), 0.25), 4, 2), np.full((4, 2), 0.25))


# --------------------------------------------------------------------------- #
# End to end: the real run loop
# --------------------------------------------------------------------------- #

def test_real_runs_in_every_palette_and_at_the_throttle():
    with sandbox():
        with env(ASCIIVIZ_SELFTEST="6"):
            for palette in ("dots", "ramp", "braille"):
                assert app_main(["--pattern", "mandelbrot", "--palette", palette,
                                 "--color"]) == 0, palette
        with env(ASCIIVIZ_SELFTEST="3"):    # already throttled to 2 fps
            assert app_main(["--screensaver", "--full-minutes", "0",
                             "--cycle-patterns", "mandelbrot", "--palette",
                             "braille"]) == 0


if __name__ == "__main__":
    sys.exit(run_all(dict(globals())))
