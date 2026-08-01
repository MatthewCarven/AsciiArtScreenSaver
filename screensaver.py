#!/usr/bin/env python3
"""Windows screensaver entry point for ASCII Visualizer.

Windows launches a ``.scr`` with one of these command lines:

    (no args)     run the screensaver (we treat a bare double-click as "run")
    /s            run the screensaver fullscreen
    /p <hwnd>     preview inside the Settings dialog's mini-monitor
    /c[:<hwnd>]   show the configuration dialog

Settings are **not** baked in any more. Windows can't pass command-line options
to a screensaver, so they come from ``config.json`` instead — see
``asciiviz/config.py`` for where that file is looked for. Clicking "Settings" in
the Windows screensaver picker (the ``/c`` command line) opens that file in an
editor, creating a starter one first if it doesn't exist yet. So retuning the
saver no longer needs a rebuild.

Build this into ``ASCIIVisualizer.scr`` with ``build_screensaver.ps1`` (or
``.bat``) on Windows — see the README's "Windows screensaver" section.
"""

import os
import subprocess
import sys


def parse_mode(argv):
    """Return ('s' | 'p' | 'c', hwnd_or_None) from a Windows .scr command line."""
    if len(argv) < 2 or not argv[1]:
        return "s", None
    arg = argv[1].lower()
    flag = arg[:2]
    if flag == "/p":
        hwnd = argv[2] if len(argv) > 2 else (arg[3:] or None)
        return "p", hwnd
    if flag == "/c":
        return "c", None
    if flag == "/s":
        return "s", None
    return "s", None


def _open_in_editor(path) -> bool:
    """Open a file in the platform's text editor. True if something launched."""
    try:
        if os.name == "nt":
            # Notepad rather than the default .json handler: that handler is
            # often a browser (which can't save it) or a heavyweight IDE. Notepad
            # is always present and edits the file immediately.
            try:
                subprocess.Popen(["notepad.exe", str(path)])
                return True
            except OSError:
                os.startfile(str(path))  # Windows-only fallback
                return True
        subprocess.Popen(["xdg-open", str(path)])
        return True
    except Exception:
        return False


def _message(text):
    """Best-effort dialog; falls back to stdout when there's no display."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("ASCII Visualizer", text)
        root.destroy()
    except Exception:
        print(text)


def _show_config():
    """The Windows "Settings" button: open the settings file the saver actually
    reads, creating a starter one if there isn't a config anywhere yet."""
    from asciiviz import config
    try:
        path = config.ensure_exists()
    except OSError as exc:
        _message(f"Couldn't create a settings file:\n\n{exc}")
        return
    if not _open_in_editor(path):
        _message("Edit your screensaver settings here:\n\n"
                 f"{path}\n\nSave the file, then restart the screensaver.")


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    mode, _hwnd = parse_mode(argv)

    if mode == "c":
        _show_config()
        return 0
    if mode == "p":
        # Rendering into the Settings mini-monitor (a parent HWND) isn't
        # supported; exit quietly so the dialog shows a blank preview.
        return 0

    # mode == "s": run fullscreen. Everything else — timings, palette, which
    # patterns cycle — comes from config.json, falling back to exactly the
    # defaults this file used to hard-code.
    from asciiviz.app import main as app_main
    return app_main(["--screensaver"])


if __name__ == "__main__":
    sys.exit(main())
