#!/usr/bin/env python3
"""Two-Point Discrimination Experiment Tool — entry point."""

import sys


def main() -> None:
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print(
            "Error: tkinter is required but not installed.\n"
            "On Ubuntu/Debian: sudo apt-get install python3-tk\n"
            "On macOS (Homebrew): brew install python-tk"
        )
        sys.exit(1)

    from gui import App

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
