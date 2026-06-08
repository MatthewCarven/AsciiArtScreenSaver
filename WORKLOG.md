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
