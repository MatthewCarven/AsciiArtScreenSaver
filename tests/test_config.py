"""Tests for the runtime config file and its precedence against the CLI.

Runs under pytest, or standalone with ``python tests/test_config.py`` — so
verifying a change never depends on having pytest installed. No fixtures, for
the same reason.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))     # the project
sys.path.insert(0, str(HERE))            # _support
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")   # app.py imports pygame
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from _support import env, patched, run_all, sandbox, write   # noqa: E402

from asciiviz import config                      # noqa: E402
from asciiviz.app import build_parser, main as app_main   # noqa: E402


def parse(argv, cfg_values):
    """Parse argv the way main() does, with cfg_values as the file's contents."""
    p = build_parser()
    p.set_defaults(**cfg_values)
    return p.parse_args(argv)


# --------------------------------------------------------------------------- #
# Search order
# --------------------------------------------------------------------------- #

def test_no_config_anywhere_is_not_an_error():
    with sandbox():
        values, path, problems = config.load()
        assert values == {} and path is None and problems == []


def test_explicit_path_wins_over_env():
    with sandbox() as d:
        write(d / "explicit.json", {"density": 0.11})
        write(d / "env.json", {"density": 0.22})
        with env(ASCIIVIZ_CONFIG=str(d / "env.json")):
            values, path, _ = config.load(str(d / "explicit.json"))
        assert values["density"] == 0.11
        assert Path(path).name == "explicit.json"


def test_env_wins_over_user_config():
    with sandbox() as d:
        write(config.user_config_path(), {"density": 0.33})
        write(d / "env.json", {"density": 0.22})
        with env(ASCIIVIZ_CONFIG=str(d / "env.json")):
            values, _, _ = config.load()
        assert values["density"] == 0.22


def test_user_config_wins_over_program_dir():
    with sandbox():
        write(config.user_config_path(), {"density": 0.33})
        # config.json also sits beside the program (checked into the repo root
        # during this test) — the per-user one must still win.
        beside = config.program_dir() / config.CONFIG_NAME
        existed = beside.exists()
        if not existed:
            write(beside, {"density": 0.44})
        try:
            values, path, _ = config.load()
            assert values["density"] == 0.33
            assert Path(path) == config.user_config_path()
        finally:
            if not existed and beside.exists():
                beside.unlink()


def test_missing_explicit_path_is_reported_not_fatal():
    with sandbox() as d:
        values, path, problems = config.load(str(d / "nope.json"))
        assert values == {} and path is None
        assert any("not found" in m for m in problems)


def test_program_dir_follows_the_executable_when_frozen():
    saved_frozen = getattr(sys, "frozen", None)
    saved_exe = sys.executable
    try:
        sys.frozen = True
        sys.executable = str(Path(tempfile.gettempdir()) / "ASCIIVisualizer.scr")
        assert config.program_dir() == Path(tempfile.gettempdir()).resolve()
    finally:
        sys.executable = saved_exe
        if saved_frozen is None:
            del sys.frozen
        else:
            sys.frozen = saved_frozen


# --------------------------------------------------------------------------- #
# Parsing and validation — nothing here may raise
# --------------------------------------------------------------------------- #

def test_malformed_json_falls_back_to_defaults():
    with sandbox() as d:
        write(d / "bad.json", "{ this is not json ")
        values, path, problems = config.load(str(d / "bad.json"))
        assert values == {}
        assert path is not None                    # we found it, couldn't read it
        assert any("not valid JSON" in m for m in problems)


def test_one_bad_value_does_not_discard_the_good_ones():
    values, problems = config.validate({"density": 99.0, "idle_fps": 3})
    assert values == {"idle_fps": 3}               # density dropped, fps kept
    assert any(m.startswith("density:") for m in problems)


def test_unknown_key_is_reported_and_ignored():
    values, problems = config.validate({"colour": True})   # British spelling trap
    assert values == {}
    assert any("unknown setting" in m for m in problems)


def test_reserved_and_comment_keys_are_silently_accepted():
    values, problems = config.validate(
        {"_note": "hi", "themes": {"x": {}}, "presets": {}, "palettes": {}})
    assert values == {} and problems == []


def test_root_must_be_an_object():
    values, problems = config.validate([1, 2, 3])
    assert values == {} and problems


def test_booleans_are_not_accepted_as_numbers():
    values, problems = config.validate({"idle_fps": True})
    assert values == {} and any(m.startswith("idle_fps:") for m in problems)


def test_bom_is_tolerated():
    with sandbox() as d:
        p = d / "bom.json"
        p.write_bytes(b"\xef\xbb\xbf" + json.dumps({"idle_fps": 7}).encode())
        values, _, problems = config.load(str(p))
        assert values == {"idle_fps": 7} and problems == []


def test_negative_throttle_is_allowed_meaning_never_exit():
    values, problems = config.validate({"throttle_minutes": -1})
    assert values["throttle_minutes"] == -1.0 and problems == []


def test_cycle_patterns_accepts_a_list_or_a_string():
    known = config.pattern_names()[:2]
    assert config.validate({"cycle_patterns": known})[0]["cycle_patterns"] == known
    as_text = ", ".join(known)
    assert config.validate({"cycle_patterns": as_text})[0]["cycle_patterns"] == known


def test_cycle_patterns_rejects_unknown_names():
    values, problems = config.validate({"cycle_patterns": ["dotfield", "nope"]})
    assert values == {} and any("nope" in m for m in problems)


def test_pattern_must_be_a_real_pattern():
    assert config.validate({"pattern": "plasma"})[0] == {"pattern": "plasma"}
    assert config.validate({"pattern": "wobble"})[0] == {}


def test_cycle_content_is_one_of_three():
    for good in ("patterns", "images", "mixed"):
        assert config.validate({"cycle_content": good}) == ({"cycle_content": good}, [])
    for bad in ("slideshow", "Mixed", "", 1, True, None, ["images"]):
        values, problems = config.validate({"cycle_content": bad})
        assert values == {}, bad
        assert len(problems) == 1 and problems[0].startswith("cycle_content:"), bad


def test_images_dir_is_a_path_or_null():
    assert config.validate({"images_dir": "C:/Pictures/Saver"})[0] == \
        {"images_dir": "C:/Pictures/Saver"}
    assert config.validate({"images_dir": None}) == ({"images_dir": None}, [])
    for bad in (5, True, ["C:/a", "C:/b"], {"path": "x"}):
        values, problems = config.validate({"images_dir": bad})
        assert values == {}, bad
        assert len(problems) == 1 and problems[0].startswith("images_dir:"), bad


def test_a_missing_images_dir_is_not_a_config_problem():
    # The folder may be a drive that isn't plugged in yet; the app rescans.
    with sandbox() as d:
        values, problems = config.validate({"images_dir": str(d / "not-yet")})
        assert problems == [] and values["images_dir"] == str(d / "not-yet")


# --------------------------------------------------------------------------- #
# Precedence: defaults < config file < command line
# --------------------------------------------------------------------------- #

def test_default_applies_when_nothing_else_says_otherwise():
    assert parse([], {}).idle_fps == config.DEFAULTS["idle_fps"]


def test_config_overrides_the_default():
    assert parse([], {"idle_fps": 9}).idle_fps == 9


def test_cli_overrides_the_config():
    assert parse(["--idle-fps", "30"], {"idle_fps": 9}).idle_fps == 30


def test_cli_can_switch_a_boolean_back_off():
    # The reason --color grew a --no-color twin: with colour enabled in the
    # config there was previously no way to turn it off for one run.
    assert parse([], {"color": True}).color is True
    assert parse(["--no-color"], {"color": True}).color is False
    assert parse(["--color"], {"color": False}).color is True


def test_slideshow_settings_follow_the_same_precedence():
    assert parse([], {}).cycle_content == "mixed"
    assert parse([], {}).images_dir is None
    assert parse([], {"cycle_content": "images"}).cycle_content == "images"
    assert parse(["--cycle-content", "patterns"],
                 {"cycle_content": "images"}).cycle_content == "patterns"
    assert parse(["--images-dir", "C:/mine"],
                 {"images_dir": "C:/theirs"}).images_dir == "C:/mine"


def test_the_command_line_refuses_an_unknown_cycle_content():
    try:
        with open(os.devnull, "w") as quiet, patched(sys, "stderr", quiet):
            parse(["--cycle-content", "slideshow"], {})
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("argparse should have refused it")


def test_parser_defaults_come_from_the_config_module():
    p = build_parser()
    for key, expected in config.DEFAULTS.items():
        assert p.get_default(key) == expected, key


# --------------------------------------------------------------------------- #
# Writing a config back out
# --------------------------------------------------------------------------- #

def test_write_config_round_trips():
    with sandbox() as d:
        target = d / "out.json"
        assert app_main(["--write-config", str(target)]) == 0
        values, path, problems = config.load(str(target))
        assert problems == [] and Path(path) == target
        for key, expected in config.DEFAULTS.items():
            if expected is not None:               # nulls are written but mean "unset"
                assert values[key] == expected, key


def test_written_config_carries_the_command_line_settings():
    with sandbox() as d:
        target = d / "out.json"
        app_main(["--idle-fps", "11", "--palette", "braille",
                  "--write-config", str(target)])
        values, _, _ = config.load(str(target))
        assert values["idle_fps"] == 11 and values["palette"] == "braille"


def test_starter_file_carries_and_explains_the_slideshow_settings():
    body = json.loads(config.dump_template())
    assert body["cycle_content"] == "mixed" and body["images_dir"] is None
    help_text = "\n".join(body["_help"])
    assert "cycle_content" in help_text and "images_dir" in help_text
    for kind in config.CYCLE_CONTENT:
        assert f'"{kind}"' in help_text, kind


def test_write_config_to_an_impossible_path_reports_and_exits_nonzero():
    with sandbox() as d:
        blocker = d / "afile"
        blocker.write_text("not a directory")
        assert app_main(["--write-config", str(blocker / "x.json")]) == 1


def test_ensure_exists_prefers_an_existing_file_over_creating_one():
    with sandbox() as d:
        existing = write(d / "mine.json", {"idle_fps": 5})
        with env(ASCIIVIZ_CONFIG=str(existing)):
            assert config.ensure_exists() == existing
        assert not config.user_config_path().exists()


def test_ensure_exists_creates_where_the_user_pointed():
    # If ASCIIVIZ_CONFIG names a file, creating it anywhere else would mean the
    # user edits a file the app then ignores.
    with sandbox() as d:
        target = d / "elsewhere" / "mine.json"
        with env(ASCIIVIZ_CONFIG=str(target)):
            assert config.ensure_exists() == target
        assert target.is_file()
        assert not config.user_config_path().exists()


def test_ensure_exists_creates_a_usable_starter_file():
    with sandbox():
        path = config.ensure_exists()
        assert path == config.user_config_path() and path.is_file()
        values, _, problems = config.load()
        assert problems == []                      # what we write, we can read
        assert values["idle_fps"] == config.DEFAULTS["idle_fps"]


# --------------------------------------------------------------------------- #
# Standalone runner
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    sys.exit(run_all(dict(globals())))
