#!/usr/bin/env python3
"""Entry point for the ASCII Visualizer.

Run from this folder:

    python main.py                  # generative dot-field idle mode
    python main.py --mode image     # start on an image
    python main.py --image path/to/photo.jpg
    python main.py --palette braille --color

See the README for the full list of runtime controls.
"""

from asciiviz.app import main

if __name__ == "__main__":
    main()
