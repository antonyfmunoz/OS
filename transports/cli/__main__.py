"""Allow `python -m transports.cli` invocation."""

import os
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_repo_root = _here.parent.parent
sys.path.insert(0, str(_repo_root))

from transports.cli.main import main

main()
