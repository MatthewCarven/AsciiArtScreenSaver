"""Shared test helpers.

Deliberately fixture-free so every test file runs two ways: under pytest, and
standalone with ``python tests/test_whatever.py``. Verifying a change should
never depend on having pytest installed.
"""

import contextlib
import json
import os
import tempfile
from pathlib import Path


@contextlib.contextmanager
def env(**pairs):
    """Temporarily set environment variables; ``None`` unsets one."""
    saved = {k: os.environ.get(k) for k in pairs}
    try:
        for k, v in pairs.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = str(v)
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@contextlib.contextmanager
def sandbox():
    """A temp dir with the whole config search path redirected inside it.

    Every test that might *create* a config file must use this. Without it a
    test writes into the developer's real ``~/.config`` or ``%APPDATA%``, which
    then silently changes the result of later tests — exactly the failure that
    prompted this helper.
    """
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "home").mkdir()
        with env(ASCIIVIZ_CONFIG=None, XDG_CONFIG_HOME=str(d / "home"),
                 APPDATA=str(d / "home"), HOME=str(d / "home")):
            yield d


@contextlib.contextmanager
def patched(obj, name, value):
    """Swap an attribute for the duration of the block."""
    missing = object()
    saved = getattr(obj, name, missing)
    setattr(obj, name, value)
    try:
        yield
    finally:
        if saved is missing:
            delattr(obj, name)
        else:
            setattr(obj, name, saved)


def write(path, data):
    """Write JSON (or raw text, if given a string) to ``path``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data),
                    encoding="utf-8")
    return path


def run_all(namespace):
    """Run every ``test_*`` in a module's globals. Returns a process exit code."""
    tests = [(n, f) for n, f in sorted(namespace.items())
             if n.startswith("test_") and callable(f)]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"  pass  {name}")
        except Exception as exc:
            failed.append(name)
            print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - len(failed)}/{len(tests)} passed")
    return 1 if failed else 0
