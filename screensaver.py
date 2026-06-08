#!/usr/bin/env python3
"""Windows screensaver entry point for ASCII Visualizer.

Windows launches a ``.scr`` with one of these command lines:

    (no args)     run the screensaver (we treat a bare double-click as "run")
    /s            run the screensaver fullscreen
    /p <hwnd>     preview inside the Settings dialog's mini-monitor
    /c[:<hwnd>]   show the configuration dialog

Build this into ``ASCIIVisualizer.scr`` with ``build_screensaver.ps1`` (or
``.bat``) on Windows — see the README's "Windows screensaver" section.
"""

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


def _show_config():
    """A minimal configuration dialog (there are no options yet)."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "ASCII Visualizer",
            "ASCII Visualizer screensaver\n\n"
            "It cycles through the generative patterns automatically.\n"
            "For palettes, images, and webcam, run the app directly:\n"
            "    python main.py",
        )
        root.destroy()
    except Exception:
        pass  # no display / tkinter unavailable — nothing to configure


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    mode, _hwnd = parse_mode(argv)

    if mode == "c":
        _show_config()
        return
    if mode == "p":
        # Rendering into the Settings mini-monitor (a parent HWND) isn't
        # supported; exit quietly so the dialog shows a blank preview.
        return

    # mode == "s": run the visualizer in fullscreen screensaver mode.
    # Tweak these timings to taste, then rebuild the .scr (Windows can't pass
    # command-line options to a screensaver itself, so they're baked in here):
    args = [
        "--screensaver",
        "--full-minutes", "5",      # full-speed animation while you might watch
        "--throttle-minutes", "5",  # then near-idle (low CPU) for a bit
        "--idle-fps", "2",          # frame rate during the throttle phase
        # "--keep-display-awake",   # uncomment for always-on "art mode"
    ]
    from asciiviz.app import build_parser, App
    opts = build_parser().parse_args(args)
    App(opts).run()


if __name__ == "__main__":
    main()
