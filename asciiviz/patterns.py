"""Generative pattern functions for the idle screensaver.

Each pattern takes the physical coordinate grids ``X`` and ``Y`` (measured in
cell-widths, so motion looks isotropic regardless of palette sub-resolution),
the time ``t`` in seconds, and the owning :class:`GenerativeField` ``gf`` (for
its random ``phase`` array and span). It returns a brightness field in roughly
[0, 1]; ``GenerativeField`` applies the shared density/contrast shaping after.

Add a new pattern by writing a function with this signature and appending it to
``PATTERNS`` — it then becomes selectable at runtime (the G key).
"""

from __future__ import annotations

import numpy as np


def _k(gf) -> float:
    """Base wave number: one full wave per ``width_span`` cell-widths."""
    return 2.0 * np.pi / max(gf.width_span, 1.0)


def dotfield(X, Y, t, gf):
    """The original soft mosaic: layered sines + two wandering radial sources."""
    p = gf.phase
    k = _k(gf)
    f = np.sin(X * (k * 3.0) + t * 0.50 + p[0])
    f = f + np.sin(Y * (k * 3.0) - t * 0.42 + p[1])
    f = f + np.sin((X + Y) * (k * 2.0) + t * 0.31 + p[2])
    f = f + np.sin((X - Y) * (k * 2.4) - t * 0.27 + p[3])
    cx = gf.width_span * (0.5 + 0.32 * np.sin(t * 0.16 + p[4]))
    cy = gf.height_span * (0.5 + 0.32 * np.cos(t * 0.12 + p[5]))
    r1 = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    f = f + 1.4 * np.sin(r1 * (k * 2.2) - t * 0.9 + p[6])
    cx2 = gf.width_span * (0.5 + 0.40 * np.cos(t * 0.09 + p[7]))
    cy2 = gf.height_span * (0.5 + 0.40 * np.sin(t * 0.07))
    r2 = np.sqrt((X - cx2) ** 2 + (Y - cy2) ** 2)
    f = f + 1.1 * np.sin(r2 * (k * 1.6) + t * 0.6)
    return 0.5 + 0.5 * (f / 5.0)


def plasma(X, Y, t, gf):
    """Classic plasma — smooth interfering sines, great with colour on."""
    p = gf.phase
    k = _k(gf)
    v = np.sin(X * (k * 4.0) + t * 0.6 + p[0])
    v = v + np.sin(Y * (k * 3.3) - t * 0.5 + p[1])
    v = v + np.sin((X + Y) * (k * 2.6) + t * 0.4 + p[2])
    cx = gf.width_span * (0.5 + 0.30 * np.sin(t * 0.30 + p[3]))
    cy = gf.height_span * (0.5 + 0.30 * np.cos(t * 0.27 + p[4]))
    v = v + np.sin(np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) * (k * 3.0) + t * 0.7)
    return 0.5 + 0.5 * (v / 4.0)


def ripples(X, Y, t, gf):
    """Two wandering centres throwing interfering concentric ripples."""
    p = gf.phase
    k = _k(gf)
    cx = gf.width_span * (0.5 + 0.25 * np.sin(t * 0.20 + p[0]))
    cy = gf.height_span * (0.5 + 0.25 * np.cos(t * 0.17 + p[1]))
    r1 = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    cx2 = gf.width_span * (0.5 + 0.30 * np.cos(t * 0.13 + p[2]))
    cy2 = gf.height_span * (0.5 + 0.30 * np.sin(t * 0.11 + p[3]))
    r2 = np.sqrt((X - cx2) ** 2 + (Y - cy2) ** 2)
    v = np.sin(r1 * (k * 5.0) - t * 1.4) + np.sin(r2 * (k * 4.0) - t * 1.1)
    return 0.5 + 0.5 * (v / 2.0)


def flow(X, Y, t, gf):
    """Swirling bands: coordinates warped by sines of the opposite axis."""
    p = gf.phase
    k = _k(gf)
    amp = gf.width_span * 0.06
    wx = X + amp * np.sin(Y * (k * 1.5) + t * 0.40 + p[0])
    wy = Y + amp * np.sin(X * (k * 1.5) - t * 0.35 + p[1])
    v = np.sin(wx * (k * 3.0) + t * 0.30) + np.sin(wy * (k * 3.0) - t * 0.25)
    return 0.5 + 0.5 * (v / 2.0)


def starfield(X, Y, t, gf):
    """Twinkling stars — independent hashes for which cells are stars and for
    each star's twinkle phase, so they sparkle out of sync."""
    p = gf.phase
    s = 1.3  # star-cell size in cell-widths
    gx = np.floor(X / s).astype(np.int64)
    gy = np.floor(Y / s).astype(np.int64)
    seed = int(gf.phase[0] * 1000.0)
    n = np.abs((gx * 73856093) ^ (gy * 19349663) ^ seed)
    sel = (n % 997).astype(np.float32) / 997.0          # star selection
    ph = ((n // 997) % 991).astype(np.float32) / 991.0  # independent twinkle phase
    is_star = (sel > 0.86).astype(np.float32)           # ~14% of cells are stars
    twinkle = 0.45 + 0.55 * (0.5 + 0.5 * np.sin(t * 1.6 + ph * 6.2832 + p[1]))
    return is_star * twinkle


# Order defines the cycle order of the G key. dotfield stays first (default).
PATTERNS = [
    ("dotfield", dotfield),
    ("plasma", plasma),
    ("ripples", ripples),
    ("flow", flow),
    ("starfield", starfield),
]
