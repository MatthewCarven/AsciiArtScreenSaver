"""The generative dot-field — the idle "screensaver" brightness source.

Produces a smooth, slowly drifting brightness field from layered sine waves and
a couple of wandering radial blobs. It is evaluated in *physical* coordinates
(measured in cell widths) so the pattern looks the same regardless of palette
sub-resolution, and a ``density`` control sparsifies it into the soft mosaic of
dots that inspired this project.
"""

from __future__ import annotations

import numpy as np


class GenerativeField:
    def __init__(self, cols: int, rows: int, cell_aspect: float = 2.0,
                 density: float = 0.6, seed: int = 7):
        self.density = float(density)
        rng = np.random.default_rng(seed)
        self.phase = rng.uniform(0, 2 * np.pi, size=8).astype(np.float32)
        self.set_dims(cols, rows, cell_aspect)

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

    def frame(self, t: float, h: int, w: int) -> np.ndarray:
        """Return an (h, w) brightness field in [0, 1] at time ``t`` seconds."""
        X, Y = self._grid(h, w)
        p = self.phase
        span = max(self.width_span, 1.0)
        k = 2.0 * np.pi / span  # one full wave per 'span' cell-widths

        f = np.sin(X * (k * 3.0) + t * 0.50 + p[0])
        f = f + np.sin(Y * (k * 3.0) - t * 0.42 + p[1])
        f = f + np.sin((X + Y) * (k * 2.0) + t * 0.31 + p[2])
        f = f + np.sin((X - Y) * (k * 2.4) - t * 0.27 + p[3])

        # Two slowly wandering radial sources add larger-scale structure.
        cx = self.width_span * (0.5 + 0.32 * np.sin(t * 0.16 + p[4]))
        cy = self.height_span * (0.5 + 0.32 * np.cos(t * 0.12 + p[5]))
        r1 = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        f = f + 1.4 * np.sin(r1 * (k * 2.2) - t * 0.9 + p[6])

        cx2 = self.width_span * (0.5 + 0.40 * np.cos(t * 0.09 + p[7]))
        cy2 = self.height_span * (0.5 + 0.40 * np.sin(t * 0.07))
        r2 = np.sqrt((X - cx2) ** 2 + (Y - cy2) ** 2)
        f = f + 1.1 * np.sin(r2 * (k * 1.6) + t * 0.6)

        # Normalise the roughly [-5, 5] sum into [0, 1].
        f = 0.5 + 0.5 * (f / 5.0)
        np.clip(f, 0.0, 1.0, out=f)

        # Sparsify into dots: crush everything below (1 - density) to zero, then
        # apply a gentle gamma so the surviving dots have a soft falloff.
        d = max(self.density, 1e-3)
        g = np.clip((f - (1.0 - d)) / d, 0.0, 1.0)
        np.power(g, 1.3, out=g)
        return g.astype(np.float32)
