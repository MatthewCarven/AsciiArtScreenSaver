# ASCII Visualizer

A pygame screensaver-style ASCII visualizer. It has two modes — a **generative
idle mode** with five drifting patterns (dot-field, plasma, ripples, flow, and a
twinkling starfield; the dot-field is the soft mosaic-of-dots look from the blank
Claude window) and an **image-to-ASCII** converter — and three character
palettes you can switch between live: **dots**, a **grayscale ramp**, and
**braille**. Press `G` to cycle the generative patterns.

![dots](images/sample_rings.png)

## Install

```bash
pip install -r requirements.txt
```

Dependencies: `pygame`, `Pillow`, `numpy`.

> **Braille palette note:** braille glyphs need a font that includes the Unicode
> Braille Patterns block. **DejaVu Sans Mono** (very common; ships with many
> tools) works perfectly. If no braille-capable font is found, the app tells you
> and the other two palettes still work. On Windows, installing DejaVu Sans Mono
> is the easiest fix — Consolas alone does not include braille.

## Run

```bash
python main.py                       # generative dot-field (idle screensaver)
python main.py --mode image          # start on the bundled sample image
python main.py --image path/to/photo.jpg
python main.py --palette braille --color
python main.py --font-size 12 --density 0.5
```

All options: `--image`, `--mode {generative,image}`, `--palette
{dots,ramp,braille}`, `--color`, `--font-size`, `--density`, `--fps`,
`--width`, `--height`. See `python main.py --help`.

## Controls

| Key            | Action                                              |
| -------------- | --------------------------------------------------- |
| `Tab` / `M`    | Switch mode (generative ⇄ image)                    |
| `1` `2` `3`    | Palette: dots / ramp / braille                      |
| `G`            | Cycle generative pattern (dotfield → plasma → ripples → flow → starfield) |
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
main.py              # entry point (also: python -m asciiviz)
asciiviz/
  palettes.py        # the three palette definitions
  patterns.py        # generative pattern functions (dot-field, plasma, ripples, flow, starfield)
  engine.py          # brightness-field -> glyphs; image loading
  generative.py      # drives the selected pattern; density/contrast shaping
  renderer.py        # pygame fonts, cell grid, glyph blitting
  app.py             # window, input, modes, HUD, CLI
images/              # drop images here; ships with a sample
captures/            # screenshots saved with the S key
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
