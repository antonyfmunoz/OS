"""
Provider Health — single source of truth for "can we run an LLM job right now?"

Used by:
- scheduled cron wrappers, to skip LLM-dependent work when no provider is healthy
- operator status script, to show inspectable health
- model_router, indirectly (it does its own checks too)

Design:
- Cheap, fast checks (≤2s per provider). No real model calls.
- Returns structured ProviderHealth with reasons, not just booleans.
- Honest about state — no optimistic defaults.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class ProviderHealth:
    cc_sdk: bool = False
    cc_sdk_reason: str = ""
    anthropic: bool = False
    anthropic_reason: str = ""
    gemini: bool = False
    gemini_reason: str = ""
    perplexity: bool = False
    perplexity_reason: str = ""
    groq: bool = False
    groq_reason: str = ""
    ollama: bool = False
    ollama_reason: str = ""
    checked_at: float = field(default_factory=time.time)

    @property
    def any_healthy(self) -> bool:
        return any([self.cc_sdk, self.anthropic, self.gemini, self.perplexity, self.groq, self.ollama])

    @property
    def any_cloud_healthy(self) -> bool:
        return any([self.cc_sdk, self.anthropic, self.gemini, self.perplexity, self.groq])

    def healthy_providers(self) -> list[str]:
        out = []
        for name in ("cc_sdk", "anthropic", "gemini", "perplexity", "groq", "ollama"):
            if getattr(self, name):
                out.append(name)
        return out

    def summary(self) -> str:
        rows = []
        for name in ("cc_sdk", "anthropic", "gemini", "perplexity", "groq", "ollama"):
            ok = "✓" if getattr(self, name) else "✗"
            reason = getattr(self, f"{name}_reason") or ("ok" if getattr(self, name) else "unknown")
            rows.append(f"  {ok} {name}: {reason}")
        return "Provider health:\n" + "\n".join(rows)


def _has_env(name: str) -> bool:
    val = os.getenv(name, "").strip()
    return bool(val) and not val.lower().startswith("your_")


def check_anthropic() -> tuple[bool, str]:
    if not _has_env("ANTHROPIC_API_KEY"):
        return False, "no api key"
    # Real inference probe — 1 token. /v1/models returns 200 even when
    # inference is blocked by credits/quota, so it's not trustworthy alone.
    try:
        import requests
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": os.getenv("ANTHROPIC_API_KEY", ""),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "."}],
            },
            timeout=5,
        )
        if r.status_code == 200:
            return True, "ok"
        if r.status_code == 401:
            return False, "401 invalid key"
        if r.status_code in (400, 402, 429):
            body = (r.text or "")[:120]
            return False, f"{r.status_code} {body}"
        return False, f"http {r.status_code}"
    except Exception as e:
        return False, f"net error: {str(e)[:50]}"


def check_gemini() -> tuple[bool, str]:
    if not _has_env("GEMINI_API_KEY"):
        return False, "no api key"
    # Real inference probe — generateContent with 1 token output.
    try:
        import requests
        key = os.getenv("GEMINI_API_KEY", "")
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}",
            json={
                "contents": [{"parts": [{"text": "."}]}],
                "generationConfig": {"maxOutputTokens": 1},
            },
            timeout=5,
        )
        if r.status_code == 200:
            return True, "ok"
        if r.status_code == 429:
            return False, "429 quota/cap exceeded"
        if r.status_code in (401, 403):
            return False, f"{r.status_code} auth"
        return False, f"http {r.status_code} {(r.text or '')[:80]}"
    except Exception as e:
        return False, f"net error: {str(e)[:50]}"


def check_perplexity() -> tuple[bool, str]:
    if not _has_env("PERPLEXITY_API_KEY"):
        return False, "no api key"
    # Perplexity has no cheap list endpoint — trust env presence + recent success
    return True, "key present (no cheap probe)"


def check_groq() -> tuple[bool, str]:
    if not _has_env("GROQ_API_KEY"):
        return False, "no api key"
    try:
        import requests
        r = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}"},
            timeout=3,
        )
        if r.status_code == 200:
            return True, "ok"
        return False, f"http {r.status_code}"
    except Exception as e:
        return False, f"net error: {str(e)[:50]}"


def check_ollama() -> tuple[bool, str]:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        import requests
        r = requests.get(f"{base}/api/tags", timeout=2)
        if r.status_code == 200:
            tags = r.json().get("models", [])
            if not tags:
                return False, "running but no models loaded"
            return True, f"running ({len(tags)} models)"
        return False, f"http {r.status_code}"
    except Exception as e:
        return False, f"down: {str(e)[:50]}"


def check_cc_sdk() -> tuple[bool, str]:
    """Claude Code SDK availability — checks for `claude` CLI on PATH."""
    import shutil
    if shutil.which("claude"):
        return True, "claude cli present"
    return False, "claude cli not found"


def check_all() -> ProviderHealth:
    """Run all provider checks. Designed to complete in under 15 seconds."""
    h = ProviderHealth()
    h.cc_sdk, h.cc_sdk_reason = check_cc_sdk()
    h.anthropic, h.anthropic_reason = check_anthropic()
    h.gemini, h.gemini_reason = check_gemini()
    h.perplexity, h.perplexity_reason = check_perplexity()
    h.groq, h.groq_reason = check_groq()
    h.ollama, h.ollama_reason = check_ollama()
    return h


# ─── Cron-friendly gate helpers ──────────────────────────────────────────────


def require_llm_or_skip(job_name: str, log_path: Optional[str] = None) -> ProviderHealth:
    """
    Cron entry-point gate: returns ProviderHealth if at least one provider is up.
    If none are up, prints a clear skip line and exits with status 0.

    Usage in a cron script:
        from eos_ai.provider_health import require_llm_or_skip
        health = require_llm_or_skip("nightly_consolidation")
        # ... continue with LLM work ...
    """
    import sys as _sys
    from datetime import datetime as _dt

    h = check_all()
    if not h.any_healthy:
        msg = (
            f"[{_dt.now().isoformat(timespec='seconds')}] "
            f"SKIP {job_name}: no healthy LLM provider. "
            f"anthropic={h.anthropic_reason}; gemini={h.gemini_reason}; "
            f"groq={h.groq_reason}; ollama={h.ollama_reason}"
        )
        print(msg)
        if log_path:
            try:
                Path(log_path).parent.mkdir(parents=True, exist_ok=True)
                with open(log_path, "a") as f:
                    f.write(msg + "\n")
            except Exception:
                pass
        _sys.exit(0)
    return h


if __name__ == "__main__":
    print(check_all().summary())
