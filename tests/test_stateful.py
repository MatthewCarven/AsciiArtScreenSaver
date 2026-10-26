"""Tests for R2b's stateful patterns — fire and life — and the contract
change they brought: reset on resize, palette switch and pattern switch; a
capped substep; pause freezing the sim; and the screensaver's 2 fps throttle
slowing it down rather than breaking it, all at faked timestamps.

Runs under pytest, or standalone with ``python tests/test_stateful.py``.
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
import pygame                             # noqa: E402

from _support import env, patched, run_all, sandbox   # noqa: E402

from asciiviz import app as app_module, patterns      # noqa: E402
from asciiviz.app import App, build_parser, main as app_main   # noqa: E402
from asciiviz.generative import GenerativeField       # noqa: E402

COLS, ROWS = 48, 18


def sim_field(name, cols=COLS, rows=ROWS):
    """A field on ``name``, plus the field's own copy of that sim."""
    gf = GenerativeField(cols, rows, 1.9, 0.6)
    assert gf.set_pattern(name)
    return gf, gf.patterns[gf.pattern_index][1]


def drive(gf, t0, t1, fps, h=ROWS, w=COLS):
    """Call ``gf.frame`` as the app would at ``fps`` from ``t0`` to ``t1``."""
    n = int(round((t1 - t0) * fps))
    f = None
    for i in range(n + 1):
        f = gf.frame(t0 + i / fps, h, w)
    return f


# --------------------------------------------------------------------------- #
# Resets: resize, palette switch, pattern switch
# --------------------------------------------------------------------------- #

def test_resize_resets_the_sim():
    for name in ("fire", "life"):
        gf, sim = sim_field(name)
        drive(gf, 0.0, 2.0, 60)
        assert sim.steps > 0 and sim.shape == (ROWS, COLS)
        gf.set_dims(COLS + 10, ROWS + 4, 1.9)
        assert sim.steps == 0 and sim.shape is None, f"{name} kept its state"
        f = gf.frame(2.0, ROWS + 4, COLS + 10)
        assert f.shape == (ROWS + 4, COLS + 10) and sim.steps == 0
        # A clean start: exactly what a brand-new field draws at that moment.
        fresh, _ = sim_field(name, COLS + 10, ROWS + 4)
        assert np.array_equal(f, fresh.frame(2.0, ROWS + 4, COLS + 10)), name


def test_a_palette_switch_resets_the_sim_by_shape():
    # Switching to braille changes the sub-resolution without any resize, so
    # the sim has to notice the new shape by itself.
    for name in ("fire", "life"):
        gf, sim = sim_field(name)
        drive(gf, 0.0, 2.0, 60)
        before = sim.steps
        gf.frame(2.0, ROWS * 4, COLS * 2)
        assert sim.shape == (ROWS * 4, COLS * 2) and sim.steps == 0, name
        drive(gf, 2.0, 3.0, 60, ROWS * 4, COLS * 2)
        assert sim.steps > 0
        gf.frame(3.0, ROWS, COLS)            # and back again
        assert sim.shape == (ROWS, COLS) and sim.steps == 0 and before > 0


def test_switching_to_a_sim_starts_it_afresh():
    gf, sim = sim_field("life")
    drive(gf, 0.0, 2.0, 60)
    assert sim.steps > 0
    gf.set_pattern("life")                   # already on it: carry on
    assert sim.steps > 0
    gf.set_pattern("plasma")
    gf.frame(2.5, ROWS, COLS)
    gf.set_pattern("life")
    assert sim.steps == 0 and sim.shape is None
    gf.next_pattern()                        # G away and all the way round
    while gf.pattern_name != "life":
        gf.next_pattern()
    assert sim.shape is None


# --------------------------------------------------------------------------- #
# The substep cap
# --------------------------------------------------------------------------- #

def test_substeps_are_capped_per_frame():
    for name in ("fire", "life"):
        gf, sim = sim_field(name)
        gf.frame(0.0, ROWS, COLS)
        gf.frame(100.0, ROWS, COLS)          # a huge gap: back from image mode
        assert sim.steps == patterns.Simulation.MAX_STEPS, (name, sim.steps)


def test_dropped_ticks_are_not_owed_afterwards():
    gf, sim = sim_field("fire")
    gf.frame(0.0, ROWS, COLS)
    gf.frame(100.0, ROWS, COLS)
    after_gap = sim.steps
    gf.frame(100.0 + 1 / 60, ROWS, COLS)     # one normal frame later
    assert sim.steps - after_gap <= 1, "the sim tried to catch up on the gap"


def test_braille_ticks_faster_so_flames_rise_at_the_same_speed():
    gf, sim = sim_field("fire")
    drive(gf, 0.0, 1.0, 60)
    cell = sim.steps
    gf.set_dims(COLS, ROWS, 1.9)
    drive(gf, 0.0, 1.0, 60, ROWS * 4, COLS * 2)
    assert abs(cell - 30) <= 1 and abs(sim.steps - 120) <= 2, (cell, sim.steps)


# --------------------------------------------------------------------------- #
# Pause
# --------------------------------------------------------------------------- #

def test_pause_freezes_the_sim():
    # The app's pause freezes t; with steps derived from t, the sim freezes too.
    for name in ("fire", "life"):
        gf, sim = sim_field(name)
        held = drive(gf, 0.0, 2.0, 60)
        steps = sim.steps
        for _ in range(30):                  # half a second of paused frames
            again = gf.frame(2.0, ROWS, COLS)
            assert np.array_equal(again, held), f"{name} moved while paused"
        assert sim.steps == steps
        drive(gf, 2.0, 3.0, 60)              # unpaused: it carries on
        assert sim.steps > steps


def test_pause_freezes_the_sim_in_the_real_loop():
    def run(pause):
        app = App(build_parser().parse_args(["--pattern", "fire"]))
        sim = app.gen.patterns[app.gen.pattern_index][1]
        if pause:   # Space, handled in the first frame after that frame's tick
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        app.run()
        return app, sim

    with env(ASCIIVIZ_SELFTEST="12"):
        moving, moving_sim = run(pause=False)
        paused, paused_sim = run(pause=True)
    assert moving_sim.steps >= 5, "control: 12 frames at 60 fps should tick"
    assert paused.paused and paused_sim.steps == 0, paused_sim.steps


# --------------------------------------------------------------------------- #
# The screensaver throttle, at faked timestamps
# --------------------------------------------------------------------------- #

def test_at_2fps_fire_runs_slower_but_still_burns():
    gf, sim = sim_field("fire")
    f = drive(gf, 0.0, 10.0, 2)              # 21 frames, half a second apart
    assert sim.steps == 20 * patterns.Simulation.MAX_STEPS
    assert sim.steps < 10.0 * sim.RATE, "should be slower than at full speed"
    lit_rows = np.flatnonzero((f > 0.0).any(axis=1))
    assert lit_rows.size and lit_rows[0] < ROWS // 2, "flames never rose"


def test_at_2fps_life_keeps_full_speed_under_the_cap():
    # Ten generations a second is five per half-second frame: under the cap,
    # so Life loses nothing at the throttle — it just shows every fifth.
    gf, sim = sim_field("life")
    drive(gf, 0.0, 10.0, 2)
    assert abs(sim.steps - 100) <= 1, sim.steps


def test_throttle_switch_mid_run_through_the_app_clock():
    # 60 fps, then the screensaver's full phase ends and it drops to 2 fps.
    app = App(build_parser().parse_args(
        ["--screensaver", "--pattern", "fire", "--full-minutes", "0.05",
         "--idle-fps", "2"]))
    try:
        sim = app.gen.patterns[app.gen.pattern_index][1]
        t, frames = 0.0, 0
        while t < 6.0:
            t += 1.0 / app._ss_fps()
            app.t = t
            app._draw_generative()
            frames += 1
        full = 3.0 * 30                       # ticks in the 3 s at 60 fps
        assert app._ss_fps() == 2
        assert abs(sim.steps - (full + 6 * 6)) <= 2, sim.steps
    finally:
        app.gen = None


# --------------------------------------------------------------------------- #
# Life's rules and stamina
# --------------------------------------------------------------------------- #

def board(rows, shape=(8, 8)):
    b = np.zeros(shape, dtype=bool)
    for y, x in rows:
        b[y, x] = True
    return b


def test_life_follows_b3_s23():
    blinker = board([(3, 2), (3, 3), (3, 4)])
    turned = patterns.life_step(blinker)
    assert np.array_equal(turned, board([(2, 3), (3, 3), (4, 3)]))
    assert np.array_equal(patterns.life_step(turned), blinker)
    block = board([(1, 1), (1, 2), (2, 1), (2, 2)])
    assert np.array_equal(patterns.life_step(block), block)
    glider = board([(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)])
    g = glider
    for _ in range(4):
        g = patterns.life_step(g)
    assert np.array_equal(g, np.roll(np.roll(glider, 1, axis=0), 1, axis=1))


def test_life_rule_table_for_every_neighbour_count():
    # Born on exactly 3, survives on 2 or 3, otherwise dead — for n = 0..8.
    ring = [(1, 1), (1, 2), (1, 3), (2, 1), (2, 3), (3, 1), (3, 2), (3, 3)]
    for n in range(9):
        for was_alive in (False, True):
            b = board(ring[:n] + ([(2, 2)] if was_alive else []), (7, 7))
            now = patterns.life_step(b)[2, 2]
            assert now == (n == 3 or (was_alive and n == 2)), (n, was_alive)


def test_life_wraps_around_the_edges():
    edge = board([(0, 7), (1, 7), (2, 7)])   # a blinker on the right edge
    turned = patterns.life_step(edge)
    assert np.array_equal(turned, board([(1, 6), (1, 7), (1, 0)]))


def test_life_never_dies_out():
    gf, sim = sim_field("life", 24, 10)
    gf.frame(0.0, 10, 24)
    sim.alive[:] = False                      # the worst case: a dead board
    gens = sim.SPLASH_EVERY + 1
    drive(gf, 0.0, gens / sim.RATE, 60, 10, 24)
    assert sim.steps >= sim.SPLASH_EVERY and sim.alive.any(), \
        "a fresh patch of soup should have landed"
    drive(gf, gens / sim.RATE, 120.0, 10, 10, 24)   # and a long run after
    assert sim.alive.any()


def test_life_trails_fade_with_t_not_with_generations():
    gf, sim = sim_field("life")
    drive(gf, 0.0, 2.0, 60)
    sim.seen[0, 0] = 1.9                      # a cell that died 0.1 s ago
    sim.alive[0, 0] = False
    a = sim.draw(2.0, gf)[0, 0]
    b = sim.draw(2.5, gf)[0, 0]
    assert 0.0 < b < a < 0.85


# --------------------------------------------------------------------------- #
# Colour: the per-pattern gradient override
# --------------------------------------------------------------------------- #

def colours_drawn(pattern):
    app = App(build_parser().parse_args(
        ["--pattern", pattern, "--color", "--palette", "dots"]))
    seen = []
    with patched(app.renderer, "blit_grid_color",
                 lambda surf, grid, cg, **kw: seen.append(cg.copy())):
        for i in range(61):
            app.t = i / 60
            app._draw_generative()
    return seen[-1].reshape(-1, 3).astype(int)


def test_fire_burns_orange_and_life_glows_green():
    fire = colours_drawn("fire")
    hot = fire[fire.sum(axis=1).argmax()]
    assert hot[0] > hot[1] > hot[2], f"fire isn't ember-coloured: {hot}"
    life = colours_drawn("life")
    lit = life[life.sum(axis=1).argmax()]
    assert lit[1] > lit[0] and lit[1] > lit[2], f"life isn't green: {lit}"


def test_other_patterns_keep_the_global_gradient():
    plasma = colours_drawn("plasma")
    hot = plasma[plasma.sum(axis=1).argmax()]
    assert hot[2] > hot[0], "plasma lost its blue gradient"
    assert set(app_module._GEN_GRADIENTS) == {"fire", "life"}


# --------------------------------------------------------------------------- #
# End to end: the real run loop on each sim, in every palette
# --------------------------------------------------------------------------- #

def test_real_runs_on_fire_and_life():
    with sandbox():
        with env(ASCIIVIZ_SELFTEST="6"):
            for name in ("fire", "life"):
                for palette in ("dots", "ramp", "braille"):
                    assert app_main(["--pattern", name, "--palette", palette,
                                     "--color"]) == 0, (name, palette)


if __name__ == "__main__":
    sys.exit(run_all(dict(globals())))
