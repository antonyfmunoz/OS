"""Session 1 launcher — starts UMH node daemon in the interactive desktop session.

Used by Task Scheduler (ONLOGON trigger) to run the daemon with
desktop access (Session 1) instead of as a Windows Service (Session 0).
Session 1 enables: screenshots, SendKeys, GUI automation.
"""
import sys
sys.path.insert(0, r"C:\dev\dev\OS")
from nodes.windows.umh_node.model_assets import configure_process_runtime_environment

run_root = configure_process_runtime_environment()
try:
    import os
    os.chdir(str(run_root))
except OSError:
    pass

from nodes.windows.umh_node.service import run_foreground
run_foreground()
