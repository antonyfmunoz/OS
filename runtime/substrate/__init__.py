"""Compatibility shim — runtime.substrate moved to runtime.transport (Wave 4, 2026-05-10).

All imports transparently re-export from runtime.transport.
"""
from runtime.transport import *  # noqa: F401,F403
