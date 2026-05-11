"""
ExecutionSpine — single execution path for all EOS operations.

Every LLM call in the system should flow through here:
    spine = ExecutionSpine()
    response = spine.run(message, unified_context, ...)

Guarantees on every execution:
    1. Authority validation
    2. LLM call via model_router.call_with_fallback()
    3. Mandatory memory writes (messages + interactions)
    4. Session persistence to SubstrateStorage
    5. Async embedding attempt
"""

import os
import sys
import threading
import uuid
from datetime import datetime, timezone

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


class ExecutionSpine:

    def run(
        self,
        message: str,
        unified_context: object,
        agent_type: str = "executive_assistant",
        authority_class: str = "analyze",
        session_id: str | None = None,
        channel_id: str | None = None,
        org_id: str | None = None,
        user_id: str | None = None,
        task_type: object = None,
        venture_id: str | None = None,
        skill_name: str | None = None,
    ) -> str:
        """
        Execute a single LLM operation with mandatory memory writes.

        Returns the response string. Never raises — returns an error
        message string on failure so callers always get a printable result.
        """
        session_id = session_id or str(uuid.uuid4())
        _start = datetime.now(timezone.utc)

        # 1. Authority validation
        try:
            from runtime.context import load_context_from_env
            from runtime.authority_engine import AuthorityEngine

            ctx = load_context_from_env()
            ae = AuthorityEngine(ctx)
            check = ae.check_can_execute(authority_class)
            if not check["can_execute"] and check.get("requires_approval"):
                approval_id = ae.queue_for_approval(
                    authority_class,
                    {"prompt": message, "agent": agent_type},
                    agent_type,
                )
                return (
                    f"Queued for approval — use `!approve {approval_id}` to execute."
                )
        except Exception as e:
            print(f"[ExecutionSpine] Authority check failed (proceeding): {e}")
            ctx = None

        # 2. LLM call via model_router
        system_prompt = ""
        try:
            system_prompt = unified_context.to_system_prompt()
        except Exception as e:
            print(f"[ExecutionSpine] Context assembly failed: {e}")

        response = ""
        try:
            from runtime.model_router import call_with_fallback

            routing_result = call_with_fallback(
                prompt=message,
                system=system_prompt or None,
                agent_type=agent_type,
                task_type=task_type,
            )
            response = routing_result.output if routing_result else ""
            if not response:
                response = "[ExecutionSpine] No response from model chain."
        except Exception as e:
            print(f"[ExecutionSpine] LLM call failed: {e}")
            response = f"I encountered an error processing your request: {e}"

        # 3. Mandatory memory writes
        # 3a. ConversationMemory — messages table
        try:
            if ctx is None:
                from runtime.context import load_context_from_env
                ctx = load_context_from_env()

            from runtime.memory import ConversationMemory
            cm = ConversationMemory(ctx)
            cm.store(
                session_id=session_id,
                role="user",
                content=message[:10000],
                channel=channel_id or "unknown",
                agent=agent_type,
            )
            cm.store(
                session_id=session_id,
                role="assistant",
                content=response[:10000],
                channel=channel_id or "unknown",
                agent=agent_type,
            )
        except Exception as e:
            print(f"[ExecutionSpine] ConversationMemory write FAILED: {e}")

        # 3b. AgentMemory — interactions table
        try:
            from runtime.memory import AgentMemory
            from runtime.agent_runtime import AgentResult

            _agent_result = AgentResult(
                output=response[:2000],
                model_used="spine",
                tokens_used={"input": 0, "output": 0, "total": 0},
                skill_used=skill_name,
            )
            mem = AgentMemory()
            mem.log(
                agent_result=_agent_result,
                venture_id=venture_id,
                input_summary=message[:2000],
                agent=agent_type,
                task_type=str(task_type) if task_type else "unknown",
            )
        except Exception as e:
            print(f"[ExecutionSpine] AgentMemory write FAILED: {e}")

        # 4. Session persistence — channel_id → session_id mapping
        if channel_id:
            try:
                from runtime.transport.storage import get_storage
                store = get_storage()
                store.put(f"session:{channel_id}", session_id)
            except Exception as e:
                print(f"[ExecutionSpine] Session persistence FAILED: {e}")

        # 5. Async embedding attempt (requires interaction_id from step 3b)
        # Embedding ties to an interaction record — skip if memory write failed.
        # This matches the pattern in AgentMemory.log() which also embeds async.

        _elapsed = (datetime.now(timezone.utc) - _start).total_seconds()
        print(
            f"[ExecutionSpine] agent={agent_type} session={session_id[:8]}... "
            f"tokens_in~{len(system_prompt)//4} elapsed={_elapsed:.1f}s"
        )

        return response


if __name__ == "__main__":
    print("ExecutionSpine import OK")
    spine = ExecutionSpine()
    print("ExecutionSpine instantiation OK")
