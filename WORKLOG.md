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

## 2026-08-10 — Electric ! found and identified (docs only)

Matthew asked how dotfield's data is calculated (answer: no particles — six
interfering waves, two of them ripples from invisible orbiting sources, then
density-crush and the dot ramp), which surfaced a memory of an old particle
screensaver. He named the file — `electric.scr` — then produced the real thing
from storage into `electric/`: *Electric !* v1.3.1, JX Bardant, French
freeware, 1997, GeoCities home page, readmes in seven languages.

Static analysis (readme + `strings` on the PE) settled how it worked, and
Matthew's recall that "it uses the windows palette heavily" was the exact
mechanism, not just a detail:

- Settings dialog text: "Patterns represent the electric field of particles
  laid on the screen. Choose here their type and number." Particle types are
  all French *-ons*: Electrons, Melons, Dindons, Cochons, Jambons, Cornichons,
  Oignons. "All of them !" is an option.
- Imports `CreatePalette` / `RealizePalette` / `AnimatePalette`: the field is
  computed once per pixel into a 256-colour indexed image ("computing
  intensive" on a 486, per the readme), then animated by rotating the hardware
  palette — motion with zero recomputation, plus a "new image after N seconds"
  re-seed. Hence the readme's warning that True Color shows only static
  images: no palette, no animation. It's a 32-bit PE, so it would still *run*
  on modern Windows — but only as a still life. An ASCII homage is the
  realistic way to see it move again.

Actions: `electric/` added to `.gitignore` (the `*.scr` rule already covered
the binary; this keeps the readmes out of status too), and the homage pattern
parked in TODO with a sketch — pure-contract, the glyph ramp playing the role
of the rotating palette. Promotion into the build queue is Matthew's call.
Also noticed in passing: a fresh `ASCIIVisualizer.scr` built 2026-08-10 — the
R1 rebuild has happened; field-run results still to be jotted here.

**Addendum, same evening:** Matthew said yes — `electric` is promoted into
R2a, which becomes "six for free" (R2 now lands 5 → 14 patterns). TODO
updated; the parked entry is now a stub pointing here. Still planning-only:
R2a's build starts when Matthew says go.

## 2026-08-11 — R2a shipped: six for free (5 → 11 patterns)

Matthew said go over morning coffee, so R2a got built: rain, lava, tunnel,
galaxy, fireflies and electric, all pure functions of `(X, Y, t, gf)` appended
to `patterns.py` — which was the *only* app file that changed. Everything else
(G key, HUD, `--pattern`, `--list-patterns`, `cycle_patterns` validation, the
screensaver rotation) picked the new names up automatically from `PATTERNS`,
exactly as R1 promised. A new `_hash01` helper packages starfield's integer-
hash trick so stateless patterns can give columns/blobs/charges persistent
personalities without storing anything.

**Tuning story** (every pattern eyeballed via headless contact sheets at
1920×1080, dots palette, three timestamps; then re-tuned against numbers):

- The density crush (values below `1 - density` go black) is the recurring
  antagonist for sparse patterns. Rain's tails and fireflies' glows died at
  first render; both now pre-lift their brightness so the fade bottoms out at
  the crush threshold instead of vanishing halfway. Constants are tuned for
  the default `density 0.6` and still thin correctly at other settings.
- Rain: heads carry a hot glint, two hash layers give columns multiple drops,
  and a coarse time-quantised per-cell hash adds glyph-shimmer. Reads as a
  proper downpour now.
- Lava went from solid white slabs to a *rim-lit shell* look — `4m(1-m)`
  peaks brightness at the blob boundary, interiors glow dimmer — which reads
  beautifully in dots and braille both.
- Tunnel was rebuilt twice: spokes+rings read as moiré petals, and the first
  ring version could never reach a bright glyph — the fog ceiling capped raw
  values at 0.83, which the shaping gamma turned into 0.65 max (found by
  printing shaped-field stats, not by squinting). Final: tanh-sharpened rings,
  slight angular wobble, fog floor raised so near rings hit full glow while
  the throat stays dim. 20% of cells land in the bright glyphs now.
- Galaxy: log-spiral arms (`theta*3 - log(r)*4.6`), envelope and gain raised
  until the pinwheel fills the frame with dusty arm tails.
- Electric came out right on the first render — bands 2.6 per potential unit,
  flow 0.55/s, `tanh(|V|)` far-field damping — and looks eerily like the
  original's nested contour blobs, shimmering cores included.

**Performance** (measured, field compute per frame at 192×56 / braille ×8):
fireflies started at 83 ms in braille — forty full-grid gaussians — and is
2.6 ms after windowing each fly to its own ±8 cell-width patch of the grid.
Rain halved to 4.9 ms by hashing one row and broadcasting against Y. Heaviest
pattern is now lava at ~8 ms braille *on the sandbox CPU*; all are 60 fps
territory on real hardware, but the fps counter on the HUD will say for sure.

**Verification:** new `tests/test_patterns.py` (10 tests: shape/range/finite
at cell, braille and 1×1 grids; determinism in `t`; density thinning; config
accepting the six names and still rejecting nonsense — "melons", in memoriam).
Full suite 56/56. Run-loop smoke for each new pattern through real `main.py`
headlessly, plus braille and screensaver auto-cycle paths. Braille contact
sheet eyeballed — tunnel and electric are spectacular there.

**Not tested here** (sandbox has no screen — Matthew's half): how they feel in
motion, colour-on appearance (still the global blue gradient until R2b's warm
hook), and real fps on his hardware. Run sheet updated in TODO's field-run
section. No `.scr` rebuild yet — that still waits for the end of R2.

## 2026-10-15 — One build script for the app and the screensaver

*(Written up 2026-10-26 from the diff and that session's transcript: the
session stopped partway through its smoke test, before any commit or worklog
entry. Finished in the entry below.)*

The ask: build the visualizer as a standalone app, not just as the screensaver.

- **`build.ps1` + `build.bat` replace `build_screensaver.ps1` / `.bat`.**
  Targets `all` (default), `app`, `screensaver`; `-Python` builds from a venv.
  It checks pygame/numpy/Pillow first, installs PyInstaller if it's missing,
  gives each target its own `dist\` and `build\` subfolders, and copies the
  result into the project folder. `ASCIIVisualizer.exe` comes from `main.py`
  and includes OpenCV if it's installed (73 MB). `ASCIIVisualizer.scr` comes
  from `screensaver.py` and always leaves OpenCV out (38 MB, faster to unpack
  on every launch). `build.bat` is the double-click wrapper and pauses at the
  end.
- **Found and fixed: the built versions lost every screenshot.** `app.py`
  located `images/` and `captures/` from `__file__`, which in a one-file build
  points into PyInstaller's temporary unpack folder, deleted on exit. So S-key
  captures from the `.scr` vanished, and photos dropped beside it were never
  seen. New `config.data_dir()`: the project folder from source, as before;
  beside the `.exe` / `.scr` when frozen; `%APPDATA%\ASCIIVisualizer` when that
  folder can't be written to (a `.scr` copied into `System32`). A failed
  capture is now a toast, not an exception, and a missing images folder means
  no images, never a failed start.
- **`main.py` gives the windowed exe a console when there is one.** A
  `--windowed` build has none, so `--help`, `--list-patterns`, `--write-config`
  and option errors printed to nowhere. Run from a terminal, it now borrows that
  terminal's console (it didn't work in the real build yet; see 2026-10-26).
  The pygame banner is hidden in the exe.
- `tests/test_frozen.py`: 6 tests, faking the frozen state by patching
  `sys.frozen` / `sys.executable`. 62 in total. README's build section
  rewritten, TODO run sheet step 0 points at `build.bat`, `.gitignore` gains
  `*.exe`.
- Both built that night (`.scr` 23:30, `.exe` 23:32), with R1 and R2a in them.

## 2026-10-26 — Smoke-testing both builds; the console hookup fixed

Both binaries were newer than every source file they're built from, so they
were tested as built. All runs happened on copies in a scratch folder, with
`SDL_VIDEODRIVER=dummy`, so nothing opened on screen except one Notepad.

**`.exe`.** A headless run of the copy, started from `%TEMP%` on
`--pattern electric`, stayed up for 10 s and created `images/sample_rings.png`
beside the copy. So `data_dir()` holds in the real build, not just under the
patched tests. `--write-config PATH` wrote a correct file.

**But nothing printed in a terminal**, not `--list-patterns`, `--help` or a bad
option. Cause: a one-file PyInstaller build on Windows is two processes. The
launcher unpacks Python and starts a second copy of itself, which runs the
program; the process tree read pwsh → launcher → Python. So
`AttachConsole(ATTACH_PARENT_PROCESS)` asked the launcher, which has no
console, and the failure was swallowed. The 2026-10-15 tests couldn't catch
it: only the real build is two processes. **Fix:** if the parent has no
console, attach to the grandparent's, found with a Toolhelp process snapshot
(`main._parent_pid`). It loads its own `WinDLL("kernel32")` handle, so its
`argtypes` don't leak into `ctypes.windll.kernel32` for pygame. A new test
checks it against `os.getppid()`; 63 tests in total. Rebuilt the `.exe` (22 s).
`--list-patterns` (all 11), the bad-option error and `--help` now print, en and
em dashes intact. Typed straight at a PowerShell prompt, the output lands after
the next prompt, because PowerShell doesn't wait for a windowed program.
That's expected, and it's in the README now.

**`.scr`** (not rebuilt: `main.py` isn't part of it). `/p 12345` exits 0 in
about a second. `/s` is still running headless at 10 s (and a stray one ran
over two minutes without trouble). `/c`, with `ASCIIVIZ_CONFIG` pointed at the
scratch folder, created the starter config and opened Notepad on it. `images/`
appeared beside the copy.

**Testing trap, for next time:** `Start-Process` on a `.scr` goes through the
file association, `"%1" /S`, which throws the arguments away. A "/p" test
silently ran the saver, and `-Wait` sat on it for good. Launch through
`ProcessStartInfo` with `UseShellExecute = $false`.

Also: `screensaver.py`'s docstring still named `build_screensaver.ps1`. Fixed;
it's a comment, so no rebuild. TODO housekeeping: the `.scr` rebuild is done
(R1 and R2a are in it). The `Claude.md` line-ending item has resolved itself:
`core.autocrlf` is `true` now and git sees the file as clean.

**Still Matthew's (needs a real screen):** in a real window, `S` in the built
`.exe` should save into `captures/` beside it. The Settings button from
Windows' own screensaver dialog (`/c` worked when launched directly). The rest
of the field run. R2b–R2d are new code, so they'll need one more rebuild when
R2 is done; settings never will.

## 2026-10-26 — R2b shipped: fire and Life, the stateful pair (11 → 13 patterns)

Built in a side session started from the build-script session, to the R2b
spec in TODO and the 2026-08-05 decisions. Fire and Life are the first patterns
with memory, so this is the one R2 session that changed the contract.

**The contract change** (`patterns.py`, `generative.py`, about 30 lines of
plumbing):

- `patterns.Simulation` is the base both sims share. A sim advances in fixed
  ticks of `1/rate` s, and how many are due is worked out from `t` alone, so
  pause (which freezes `t`) freezes it with no code of its own. At most
  `MAX_STEPS = 6` ticks a frame; when it's further behind (the 2 fps throttle,
  or coming back from image mode) it runs the last six, stamped across the
  last six tick intervals, and re-anchors at `t`. The dropped ticks are never
  owed, so it can't snowball. State is keyed by the field's shape, which is
  what catches a palette switch (braille changes the sub-resolution without
  any resize). The RNG is reseeded on every fresh start, so the same
  timestamps always give the same frames, which is what made it testable.
- `GenerativeField` calls `reset()` on every sim in `set_dims` (resize, font
  size), and on a sim when it is switched *to*. Re-selecting the pattern
  you're already on doesn't reset it, so a one-pattern `cycle_patterns` doesn't
  restart Life every 20 s.
- **Beyond the spec, one line:** each `GenerativeField` takes a `copy.copy` of
  the sim prototypes in `PATTERNS`, so two fields never share one sim. The app
  only ever has one field, but the tests make dozens, and a module-level
  singleton with state is a trap waiting for the next person.
- The eleven existing patterns are untouched; a test pins that they're still
  plain functions with no `reset`.

**Fire** (`Fire`): the Doom algorithm, vectorised as a gather. Each tick a
cell takes the heat of a random neighbour in the row below (offsets −1…+2:
Doom's leftward wind), minus `cool` on half the ticks. Two scalings keep it
looking the same in every palette: cooling is `2 / (REACH·h)`, so flames
reach the same share of the screen at any size, and the tick rate is
`30 Hz × (h / rows)`, so braille (4 sub-rows a cell) ticks at 120 Hz and the
flames rise at the same on-screen speed.

**Life** (`Life`): B3/S23 on a torus, neighbour count from four `np.roll`s,
10 generations/s, at full braille sub-resolution as decided. Trails fade on
`t`, not on generations: each cell remembers when it was last alive and glows
`0.85·exp(−age/1.4 s)`, so the fade is smooth at 60 fps although the board
changes ten times a second. **Beyond the spec:** every 40 generations a patch
of fresh soup lands somewhere. Left alone, Life settles into still lifes and
blinkers, and a Life-only rotation would sit on a static board for good.

**Colour:** `app._GEN_GRADIENTS` maps `fire` → ember (120,22,4)→(255,200,90)
and `life` → phosphor (14,72,30)→(150,255,160); everything else keeps
`_GEN_LOW`→`_GEN_HIGH`. Colour is still the `C` toggle (off by default), and
it applies to dots and ramp only: braille generative has always drawn in one
colour, for every pattern. Left alone as out of scope; R3's themes are the
natural place for it.

**Tuning story** (headless contact sheets at 1920×1080 with colour on, all
three palettes, at 1.5 / 6 / 20 s, driven at 60 fps and at 2 fps):

- Fire's first render was a flat band: bright only in the bottom rows, with a
  haze of faint dots above. The density crush hides heat below 0.4, and
  that's exactly where all of the raggedness is. Fix: the R2a pre-lift
  (`0.42 + 0.58·heat` wherever heat is non-zero), so the tips fade to the
  threshold instead of hiding.
- Then it stood as an even wall of fire: Doom's coals are uniformly
  white-hot. **A deliberate departure from Doom:** the bottom row is now two
  slow sine waves beating against each other (0.65–1.15, clipped later), so
  the flames surge and slump in places. That one change gave real leaning
  tongues, clearest in braille.
- Then it was dim and short; hotter coals and `REACH` 0.62 → 0.70 settled it.
  In dots at full resolution: hot yellow clumps at the base, embers reddening
  as they rise. Lovely.
- Life looked right on the first render: phosphor-green cells, recognisable
  blocks, beehives and blinkers, soft `:` `.` afterglow behind anything that
  moved. Braille is the promised richer soup.

**Timings** (field compute per frame at 60 fps, 192×56 cells / 384×224
braille, this laptop): fire 0.14 ms / 3.3 ms (2 ticks a frame in braille),
Life 0.18 ms / 1.8 ms. (R2a's figures, lava ~8 ms braille, were taken on the
old sandbox's CPU, so they don't compare directly.)

**At the 2 fps throttle:** fire wants 15 ticks a frame and gets 6, so it runs
at 40% speed (braille 10%, where igniting takes most of a 20 s slot). Slower,
not broken, as the spec says. Life wants 5 a frame, under the cap, so it keeps
full speed and simply shows every fifth generation. The 2 fps sheets match the
60 fps ones once fire is lit.

**Verification:** `tests/test_stateful.py` (19 tests): reset on resize, on
palette switch (by shape) and on switching to a sim; the substep cap, and
that dropped ticks aren't owed; braille ticking 4× faster; pause freezing the
sim, at the field level and through the real `run()` loop with a posted Space
key next to an unpaused control run; the throttle at faked timestamps (fire at
6 ticks a frame and still burning, Life at full speed, and a 60 → 2 fps
switch driven by the app's own `_ss_fps`); Life's full rule table for every
neighbour count, wrap-around, a glider, and an emptied board coming back; the
colour override, read off the colour grid handed to the renderer; and real
`main()` runs on both sims in all three palettes inside `sandbox()`.
`tests/test_patterns.py` gained five contract checks (13 names, only the pair
stateful, per-field copies, the sims drawing from their first frame on,
repeatability) and now runs the density check over the pair too. **87 pass**
(63 before), standalone and under pytest. Then a mutation check: 15
hand-written mutants of the new code (no cap, owed ticks, ignoring `t`, no
shape key, no resets, shared sims, HighLife's B36, no splashes, trails by
generation, no gradient...). Two lived at first, B36 and no-splash, and those
tests were sharpened (the rule table; an emptied board must revive within 40
generations). After that all 15 were caught. Plus headless `main.py` runs:
`--pattern fire --color`, `--pattern life --palette braille`, and screensaver
rotation through fire → life → plasma.

**Found in passing, not fixed (out of scope):** on this laptop braille draws
empty boxes, and the "install DejaVu" toast never fires.
`DejaVuSansMono.ttf` is installed but has no braille glyphs, and
`_has_braille`'s `metrics()` check passes the missing-glyph box. My braille
sheets borrowed DejaVu Sans, which has them. Logged in TODO under "Found in
passing", with a likely fix. R2a's braille sheets were made in the old
sandbox, with whatever fonts it had, so they never showed what this laptop
shows.

**Not tested here:** anything on a real screen. That covers how fire and Life
feel in motion, real fps, a real screensaver run reaching the throttle (only
faked timestamps and headless 2 fps driving), and mono (the sheets were
colour-on; mono draws the same glyphs in one colour). No `.exe`/`.scr`
rebuild: that waits for the end of R2, so the builds don't have fire or Life
yet. TODO's run sheet says so and gains the fire/Life checks. Nothing pushed.

## 2026-10-26 — Braille font check fixed: decided by drawing

A side session, picking up the TODO item R2b logged: on this laptop braille
drew empty boxes, and the "no braille-capable font" toast never fired.

**Cause, confirmed by probe.** `_has_braille` asked `font.metrics("⣿")`, and
SDL_ttf answers that for the missing-glyph box too. This laptop's
`DejaVuSansMono.ttf` has no braille: ⣿, ⠁, the blank U+2800 and a private-use
U+E000 all draw the same box with the same ink. So the mono font passed, and
the search never reached a font that has the glyphs. Consolas, Courier New
(what `match_font("freemono")` answers here) and pygame's own bundled font
draw boxes too. DejaVu Sans and Segoe UI Symbol draw real dots. The README
promised a toast when no font has braille, but on Windows the old check would
have passed Consolas the same way, so that toast could never have fired there.

**Fix** (`renderer._has_braille`, a few lines): render ⣿ and ⠁ and require the
full cell to carry more ink than the single dot. A box draws both the same, a
blank draws neither. Ink is the sum of `surfarray.array_alpha`: a render with
no background is an SRCALPHA surface whose RGB is the text colour everywhere,
so RGB can't tell glyphs apart. Now the mono font fails, the search falls
through to DejaVu Sans (the next candidate), and the toast fires only when no
candidate draws braille. A Windows machine without DejaVu should land on
Segoe UI Symbol, so on Windows the toast should be rare.

**Tests** (`tests/test_renderer.py`, 4). pygame's bundled font ships with every
pygame and has no braille, so it is the missing-glyph case on any machine. It
must fail at sizes 6, 16 and 32, and so must stand-in fonts that draw one box
for everything or nothing at all. A stand-in that draws one dot per raised bit
must pass, and so must DejaVu Sans and Segoe UI Symbol wherever they're
installed. Those are matched by file name, because `match_font` answers a
missing family with another of its alias group (no DejaVu Sans gives Arial).
At the `Renderer` level: when every font draws boxes, `braille_ok` is False,
which is what fires the toast. When the mono font and the first candidate draw
boxes, the search falls through to a real one. The stand-in renders the way
pygame does (text colour everywhere, glyph in alpha), so an RGB-based check
fails the suite even on a machine with no braille font. Mutation check, six
mutants of the check: the old metrics one, ink from RGB, `>=` for `>`, always
True, always False, and ⣿ against the blank U+2800 instead of ⠁. All caught
but the last, which is an equally valid render check, not a test gap. **91
pass** (87 before), under pytest and standalone.

**Alignment**, checked headless (`SDL_VIDEODRIVER=dummy`, 1280×720 braille at
the default size 16). Tunnel, electric and Life now draw real dots, where the
old choice drew a box per cell. DejaVu Sans isn't monospaced: its braille
advance is 12 px against the mono cell's 10. But the renderer places braille
at fixed cell origins, so nothing drifts, and Life's blocks, beehives and
blinkers sit on an even grid. Measured over sizes 12–40, the ⣿ ink stays
inside the cell both ways, and the dot columns land within about 2 px of the
cell's quarter points, leaning right a little more at larger sizes.
Vertically, at size 16, the rows sit 4, 5 and 4 px apart, with 6 px across a
cell boundary. That spacing comes from the font's own glyph, not from the
fallback. Segoe UI Symbol, measured the same way, sits lower in the cell
(4 px at size 16) and draws bigger, rounder dots. Its bottom row reaches a few
pixels past the cell but never touches the next row's dots, and its frames
look right. At size 8 and below, the dots run together in both fonts: that's
the resolution floor, not a font problem.

**Left alone:** the toast still says "install DejaVu Sans Mono" (`app.py`,
out of this session's scope). That's still sound advice, since a full copy
has braille; it's this laptop's copy that doesn't. README's braille note now
describes the check. No `.exe`/`.scr` rebuild: the builds keep the old check,
and draw boxes here, until the end-of-R2 rebuild. TODO's run sheet says so.
Nothing pushed.

## 2026-10-26 — R2c shipped: the slideshow joins the screensaver's rotation

A side session, run alongside R2d (the zoom, in its own worktree), to the R2c
spec in TODO and the 2026-08-05 decisions. Nothing in `patterns.py`, which is
R2d's.

**What it does.** Two new settings, each also a flag:

- `cycle_content`: `"patterns"`, `"images"` or `"mixed"`, default `"mixed"`.
  It decides what the screensaver rotates, each item held for
  `cycle_seconds`. Mixed goes pattern → image → next pattern → next image.
  Images enter with the existing dissolve. Making mixed the default is
  Matthew's deliberate change from 2026-08-05.
- `images_dir`: any folder, read-only. Unset, it's the app's own `images/`
  exactly as before, including `config.data_dir()`'s frozen fallback and the
  sample image. A named folder is never created and never gets the sample.
  `~` and `%VAR%` are expanded, since a `.scr` runs from an unknown current
  folder and a full path is the only safe kind.

**How** (`app.py`, about 120 lines). The run loop's inline cycle check became
`App._ss_cycle()`, which is also what the tests drive at faked timestamps. It
picks an image (`_ss_next_image`) when mixed is on a pattern, or always in
"images". When there's none to show, the slot goes to the next pattern
(`_ss_next_pattern`), so "images" and "mixed" both fall back to patterns. The
slideshow keeps its own place in `self.images` (`_ss_image_pos`) and rescans
the folder when a lap ends, or every slot while the list is empty. So a file
dropped in mid-lap joins the next lap, and a folder that starts empty starts
showing pictures one slot after the first one lands. `--image` stays at the
front of the list across rescans, as it is at startup. The manual keys don't
touch any of this: `Tab`, `N`/`P`, `G` and `--image` are unchanged, and
nothing rotates outside `--screensaver`.

**The sims.** Mixed returning from an image to a *different* sim already went
through `GenerativeField`'s switch-to reset. A one-pattern rotation (say
`cycle_patterns: ["life"]`) came back to the same index, which by R2b's rule
doesn't reset. So `GenerativeField.restart()` (three lines) is called when the
rotation comes back from an image to the same pattern. A sim then always
starts afresh after an image, and "patterns" with one sim still leaves it
running, as R2b decided. Both are tested.

**Beyond the spec, all in service of "never a black screen":**

- **An image that won't load is skipped, not fatal.** Before this, a corrupt
  file in `images/` raised out of `load_image_fields` and took the app down on
  `N`. With rescans picking up files mid-copy, that would have killed the
  screensaver. `_ensure_image_loaded` now catches the failure, remembers it
  (so a broken picture isn't re-decoded every frame), and draws the pattern.
  The rotation tries the next file in the lap, and clears the memo a lap later
  so a finished copy gets its turn. Strictly this changes manual behaviour,
  but only from a crash to a toast.
- `_scan_images` treats an `OSError` (a share or USB drive gone away) as an
  empty folder.
- A lone image in an "images" slideshow is held rather than re-dissolved every
  slot. It would otherwise blink to black and back each cycle, and R2b set the
  same rule for a lone sim.
- A named `images_dir` that doesn't exist gets a toast in the windowed app,
  not a config problem. The validator stays pure, and the folder may be a
  drive that isn't plugged in yet.

**Verification.** `tests/test_slideshow.py` (22 tests): the default; nothing
moving before `cycle_seconds` are up; each of the three rotations in
sequence; the dissolve starting on every image entry; the lone image held;
rescans at lap ends (a file sorting first but added mid-lap waits for the
next lap, and a deleted one leaves); empty and missing folders falling back
and picking up pictures as they arrive; the missing folder not created; the
named folder never given the sample; broken files skipped in "images" and
"mixed", retried after a "copy" finishes, and loaded once (not per frame) when
reached by `N`; sims afresh after an image, and a lone sim left running under
"patterns"; the windowed app never rotating; the manual keys; `--image`
across rescans; "patterns" keeping a starting image; and real `main()` runs
in all three modes, in dots and in braille with colour. `test_config.py` +6
(both validators, precedence, argparse refusing a bad choice, the starter
file's help) and `test_frozen.py` +1 (frozen: unset means beside the
exe with the sample, named means read-only there, and captures beside the exe
either way). **120 pass** (91 before), under pytest and file by file. Then 18
hand-written mutants: no rescan, no alternation, no restart, sample into the
named folder, named folder created, per-frame retries, the failure memo never
cleared, no skip, "patterns" leaving an image, re-dissolving a lone image, no
exception catch, the slideshow opening on a pattern, `--image` lost on
rescan, the windowed app rotating, default `"patterns"`, no dissolve, no
`images_dir` validation, no missing-folder toast. All 18 caught, each by the
test meant for it. (One first "caught" was my own mutant's syntax error;
redone properly, it's caught by the mid-copy test.)

**Headless smoke** (`SDL_VIDEODRIVER=dummy`, `python main.py --screensaver
--full-minutes 0.1 --throttle-minutes 0.05 --cycle-seconds 1 --images-dir
<folder>`, one run per mode): all three exit 0 after 9.4 s, as the phases
add up. A wrapper logging each change in the real loop showed fire → life →
plasma for "patterns"; one → two → one ("broken.png" skipped silently) for
"images"; and fire → one → life → two → plasma → one for "mixed". Run first
by accident with only `broken.png` in the folder, all three still ran their
9.4 s on patterns.

**Measured, not fixed (logged in TODO "Found in passing"):**

- Photo loads on this laptop: 40 ms for 1920×1080, 210 ms for 12 MP,
  400 ms for 24 MP (braille and colour cost about the same). That stalls the
  animation as each photo arrives and starts the dissolve part-way in. In the
  logged run a 12 MP photo took 189 ms. JPEG `draft()` decoding is the likely
  fix if the field run minds. It's in `engine.py`, not the surface cache.
- EXIF orientation is ignored: a test JPEG tagged "rotate 90°" loaded
  unrotated, so upright phone photos will show sideways.

**Worth Matthew's eye:** with no `images_dir`, the app's own `images/` always
holds the generated sample, so out of the box mixed shows the same rings
picture in every other slot. That is the spec as written (the "empty folder →
patterns" fallback never applies to the app's own folder), but it may not be
what "a fresh install alternates patterns and images" pictured. It's on the
run sheet (TODO step 3b) with the options.

**Not tested here:** anything on a real screen, a real folder of photos, and
the throttle with a photo up for a long time. No `.exe`/`.scr` rebuild: that
waits for the end of R2. Until then the builds treat both new keys as unknown
settings and ignore them. Nothing pushed.
