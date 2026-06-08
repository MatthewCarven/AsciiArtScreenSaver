# Worklog

## 2026-06-08 — Initial build

Built the first working version of the ASCII Visualizer from scratch.

**Decisions**
- pygame desktop app (matches the project folder; can go fullscreen as a real
  screensaver).
- Single core abstraction: a brightness field in `[0, 1]` feeds every palette,
  so generative and image modes share the same conversion engine.
- Three palettes per the brief — dots, grayscale ramp, braille (2×4 sub-pixel
  packing, with ordered/Bayer dithering for smooth image tones).
- Both sources: a generative drifting dot-field (idle/screensaver) and
  image-to-ASCII with aspect-correct fitting and a dissolve-in reveal.

**Implemented**
- `engine.py` (field→glyphs, braille packing, image loading, sample generator),
  `generative.py` (layered sines + wandering radial sources, density control),
  `renderer.py` (font discovery incl. braille-capability detection, fast row
  rendering + cached per-cell blits), `app.py` (loop, input, HUD, CLI).
- Live controls: mode/palette/colour toggles, resolution, density, fullscreen,
  PNG capture, HUD. CLI flags for all of the above.
- Ships a generated sample image so image mode works out of the box.

**Verification (headless, SDL dummy driver)**
- 15 logic checks pass (ramp mapping, braille bit-packing incl. known glyphs
  U+28FF/U+2800/U+2801, field shapes, image aspect fitting).
- Rendered sample frames for every mode/palette and eyeballed them — dot-field
  and dots/ramp image conversion look great; braille verified crisp in mono.
- Full `App.run()` smoke-tested across 4 config combos + `python -m asciiviz`;
  no exceptions.

**Notes / next ideas**
- Not a git repo yet — flagging for Matthew to `git init` if desired.
- Braille + colour on very dark images reads dim (small dots + dark source);
  fine on brighter/real photos, and braille-mono is crisp. Could add a
  brightness/contrast control for image mode.
- Possible follow-ups: video/webcam input, more generative patterns (flow
  fields, reaction-diffusion), palette editor, export to animated GIF.

### Later same day — attribution
- Added an "Acknowledgements & inspiration" section to the README: credits the
  Claude desktop app's ambient idle animation as the visual inspiration, states
  the project is independent/unofficial and shares no code or assets, and notes
  the Anthropic trademarks. Title kept as "ASCII Visualizer" (safer than naming
  it after the trademark); Matthew can rename anytime.

## 2026-06-09

- Added HUD auto-fade: stays full for 15s after the last input, fades over 1s,
  and relights instantly on any key press or mouse movement (`H` still hard-
  toggles). Implemented via a `last_activity` timestamp + a `BLEND_RGBA_MULT`
  alpha multiply on the HUD panel. Verified headless (full/mid-fade/hidden
  render frames + pixel checks; run-loop smoke across modes).
- Queued backlog tasks: webcam/video input, more generative patterns, and
  Windows `.scr` packaging.
- Note: the Linux sandbox mirror of the project folder served a stale, truncated
  copy of `app.py` mid-session (a sync hiccup on the tooling side). The real
  on-disk file is complete and correct (405 lines); verification was run against
  a faithfully reconstructed copy.

### More generative patterns
- Added `asciiviz/patterns.py` with five selectable idle patterns: dotfield
  (the original), plasma, ripples, flow, and starfield. `GenerativeField` now
  dispatches to the selected pattern and applies the shared density/contrast
  shaping, so the +/- density control works across all of them.
- New `G` key cycles patterns (and switches to generative mode); the HUD shows
  the active pattern name and a `[G]` hint.
- Bug caught in verification: starfield rendered empty because star brightness
  and twinkle phase were derived from the same hash, so the brightest stars
  dimmed in unison below the density threshold. Fixed by splitting selection and
  twinkle phase into two independent integer hashes.
- Verified: each pattern rendered to a frame and eyeballed; an integrated
  G-cycle + run-loop smoke test passes against a reconstructed copy (the mirror
  is still stale for app.py/generative.py, so this was run via /tmp). Real files
  confirmed correct via read-back.

### Webcam / video input
- Added `asciiviz/video.py`: a `VideoSource` wrapping OpenCV `VideoCapture` for
  a webcam (device index) or a video file. Converts each frame to the same
  brightness/colour fields as the image source (reuses engine `_placement`),
  mirrors the webcam like a selfie, loops video files, and throttles file
  playback to the clip's native fps.
- app.py: new "video" mode. `V` toggles the webcam; `--video PATH` / `--webcam
  [INDEX]` start in video mode; the draw loop auto-releases the camera when you
  switch to any other mode. HUD shows the active source.
- OpenCV is an optional dependency — if it's missing, video is disabled with a
  toast and the rest of the app is unaffected.
- Verified: video.py standalone (fields for all palettes, file looping, bad
  device handling) and full integration (play `--video`, palette/colour variants,
  graceful no-camera fallback, `--video` run-loop selftest) via a clean /tmp
  reconstruction; all 9 app.py edits confirmed on the real file by read-back.
- Webcam live capture itself couldn't be tested here (no camera in the sandbox) —
  Matthew to confirm the live feed.

### Windows .scr screensaver
- Added `screensaver.py` (the .scr entry point): parses `/s` (run), `/p`
  (preview — exits blank, not supported), `/c` (config — minimal Tk messagebox),
  and a bare launch (runs). Builds via `build_screensaver.ps1` / `.bat` using
  PyInstaller (`--onefile --noconsole`, excludes cv2 to stay small).
- app.py: new `--screensaver` mode (+ `--cycle-seconds`). Starts fullscreen,
  hides the cursor, drops the HUD, auto-cycles generative patterns, and exits on
  any key / click / >5px mouse move (the first motion event anchors, so jitter
  doesn't instantly kill it).
- Can't build/run a real .scr here (no Windows; PyInstaller can't cross-compile),
  so verified all logic headlessly — parse_mode, _ss_should_exit, auto-cycle,
  and the /s /c /p entry paths — via the /tmp reconstruction. Matthew runs the
  one build command on Windows.
- Standing note: the sandbox's mirror of the folder stayed stale/corrupt for
  app.py and generative.py this whole session; every change was verified against
  the real files (read-back) and clean /tmp reconstructions instead.

### Keep the display awake (Matthew's one regret, fixed)
- Screensaver now calls `SetThreadExecutionState(ES_CONTINUOUS |
  ES_DISPLAY_REQUIRED)` on start and clears it (`ES_CONTINUOUS`) on exit, via
  ctypes — so it holds the monitor on while it's showing instead of needing the
  user to disable Windows' "turn off display" power setting. The documented
  kernel32 approach (what media players use), not a WM_SYSCOMMAND hook. Guarded
  to a no-op off Windows.
- Verified by mocking kernel32 and asserting the exact flags (0x80000002 on,
  0x80000000 off), plus the posix no-op and a full screensaver run.

### Screensaver wind-down (the behaviour Matthew actually wanted)
- Reversed the default: the screensaver no longer holds the display awake.
  `SetThreadExecutionState` is now opt-in via `--keep-display-awake`; by default
  Windows powers off the display / sleeps on its own timers underneath.
- Three-phase life: full speed for `--full-minutes` (default 5), then throttle to
  `--idle-fps` (default 2) for `--throttle-minutes` (default 5), then the process
  exits — so CPU/fans go quiet instead of droning all night, and the timed exit
  hands control fully back to Windows. `screensaver.py` spells the timings out as
  an editable args list (a .scr can't take CLI args from Windows, so rebuild to
  change them).
- Verified: keep_awake gating (default off / flag on), phase thresholds
  (full→throttle→done at the right times), and an unattended run that self-exits
  cleanly with no input and no selftest cap.
- Open question for the morning: whether Windows relaunches the saver after it
  self-exits while still idle (version-dependent). If it loops annoyingly, push
  --throttle-minutes way up (effectively throttle-and-stay) or drop the exit.
