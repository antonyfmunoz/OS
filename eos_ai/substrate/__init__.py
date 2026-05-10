"""Compatibility shim — eos_ai.substrate moved to eos_ai.transport (Wave 4, 2026-05-10).

All imports transparently re-export from eos_ai.transport.
"""
from eos_ai.transport import *  # noqa: F401,F403
