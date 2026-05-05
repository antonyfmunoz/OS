"""Entry point for python3 -m umh.execution.approvals."""

import sys

sys.path.insert(0, "/opt/OS")

from umh.execution.approvals_cli import main

sys.exit(main())
