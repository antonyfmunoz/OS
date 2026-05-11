"""
ContextBuilder — single-pass context assembly for the execution spine.

Replaces the 25 manual injection steps in cognitive_loop.py with one call:
    builder = ContextBuilder()
    ctx_result = builder.build(ctx, message, session_id, ...)

Every source is wrapped in its own try/except so one failure cannot break
the entire context assembly. Fields that fail are set to None.
"""

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_REPO_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
_ROOT = Path(_REPO_ROOT)

from runtime.context import EOSContext


@dataclass
class UnifiedContext:
    # Layer 0: AI identity + standards
    ai_identity: str | None = None
    ea_standards: str | None = None
    signal_classification: dict | None = None
    signal_prompt: str | None = None
    quality_enhancement: str | None = None

    # Layer 1d: BIS / tenant
    bis_prompt: str | None = None
    north_star: str | None = None

    # Layer 1e: Knowledge domains
    gws_docs: str | None = None
    founder_profile: str | None = None
    brand_identity: str | None = None
    funnel_strategy: str | None = None
    workbook_framework: str | None = None
    pattern_context: str | None = None
    decision_log: str | None = None
    dex_learnings: str | None = None
    notebooklm_insights: str | None = None

    # Layer 1f: Primitives
    primitives: str | None = None

    # Layer 1h: Hierarchy
    hierarchy: str | None = None

    # Runtime context
    calendar: str | None = None
    human_intelligence: str | None = None
    semantic_memory: str | None = None
    conversation_history: str | None = None
    confidentiality: str | None = None
    martell_patterns: str | None = None
    no_list: str | None = None
    intent_context: str | None = None
    world_model_context: str | None = None

    # Metadata
    estimated_tokens: int = 0
    compacted: bool = False
    failed_sources: list[str] = field(default_factory=list)

    def to_system_prompt(self) -> str:
        """Assemble all non-None fields into a single system prompt string."""
        parts = []
        for fname, val in self.__dict__.items():
            if fname in ("estimated_tokens", "compacted", "failed_sources"):
                continue
            if val is not None and isinstance(val, str) and val.strip():
                parts.append(val)
        return "\n\n".join(parts)


class ContextBuilder:

    def build(
        self,
        ctx: EOSContext,
        message: str,
        session_id: str,
        agent: str = "executive_assistant",
        venture_id: str | None = None,
        channel: str = "",
        conversation_memory: Any = None,
    ) -> UnifiedContext:
        uc = UnifiedContext()

        # Layer 0: AI Identity
        try:
            from runtime.ai_identity import AIIdentityEngine
            uc.ai_identity = AIIdentityEngine().get_foundation_prompt()
        except Exception as e:
            uc.failed_sources.append(f"ai_identity: {e}")

        # Layer 0a: EA standards (EA/DEX agents only)
        _ea_agents = ("executive_assistant", "dex", "ea", None)
        if agent in _ea_agents or (agent and "ea" in agent.lower()):
            try:
                from runtime.ea_operational_standards import get_all_standards
                standards = get_all_standards()
                uc.ea_standards = f"## Operating Standards\n{standards}"
            except Exception as e:
                uc.failed_sources.append(f"ea_standards: {e}")

        # Layer 0b: Signal classification
        try:
            from runtime.signal_hierarchy import SignalHierarchyEngine
            she = SignalHierarchyEngine(ctx=ctx)
            uc.signal_classification = she.classify_input(message or "", channel="unknown")
            prompt = she.format_for_prompt(uc.signal_classification)
            if prompt:
                uc.signal_prompt = prompt
        except Exception as e:
            uc.failed_sources.append(f"signal_hierarchy: {e}")

        # Layer 0c: Quality requirements
        try:
            from runtime.quality_gate import QualityTransformationGate, TransformationResult
            qtg = QualityTransformationGate(ctx)
            pre_result = TransformationResult(
                original="", transformed="",
                reality_score=0.5, intelligence_score=0.5,
                personalization_score=0.5, execution_score=0.5,
                overall_score=0.5, transformations_applied=[],
                is_world_class=False,
            )
            enhancement = qtg.get_enhancement_prompt(
                pre_result, uc.signal_classification or {}
            )
            if enhancement:
                uc.quality_enhancement = enhancement
        except Exception as e:
            uc.failed_sources.append(f"quality_gate: {e}")

        # Layer 1d: BIS / TenantManager
        try:
            from runtime.tenant import TenantManager
            tm = TenantManager(ctx)
            bis_prompt = tm.format_for_prompt()
            if bis_prompt and bis_prompt.strip():
                uc.bis_prompt = bis_prompt
            else:
                uc.bis_prompt = "INSTANCE CONTEXT:\nStage: pre-revenue\nLoad BIS for full context."
        except Exception:
            uc.bis_prompt = (
                "INSTANCE CONTEXT:\nStage: pre-revenue\n"
                "BIS unavailable — operating with minimal context."
            )

        # Layer 1e: GWS document context
        try:
            gws_path = _ROOT / "data" / "gws_context.md"
            if gws_path.exists():
                raw = gws_path.read_text()
                preview = raw[:600].strip()
                if preview:
                    uc.gws_docs = f"FOUNDER DOCS (Google Drive):\n{preview}"
        except Exception as e:
            uc.failed_sources.append(f"gws_docs: {e}")

        # Layer 1e-ii: Founder profile
        try:
            profile_path = _ROOT / "data" / "founder_profile.md"
            if profile_path.exists():
                raw = profile_path.read_text()
                preview = raw[:300].strip()
                if preview:
                    uc.founder_profile = f"FOUNDER PROFILE:\n{preview}"
        except Exception as e:
            uc.failed_sources.append(f"founder_profile: {e}")

        # Layer 1e-iii: Brand identity
        try:
            brand_path = _ROOT / "data" / "brand_identity.md"
            if brand_path.exists():
                raw = brand_path.read_text()
                preview = raw[:500].strip()
                if preview:
                    uc.brand_identity = f"BRAND IDENTITY:\n{preview}"
        except Exception as e:
            uc.failed_sources.append(f"brand_identity: {e}")

        # Layer 1e-iv: Funnel strategy
        try:
            funnel_path = _ROOT / "data" / "funnel_strategy.md"
            if funnel_path.exists():
                raw = funnel_path.read_text()
                preview = raw[:400].strip()
                if preview:
                    uc.funnel_strategy = f"FUNNEL STRATEGY:\n{preview}"
        except Exception as e:
            uc.failed_sources.append(f"funnel_strategy: {e}")

        # Layer 1e-v: Workbook framework
        try:
            wb_path = _ROOT / "data" / "workbook_framework.md"
            if wb_path.exists():
                raw = wb_path.read_text()
                preview = raw[:300].strip()
                if preview:
                    uc.workbook_framework = f"WORKBOOK FRAMEWORK:\n{preview}"
        except Exception as e:
            uc.failed_sources.append(f"workbook_framework: {e}")

        # Layer 1e-vi: Cross-session behavioral patterns
        try:
            from runtime.pattern_engine import PatternEngine
            pe = PatternEngine(ctx)
            patterns = pe.analyze(days_back=14)
            if patterns:
                uc.pattern_context = pe.inject_to_context(patterns)
        except Exception as e:
            uc.failed_sources.append(f"pattern_engine: {e}")

        # Layer 1e-vii: Decision log
        try:
            from runtime.decision_log import DecisionLog
            dl = DecisionLog(ctx)
            decisions = dl.get_recent_decisions(
                venture_id=venture_id or "", limit=5,
            )
            if decisions:
                uc.decision_log = dl.format_for_context(decisions)
        except Exception as e:
            uc.failed_sources.append(f"decision_log: {e}")

        # Layer 1e-vii-b: DEX learnings
        try:
            from runtime.db import get_conn
            with get_conn(ctx.org_id) as cur:
                cur.execute(
                    """
                    SELECT payload_json FROM events
                    WHERE org_id = %s AND event_type = 'dex_learning'
                    ORDER BY created_at DESC LIMIT 10
                    """,
                    (str(ctx.org_id),),
                )
                learnings = cur.fetchall()
            if learnings:
                lines = []
                for lr in learnings:
                    lp = lr["payload_json"]
                    if isinstance(lp, str):
                        lp = json.loads(lp)
                    lq = lp.get("question", "")
                    la = lp.get("answer", "")
                    if lq and la:
                        lines.append(f"Q: {lq} → A: {la}")
                if lines:
                    uc.dex_learnings = (
                        "## What Antony Has Taught DEX\n" + "\n".join(lines[:10])
                    )
        except Exception as e:
            uc.failed_sources.append(f"dex_learnings: {e}")

        # Layer 1e-viii: NotebookLM insights
        try:
            from runtime.notebooklm_sync import NotebookLMSync
            nls = NotebookLMSync(ctx)
            insights = nls.get_recent_insights(
                venture_id=venture_id or "", limit=3,
            )
            if insights:
                nlm_lines = [
                    f"NLM: {i.get('answer', '')[:100]}"
                    for i in insights if i.get("answer")
                ]
                if nlm_lines:
                    uc.notebooklm_insights = (
                        "NOTEBOOKLM INSIGHTS:\n" + "\n".join(nlm_lines)
                    )
        except Exception as e:
            uc.failed_sources.append(f"notebooklm_insights: {e}")

        # Layer 1f: Primitives
        try:
            from runtime.primitives import PrimitiveRegistry
            pr = PrimitiveRegistry(ctx)
            prim_ctx = pr.compose_business_context(
                venture_id or getattr(ctx, "active_venture_id", "") or ""
            )
            block = prim_ctx.strip()[:800] if prim_ctx else ""
            if block:
                uc.primitives = block
        except Exception as e:
            uc.failed_sources.append(f"primitives: {e}")

        # Layer 1d (north star): BIS north star + stage
        try:
            from runtime.business_instance import BusinessInstanceManager
            bim = BusinessInstanceManager(ctx)
            bis = bim.get_bis(
                venture_id or getattr(ctx, "active_venture_id", "") or ""
            )
            if bis and bis.north_star:
                block = f"North star: {bis.north_star}"
                if bis.stage_name:
                    block += f" | Stage: {bis.current_stage} ({bis.stage_name})"
                uc.north_star = block
        except Exception as e:
            uc.failed_sources.append(f"north_star: {e}")

        # Layer 1h: Hierarchy
        try:
            from runtime.agent_hierarchy import AgentHierarchy
            ah = AgentHierarchy()
            skip_agents = ("default", "gateway.direct", "prompt_engine", "quality_checker")
            if agent and agent not in skip_agents:
                h_full = ah.format_for_prompt(agent)
                if h_full:
                    h_lines = [l for l in h_full.splitlines() if l.strip()][:2]
                    uc.hierarchy = "\n".join(h_lines)
        except Exception as e:
            uc.failed_sources.append(f"hierarchy: {e}")

        # Calendar context
        try:
            from runtime.gws_connector import GWSConnector
            gws = GWSConnector()
            events = gws.get_today_events()
            if events:
                cal_text = "TODAY'S SCHEDULE:\n"
                for ev in events[:3]:
                    title = ev.get("title", "")
                    start = ev.get("start", "all day")
                    if start and "T" in str(start):
                        start = str(start).split("T")[1][:5]
                    cal_text += f"  {start} {title}\n"
                uc.calendar = cal_text
        except Exception as e:
            uc.failed_sources.append(f"calendar: {e}")

        # Human intelligence
        try:
            from runtime.human_intelligence import HumanIntelligenceEngine
            from runtime.db import get_conn
            hi = HumanIntelligenceEngine(ctx)
            text_lower = (message or "").lower()
            with get_conn(ctx.org_id) as hi_cur:
                hi_cur.execute(
                    "SELECT username FROM human_profiles WHERE org_id = %s",
                    (ctx.org_id,),
                )
                known = [r["username"] for r in hi_cur.fetchall()]
            for uname in known:
                if uname and uname.lower() in text_lower:
                    rel_brief = hi.get_relationship_context(uname)
                    if rel_brief:
                        uc.human_intelligence = rel_brief
                    break
        except Exception as e:
            uc.failed_sources.append(f"human_intelligence: {e}")

        # Semantic memory
        try:
            from runtime.memory import AgentMemory
            mem = AgentMemory()
            if message and len(message.split()) >= 3:
                hits = mem.semantic_search(
                    query=message, limit=3,
                    min_similarity=0.60, venture_id=venture_id,
                )
                if hits:
                    block = "## Relevant Past Context (semantic memory)\n"
                    for hit in hits:
                        sim = hit.get("similarity", 0)
                        date = (hit.get("created_at") or "")[:10]
                        inp = str(hit.get("input_summary") or "")[:150]
                        out = str(hit.get("output_summary") or "")[:200]
                        block += f"\n[{date} | similarity: {sim}]\n"
                        if inp:
                            block += f"Input: {inp}\n"
                        if out:
                            block += f"Output: {out}\n"
                    uc.semantic_memory = block
        except Exception as e:
            uc.failed_sources.append(f"semantic_memory: {e}")

        # Conversation history
        try:
            if session_id and conversation_memory:
                cm = conversation_memory
                if channel:
                    history = cm.format_channel_history_for_prompt(
                        channel, query=message
                    )
                else:
                    history = cm.format_session_for_prompt(session_id)
                if history and history.strip():
                    uc.conversation_history = (
                        f"## Conversation History (this session)\n{history}"
                    )
        except Exception as e:
            uc.failed_sources.append(f"conversation_history: {e}")

        # Confidentiality
        try:
            from runtime.confidentiality import detect_confidential_context
            conf = detect_confidential_context(message)
            if conf.get("is_confidential"):
                level = conf.get("level", "restricted")
                uc.confidentiality = (
                    f"## Confidentiality Alert\nLevel: {level}\n"
                    f"{conf.get('recommendation', '')}\n"
                    "Do not log sensitive details. "
                    "Acknowledge confidentiality in response."
                )
        except Exception as e:
            uc.failed_sources.append(f"confidentiality: {e}")

        # Martell patterns
        try:
            from runtime.martell_patterns import (
                detect_leverage_killer, check_solution_standard,
            )
            assassin = detect_leverage_killer(message)
            if assassin and assassin.get("intervention"):
                uc.martell_patterns = (
                    f"## Behavioral Alert\n{assassin['intervention']}\n"
                    "Note: Surface this observation to the founder in your response."
                )
            if check_solution_standard(message):
                sol = (
                    "## Solution Standard Alert\n"
                    "The founder is presenting a problem without options. "
                    "Apply the Solution Standard: acknowledge the problem, then ask "
                    "for or present 3 options with a clear recommendation."
                )
                if uc.martell_patterns:
                    uc.martell_patterns += f"\n\n{sol}"
                else:
                    uc.martell_patterns = sol
        except Exception as e:
            uc.failed_sources.append(f"martell_patterns: {e}")

        # No List enforcement
        try:
            from runtime.founder_rate import check_against_no_list
            violations = check_against_no_list(message)
            if violations:
                uc.no_list = (
                    "## No List Alert\n"
                    "The following items are on Antony's No List and appear "
                    f"in this message: {', '.join(violations)}\n"
                    "Flag this to Antony — he has committed to never doing these."
                )
        except Exception as e:
            uc.failed_sources.append(f"no_list: {e}")

        # Intent detection
        try:
            from runtime.cognitive_loop import (
                detect_intent_and_inject, _format_intent_context,
            )
            intent_data = detect_intent_and_inject(
                text=message, req={}, ctx=ctx,
            )
            if intent_data and intent_data.get("intent"):
                uc.intent_context = (
                    f"## Intent Detected: {intent_data.get('intent', '')}\n"
                    + _format_intent_context(intent_data)
                )
        except Exception as e:
            uc.failed_sources.append(f"intent_detection: {e}")

        # World model context — canonical + instance entries relevant to this message
        try:
            from runtime.world_model import WorldModel
            _wm = WorldModel(org_id=str(ctx.org_id))
            _wm_ctx = _wm.get_context_for_prompt(message)
            if _wm_ctx:
                uc.world_model_context = _wm_ctx
        except Exception as e:
            uc.failed_sources.append(f"world_model: {e}")

        # Token estimation + compaction check
        system_prompt = uc.to_system_prompt()
        uc.estimated_tokens = len(system_prompt) // 4
        if uc.estimated_tokens > 140_000:
            try:
                from runtime.context_compaction import ContextCompactor
                compactor = ContextCompactor(ctx)
                messages = [{"role": "system", "content": system_prompt}]
                brief = compactor.compact(messages, session_id)
                seeded = compactor.build_seeded_context(brief)
                uc.conversation_history = seeded
                uc.compacted = True
                uc.estimated_tokens = len(uc.to_system_prompt()) // 4
            except Exception as e:
                uc.failed_sources.append(f"compaction: {e}")

        return uc


if __name__ == "__main__":
    from runtime.context import EOSContext
    import os

    ctx = EOSContext(
        org_id=os.getenv("EOS_ORG_ID", "test"),
        user_id=os.getenv("EOS_USER_ID", "test"),
        active_venture_id="lyfe_institute",
    )
    builder = ContextBuilder()
    result = builder.build(ctx, "test message", "test_session")
    print("ContextBuilder OK")
    for f, value in result.__dict__.items():
        status = "OK" if value is not None else "EMPTY"
        print(f"  {f}: {status}")
