"""Runtime configuration — settings from a JSON file instead of a rebuild.

Why this exists
---------------
Windows cannot pass command-line arguments to a ``.scr``, so until now every
screensaver tweak meant editing the args list in ``screensaver.py`` and
rebuilding the whole PyInstaller bundle (~36 MB) and reinstalling it. Settings
now come from a small JSON file read at startup, so the installed screensaver
can be retuned without a rebuild.

Precedence is **defaults < config file < command line**. That falls out of
applying :meth:`argparse.ArgumentParser.set_defaults` *before* ``parse_args()``:
an explicitly-passed flag always wins, and there is no "was this supplied?"
bookkeeping to get wrong.

Search order (first file that exists wins)
------------------------------------------
1. ``--config PATH``
2. the ``ASCIIVIZ_CONFIG`` environment variable
3. ``%APPDATA%\\ASCIIVisualizer\\config.json`` on Windows, or
   ``$XDG_CONFIG_HOME/asciiviz/config.json`` (default ``~/.config``) elsewhere
4. ``config.json`` beside the program — the directory containing the ``.exe`` /
   ``.scr`` when frozen by PyInstaller, the project directory otherwise

Robustness
----------
A screensaver runs with no console attached, so an unhandled exception at
startup is invisible and baffling — the saver simply never appears. **Nothing in
this module raises.** A missing file means defaults; an unparseable file means
defaults; a bad individual value means that one key falls back to its default
and the rest still apply. Problems are collected and returned so the caller can
show them in the HUD and print them to stderr.

Keys are the argparse ``dest`` names, so there is one vocabulary rather than
two: anything you can pass as ``--throttle-minutes`` is ``"throttle_minutes"``
here. Keys beginning with ``_`` are ignored, which gives JSON the comments it
otherwise lacks.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

CONFIG_NAME = "config.json"
CONFIG_ENV = "ASCIIVIZ_CONFIG"

#: Single source of truth for every default. ``app.build_parser`` reads these,
#: so the CLI and the config file can never drift apart.
DEFAULTS = {
    "mode": "generative",
    "palette": "dots",
    "pattern": None,            # None -> whatever the field starts on
    "color": False,
    "font_size": 16,
    "density": 0.6,
    "fps": 60,
    "width": 1100,
    "height": 700,
    "image": None,
    "video": None,
    "webcam": None,
    "screensaver": False,
    "cycle_seconds": 20.0,
    "cycle_patterns": None,     # None -> cycle all of them
    "full_minutes": 5.0,
    "throttle_minutes": 5.0,    # negative -> stay throttled, never self-exit
    "idle_fps": 2,
    "keep_display_awake": False,
}

#: Accepted silently and ignored for now — reserved for the presets/themes
#: phase, so people can write them early without being told they're unknown.
RESERVED = frozenset({"themes", "presets", "palettes"})


# --------------------------------------------------------------------------- #
# Where the file lives
# --------------------------------------------------------------------------- #

def program_dir() -> Path:
    """Directory of the running program.

    When PyInstaller freezes us into ``ASCIIVisualizer.scr`` this is the folder
    holding that file (often ``C:\\Windows\\System32``); otherwise it's the
    project directory. ``__file__`` would point inside the temporary unpack
    directory when frozen, which is wiped on exit — hence ``sys.executable``.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """Folder holding ``images/`` and ``captures/``.

    From source that's the project folder, as it always was. Frozen, it's the
    folder holding the ``.exe`` / ``.scr``: the app used to work this out from
    ``__file__``, which points into PyInstaller's temporary unpack folder, so
    every S-key screenshot was wiped the moment the program closed. If the
    program's folder can't be written to (a ``.scr`` copied into
    ``System32``), the per-user settings folder stands in.

    Creates ``images/`` as a side effect when frozen: that is the probe, and
    the app needs the folder anyway.
    """
    home = program_dir()
    if not getattr(sys, "frozen", False):
        return home
    try:
        (home / "images").mkdir(exist_ok=True)
        return home
    except OSError:
        return user_config_path().parent


def user_config_path() -> Path:
    """Per-user config location, the conventional one for the platform."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "ASCIIVisualizer" / CONFIG_NAME
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "asciiviz" / CONFIG_NAME


def search_paths(explicit=None):
    """The candidate paths, in priority order."""
    paths = []
    if explicit:
        paths.append(Path(explicit))
    env = os.environ.get(CONFIG_ENV)
    if env:
        paths.append(Path(env))
    paths.append(user_config_path())
    paths.append(program_dir() / CONFIG_NAME)
    return paths


def find(explicit=None):
    """First existing config file, or ``None``."""
    for p in search_paths(explicit):
        try:
            if p.is_file():
                return p
        except OSError:
            continue          # unreadable drive, bad path, permissions
    return None


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

class _Invalid(ValueError):
    pass


def _boolean(v):
    if isinstance(v, bool):
        return v
    raise _Invalid("expected true or false")


def _integer(lo=None, hi=None):
    def check(v):
        # bool is a subclass of int; a stray `true` here is a mistake, not a 1.
        if isinstance(v, bool) or not isinstance(v, int):
            raise _Invalid("expected a whole number")
        if lo is not None and v < lo:
            raise _Invalid(f"must be at least {lo}")
        if hi is not None and v > hi:
            raise _Invalid(f"must be at most {hi}")
        return v
    return check


def _number(lo=None, hi=None):
    def check(v):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise _Invalid("expected a number")
        v = float(v)
        if lo is not None and v < lo:
            raise _Invalid(f"must be at least {lo}")
        if hi is not None and v > hi:
            raise _Invalid(f"must be at most {hi}")
        return v
    return check


def _text(v):
    if not isinstance(v, str):
        raise _Invalid("expected a string")
    return v


def _one_of(options):
    """``options`` is a callable so pattern names are resolved lazily — it keeps
    this module importable without pulling in numpy."""
    def check(v):
        allowed = list(options())
        if not isinstance(v, str) or v not in allowed:
            raise _Invalid("expected one of: " + ", ".join(allowed))
        return v
    return check


def _text_list(options=None):
    def check(v):
        if isinstance(v, str):            # be kind: "a, b" works as well as a list
            v = [s.strip() for s in v.split(",") if s.strip()]
        if not isinstance(v, list) or not all(isinstance(s, str) for s in v):
            raise _Invalid("expected a list of names")
        if options is not None:
            allowed = list(options())
            bad = [s for s in v if s not in allowed]
            if bad:
                raise _Invalid("unknown name(s): " + ", ".join(bad)
                               + "; known: " + ", ".join(allowed))
        return v or None
    return check


def _nullable(check):
    def wrapped(v):
        return None if v is None else check(v)
    return wrapped


def _palette_names():
    from . import palettes
    return palettes.NAMES


def pattern_names():
    """Names of the generative patterns, in cycle order."""
    from . import patterns
    return [n for n, _ in patterns.PATTERNS]


SCHEMA = {
    "mode": _one_of(lambda: ("generative", "image", "video")),
    "palette": _one_of(_palette_names),
    "pattern": _nullable(_one_of(pattern_names)),
    "color": _boolean,
    "font_size": _integer(6, 200),
    "density": _number(0.05, 1.0),
    "fps": _integer(1, 240),
    "width": _integer(160, 16384),
    "height": _integer(120, 16384),
    "image": _nullable(_text),
    "video": _nullable(_text),
    "webcam": _nullable(_integer(0, 64)),
    "screensaver": _boolean,
    "cycle_seconds": _number(1.0, 86400.0),
    "cycle_patterns": _nullable(_text_list(pattern_names)),
    "full_minutes": _number(0.0, 10080.0),
    # No lower bound on purpose: a negative value means "stay in the throttled
    # phase and never self-exit", which is the knob for the open question about
    # Windows relaunching the saver after it bows out.
    "throttle_minutes": _number(None, 10080.0),
    "idle_fps": _integer(1, 240),
    "keep_display_awake": _boolean,
}


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

def validate(raw):
    """Split a raw dict into (clean values, problem messages).

    Unknown and malformed keys are reported and dropped, never fatal.
    """
    values, problems = {}, []
    if not isinstance(raw, dict):
        return {}, ["config root must be a JSON object ({...})"]
    for key, value in raw.items():
        if not isinstance(key, str) or key.startswith("_") or key in RESERVED:
            continue                     # comment key, or reserved for later
        check = SCHEMA.get(key)
        if check is None:
            problems.append(f"unknown setting {key!r} (ignored)")
            continue
        try:
            values[key] = check(value)
        except _Invalid as exc:
            problems.append(f"{key}: {exc} (using the default)")
        except Exception as exc:         # a validator itself misbehaving
            problems.append(f"{key}: could not be read ({exc}); using the default")
    return values, problems


def load(explicit=None):
    """Return ``(values, path_or_None, problems)``. Never raises."""
    path = find(explicit)
    if path is None:
        if explicit:
            return {}, None, [f"config file not found: {explicit}"]
        return {}, None, []
    try:
        text = path.read_text(encoding="utf-8-sig")   # tolerate a Windows BOM
    except OSError as exc:
        return {}, None, [f"could not read {path}: {exc}"]
    try:
        raw = json.loads(text)
    except ValueError as exc:
        return {}, path, [f"{path.name} is not valid JSON ({exc}); using defaults"]
    values, problems = validate(raw)
    return values, path, problems


# --------------------------------------------------------------------------- #
# Writing a starter file
# --------------------------------------------------------------------------- #

_HELP = [
    "ASCII Visualizer settings. Delete any line to fall back to its default.",
    "Keys match the command-line options: --throttle-minutes is throttle_minutes.",
    "Command-line flags override this file; this file overrides the defaults.",
    "throttle_minutes: minutes at idle_fps after full_minutes, then the saver",
    "  exits. Use a negative number to stay throttled and never exit.",
    "cycle_patterns: which patterns the screensaver rotates, e.g.",
    '  ["dotfield", "plasma"]. Omit or null to cycle all of them.',
    "Any key starting with _ is ignored, so use them for your own notes.",
]


def dump_template(values=None) -> str:
    """JSON text for a starter config: every setting at its current value."""
    values = dict(DEFAULTS if values is None else values)
    body = {"_help": _HELP}
    for key in SCHEMA:                      # SCHEMA order, not dict-insertion luck
        if key in values:
            body[key] = values[key]
    return json.dumps(body, indent=2) + "\n"


def write_template(path, values=None):
    """Write a starter config. Returns the path; raises only on real I/O errors
    (callers that must not fail should catch)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_template(values), encoding="utf-8")
    return path


def ensure_exists(explicit=None, values=None):
    """Path to the config file, creating a starter one if none exists yet.

    Used by the screensaver's Windows "Settings" button: it should open whatever
    file is actually in effect, and only create one when there is nothing to
    open. When it does create one, it uses the location the user pointed at
    (``--config`` or the environment variable) if they named one, since putting
    it somewhere else would mean editing a file that then gets ignored.
    """
    found = find(explicit)
    if found is not None:
        return found
    target = explicit or os.environ.get(CONFIG_ENV) or user_config_path()
    return write_template(Path(target), values)
