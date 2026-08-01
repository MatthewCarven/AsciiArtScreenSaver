"""Allow `python -m asciiviz`."""

import sys

from .app import main

if __name__ == "__main__":
    sys.exit(main())
