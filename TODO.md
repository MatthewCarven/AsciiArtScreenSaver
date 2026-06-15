# TODO

## Field run — Matthew (blocking)
- [ ] Delete stale git lock/temp files (sandbox can't unlink them; they'll block
      future commits): `.git\HEAD.lock`, `.git\index.lock`, and the four
      `.git\objects\**\tmp_obj_*` files (in `11\`, `31\`, `a1\`, `e9\`).
      (Re-confirmed 2026-06-16: sandbox still gets "Operation not permitted".)
- [x] Rebuild the .scr: rebuilt + installed cleanly on 2026-06-16 ("works
      flawlessly"). Now carries the wind-down timings (5 full / 5 throttle / exit).
- [ ] Overnight test (in progress, night of 2026-06-16): wake the PC a few times,
      watch CPU/fan. Two things to note:
      - Does the fan actually go quiet after the ~5-min full-speed phase?
      - After the saver self-exits (~10 min total), does Windows relaunch it while
        still idle? If it loops annoyingly: crank `--throttle-minutes` way up in
        `screensaver.py`'s args list (throttle-and-stay), or drop the timed exit.
- [ ] Webcam check: press `V` in the app — confirm the live feed renders
      (couldn't be tested in the sandbox, no camera).
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
