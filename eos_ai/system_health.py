"""
EOS System Health Monitor
=========================
EOS monitors its own operational state.
Runs at: SessionStart, heartbeat every 30min,
after every gateway call.

This is Level 1 enforcement — Python layer.
Runs independent of Claude Code.
Works whether CC session is open or not.

Different from self_awareness.py which handles
business state changes (stage transitions, etc).
This module monitors SYSTEM health — providers,
chain connectivity, feedback loop, training data.

The system cannot operate autonomously
if it cannot monitor itself.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
PDT = ZoneInfo("America/Los_Angeles")


class EOSSystemHealth:
    """
    EOS knows its own operational state at all times.

    quality_level() — what intelligence is active
    chain_health() — is every layer connected
    feedback_health() — is the loop closing
    provider_status() — which providers work
    alert_if_degraded() — Discord if compromised
    training_data_health() — Stage 3 readiness
    """

    def __init__(self, ctx=None):
        self.ctx = ctx
        self._cached_quality: str | None = None

    def quality_level(self) -> str:
        """
        Current output quality based on provider availability flags.

        OPTIMAL — CC subprocess (Opus) available
        STANDARD — Anthropic SDK available
        DEGRADED — Gemini Flash available
        COMPROMISED — Ollama/gemma3:4b available
        OFFLINE — all providers down

        Does NOT make a live LLM call — checks availability only.
        Previous implementation called call_with_fallback("Say OK") which
        caused zombie processes when providers were down.
        """
        try:
            from eos_ai.model_router import (
                get_router,
                MODEL_REGISTRY,
                ModelProvider,
            )
            from eos_ai.cc_sdk import query_cc_sync

            # Check cc_sdk availability (cheapest check — just import)
            if query_cc_sync is not None:
                return "OPTIMAL"

            router = get_router()
            router._check_availability()

            # Check in priority order
            for cfg in MODEL_REGISTRY.values():
                if not cfg.available:
                    continue
                if cfg.provider == ModelProvider.ANTHROPIC:
                    return "STANDARD"
                if cfg.provider == ModelProvider.GEMINI:
                    return "DEGRADED"
                if cfg.provider in (ModelProvider.GROQ, ModelProvider.PERPLEXITY):
                    return "DEGRADED"
                if cfg.provider == ModelProvider.OLLAMA:
                    return "COMPROMISED"

            return "OFFLINE"

        except Exception:
            return "OFFLINE"

    def provider_status(self) -> dict:
        """Which intelligence providers are currently available."""
        import shutil

        infrastructure: dict = {}
        intelligence: dict = {}

        # CC subprocess
        infrastructure["cc_subprocess"] = bool(shutil.which("claude"))

        # Anthropic SDK
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        intelligence["anthropic_sdk"] = bool(
            api_key and not api_key.startswith("sk-ant-INVALID")
        )

        # Gemini
        intelligence["gemini"] = bool(os.getenv("GEMINI_API_KEY", ""))

        # Ollama
        try:
            import urllib.request

            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=2) as r:
                data = json.loads(r.read())
            models = [m["name"] for m in data.get("models", [])]
            intelligence["ollama"] = bool(models)
            intelligence["ollama_models"] = models
        except Exception:
            intelligence["ollama"] = False
            intelligence["ollama_models"] = []

        return {
            "infrastructure": infrastructure,
            "intelligence": intelligence,
        }

    def chain_health(self) -> dict:
        """Verify every layer of the chain is connected and responding."""
        health: dict = {}

        # Foundation — BIS context loads
        try:
            from eos_ai.context import load_context_from_env

            ctx = load_context_from_env()
            ventures = ctx.ventures or []
            health["foundation"] = {
                "status": "healthy",
                "ventures": len(ventures),
                "has_data": all(v.get("icp") and v.get("offer") for v in ventures),
            }
        except Exception as e:
            health["foundation"] = {
                "status": "broken",
                "error": str(e)[:100],
            }

        # Gateway singleton
        try:
            from eos_ai.gateway import get_gateway

            gw = get_gateway()
            health["gateway"] = {
                "status": "healthy",
                "singleton": gw is not None,
            }
        except Exception as e:
            health["gateway"] = {
                "status": "broken",
                "error": str(e)[:100],
            }

        # Model router — availability check only (no real LLM call)
        try:
            from eos_ai.model_router import get_router, MODEL_REGISTRY

            router = get_router()
            router._check_availability()
            available = [
                f"{c.provider.value}/{c.model_id}"
                for c in MODEL_REGISTRY.values()
                if c.available
            ]
            health["model_router"] = {
                "status": "healthy" if available else "no_providers",
                "available_models": available,
            }
        except Exception as e:
            health["model_router"] = {
                "status": "broken",
                "error": str(e)[:100],
            }

        # Memory / DB
        try:
            import psycopg2

            conn = psycopg2.connect(os.getenv("DATABASE_URL", ""), connect_timeout=3)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM interactions")
            count = cur.fetchone()[0]
            conn.close()
            health["memory"] = {
                "status": "healthy",
                "interactions": count,
            }
        except Exception as e:
            health["memory"] = {
                "status": "broken",
                "error": str(e)[:100],
            }

        # Notion
        token = os.getenv("NOTION_API_KEY", "")
        health["notion"] = {
            "status": "healthy" if token else "no_token",
            "has_token": bool(token),
        }

        # Overall chain status
        broken = [
            k
            for k, v in health.items()
            if isinstance(v, dict) and v.get("status") == "broken"
        ]
        health["overall"] = "healthy" if not broken else f"broken: {broken}"

        return health

    def feedback_health(self) -> dict:
        """
        Is the feedback loop closing?
        Interaction count, event types, outcome rate.
        """
        try:
            import psycopg2

            conn = psycopg2.connect(os.getenv("DATABASE_URL", ""), connect_timeout=3)
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM interactions")
            interactions = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM events WHERE event_type = %s",
                ("recommendation",),
            )
            recommendations = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM events WHERE event_type = %s",
                ("gateway:agent_task",),
            )
            gateway_tasks = cur.fetchone()[0]

            cur.execute("SELECT MAX(created_at) FROM interactions")
            last_interaction = cur.fetchone()[0]

            conn.close()

            return {
                "interactions": interactions,
                "recommendations": recommendations,
                "gateway_tasks": gateway_tasks,
                "last_interaction": str(last_interaction),
                "status": "healthy" if interactions > 100 else "building",
                "assessment": (
                    f"{interactions:,} interactions, "
                    f"{recommendations} recommendations, "
                    f"{gateway_tasks} gateway tasks"
                ),
            }

        except Exception as e:
            return {"status": "error", "error": str(e)[:100]}

    def training_data_health(self) -> dict:
        """
        Quality of captured data for Stage 3 LLM.
        Every interaction is a training example.
        """
        feedback = self.feedback_health()
        quality = self._cached_quality or self.quality_level()

        interaction_count = feedback.get("interactions", 0)

        quality_multipliers = {
            "OPTIMAL": 1.0,
            "STANDARD": 0.85,
            "DEGRADED": 0.60,
            "COMPROMISED": 0.35,
            "OFFLINE": 0.0,
        }
        multiplier = quality_multipliers.get(quality, 0.5)
        effective_examples = int(interaction_count * multiplier)

        return {
            "total_interactions": interaction_count,
            "quality_level": quality,
            "quality_multiplier": multiplier,
            "effective_training_examples": effective_examples,
            "stage3_readiness": (
                "building"
                if effective_examples < 10000
                else "approaching"
                if effective_examples < 50000
                else "ready"
            ),
            "assessment": (
                f"{effective_examples:,} effective training examples. "
                f"Quality: {quality}. Total: {interaction_count:,}."
            ),
        }

    def full_report(self) -> dict:
        """Complete system state report."""
        # Cache quality_level to avoid repeated LLM calls
        quality = self.quality_level()
        self._cached_quality = quality
        report = {
            "timestamp": datetime.now(PDT).isoformat(),
            "quality_level": quality,
            "provider_status": self.provider_status(),
            "chain_health": self.chain_health(),
            "feedback_health": self.feedback_health(),
            "training_data": self.training_data_health(),
        }
        self._cached_quality = None
        return report

    def alert_if_degraded(self, threshold: str = "COMPROMISED") -> bool:
        """
        Send alert if quality is at or below threshold.
        Returns True if alert was sent.
        """
        quality = self.quality_level()
        level_order = [
            "OPTIMAL",
            "STANDARD",
            "DEGRADED",
            "COMPROMISED",
            "OFFLINE",
        ]

        current_idx = level_order.index(quality) if quality in level_order else 4
        threshold_idx = level_order.index(threshold) if threshold in level_order else 3

        if current_idx < threshold_idx:
            return False

        providers = self.provider_status()
        intel = providers["intelligence"]
        working = [k for k, v in intel.items() if v and k != "ollama_models"]
        broken = [k for k, v in intel.items() if not v and k != "ollama_models"]

        message = (
            f"EOS Intelligence Degraded\n"
            f"Quality: {quality}\n"
            f"Working: {working}\n"
            f"Down: {broken}\n"
            f"Action: Fix API keys\n"
            f"Running on: {intel.get('ollama_models', ['?'])}"
        )

        try:
            from eos_ai.channel import get_channel_router

            router = get_channel_router()
            router.notify(message)
            logger.warning(f"[SystemHealth] Degradation alert sent: {quality}")
            return True
        except Exception as e:
            logger.error(f"[SystemHealth] Alert failed: {e}")

        # Fallback: audit log
        try:
            os.makedirs("/opt/OS/logs", exist_ok=True)
            with open("/opt/OS/logs/audit.log", "a") as f:
                f.write(
                    f"{time.strftime('%Y-%m-%dT%H:%M:%S')} "
                    f"SYSTEM_HEALTH_ALERT: {quality}\n"
                )
        except Exception:
            pass
        return False

    def system_check(self) -> str:
        """Human-readable system status for morning brief and SessionStart."""
        quality = self.quality_level()
        chain = self.chain_health()
        feedback = self.feedback_health()

        broken_links = [
            k
            for k, v in chain.items()
            if isinstance(v, dict) and v.get("status") == "broken"
        ]

        lines = [
            f"Intelligence: {quality}",
            f"Chain: {chain.get('overall', '?')}",
            f"Feedback: {feedback.get('status', '?')} "
            f"({feedback.get('interactions', 0):,} interactions)",
        ]

        if broken_links:
            lines.append(f"Broken: {broken_links}")

        if quality in ("COMPROMISED", "OFFLINE"):
            lines.append("Fix API keys immediately.")

        return "\n".join(lines)


def get_system_health(ctx=None) -> EOSSystemHealth:
    """Get configured system health instance."""
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS", "eos_ai", ".env"))
    return EOSSystemHealth(ctx)


if __name__ == "__main__":
    sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
    sh = get_system_health()
    print("=== EOS SYSTEM CHECK ===")
    print()
    print(sh.system_check())
    print()
    providers = sh.provider_status()
    print("=== Infrastructure ===")
    print(json.dumps(providers["infrastructure"], indent=2, default=str))
    print()
    print("=== Intelligence ===")
    print(json.dumps(providers["intelligence"], indent=2, default=str))
    print()
    report = sh.full_report()
    print("=== FULL REPORT ===")
    print(json.dumps(report, indent=2, default=str))
