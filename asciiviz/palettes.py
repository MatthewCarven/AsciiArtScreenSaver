"""Character palettes for the visualizer.

A palette maps a brightness value in [0, 1] to a glyph. Two of the palettes
("dots" and "ramp") are simple ordered strings from darkest -> brightest, where
index 0 is empty space and the last index is the densest glyph. "braille" is a
special palette handled by the engine via 2x4 sub-pixel packing.

We draw light glyphs on a dark background, so a *bright* source value should map
to a *denser* glyph (more ink on screen == brighter cell).
"""

# Dots / full-stops: the soft mosaic look (like the blank Claude window).
# Ordered by roughly increasing ink coverage.
DOTS = " ·.:•●"

# Classic grayscale ramp, dark -> light (space is darkest, '@' is brightest).
RAMP = " .:-=+*#%@"

# A longer, smoother ramp available via the palette registry for fine detail.
RAMP_LONG = " .'`^\",:;Il!i~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@"

NAMES = ("dots", "ramp", "braille")

_RAMP_STRINGS = {
    "dots": DOTS,
    "ramp": RAMP,
    "ramp_long": RAMP_LONG,
}


def is_braille(name: str) -> bool:
    return name == "braille"


def ramp_string(name: str) -> str:
    """Return the ordered glyph string for a non-braille palette."""
    return _RAMP_STRINGS[name]


def next_name(name: str, step: int = 1) -> str:
    """Cycle to the next/previous palette name."""
    i = NAMES.index(name) if name in NAMES else 0
    return NAMES[(i + step) % len(NAMES)]
