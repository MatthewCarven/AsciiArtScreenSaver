"""Tests for what changes once PyInstaller freezes the app into an .exe / .scr.

Frozen, ``__file__`` points into PyInstaller's temporary unpack folder, which is
wiped when the program closes, so anything the app keeps (images, S-key
captures) has to be found from ``sys.executable`` instead. These tests fake the
frozen state by patching ``sys.frozen`` and ``sys.executable``.

Runs under pytest, or standalone with ``python tests/test_frozen.py``.
"""

import contextlib
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))     # the project
sys.path.insert(0, str(HERE))            # _support
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")   # app.py imports pygame
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from _support import patched, run_all, sandbox   # noqa: E402

from asciiviz import config                       # noqa: E402
from asciiviz.app import App, build_parser        # noqa: E402

PROJECT = HERE.parent


@contextlib.contextmanager
def frozen_at(exe):
    """Pretend to be a PyInstaller build living at ``exe``."""
    with patched(sys, "frozen", True), patched(sys, "executable", str(exe)):
        yield


# --------------------------------------------------------------------------- #
# Where images/ and captures/ live
# --------------------------------------------------------------------------- #

def test_from_source_the_data_folder_is_the_project():
    assert config.data_dir() == PROJECT


def test_frozen_the_data_folder_is_beside_the_program():
    with sandbox() as d:
        with frozen_at(d / "ASCIIVisualizer.exe"):
            assert config.data_dir() == d.resolve()
        assert (d / "images").is_dir(), "images/ should have been made beside it"


def test_frozen_in_an_unwritable_folder_falls_back_to_the_user_folder():
    # A .scr copied into System32 can't make images/ beside itself. Stand-in:
    # a "folder" that is really a file, so mkdir inside it always fails.
    with sandbox() as d:
        blocker = d / "blocker"
        blocker.write_text("not a folder")
        with frozen_at(blocker / "ASCIIVisualizer.scr"):
            assert config.data_dir() == config.user_config_path().parent


# --------------------------------------------------------------------------- #
# The app itself, frozen
# --------------------------------------------------------------------------- #

def test_frozen_app_saves_captures_beside_the_program():
    with sandbox() as d:
        with frozen_at(d / "ASCIIVisualizer.exe"):
            app = App(build_parser().parse_args([]))
            saved = app._save_capture()
        assert saved is not None and saved.is_file()
        assert saved.parent == d.resolve() / "captures"
        assert app.toast_text.startswith("saved")


def test_a_failed_capture_is_reported_not_raised():
    with sandbox() as d:
        with frozen_at(d / "ASCIIVisualizer.exe"):
            app = App(build_parser().parse_args([]))
        (d / "captures").write_text("a file where the folder should be")
        assert app._save_capture() is None
        assert app.toast_text.startswith("couldn't save")


def test_frozen_app_still_starts_when_nowhere_is_writable():
    # The screensaver must never fail to appear over a folder it can't write.
    with sandbox() as d:
        blocker = d / "blocker"
        blocker.write_text("not a folder")
        with frozen_at(blocker / "ASCIIVisualizer.scr"), \
                patched(config, "user_config_path", lambda: blocker / "x" / "config.json"):
            app = App(build_parser().parse_args(["--screensaver"]))
        assert app.images == []
        assert app._current_image_path() is None


# --------------------------------------------------------------------------- #
# Borrowing the terminal's console (main.py)
# --------------------------------------------------------------------------- #

def test_parent_pid_finds_who_started_this_process():
    # The built exe walks one step past PyInstaller's launcher with this to
    # reach the terminal; here it just has to agree with the OS.
    if os.name != "nt":
        return
    import main
    assert main._parent_pid(os.getpid()) == os.getppid()
    assert main._parent_pid(0xFFFFFFF0) is None     # no such process


# --------------------------------------------------------------------------- #
# Standalone runner
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    sys.exit(run_all(dict(globals())))
