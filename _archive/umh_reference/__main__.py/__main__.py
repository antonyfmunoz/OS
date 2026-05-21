"""UMH CLI entry point — delegates to umh.interfaces.cli."""

import sys

from umh.interfaces.cli import main

if __name__ == "__main__":
    sys.exit(main())
