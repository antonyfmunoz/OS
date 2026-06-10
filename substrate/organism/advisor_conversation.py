"""Conversational advisor — multi-turn conversation with intent routing.

Wraps Advisor.handle_signal() with conversation history, intent classification,
response formatting, and suggested actions. Conversation-first: most messages
are natural conversation, not commands. Only explicit action keywords route
to structured handlers.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_CONVERSATIONS_PATH = os.path.join(
    os.environ.get("UMH_ROOT", "/opt/OS"),
    "data",
    "umh",
    "operator_experience",
    "dex_conversations.jsonl",
)


@dataclass
class AdvisorResponse:
    text: str
    conversation_id: str
    intent: str
    suggested_actions: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    spoken_text: str = ""  # Concise TTS-friendly version; empty means use text
    routing: dict[str, Any] = field(default_factory=dict)  # Voice route metadata

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    @property
    def display_text(self) -> str:
        """Alias for text — the full display version."""
        return self.text

    def to_api_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if not self.spoken_text:
            d.pop("spoken_text", None)
        if not self.routing:
            d.pop("routing", None)
        return d


class AdvisorConversation:
    """Multi-turn conversational advisor with intent routing."""

    _MAX_TURNS = 20
    _MAX_CONTEXT_CHARS = 2048
    _VOICE_TURN_CACHE_TTL_S = 600  # 10 minutes

    def __init__(self, advisor: Any, store: Any | None = None) -> None:
        self._advisor = advisor
        self._store = store
        self._histories: dict[str, list[dict[str, Any]]] = {}
        # voice_turn_id → (AdvisorResponse, timestamp) for idempotency
        self._voice_turn_cache: dict[str, tuple[AdvisorResponse, float]] = {}
        os.makedirs(os.path.dirname(_CONVERSATIONS_PATH), exist_ok=True)

    def converse(
        self,
        content: str,
        conversation_id: str = "",
        view_context: dict[str, Any] | None = None,
        source: str = "text",
        routing: dict[str, Any] | None = None,
        voice_turn_id: str = "",
    ) -> AdvisorResponse:
        # Idempotency guard: return cached response for duplicate voice turn IDs
        if voice_turn_id:
            self._clean_voice_turn_cache()
            cached = self._voice_turn_cache.get(voice_turn_id)
            if cached is not None:
                logger.info(
                    "Voice turn cache hit: %s — returning cached response",
                    voice_turn_id,
                )
                return cached[0]

        if not conversation_id:
            conversation_id = f"conv-{uuid.uuid4().hex[:12]}"

        if conversation_id not in self._histories:
            self._histories[conversation_id] = self._load_history(conversation_id)

        history = self._histories[conversation_id]

        from substrate.workstation.command_router import (
            CommandIntent,
            classify_intent,
        )

        # Deterministic identity handler — never let the LLM hallucinate system name
        from substrate.organism.system_identity import (
            get_identity_answer,
            is_identity_question,
        )

        if is_identity_question(content):
            identity_answer = get_identity_answer(
                content,
                voice=(source == "voice"),
            )
            if identity_answer:
                response = AdvisorResponse(
                    text=identity_answer,
                    conversation_id=conversation_id,
                    intent="identity",
                )
                response.conversation_id = conversation_id
                response.intent = "identity"
                self._save_turn(conversation_id, "operator", content, view_context)
                self._save_turn(
                    conversation_id,
                    "assistant",
                    response.text,
                    view_context,
                    intent="identity",
                )
                history.append({"role": "operator", "content": content})
                history.append({"role": "assistant", "content": response.text})
                if len(history) > self._MAX_TURNS * 2:
                    self._histories[conversation_id] = history[-self._MAX_TURNS * 2 :]
                return response

        intent = classify_intent(content)
        context_summary = self._build_context_summary(view_context)

        if intent == CommandIntent.UNKNOWN:
            response = self._handle_conversation(
                content,
                conversation_id,
                history,
                view_context,
                context_summary,
            )
        elif intent == CommandIntent.COUNCIL_REVIEW:
            response = self._handle_council(content, view_context, context_summary)
        elif intent == CommandIntent.CC_SEND:
            response = self._handle_cc_send(content, view_context)
        elif intent == CommandIntent.CC_CAPTURE:
            response = self._handle_cc_capture(view_context)
        elif intent == CommandIntent.DECOMPOSE_INTENT:
            response = self._handle_decompose(content, history)
        elif intent == CommandIntent.RESUME_QUERY:
            response = self._handle_resume()
        elif intent in (
            CommandIntent.STATUS_QUERY,
            CommandIntent.COMMAND_CENTER_QUERY,
        ):
            response = self._handle_status(content)
        elif intent == CommandIntent.COCKPIT_NAVIGATION:
            response = self._handle_navigation(content)
        elif intent == CommandIntent.EXPLAIN_CURRENT_VIEW:
            response = self._handle_explain_view(
                content,
                conversation_id,
                history,
                view_context,
                context_summary,
            )
        elif intent == CommandIntent.AGENT_QUERY:
            from substrate.organism.grounded_handlers import handle_grounded_agents

            response = handle_grounded_agents(content)
        elif intent == CommandIntent.BLOCKED_QUERY:
            from substrate.organism.grounded_handlers import handle_grounded_blocked

            response = handle_grounded_blocked(content)
        elif intent == CommandIntent.APPROVAL_QUERY:
            response = self._handle_approval_query()
        elif intent == CommandIntent.WORKSTATION_CONTROL:
            response = self._handle_workstation_control(content)
        elif intent == CommandIntent.VPS_CONTROL:
            response = self._handle_vps_control(content)
        elif intent == CommandIntent.CONTINUITY_TRANSITION:
            response = self._handle_continuity_transition(content)
        elif intent == CommandIntent.STARTUP_SEQUENCE:
            response = self._handle_startup_sequence()
        elif intent == CommandIntent.MODE_SWITCH:
            response = self._handle_mode_switch(content)
        else:
            response = self._handle_advisor_signal(content, context_summary)

        response.conversation_id = conversation_id
        response.intent = intent.value

        # Voice-sourced responses: generate a concise spoken_text for TTS
        if source == "voice" and response.text:
            response.spoken_text = self._build_spoken_text(response.text)

        # Routing metadata: resolve if caller provided routing context
        if routing:
            response.routing = self._resolve_routing(content, routing)

        self._save_turn(
            conversation_id,
            "operator",
            content,
            view_context,
            routing=routing,
        )
        self._save_turn(
            conversation_id,
            "assistant",
            response.text,
            view_context,
            intent=intent.value,
            suggested_actions=response.suggested_actions,
        )

        history.append({"role": "operator", "content": content})
        history.append({"role": "assistant", "content": response.text})
        if len(history) > self._MAX_TURNS * 2:
            self._histories[conversation_id] = history[-self._MAX_TURNS * 2 :]

        # Cache response for voice turn idempotency
        if voice_turn_id:
            import time as _time

            self._voice_turn_cache[voice_turn_id] = (response, _time.time())

        return response

    def _clean_voice_turn_cache(self) -> None:
        """Remove expired entries from the voice turn cache."""
        import time as _time

        now = _time.time()
        expired = [
            k
            for k, (_, ts) in self._voice_turn_cache.items()
            if now - ts > self._VOICE_TURN_CACHE_TTL_S
        ]
        for k in expired:
            del self._voice_turn_cache[k]

    def _build_spoken_text(self, text: str) -> str:
        """Convert display text to a TTS-friendly spoken form.

        Strips markdown, code blocks, metadata lines, and truncates to ~400 chars
        so TTS latency stays low.
        """
        try:
            from substrate.execution.bridge.voice_first import prepare_voice_response

            return prepare_voice_response(text)
        except Exception as exc:
            logger.debug("voice_first.prepare_voice_response unavailable: %s", exc)

        import re

        # Strip code blocks
        cleaned = re.sub(r"```[\s\S]*?```", "", text)
        # Strip markdown formatting
        cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)
        cleaned = re.sub(r"\*(.+?)\*", r"\1", cleaned)
        cleaned = re.sub(r"`(.+?)`", r"\1", cleaned)
        # Strip metadata-looking lines (key: value patterns at line start)
        cleaned = re.sub(r"^[\w_]+:\s+\S.*$", "", cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()
        return cleaned[:400]

    def _resolve_routing(self, content: str, routing: dict[str, Any]) -> dict[str, Any]:
        """Run the voice route resolver and return routing dict for the response."""
        try:
            from substrate.workstation.voice_route_resolver import resolve_voice_route

            source_session_id = routing.get("source_session_id", "")
            requested_target = routing.get("execution_target")
            route = resolve_voice_route(
                transcript=content,
                source_session_id=source_session_id,
                requested_target_node=requested_target,
            )
            return route.to_dict()
        except Exception as exc:
            logger.debug("Voice route resolution failed: %s", exc)
            return {}

    def _handle_conversation(
        self,
        content: str,
        conversation_id: str,
        history: list[dict[str, Any]],
        view_context: dict[str, Any] | None,
        context_summary: str,
    ) -> AdvisorResponse:
        # Grounding guard: catch status-seeking queries that classify_intent missed
        from substrate.organism.grounding_registry import detect_status_seeking

        status_type = detect_status_seeking(content)
        if status_type:
            return self._route_grounded_query(status_type, content)

        from substrate.state.business.business_instance import get_ai_name

        ai_name = get_ai_name() or "Assistant"

        from substrate.organism.system_identity import get_prompt_grounding

        prompt_parts = [
            f"You are {ai_name}, a strategic advisor and executive assistant for UMH "
            f"(Universal Meta Harness). You are the operator's primary conversational "
            f"partner — a co-founder-level thinker who brainstorms, plans, reviews, and "
            f"helps make decisions. Be direct, insightful, and actionable. Do not hedge. "
            f"You have access to the UMH cockpit, work packets, agents, and Claude Code "
            f"sessions.\n\n" + get_prompt_grounding(ai_name),
        ]

        if context_summary:
            prompt_parts.append(f"\nCurrent context: {context_summary}")

        if history:
            prompt_parts.append("\nRecent conversation:")
            for turn in history[-20:]:
                role_label = "Operator" if turn["role"] == "operator" else ai_name
                prompt_parts.append(f"{role_label}: {turn['content'][:500]}")

        prompt_parts.append(f"\nOperator: {content}")
        prompt_parts.append(f"\n{ai_name}:")

        prompt = "\n".join(prompt_parts)

        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt,
                task_type="conversation",
                agent_type="ceo",
            )
            response_text = ""
            if result and hasattr(result, "output"):
                response_text = result.output or ""
            elif result and hasattr(result, "content"):
                response_text = result.content or ""
            elif isinstance(result, str):
                response_text = result
            elif isinstance(result, dict):
                response_text = result.get("content", "") or result.get("text", "")

            if not response_text:
                response_text = (
                    "I can process commands but the conversational model is "
                    "temporarily unavailable. Try asking me to check status, "
                    "create work packets, or run a council review."
                )
                return AdvisorResponse(
                    text=response_text,
                    conversation_id=conversation_id,
                    intent="chat",
                    suggested_actions=self._default_suggestions(),
                )

            suggestions = self._infer_suggestions(content, response_text, view_context)

            metadata: dict[str, Any] = {}
            if result and hasattr(result, "provider"):
                metadata["model_tier"] = result.provider
            if result and hasattr(result, "model"):
                metadata["model"] = result.model
            if result and getattr(result, "metadata", None):
                metadata.update(result.metadata)

            return AdvisorResponse(
                text=response_text.strip(),
                conversation_id=conversation_id,
                intent="chat",
                suggested_actions=suggestions,
                metadata=metadata,
            )
        except Exception as exc:
            logger.error("Conversation LLM call failed: %s", exc)
            return AdvisorResponse(
                text=(
                    "I can process commands but conversational mode hit an error. "
                    f"({type(exc).__name__})"
                ),
                conversation_id=conversation_id,
                intent="chat",
                suggested_actions=self._default_suggestions(),
            )

    def _handle_council(
        self,
        content: str,
        view_context: dict[str, Any] | None,
        context_summary: str,
    ) -> AdvisorResponse:
        try:
            review = self._advisor.convene_council(
                context=context_summary or content[:500],
                plan=content,
            )
            text = self._format_council_review(review)
            return AdvisorResponse(
                text=text,
                conversation_id="",
                intent="council",
                metadata={"council_review": review},
            )
        except Exception as exc:
            logger.error("Council review failed: %s", exc)
            return AdvisorResponse(
                text=f"Council review failed: {exc}",
                conversation_id="",
                intent="council",
            )

    def _handle_cc_send(
        self,
        content: str,
        view_context: dict[str, Any] | None,
    ) -> AdvisorResponse:
        try:
            from substrate.execution.bridge.claude_session_bridge import (
                list_sessions,
                send_message,
            )

            sessions = list_sessions()
            session_list = sessions.get("sessions", [])
            if not session_list:
                return AdvisorResponse(
                    text="No active Claude Code sessions found. Start a session first.",
                    conversation_id="",
                    intent="cc_send",
                    suggested_actions=[
                        {
                            "label": "Check sessions",
                            "action": "query",
                            "payload": {"content": "show claude code sessions"},
                        }
                    ],
                )

            target_session = (
                session_list[0]
                if isinstance(session_list[0], str)
                else session_list[0].get("name", "")
            )
            prompt_text = (
                content.replace("send to claude code", "")
                .replace("send this to cc", "")
                .replace("delegate to claude", "")
                .strip()
            )
            if not prompt_text:
                prompt_text = content

            result = send_message("local", target_session, prompt_text)
            if result.get("ok"):
                return AdvisorResponse(
                    text=f"Sent to Claude Code session `{target_session}`. Use 'capture output' to see the result.",
                    conversation_id="",
                    intent="cc_send",
                    metadata={"cc_result": result},
                    suggested_actions=[
                        {
                            "label": "Capture Output",
                            "action": "query",
                            "payload": {"content": "capture claude output"},
                        },
                        {
                            "label": "Open Meta IDE",
                            "action": "navigate",
                            "payload": {"panel": "editor"},
                        },
                    ],
                )
            error_detail = result.get("error", "")
            if not error_detail:
                error_detail = "No active Claude Code session accepted the message. Check that a session is running and attached."
            return AdvisorResponse(
                text=f"Claude Code send failed: {error_detail}",
                conversation_id="",
                intent="cc_send",
                suggested_actions=[
                    {
                        "label": "Check sessions",
                        "action": "query",
                        "payload": {"content": "show claude code sessions"},
                    },
                    {"label": "Retry", "action": "query", "payload": {"content": content}},
                ],
            )
        except ImportError:
            return AdvisorResponse(
                text="Claude Code bridge is not installed on this node. The session bridge module is required to send messages to Claude Code.",
                conversation_id="",
                intent="cc_send",
            )
        except Exception as exc:
            return AdvisorResponse(
                text=f"Claude Code bridge unavailable: {exc}",
                conversation_id="",
                intent="cc_send",
                suggested_actions=[
                    {
                        "label": "Check sessions",
                        "action": "query",
                        "payload": {"content": "show claude code sessions"},
                    },
                ],
            )

    def _handle_cc_capture(self, view_context: dict[str, Any] | None) -> AdvisorResponse:
        try:
            from substrate.execution.bridge.claude_session_bridge import (
                capture_output,
                list_sessions,
            )

            sessions = list_sessions()
            session_list = sessions.get("sessions", [])
            if not session_list:
                return AdvisorResponse(
                    text="No active Claude Code sessions to capture from.",
                    conversation_id="",
                    intent="cc_capture",
                )

            target = (
                session_list[0]
                if isinstance(session_list[0], str)
                else session_list[0].get("name", "")
            )
            result = capture_output("local", target)
            output = result.get("output", "")
            if output:
                truncated = output[:2000]
                if len(output) > 2000:
                    truncated += f"\n\n... ({len(output)} chars total, showing first 2000)"
                return AdvisorResponse(
                    text=f"**Claude Code output from `{target}`:**\n\n```\n{truncated}\n```",
                    conversation_id="",
                    intent="cc_capture",
                    suggested_actions=[
                        {
                            "label": "Create Work Packet",
                            "action": "query",
                            "payload": {"content": "turn this into work packets"},
                        },
                    ],
                )
            return AdvisorResponse(
                text=f"No output captured from session `{target}`.",
                conversation_id="",
                intent="cc_capture",
            )
        except Exception as exc:
            return AdvisorResponse(
                text=f"Capture failed: {exc}",
                conversation_id="",
                intent="cc_capture",
            )

    def _handle_decompose(
        self,
        content: str,
        history: list[dict[str, Any]],
    ) -> AdvisorResponse:
        try:
            from substrate.organism.work_packet_engine import WorkPacketEngine

            engine = WorkPacketEngine()
            recent_context = " ".join(t["content"] for t in history[-6:] if t["role"] == "operator")
            intent_text = recent_context + " " + content if recent_context else content

            result = engine.decompose_intent_to_batch(
                user_intent=intent_text.strip(),
            )

            if result.get("ok") is False:
                return AdvisorResponse(
                    text=f"Decomposition failed: {result.get('error', 'unknown')}",
                    conversation_id="",
                    intent="decompose_intent",
                )

            child_count = result.get("created_count", len(result.get("child_packet_ids", [])))
            parent_id = result.get("parent_packet_id", "")
            text = (
                f"Created {child_count} work packets"
                f"{f' under batch {parent_id}' if parent_id else ''}.\n"
            )

            children = result.get("child_packet_ids", [])
            if children:
                text += "\nPackets:\n"
                for cid in children[:10]:
                    text += f"- `{cid}`\n"

            return AdvisorResponse(
                text=text.strip(),
                conversation_id="",
                intent="decompose_intent",
                metadata={"decompose_result": result},
                suggested_actions=[
                    {"label": "Open Work", "action": "navigate", "payload": {"panel": "work"}},
                    {
                        "label": "Run Council Review",
                        "action": "query",
                        "payload": {"content": "run council review on the latest batch"},
                    },
                ],
            )
        except Exception as exc:
            return AdvisorResponse(
                text=f"Decomposition failed: {exc}",
                conversation_id="",
                intent="decompose_intent",
            )

    def _handle_resume(self) -> AdvisorResponse:
        # Deterministic-first: real event/state data, no LLM fabrication
        from substrate.organism.grounded_handlers import handle_grounded_resume

        return handle_grounded_resume()

    def _handle_status(self, content: str) -> AdvisorResponse:
        # Deterministic-first: real data only, no LLM fabrication
        from substrate.organism.grounded_handlers import handle_grounded_status

        return handle_grounded_status(content)

    def _route_grounded_query(self, query_type: str, content: str) -> AdvisorResponse:
        """Route a detected status-seeking query to its specific grounded handler."""
        from substrate.organism import grounded_handlers as gh

        _GROUNDED_ROUTER: dict[str, Any] = {
            "docker_status": gh.handle_grounded_docker,
            "provider_health": gh.handle_grounded_providers,
            "voice_health": gh.handle_grounded_voice,
            "vision_status": gh.handle_grounded_vision,
            "visual_query": gh.handle_grounded_visual,
            "beast_health": gh.handle_grounded_beast,
            "work_packets": gh.handle_grounded_status,
            "blocked_packets": gh.handle_grounded_blocked,
            "composite_blockers": gh.handle_grounded_composite_blockers,
            "agent_status": gh.handle_grounded_agents,
            "recent_reports": gh.handle_grounded_reports,
            "approval_status": gh.handle_grounded_approvals,
            "recent_deployments": gh.handle_grounded_deployments,
            "hermes_status": gh.handle_grounded_hermes,
            "webhook_health": gh.handle_grounded_webhook,
            "system_status": gh.handle_grounded_status,
        }

        handler = _GROUNDED_ROUTER.get(query_type, gh.handle_grounded_status)
        return handler(content)

    def _deterministic_status(self) -> str:
        """Read organism state directly without LLM — always works."""
        import json
        from pathlib import Path

        repo = os.environ.get("UMH_ROOT", "/opt/OS")
        lines = []

        # Provider health
        try:
            from adapters.models.model_router import MODEL_REGISTRY, ROLE_SLOTS

            healthy = [k for k, c in MODEL_REGISTRY.items() if c.available]
            lines.append(f"**Providers:** {len(healthy)} healthy — {', '.join(healthy) or 'none'}")
        except Exception:
            lines.append("**Providers:** status unavailable")

        # Work packets
        try:
            wp_path = Path(repo) / "data" / "umh" / "universal_work" / "work_packets.jsonl"
            if wp_path.exists():
                active = 0
                with open(wp_path) as f:
                    for line in f:
                        if '"active"' in line or '"in_progress"' in line:
                            active += 1
                lines.append(f"**Work packets:** {active} active")
        except Exception:
            pass

        # Workcell heartbeats
        try:
            wc_dir = Path(repo) / "data" / "umh" / "organism" / "workcells"
            if wc_dir.exists():
                alive = []
                for hb in wc_dir.glob("*/heartbeat.json"):
                    alive.append(hb.parent.name)
                if alive:
                    lines.append(f"**Workcells:** {', '.join(alive)}")
        except Exception:
            pass

        if not lines:
            return "System operational. Use the command center for detailed status."
        return "\n".join(lines)

    def _handle_navigation(self, content: str) -> AdvisorResponse:
        from substrate.workstation.command_router import resolve_navigation_target

        panel = resolve_navigation_target(content)
        return AdvisorResponse(
            text=f"Opening {panel}." if panel else "Could not resolve navigation target.",
            conversation_id="",
            intent="cockpit_navigation",
            metadata={"target_node": "cockpit", "panel": panel} if panel else {},
            suggested_actions=[
                {"label": f"Open {panel}", "action": "navigate", "payload": {"panel": panel}},
            ]
            if panel
            else [],
        )

    def _handle_explain_view(
        self,
        content: str,
        conversation_id: str,
        history: list[dict[str, Any]],
        view_context: dict[str, Any] | None,
        context_summary: str,
    ) -> AdvisorResponse:
        from substrate.state.business.business_instance import get_ai_name

        ai_name = get_ai_name() or "Assistant"

        if not view_context or not context_summary:
            route = ""
            if view_context and view_context.get("active_route"):
                route = view_context["active_route"]
            fallback = (
                f"I can see you're in {route}." if route else "I can see you're in the cockpit."
            )
            fallback += (
                " I don't have details about what's currently selected. "
                "Try selecting an item or tell me what you're looking at."
            )
            return AdvisorResponse(
                text=fallback,
                conversation_id=conversation_id,
                intent="explain_current_view",
                suggested_actions=[
                    {
                        "label": "Status",
                        "action": "query",
                        "payload": {"content": "current status"},
                    },
                    {
                        "label": "Open Command Center",
                        "action": "navigate",
                        "payload": {"panel": "commandcenter"},
                    },
                ],
            )

        prompt_parts = [
            f"You are {ai_name}, a strategic advisor. The operator is asking about "
            f"what they're currently viewing in the cockpit. Describe what they're "
            f"looking at, explain its significance, and suggest the highest-leverage "
            f"next action. Be concise and actionable.",
            f"\nCurrent context: {context_summary}",
        ]

        if view_context.get("visible_context_summary"):
            prompt_parts.append(f"Visible: {view_context['visible_context_summary']}")
        if view_context.get("available_actions"):
            prompt_parts.append(
                f"Available actions: {', '.join(view_context['available_actions'])}"
            )

        if history:
            prompt_parts.append("\nRecent conversation:")
            for turn in history[-6:]:
                role_label = "Operator" if turn["role"] == "operator" else ai_name
                prompt_parts.append(f"{role_label}: {turn['content'][:300]}")

        prompt_parts.append(f"\nOperator: {content}")
        prompt_parts.append(f"\n{ai_name}:")

        prompt = "\n".join(prompt_parts)

        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(prompt, task_type="conversation")
            response_text = ""
            if result and hasattr(result, "output"):
                response_text = result.output or ""
            elif result and hasattr(result, "content"):
                response_text = result.content or ""
            elif isinstance(result, str):
                response_text = result
            elif isinstance(result, dict):
                response_text = result.get("content", "") or result.get("text", "")

            if not response_text:
                response_text = (
                    f"You're viewing: {context_summary}. "
                    "I couldn't generate a detailed explanation right now."
                )

            suggestions = self._infer_suggestions(content, response_text, view_context)
            return AdvisorResponse(
                text=response_text.strip(),
                conversation_id=conversation_id,
                intent="explain_current_view",
                suggested_actions=suggestions,
                metadata={"model_tier": "fast"},
            )
        except Exception as exc:
            logger.error("Explain view LLM call failed: %s", exc)
            return AdvisorResponse(
                text=(
                    f"You're viewing: {context_summary}. (Detail unavailable: {type(exc).__name__})"
                ),
                conversation_id=conversation_id,
                intent="explain_current_view",
                suggested_actions=self._default_suggestions(),
            )

    def _handle_advisor_signal(
        self,
        content: str,
        context_summary: str,
    ) -> AdvisorResponse:
        # Grounding guard: prevent status fabrication through the advisor path
        from substrate.organism.grounding_registry import detect_status_seeking

        status_type = detect_status_seeking(content)
        if status_type:
            return self._route_grounded_query(status_type, content)

        enriched = f"{context_summary} {content}".strip() if context_summary else content
        try:
            result = self._advisor.handle_signal(enriched)
            text = self._format_advisor_result(result)

            if text in ("Signal processed.", "No response from advisor.", ""):
                text = (
                    "I processed that command but didn't get a substantive result. "
                    "The action may have completed silently or there was nothing to act on."
                )
                return AdvisorResponse(
                    text=text,
                    conversation_id="",
                    intent="action",
                    metadata={"advisor_result": result},
                    suggested_actions=[
                        {
                            "label": "Check Status",
                            "action": "query",
                            "payload": {"content": "current status"},
                        },
                        {
                            "label": "Open Command Center",
                            "action": "navigate",
                            "payload": {"panel": "commandcenter"},
                        },
                    ],
                )

            return AdvisorResponse(
                text=text,
                conversation_id="",
                intent="action",
                metadata={"advisor_result": result},
            )
        except Exception as exc:
            logger.error("Advisor signal failed: %s", exc)
            return AdvisorResponse(
                text=(
                    f"I couldn't complete that action: {exc}. Your conversation is still intact."
                ),
                conversation_id="",
                intent="action",
                suggested_actions=[
                    {
                        "label": "Check Status",
                        "action": "query",
                        "payload": {"content": "current status"},
                    },
                    {
                        "label": "Open Command Center",
                        "action": "navigate",
                        "payload": {"panel": "commandcenter"},
                    },
                ],
            )

    # ── Approval Query (deterministic) ───────────────────────────────

    def _handle_approval_query(self) -> AdvisorResponse:
        """Deterministic approval queue reader — no LLM."""
        from pathlib import Path

        repo = os.environ.get("UMH_ROOT", "/opt/OS")
        approvals: list[dict[str, Any]] = []

        approval_dir = Path(repo) / "data" / "umh" / "governance" / "pending_approvals"
        try:
            if approval_dir.exists():
                for f in sorted(approval_dir.glob("*.json")):
                    try:
                        entry = json.loads(f.read_text())
                        approvals.append(
                            {
                                "id": entry.get("id", f.stem),
                                "title": entry.get("title", entry.get("command", f.stem)),
                                "risk": entry.get("risk", "unknown"),
                                "created_at": entry.get("created_at", ""),
                            }
                        )
                    except Exception:
                        pass
        except Exception:
            pass

        if not approvals:
            return AdvisorResponse(
                text="No pending approvals.",
                conversation_id="",
                intent="approval_query",
                metadata={"model_tier": "deterministic", "count": 0},
                suggested_actions=[
                    {
                        "label": "Status",
                        "action": "query",
                        "payload": {"content": "current status"},
                    },
                ],
            )

        lines = [f"**{len(approvals)} pending approval(s):**\n"]
        for a in approvals[:10]:
            risk_tag = f" [{a['risk']}]" if a.get("risk") else ""
            lines.append(f"- **{a['title']}**{risk_tag}")
            if a.get("created_at"):
                lines.append(f"  Created: {a['created_at']}")

        return AdvisorResponse(
            text="\n".join(lines),
            conversation_id="",
            intent="approval_query",
            metadata={
                "model_tier": "deterministic",
                "count": len(approvals),
                "approvals": approvals,
            },
            suggested_actions=[
                {
                    "label": "Open Approvals",
                    "action": "navigate",
                    "payload": {"panel": "approvals"},
                },
            ],
        )

    # ── Workstation / Continuity / Startup ─────────────────────────────

    def _handle_workstation_control(self, content: str) -> AdvisorResponse:
        from substrate.workstation.command_router import resolve_workstation_target

        target = resolve_workstation_target(content)
        action = target.get("action", "open")
        app = target.get("target_app", "")
        risk = target.get("risk", "low")
        requires_approval = target.get("requires_approval", False)

        if action == "screenshot":
            return self._execute_workstation_command(
                "desktop.screenshot",
                {},
                "Taking a screenshot.",
                "workstation_control",
            )

        if action == "list_windows":
            return self._execute_workstation_command(
                "desktop.list_windows",
                {},
                "Listing open windows.",
                "workstation_control",
            )

        if action.startswith("media_"):
            _KEYBD_EVENT_PREAMBLE = (
                "$sig = '[DllImport(\"user32.dll\")] public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);';"
                " $kb = Add-Type -MemberDefinition $sig -Name KB -Namespace W32 -PassThru;"
            )
            media_cmds = {
                "media_play": f"{_KEYBD_EVENT_PREAMBLE} $kb::keybd_event(0xB3,0,0,[UIntPtr]::Zero); $kb::keybd_event(0xB3,0,2,[UIntPtr]::Zero)",
                "media_pause": f"{_KEYBD_EVENT_PREAMBLE} $kb::keybd_event(0xB3,0,0,[UIntPtr]::Zero); $kb::keybd_event(0xB3,0,2,[UIntPtr]::Zero)",
                "media_next": f"{_KEYBD_EVENT_PREAMBLE} $kb::keybd_event(0xB0,0,0,[UIntPtr]::Zero); $kb::keybd_event(0xB0,0,2,[UIntPtr]::Zero)",
                "media_previous": f"{_KEYBD_EVENT_PREAMBLE} $kb::keybd_event(0xB1,0,0,[UIntPtr]::Zero); $kb::keybd_event(0xB1,0,2,[UIntPtr]::Zero)",
            }
            ps_cmd = media_cmds.get(action)
            if ps_cmd:
                label = action.replace("media_", "").capitalize()
                return self._execute_workstation_command(
                    "shell.powershell",
                    {"command": ps_cmd},
                    f"{label} — sent media key.",
                    "workstation_control",
                )
            return AdvisorResponse(
                text=f"Unknown media action: {action}.",
                conversation_id="",
                intent="workstation_control",
                metadata={"action": action, "target": target},
            )

        if requires_approval or risk == "high":
            desc = f"{action} {app}".strip() if app else "this"
            return AdvisorResponse(
                text=f"That requires approval — {desc} is a high-risk external action.",
                conversation_id="",
                intent="workstation_control",
                metadata={
                    "action": action,
                    "target": target,
                    "blocked": True,
                    "target_node": "beast_windows",
                },
                suggested_actions=[
                    {"label": "Approve", "action": "approve", "payload": {"command": content}},
                ],
            )

        if app:
            process = target.get("process_name", "")
            url = target.get("target_url", "")
            if action == "focus" and process:
                return self._execute_workstation_command(
                    "desktop.focus_window",
                    {"process": process},
                    f"Focusing {app}.",
                    "workstation_control",
                )
            if url:
                return self._execute_workstation_command(
                    "shell.powershell",
                    {"command": f'Start-Process "{url}"'},
                    f"Opening {app}.",
                    "workstation_control",
                )
            if process:
                return self._execute_workstation_command(
                    "shell.powershell",
                    {"command": f'Start-Process "{process}"'},
                    f"Opening {app}.",
                    "workstation_control",
                )
            return AdvisorResponse(
                text=f"I don't know how to open {app} — it's not in the app registry.",
                conversation_id="",
                intent="workstation_control",
                metadata={"target": target},
            )

        return AdvisorResponse(
            text="I couldn't determine which app or action you want.",
            conversation_id="",
            intent="workstation_control",
            suggested_actions=[
                {
                    "label": "List Windows",
                    "action": "query",
                    "payload": {"content": "what windows are open"},
                },
            ],
        )

    def _handle_vps_control(self, content: str) -> AdvisorResponse:
        """Handle VPS control commands through the governed catalog."""
        from substrate.workstation.vps_control_catalog import (
            check_blocked,
            execute_catalog_action,
            resolve_vps_action,
        )

        blocked_reason = check_blocked(content)
        if blocked_reason:
            return AdvisorResponse(
                text=f"**Blocked.** {blocked_reason}",
                conversation_id="",
                intent="vps_control",
                metadata={
                    "ok": False,
                    "status": "blocked",
                    "target_node": "vps",
                    "blocked_reason": blocked_reason,
                },
            )

        action = resolve_vps_action(content)
        if not action:
            return AdvisorResponse(
                text=(
                    "I couldn't map that to a known VPS command. "
                    "Try: show docker containers, vps status, provider health, "
                    "git status, capture tmux, operator logs, or service status."
                ),
                conversation_id="",
                intent="vps_control",
                metadata={
                    "ok": False,
                    "status": "unsupported",
                    "target_node": "vps",
                },
                suggested_actions=[
                    {
                        "label": "VPS Status",
                        "action": "query",
                        "payload": {"content": "show vps status"},
                    },
                    {
                        "label": "Docker Containers",
                        "action": "query",
                        "payload": {"content": "show docker containers"},
                    },
                    {
                        "label": "Provider Health",
                        "action": "query",
                        "payload": {"content": "check provider health"},
                    },
                ],
            )

        result = execute_catalog_action(action)

        if result.status == "needs_approval":
            return AdvisorResponse(
                text=f"**{result.display_name}** requires approval (risk: {result.risk}).",
                conversation_id="",
                intent="vps_control",
                metadata={
                    "ok": False,
                    "status": "needs_approval",
                    "target_node": "vps",
                    "action": result.action,
                    "risk": result.risk,
                    "requires_approval": True,
                },
                suggested_actions=[
                    {
                        "label": f"Approve {result.display_name}",
                        "action": "approve",
                        "payload": {"command": content, "vps_action": result.action},
                    },
                ],
            )

        if result.status == "blocked":
            return AdvisorResponse(
                text=f"**{result.display_name}** blocked: {result.blocked_reason}",
                conversation_id="",
                intent="vps_control",
                metadata={
                    "ok": False,
                    "status": "blocked",
                    "target_node": "vps",
                    "blocked_reason": result.blocked_reason,
                },
            )

        if result.status == "error":
            return AdvisorResponse(
                text=f"**{result.display_name}** failed: {result.error}",
                conversation_id="",
                intent="vps_control",
                metadata={
                    "ok": False,
                    "status": "error",
                    "target_node": "vps",
                    "error": result.error,
                },
            )

        output_text = result.output or "(no output)"
        return AdvisorResponse(
            text=f"**{result.display_name}**\n\n```\n{output_text}\n```",
            conversation_id="",
            intent="vps_control",
            metadata={
                "ok": True,
                "status": "executed",
                "target_node": "vps",
                "action": result.action,
                "risk": result.risk,
            },
            suggested_actions=[
                {
                    "label": "VPS Status",
                    "action": "query",
                    "payload": {"content": "show vps status"},
                },
                {
                    "label": "Docker Containers",
                    "action": "query",
                    "payload": {"content": "show docker containers"},
                },
            ],
        )

    def _handle_continuity_transition(self, content: str) -> AdvisorResponse:
        from substrate.workstation.command_router import resolve_continuity_target

        target_state = resolve_continuity_target(content)
        if not target_state:
            return AdvisorResponse(
                text="I couldn't determine which continuity state you want.",
                conversation_id="",
                intent="continuity_transition",
            )

        try:
            from substrate.workstation.continuity import ContinuityState

            valid_states = {s.value for s in ContinuityState}
            if target_state not in valid_states:
                return AdvisorResponse(
                    text=f"Unknown continuity state: {target_state}.",
                    conversation_id="",
                    intent="continuity_transition",
                )
        except ImportError:
            pass

        risk_info = ""
        try:
            from substrate.workstation.lifecycle_modes import LifecycleMode

            mode_map = {
                "active": LifecycleMode.DAY_CYCLE,
                "night_sleeping": LifecycleMode.NIGHT_CYCLE,
                "away": LifecycleMode.AWAY,
                "remote": LifecycleMode.REMOTE_WORK,
                "extended_absence": LifecycleMode.AWAY,
            }
            mode = mode_map.get(target_state)
            if mode:
                risk_info = f" Risk ceiling: {mode.value}."
        except ImportError:
            pass

        return AdvisorResponse(
            text=f"Transitioning to {target_state}.{risk_info}",
            conversation_id="",
            intent="continuity_transition",
            metadata={"target_state": target_state},
            suggested_actions=[
                {"label": "Status", "action": "query", "payload": {"content": "current status"}},
            ],
        )

    def _handle_startup_sequence(self) -> AdvisorResponse:
        lines = ["**Starting up.**\n"]
        node_status: dict[str, str] = {}

        try:
            from adapters.models.model_router import MODEL_REGISTRY, refresh_provider_health

            try:
                refresh_provider_health()
            except Exception:
                pass
            healthy = [k for k, c in MODEL_REGISTRY.items() if c.available]
            lines.append(f"**Providers:** {len(healthy)} healthy — {', '.join(healthy) or 'none'}")
        except Exception:
            lines.append("**Providers:** status unavailable")

        try:
            import urllib.request

            health_host = os.environ.get("UMH_API_HOST", "localhost")
            health_port = os.environ.get("UMH_API_PORT", "8091")
            req = urllib.request.Request(
                f"http://{health_host}:{health_port}/health",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                lines.append("**VPS API:** healthy")
                node_status["vps"] = "healthy"
        except Exception:
            lines.append("**VPS API:** unreachable (may be inside container)")
            node_status["vps"] = "unreachable"

        try:
            import json as _json
            from pathlib import Path

            mesh_file = (
                Path(os.environ.get("UMH_ROOT", "/opt/OS")) / "data" / "runtime" / "mesh_nodes.json"
            )
            if mesh_file.exists():
                nodes = _json.loads(mesh_file.read_text())
                for node in nodes:
                    if "desktop" in node.get("capabilities", []):
                        status = node.get("status", "unknown")
                        lines.append(f"**Beast:** {status}")
                        node_status["beast_windows"] = status
                        break
                else:
                    lines.append("**Beast:** no desktop node registered")
                    node_status["beast_windows"] = "not_registered"
            else:
                lines.append("**Beast:** mesh data unavailable")
                node_status["beast_windows"] = "no_mesh_data"
        except Exception:
            lines.append("**Beast:** status check failed")
            node_status["beast_windows"] = "error"

        try:
            from substrate.workstation.continuity import ContinuityState

            lines.append(f"**Continuity:** transitioning to {ContinuityState.ACTIVE.value}")
        except ImportError:
            pass

        try:
            from substrate.workstation.resume_brief import ReturnBriefGenerator

            gen = ReturnBriefGenerator()
            brief = gen.generate_brief()
            if brief:
                brief_text = brief if isinstance(brief, str) else str(brief)
                if brief_text and brief_text != "None":
                    lines.append(f"\n**Resume brief:**\n{brief_text[:500]}")
        except Exception:
            pass

        return AdvisorResponse(
            text="\n".join(lines),
            conversation_id="",
            intent="startup_sequence",
            metadata={"node_status": node_status},
            suggested_actions=[
                {"label": "Full Status", "action": "query", "payload": {"content": "full status"}},
                {
                    "label": "What's Next?",
                    "action": "query",
                    "payload": {"content": "what should we do next"},
                },
            ],
        )

    def _handle_mode_switch(self, content: str) -> AdvisorResponse:
        from substrate.workstation.command_router import resolve_mode_target

        target = resolve_mode_target(content)
        if not target:
            return AdvisorResponse(
                text="I couldn't determine which mode you want.",
                conversation_id="",
                intent="mode_switch",
            )

        continuity_modes = {"night_sleeping", "away", "returning", "active"}
        if target in continuity_modes:
            return self._handle_continuity_transition(content)

        try:
            from substrate.workstation.profile_modes import ProfileMode

            profile_values = {m.value for m in ProfileMode}
        except ImportError:
            profile_values = set()

        if target in profile_values:
            return AdvisorResponse(
                text=f"Switching to {target} mode.",
                conversation_id="",
                intent="mode_switch",
                metadata={"profile_mode": target},
                suggested_actions=[
                    {
                        "label": "Status",
                        "action": "query",
                        "payload": {"content": "current status"},
                    },
                ],
            )

        return AdvisorResponse(
            text=f"Mode '{target}' recognized but not yet mapped to a profile.",
            conversation_id="",
            intent="mode_switch",
            metadata={"raw_target": target},
        )

    def _execute_workstation_command(
        self,
        capability: str,
        params: dict[str, Any],
        success_text: str,
        intent: str,
    ) -> AdvisorResponse:
        """Send a command to the workstation node via the mesh server."""
        import json as _json
        from pathlib import Path
        from uuid import uuid4

        desktop_node_id = None
        mesh_file = Path(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data",
            "runtime",
            "mesh_nodes.json",
        )
        try:
            if mesh_file.exists():
                nodes = _json.loads(mesh_file.read_text())
                for node in nodes:
                    if "desktop" in node.get("capabilities", []):
                        if node.get("status") == "connected":
                            desktop_node_id = node.get("id", node.get("name", "unknown"))
                            break
        except Exception:
            pass

        if not desktop_node_id:
            return AdvisorResponse(
                text=f"No workstation node online — can't execute {capability}.",
                conversation_id="",
                intent=intent,
                metadata={"ok": False, "status": "blocked", "reason": "workstation_offline"},
            )

        return self._dispatch_via_http_relay(
            desktop_node_id,
            capability,
            params,
            success_text,
            intent,
        )

    def _dispatch_via_http_relay(
        self,
        node_id: str,
        capability: str,
        params: dict[str, Any],
        success_text: str,
        intent: str,
    ) -> AdvisorResponse:
        """Dispatch a command to a node via the mesh server's HTTP relay."""
        import urllib.request

        relay_host = os.environ.get("UMH_MESH_RELAY_HOST", "172.18.0.1")
        relay_port = os.environ.get("UMH_MESH_RELAY_PORT", "8095")
        url = f"http://{relay_host}:{relay_port}/dispatch"

        payload = json.dumps(
            {
                "node_id": node_id,
                "capability": capability,
                "params": params,
                "timeout": 15,
            }
        ).encode()

        try:
            req = urllib.request.Request(
                url,
                data=payload,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                result = json.loads(resp.read())
        except Exception as exc:
            logger.error("Mesh HTTP relay dispatch failed: %s", exc)
            return AdvisorResponse(
                text=f"Mesh relay unreachable — can't dispatch {capability} to {node_id}. ({exc})",
                conversation_id="",
                intent=intent,
                metadata={"ok": False, "status": "relay_unreachable", "error": str(exc)},
            )

        if result.get("ok"):
            result_data = result.get("result_data", {})
            proof: dict[str, Any] = {}
            if "stdout" in result_data:
                proof["stdout"] = result_data["stdout"][:500]
            if "window" in result_data:
                proof["active_window"] = result_data["window"]
            if "windows" in result_data:
                proof["window_count"] = len(result_data["windows"])
                proof["windows"] = [w.get("title", "") for w in result_data["windows"][:10]]
            if "image_base64" in result_data:
                proof["screenshot_available"] = True

            return AdvisorResponse(
                text=success_text,
                conversation_id="",
                intent=intent,
                metadata={
                    "ok": True,
                    "status": "executed",
                    "target_node": "beast_windows",
                    "capability": capability,
                    "params": params,
                    "routed_to": node_id,
                    "proof": proof,
                    "latency_ms": result.get("latency_ms", 0),
                },
                suggested_actions=[
                    {
                        "label": "List Windows",
                        "action": "query",
                        "payload": {"content": "list windows"},
                    },
                    {
                        "label": "Screenshot",
                        "action": "query",
                        "payload": {"content": "take a screenshot"},
                    },
                ],
            )
        else:
            error_msg = result.get("error") or ""
            result_data = result.get("result_data", {})
            if not error_msg and result_data.get("stderr"):
                error_msg = result_data["stderr"][:200]
            if not error_msg:
                error_msg = "unknown error"
            status = result.get("status", "failed")
            return AdvisorResponse(
                text=f"Command failed on {node_id}: {error_msg}",
                conversation_id="",
                intent=intent,
                metadata={
                    "ok": False,
                    "status": status,
                    "capability": capability,
                    "params": params,
                    "routed_to": node_id,
                    "error": error_msg,
                },
            )

    # ── Formatting ────────────────────────────────────────────────────

    def _format_advisor_result(self, result: dict[str, Any]) -> str:
        if not result:
            return "No response from advisor."

        if "error" in result:
            return f"Error: {result['error']}"

        deliverable = result.get("deliverable")
        if isinstance(deliverable, dict):
            content = deliverable.get("content", "") or deliverable.get("summary", "")
            if content:
                return str(content)[:3000]

        output = result.get("output")
        if output:
            return str(output)[:3000]

        execution = result.get("execution", "")
        capability = result.get("capability", "")
        agent = result.get("delegated_to", "")
        parts = []
        if execution:
            parts.append(f"Execution: {execution}")
        if capability:
            parts.append(f"Capability: {capability}")
        if agent:
            parts.append(f"Delegated to: {agent}")
        return " | ".join(parts) if parts else "Signal processed."

    def _format_council_review(self, review: dict[str, Any] | Any) -> str:
        if isinstance(review, dict):
            data = review
        elif hasattr(review, "to_dict"):
            data = review.to_dict()
        else:
            return str(review)

        parts = ["**Council Review**\n"]
        consensus = data.get("consensus", "unknown")
        parts.append(f"**Consensus:** {consensus}")

        recommendation = data.get("final_recommendation", "")
        if recommendation:
            parts.append(f"**Recommendation:** {recommendation}")

        risk = data.get("risk_summary", "")
        if risk:
            parts.append(f"**Risk:** {risk}")

        dissent = data.get("dissenting_points", [])
        if dissent:
            parts.append("\n**Dissenting concerns:**")
            for d in dissent[:5]:
                parts.append(f"- {d}")

        changes = data.get("required_changes", [])
        if changes:
            parts.append("\n**Required changes:**")
            for c in changes[:5]:
                parts.append(f"- {c}")

        roles = data.get("roles", [])
        if roles:
            parts.append("\n**Role assessments:**")
            for r in roles[:7]:
                role_name = r.get("role", "")
                rec = r.get("recommendation", "")
                conf = r.get("confidence", 0)
                parts.append(f"- **{role_name}**: {rec} (confidence: {conf:.0%})")

        return "\n".join(parts)

    # ── Suggestions ───────────────────────────────────────────────────

    def _infer_suggestions(
        self,
        user_content: str,
        response_text: str,
        view_context: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        suggestions: list[dict[str, Any]] = []
        combined = (user_content + " " + response_text).lower()

        if any(kw in combined for kw in ["plan", "implement", "build", "create", "design"]):
            suggestions.append(
                {
                    "label": "Create Work Packets",
                    "action": "query",
                    "payload": {"content": "turn this into work packets"},
                }
            )

        if any(kw in combined for kw in ["review", "evaluate", "assess", "good enough"]):
            suggestions.append(
                {
                    "label": "Run Council Review",
                    "action": "query",
                    "payload": {"content": "run council review"},
                }
            )

        if any(kw in combined for kw in ["code", "implement", "fix", "build", "write"]):
            suggestions.append(
                {
                    "label": "Send to Claude Code",
                    "action": "query",
                    "payload": {"content": "send to claude code"},
                }
            )

        if not suggestions:
            suggestions = self._default_suggestions()

        return suggestions[:4]

    def _default_suggestions(self) -> list[dict[str, Any]]:
        return [
            {
                "label": "What's next?",
                "action": "query",
                "payload": {"content": "what should we do next"},
            },
            {"label": "Status", "action": "query", "payload": {"content": "current status"}},
        ]

    # ── Context ───────────────────────────────────────────────────────

    def _build_context_summary(self, view_context: dict[str, Any] | None) -> str:
        if not view_context or not isinstance(view_context, dict):
            return ""
        parts = []
        if view_context.get("active_route"):
            parts.append(view_context["active_route"])
        if view_context.get("selected_object_type"):
            desc = view_context["selected_object_type"]
            if view_context.get("selected_object_summary"):
                desc += f": {view_context['selected_object_summary']}"
            elif view_context.get("selected_object_id"):
                desc += f": {view_context['selected_object_id']}"
            parts.append(desc)
        if parts:
            raw = f"[Context: viewing {' > '.join(parts)}]"
            return raw[: self._MAX_CONTEXT_CHARS]
        return ""

    # ── Persistence ───────────────────────────────────────────────────

    def _save_turn(
        self,
        conversation_id: str,
        role: str,
        content: str,
        view_context: dict[str, Any] | None = None,
        intent: str = "",
        suggested_actions: list[dict[str, Any]] | None = None,
        routing: dict[str, Any] | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "conversation_id": conversation_id,
            "message_id": f"conv-{uuid.uuid4().hex[:12]}",
            "role": role,
            "content": content[:5000],
            "view_context_summary": self._build_context_summary(view_context),
            "intent": intent,
            "suggested_actions": suggested_actions or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        # Persist device/session routing metadata when present
        if routing:
            entry["source"] = "voice"
            entry["device_id"] = routing.get("source_device_id", "")
            entry["session_id"] = routing.get("source_session_id", "")
            entry["execution_target"] = routing.get("execution_target", "")
            entry["audio_output_session"] = routing.get("audio_output_session", "")
        try:
            with open(_CONVERSATIONS_PATH, "a") as f:
                f.write(json.dumps(entry, default=str, separators=(",", ":")) + "\n")
        except Exception as exc:
            logger.debug("Failed to persist conversation turn: %s", exc)

    def _load_history(self, conversation_id: str) -> list[dict[str, Any]]:
        turns: list[dict[str, Any]] = []
        try:
            if not os.path.exists(_CONVERSATIONS_PATH):
                return turns
            with open(_CONVERSATIONS_PATH) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if entry.get("conversation_id") == conversation_id:
                        turns.append(
                            {
                                "role": entry.get("role", "operator"),
                                "content": entry.get("content", ""),
                            }
                        )
        except Exception as exc:
            logger.debug("Failed to load conversation history: %s", exc)
        return turns[-self._MAX_TURNS * 2 :]
