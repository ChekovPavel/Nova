"""Allows Nova to be started with ``python -m nova`` after ``pip install -e .``."""

from nova.cli import main

if __name__ == "__main__":
    main()
