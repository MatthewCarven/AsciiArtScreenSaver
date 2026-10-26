"""Application loop: window, input handling, and frame composition."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np
import pygame

from . import config, palettes
from .engine import (
    field_to_braille,
    field_to_ramp,
    load_image_fields,
    make_sample_image,
)
from .generative import GenerativeField
from .renderer import Renderer
from .video import VideoSource, VideoUnavailable

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
_REVEAL_SECONDS = 1.4
# HUD stays fully visible for _HUD_VISIBLE_SECONDS after the last input, then
# fades over _HUD_FADE_SECONDS. Any key press or mouse movement relights it.
_HUD_VISIBLE_SECONDS = 15.0
_HUD_FADE_SECONDS = 1.0
# Generative colour gradient (dark -> bright), used only when colour is on.
_GEN_LOW = np.array([36, 54, 110], dtype=np.float32)
_GEN_HIGH = np.array([196, 214, 255], dtype=np.float32)
# Per-pattern (low, high) overrides of that gradient. Deliberately minimal:
# R3's colour themes will absorb and generalise this.
_GEN_GRADIENTS = {
    "fire": (np.array([120, 22, 4], dtype=np.float32),       # ember
             np.array([255, 200, 90], dtype=np.float32)),
    "life": (np.array([14, 72, 30], dtype=np.float32),       # phosphor green
             np.array([150, 255, 160], dtype=np.float32)),
}


def _set_display_awake(enabled):
    """Keep the monitor awake while the screensaver runs (Windows only).

    Uses SetThreadExecutionState — the documented kernel32 call media players
    use to hold the display on — so the screensaver stays visible without you
    disabling Windows' "turn off display" power setting. The state is per-thread
    and Windows releases it automatically when the process exits, but we also
    clear it explicitly on a clean exit. No-op on non-Windows or if unavailable.
    """
    if os.name != "nt":
        return
    try:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_DISPLAY_REQUIRED = 0x00000002
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | (ES_DISPLAY_REQUIRED if enabled else 0))
    except Exception:
        pass


class App:
    def __init__(self, opts):
        pygame.init()
        pygame.display.set_caption("ASCII Visualizer")

        # The project folder from source; beside the .exe / .scr when built.
        self.project_dir = config.data_dir()
        self.captures_dir = self.project_dir / "captures"
        # images_dir points the image source at a folder of your own. That
        # folder is only ever read: not created, and no sample written into it.
        named = getattr(opts, "images_dir", None)
        self.own_images_dir = not named
        if named:
            self.images_dir = Path(os.path.expandvars(os.path.expanduser(named)))
        else:
            self.images_dir = self.project_dir / "images"
            try:
                self.images_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass            # no images then; never a reason not to start

        self.opts = opts
        self.windowed_size = (opts.width, opts.height)
        flags = pygame.RESIZABLE
        self.fullscreen = False
        self.screen = pygame.display.set_mode(self.windowed_size, flags)

        self.clock = pygame.time.Clock()
        self.renderer = Renderer(opts.font_size)

        self.mode = opts.mode
        self.palette = opts.palette
        self.color = opts.color
        self.paused = False
        self.show_hud = True
        self.fps = opts.fps
        self.last_activity = time.monotonic()
        self.video = None
        self._video_adv = 0.0

        self.t = 0.0
        self.gen = GenerativeField(1, 1, self.renderer.cell_aspect, opts.density)

        # Which patterns the screensaver rotates through (empty = all of them).
        self.cycle_names = list(getattr(opts, "cycle_patterns", None) or [])
        start_pattern = getattr(opts, "pattern", None) or (
            self.cycle_names[0] if self.cycle_names else None)
        if start_pattern:
            self.gen.set_pattern(start_pattern)

        # Image state.
        self._start_image = Path(opts.image) if opts.image else None
        self._rescan_images()
        if not self.images and self.own_images_dir:
            sample = self.images_dir / "sample_rings.png"
            try:
                make_sample_image(str(sample))
            except OSError:
                pass
            self._rescan_images()
        self.image_index = 0

        self._img_cache = None      # dict from load_image_fields
        self._img_key = None        # cache key for the rendered surface
        self._img_surface = None
        self._reveal_start = None
        self._randmap = None

        self.toast_text = ""
        self.toast_until = 0.0
        self.hud_font = pygame.font.SysFont("monospace,consolas,dejavusansmono", 14)

        self.cols, self.rows = 1, 1
        self._recompute_grid()
        if self.mode == "image":
            self._begin_reveal()
        if self.palette == "braille" and not self.renderer.braille_ok:
            self._toast("No braille-capable font found — install DejaVu Sans Mono")
        if getattr(opts, "video", None):
            self._open_video(opts.video)
        elif getattr(opts, "webcam", None) is not None:
            self._open_video(int(opts.webcam))

        self.screensaver = bool(getattr(opts, "screensaver", False))
        self.keep_awake = bool(getattr(opts, "keep_display_awake", False))
        self.ss_cycle_seconds = float(getattr(opts, "cycle_seconds", 20.0))
        self.cycle_content = getattr(opts, "cycle_content", "mixed")
        self.ss_idle_fps = max(1, int(getattr(opts, "idle_fps", 2)))
        self._ss_full = float(getattr(opts, "full_minutes", 5.0)) * 60.0
        self._ss_throttle = float(getattr(opts, "throttle_minutes", 5.0)) * 60.0
        self._ss_cycle_t = 0.0
        # The slideshow's place in self.images: the next one it will show.
        self._ss_image_pos = self.image_index + 1 if self.mode == "image" else 0
        self._ss_mouse = None
        if self.screensaver:
            self.show_hud = False
            pygame.mouse.set_visible(False)
            if not self.fullscreen:
                self._toggle_fullscreen()
            if self.cycle_content == "images" and self.mode == "generative":
                self._ss_next_image()   # a slideshow opens on a picture, if any

        if not self.own_images_dir and not self.images_dir.is_dir():
            self._toast(f"images_dir: no such folder: {self.images_dir}", seconds=6.0)

        # Where settings came from, and anything wrong with them. Surfaced in
        # the HUD because the screensaver has no console to print to.
        self.config_path = getattr(opts, "config_path", None)
        problems = list(getattr(opts, "config_problems", None) or [])
        if problems:
            extra = f" (+{len(problems) - 1} more)" if len(problems) > 1 else ""
            self._toast(f"config: {problems[0]}{extra}", seconds=6.0)

    # ------------------------------------------------------------------ #
    # Setup helpers
    # ------------------------------------------------------------------ #
    def _scan_images(self):
        try:
            if not self.images_dir.is_dir():
                return []
            return sorted(
                p for p in self.images_dir.iterdir()
                if p.is_file() and p.suffix.lower() in _IMAGE_EXTS
            )
        except OSError:
            return []           # a share or drive that's gone away: no images

    def _rescan_images(self):
        """Re-read the folder, so files dropped in since join and deleted
        ones leave. ``--image`` stays at the front while it exists."""
        images = self._scan_images()
        if self._start_image is not None and self._start_image.exists():
            images.insert(0, self._start_image)
        self.images = images

    def _recompute_grid(self):
        w, h = self.screen.get_size()
        self.cols, self.rows = self.renderer.grid_size(w, h)
        self.gen.set_dims(self.cols, self.rows, self.renderer.cell_aspect)
        self._randmap = np.random.default_rng(99).random((self.rows, self.cols)).astype(np.float32)
        self._img_cache = None       # force reload at new grid size
        self._img_key = None

    def _toast(self, text, seconds=2.5):
        self.toast_text = text
        self.toast_until = time.monotonic() + seconds

    # ------------------------------------------------------------------ #
    # Image handling
    # ------------------------------------------------------------------ #
    def _current_image_path(self):
        if not self.images:
            return None
        return self.images[self.image_index % len(self.images)]

    def _ensure_image_loaded(self):
        path = self._current_image_path()
        if path is None:
            return False
        want = (str(path), self.palette, self.cols, self.rows)
        if self._img_cache is not None and self._img_cache.get("_want") == want:
            return not self._img_cache.get("_failed")
        braille = palettes.is_braille(self.palette)
        try:
            data = load_image_fields(str(path), self.cols, self.rows,
                                     self.renderer.cell_aspect, braille)
        except Exception as exc:
            # Corrupt, deleted, or still being copied into a watched folder.
            # Remember the failure, so it isn't retried every frame, and let
            # the caller draw a pattern: never a crash, never a black screen.
            data = {"_failed": True}
            self._toast(f"couldn't load {path.name}: {exc}", seconds=6.0)
        data["_want"] = want
        self._img_cache = data
        self._img_key = None  # invalidate rendered surface
        return not data.get("_failed")

    def _begin_reveal(self):
        self._reveal_start = self.t

    def _reveal_mask(self):
        """Return an (rows, cols) mask in [0, 1], or None when fully revealed."""
        if self._reveal_start is None:
            return None
        p = (self.t - self._reveal_start) / _REVEAL_SECONDS
        if p >= 1.0:
            self._reveal_start = None
            return None
        mask = np.clip((p * 1.25 - self._randmap) * 6.0, 0.0, 1.0)
        return mask.astype(np.float32)

    # ------------------------------------------------------------------ #
    # Frame composition
    # ------------------------------------------------------------------ #
    def _draw_generative(self):
        if palettes.is_braille(self.palette):
            H, W = self.rows * 4, self.cols * 2
            field = self.gen.frame(self.t, H, W)
            rows, grid = field_to_braille(field, threshold=0.5)
            self.renderer.blit_grid_mono(self.screen, grid,
                                         font=self.renderer.braille_font)
        else:
            field = self.gen.frame(self.t, self.rows, self.cols)
            ramp = palettes.ramp_string(self.palette)
            rows, grid = field_to_ramp(field, ramp)
            if self.color:
                low, high = _GEN_GRADIENTS.get(self.gen.pattern_name,
                                               (_GEN_LOW, _GEN_HIGH))
                cg = (low + (high - low) * field[..., None])
                cg = cg.astype(np.uint8)
                self.renderer.blit_grid_color(self.screen, grid, cg)
            else:
                self.renderer.blit_rows_mono(self.screen, rows)

    def _build_image_surface(self, mask):
        data = self._img_cache
        braille = data["kind"] == "braille"
        field = data["field"]
        if mask is not None:
            if braille:
                m = np.repeat(np.repeat(mask, 4, axis=0), 2, axis=1)
                field = field * m
            else:
                field = field * mask

        if braille:
            rows, grid = field_to_braille(field, dither=True)
        else:
            rows, grid = field_to_ramp(field, palettes.ramp_string(self.palette))

        cw, ch = self.renderer.cell_w, self.renderer.cell_h
        surf = pygame.Surface((self.cols * cw, self.rows * ch))
        surf.fill(self.renderer.bg)
        if self.color:
            font = self.renderer.braille_font if braille else self.renderer.mono
            self.renderer.blit_grid_color(surf, grid, data["color"], font=font)
        elif braille:
            self.renderer.blit_grid_mono(surf, grid, font=self.renderer.braille_font)
        else:
            self.renderer.blit_rows_mono(surf, rows)
        return surf

    def _draw_image(self):
        if not self._ensure_image_loaded():
            self._draw_generative()
            return
        mask = self._reveal_mask()
        revealing = mask is not None
        key = (self._img_cache.get("_want"), self.color,
               self.renderer.font_size,
               int((self.t - (self._reveal_start or self.t)) * 30) if revealing else "done")
        if revealing or self._img_surface is None or key != self._img_key:
            self._img_surface = self._build_image_surface(mask)
            self._img_key = key
        self.screen.blit(self._img_surface, (0, 0))

    # ------------------------------------------------------------------ #
    # Video / webcam
    # ------------------------------------------------------------------ #
    def _open_video(self, source):
        try:
            if self.video is not None:
                self.video.release()
            self.video = VideoSource(source)
            self.mode = "video"
            self._video_adv = self.t
            self._toast(f"video: {self.video.label}")
        except VideoUnavailable as exc:
            self.video = None
            self.mode = "generative"
            self._toast(str(exc))

    def _stop_video(self):
        if self.video is not None:
            self.video.release()
            self.video = None

    def _draw_video(self):
        if self.video is None:
            self._draw_generative()
            return
        advance = (self.t - self._video_adv) >= self.video.frame_interval
        if advance:
            self._video_adv = self.t
        braille = palettes.is_braille(self.palette)
        data = self.video.fields(self.cols, self.rows, self.renderer.cell_aspect,
                                 braille, advance=advance)
        if data is None:
            self._toast("video stream ended")
            self._stop_video()
            self.mode = "generative"
            self._draw_generative()
            return
        field = data["field"]
        if braille:
            _, grid = field_to_braille(field, dither=True)
            if self.color:
                self.renderer.blit_grid_color(self.screen, grid, data["color"],
                                              font=self.renderer.braille_font)
            else:
                self.renderer.blit_grid_mono(self.screen, grid,
                                             font=self.renderer.braille_font)
        else:
            rows, grid = field_to_ramp(field, palettes.ramp_string(self.palette))
            if self.color:
                self.renderer.blit_grid_color(self.screen, grid, data["color"])
            else:
                self.renderer.blit_rows_mono(self.screen, rows)

    def _draw_hud(self):
        now = time.monotonic()
        idle = now - self.last_activity
        if idle >= _HUD_VISIBLE_SECONDS + _HUD_FADE_SECONDS:
            return  # fully faded out after the idle timeout
        fade = 1.0 if idle <= _HUD_VISIBLE_SECONDS else \
            1.0 - (idle - _HUD_VISIBLE_SECONDS) / _HUD_FADE_SECONDS
        lines = [
            f"mode: {self.mode}    palette: {self.palette}"
            f"    color: {'on' if self.color else 'off'}"
            f"    {'PAUSED' if self.paused else f'{self.clock.get_fps():4.0f} fps'}",
            f"grid: {self.cols}x{self.rows}    cell: {self.renderer.font_size}px",
        ]
        if self.mode == "image":
            p = self._current_image_path()
            lines.append(f"image: {p.name if p else '(none)'}  [{self.image_index % max(len(self.images),1) + 1}/{len(self.images)}]")
        elif self.mode == "video":
            lines.append(f"video: {self.video.label if self.video else '(none)'}")
        else:
            lines.append(f"pattern: {self.gen.pattern_name}")
        help_lines = [
            "[Tab] mode  [G] pattern  [V] webcam  [1/2/3] palette",
            "[C] color  [Space] pause  [N/P] image  [+/-] density",
            "[ [ / ] ] resolution  [F] fullscreen  [S] save  [H] HUD  [Esc/Q] quit",
        ]
        if self.config_path:
            help_lines.append(f"config: {self.config_path}")
        if now < self.toast_until and self.toast_text:
            help_lines.append(f">> {self.toast_text}")

        pad = 8
        rendered = [self.hud_font.render(t, True, (235, 238, 245)) for t in lines]
        rendered += [self.hud_font.render(t, True, (150, 156, 170)) for t in help_lines]
        w = max(s.get_width() for s in rendered) + pad * 2
        h = sum(s.get_height() for s in rendered) + pad * 2
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((10, 12, 18, 180))
        y = pad
        for s in rendered:
            panel.blit(s, (pad, y))
            y += s.get_height()
        if fade < 1.0:
            panel.fill((255, 255, 255, int(255 * fade)),
                       special_flags=pygame.BLEND_RGBA_MULT)
        self.screen.blit(panel, (10, 10))

    # ------------------------------------------------------------------ #
    # Input
    # ------------------------------------------------------------------ #
    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.windowed_size = self.screen.get_size()
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self._recompute_grid()

    def _set_palette(self, name):
        if name == "braille" and not self.renderer.braille_ok:
            self._toast("No braille-capable font found — install DejaVu Sans Mono")
            return
        self.palette = name
        self._img_cache = None
        self._img_key = None

    def _advance_pattern(self):
        """Next pattern in the screensaver rotation.

        Honours ``cycle_patterns`` when configured, so a big pattern library
        doesn't dilute the rotation. The G key deliberately still cycles *all*
        of them — the restriction is for unattended running, not for you.
        """
        names = self.cycle_names
        if not names:
            return self.gen.next_pattern()
        try:
            i = names.index(self.gen.pattern_name)
        except ValueError:
            i = -1
        name = names[(i + 1) % len(names)]
        self.gen.set_pattern(name)
        return name

    def _ss_cycle(self):
        """Move the screensaver on once the current pattern or image has had
        its ``cycle_seconds``.

        ``cycle_content`` says what comes next: "patterns" rotates patterns
        only (and an image you started on stays put, as it always has),
        "images" is a slideshow, and "mixed" alternates the two: a pattern, an
        image, the next pattern, the next image. With no image to show, the
        last two fall back to patterns, so the screen is never left black.
        """
        if not self.screensaver or self.t - self._ss_cycle_t < self.ss_cycle_seconds:
            return
        if self.mode == "generative" or (
                self.mode == "image" and self.cycle_content != "patterns"):
            self._ss_cycle_t = self.t
            if self.cycle_content == "images" or (
                    self.cycle_content == "mixed" and self.mode == "generative"):
                if self._ss_next_image():
                    return
            self._ss_next_pattern()

    def _ss_next_pattern(self):
        from_image = self.mode == "image"
        self.mode = "generative"
        before = self.gen.pattern_index
        self._advance_pattern()
        if from_image and self.gen.pattern_index == before:
            # Back onto the same pattern after an image (a one-pattern
            # rotation): a sim starts afresh, as it does when switched to.
            self.gen.restart()

    def _ss_next_image(self):
        """Show the slideshow's next image, entering with the dissolve reveal.
        False if there's none to show.

        At the end of each lap, and while there are no images at all, the
        folder is rescanned: pictures dropped in while the saver runs join the
        next lap. One that won't load (say, still being copied) is skipped.
        """
        on_screen = self._current_image_path() if self.mode == "image" else None
        if self._ss_image_pos >= len(self.images):
            self._rescan_images()
            self._ss_image_pos = 0
        if self._img_cache is not None and self._img_cache.get("_failed"):
            self._img_cache = None          # a lap on, give it another go
        while self._ss_image_pos < len(self.images):
            self.image_index = self._ss_image_pos
            self._ss_image_pos += 1
            if self._ensure_image_loaded():
                self.mode = "image"
                if self._current_image_path() != on_screen:
                    self._begin_reveal()    # a lone image isn't re-dissolved
                return True
        return False

    def _change_font(self, delta):
        self.renderer.set_font_size(self.renderer.font_size + delta)
        self._recompute_grid()

    def _next_image(self, step):
        if not self.images:
            return
        self.mode = "image"
        self.image_index = (self.image_index + step) % len(self.images)
        self._img_cache = None
        self._begin_reveal()

    def _save_capture(self):
        name = time.strftime("ascii_%Y%m%d_%H%M%S.png")
        path = self.captures_dir / name
        try:
            self.captures_dir.mkdir(parents=True, exist_ok=True)
            pygame.image.save(self.screen, str(path))
        except (OSError, pygame.error) as exc:
            self._toast(f"couldn't save {name}: {exc}", seconds=6.0)
            return None
        self._toast(f"saved captures/{name}")
        return path

    def _handle_key(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_q):
            return False
        elif key == pygame.K_TAB or key == pygame.K_m:
            if self.mode == "generative":
                self.mode = "image"
                self._begin_reveal()
            else:
                self.mode = "generative"
        elif key == pygame.K_1:
            self._set_palette("dots")
        elif key == pygame.K_2:
            self._set_palette("ramp")
        elif key == pygame.K_3:
            self._set_palette("braille")
        elif key == pygame.K_g:
            self.mode = "generative"
            self._toast(f"pattern: {self.gen.next_pattern()}")
        elif key == pygame.K_v:
            if self.mode == "video":
                self._stop_video()
                self.mode = "generative"
            else:
                self._open_video(0)
        elif key == pygame.K_c:
            self.color = not self.color
            self._img_key = None
        elif key == pygame.K_SPACE:
            self.paused = not self.paused
        elif key in (pygame.K_n, pygame.K_RIGHT):
            self._next_image(1)
        elif key in (pygame.K_p, pygame.K_LEFT):
            self._next_image(-1)
        elif key == pygame.K_LEFTBRACKET:
            self._change_font(-2)
        elif key == pygame.K_RIGHTBRACKET:
            self._change_font(2)
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.gen.density = min(1.0, self.gen.density + 0.05)
            self._toast(f"density {self.gen.density:.2f}")
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.gen.density = max(0.05, self.gen.density - 0.05)
            self._toast(f"density {self.gen.density:.2f}")
        elif key == pygame.K_f:
            self._toggle_fullscreen()
        elif key == pygame.K_s:
            self._save_capture()
        elif key == pygame.K_h:
            self.show_hud = not self.show_hud
        return True

    def _ss_fps(self) -> int:
        """Frame rate for this tick: full speed, then the throttled phase."""
        if self.screensaver and self.t >= self._ss_full:
            return self.ss_idle_fps
        return self.fps

    def _ss_finished(self) -> bool:
        """True once the full-speed and throttled phases are both over, so the
        process can bow out and hand control back to Windows.

        A negative ``throttle_minutes`` means "stay throttled, never exit" — the
        escape hatch for Windows versions that just relaunch the saver while the
        machine is still idle.
        """
        if not self.screensaver or self._ss_throttle < 0:
            return False
        return self.t >= self._ss_full + self._ss_throttle

    def _ss_should_exit(self, event):
        """In screensaver mode, any key, click, or real mouse movement exits."""
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            return True
        if event.type == pygame.MOUSEMOTION:
            if self._ss_mouse is None:
                self._ss_mouse = event.pos
                return False
            dx = event.pos[0] - self._ss_mouse[0]
            dy = event.pos[1] - self._ss_mouse[1]
            return (dx * dx + dy * dy) > 25  # ignore <=5px of jitter
        return False

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def run(self):
        running = True
        selftest_frames = int(os.environ.get("ASCIIVIZ_SELFTEST", "0"))
        frame = 0
        if self.keep_awake:
            _set_display_awake(True)
        while running:
            dt = self.clock.tick(self._ss_fps()) / 1000.0
            if not self.paused:
                self.t += dt
            if self._ss_finished():
                running = False
            self._ss_cycle()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif self.screensaver:
                    if self._ss_should_exit(event):
                        running = False
                elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                    self.screen = pygame.display.set_mode((event.w, event.h),
                                                          pygame.RESIZABLE)
                    self._recompute_grid()
                elif event.type == pygame.KEYDOWN:
                    self.last_activity = time.monotonic()
                    running = self._handle_key(event.key)
                elif event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
                    self.last_activity = time.monotonic()

            self.renderer.clear(self.screen)
            if self.mode != "video" and self.video is not None:
                self._stop_video()  # release the camera when leaving video mode
            if self.mode == "image":
                self._draw_image()
            elif self.mode == "video":
                self._draw_video()
            else:
                self._draw_generative()
            if self.show_hud:
                self._draw_hud()
            pygame.display.flip()

            frame += 1
            if selftest_frames and frame >= selftest_frames:
                running = False

        if self.keep_awake:
            _set_display_awake(False)
        pygame.quit()


def build_parser():
    """The CLI. Defaults come from :data:`asciiviz.config.DEFAULTS` so the
    command line and the config file can never drift apart."""
    D = config.DEFAULTS
    flag = argparse.BooleanOptionalAction   # gives --color *and* --no-color
    p = argparse.ArgumentParser(
        prog="asciiviz",
        description="ASCII Visualizer — generative dot-field + image-to-ASCII screensaver.",
    )
    p.add_argument("--config", metavar="PATH",
                   help="settings file to use (otherwise the usual locations are searched)")
    p.add_argument("--write-config", nargs="?", const="", metavar="PATH",
                   dest="write_config",
                   help="write current settings to a config file and exit "
                        "(no PATH = your per-user config location)")
    p.add_argument("--list-patterns", action="store_true", dest="list_patterns",
                   help="print the generative pattern names and exit")

    p.add_argument("--image", default=D["image"],
                   help="path to an image to load on startup (switches to image mode)")
    p.add_argument("--images-dir", default=D["images_dir"], dest="images_dir", metavar="FOLDER",
                   help="folder of images for N/P and the screensaver's slideshow "
                        "(default: the app's own images/)")
    p.add_argument("--video", default=D["video"],
                   help="path to a video file to play as ASCII (switches to video mode)")
    p.add_argument("--webcam", type=int, nargs="?", const=0, default=D["webcam"],
                   help="capture from a webcam device index (default 0)")
    p.add_argument("--mode", choices=("generative", "image", "video"), default=D["mode"])
    p.add_argument("--palette", choices=palettes.NAMES, default=D["palette"])
    p.add_argument("--pattern", default=D["pattern"],
                   help="generative pattern to start on (see --list-patterns)")
    p.add_argument("--color", action=flag, default=D["color"],
                   help="tint glyphs by source/brightness colour")
    p.add_argument("--font-size", type=int, default=D["font_size"], dest="font_size",
                   help="cell font size in px (controls resolution)")
    p.add_argument("--density", type=float, default=D["density"],
                   help="generative dot density, 0.05–1.0")
    p.add_argument("--screensaver", action=flag, default=D["screensaver"],
                   help="fullscreen screensaver: hide cursor, auto-cycle patterns and images, "
                        "exit on any input")
    p.add_argument("--cycle-seconds", type=float, default=D["cycle_seconds"], dest="cycle_seconds",
                   help="screensaver: seconds each pattern or image is shown")
    p.add_argument("--cycle-content", choices=config.CYCLE_CONTENT, default=D["cycle_content"],
                   dest="cycle_content",
                   help="screensaver: what it rotates. mixed (the default) alternates a "
                        "pattern and an image; with no images, patterns only")
    p.add_argument("--cycle-patterns", default=D["cycle_patterns"], dest="cycle_patterns",
                   type=lambda s: [x.strip() for x in s.split(",") if x.strip()] or None,
                   help="comma-separated patterns the screensaver rotates (default: all)")
    p.add_argument("--full-minutes", type=float, default=D["full_minutes"], dest="full_minutes",
                   help="screensaver: minutes of full-speed animation before throttling")
    p.add_argument("--throttle-minutes", type=float, default=D["throttle_minutes"],
                   dest="throttle_minutes",
                   help="screensaver: minutes at idle fps after that, before it exits "
                        "(negative = stay throttled and never exit)")
    p.add_argument("--idle-fps", type=int, default=D["idle_fps"], dest="idle_fps",
                   help="screensaver: frame rate during the throttle phase (keeps CPU low)")
    p.add_argument("--keep-display-awake", action=flag, default=D["keep_display_awake"],
                   dest="keep_display_awake",
                   help="screensaver holds the monitor on instead of letting Windows power it off")
    p.add_argument("--fps", type=int, default=D["fps"])
    p.add_argument("--width", type=int, default=D["width"])
    p.add_argument("--height", type=int, default=D["height"])
    return p


def _load_config(argv):
    """Find and read the config file. ``--config`` has to be read before the
    real parse, since it decides what the defaults are."""
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config")
    try:
        known, _ = pre.parse_known_args(argv)
    except SystemExit:          # e.g. "--config" with nothing after it
        return {}, None, ["could not read --config; using defaults"]
    return config.load(known.config)


def main(argv=None):
    values, cfg_path, problems = _load_config(argv)

    parser = build_parser()
    # Precedence falls out of ordering: defaults < config file < command line.
    # set_defaults runs first, so an explicitly-passed flag still wins.
    parser.set_defaults(**values)
    opts = parser.parse_args(argv)

    if opts.list_patterns:
        for name in config.pattern_names():
            print(name)
        return 0

    if opts.write_config is not None:
        target = Path(opts.write_config) if opts.write_config else config.user_config_path()
        current = {k: v for k, v in vars(opts).items() if k in config.SCHEMA}
        try:
            written = config.write_template(target, current)
        except OSError as exc:
            print(f"could not write {target}: {exc}", file=sys.stderr)
            return 1
        print(f"wrote {written}")
        return 0

    for msg in problems:
        print(f"config: {msg}", file=sys.stderr)
    opts.config_path = cfg_path
    opts.config_problems = problems

    if opts.image:
        opts.mode = "image"
    if opts.video or opts.webcam is not None:
        opts.mode = "video"
    App(opts).run()
    return 0


if __name__ == "__main__":
    main()
# --- asciiviz.app end ---
