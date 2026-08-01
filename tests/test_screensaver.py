"""Tests for screensaver behaviour: the .scr entry points, the wind-down
phases, and the configurable pattern rotation.

Runs under pytest, or standalone with ``python tests/test_screensaver.py``.
The wind-down phases are checked against :meth:`App._ss_fps` and
:meth:`App._ss_finished` rather than by running the loop for ten minutes.
"""

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))     # the project
sys.path.insert(0, str(HERE))            # _support
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")   # app.py imports pygame
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from _support import env, patched, run_all, sandbox, write   # noqa: E402

import screensaver                                        # noqa: E402
from asciiviz import config                               # noqa: E402
from asciiviz.app import App, build_parser, main as app_main   # noqa: E402


def make_app(argv):
    """An App built straight from a command line, no config file involved."""
    opts = build_parser().parse_args(argv)
    return App(opts)


# --------------------------------------------------------------------------- #
# Windows .scr command lines
# --------------------------------------------------------------------------- #

def test_parse_mode_covers_every_windows_command_line():
    assert screensaver.parse_mode(["x"]) == ("s", None)          # bare launch
    assert screensaver.parse_mode(["x", ""]) == ("s", None)
    assert screensaver.parse_mode(["x", "/s"]) == ("s", None)
    assert screensaver.parse_mode(["x", "/S"]) == ("s", None)    # case-insensitive
    assert screensaver.parse_mode(["x", "/c"]) == ("c", None)
    assert screensaver.parse_mode(["x", "/c:12345"]) == ("c", None)
    assert screensaver.parse_mode(["x", "/p", "9876"]) == ("p", "9876")
    assert screensaver.parse_mode(["x", "/p:9876"]) == ("p", "9876")


def test_preview_exits_without_starting_anything():
    launched = []
    with patched(screensaver, "_show_config", lambda: launched.append("config")):
        assert screensaver.main(["x", "/p", "1"]) == 0
    assert launched == []


def test_run_routes_through_the_app_with_screensaver_mode():
    seen = []

    def fake_app_main(argv):
        seen.append(list(argv))
        return 0

    import asciiviz.app
    with patched(asciiviz.app, "main", fake_app_main):
        assert screensaver.main(["x", "/s"]) == 0
    assert seen == [["--screensaver"]]


def test_settings_button_creates_then_opens_the_config_file():
    opened = []
    with sandbox() as d:
        target = d / "config.json"
        with env(ASCIIVIZ_CONFIG=str(target)), \
                patched(screensaver, "_open_in_editor",
                        lambda p: opened.append(Path(p)) or True):
            screensaver.main(["x", "/c"])
        assert opened == [target]
        assert target.is_file(), "a starter config should have been created"
        assert json.loads(target.read_text())["idle_fps"] == config.DEFAULTS["idle_fps"]


def test_settings_button_opens_the_config_already_in_effect():
    # Don't create a second file shadowing the one the saver is really reading.
    opened = []
    with sandbox() as d:
        existing = write(d / "live.json", {"idle_fps": 9})
        with env(ASCIIVIZ_CONFIG=str(existing)), \
                patched(screensaver, "_open_in_editor",
                        lambda p: opened.append(Path(p)) or True):
            screensaver.main(["x", "/c"])
        assert opened == [existing]
        assert json.loads(existing.read_text()) == {"idle_fps": 9}, "not overwritten"


def test_settings_button_falls_back_to_a_dialog_when_no_editor_opens():
    shown = []
    with sandbox() as d:
        with env(ASCIIVIZ_CONFIG=str(d / "config.json")), \
                patched(screensaver, "_open_in_editor", lambda p: False), \
                patched(screensaver, "_message", lambda t: shown.append(t)):
            screensaver.main(["x", "/c"])
    assert len(shown) == 1 and "config.json" in shown[0]


# --------------------------------------------------------------------------- #
# Wind-down phases
# --------------------------------------------------------------------------- #

def test_full_speed_then_throttled_then_finished():
    app = make_app(["--screensaver", "--fps", "60", "--idle-fps", "2",
                    "--full-minutes", "1", "--throttle-minutes", "1"])
    try:
        app.t = 0.0
        assert app._ss_fps() == 60 and not app._ss_finished()
        app.t = 59.0
        assert app._ss_fps() == 60 and not app._ss_finished()
        app.t = 61.0                       # into the throttled phase
        assert app._ss_fps() == 2 and not app._ss_finished()
        app.t = 119.0
        assert app._ss_fps() == 2 and not app._ss_finished()
        app.t = 121.0                      # both phases done
        assert app._ss_finished()
    finally:
        app.gen = None


def test_negative_throttle_never_finishes():
    app = make_app(["--screensaver", "--full-minutes", "1", "--throttle-minutes", "-1"])
    app.t = 1.0
    assert not app._ss_finished()
    app.t = 60.0 * 60.0 * 24.0             # a full day in
    assert app._ss_fps() == app.ss_idle_fps, "should still be throttled"
    assert not app._ss_finished(), "negative throttle means never bow out"


def test_windowed_app_never_finishes_on_a_timer():
    app = make_app(["--full-minutes", "0", "--throttle-minutes", "0"])
    app.t = 10_000.0
    assert not app._ss_finished()
    assert app._ss_fps() == app.fps        # and never throttles


# --------------------------------------------------------------------------- #
# Pattern rotation
# --------------------------------------------------------------------------- #

def test_rotation_covers_every_pattern_by_default():
    app = make_app([])
    names = config.pattern_names()
    seen = [app.gen.pattern_name]
    for _ in range(len(names) - 1):
        app._advance_pattern()
        seen.append(app.gen.pattern_name)
    assert sorted(seen) == sorted(names)


def test_rotation_is_restricted_to_the_configured_patterns():
    chosen = ["plasma", "starfield"]
    app = make_app(["--cycle-patterns", ",".join(chosen)])
    assert app.gen.pattern_name == "plasma", "should start on the first one"
    order = []
    for _ in range(4):
        app._advance_pattern()
        order.append(app.gen.pattern_name)
    assert order == ["starfield", "plasma", "starfield", "plasma"]


def test_manual_cycling_still_reaches_every_pattern():
    # The G key must not be restricted by cycle_patterns — that setting is for
    # unattended running, not for the person at the keyboard.
    app = make_app(["--cycle-patterns", "plasma"])
    names = config.pattern_names()
    seen = {app.gen.pattern_name}
    for _ in range(len(names)):
        seen.add(app.gen.next_pattern())
    assert seen == set(names)


def test_start_pattern_can_be_chosen_directly():
    assert make_app(["--pattern", "ripples"]).gen.pattern_name == "ripples"


def test_explicit_pattern_beats_the_head_of_the_cycle_list():
    app = make_app(["--pattern", "flow", "--cycle-patterns", "plasma,starfield"])
    assert app.gen.pattern_name == "flow"


# --------------------------------------------------------------------------- #
# End to end: a real config file drives a real run
# --------------------------------------------------------------------------- #

def test_config_file_drives_a_real_screensaver_run():
    with sandbox() as d:
        cfg = d / "config.json"
        cfg.write_text(json.dumps({
            "palette": "ramp",
            "pattern": "plasma",
            "cycle_patterns": ["plasma", "flow"],
            "idle_fps": 4,
            "full_minutes": 0.001,
            "throttle_minutes": -1,
            "cycle_seconds": 0.01,
            "color": True,
        }))
        with env(ASCIIVIZ_CONFIG=str(cfg), ASCIIVIZ_SELFTEST="8"):
            assert app_main(["--screensaver"]) == 0, "run loop raised or refused"


def test_command_line_still_beats_the_config_file_at_runtime():
    with sandbox() as d:
        cfg = d / "config.json"
        cfg.write_text(json.dumps({"palette": "ramp", "idle_fps": 4}))
        with env(ASCIIVIZ_CONFIG=str(cfg)):
            values, _, _ = config.load()
            opts = build_parser()
            opts.set_defaults(**values)
            parsed = opts.parse_args(["--palette", "dots"])
        assert parsed.palette == "dots" and parsed.idle_fps == 4


def test_a_broken_config_still_lets_the_screensaver_start():
    # The whole point: a .scr has no console, so a bad settings file must
    # degrade to defaults rather than leaving a screensaver that never appears.
    with sandbox() as d:
        cfg = d / "config.json"
        cfg.write_text("{ oh dear ")
        with env(ASCIIVIZ_CONFIG=str(cfg), ASCIIVIZ_SELFTEST="3"):
            assert app_main(["--screensaver"]) == 0


def test_bad_values_are_surfaced_to_the_user():
    with sandbox() as d:
        cfg = d / "config.json"
        cfg.write_text(json.dumps({"idle_fps": -5, "palette": "nonsense"}))
        with env(ASCIIVIZ_CONFIG=str(cfg)):
            values, _, problems = config.load()
            assert values == {} and len(problems) == 2
            p = build_parser()
            p.set_defaults(**values)
            opts = p.parse_args([])
            opts.config_path, opts.config_problems = cfg, problems
            app = App(opts)
        assert app.toast_text.startswith("config:") and "+1 more" in app.toast_text


# --------------------------------------------------------------------------- #
# Standalone runner
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    sys.exit(run_all(dict(globals())))
