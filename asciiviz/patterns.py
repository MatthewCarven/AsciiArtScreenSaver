"""Generative pattern functions for the idle screensaver.

Each pattern takes the physical coordinate grids ``X`` and ``Y`` (measured in
cell-widths, so motion looks isotropic regardless of palette sub-resolution),
the time ``t`` in seconds, and the owning :class:`GenerativeField` ``gf`` (for
its random ``phase`` array and span). It returns a brightness field in roughly
[0, 1]; ``GenerativeField`` applies the shared density/contrast shaping after.

Add a new pattern by writing a function with this signature and appending it to
``PATTERNS`` — it then becomes selectable at runtime (the G key).

Every pattern here is a *pure* function of ``(X, Y, t)`` — no memory between
frames — which is what makes pause free and the screensaver's throttle phase
harmless. The R2a batch (rain, lava, tunnel, galaxy, fireflies, electric) keeps
that contract by deriving all per-entity state (drop speeds, blob orbits,
charge paths) from integer hashes and closed-form orbits instead of simulation.
"""

from __future__ import annotations

import numpy as np


def _k(gf) -> float:
    """Base wave number: one full wave per ``width_span`` cell-widths."""
    return 2.0 * np.pi / max(gf.width_span, 1.0)


def _hash01(n, salt: int = 0):
    """Deterministic integer hash to floats in [0, 1). ``n`` may be an array.

    The same trick starfield uses, packaged: cheap, seedable, and stable across
    frames — which is how the stateless patterns give every column/blob/charge
    its own persistent personality without storing anything.
    """
    h = np.asarray(n, dtype=np.int64)
    h = (h * 73856093) ^ (np.int64(salt + 1) * 19349663)
    h = np.abs(h * 83492791 + 0x9E3779B9)
    return (h % 100003).astype(np.float32) / np.float32(100003.0)


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


# --------------------------------------------------------------------------- #
# R2a — six for free (all pure functions, no state)
# --------------------------------------------------------------------------- #

def rain(X, Y, t, gf):
    """Matrix-style rain: bright-headed streams with fading tails.

    Stateless: each cell-width column hashes to a persistent speed, phase and
    tail length, and the head position is just ``(offset + t*speed) mod span``.
    Two independent layers let a column carry more than one drop, and a coarse
    time-quantised hash adds the glyph-shimmer feel without any glyph channel.
    The density control doubles as tail length.
    """
    H = gf.height_span
    # Everything per-column is computed on a 1-D row and broadcast against Y —
    # same maths as hashing the full grid, at a fraction of the cost.
    xs = X[0, :]
    col = np.floor(xs).astype(np.int64)
    out = np.zeros_like(X, dtype=np.float32)
    for salt, weight in ((11, 1.0), (29, 0.72)):
        u_speed = _hash01(col, salt)
        u_off = _hash01(col, salt + 1)
        u_tail = _hash01(col, salt + 2)
        speed = H * (0.22 + 0.42 * u_speed)          # full drop in ~2.4–4.5 s
        tail = H * (0.16 + 0.30 * u_tail)
        span = H + tail + 2.0
        head = ((u_off * span * 7.0 + t * speed) % span)[None, :]
        d = head - Y                                  # 0 at the head, grows up-tail
        tail = tail[None, :]
        fall = np.clip(1.0 - d / np.maximum(tail, 1e-3), 0.0, 1.0) ** 1.2
        # Lift the whole tail above the density crush so it fades to the
        # threshold at its end instead of vanishing halfway up.
        body = np.where((d >= 0.0) & (d <= tail), 0.45 + 0.55 * fall, 0.0)
        glint = 0.22 * np.exp(-(d / 0.6) ** 2)        # hot leading character
        out = np.maximum(out, np.clip(body + glint, 0.0, 1.0) * weight)
    row = np.floor(Y[:, 0]).astype(np.int64)
    shimmer = 0.82 + 0.18 * _hash01(col[None, :] * 1543 + row[:, None] * 2029
                                    + np.int64(np.floor(t * 6.0)), 5)
    return out * shimmer


def lava(X, Y, t, gf):
    """Lava lamp: slow metaball blobs that merge and split.

    Seven blobs on closed-form orbits; summing their gaussian fields and soft-
    thresholding the total is what makes close blobs neck together and pull
    apart — the metaball trick, with no simulation.
    """
    W, H = gf.width_span, gf.height_span
    field = np.zeros_like(X, dtype=np.float32)
    for i in range(7):
        sx = 0.043 + 0.050 * float(_hash01(i, 1))
        sy = 0.031 + 0.042 * float(_hash01(i, 2))
        px = 6.2832 * float(_hash01(i, 3))
        py = 6.2832 * float(_hash01(i, 4))
        bx = W * (0.5 + 0.34 * np.sin(t * sx + px))
        by = H * (0.5 + 0.38 * np.sin(t * sy + py))
        rad = W * (0.075 + 0.070 * float(_hash01(i, 6)))
        d2 = (X - bx) ** 2 + (Y - by) ** 2
        field += np.exp(-d2 / (rad * rad))
    m = np.clip((field - 0.50) * 1.6, 0.0, 1.0)       # inside-ness of a blob
    rim = 4.0 * m * (1.0 - m)                         # peaks at the boundary
    return np.clip(0.60 * m ** 1.8 + 0.75 * rim, 0.0, 1.0)   # lit shell look


def tunnel(X, Y, t, gf):
    """Hypnotic depth tunnel: rings born deep in the centre race outward.

    The ``1/r`` term is the whole illusion — equal ring spacing in *depth*
    compresses toward the centre on screen. A slight barrel roll and a
    wandering vanishing point keep it from feeling mechanical, and distance fog
    dims the far end so the centre shimmers instead of screaming.
    """
    p = gf.phase
    W, H = gf.width_span, gf.height_span
    cx = W * (0.5 + 0.08 * np.sin(t * 0.11 + p[0]))
    cy = H * (0.5 + 0.08 * np.cos(t * 0.09 + p[1]))
    dx, dy = X - cx, Y - cy
    r = np.sqrt(dx * dx + dy * dy) + 0.02 * W
    theta = np.arctan2(dy, dx)
    depth = (2.6 * W) / r
    wobble = 0.35 * np.sin(theta * 3.0 + t * 0.40 + p[3])
    band = np.tanh(2.8 * (np.sin(depth * 3.0 + t * 2.8 + wobble + p[2]) - 0.15))
    v = 0.5 + 0.5 * band                              # bold rings, soft edges
    fog = r / (r + 0.20 * W)                          # deep centre stays dim
    return v * np.minimum(0.45 + 0.75 * fog, 1.0)     # near rings reach full glow


def galaxy(X, Y, t, gf):
    """A rotating spiral galaxy: three log-spiral arms around a bright core.

    ``theta*arms - log(r)*twist`` is the classic self-similar spiral — the
    arms keep their shape at every radius. The whole thing turns slowly, a
    faint radial shimmer stands in for dust lanes, and an exponential envelope
    fades it into blackness before the screen edge.
    """
    p = gf.phase
    W, H = gf.width_span, gf.height_span
    cx = W * (0.5 + 0.05 * np.sin(t * 0.05 + p[0]))
    cy = H * (0.5 + 0.05 * np.cos(t * 0.04 + p[1]))
    dx, dy = X - cx, Y - cy
    r = np.sqrt(dx * dx + dy * dy) + 1e-3
    theta = np.arctan2(dy, dx)
    arms = np.sin(theta * 3.0 - np.log(r + 1.0) * 4.6 + t * 0.32 + p[2])
    env = np.exp(-r / (0.36 * W))
    core = np.exp(-((r / (0.05 * W)) ** 2))
    dust = 0.78 + 0.22 * np.sin(r * (_k(gf) * 7.0) - t * 0.22 + p[3])
    return np.clip(env * (0.24 + 1.15 * np.clip(arms, 0.0, 1.0) * dust)
                   + 1.15 * core, 0.0, 1.0)


def fireflies(X, Y, t, gf):
    """Drifting glowing points on Lissajous orbits, each twinkling to its own
    clock. Looks like a particle system; is eighteen closed-form orbits."""
    W, H = gf.width_span, gf.height_span
    out = np.zeros_like(X, dtype=np.float32)
    h, w = X.shape
    xs, ys = X[0, :], Y[:, 0]
    ix = (w - 1) / max(W, 1e-6)                       # array cells per cell-width
    iy = (h - 1) / max(H, 1e-6)
    R = 8.0                                           # glow support: e^-64/12 ~ 0
    for i in range(40):
        ax = 0.05 + 0.15 * float(_hash01(i, 11))
        ay = 0.05 + 0.15 * float(_hash01(i, 12))
        px = 6.2832 * float(_hash01(i, 13))
        py = 6.2832 * float(_hash01(i, 14))
        fx = W * (0.5 + 0.44 * np.sin(t * ax + px))
        fy = H * (0.5 + 0.44 * np.sin(t * ay + py))
        # Baseline sits above the density crush so every fly stays visible;
        # the twinkle breathes the halo instead of blinking the fly out.
        tw = 0.78 + 0.22 * np.sin(t * (0.7 + 1.5 * float(_hash01(i, 15)))
                                  + 6.2832 * float(_hash01(i, 16)))
        # Each fly only touches its own little window of the grid.
        i0, i1 = max(int((fx - R) * ix), 0), min(int((fx + R) * ix) + 2, w)
        j0, j1 = max(int((fy - R) * iy), 0), min(int((fy + R) * iy) + 2, h)
        if i0 >= i1 or j0 >= j1:
            continue
        d2 = ((ys[j0:j1] - fy) ** 2)[:, None] + ((xs[i0:i1] - fx) ** 2)[None, :]
        glow = np.exp(-d2 / 2.0) + 0.62 * np.exp(-d2 / 12.0)
        region = out[j0:j1, i0:i1]
        np.maximum(region, np.float32(tw) * glow, out=region)
    return np.clip(out, 0.0, 1.0)


def electric(X, Y, t, gf):
    """Homage to *Electric !* (JX Bardant, 1997): the electric field of a few
    wandering charges, drawn as equipotential bands that flow forever.

    The original computed the field once into a 256-colour image and animated
    it purely by rotating the hardware palette (``AnimatePalette``). Here the
    glyph ramp plays the palette: ``frac(V*bands + t*flow)`` sweeps the bands
    along the field lines — out of the negative charges, into the positive —
    and the dense shimmering rings right at each charge are the same aliasing
    the 1997 original had. Charges wander instead of re-seeding, since we can
    afford to recompute what a 486 could not.
    """
    W, H = gf.width_span, gf.height_span
    V = np.zeros_like(X, dtype=np.float32)
    for i in range(5):
        q = 1.0 if i % 2 == 0 else -1.0               # 3 positive, 2 negative
        sx = 0.020 + 0.030 * float(_hash01(i, 21))
        sy = 0.017 + 0.028 * float(_hash01(i, 22))
        px = 6.2832 * float(_hash01(i, 23))
        py = 6.2832 * float(_hash01(i, 24))
        cx = W * (0.5 + 0.36 * np.sin(t * sx + px))
        cy = H * (0.5 + 0.36 * np.sin(t * sy + py))
        r = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) + 1.2
        V += q * (0.16 * W) / r
    bands = (V * 2.6 + t * 0.55) % 1.0
    return bands * (0.30 + 0.70 * np.tanh(np.abs(V) * 1.1))


# Order defines the cycle order of the G key. dotfield stays first (default);
# the R2a batch follows the originals, electric as the finale.
PATTERNS = [
    ("dotfield", dotfield),
    ("plasma", plasma),
    ("ripples", ripples),
    ("flow", flow),
    ("starfield", starfield),
    ("rain", rain),
    ("lava", lava),
    ("tunnel", tunnel),
    ("galaxy", galaxy),
    ("fireflies", fireflies),
    ("electric", electric),
]
