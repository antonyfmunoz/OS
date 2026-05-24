"""UMH Workstation — the front door to the Universal Mastery Hierarchy substrate."""

import os
import sys

UMH_ROOT = os.environ.get("UMH_ROOT", "/opt/OS")
sys.path.insert(0, UMH_ROOT)

__version__ = "0.1.0"
