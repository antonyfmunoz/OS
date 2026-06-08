"""Backward-compat shim — canonical module is command_router.py.

All new code should import from substrate.workstation.command_router.
"""
from substrate.workstation.command_router import *  # noqa: F401,F403
