import json
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE = Path(__file__).parent.parent / 'eos_ai' / 'session_state.json'


class SessionState:

    # ─── Ambient state ────────────────────────────────────────────────────────
    # In-memory cache of the current market reality snapshot.
    # Refreshed every 30 minutes by orchestrator.refresh_ambient_state().
    # Consumed by CognitiveLoop PERCEIVE step to avoid recomputing on every call.

    _ambient_state: dict = {}

    @classmethod
    def set_ambient(cls, state: dict) -> None:
        """Store a fresh reality snapshot as ambient state."""
        cls._ambient_state = state or {}

    @classmethod
    def get_ambient(cls) -> dict:
        """Return the current ambient state. Empty dict if never set."""
        return cls._ambient_state

    @classmethod
    def save(
        cls,
        phase: str,
        last_completed: str,
        in_progress: str | None = None,
        files_modified: list[str] | None = None,
        next_steps: list[str] | None = None,
        context: dict | None = None,
    ) -> dict:
        state = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'phase': phase,
            'last_completed': last_completed,
            'in_progress': in_progress,
            'files_modified': files_modified or [],
            'next_steps': next_steps or [],
            'context': context or {},
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        return state

    @classmethod
    def load(cls) -> dict | None:
        if not STATE_FILE.exists():
            return None
        with open(STATE_FILE) as f:
            return json.load(f)

    @classmethod
    def get_resume_context(cls) -> str:
        state = cls.load()
        if not state:
            return 'No previous session state found.'
        lines = [
            f"Last session: {state['timestamp']}",
            f"Phase: {state['phase']}",
            f"Last completed: {state['last_completed']}",
            f"In progress: {state.get('in_progress') or 'nothing'}",
            f"Files modified: {', '.join(state.get('files_modified', [])) or 'none'}",
        ]
        if state.get('next_steps'):
            lines.append('Next steps:')
            for step in state['next_steps']:
                lines.append(f'  - {step}')
        if state.get('context'):
            lines.append(f"Context: {state['context']}")
        return '\n'.join(lines)

    @classmethod
    def clear(cls):
        if STATE_FILE.exists():
            STATE_FILE.unlink()

    @classmethod
    def update_progress(cls, last_completed: str, in_progress: str | None = None):
        """Load current state, update only last_completed and in_progress, preserve all other fields."""
        state = cls.load() or {}
        state['last_completed'] = last_completed
        state['in_progress'] = in_progress
        state['timestamp'] = datetime.now(timezone.utc).isoformat()
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
