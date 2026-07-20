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


def _conversations_path() -> str:
    from substrate.state.runtime_paths import runtime_state_path

    return str(
        runtime_state_path(
            "operator_experience", "advisor_conversations.jsonl", create_parent=False
        )
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
        os.makedirs(os.path.dirname(_conversations_path()), exist_ok=True)

    def converse(
        self,
        content: str,
        conversation_id: str = "",
        view_context: dict[str, Any] | None = None,
        source: str = "text",
        routing: dict[str, Any] | None = None,
        voice_turn_id: str = "",
        media: list[dict[str, Any]] | None = None,
    ) -> AdvisorResponse:
        """``media`` is the operator's attachments (MediaAttachment dicts). Their
        CONTENT — image/video/pdf via free Gemini vision, audio via local Whisper,
        links in the text via fetch+summarize — is understood and folded into the
        prompt so the assistant reasons over what was actually sent, not just the
        words. This is the ONE seam every surface (cockpit/CLI/discord/voice)
        shares, so wiring it here makes multi-modal understanding coherent everywhere."""
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

        # Deterministic identity handler — never let the LLM hallucinate system name
        from substrate.organism.system_identity import (
            get_identity_answer,
            is_identity_question,
        )
        from substrate.workstation.command_router import (
            CommandIntent,
            classify_intent,
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

        # Multi-modal understanding: fold attachment content + link content into the
        # prompt so the LLM reasons over what the operator actually sent. FREE (Gemini
        # vision / local Whisper / fetch) and best-effort — a failure degrades to a
        # factual stub and never breaks the turn. Applies to EVERY surface via this seam.
        if media or (content and "http" in content.lower()):
            try:
                from substrate.understanding.perception.multimodal import understand_media

                perception = understand_media(media, content)
                extra = perception.as_prompt_context()
                if extra:
                    content = f"{content}{extra}"
                    logger.info(
                        "CONVERSE multimodal: understood %d attachment(s)/link(s)",
                        len(perception.items),
                    )
            except Exception as exc:  # never let perception break the conversation
                logger.warning("multimodal understanding skipped: %s", exc)

        intent = classify_intent(content)
        logger.info("CONVERSE classify_intent(%r) => %s", content[:80], intent.value)
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
        elif intent == CommandIntent.SHUTDOWN_SEQUENCE:
            response = self._handle_shutdown_sequence()
        elif intent == CommandIntent.ENGINEERING_BUILD:
            response = self._handle_engineering_build(content)
        elif intent == CommandIntent.INTENT_CAPTURE:
            response = self._handle_intent_capture(content)
        elif intent == CommandIntent.MODE_SWITCH:
            response = self._handle_mode_switch(content)
        elif intent == CommandIntent.CAMERA_CONTROL:
            from substrate.organism.grounded_handlers import handle_camera_control

            response = handle_camera_control(content)
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

    def _build_reality_context(self) -> str:
        """Query reality models and work queue for current system state.

        Returns a concise text summary for prompt injection. Non-executing —
        awareness only, no automatic work packets or execution.
        """
        sections: list[str] = []

        try:
            from substrate.reality_model.instance import InstanceRealityModel

            instance = InstanceRealityModel()
            recent = instance.recent(limit=5)
            if recent:
                obs_lines = []
                for obs in recent:
                    conf = (
                        obs.effective_confidence()
                        if hasattr(obs, "effective_confidence")
                        else obs.confidence
                    )
                    obs_lines.append(
                        f"- [{obs.domain}] {obs.content[:120]} (confidence: {conf:.2f})"
                    )
                sections.append("Recent observations:\n" + "\n".join(obs_lines))
        except Exception:
            pass

        try:
            from substrate.reality_model.canonical import CanonicalRealityModel

            canonical = CanonicalRealityModel()
            patterns = canonical.all()[:5]
            if patterns:
                pat_lines = [
                    f"- {p.name}: {p.description[:100]}" for p in patterns if p.description
                ]
                if pat_lines:
                    sections.append("Known patterns:\n" + "\n".join(pat_lines))
        except Exception:
            pass

        try:
            from substrate.organism.universal_work_queue import UniversalWorkQueue

            q = UniversalWorkQueue()
            summary = q.compute_queue_summary()
            approvals = q.get_packets_requiring_approval()
            total = summary.get("total", 0)
            if total > 0:
                queue_text = f"Work queue: {total} packets"
                if approvals:
                    queue_text += f", {len(approvals)} awaiting approval"
                sections.append(queue_text)
        except Exception:
            pass

        if not sections:
            return ""
        return "System awareness (live state):\n" + "\n".join(sections)

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

        reality_context = self._build_reality_context()
        if reality_context:
            prompt_parts.append(f"\n{reality_context}")

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
            from substrate.sockets.intelligence_port import call_with_fallback

            result = call_with_fallback(
                prompt=prompt,
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
                        "label": "Create Engineering Plan",
                        "action": "engineering_plan",
                        "payload": {"intent": content},
                    },
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

        lines = []

        # Provider health
        try:
            from substrate.sockets.intelligence_port import get_model_registry, get_role_slots

            MODEL_REGISTRY = get_model_registry()
            ROLE_SLOTS = get_role_slots()

            healthy = [k for k, c in MODEL_REGISTRY.items() if c.available]
            lines.append(f"**Providers:** {len(healthy)} healthy — {', '.join(healthy) or 'none'}")
        except Exception:
            lines.append("**Providers:** status unavailable")

        # Work packets
        try:
            from substrate.state.runtime_paths import runtime_state_path

            wp_path = runtime_state_path(
                "universal_work", "work_packets.jsonl", create_parent=False
            )
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
            from substrate.state.runtime_paths import runtime_state_dir

            wc_dir = runtime_state_dir("organism", create=False) / "workcells"
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
            from substrate.sockets.intelligence_port import call_with_fallback

            result = call_with_fallback(prompt=prompt, task_type="conversation")
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
        try:
            from substrate.workstation.continuity_engine import ContinuityEngine

            engine = ContinuityEngine()
            result = engine.startup_sequence()

            lines = ["**Starting up.**\n"]

            # Provider status
            prov = result.provider_status
            if "error" in prov:
                lines.append(f"**Providers:** {prov['error']}")
            elif prov.get("healthy"):
                lines.append(
                    f"**Providers:** {len(prov['healthy'])} healthy — {', '.join(prov['healthy'])}"
                )
            else:
                lines.append("**Providers:** status unavailable")

            # Node status
            nodes = result.node_status
            lines.append(f"**VPS:** {nodes.get('vps', 'unknown')}")
            lines.append(f"**Beast:** {nodes.get('beast', 'unknown')}")

            # Continuity
            lines.append(f"**Continuity:** {result.continuity_state}")
            lines.append(f"**Profile:** {result.profile_mode}")

            # Active loops
            if result.active_loops:
                lines.append(
                    f"**Active loops:** {len(result.active_loops)} — "
                    + ", ".join(l["intent"][:40] for l in result.active_loops[:3])
                )

            # Blockers
            if result.open_blockers:
                lines.append(f"**Blockers:** {len(result.open_blockers)}")

            # Approvals
            if result.pending_approvals:
                lines.append(f"**Pending approvals:** {len(result.pending_approvals)}")

            # Resume summary
            if result.resume_summary:
                lines.append(f"\n**While you were away:** {result.resume_summary}")

            # Next action
            if result.recommended_next:
                lines.append(f"\n**Next:** {result.recommended_next}")

            # Errors
            if result.errors:
                lines.append(f"\n**Warnings:** {'; '.join(result.errors)}")

            return AdvisorResponse(
                text="\n".join(lines),
                conversation_id="",
                intent="startup_sequence",
                metadata={
                    "node_status": result.node_status,
                    "continuity_state": result.continuity_state,
                    "profile_mode": result.profile_mode,
                    "active_loops": len(result.active_loops),
                    "open_blockers": len(result.open_blockers),
                    "pending_approvals": len(result.pending_approvals),
                },
                suggested_actions=[
                    {
                        "label": "Full Status",
                        "action": "query",
                        "payload": {"content": "full status"},
                    },
                    {
                        "label": "What's Next?",
                        "action": "query",
                        "payload": {"content": "what should we do next"},
                    },
                ],
            )
        except Exception as exc:
            logger.error("Startup sequence failed: %s", exc)
            return AdvisorResponse(
                text=f"Startup sequence failed: {exc}",
                conversation_id="",
                intent="startup_sequence",
            )

    def _handle_shutdown_sequence(self) -> AdvisorResponse:
        """End-of-day seal — summarize work, save resume point, create report."""
        try:
            from substrate.workstation.continuity_engine import ContinuityEngine

            engine = ContinuityEngine()
            result = engine.shutdown_sequence()

            lines = ["**Shutting down for the day.**\n"]

            if result.completed_work:
                lines.append(f"**Completed:** {', '.join(result.completed_work[:5])}")

            if result.open_loops:
                lines.append(
                    f"**Open loops:** {len(result.open_loops)} — "
                    + ", ".join(l[:40] for l in result.open_loops[:3])
                )

            if result.open_blockers:
                lines.append(f"**Blockers:** {len(result.open_blockers)}")

            if result.pending_approvals:
                lines.append(f"**Pending approvals:** {len(result.pending_approvals)}")

            lines.append(f"\n**Resume point:** {result.resume_point}")

            if result.report_path:
                lines.append(f"**Session report:** {result.report_path}")

            if result.errors:
                lines.append(f"\n**Warnings:** {'; '.join(result.errors)}")

            return AdvisorResponse(
                text="\n".join(lines),
                conversation_id="",
                intent="shutdown_sequence",
                metadata={
                    "resume_point": result.resume_point,
                    "report_path": result.report_path,
                    "open_loops": len(result.open_loops),
                },
                suggested_actions=[
                    {
                        "label": "Review Report",
                        "action": "query",
                        "payload": {"content": "show today's session report"},
                    },
                ],
            )
        except Exception as exc:
            logger.error("Shutdown sequence failed: %s", exc)
            return AdvisorResponse(
                text=f"Shutdown sequence failed: {exc}",
                conversation_id="",
                intent="shutdown_sequence",
            )

    def _handle_engineering_build(self, content: str) -> AdvisorResponse:
        """Route engineering intent to the shared planner and return a plan for approval."""
        try:
            from substrate.meta_ide.shared_planner import get_shared_planner

            planner = get_shared_planner()
            if planner is None:
                return AdvisorResponse(
                    text="Engineering planner unavailable.",
                    conversation_id="",
                    intent="engineering_build",
                )

            plan = planner.create_plan(content)
            task_lines = []
            for i, task in enumerate(plan.tasks):
                desc = task.description if hasattr(task, "description") else str(task)
                task_lines.append(f"  {i + 1}. {desc}")

            lines = [
                "**Engineering Plan Created**\n",
                f"**Goal:** {plan.intent.goal}",
                f"**Type:** {plan.intent.intent_type.value if hasattr(plan.intent.intent_type, 'value') else plan.intent.intent_type}",
                f"**Tasks ({len(plan.tasks)}):**",
                *task_lines,
                f"\n**Plan ID:** `{plan.plan_id}`",
                f"**Status:** {plan.status}",
            ]

            return AdvisorResponse(
                text="\n".join(lines),
                conversation_id="",
                intent="engineering_build",
                metadata={
                    "plan_id": plan.plan_id,
                    "task_count": len(plan.tasks),
                    "intent_type": str(
                        plan.intent.intent_type.value
                        if hasattr(plan.intent.intent_type, "value")
                        else plan.intent.intent_type
                    ),
                },
                suggested_actions=[
                    {
                        "label": "Approve Plan",
                        "action": "approve_engineering_plan",
                        "payload": {"plan_id": plan.plan_id},
                    },
                    {
                        "label": "Reject Plan",
                        "action": "reject_engineering_plan",
                        "payload": {"plan_id": plan.plan_id},
                    },
                    {
                        "label": "Refine Plan",
                        "action": "query",
                        "payload": {"content": f"refine engineering plan {plan.plan_id}"},
                    },
                ],
            )
        except Exception as exc:
            logger.error("Engineering build failed: %s", exc)
            return AdvisorResponse(
                text="Engineering plan creation failed. Check logs for details.",
                conversation_id="",
                intent="engineering_build",
            )

    def _handle_intent_capture(self, content: str) -> AdvisorResponse:
        """Convert high-level operator intent into an IntentContract."""
        try:
            from substrate.workstation.intent_contract import (
                IntentContractManager,
                create_contract_from_intent,
            )

            contract = create_contract_from_intent(operator_intent=content)
            mgr = IntentContractManager()
            mgr.save(contract)

            lines = [
                "**Intent captured.**\n",
                f"**Intent:** {contract.operator_intent}",
                f"**End state:** {contract.desired_end_state}",
                f"**Risk:** {contract.risk_level}",
                f"**Autonomy:** {contract.allowed_autonomy}",
                f"**Max iterations:** {contract.max_iterations}",
                f"**Contract ID:** `{contract.intent_id}`",
            ]

            return AdvisorResponse(
                text="\n".join(lines),
                conversation_id="",
                intent="intent_capture",
                metadata={
                    "intent_id": contract.intent_id,
                    "risk_level": contract.risk_level,
                    "status": contract.status,
                },
                suggested_actions=[
                    {
                        "label": "Start Executing",
                        "action": "query",
                        "payload": {"content": f"execute intent {contract.intent_id}"},
                    },
                    {
                        "label": "Refine Contract",
                        "action": "query",
                        "payload": {"content": f"refine intent {contract.intent_id}"},
                    },
                ],
            )
        except Exception as exc:
            logger.error("Intent capture failed: %s", exc)
            return AdvisorResponse(
                text=f"Intent capture failed: {exc}",
                conversation_id="",
                intent="intent_capture",
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
            try:
                from substrate.workstation.profile_behavior import get_behavior

                behavior = get_behavior(target)
                behavior_info = (
                    f" Voice: {behavior.voice_behavior}."
                    f" Notifications: {behavior.notification_policy}."
                    f" Camera: {behavior.camera_policy}."
                    f" Execution: {behavior.default_execution_mode}."
                )
            except Exception:
                behavior_info = ""

            return AdvisorResponse(
                text=f"Switching to **{target}** mode.{behavior_info}",
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
        """Dispatch a command to a node via the governed mesh dispatch port.

        Routes DOWN through substrate.sockets.mesh_dispatch_port — never a raw
        relay POST. Workstation commands actuate the remote desktop, so they are
        treated as write-class: the port signs a verdict and authenticates to
        the relay before the node executes (fail-closed).
        """
        from substrate.sockets.mesh_dispatch_port import mesh_dispatch

        try:
            result = mesh_dispatch(
                node_id=node_id,
                capability=capability,
                params=params,
                risk_class="reversible_write",
                timeout=15,
            )
        except Exception as exc:
            logger.error("Mesh dispatch failed: %s", exc)
            return AdvisorResponse(
                text=f"Mesh relay unreachable — can't dispatch {capability} to {node_id}. ({exc})",
                conversation_id="",
                intent=intent,
                metadata={"ok": False, "status": "relay_unreachable", "error": str(exc)},
            )
        if not result.get("ok") and result.get("status") in (
            "relay_secret_unset",
            "verdict_secret_unset",
            "transport_error",
            "dispatcher_unregistered",
        ):
            return AdvisorResponse(
                text=f"Mesh dispatch blocked ({result.get('status')}) — can't run {capability} on {node_id}.",
                conversation_id="",
                intent=intent,
                metadata={
                    "ok": False,
                    "status": result.get("status"),
                    "error": result.get("error", ""),
                },
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
            with open(_conversations_path(), "a") as f:
                f.write(json.dumps(entry, default=str, separators=(",", ":")) + "\n")
        except Exception as exc:
            logger.debug("Failed to persist conversation turn: %s", exc)

    def _load_history(self, conversation_id: str) -> list[dict[str, Any]]:
        turns: list[dict[str, Any]] = []
        try:
            if not os.path.exists(_conversations_path()):
                return turns
            with open(_conversations_path()) as f:
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
