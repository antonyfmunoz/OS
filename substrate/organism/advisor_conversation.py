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

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_api_dict(self) -> dict[str, Any]:
        return asdict(self)


class AdvisorConversation:
    """Multi-turn conversational advisor with intent routing."""

    _MAX_TURNS = 20
    _MAX_CONTEXT_CHARS = 2048

    def __init__(self, advisor: Any, store: Any | None = None) -> None:
        self._advisor = advisor
        self._store = store
        self._histories: dict[str, list[dict[str, Any]]] = {}
        os.makedirs(os.path.dirname(_CONVERSATIONS_PATH), exist_ok=True)

    def converse(
        self,
        content: str,
        conversation_id: str = "",
        view_context: dict[str, Any] | None = None,
        source: str = "text",
    ) -> AdvisorResponse:
        if not conversation_id:
            conversation_id = f"conv-{uuid.uuid4().hex[:12]}"

        if conversation_id not in self._histories:
            self._histories[conversation_id] = self._load_history(conversation_id)

        history = self._histories[conversation_id]

        from substrate.workstation.command_router import (
            CommandIntent,
            classify_intent,
        )

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
        elif intent == CommandIntent.WORKSTATION_CONTROL:
            response = self._handle_workstation_control(content)
        elif intent == CommandIntent.CONTINUITY_TRANSITION:
            response = self._handle_continuity_transition(content)
        elif intent == CommandIntent.STARTUP_SEQUENCE:
            response = self._handle_startup_sequence()
        else:
            response = self._handle_advisor_signal(content, context_summary)

        response.conversation_id = conversation_id
        response.intent = intent.value

        self._save_turn(conversation_id, "operator", content, view_context)
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

        return response

    def _handle_conversation(
        self,
        content: str,
        conversation_id: str,
        history: list[dict[str, Any]],
        view_context: dict[str, Any] | None,
        context_summary: str,
    ) -> AdvisorResponse:
        from substrate.state.business.business_instance import get_ai_name

        ai_name = get_ai_name() or "Assistant"
        prompt_parts = [
            f"You are {ai_name}, a strategic advisor and executive assistant for UMH "
            f"(Universal Mastery Hierarchy). You are the operator's primary conversational "
            f"partner — a co-founder-level thinker who brainstorms, plans, reviews, and "
            f"helps make decisions. Be direct, insightful, and actionable. Do not hedge. "
            f"You have access to the UMH cockpit, work packets, agents, and Claude Code "
            f"sessions.",
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
        try:
            result = self._advisor.handle_signal("what should resume next")
            text = self._format_advisor_result(result)
            return AdvisorResponse(
                text=text,
                conversation_id="",
                intent="resume_query",
                suggested_actions=[
                    {
                        "label": "Open Command Center",
                        "action": "navigate",
                        "payload": {"panel": "commandcenter"},
                    },
                    {
                        "label": "Show Blocked",
                        "action": "query",
                        "payload": {"content": "what is blocked"},
                    },
                ],
            )
        except Exception as exc:
            return AdvisorResponse(
                text=f"Resume query failed: {exc}",
                conversation_id="",
                intent="resume_query",
            )

    def _handle_status(self, content: str) -> AdvisorResponse:
        try:
            result = self._advisor.handle_signal(content)
            text = self._format_advisor_result(result)
            if text and text not in ("Signal processed.", "No response from advisor.", ""):
                return AdvisorResponse(
                    text=text,
                    conversation_id="",
                    intent="status_query",
                    suggested_actions=[
                        {
                            "label": "Open Command Center",
                            "action": "navigate",
                            "payload": {"panel": "commandcenter"},
                        },
                        {
                            "label": "What's Next?",
                            "action": "query",
                            "payload": {"content": "what should we do next"},
                        },
                    ],
                )
        except Exception as exc:
            logger.debug("Advisor status failed, using deterministic: %s", exc)

        text = self._deterministic_status()
        return AdvisorResponse(
            text=text,
            conversation_id="",
            intent="status_query",
            metadata={"model_tier": "deterministic", "model": "fallback"},
            suggested_actions=[
                {
                    "label": "Open Command Center",
                    "action": "navigate",
                    "payload": {"panel": "commandcenter"},
                },
            ],
        )

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
                "desktop.screenshot", {},
                "Taking a screenshot.",
                "workstation_control",
            )

        if action == "list_windows":
            return self._execute_workstation_command(
                "desktop.list_windows", {},
                "Listing open windows.",
                "workstation_control",
            )

        if action.startswith("media_"):
            return AdvisorResponse(
                text=f"Media control: {action.replace('media_', '')}.",
                conversation_id="",
                intent="workstation_control",
                metadata={"action": action, "target": target},
                suggested_actions=[
                    {"label": "List Windows", "action": "query", "payload": {"content": "list windows"}},
                ],
            )

        if requires_approval or risk == "high":
            desc = f"{action} {app}".strip() if app else "this"
            return AdvisorResponse(
                text=f"That requires approval — {desc} is a high-risk external action.",
                conversation_id="",
                intent="workstation_control",
                metadata={"action": action, "target": target, "blocked": True},
                suggested_actions=[
                    {"label": "Approve", "action": "approve", "payload": {"command": content}},
                ],
            )

        if app:
            process = target.get("process_name", "")
            url = target.get("target_url", "")
            if action == "focus" and process:
                return self._execute_workstation_command(
                    "desktop.focus_window", {"process": process},
                    f"Focusing {app}.",
                    "workstation_control",
                )
            if url:
                return self._execute_workstation_command(
                    "shell.powershell", {"command": f'Start-Process "{url}"'},
                    f"Opening {app}.",
                    "workstation_control",
                )
            if process:
                return self._execute_workstation_command(
                    "shell.powershell", {"command": f'Start-Process "{process}"'},
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
                {"label": "List Windows", "action": "query", "payload": {"content": "what windows are open"}},
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

        try:
            from adapters.models.model_router import MODEL_REGISTRY
            healthy = [k for k, c in MODEL_REGISTRY.items() if c.available]
            lines.append(f"**Providers:** {len(healthy)} healthy — {', '.join(healthy) or 'none'}")
        except Exception:
            lines.append("**Providers:** status unavailable")

        try:
            import urllib.request
            req = urllib.request.Request("http://localhost:8091/health", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                lines.append("**VPS API:** healthy")
        except Exception:
            lines.append("**VPS API:** unreachable")

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
            suggested_actions=[
                {"label": "Full Status", "action": "query", "payload": {"content": "full status"}},
                {"label": "What's Next?", "action": "query", "payload": {"content": "what should we do next"}},
            ],
        )

    def _execute_workstation_command(
        self,
        capability: str,
        params: dict[str, Any],
        success_text: str,
        intent: str,
    ) -> AdvisorResponse:
        """Send a command to the workstation node via the mesh."""
        import json as _json
        from pathlib import Path

        desktop_node = None
        mesh_file = Path(
            os.environ.get("UMH_ROOT", "/opt/OS"),
            "data", "runtime", "mesh_nodes.json",
        )
        try:
            if mesh_file.exists():
                nodes = _json.loads(mesh_file.read_text())
                for node in nodes:
                    if "desktop" in node.get("capabilities", []):
                        if node.get("status") == "connected":
                            desktop_node = node.get("id", node.get("name", "unknown"))
                            break
        except Exception:
            pass

        if not desktop_node:
            return AdvisorResponse(
                text=f"No workstation node online — can't execute {capability}.",
                conversation_id="",
                intent=intent,
                metadata={"blocked": True, "reason": "workstation_offline"},
            )

        return AdvisorResponse(
            text=success_text,
            conversation_id="",
            intent=intent,
            metadata={"capability": capability, "params": params, "routed_to": desktop_node},
            suggested_actions=[
                {"label": "List Windows", "action": "query", "payload": {"content": "list windows"}},
            ],
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
    ) -> None:
        entry = {
            "conversation_id": conversation_id,
            "message_id": f"conv-{uuid.uuid4().hex[:12]}",
            "role": role,
            "content": content[:5000],
            "view_context_summary": self._build_context_summary(view_context),
            "intent": intent,
            "suggested_actions": suggested_actions or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
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
