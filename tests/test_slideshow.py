"""Tests for R2c — the slideshow in the screensaver's rotation.

``cycle_content`` ("patterns", "images" or "mixed") decides what the saver
rotates, and ``images_dir`` points the image source at any folder. Sequencing
is checked at faked timestamps: ``app.t`` is set by hand and the rotation is
asked to move on, rather than waiting out real 20-second slots. Every test
works inside ``sandbox()`` with its own picture folder.

Runs under pytest, or standalone with ``python tests/test_slideshow.py``.
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))     # the project
sys.path.insert(0, str(HERE))            # _support
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")   # app.py imports pygame
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame                             # noqa: E402
from PIL import Image                     # noqa: E402

from _support import env, patched, run_all, sandbox   # noqa: E402

from asciiviz import app as app_module, config        # noqa: E402
from asciiviz.app import App, build_parser, main as app_main   # noqa: E402

ROTATION = "plasma,flow,ripples"


def pictures(folder, *names):
    """A folder holding a small picture under each name (plus a stray text
    file, which must never count as an image)."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "notes.txt").write_text("not a picture")
    for i, name in enumerate(names):
        Image.new("RGB", (24, 16), (40 * i, 200, 255 - 40 * i)).save(folder / name)
    return folder


def saver(folder, content, *extra):
    """A screensaver App rotating ``content`` from ``folder``."""
    return App(build_parser().parse_args(
        ["--screensaver", "--cycle-content", content, "--images-dir", str(folder),
         "--cycle-patterns", ROTATION, *extra]))


def shown(app):
    """What's on screen: an image's file name, or a pattern's name."""
    if app.mode == "image":
        return app._current_image_path().name
    return app.gen.pattern_name


def step(app):
    """Let the current item run its ``cycle_seconds``, then say what's next."""
    app.t += app.ss_cycle_seconds
    app._ss_cycle()
    return shown(app)


def steps(app, n):
    return [step(app) for _ in range(n)]


def sim_now(app):
    return app.gen.patterns[app.gen.pattern_index][1]


def run_frames(app, seconds, fps=60):
    """Draw the current pattern for ``seconds`` of faked time."""
    for _ in range(int(seconds * fps)):
        app.t += 1.0 / fps
        app._draw_generative()


# --------------------------------------------------------------------------- #
# The three kinds of rotation
# --------------------------------------------------------------------------- #

def test_mixed_is_the_default():
    assert config.DEFAULTS["cycle_content"] == "mixed"
    assert build_parser().parse_args([]).cycle_content == "mixed"


def test_nothing_moves_before_cycle_seconds_are_up():
    with sandbox() as d:
        app = saver(pictures(d / "pics", "a.png"), "mixed")
        app.t = app.ss_cycle_seconds - 0.01
        app._ss_cycle()
        assert shown(app) == "plasma"
        app.t = app.ss_cycle_seconds
        app._ss_cycle()
        assert shown(app) == "a.png"


def test_patterns_rotates_patterns_only():
    with sandbox() as d:
        app = saver(pictures(d / "pics", "a.png", "b.png"), "patterns")
        assert shown(app) == "plasma"
        assert steps(app, 6) == ["flow", "ripples", "plasma"] * 2


def test_mixed_alternates_pattern_and_image():
    with sandbox() as d:
        app = saver(pictures(d / "pics", "a.png", "b.jpg"), "mixed")
        assert shown(app) == "plasma", "mixed opens on a pattern"
        seen = []
        for _ in range(8):
            seen.append(step(app))
            if app.mode == "image":
                assert app._reveal_start == app.t, "images enter with the dissolve"
        assert seen == ["a.png", "flow", "b.jpg", "ripples",
                        "a.png", "plasma", "b.jpg", "flow"]


def test_images_is_a_slideshow_that_wraps():
    with sandbox() as d:
        app = saver(pictures(d / "pics", "a.png", "b.png", "c.png"), "images")
        assert shown(app) == "a.png", "a slideshow opens on a picture"
        assert app._reveal_start == app.t
        assert steps(app, 5) == ["b.png", "c.png", "a.png", "b.png", "c.png"]


def test_a_lone_image_is_held_not_redissolved():
    with sandbox() as d:
        app = saver(pictures(d / "pics", "only.png"), "images")
        app.t = 1.0                          # well into the first dissolve...
        app._reveal_mask()                   # ...which finishes as it's drawn
        app.t = 5.0
        app._reveal_mask()
        assert app._reveal_start is None
        assert step(app) == "only.png"
        assert app._reveal_start is None, "the same picture shouldn't blink"


# --------------------------------------------------------------------------- #
# Rescans, and folders with nothing (usable) in them
# --------------------------------------------------------------------------- #

def test_the_folder_is_rescanned_at_the_end_of_each_lap():
    with sandbox() as d:
        pics = pictures(d / "pics", "a.png", "b.png")
        app = saver(pics, "images")
        assert shown(app) == "a.png"
        pictures(pics, "0.png")              # sorts first, but lands mid-lap
        assert step(app) == "b.png", "a new file waits for the next lap"
        assert steps(app, 3) == ["0.png", "a.png", "b.png"]
        (pics / "a.png").unlink()            # and a deleted one leaves
        assert steps(app, 4) == ["0.png", "b.png", "0.png", "b.png"]


def test_an_empty_folder_falls_back_to_patterns_then_picks_up_pictures():
    for content in ("images", "mixed"):
        with sandbox() as d:
            pics = d / "pics"
            pics.mkdir()
            app = saver(pics, content)
            assert app.images == []
            assert shown(app) == "plasma", content
            assert steps(app, 3) == ["flow", "ripples", "plasma"], content
            pictures(pics, "new.png")        # dropped in while it runs
            assert step(app) == "new.png", content


def test_a_missing_folder_falls_back_and_is_never_created():
    with sandbox() as d:
        gone = d / "not-there"
        app = saver(gone, "mixed")
        assert steps(app, 3) == ["flow", "ripples", "plasma"]
        assert not gone.exists()
        assert "no such folder" in app.toast_text


def test_a_named_folder_never_gets_the_sample_image():
    with sandbox() as d:
        pics = d / "pics"
        pics.mkdir()
        app = App(build_parser().parse_args(["--images-dir", str(pics)]))
        assert app.images == [] and list(pics.iterdir()) == []
        assert not app.own_images_dir


def test_unset_images_dir_is_the_apps_own_folder():
    with sandbox():
        app = App(build_parser().parse_args([]))
    assert app.own_images_dir
    assert app.images_dir == config.data_dir() / "images"
    assert app.images, "the app's own folder always has at least the sample"


def test_a_broken_picture_is_skipped():
    with sandbox() as d:
        pics = pictures(d / "pics", "a.png", "c.png")
        (pics / "b.png").write_bytes(b"\x89PNG half a file")
        app = saver(pics, "images")
        assert steps(app, 4) == ["c.png", "a.png", "c.png", "a.png"]
        mixed = saver(pics, "mixed")
        assert steps(mixed, 4) == ["a.png", "flow", "c.png", "ripples"]


def test_a_picture_that_was_mid_copy_is_tried_again_next_lap():
    with sandbox() as d:
        pics = d / "pics"
        pics.mkdir()
        (pics / "slow.png").write_bytes(b"\x89PNG still copy")
        app = saver(pics, "images")
        assert shown(app) == "plasma", "nothing loadable yet: patterns"
        assert step(app) == "flow"
        pictures(pics, "slow.png")           # the copy finishes
        assert step(app) == "slow.png"


def test_a_broken_picture_by_hand_shows_a_pattern_and_isnt_retried_per_frame():
    with sandbox() as d:
        pics = d / "pics"
        pics.mkdir()
        (pics / "bad.png").write_bytes(b"nope")
        app = App(build_parser().parse_args(["--images-dir", str(pics)]))
        calls = []
        real = app_module.load_image_fields

        def counting(*a, **kw):
            calls.append(a[0])
            return real(*a, **kw)

        drawn = []
        with patched(app_module, "load_image_fields", counting), \
                patched(app, "_draw_generative", lambda: drawn.append(1)):
            app._handle_key(pygame.K_n)
            for _ in range(5):
                app._draw_image()
        assert app.mode == "image" and len(drawn) == 5
        assert len(calls) == 1, "a failed load should be remembered"
        assert "couldn't load bad.png" in app.toast_text


# --------------------------------------------------------------------------- #
# Simulations coming back after an image
# --------------------------------------------------------------------------- #

def test_mixed_switches_onto_the_next_sim_afresh():
    with sandbox() as d:
        app = saver(pictures(d / "pics", "a.png"), "mixed",
                    "--cycle-patterns", "fire,life")
        fire = sim_now(app)
        run_frames(app, 1.0)
        assert fire.steps > 0
        assert steps(app, 2) == ["a.png", "life"]
        run_frames(app, 1.0)
        assert steps(app, 2) == ["a.png", "fire"]
        assert sim_now(app) is fire
        assert fire.shape is None and fire.steps == 0, "fire should start afresh"


def test_a_one_sim_rotation_restarts_it_after_each_image():
    with sandbox() as d:
        app = saver(pictures(d / "pics", "a.png"), "mixed", "--cycle-patterns", "life")
        run_frames(app, 1.0)
        assert sim_now(app).steps > 0
        assert step(app) == "a.png"
        assert step(app) == "life"
        assert sim_now(app).shape is None and sim_now(app).steps == 0, \
            "back from an image should be a fresh start, like any switch to it"


def test_patterns_only_still_leaves_a_lone_sim_running():
    # R2b's rule: re-selecting the pattern you're on doesn't restart it, so a
    # one-pattern rotation doesn't wipe Life every cycle. No image, no reset.
    with sandbox() as d:
        app = saver(pictures(d / "pics", "a.png"), "patterns", "--cycle-patterns", "life")
        run_frames(app, 1.0)
        before = sim_now(app).steps
        assert step(app) == "life"
        assert sim_now(app).steps == before > 0


# --------------------------------------------------------------------------- #
# What it leaves alone
# --------------------------------------------------------------------------- #

def test_the_windowed_app_never_rotates():
    with sandbox() as d:
        app = App(build_parser().parse_args(["--images-dir", str(pictures(d / "p", "a.png"))]))
        assert app.cycle_content == "mixed"
        name = app.gen.pattern_name
        app.t = 10_000.0
        app._ss_cycle()
        assert app.mode == "generative" and app.gen.pattern_name == name


def test_manual_keys_work_as_before():
    with sandbox() as d:
        app = App(build_parser().parse_args(
            ["--images-dir", str(pictures(d / "p", "a.png", "b.png"))]))
        app._handle_key(pygame.K_TAB)
        assert shown(app) == "a.png" and app._reveal_start == app.t
        app._handle_key(pygame.K_n)
        assert shown(app) == "b.png"
        app._handle_key(pygame.K_p)
        assert shown(app) == "a.png"
        start = app.gen.pattern_name
        app._handle_key(pygame.K_g)
        assert app.mode == "generative" and app.gen.pattern_name != start
        app._handle_key(pygame.K_TAB)
        app._handle_key(pygame.K_TAB)
        assert app.mode == "generative"


def test_image_flag_stays_first_across_rescans():
    with sandbox() as d:
        pics = pictures(d / "pics", "a.png", "b.png")
        extra = pictures(d / "elsewhere", "start.png") / "start.png"
        opts = build_parser().parse_args(
            ["--screensaver", "--cycle-content", "images", "--images-dir", str(pics),
             "--image", str(extra)])
        opts.mode = "image"                  # as main() does for --image
        app = App(opts)
        assert shown(app) == "start.png"
        assert steps(app, 4) == ["a.png", "b.png", "start.png", "a.png"]


def test_patterns_mode_keeps_a_starting_image_on_screen():
    # cycle_content "patterns" is the old behaviour exactly: a saver started on
    # an image never rotated away from it.
    with sandbox() as d:
        opts = build_parser().parse_args(
            ["--screensaver", "--cycle-content", "patterns",
             "--images-dir", str(pictures(d / "pics", "a.png", "b.png"))])
        opts.mode = "image"
        app = App(opts)
        assert steps(app, 3) == ["a.png"] * 3


# --------------------------------------------------------------------------- #
# End to end: the real run loop, every kind of rotation
# --------------------------------------------------------------------------- #

def test_real_runs_in_every_cycle_content():
    with sandbox() as d:
        pics = pictures(d / "pics", "a.png", "b.jpg")
        with env(ASCIIVIZ_SELFTEST="10"):
            for content in config.CYCLE_CONTENT:
                for palette in ("dots", "braille"):
                    argv = ["--screensaver", "--cycle-seconds", "0.01",
                            "--cycle-content", content, "--images-dir", str(pics),
                            "--palette", palette, "--color"]
                    assert app_main(argv) == 0, (content, palette)


if __name__ == "__main__":
    sys.exit(run_all(dict(globals())))
