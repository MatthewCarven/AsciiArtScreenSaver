"""The generative brightness source for the idle screensaver.

Holds the animation state (random phases, the selected pattern, the coordinate
grid) and produces a brightness field by delegating to one of the functions in
:mod:`asciiviz.patterns`. Patterns are evaluated in *physical* coordinates
(cell-widths) so they look identical regardless of palette sub-resolution, and a
shared ``density`` control sparsifies the result into the soft mosaic of dots
that inspired this project.
"""

from __future__ import annotations

import numpy as np

from . import patterns


class GenerativeField:
    def __init__(self, cols: int, rows: int, cell_aspect: float = 2.0,
                 density: float = 0.6, seed: int = 7):
        self.density = float(density)
        rng = np.random.default_rng(seed)
        self.phase = rng.uniform(0, 2 * np.pi, size=8).astype(np.float32)
        self.patterns = patterns.PATTERNS
        self.pattern_index = 0
        self.set_dims(cols, rows, cell_aspect)

    # -- pattern selection ------------------------------------------------- #
    @property
    def pattern_name(self) -> str:
        return self.patterns[self.pattern_index][0]

    def next_pattern(self, step: int = 1) -> str:
        self.pattern_index = (self.pattern_index + step) % len(self.patterns)
        return self.pattern_name

    def set_pattern(self, name: str) -> bool:
        for i, (n, _) in enumerate(self.patterns):
            if n == name:
                self.pattern_index = i
                return True
        return False

    # -- geometry ---------------------------------------------------------- #
    def set_dims(self, cols: int, rows: int, cell_aspect: float):
        self.cols = max(1, cols)
        self.rows = max(1, rows)
        self.cell_aspect = cell_aspect
        self.width_span = float(self.cols)
        self.height_span = float(self.rows) * cell_aspect
        self._coords: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}

    def _grid(self, h: int, w: int):
        c = self._coords.get((h, w))
        if c is None:
            xs = np.linspace(0.0, self.width_span, w, dtype=np.float32)
            ys = np.linspace(0.0, self.height_span, h, dtype=np.float32)
            c = np.meshgrid(xs, ys)
            self._coords[(h, w)] = c
        return c

    # -- frame ------------------------------------------------------------- #
    def frame(self, t: float, h: int, w: int) -> np.ndarray:
        """Return an (h, w) brightness field in [0, 1] at time ``t`` seconds."""
        X, Y = self._grid(h, w)
        raw = self.patterns[self.pattern_index][1](X, Y, float(t), self)
        raw = np.clip(raw, 0.0, 1.0)

        # Sparsify into dots: crush everything below (1 - density) to zero, then
        # apply a gentle gamma so the surviving dots have a soft falloff.
        d = max(self.density, 1e-3)
        g = np.clip((raw - (1.0 - d)) / d, 0.0, 1.0)
        np.power(g, 1.3, out=g)
        return g.astype(np.float32)
