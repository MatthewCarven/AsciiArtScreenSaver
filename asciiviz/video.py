"""Live video / webcam input — a third ASCII source.

Wraps an OpenCV ``VideoCapture`` (a webcam device index, or a video file path)
and turns each frame into the same brightness + colour fields the image and
generative sources produce, so the renderer treats all three identically.

OpenCV is an optional dependency: importing this module still works without it,
and constructing a :class:`VideoSource` then raises :class:`VideoUnavailable`
with a helpful message instead of crashing the app.
"""

from __future__ import annotations

import numpy as np

try:
    import cv2
except Exception:  # pragma: no cover - optional dependency
    cv2 = None

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

from .engine import _placement


class VideoUnavailable(RuntimeError):
    """OpenCV is missing, or a capture source could not be opened."""


class VideoSource:
    """A webcam (integer device index) or a video file (path string)."""

    def __init__(self, source):
        if cv2 is None:
            raise VideoUnavailable(
                "OpenCV is not installed — run: pip install opencv-python"
            )
        if Image is None:
            raise VideoUnavailable("Pillow is not installed.")
        self.source = source
        self.is_webcam = isinstance(source, int)
        self.cap = cv2.VideoCapture(source)
        if not self.cap or not self.cap.isOpened():
            self.release()
            what = f"webcam #{source}" if self.is_webcam else f"video '{source}'"
            raise VideoUnavailable(f"could not open {what}")
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 0.0
        # Throttle file playback to its native fps; webcams stream as they grab.
        self.frame_interval = (1.0 / fps) if (fps and not self.is_webcam) else 0.0
        self.label = (
            f"webcam {source}" if self.is_webcam
            else str(source).replace("\\", "/").rsplit("/", 1)[-1]
        )
        self._last = None  # most recent RGB frame (numpy HxWx3)

    def _grab(self):
        ok, frame = self.cap.read()
        if not ok:
            if self.is_webcam:
                return None
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # loop video files
            ok, frame = self.cap.read()
            if not ok:
                return None
        if self.is_webcam:
            frame = cv2.flip(frame, 1)  # mirror so it reads like a selfie
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def fields(self, cols, rows, cell_aspect, braille, advance=True):
        """Return image-style fields for the current frame, or None if the
        stream has ended / has no frame yet."""
        if advance or self._last is None:
            rgb = self._grab()
            if rgb is not None:
                self._last = rgb
        if self._last is None:
            return None
        return fields_from_rgb(self._last, cols, rows, cell_aspect, braille)

    def release(self):
        cap = getattr(self, "cap", None)
        if cap is not None:
            cap.release()
        self.cap = None


def fields_from_rgb(rgb, cols, rows, cell_aspect, braille):
    """Fit an in-memory RGB frame into grid-sized brightness + colour fields.

    Mirrors :func:`asciiviz.engine.load_image_fields`, but works from a numpy
    array (what OpenCV hands us) rather than a file on disk.
    """
    img = Image.fromarray(rgb, "RGB")
    iw, ih = img.size
    ncols, nrows, ox, oy = _placement(iw, ih, cols, rows, cell_aspect)

    color_small = np.asarray(img.resize((ncols, nrows), Image.LANCZOS), dtype=np.uint8)
    color = np.zeros((rows, cols, 3), dtype=np.uint8)
    color[oy:oy + nrows, ox:ox + ncols] = color_small

    if braille:
        gray = img.convert("L").resize((ncols * 2, nrows * 4), Image.LANCZOS)
        gsmall = np.asarray(gray, dtype=np.float32) / 255.0
        field = np.zeros((rows * 4, cols * 2), dtype=np.float32)
        field[oy * 4:oy * 4 + nrows * 4, ox * 2:ox * 2 + ncols * 2] = gsmall
        kind = "braille"
    else:
        gray = img.convert("L").resize((ncols, nrows), Image.LANCZOS)
        gsmall = np.asarray(gray, dtype=np.float32) / 255.0
        field = np.zeros((rows, cols), dtype=np.float32)
        field[oy:oy + nrows, ox:ox + ncols] = gsmall
        kind = "simple"

    return {"kind": kind, "field": field, "color": color,
            "region": (ox, oy, ncols, nrows)}
