# TODO / Roadmap

The app is feature-complete for its original brief: generative idle patterns,
image-to-ASCII, video/webcam, three palettes, HUD, and a working Windows `.scr`
with wind-down. What follows is where it could go next, in the order that makes
the most sense to build.

Planned 2026-08-01. **R1 shipped 2026-08-01.** **R2 scoped in detail
2026-08-05** with Matthew (all candidates chosen, slideshow unparked into it,
build order agreed). **R2a shipped 2026-08-11** — 11 patterns now.
**Build script 2026-10-15**: `build.bat` makes a standalone `ASCIIVisualizer.exe`
as well as the `.scr`; both smoke-tested 2026-10-26. **R2b shipped
2026-10-26** — fire and Life, the first stateful patterns; 13 patterns now
(not in the builds yet: that rebuild waits for the end of R2). **Braille font
check fixed 2026-10-26** (it was passing a font whose braille is a box; also
waits for that rebuild). **R2d shipped 2026-10-26** — the Mandelbrot zoom, 14
patterns now (also waits for that rebuild). R2c and R3–R4 not started.

---

## Field run — Matthew (open)

A run sheet for the next sit-down. Roughly in order, but each step stands alone
— skip anything you don't fancy. Most of this has *never* run on real hardware:
the sandbox has no camera, no Windows, and no screen, so everything below was
verified logically rather than by looking at it.

### 0. Build the app and the .scr once

```
build.bat
```

Double-click it: it builds both `ASCIIVisualizer.exe` (the app) and
`ASCIIVisualizer.scr` (2026-10-15; `build.bat app` or `build.bat screensaver`
builds just one). Right-click the new `.scr` → **Install**. This is the last
rebuild you should need for a settings change. *Both are already built (the
`.exe` on 2026-10-26, the `.scr` on 2026-10-15), so you can go straight to
Install — but they predate R2b, so fire, Life and the Mandelbrot zoom are only
in `python main.py` until the one rebuild at the end of R2.* Every other step below works with
`ASCIIVisualizer.exe` in place of `python main.py`, and it's worth trying both
at least once.

### 1. The app, windowed

```
python main.py
```

- `G` cycles patterns — now all 14: the original five plus rain, lava, tunnel,
  galaxy, fireflies, electric (R2a, 2026-08-11), then fire and Life (R2b,
  2026-10-26), then the Mandelbrot zoom (R2d, 2026-10-26). Worth a slow lap in
  each palette: electric's flowing bands and the tunnel are the showpieces,
  braille makes both spectacular, and fireflies is deliberately the calm one.
  This is windowed `python main.py` — no rebuild needed to see any of it.
- **The Mandelbrot zoom** (R2d): `python main.py --pattern mandelbrot`. Each
  dive takes 80 s, from the whole set down a trillion-fold into the boundary,
  then fades to black and starts on the next of five targets (Seahorse Valley,
  the triple-spiral valley, Elephant Valley, the point i, the antenna). Ramp
  (`2`) is the classic text-mode look. Worth one whole dive and a reset.
  Questions: is 80 s a dive the right pace, does it shimmer too much near the
  set in motion, and what does the HUD's fps say full-screen in braille? Its
  pattern costs less there than electric or Life, but nothing here measured a
  real screen. `--fps 2` shows the throttle: a 20% zoom step each frame.
- **Fire and Life at 60 fps and at the 2 fps throttle** (R2b). They're the
  first patterns with memory, so the questions are new: press `C` for colour
  (fire is ember-orange, Life phosphor-green). `Space` should freeze both dead
  still, trails and all. Resizing the window or switching palette restarts
  them, which is deliberate. Then watch them at the throttle's frame rate:
  `python main.py --pattern fire --fps 2` (and `life`). Fire should look
  slower and still burn; Life keeps its full speed and just jumps five
  generations a frame. For the real thing, `python main.py --screensaver
  --full-minutes 0 --cycle-patterns fire,life` starts already throttled (any
  key exits). Braille fire at 2 fps takes most of a 20 s slot to climb the
  screen. That's expected; say if it bothers you.
- `1` `2` `3` switch palettes. **Braille (`3`) is the one to watch**: it needs
  a font that really draws the braille block, and since 2026-10-26 the app
  checks by drawing. This laptop's DejaVu Sans Mono has no braille in it, so
  braille now comes from DejaVu Sans (elsewhere on Windows, Segoe UI Symbol):
  expect real dots, not empty boxes, and a toast only if no font has them.
  Worth a look at a few font sizes (`[`/`]`) to see the dots read evenly.
  *The built `.exe` and `.scr` predate that fix, so they still draw boxes
  here until the end-of-R2 rebuild.*
- `C` colour, `+`/`-` density, `[`/`]` resolution, `Tab` image mode, `N`/`P`
  through `images/`, `S` saves a PNG to `captures/`.
- HUD should fade after 15 s of no input and relight the instant you touch
  anything.
- In `ASCIIVisualizer.exe`, `S` should save into `captures/` here, beside the
  exe. Builds before 2026-10-15 saved into a temp folder that was deleted on
  exit, so this is the fix to look for. The only part the smoke test couldn't
  reach is the key press in a real window.

### 2. Webcam — still never tested

Press `V` (or `python main.py --webcam --palette braille --color`). Needs
`pip install opencv-python`. Without it you should get a polite toast, not a
crash. Pressing `V` again, or switching modes, must release the camera — check
the webcam light actually goes out.

### 3. The config file — brand new, untested off-sandbox

```
python main.py --write-config
```

Writes `%APPDATA%\ASCIIVisualizer\config.json`. Edit it, rerun, and the HUD's
bottom line should show that path. Worth trying deliberately:

- A nonsense value (`"idle_fps": -5`) → a toast naming the problem, app still
  starts on the default.
- Broken JSON (delete a brace) → app still starts. **This is the one that
  matters** — a screensaver that won't start gives you no error at all, just
  nothing, so it must never die on a bad file.
- `"cycle_patterns": ["plasma", "ripples"]` → the screensaver rotates only
  those two, while `G` still reaches all eleven.

Note: `%APPDATA%` is the right home for this file. "Beside the program" also
works, but for an installed `.scr` that means `System32`, which needs admin.

### 4. The Settings button

In Windows' screensaver picker, select ASCII Visualizer and click **Settings**.
It should open `config.json` in Notepad — creating it first if you skipped step
3. Save, then preview. (The little preview monitor in that dialog stays blank;
that's expected and not worth chasing.)

### 5. The overnight question, finally answerable

Still open from June: after the saver self-exits (~10 min), does Windows just
relaunch it while you're still idle? Watch once and see. If it does loop
annoyingly, the fix no longer needs a rebuild:

```json
{ "throttle_minutes": -1 }
```

That keeps it in the quiet 2 fps phase indefinitely instead of bowing out. Also
still unanswered: does the fan actually go quiet when it drops to `idle_fps`
after the first 5 minutes?

### Found something odd?

Jot it in `WORKLOG.md` under a dated heading — that's what the next session
reads first. Rough notes are fine; no need to diagnose it.

## Housekeeping — Matthew

- [x] Git litter (`_to_delete/`, the orphaned `tmp_obj_*` objects) deleted
      2026-08-01, and the roadmap commit pushed.
- [x] **Rebuild the `.scr` once more** to pick up R1. Done 2026-10-15 with
      `build.bat` (which replaced `build_screensaver.bat` and builds the app
      `.exe` too); the build has R1 and R2a in it. Right-click → **Install** is
      still yours to do. No more rebuilds for settings; new code (R2b–R2d)
      gets one at the end of R2.
- [x] `Claude.md` showed as modified (line endings only). Resolved by
      2026-10-26: `core.autocrlf` is `true` now and git sees it clean.

## Found in passing — for a session

- [x] **Braille shows empty boxes on this laptop, with no toast** (found
      2026-10-26 during R2b's headless checks). `C:\Windows\Fonts\DejaVuSansMono.ttf`
      is installed, but its copy has no braille glyphs: every braille codepoint
      draws the same missing-glyph box (identical ink to a private-use
      character). `renderer._has_braille` asks `font.metrics()`, which answers
      for the missing-glyph box too, so the mono font passes and the "install
      DejaVu" toast never fires. DejaVu Sans (`DejaVuSans.ttf`, already in the
      candidate list) and Segoe UI Symbol both draw braille properly. Likely
      fix: test by rendering, e.g. require `⣿` and `⠁` to come out with
      different ink, so the search falls through to a font that has them. Small
      and self-contained; it touches every braille frame, so check alignment in
      a headless render afterwards. New code, so it rides the end-of-R2 rebuild.
      **Fixed 2026-10-26** as suggested: ⣿ must draw more ink than ⠁, read from
      alpha. Braille now comes from DejaVu Sans here, and headless renders
      show real dots on an even grid. `tests/test_renderer.py`; WORKLOG
      2026-10-26 has the measurements.

---

# Roadmap

Four items, ordered by dependency rather than excitement. R1 came first because
it makes R2–R4 testable in the field: a screensaver tweak used to mean a full
PyInstaller rebuild (36 MB, several minutes, then reinstall to System32), so
auditioning eight new patterns would have meant eight rebuild cycles. That's
fixed; the rest is the fun part.

---

## R1 — Runtime config ✅ shipped 2026-08-01

`asciiviz/config.py` reads a `config.json` at startup (searched: `--config` →
`ASCIIVIZ_CONFIG` → `%APPDATA%` → beside the program), validated key by key so a
bad file can never stop the saver appearing. Precedence is defaults → file →
command line, via `set_defaults` before `parse_args`. Windows' Settings button
now opens that file in Notepad instead of showing a stub dialog. Also landed:
`--pattern`, `--list-patterns`, `--cycle-patterns`, `--write-config`, `--no-*`
twins for the boolean flags, and `throttle_minutes: -1` meaning "stay quiet,
never exit". 46 tests in `tests/` cover it.

<details>
<summary>Original plan, kept for reference</summary>

### R1 — Runtime config (no rebuild to change settings)

**Why first.** The README literally says *"edit and rebuild to change them"*.
A `.scr` can't take CLI arguments from Windows, so `screensaver.py` hardcodes an
args list at build time. Every other item on this roadmap adds settings that
someone will want to change — this is the multiplier.

**Approach**

- **Search order**, first hit wins, absence is fine:
  1. `--config PATH`
  2. `ASCIIVIZ_CONFIG` environment variable
  3. `%APPDATA%\ASCIIVisualizer\config.json` (Windows) / `~/.config/asciiviz/config.json`
  4. `config.json` beside the executable — `Path(sys.executable).parent` when
     frozen by PyInstaller, project dir otherwise
- **Format: JSON.** Stdlib only, no new dependency, PyInstaller-safe. (TOML would
  read nicer by hand but `tomllib` is 3.11+, and the `__pycache__` shows this
  project has been run on 3.10.)
- **Keys mirror the argparse `dest` names exactly** — `palette`, `density`,
  `font_size`, `color`, `cycle_seconds`, `full_minutes`, `throttle_minutes`,
  `idle_fps`, `keep_display_awake` — so there's one vocabulary, not two.
- **Precedence: defaults < config file < CLI flags.** Implement with
  `parser.set_defaults(**config)` *before* `parse_args()`. Explicitly-passed
  flags then win for free, with no "was this supplied?" bookkeeping.
- **A broken config must never brick the screensaver.** It runs as a `.scr` with
  no console — a traceback on startup is invisible and baffling. Unknown keys →
  ignore with a warning; wrong types → fall back to the default; unparseable
  file → run on defaults entirely. Surface problems as a HUD toast in windowed
  mode and to stderr, never as an exception.
- `--write-config` dumps current effective settings as a starter file.
- **Upgrade the `/c` handler.** `screensaver.py` currently answers Windows'
  "Settings" button with a stub Tk messagebox. Make it open the config file in
  the default editor (creating it from defaults first if missing) — that's the
  behaviour a user expects from that button.
- Falls out cheaply while in there: `--pattern NAME` and `--list-patterns`.
  Right now a pattern can only be reached by cycling with `G`.

**Risk:** low. Nothing existing changes behaviour when no config file is present.

**Verify:** precedence (default/config/CLI three-way), each search-order slot via
a temp `APPDATA`/`HOME`, malformed and partial JSON, and a frozen-path simulation
with `sys.frozen` monkeypatched.

**Hand-off:** one final `.scr` rebuild after this lands — then no more rebuilds
for settings, ever.

</details>

---

## R2 — More generative patterns & the slideshow ⏳ scoped 2026-08-05

Planned with Matthew 2026-08-05; R2a, R2b and R2d built since. Verdict on the candidate
list: **all of them** — fire, rain, lava lamp, Life, tunnel, galaxy, fireflies,
Mandelbrot zoom, and (promoted 2026-08-10) the *Electric !* homage
(5 → 14 patterns) — plus the **image slideshow, unparked** from
the shelf and folded in here as R2c. Split into four self-contained sessions,
each ending committed, tested, and watchable the same evening with
`python main.py`. Kaleidoscope and reaction–diffusion were left on the shelf
(a modifier and a CPU hog respectively — neither fits this round).

**Decisions locked 2026-08-05** (Matthew's calls)

- **Build order: R2a → R2b → R2c → R2d.**
- **Mixed rotation becomes the out-of-the-box default** (`cycle_content:
  "mixed"`): a fresh install alternates patterns and images. A deliberate
  exception to R1's behaviour-identical principle — chosen, not drifted into;
  one config line restores patterns-only, and an empty images folder degrades
  to patterns-only on its own.
- **Fire doesn't wait for R3 to be orange.** R2b includes a minimal per-pattern
  two-stop gradient override (fire ember-orange; Life a phosphor-green
  candidate). R3 themes absorbs and generalises it later — don't gold-plate.
- **Rain ships brightness-only.** The per-cell glyph-override channel (katakana
  heads etc.) is the one candidate that widens the core brightness-field
  abstraction, so it moves to Parked as a conscious deferral, exactly as the
  old engine note asked.
- **Braille runs sims at full sub-resolution.** Life at 8× the cells is richer
  soup — treated as a look, not a bug. Revisit only if the field run says
  otherwise.
- **Slideshow transitions stay the existing dissolve reveal.** Crossfade/drift
  remains parked with Transitions & post-FX, so R2c never touches the
  image-surface cache strategy.

### R2a — six for free *(first)* ✅ shipped 2026-08-11

Tunnel, galaxy (rotating spiral arms), fireflies (Lissajous orbits), lava lamp
(metaballs), Matrix rain, and `electric` — the *Electric !* homage, promoted
from Parked 2026-08-10 on Matthew's say-so. All six fit the existing
pure-function contract untouched — `patterns.py` was the only app file that
changed. Tuning notes and the two performance rewrites (windowed fireflies,
column-vectorised rain) are in WORKLOG 2026-08-11; `tests/test_patterns.py`
now pins the contract (56 tests total). Rain statelessly: per-column integer hash →
speed / phase offset / tail length; head position `(offset + t·speed) mod
(span + tail)`; brightness is a distance-behind-head ramp; run two hash layers
so a column can carry more than one drop. Electric: potential field from
hash-placed, slowly wandering charges; brightness `frac(field·bands −
t·speed)`, so the glyph ramp plays the 1997 hardware palette and the contour
bands flow forever — `AnimatePalette` reborn — with a periodic charge re-seed
echoing the original's "new image after N seconds". Pause works for free
because nothing has memory. The shared density shaping doubles as tail-length
control on rain and band-width control on electric.

Verify: shape/range/NaN tests per pattern, headless renders at several `t`
eyeballed in all three palettes. `cycle_patterns` / `--pattern` validation
picks the new names up from `PATTERNS` automatically.

### R2b — the stateful pair ✅ shipped 2026-10-26

Built as planned below. `patterns.Simulation` is the base both share: fixed
ticks counted from `t`, at most 6 a frame with the excess dropped, not owed;
state keyed by shape; RNG reseeded on each fresh start. `GenerativeField`
resets sims on `set_dims` and when switching *to* one, and gives each field its
own copy. The eleven older patterns are untouched. Fire departs from Doom in
one way: drifting hot and cool coals instead of a uniform white-hot row, so the
flames surge in places rather than standing as a wall. Colour overrides live in
`app._GEN_GRADIENTS` (dots and ramp only: braille generative has always been
single-colour, which R3's themes can take up). Tuning and timings are in
WORKLOG 2026-10-26; tests are `tests/test_stateful.py` plus the contract
checks in `tests/test_patterns.py` (87 in total). Original plan:

Doom fire + Conway's Life with soft decay trails, plus the contract they need:

- A `PATTERNS` entry may be either a plain function (unchanged) or a callable
  object with an optional `reset()`, hooked into `GenerativeField.set_dims`
  and pattern switching. The eleven existing patterns need no edits.
- **Substep by `dt`, capped (~6 steps/frame):** at the 2 fps throttle the sim
  advances proportionally and just looks slower, never broken. No pattern
  blacklisting.
- State keyed by field shape; resize or palette switch = clean reset. Pause
  freezes the sim because steps derive from `t`, which pause freezes.
- The per-pattern gradient override lands here (see decisions above).

Verify: reset-on-resize, substep cap, pause-freezes-sim, throttle behaviour at
faked timestamps, plus the usual eyeballed renders. The session with the
architecture risk carries the tests.

### R2c — slideshow in the rotation

- `cycle_content`: `"patterns" | "images" | "mixed"` (default `"mixed"`) — what
  the screensaver rotates. Mixed alternates pattern → image → next pattern →
  next image, each for `cycle_seconds`, images entering with the dissolve
  reveal.
- `images_dir`: point the image source at any folder; unset means the app's own
  `images/` as today.
- Rescan the folder each lap so newly dropped files join without a restart;
  empty folder falls back to patterns-only — never a black screen.
- Manual behaviour untouched: `Tab`, `N`/`P`, and `--image` work exactly as
  they do now.

Verify: rotation sequencing unit-tested at faked timestamps (advance, wrap +
rescan, empty-folder fallback, mixed alternation), config validation for both
new keys, run-loop smoke in all three `cycle_content` values.

### R2d — the zoom *(last)* ✅ shipped 2026-10-26

Built as `mandelbrot`, a pure function like R2a's, in a side session running
alongside R2c. Each 80 s dive goes from the whole set down to a 1e-12 view,
easing in, panning onto its target, and fading through black at the reset. The
five targets are Misiurewicz points found by Newton's method (Seahorse Valley,
the triple-spiral valley, Elephant Valley, the point i, the antenna), so every
depth stays busy; the famous hand-picked Seahorse coordinates turned out to be
solid minibrot by 1e-7. Escape time drops escaped points as it goes and checks
escape every 6 iterations. The cap rises 20 a decade, and the frame's own
first escapes set the working budget. Drawn as smooth-coloured contour bands
spaced by octaves, merging into a solid set, flowing slowly inward. **Julia
not done:** Mandelbrot only, dives rotating through the five targets. Braille
computes once per cell and interpolates: measured, full 2×4 costs 18 ms median
/ 50 ms max a frame for the pattern alone. Timings, the target hunt and the
precision check are in WORKLOG 2026-10-26; tests are `tests/test_zoom.py`
plus the contract checks (106 in total). Original plan:

Mandelbrot/Julia endless zoom. Pure `(X, Y, t)` but the heaviest per frame:
escape-time with early-exit masking, an iteration budget that scales with zoom
depth, smooth (normalised) colouring, and a cycle reset before float64
precision dies (~1e-13). Measure frame times headlessly at full-screen braille
resolution first; if it can't hold `fps` there, it computes at cell resolution
and upsamples for braille — measured, not guessed.

### After R2

One `.scr` rebuild picks up all of it — new *code* needs a rebuild, settings
never do (R1's whole point). Fold that rebuild into the still-open field run,
whose sheet gains: `G` through 14 patterns, mixed rotation against a folder of
real photos, and rain/fire/Life watched at both 60 fps and the 2 fps throttle.

---

## R3 — Presets, colour themes & custom palettes

Covers the old "palette editor" backlog item, and shares R1's config machinery —
which is why it sits here rather than first.

**Colour themes.** Colour is currently three unrelated things: a hardcoded
two-stop gradient for generative (`_GEN_LOW` → `_GEN_HIGH`, blue-ish), source
tint for image/video, and `renderer.bg`/fg for mono. A theme unifies them:
a named `{bg, fg, gradient stops}`. Ship amber CRT (`#FFB000` on near-black),
green phosphor, warm cream-on-slate, ice, mono-white, plus "source colour" for
image/video. Multi-stop gradients via `np.interp` per channel — cleaner than the
current two-stop lerp and no more expensive. Themes live as data in `themes.py`
and are extendable from the config file, so a user adds one without touching code.
(By the time this lands, R2b's minimal per-pattern two-stop override — fire,
Life — already exists; themes absorb and generalise it rather than fighting it.)

**Presets.** A named bundle of full app state — mode, pattern, palette, theme,
density, font size, colour, fps. `F1`–`F8` recall; a save binding writes the
current state into a slot. HUD shows the active preset name.

**Two design notes**

- **Don't let the app write the hand-edited file.** If `config.json` is both
  hand-authored and machine-rewritten, a save reformats whatever the user typed
  (and JSON has no comments to lose, but ordering and spacing still go). Cleanest
  split: `config.json` is read-only to the app; `presets.json` is app-managed.
- **Theme changes must invalidate the image cache.** `_img_surface` / `_img_key`
  hold a pre-rendered surface; forget this and the theme appears not to apply
  until you press `N`. Same trap `_set_palette` already handles.

**Custom palettes, the cheap way.** The original "palette editor" idea implied a
UI. 90% of the value comes from a config key — `"palettes": {"blocks": " ░▒▓█"}`
— registered into `_RAMP_STRINGS` and `NAMES` at startup. Do that first; a live
in-app ramp editor is a stretch goal, not a prerequisite.

---

## R4 — Edge-aware image mode

The biggest visual win available for photographs, and the biggest change to the
hot path — hence last.

**What it is.** Image mode maps brightness only, so edges dissolve into tonal
mush. Structure-aware ASCII computes the image gradient per cell and, where the
gradient is strong, substitutes a *directional* glyph — `-` horizontal, `|`
vertical, `/` and `\` diagonal — falling back to the brightness ramp elsewhere.
It's what separates ASCII art that reads as a picture from ASCII art that reads
as a gradient.

**Approach**

- Blur before differentiating. A **difference-of-Gaussians** (σ≈1.0 and 1.6) on
  the grayscale first is what makes edges read as deliberate *lines* rather than
  per-pixel noise. Skipping this is the usual reason naive attempts look jittery.
- Sobel for magnitude and direction; quantise direction into 4 bins (8 if the
  font carries convincing glyphs for the extra angles).
- **Adaptive threshold** — a percentile of gradient magnitude, not a constant —
  so dark and bright photos both behave.
- **No new dependencies.** Sobel and Gaussian blur are separable 1-D
  convolutions; numpy does both fine. Do not pull in scipy for this.
- **Keep the single abstraction intact.** Brightness field stays the core;
  add a separate `apply_edges(grid, gray, …)` overlay step after
  `field_to_ramp`. Don't fold edge logic into the mapper.
- **Gate it off for braille** — braille already encodes structure at 2×4 and has
  no directional glyphs. Make it a per-palette capability flag rather than a
  special case buried in a branch.
- **Video too**, same code path — but it's per-frame cost at 30 fps. Benchmark
  before enabling by default; expose an `E` toggle and a config key.

**Fold in the old brightness/contrast backlog item here.** Gamma plus black/white
point applied to the brightness field before glyph mapping, adjustable live and
shown in the HUD. It's the same "make image mode actually good" job, and it fixes
the known braille-plus-colour dimness on dark images.

**Risk: medium.** It touches the hottest path and interacts with the image
surface cache, colour tinting, and the reveal-dissolve mask. `tests/` now exists
(R1 started it), so add engine-mapping tests there before changing the mapper —
the braille and ramp paths must not be able to regress silently.

---

# Parked — considered, not scheduled

Ideas raised 2026-08-01 and deliberately not taken this round. Recorded so they
don't need rediscovering.

- **Audio-reactive mode** — mic or Windows WASAPI system-audio loopback driving
  the brightness field (spectrum bars, radial bloom, waveform). The obvious
  missing piece for something called a *visualizer*. Would take an optional
  dependency, the same way OpenCV is optional today.
- **Transitions & post-FX** — crossfade between patterns instead of the current
  hard cut every 20 s; CRT scanlines, bloom on bright glyphs, vignette.
- **Export & headless CLI** — GIF/MP4 recording, ANSI `.txt` and HTML/SVG output,
  and a one-shot `convert` command needing no GUI. (Absorbs the old "export to
  animated GIF" backlog item.)
- **Test suite** — started in R1 (`tests/`, 46 tests, runs with or without
  pytest). Still missing: engine/palette coverage, which R4 wants, and most
  of the renderer (only its braille font check is tested, since 2026-10-26).
- **Screen-capture source** — desktop or a chosen region rendered live as ASCII.
- **Image slideshow** — *unparked 2026-08-05*, now R2c above. Only the drift +
  crossfade half stays parked here, with Transitions & post-FX.
- **Per-cell glyph-override channel** — a pattern returning glyph choices
  alongside brightness (katakana rain heads, per-pattern ramps). Widens the
  core brightness-field contract, so deferred deliberately (decision
  2026-08-05) rather than drifted into. Revisit after R2 with fresh eyes.
- **`electric` homage** — *promoted 2026-08-10 into R2a* on Matthew's say-so;
  the sketch lives there now. Background (what *Electric !* was and how its
  `AnimatePalette` trick worked) is in WORKLOG 2026-08-10; the original sits
  in `electric/`, git-ignored.
- **Kaleidoscope & reaction–diffusion** — the two R2 candidates not taken:
  kaleidoscope is really a coordinate-fold *modifier* (argues for a small
  post-pattern pipeline), and Gray–Scott needs many iterations per frame in a
  screensaver whose selling point is being quiet.
- **Multi-monitor** — the `.scr` currently paints the primary display only.
- **`.scr` preview support** — the little settings-dialog monitor shows blank;
  proper support means parenting a window to the HWND Windows passes with `/p`.

---

# Standing notes

- Repo has a GitHub remote: `MatthewCarven/AsciiArtScreenSaver`. Pushing stays
  Matthew's call. (Earlier notes saying "local only, no remote" were stale.)
- Tests must never touch a real `~/.config` or `%APPDATA%` — use the `sandbox()`
  helper in `tests/_support.py`. A test that skipped it wrote a config into the
  container's home directory and then silently changed a later test's result.
- **Git from the sandbox leaves lock files it cannot delete.** The mount forbids
  `unlink`, so index/ref-touching commands leave stale `.lock` files that block
  the next one. Workaround, refined: park them *inside the mount* —
  `mkdir -p .git/stale-locks` and `mv .git/*.lock` there before and after each
  git command. Inside `.git` so they never show as untracked, and never parked
  outside the mount (a cross-filesystem move is copy-then-unlink, and the
  unlink is exactly what's forbidden — those failures hide easily). Use
  `git --no-optional-locks status` for read-only checks. The parked files are
  Matthew's to delete whenever. `tmp_obj_*` orphans under `.git/objects/` are
  harmless and don't block anything.
- The sandbox mirror has served stale copies of `app.py`/`generative.py` before.
  Verify against the real files by read-back; build test copies in `/tmp`.
