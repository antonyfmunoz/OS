"""P4S31 Voice Convergence — the TS mirror matches the Python enum byte-for-byte.

The client and server can never disagree on voice error codes because
``cockpit/src/renderer/api/voiceErrorCodes.ts`` is codegen'd from
``VoiceErrorCode``. This asserts the generated file is up to date and mirrors the
9-code canon exactly.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

_TS = _ROOT / "cockpit" / "src" / "renderer" / "api" / "voiceErrorCodes.ts"


def test_ts_mirror_matches_python() -> None:
    # Regenerating must produce a byte-identical file (idempotent codegen).
    r = subprocess.run(
        [sys.executable, "scripts/gen_voice_error_codes_ts.py", "--check"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"TS mirror out of date:\n{r.stderr}"


def test_ts_has_nine_members() -> None:
    from substrate.execution.voice.error_codes import VoiceErrorCode

    text = _TS.read_text(encoding="utf-8")
    for c in VoiceErrorCode:
        assert f'{c.name}: "{c.value}"' in text, c.name
    # CONSENT_EXPIRED deliberately absent from the mirror too.
    assert "CONSENT_EXPIRED" not in text


def test_ts_values_uppercase() -> None:
    from substrate.execution.voice.error_codes import VoiceErrorCode

    text = _TS.read_text(encoding="utf-8")
    for c in VoiceErrorCode:
        # each rendered pair is UPPERCASE key === UPPERCASE value
        assert f'{c.name}: "{c.name}"' in text
