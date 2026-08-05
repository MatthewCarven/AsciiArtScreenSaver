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

## 2026-06-11 — Checkpoint before field run

- All queued backlog items are done and committed (patterns, video/webcam,
  .scr packaging, wind-down). Project paused pending Matthew's field run.
- Created `TODO.md` capturing the test checklist (rebuild .scr — the existing
  binary predates the wind-down changes — webcam check, relaunch-after-exit
  question) and the unqueued backlog (image brightness/contrast, palette
  editor, GIF export).
- Session being archived; next session picks up from TODO.md.

## 2026-06-16 — Field run begins

- Matthew rebuilt the `.scr` via `build_screensaver.bat` and installed it; reports
  it "works flawlessly". The installed binary now carries the wind-down timings
  (5 min full-speed → 5 min throttle @ 2fps → self-exit; display-awake off).
- Overnight CPU/fan test now running: Matthew will wake the PC a few times through
  the night to watch fan behaviour and check whether Windows relaunches the saver
  after it self-exits while idle (the open question from 06-09). Results to follow.
- Still blocked for commits: the four `tmp_obj_*` files + `HEAD.lock`/`index.lock`
  under `.git\` — re-tried from the sandbox today, still "Operation not permitted".
  Matthew to delete them before the next commit lands.

## 2026-08-01 — Roadmap planning (no code changes)

Matthew asked what else the project could grow into. Read the whole codebase,
put up a menu of options, and he picked four to plan but not yet build. So this
session is planning only — `TODO.md` was rewritten as a prioritised roadmap with
approach notes, risks and open decisions per item, and nothing was implemented.

**Chosen, in build order**

1. **Runtime config** — JSON read at startup (CLI flag → env var → `%APPDATA%` →
   beside the exe), so screensaver settings stop requiring a PyInstaller rebuild.
2. **More generative patterns** — Doom fire, Matrix rain, Life, Mandelbrot,
   kaleidoscope, reaction-diffusion.
3. **Presets, colour themes & custom palettes** — absorbs the old "palette
   editor" backlog item.
4. **Edge-aware image mode** — DoG + Sobel directional glyphs; absorbs the old
   image brightness/contrast backlog item.

**Why that order.** Not by excitement — by dependency. R1 is unglamorous but it
fixes the feedback loop: today every screensaver tweak costs a full 36 MB
PyInstaller rebuild plus a reinstall, so auditioning eight new patterns without a
config file means eight rebuild cycles. R3 reuses R1's config machinery. R4 is
last because it's the only one that touches the hot path and the image cache, and
it wants a test harness alongside it.

**Design questions surfaced while planning** (recorded in TODO.md so they get
decided deliberately rather than drifted into):
- Patterns are currently pure functions of `(X, Y, t)`. Fire, Life and
  reaction-diffusion need frame-to-frame state — proposed a backwards-compatible
  contract where an entry may be a callable object with an optional `reset()`.
- Stateful patterns versus the 2 fps throttle phase: a sim advancing two steps
  per second looks broken. Either substep by `dt` or skip stateful patterns while
  throttled.
- Braille evaluates patterns at 4× the rows and 2× the columns. Sine patterns are
  resolution-independent by design; cellular ones aren't.
- Matrix rain wants specific *glyphs*, not brightness — the first real pressure
  on the single-brightness-field abstraction. Approximate, or add an optional
  per-cell glyph channel.
- If the app writes presets back into the same file a human hand-edits, saving
  reformats their work. Proposed split: `config.json` read-only to the app,
  `presets.json` app-managed.

**Parked** (raised, not scheduled, written down so they don't need
rediscovering): audio-reactive mode, pattern crossfades and CRT/bloom post-FX,
GIF/MP4/ANSI/HTML export plus a headless `convert` CLI, a proper test suite,
screen-capture source, screensaver image slideshow, multi-monitor, and real `/p`
preview support.

**Corrections to stale notes**
- The repo is no longer local-only — `origin` points at
  `MatthewCarven/AsciiArtScreenSaver` and the last commit was pushed. Docs said
  otherwise.
- The git lock problem was overstated. `HEAD.lock`/`index.lock` are gone, and the
  four `tmp_obj_*` files are orphaned temp objects that do **not** block commits.
  What actually happens: the mount forbids `unlink`, so git leaves a stale
  `.git/index.lock` behind after any index-touching command, which blocks the
  *next* one. Working around it by `mv`-ing the lock into `_to_delete/` (moves are
  permitted) and using `--no-optional-locks` for read-only checks. Commits work.
- Left open: the overnight CPU/fan test from 2026-06-16 has no recorded result.
  Worth noting R1 would let those timings be retuned without another rebuild.
- `Claude.md` shows modified in git but the content is identical — only the line
  endings flipped to CRLF. Left alone; flagged for Matthew to commit or revert,
  and `.gitattributes` would stop it recurring.

## 2026-08-01 — R1: runtime config (shipped)

Matthew deleted the git litter and pushed the roadmap commit, then said carry
on — so this session built R1, the first roadmap item.

**The problem it solves.** Windows can't pass command-line arguments to a
`.scr`, so `screensaver.py` hard-coded an args list that PyInstaller baked into
the binary. Changing the wind-down timings meant a 36 MB rebuild plus a
reinstall to System32. Now they come from a JSON file read at startup.

**New: `asciiviz/config.py`**
- Search order, first hit wins: `--config PATH` → `ASCIIVIZ_CONFIG` →
  `%APPDATA%\ASCIIVisualizer\config.json` (or `~/.config/asciiviz/`) →
  `config.json` beside the program. "Beside the program" uses `sys.executable`
  when frozen, because `__file__` points into PyInstaller's temp unpack dir,
  which is wiped on exit.
- JSON, not TOML: stdlib only, no new dependency, and `tomllib` is 3.11+ while
  this project has been run on 3.10. Keys beginning with `_` are ignored, which
  gives JSON the comments it otherwise lacks.
- **Nothing in the module raises.** A screensaver has no console, so an
  exception at startup is invisible — you just get a saver that never appears.
  Missing file, unparseable file, or one bad value all degrade to defaults, and
  the problems are collected and surfaced as a HUD toast plus stderr.
- `DEFAULTS` is now the single source of truth: `build_parser` reads its values,
  so the CLI and the config file cannot drift apart. A test asserts that.

**Precedence** is defaults → config file → command line, and it falls out of
ordering rather than bookkeeping: `parser.set_defaults(**config_values)` runs
before `parse_args`, so an explicitly-typed flag still wins. `--config` has to
be read first with a throwaway pre-parser, since it decides what the defaults
are.

**Also landed while in there**
- `--pattern NAME`, `--list-patterns`, `--cycle-patterns a,b,c`, `--write-config`.
- `--no-color` / `--no-screensaver` / `--no-keep-display-awake` via
  `argparse.BooleanOptionalAction`. Needed because with `color: true` in a
  config there was previously no way to turn it off for a single run.
- `cycle_patterns` restricts what the *screensaver* rotates; the `G` key still
  cycles everything, since that setting is for unattended running, not for the
  person at the keyboard.
- **`throttle_minutes: -1` means "stay throttled, never self-exit"** — the knob
  for the open field-run question about Windows relaunching the saver. Answering
  that no longer costs a rebuild.
- The run loop's phase logic moved into `_ss_fps()` and `_ss_finished()`, so the
  wind-down can be tested at ten thousand seconds instead of in ten minutes.
- The Windows `/c` Settings button used to show a stub messagebox saying there
  was nothing to configure. It now opens the config file in Notepad (creating a
  starter one if needed), falling back to a dialog showing the path if nothing
  launches. It opens the file that's actually *in effect* rather than creating a
  second one that would shadow it.

**Verification.** 46 tests in a new `tests/` directory — search order, precedence
three ways, malformed and partial JSON, unknown/reserved/comment keys, BOM
tolerance, the frozen-executable path, `--write-config` round-tripping, the
`.scr` entry points, wind-down phases, and pattern rotation. They run under
pytest *or* standalone (`python tests/test_config.py`), deliberately
fixture-free, so verifying a change never needs pytest installed. Beyond that:
every mode/palette combination smoke-tested through the run loop, and two frames
rendered and eyeballed — one driven by a config file, one on defaults — to
confirm the settings visibly land and nothing regressed.

**Deviation from the plan, noted per the working agreement:** the roadmap had a
test suite parked for later. Writing one here was cheap (the config logic is
pure and fast to test) and it caught two real bugs, so it went in early. R4 now
has somewhere to put engine tests.

**Two bugs the tests caught**
- `ensure_exists()` created the starter config at the per-user path even when
  `ASCIIVIZ_CONFIG` named somewhere else — so the Settings button would have
  opened a file the saver then ignored. Now it creates where the user pointed.
- A test that didn't sandbox `HOME` wrote a config into the container's real
  home directory, which then silently changed a later test's result. Hence
  `sandbox()` in `tests/_support.py`, and a standing note about it.

**Behaviour with no config file present is byte-identical to before** — the
defaults are exactly the values `screensaver.py` used to hard-code.

**Hand-off:** one `.scr` rebuild to pick this up, and it should be the last one
ever needed for a settings change.

### Session close — 2026-08-01

Matthew is archiving the session and will field-test later. Expanded the field
run section of `TODO.md` into a proper run sheet: rebuild, windowed app, webcam,
the new config file (including deliberately breaking it, since a screensaver
that won't start reports nothing at all), the Settings button, and the overnight
relaunch question — which `throttle_minutes: -1` now answers without a rebuild.
Notes on anything odd go in this file under a dated heading; that's what the
next session reads first.

State at close: everything committed (`9adeded`), one commit unpushed, working
tree clean apart from `Claude.md`'s CRLF-only diff. Nothing lives only in the
sandbox.

## 2026-08-05 — R2 scoped with Matthew (planning only, no code)

Matthew came back asking for more patterns and whether images from a source
folder could drive the screensaver — then, offered the R2 candidates as a menu,
picked *all of them* and asked to "just plan the future with me for now". So,
like 2026-08-01: a planning session. Nothing was built; `TODO.md` now carries
the full plan and this entry records the choices.

**Decisions (Matthew's, via the question widget; detail in TODO.md)**

- **R2 scope: every candidate group** — Doom fire, Matrix rain, lava lamp,
  Life-with-trails, tunnel, galaxy, fireflies, Mandelbrot zoom. 5 → 13
  patterns. Kaleidoscope and reaction–diffusion stay shelved.
- **The image slideshow is unparked** into R2 as R2c: `cycle_content`
  (patterns/images/mixed) plus `images_dir`, folder rescanned each lap,
  dissolve reveal on entry, empty folder degrading to patterns-only.
- **Build order: R2a → R2b → R2c → R2d** — five pure patterns first (no
  architecture risk, rotation doubles in one session), then the stateful pair
  with the contract change, then the slideshow, then the zoom. Each a
  self-contained session, committed and windowed-watchable the same evening.
- **Mixed rotation becomes the default.** A deliberate exception to R1's
  behaviour-identical principle — recorded as chosen, not drifted into.
- **Fire gets colour on day one:** R2b carries a minimal per-pattern two-stop
  gradient override (ember fire, phosphor Life); R3 themes absorbs it later.
- **Rain ships brightness-only.** The glyph-override channel goes to Parked as
  a conscious deferral — it's the one idea that widens the core
  brightness-field abstraction, and the old R2 engine note asked for exactly
  this decision to be made deliberately.
- **Braille sims run at full sub-resolution** (Life at 8× the cells = richer
  soup) — a look, not a bug, pending field evidence.
- Stateful contract as proposed on 2026-08-01: `PATTERNS` entries may be
  callable objects with `reset()`; substep by `dt` with a cap so the 2 fps
  throttle slows sims instead of breaking them.

**Also**

- Standing note refreshed: git lock parking now goes to `.git/stale-locks/`
  (in-mount rename; never park outside the mount — that move needs the
  forbidden `unlink` and its failure hides easily). Replaces the `_to_delete/`
  advice.
- Rebuild economics made explicit in TODO: new *code* needs one `.scr` rebuild
  at the end of R2; settings never do. Folds into the still-open field run,
  which gains the new patterns and mixed rotation as checklist items.

State at close: docs-only commit, tree otherwise untouched, nothing lives only
in the sandbox. Next session starts at R2a.
