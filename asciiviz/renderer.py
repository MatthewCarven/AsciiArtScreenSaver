"""pygame rendering: fonts, the cell grid, and fast glyph blitting.

Rendering strategy
------------------
* Mono (single colour) dots/ramp: render each row string in one ``font.render``
  call — very fast, and the natural choice for the animated generative field.
* Colour dots/ramp and all braille: blit per cell from a small glyph cache. For
  braille we always position glyphs at fixed cell origins so alignment holds
  even if the braille-capable font isn't perfectly monospaced.

Image frames (which don't change once revealed) are rendered once into a cached
surface by the app, so per-cell colour work happens only when the frame changes.
"""

from __future__ import annotations

import pygame

# Preference order for the main monospaced font.
_MONO_CANDIDATES = "dejavusansmono,consolas,liberationmono,menlo,couriernew,monospace"

# Fonts that commonly include the Braille Patterns block (U+2800+).
_BRAILLE_CANDIDATES = (
    "dejavusansmono", "dejavusans", "notosansmono", "notosanssymbols2",
    "segoeuisymbol", "seguisym", "symbola", "freemono",
)
_BRAILLE_TEST = "⣿"


def _has_braille(font: "pygame.font.Font") -> bool:
    try:
        m = font.metrics(_BRAILLE_TEST)
        return bool(m) and m[0] is not None
    except Exception:
        return False


class Renderer:
    def __init__(self, font_size: int = 16,
                 fg=(222, 227, 238), bg=(12, 13, 17)):
        self.fg = fg
        self.bg = bg
        self.set_font_size(font_size)

    # -- font / cell setup ------------------------------------------------- #
    def set_font_size(self, size: int):
        self.font_size = max(6, int(size))

        path = pygame.font.match_font(_MONO_CANDIDATES)
        self.mono = (pygame.font.Font(path, self.font_size) if path
                     else pygame.font.SysFont("monospace", self.font_size))

        self.cell_w = self.mono.size("M")[0] or max(1, self.font_size // 2)
        self.cell_h = self.mono.get_linesize()

        # Find a braille-capable font (reuse mono if it has the glyphs).
        self.braille_ok = False
        self.braille_font = self.mono
        if _has_braille(self.mono):
            self.braille_ok = True
        else:
            for name in _BRAILLE_CANDIDATES:
                p = pygame.font.match_font(name)
                if not p:
                    continue
                f = pygame.font.Font(p, self.font_size)
                if _has_braille(f):
                    self.braille_font = f
                    self.braille_ok = True
                    break

        self._glyph_cache: dict = {}

    def grid_size(self, width: int, height: int):
        return max(1, width // self.cell_w), max(1, height // self.cell_h)

    @property
    def cell_aspect(self) -> float:
        return self.cell_h / self.cell_w

    # -- drawing primitives ------------------------------------------------ #
    def clear(self, surf):
        surf.fill(self.bg)

    def _glyph(self, font, ch: str, color):
        key = (id(font), ch, color)
        s = self._glyph_cache.get(key)
        if s is None:
            s = font.render(ch, True, color)
            if len(self._glyph_cache) > 20000:  # guard against unbounded growth
                self._glyph_cache.clear()
            self._glyph_cache[key] = s
        return s

    def blit_rows_mono(self, surf, rows, color=None, x0: int = 0, y0: int = 0):
        """Fast path: one render call per row, single colour."""
        color = color or self.fg
        y = y0
        for line in rows:
            if line and not line.isspace():
                surf.blit(self.mono.render(line, True, color), (x0, y))
            y += self.cell_h

    def blit_grid_color(self, surf, grid, color_grid, font=None,
                        x0: int = 0, y0: int = 0, empty=(" ", "⠀")):
        """Per-cell colour blit. ``color_grid`` is (rows, cols, 3) uint8."""
        font = font or self.mono
        cw, ch = self.cell_w, self.cell_h
        empty_set = set(empty)
        for r in range(len(grid)):
            row = grid[r]
            crow = color_grid[r]
            y = y0 + r * ch
            for c in range(len(row)):
                glyph = row[c]
                if glyph in empty_set:
                    continue
                surf.blit(self._glyph(font, glyph, tuple(int(v) for v in crow[c])),
                          (x0 + c * cw, y))

    def blit_grid_mono(self, surf, grid, color=None, font=None,
                       x0: int = 0, y0: int = 0, empty=(" ", "⠀")):
        """Per-cell single-colour blit (used for braille, which needs fixed
        cell positioning)."""
        color = color or self.fg
        font = font or self.mono
        cw, ch = self.cell_w, self.cell_h
        empty_set = set(empty)
        for r in range(len(grid)):
            row = grid[r]
            y = y0 + r * ch
            for c in range(len(row)):
                glyph = row[c]
                if glyph in empty_set:
                    continue
                surf.blit(self._glyph(font, glyph, color), (x0 + c * cw, y))
