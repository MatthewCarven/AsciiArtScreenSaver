#!/usr/bin/env python3
"""Entry point for the ASCII Visualizer.

Run from this folder:

    python main.py                  # generative dot-field idle mode
    python main.py --mode image     # start on an image
    python main.py --image path/to/photo.jpg
    python main.py --palette braille --color

See the README for the full list of runtime controls.

``build.ps1`` (or ``build.bat``) freezes this file into ``ASCIIVisualizer.exe``,
which takes exactly the same options.
"""

import os
import sys


def _parent_pid(pid):
    """The id of the process that started ``pid`` (Windows), or None."""
    import ctypes
    from ctypes import wintypes

    class Entry(ctypes.Structure):              # PROCESSENTRY32W
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", wintypes.LONG), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", wintypes.WCHAR * 260)]

    # A private handle on kernel32, so these signatures don't leak into
    # ctypes.windll.kernel32 for pygame or anyone else in the process.
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    kernel32.Process32FirstW.argtypes = (wintypes.HANDLE, ctypes.POINTER(Entry))
    kernel32.Process32NextW.argtypes = (wintypes.HANDLE, ctypes.POINTER(Entry))
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

    snap = kernel32.CreateToolhelp32Snapshot(0x2, 0)    # TH32CS_SNAPPROCESS
    if snap in (None, wintypes.HANDLE(-1).value):       # INVALID_HANDLE_VALUE
        return None
    try:
        entry = Entry(dwSize=ctypes.sizeof(Entry))
        found = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while found:
            if entry.th32ProcessID == pid:
                return entry.th32ParentProcessID
            found = kernel32.Process32NextW(snap, ctypes.byref(entry))
        return None
    finally:
        kernel32.CloseHandle(snap)


def _attach_parent_console():
    """Give the built ``ASCIIVisualizer.exe`` somewhere to print.

    The exe is a windowed program, so a double-click opens just the visualizer
    with no terminal beside it. The price is that Windows gives it no console,
    and ``--help``, ``--list-patterns``, ``--write-config`` and any bad-option
    error would print to nowhere. When it was started from a terminal, borrow
    that terminal's console instead. A double-click has no parent console, so
    nothing changes there; running from source never gets this far.

    The one-file exe is two processes: PyInstaller's launcher unpacks Python
    and starts a second copy of itself to run it. So the terminal is usually
    this process's grandparent, and the parent (the launcher) has no console
    to lend.
    """
    if os.name != "nt" or not getattr(sys, "frozen", False) or sys.stdout is not None:
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        attached = kernel32.AttachConsole(-1)       # ATTACH_PARENT_PROCESS
        if not attached:
            grandparent = _parent_pid(os.getppid())
            attached = grandparent is not None and kernel32.AttachConsole(grandparent)
        if not attached:
            return
        encoding = f"cp{kernel32.GetConsoleOutputCP()}"
        out = open("CONOUT$", "w", encoding=encoding, errors="replace")
        sys.stdout = sys.stderr = out
        print()     # the shell has already redrawn its prompt; start below it
    except Exception:
        pass


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")   # no banner in the .exe
        _attach_parent_console()
    from asciiviz.app import main
    sys.exit(main())
