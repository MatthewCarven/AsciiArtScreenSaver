# ASCII Visualizer

A pygame screensaver-style ASCII visualizer. It has two modes — a **generative
idle mode** with thirteen drifting patterns (dot-field, plasma, ripples, flow,
starfield, Matrix rain, a lava lamp, a depth tunnel, a spiral galaxy, drifting
fireflies, `electric` — an homage to JX Bardant's 1997 *Electric !*
screensaver, its rotating-palette contour bands reborn in glyphs — and two
live simulations: PSX Doom's fire and Conway's Life with glowing trails; the
dot-field is the soft mosaic-of-dots look from the blank Claude window) and an
**image-to-ASCII** converter — and three character palettes you can switch
between live: **dots**, a **grayscale ramp**, and **braille**. Press `G` to
cycle the generative patterns.

![dots](images/sample_rings.png)

## Install

```bash
pip install -r requirements.txt
```

Dependencies: `pygame`, `Pillow`, `numpy`. The video/webcam source also needs
`opencv-python` (optional — everything else runs without it).

> **Braille palette note:** braille glyphs need a font that includes the Unicode
> Braille Patterns block. The app tests each candidate by drawing two braille
> glyphs, so a font that only has a missing-glyph box doesn't count, and uses the
> first that really draws them: **DejaVu Sans Mono**, then **DejaVu Sans**,
> **Segoe UI Symbol** (installed with Windows) and a few others. If none does,
> the app tells you and the other two palettes still work. Consolas alone does
> not include braille, and not every copy of DejaVu Sans Mono does either.

## Run

```bash
python main.py                       # generative dot-field (idle screensaver)
python main.py --mode image          # start on the bundled sample image
python main.py --image path/to/photo.jpg
python main.py --palette braille --color
python main.py --font-size 12 --density 0.5
python main.py --webcam                  # live webcam as ASCII (needs opencv-python)
python main.py --video path/to/clip.mp4  # play a video file as ASCII
python main.py --pattern electric        # start on a particular pattern
python main.py --list-patterns           # see what the pattern names are
python main.py --write-config            # save your current settings for next time
```

All options: `--image`, `--images-dir FOLDER`, `--video`, `--webcam [INDEX]`,
`--mode {generative,image,video}`, `--palette {dots,ramp,braille}`, `--pattern
NAME`, `--color` / `--no-color`, `--font-size`, `--density`, `--fps`, `--width`,
`--height`, `--config PATH`, plus the screensaver's own (see [Settings
file](#settings-file)). See `python main.py --help`.

## Controls

| Key            | Action                                              |
| -------------- | --------------------------------------------------- |
| `Tab` / `M`    | Switch mode (generative ⇄ image)                    |
| `1` `2` `3`    | Palette: dots / ramp / braille                      |
| `G`            | Cycle the 13 generative patterns (see `--list-patterns`)  |
| `V`            | Start / stop live webcam (video mode)               |
| `C`            | Toggle colour (tint glyphs by source / brightness)  |
| `Space`        | Pause / resume the animation                        |
| `N` / `P` `→` `←` | Next / previous image (drops you into image mode) |
| `[` / `]`      | Decrease / increase resolution (font cell size)     |
| `+` / `-`      | Increase / decrease generative dot density          |
| `F`            | Toggle fullscreen                                   |
| `S`            | Save the current frame to `captures/`               |
| `H`            | Show / hide the on-screen HUD                       |
| `Esc` / `Q`    | Quit                                                |

The HUD auto-hides after 15 seconds of no input and reappears the instant you
press a key or move the mouse. `H` is a hard on/off toggle that overrides the
auto-fade.

## Your own images

Drop any `.png` / `.jpg` / `.bmp` / `.gif` / `.webp` into the `images/` folder,
then cycle to them with `N` / `P`. Images are fitted to the grid with correct
aspect (character cells are taller than they are wide, so this is corrected for
you) and resolve in with a brief dissolve. For the cleanest photo conversions,
try the **braille** palette (it packs 8 sub-dots per cell, the highest detail)
or the **ramp** palette with `--color`.

To use a folder of your own instead, such as a pictures folder, point
`images_dir` at it in the [settings file](#settings-file) (or pass
`--images-dir FOLDER`). The app only reads that folder: it never creates it or
writes the sample image into it. The screensaver shows these images too,
between its patterns (see `cycle_content`).

## Video & webcam

Press `V` to start your webcam (or launch with `--webcam`), and the live feed is
converted to ASCII in real time — try it with `--color` on the ramp or braille
palette. Play a video file with `--video path/to/clip.mp4`; files loop when they
reach the end. This needs `opencv-python` (`pip install opencv-python`); without
it the app still runs and just tells you when you try to use video. Switching to
any other mode — or pressing `V` again — releases the camera.

## Settings file

Anything you can pass on the command line can live in a `config.json` instead,
so you don't have to type it every time — and so the **screensaver can be
retuned without rebuilding it**.

```bash
python main.py --write-config        # writes a starter file you can edit
```

The first of these that exists wins:

1. the path given to `--config PATH`
2. the `ASCIIVIZ_CONFIG` environment variable
3. `%APPDATA%\ASCIIVisualizer\config.json` (Windows)
   or `~/.config/asciiviz/config.json` (macOS/Linux)
4. `config.json` next to the program — for the built app or screensaver, that's
   the folder holding `ASCIIVisualizer.exe` / `ASCIIVisualizer.scr`

Keys are the long option names with dashes turned into underscores, so
`--throttle-minutes` is `"throttle_minutes"`:

```json
{
  "_comment": "keys starting with _ are ignored, so use them for notes",
  "palette": "braille",
  "pattern": "plasma",
  "color": true,
  "density": 0.7,
  "cycle_content": "mixed",
  "cycle_patterns": ["dotfield", "plasma", "ripples"],
  "images_dir": "C:/Users/you/Pictures/Saver",
  "full_minutes": 5,
  "throttle_minutes": -1,
  "idle_fps": 2
}
```

Precedence is **defaults → config file → command line**, so a flag you type
always wins for that one run. `cycle_patterns` limits which patterns the
screensaver rotates through (omit it to cycle all of them), and a negative
`throttle_minutes` means "stay in the quiet phase and never exit".

**What the screensaver rotates** is `cycle_content`, and each pattern or image
stays up for `cycle_seconds` (default 20):

- `"mixed"` (the default): a pattern, then an image, then the next pattern,
  then the next image, and so on. Images come in with the dissolve.
- `"images"`: a slideshow of your pictures only.
- `"patterns"`: patterns only, as before R2c.

The images come from `images_dir`, or from the app's own `images/` folder when
that's unset. The folder is read again at the end of each lap through it, so
pictures you drop in while the saver runs join the next lap without a restart.
If it's empty, missing, or nothing in it will load, the saver shows patterns
instead, so you never get a black screen. Give `images_dir` as a full path.
Forward slashes save you escaping (in JSON a backslash must be written `\\`),
and `~` or `%USERPROFILE%` work too. The keyboard is unchanged: `Tab`, `N`/`P`
and `G` behave the same in the windowed app.

Nothing here can stop the app starting: a missing file means defaults, an
unparseable one means defaults, and a single bad value falls back to its default
while the rest still apply. Problems appear briefly in the HUD, and the HUD also
shows which file is in effect.

## Building the app and the screensaver (Windows)

One script builds a standalone app, a real Windows screensaver, or both, each
as a single self-contained file that runs without Python installed:

```powershell
pip install -r requirements.txt                                  # once
powershell -ExecutionPolicy Bypass -File build.ps1               # both
powershell -ExecutionPolicy Bypass -File build.ps1 app           # just the .exe
powershell -ExecutionPolicy Bypass -File build.ps1 screensaver   # just the .scr
```

Or double-click `build.bat` to build both, or run `build.bat app` /
`build.bat screensaver` from a command prompt. PyInstaller is installed for you
if it's missing, and `-Python path\to\python.exe` builds from a venv instead.

| File | Built from | What it is |
| ---- | ---------- | ---------- |
| `ASCIIVisualizer.exe` | `main.py` | The app. Double-click it, or give it the same options as `python main.py`, from a shortcut or a terminal (`ASCIIVisualizer.exe --help`). Webcam and video are included if `opencv-python` was installed when you built it. |
| `ASCIIVisualizer.scr` | `screensaver.py` | The screensaver. It leaves OpenCV out, so it's smaller and starts faster. |

Run from a terminal, the `.exe` prints into it (`--help`, `--list-patterns`,
`--write-config`, option errors). It's a windowed program, so the terminal
doesn't wait for it: typed straight at a prompt, the text can land after the
next prompt. Press Enter for a fresh one.

Both read the same `config.json` (see above), and both keep `images/` and
`captures/` beside themselves. Built here, that means the same folders
`python main.py` uses.

### Installing the screensaver

Right-click `ASCIIVisualizer.scr` in Explorer and choose **Install** to
preview and set it, or copy it into `C:\Windows\System32` so it shows up in
Settings → Lock screen → Screen saver. (From `System32` it can't write beside
itself, so its `images/` folder moves to `%APPDATA%\ASCIIVisualizer`; or set
`images_dir` to a folder of your own.) It runs fullscreen, hides the cursor,
rotates through the generative patterns with your images in between (see
`cycle_content` above), and quits on any key or real mouse movement.

To stay quiet when you're away it winds down in phases: full speed for
`--full-minutes` (default 5), then it throttles to `--idle-fps` (default 2) for
`--throttle-minutes` (default 5), then it exits. So CPU and fans go near-silent,
and Windows still powers off the display / sleeps on your own timers underneath
— set "turn off display" to whatever you like (e.g. 45 min) and it just works.
It does **not** hold the display awake by default; set `keep_display_awake` for
an always-on "art mode" instead.

**Changing these doesn't need a rebuild.** Windows can't pass command-line
options to a screensaver, so the settings come from `config.json` (see above).
Click **Settings** next to the screensaver in Windows and it opens that file in
Notepad, creating it first if you haven't got one — edit, save, done. If Windows
keeps relaunching the saver after it exits, set `"throttle_minutes": -1` so it
stays in the quiet phase instead of bowing out.

(Preview in the tiny settings monitor isn't supported — it shows blank there.)

## How it works

Everything is driven by a single abstraction: a **brightness field** (a 2D
array in `[0, 1]`). The generative mode synthesises one from drifting sine waves
and a couple of wandering radial sources; image mode builds one from a
downsampled greyscale image. The engine then maps that field to glyphs:

- **dots / ramp** — each cell's brightness indexes into an ordered glyph string
  (` ·.:•●` or ` .:-=+*#%@`).
- **braille** — the field is sampled at 2×4 the cell resolution and each block
  of sub-pixels is packed into one of the 256 braille glyphs (with optional
  ordered dithering for smooth tonal images).

Rendering uses a fast path (one render call per row) for single-colour frames
and a cached per-cell blit for colour and braille. Static image frames are
rendered once into a cached surface.

## Project layout

```
main.py              # entry point (also: python -m asciiviz); built into ASCIIVisualizer.exe
screensaver.py       # Windows .scr entry point (/s run, /c settings, /p preview)
build.ps1            # builds the .exe and/or .scr (build.bat is the double-click wrapper)
asciiviz/
  config.py          # config.json discovery, validation, defaults
  palettes.py        # the three palette definitions
  patterns.py        # the 13 generative patterns (11 pure functions of x, y, t; fire and life simulate)
  engine.py          # brightness-field -> glyphs; image loading
  generative.py      # drives the selected pattern; density/contrast shaping
  video.py           # webcam / video-file capture via OpenCV
  renderer.py        # pygame fonts, cell grid, glyph blitting
  app.py             # window, input, modes, HUD, CLI
images/              # drop images here; ships with a sample
captures/            # screenshots saved with the S key
tests/               # run with pytest, or run a file directly with python
```

## Tests

```bash
python -m pytest tests           # if you have pytest
python tests/test_config.py      # or just run a file — no pytest needed
```

## Acknowledgements & inspiration

This is an independent, unofficial project. The visual idea — images and ambient
motion rendered as a soft mosaic of dots — was inspired by the ambient idle
animation in Anthropic's Claude desktop app. It shares no code or assets with
that app; everything here was written from scratch (with help from Claude in
Cowork mode).

Not affiliated with, sponsored by, or endorsed by Anthropic. "Claude" and
"Anthropic" are trademarks of Anthropic, PBC, used here only to describe the
inspiration.
