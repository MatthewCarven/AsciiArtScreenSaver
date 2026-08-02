# TODO / Roadmap

The app is feature-complete for its original brief: generative idle patterns,
image-to-ASCII, video/webcam, three palettes, HUD, and a working Windows `.scr`
with wind-down. What follows is where it could go next, in the order that makes
the most sense to build.

Planned 2026-08-01. **R1 shipped 2026-08-01**; R2–R4 not started.

---

## Field run — Matthew (open)

A run sheet for the next sit-down. Roughly in order, but each step stands alone
— skip anything you don't fancy. Most of this has *never* run on real hardware:
the sandbox has no camera, no Windows, and no screen, so everything below was
verified logically rather than by looking at it.

### 0. Rebuild the .scr once

```
build_screensaver.bat
```

Right-click the new `ASCIIVisualizer.scr` → **Install**. This is the last
rebuild you should need for a settings change.

### 1. The app, windowed

```
python main.py
```

- `G` cycles patterns — dotfield, plasma, ripples, flow, starfield.
- `1` `2` `3` switch palettes. **Braille (`3`) is the one to watch**: Windows'
  Consolas has no braille glyphs, so if DejaVu Sans Mono isn't installed you
  should get a toast saying so rather than a screen of empty boxes. Either
  outcome is worth recording.
- `C` colour, `+`/`-` density, `[`/`]` resolution, `Tab` image mode, `N`/`P`
  through `images/`, `S` saves a PNG to `captures/`.
- HUD should fade after 15 s of no input and relight the instant you touch
  anything.

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
  those two, while `G` still reaches all five.

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
- [ ] **Rebuild the `.scr` once more** to pick up R1 (`build_screensaver.bat`).
      This is the last rebuild you should ever need for a settings change — from
      then on it's the Settings button.
- [ ] `Claude.md` shows as modified in git: the content is identical, only the
      line endings flipped to CRLF. Either commit it or `git checkout Claude.md`.
      Setting `core.autocrlf` or adding a `.gitattributes` would stop it
      recurring.

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

## R2 — More generative patterns

Cheap, self-contained, immediately visible. `patterns.py` was written for this:
add a function, append to `PATTERNS`, done.

**One contract decision to make first.** The current signature is a *pure
function* of `(X, Y, t, gf)` — no memory between frames. The best-looking
candidates (fire, Life, reaction-diffusion) are iterative and need the previous
frame. Suggested fix: let a `PATTERNS` entry be either a plain function (works
exactly as now) or an object with `__call__(X, Y, t, gf)` plus an optional
`reset(shape)`. Hook `reset` into `GenerativeField.set_dims` (grid changed) and
`next_pattern` (switching in). Backwards compatible; the five existing patterns
need no edits.

**Two gotchas worth deciding up front**

- **Throttle phase.** The screensaver drops to 2 fps after 5 minutes. A stateful
  sim then advances 2 steps per second — fire stutters, Life crawls. Either step
  the sim proportionally to `dt` (multiple substeps per frame) or mark stateful
  patterns as "skip during throttle" and let the cycle pick a pure one.
- **Braille sub-resolution.** Patterns are evaluated at `(rows*4, cols*2)` for
  braille. The existing ones are resolution-independent by design (that's what
  the physical cell-width coordinates buy). Cellular ones are not — a Life grid
  at 8× the cells is a visibly different simulation. Simulate at cell resolution
  and upsample, or accept that braille looks different.

**Candidates, best look-per-line-of-code first**

| Pattern | State? | Notes |
| --- | --- | --- |
| Doom fire | yes | Bottom row seeded hot, each row above cools and jitters sideways. Stunning in the `ramp` palette with warm colour. The classic. |
| Matrix rain | light | Per-column head position + speed + fading tail — arrays, not a full sim. See the engine note below. |
| Conway's Life | yes | Neighbour count via four `np.roll` sums. Add soft decay trails so it isn't binary-flat in a dot palette. |
| Mandelbrot / Julia zoom | no | Pure `(X, Y, t)` — fits the existing contract perfectly. Escape-time normalised to `[0, 1]`. Reset the zoom cycle before float64 precision dies around 1e-14. |
| Kaleidoscope | n/a | Not a pattern — a *modifier*: fold coordinates into a wedge and mirror, then call any other pattern. Argues for a small post-pattern pipeline. |
| Reaction–diffusion (Gray-Scott) | yes | Gorgeous organic blobs, but needs many iterations per frame. This is a screensaver whose entire selling point is being quiet — simulate at low resolution and upsample, and measure the CPU cost. |
| Metaballs, Lissajous, curl-noise warp, tunnel | no | Cheap fills, all pure functions. |

**Engine note surfaced by Matrix rain:** it wants specific *glyphs* (katakana,
digits) with a bright leading character, not just brightness. Everything today
flows through the single brightness-field abstraction. Options: accept a
brightness-only approximation (works, looks decent), or add an optional per-cell
glyph-override channel that a pattern may return alongside the field. The second
is more honest but widens the core contract — worth a conscious decision rather
than drifting into it.

**Already in place from R1:** `cycle_patterns` in the config file restricts the
screensaver's rotation and `--pattern` pins one, so a big library won't dilute
the rotation. New patterns just need adding to `PATTERNS` — the config validates
names against it automatically.

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
  pytest). Still missing: engine/palette/renderer coverage, which R4 wants.
- **Screen-capture source** — desktop or a chosen region rendered live as ASCII.
- **Image slideshow for the screensaver** — cycle `images/` with drift and
  crossfade instead of only generative patterns.
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
  `unlink`, so every git command that touches the index leaves a stale
  `.git/index.lock` that blocks the next one. Workaround: `mv` the lock into
  `_to_delete/` (moves are permitted) and carry on; use
  `git --no-optional-locks status` for read-only checks. The old worry that this
  blocks commits outright was wrong — it's a nuisance, not a wall.
- The sandbox mirror has served stale copies of `app.py`/`generative.py` before.
  Verify against the real files by read-back; build test copies in `/tmp`.
