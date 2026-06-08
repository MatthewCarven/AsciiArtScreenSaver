"""Application loop: window, input handling, and frame composition."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import numpy as np
import pygame

from . import palettes
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


class App:
    def __init__(self, opts):
        pygame.init()
        pygame.display.set_caption("ASCII Visualizer")

        self.project_dir = Path(__file__).resolve().parent.parent
        self.images_dir = self.project_dir / "images"
        self.captures_dir = self.project_dir / "captures"
        self.images_dir.mkdir(exist_ok=True)

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

        # Image state.
        self.images = self._scan_images()
        if not self.images:
            sample = self.images_dir / "sample_rings.png"
            make_sample_image(str(sample))
            self.images = self._scan_images()
        self.image_index = 0
        if opts.image:
            p = Path(opts.image)
            if p.exists():
                self.images.insert(0, p)
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
        self.ss_cycle_seconds = float(getattr(opts, "cycle_seconds", 20.0))
        self._ss_cycle_t = 0.0
        self._ss_mouse = None
        if self.screensaver:
            self.show_hud = False
            pygame.mouse.set_visible(False)
            if not self.fullscreen:
                self._toggle_fullscreen()

    # ------------------------------------------------------------------ #
    # Setup helpers
    # ------------------------------------------------------------------ #
    def _scan_images(self):
        return sorted(
            p for p in self.images_dir.iterdir()
            if p.is_file() and p.suffix.lower() in _IMAGE_EXTS
        )

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
            return True
        braille = palettes.is_braille(self.palette)
        data = load_image_fields(str(path), self.cols, self.rows,
                                 self.renderer.cell_aspect, braille)
        data["_want"] = want
        self._img_cache = data
        self._img_key = None  # invalidate rendered surface
        return True

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
                cg = (_GEN_LOW + (_GEN_HIGH - _GEN_LOW) * field[..., None])
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
        self.captures_dir.mkdir(exist_ok=True)
        name = time.strftime("ascii_%Y%m%d_%H%M%S.png")
        path = self.captures_dir / name
        pygame.image.save(self.screen, str(path))
        self._toast(f"saved captures/{name}")

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
        while running:
            dt = self.clock.tick(self.fps) / 1000.0
            if not self.paused:
                self.t += dt
            if self.screensaver and self.mode == "generative" \
                    and self.t - self._ss_cycle_t >= self.ss_cycle_seconds:
                self._ss_cycle_t = self.t
                self.gen.next_pattern()

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

        pygame.quit()


def build_parser():
    p = argparse.ArgumentParser(
        prog="asciiviz",
        description="ASCII Visualizer — generative dot-field + image-to-ASCII screensaver.",
    )
    p.add_argument("--image", help="path to an image to load on startup (switches to image mode)")
    p.add_argument("--video", help="path to a video file to play as ASCII (switches to video mode)")
    p.add_argument("--webcam", type=int, nargs="?", const=0,
                   help="capture from a webcam device index (default 0)")
    p.add_argument("--mode", choices=("generative", "image", "video"), default="generative")
    p.add_argument("--palette", choices=palettes.NAMES, default="dots")
    p.add_argument("--color", action="store_true", help="tint glyphs by source/brightness colour")
    p.add_argument("--font-size", type=int, default=16, dest="font_size",
                   help="cell font size in px (controls resolution)")
    p.add_argument("--density", type=float, default=0.6,
                   help="generative dot density, 0.05–1.0")
    p.add_argument("--screensaver", action="store_true",
                   help="fullscreen screensaver: hide cursor, auto-cycle patterns, exit on any input")
    p.add_argument("--cycle-seconds", type=float, default=20.0, dest="cycle_seconds",
                   help="seconds between automatic pattern changes in screensaver mode")
    p.add_argument("--fps", type=int, default=60)
    p.add_argument("--width", type=int, default=1100)
    p.add_argument("--height", type=int, default=700)
    return p


def main(argv=None):
    opts = build_parser().parse_args(argv)
    if opts.image:
        opts.mode = "image"
    if opts.video or opts.webcam is not None:
        opts.mode = "video"
    App(opts).run()


if __name__ == "__main__":
    main()
# --- asciiviz.app end ---
