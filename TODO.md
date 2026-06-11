# TODO

## Field run — Matthew (blocking)
- [ ] Rebuild the .scr: the checked-in `ASCIIVisualizer.scr` / `dist\ASCIIVisualizer.exe`
      predate the wind-down changes. Run `build_screensaver.bat`, then re-install
      (right-click the new .scr → Install, or copy into place).
- [ ] Webcam check: press `V` in the app — confirm the live feed renders
      (couldn't be tested in the sandbox, no camera).
- [ ] Wind-down open question: after the saver self-exits (~10 min default:
      5 full-speed + 5 throttled), does Windows relaunch it while still idle?
      - If it loops annoyingly: crank `--throttle-minutes` way up in
        `screensaver.py`'s args list (throttle-and-stay), or drop the timed exit.
- [ ] General eyeball: patterns (`G` to cycle), palettes, HUD fade, image mode.

## Backlog — Claude (unblocked, any time)
- [ ] Brightness/contrast control for image mode (braille+colour reads dim on
      dark images).
- [ ] Palette editor.
- [ ] Export to animated GIF.

## Standing notes
- Sandbox mirror has served stale copies of `app.py`/`generative.py` before —
  verify against real files via read-back, build test copies in /tmp.
- Repo is local only — no remote configured; flag if pushing is ever wanted.
