"""UMH Workstation — local environment profile, session state, and boot sequencing.

Phase 77 adds identity-scoped workstation state: operator profiles,
device/environment registries, modes, sessions, resume summaries,
and a boot sequence that loads context without executing actions.
"""

from umh.workstation.boot_sequence import BootResult, run_boot_sequence
from umh.workstation.modes import ModeRegistry, WorkstationMode
from umh.workstation.operator_profile import ExecutionPreference, OperatorProfile
from umh.workstation.session_state import SessionState, get_session_store

__all__ = [
    "BootResult",
    "ExecutionPreference",
    "ModeRegistry",
    "OperatorProfile",
    "SessionState",
    "WorkstationMode",
    "get_session_store",
    "run_boot_sequence",
]
