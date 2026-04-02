"""Allows Nova to be started with ``python -m nova``."""

import sys
import os

# Ensure the project root (parent of the nova package) is on sys.path so that
# main.py can be imported regardless of the working directory.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from main import main  # noqa: E402

if __name__ == "__main__":
    main()
