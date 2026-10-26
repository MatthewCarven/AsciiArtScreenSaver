"""Generative pattern functions for the idle screensaver.

Each pattern takes the physical coordinate grids ``X`` and ``Y`` (measured in
cell-widths, so motion looks isotropic regardless of palette sub-resolution),
the time ``t`` in seconds, and the owning :class:`GenerativeField` ``gf`` (for
its random ``phase`` array and span). It returns a brightness field in roughly
[0, 1]; ``GenerativeField`` applies the shared density/contrast shaping after.

Add a new pattern by writing a function with this signature and appending it to
``PATTERNS`` — it then becomes selectable at runtime (the G key).

Most patterns here are *pure* functions of ``(X, Y, t)`` — no memory between
frames — which is what makes pause free and the screensaver's throttle phase
harmless. The R2a batch (rain, lava, tunnel, galaxy, fireflies, electric) keeps
that contract by deriving all per-entity state (drop speeds, blob orbits,
charge paths) from integer hashes and closed-form orbits instead of simulation.

The exceptions are R2b's fire and life, which really are simulations. A
``PATTERNS`` entry may therefore also be a callable object with a ``reset()``
method; :class:`Simulation` is the base they share, and it keeps the two
promises above — pause freezes it, and the throttle only slows it down.

R2d's mandelbrot zoom is a pure function again: where the dive has got to is
worked out from ``t`` alone, so it too pauses and throttles for free.
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


# --------------------------------------------------------------------------- #
# R2b — the stateful pair (simulations with memory between frames)
# --------------------------------------------------------------------------- #

class Simulation:
    """Base for patterns that remember things between frames.

    :class:`GenerativeField` calls ``reset()`` whenever the grid is resized
    and whenever the pattern is switched to. State is also keyed by the
    field's shape, so a palette switch — which changes the sub-resolution
    without resizing anything — starts afresh too.

    The sim advances in fixed ticks of ``1 / rate`` seconds, and how many
    ticks are due is worked out from ``t`` alone, so pause (which freezes
    ``t``) freezes the sim for free. At most ``MAX_STEPS`` ticks run in one
    frame, and any beyond that are dropped rather than owed: at the
    screensaver's 2 fps throttle the sim runs proportionally slower instead of
    stalling or snowballing. The RNG is reseeded on every fresh start, so the
    same timestamps always give the same frames.

    Subclasses provide ``start(h, w, gf)``, ``step(stamp, gf)`` (one tick,
    ``stamp`` being the time it happened) and ``draw(t, gf)``.
    """

    MAX_STEPS = 6
    RATE = 10.0                     # ticks per second

    def __init__(self, seed: int):
        self.seed = seed
        self.reset()

    def reset(self):
        self.shape = None           # nothing until the next frame starts it
        self.steps = 0

    def rate(self, h, gf) -> float:
        return self.RATE

    def __call__(self, X, Y, t, gf):
        h, w = X.shape
        if self.shape != (h, w) or t < self._sim_t:
            self.reset()
            self.shape = (h, w)
            self._sim_t = t
            self._rng = np.random.default_rng(self.seed)
            self.start(h, w, gf)
        tick = 1.0 / self.rate(h, gf)
        due = int((t - self._sim_t) / tick)
        if due > self.MAX_STEPS:
            # Behind (throttled, or back from image mode): run the last few
            # ticks and let the rest go.
            stamps = [t - tick * k for k in range(self.MAX_STEPS - 1, -1, -1)]
            self._sim_t = t
        else:
            stamps = [self._sim_t + tick * (k + 1) for k in range(due)]
            self._sim_t += tick * due
        for stamp in stamps:
            self.steps += 1
            self.step(stamp, gf)
        return self.draw(t, gf)


class Fire(Simulation):
    """Doom fire — the PSX Doom title-screen effect (1995), as Fabien Sanglard
    wrote it up.

    A hot bottom row feeds it. Every tick each cell takes the heat of the cell
    below it, read from a random neighbour (the lick and lean of the flames,
    with Doom's slight leftward wind), minus a random cooling. The cooling is
    scaled to the field so flames reach about the same share of the screen at
    any size, and the tick rate scales with sub-resolution so they rise at the
    same on-screen speed in braille too. One departure from Doom: its coals
    are uniformly white-hot, which stands the fire up as an even wall, so here
    hotter and cooler stretches drift along the bottom row and the flames
    surge and slump in places.
    """

    RATE = 30.0                     # ticks per second at cell resolution
    REACH = 0.70                    # where unit heat runs out, as a share of height

    def rate(self, h, gf) -> float:
        return self.RATE * max(1.0, h / gf.rows)

    def start(self, h, w, gf):
        self.heat = np.zeros((h, w), dtype=np.float32)
        self._cols = np.arange(w)
        self._u = (self._cols * (2.0 * np.pi / w)).astype(np.float32)
        # Half the ticks cool by this much, so heat runs out REACH * h up.
        self._cool = np.float32(2.0 / (self.REACH * h))
        self._stoke(self._sim_t, gf)

    def _stoke(self, stamp, gf):
        """The coals: two slow waves beating against each other along the
        bottom row. Peaks run past 1.0 for a white-hot core; the field is
        clipped later."""
        p = gf.phase
        self.heat[-1] = 0.90 + 0.25 * (np.sin(self._u * 5.0 + stamp * 0.9 + p[0])
                                       * np.sin(self._u * 9.0 - stamp * 0.6 + p[1]))

    def step(self, stamp, gf):
        self._stoke(stamp, gf)
        h, w = self.heat.shape
        if h < 2:
            return
        r = self._rng.integers(0, 4, size=(h - 1, w), dtype=np.int8)
        src = (self._cols + r - 1) % w
        below = np.take_along_axis(self.heat[1:], src, axis=1)
        self.heat[:-1] = np.maximum(below - (r & 1) * self._cool, 0.0)

    def draw(self, t, gf):
        # Lift any heat above the density crush, so the ragged tips — the
        # flicker is all up there — fade to the threshold instead of hiding.
        return np.where(self.heat > 0.0, 0.42 + 0.58 * self.heat, 0.0)


def life_step(alive):
    """One generation of Conway's Life (B3/S23) on a torus."""
    a = alive.astype(np.uint8)
    v = a + np.roll(a, 1, axis=0) + np.roll(a, -1, axis=0)
    n = v + np.roll(v, 1, axis=1) + np.roll(v, -1, axis=1) - a
    return (n == 3) | (alive & (n == 2))


class Life(Simulation):
    """Conway's Life with soft decay trails.

    Live cells are full brightness; a cell that dies glows on and fades, which
    turns gliders into comets and oscillators into soft pulses. The fade runs
    on ``t``, not on generations, so it stays smooth at 60 fps even though the
    board only changes ten times a second. Left alone, Life settles into still
    lifes and blinkers within a few thousand generations, so every few seconds
    a patch of fresh soup lands somewhere and stirs it up again.
    """

    RATE = 10.0                     # generations per second
    FILL = 0.30                     # share of cells alive in fresh soup
    TRAIL = 1.4                     # seconds for a dead cell's glow to fall by 1/e
    SPLASH_EVERY = 40               # generations between fresh-soup patches

    def start(self, h, w, gf):
        self.alive = self._rng.random((h, w)) < self.FILL
        self.seen = np.full((h, w), -np.inf)     # when each cell was last alive

    def step(self, stamp, gf):
        self.alive = life_step(self.alive)
        if self.steps % self.SPLASH_EVERY == 0:
            h, w = self.alive.shape
            ph, pw = max(3, h // 5), max(3, w // 6)
            y = int(self._rng.integers(0, max(1, h - ph + 1)))
            x = int(self._rng.integers(0, max(1, w - pw + 1)))
            patch = self.alive[y:y + ph, x:x + pw]
            patch |= self._rng.random(patch.shape) < self.FILL
        self.seen[self.alive] = stamp

    def draw(self, t, gf):
        glow = 0.85 * np.exp((self.seen - t) / self.TRAIL)
        return np.where(self.alive, 1.0, glow).astype(np.float32)


# --------------------------------------------------------------------------- #
# R2d — the zoom (a pure function again, and the heaviest per frame)
# --------------------------------------------------------------------------- #

# Misiurewicz points M(k, p), found by Newton's method on z_{k+p}(c) = z_k(c):
# the critical orbit lands on a repelling cycle after k steps. Such a point is
# on the boundary, and the set around it is self-similar all the way down, so
# a dive there never opens onto flat inside or flat outside. A point picked by
# eye isn't safe: the much-zoomed Seahorse Valley spot -0.743643887037151 +
# 0.131825904205330i is solid minibrot by 1e-7.
_ZOOM_TARGETS = (
    complex(-0.79578504006194961, 0.17210759073845566),    # M(18,4) Seahorse Valley
    complex(-0.035853604601623207, 0.65513747474659378),   # M(16,4) triple-spiral valley
    complex(0.38901616834394992, 0.10493292907959523),     # M(10,2) Elephant Valley
    complex(0.0, 1.0),                                     # M(2,2) c = i, a three-way fork
    complex(-1.5436890126920764, 0.0),                     # M(3,1) out on the antenna
)
_ZOOM_CYCLE = 80.0          # seconds per dive, fades included
_ZOOM_EASE = 4.0            # seconds to get up to speed from the whole-set view
_ZOOM_FADE = 1.5            # fade out at the bottom, fade back in at the top
_ZOOM_TOP = 3.0             # view height (short side of the screen) at the top...
_ZOOM_BOTTOM = 1e-12        # ...and at the reset, a decade before float64 shows
_ZOOM_HOME = complex(-0.6, 0.0)   # centre of the whole-set view
_ZOOM_BAIL = 64.0           # escape radius
_ZOOM_CHECK = 6             # iterations between escape checks: 64**(2**6) squared
                            # is still under float64's limit, so nothing overflows
_ZOOM_SOLID = 40.0          # escape counts past the frame's fastest where the
                            # bands begin to merge into solid set
_ZOOM_FLOW = 0.2            # band cycles per second, flowing in toward the set


def _zoom_view(t):
    """Where the dive is at time ``t``: ``(centre, height, fade, depth)``.

    Each cycle starts on the whole set and dives at constant speed in
    log(height) into the next target, easing in over the first few seconds.
    ``height`` is the view's short side in the complex plane, ``depth`` the
    decades dived so far. The view pans in as it zooms (the target's offset
    shrinks as height**1.5), so the target reaches mid-screen within the first
    couple of decades. The reset at the bottom falls inside a fade to black.
    """
    lap = np.floor(t / _ZOOM_CYCLE)
    tau = t - lap * _ZOOM_CYCLE
    target = _ZOOM_TARGETS[int(lap) % len(_ZOOM_TARGETS)]
    rate = np.log(_ZOOM_TOP / _ZOOM_BOTTOM) / (_ZOOM_CYCLE - 0.5 * _ZOOM_EASE)
    if tau < _ZOOM_EASE:
        dive = rate * tau * tau / (2.0 * _ZOOM_EASE)
    else:
        dive = rate * (tau - 0.5 * _ZOOM_EASE)
    height = _ZOOM_TOP * np.exp(-dive)
    centre = target + (_ZOOM_HOME - target) * (height / _ZOOM_TOP) ** 1.5
    fade = min(1.0, tau / _ZOOM_FADE, (_ZOOM_CYCLE - tau) / _ZOOM_FADE)
    return centre, height, fade, dive / np.log(10.0)


def _escape(c, cap):
    """Smooth escape count of each point of the 1-D complex array ``c``.

    ``inf`` where a point hasn't escaped by the time the budget runs out.
    Escaped points are dropped from the working arrays as they go, so a
    frame costs what its slowest points need, not ``cap`` times every point.
    Escape is only checked every ``_ZOOM_CHECK`` iterations, which is fine:
    ``n - log2(log|z_n|)`` barely changes once ``|z|`` is large, so it reads
    the same a few iterations late.

    ``cap`` rises with depth, but the working budget is set by the frame
    itself: anything still going ``2 * _ZOOM_SOLID`` iterations after the
    first escapes would be drawn as solid set anyway, so it stops there.
    """
    mu = np.full(c.shape, np.inf)
    idx = np.arange(c.size)
    z, cc = c.copy(), c.copy()
    n, budget = 1, cap
    while n < budget and idx.size:
        steps = min(_ZOOM_CHECK, budget - n)
        for _ in range(steps):
            np.square(z, out=z)
            z += cc
        n += steps
        m2 = z.real * z.real + z.imag * z.imag
        out = m2 > _ZOOM_BAIL * _ZOOM_BAIL
        if out.any():
            if budget == cap:
                budget = min(cap, n + int(2 * _ZOOM_SOLID) + _ZOOM_CHECK)
            mu[idx[out]] = n + 1 - np.log2(0.5 * np.log(m2[out]))
            keep = ~out
            idx, z, cc = idx[keep], z[keep], cc[keep]
    return mu


def _upsample(a, h, w):
    """Bilinear resize of a 2-D array to ``(h, w)``, corners kept on corners
    (the way ``np.linspace`` grids line up across resolutions)."""
    def axis(n_in, n_out):
        f = np.linspace(0.0, n_in - 1.0, n_out)
        i0 = np.minimum(f.astype(np.intp), max(n_in - 2, 0))
        return i0, np.minimum(i0 + 1, n_in - 1), f - i0
    r0, r1, fy = axis(a.shape[0], h)
    c0, c1, fx = axis(a.shape[1], w)
    a = a[r0] * (1.0 - fy)[:, None] + a[r1] * fy[:, None]
    return a[:, c0] * (1.0 - fx) + a[:, c1] * fx


def mandelbrot(X, Y, t, gf):
    """An endless Mandelbrot zoom: dive after dive into the boundary.

    Escape time with smooth colouring, drawn as contour bands. A pixel's
    smooth escape count is taken relative to the frame's fastest escape, so
    the picture reads the same at every depth, and bands are spaced by
    octaves of it: wide sweeping equipotentials out in the open, merging
    into a solid set near the boundary, where finer bands would only
    alias. The bands drift slowly inward, palette-cycling style.

    Braille asks for 2x4 samples a cell, and full-screen that can't hold
    60 fps (WORKLOG 2026-10-26), so this computes one sample per cell and
    interpolates up. The bands are smooth, so braille still gets sub-cell
    edges from the threshold.
    """
    centre, height, fade, depth = _zoom_view(t)
    h, w = X.shape
    rows, cols = min(h, gf.rows), min(w, gf.cols)
    xs = np.linspace(float(X[0, 0]), float(X[0, -1]), cols)
    ys = np.linspace(float(Y[0, 0]), float(Y[-1, 0]), rows)
    W, H = gf.width_span, gf.height_span
    scale = height / max(min(W, H), 1e-9)
    c = centre + scale * ((xs - 0.5 * W)[None, :] + 1j * (0.5 * H - ys)[:, None])
    mu = _escape(c.ravel(), int(100 + 20 * depth)).reshape(rows, cols)
    out = np.isfinite(mu)
    d = np.where(out, mu - (mu[out].min() if out.any() else 0.0), 2.0 * _ZOOM_SOLID)
    bands = 0.5 + 0.5 * np.cos(2.0 * np.pi * (np.log2(1.0 + d) - _ZOOM_FLOW * t))
    solid = np.clip(d / _ZOOM_SOLID - 1.0, 0.0, 1.0)
    v = (bands + (1.0 - bands) * solid) * fade
    if (rows, cols) != (h, w):
        v = _upsample(v, h, w)
    return v.astype(np.float32)


# Order defines the cycle order of the G key. dotfield stays first (default);
# the R2a batch follows the originals with electric as its finale, then R2b's
# stateful pair, then R2d's zoom. Stateful entries are prototypes: each
# GenerativeField runs its own copy.
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
    ("fire", Fire(seed=1993)),
    ("life", Life(seed=1970)),
    ("mandelbrot", mandelbrot),
]
