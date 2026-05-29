from substrate.state.context.context import SubstrateContext
from substrate.state.storage.db import get_conn
from substrate.types import PermissionTier, RiskClass, required_tier_for_action
import json, uuid
from datetime import datetime, timezone

ACTION_RISK_MAP: dict[str, RiskClass] = {}
_ACTION_RISK_TABLE: dict[RiskClass, list[str]] = {
    RiskClass.CRITICAL: [
        "send_message",
        "send_email",
        "execute_payment",
        "delete_records",
        "bulk_update",
        "mass_outreach",
        "publish_content",
    ],
    RiskClass.HIGH: ["send_dm", "create_outreach", "post_content", "update_external_crm", "book_call"],
    RiskClass.MEDIUM: ["draft_message", "draft_content", "create_task", "create_document"],
    RiskClass.LOW: [
        "analyze",
        "research",
        "score",
        "classify",
        "summarize",
        "read",
        "query",
        "report",
        "draft_brief",
        "generate_brief",
        "research_prospect",
        "extract_profile",
    ],
}
for _rc, _actions in _ACTION_RISK_TABLE.items():
    for _a in _actions:
        ACTION_RISK_MAP[_a] = _rc

RISK_CLASSES = {rc.value.upper(): actions for rc, actions in _ACTION_RISK_TABLE.items()}

AUTONOMY_LEVEL_MAP = {
    "draft_only": 0,
    "manual": 1,
    "low_risk_auto": 1,
    "medium_risk_log": 2,
    "hybrid": 3,
    "high_risk_delay": 3,
    "all_except_commit": 4,
    "autonomous": 4,
    "full_autonomy": 5,
}

MIN_LEVEL_TO_EXECUTE: dict[RiskClass, int] = {
    RiskClass.LOW: 0,
    RiskClass.MEDIUM: 2,
    RiskClass.HIGH: 3,
    RiskClass.CRITICAL: 999,
}

AUTONOMY_LEVEL_RESTRICTIONS = {
    5: {"blocked_departments": ["finance", "legal"]},
}


class AuthorityEngine:
    def __init__(self, ctx: SubstrateContext):
        self.ctx = ctx
        self._org_autonomy = self._load_org_autonomy()

    def _load_org_autonomy(self) -> int:
        with get_conn(self.ctx.org_id) as cur:
            cur.execute(
                "SELECT autonomy_stage FROM organizations WHERE id = %s", (self.ctx.org_id,)
            )
            row = cur.fetchone()
            stage = row["autonomy_stage"] if row else "manual"
            return AUTONOMY_LEVEL_MAP.get(stage, 1)

    def classify_action(self, action_type: str) -> RiskClass:
        return ACTION_RISK_MAP.get(action_type, RiskClass.LOW)

    def get_autonomy_level(self, workflow_id: str | None = None) -> int:
        if workflow_id:
            try:
                with get_conn(self.ctx.org_id) as cur:
                    cur.execute(
                        "SELECT autonomy_stage FROM workflows WHERE id = %s AND org_id = %s",
                        (workflow_id, self.ctx.org_id),
                    )
                    row = cur.fetchone()
                    if row:
                        return AUTONOMY_LEVEL_MAP.get(row["autonomy_stage"], 1)
            except Exception:
                pass
        return self._org_autonomy

    def check_can_execute(
        self,
        action_type: str,
        workflow_id: str | None = None,
        caller_permission_tier: str = "execute",
    ) -> dict:
        try:
            caller_tier = PermissionTier(caller_permission_tier)
        except ValueError:
            caller_tier = PermissionTier.EXECUTE

        required = required_tier_for_action(action_type)
        if not caller_tier.permits(required):
            return {
                "can_execute": False,
                "requires_approval": False,
                "reason": f"Permission tier {caller_tier.value} cannot perform {action_type} (requires {required.value})",
                "autonomy_level": self.get_autonomy_level(workflow_id),
                "risk_class": self.classify_action(action_type).value.upper(),
                "permission_tier": caller_tier.value,
                "required_tier": required.value,
            }

        risk_class = self.classify_action(action_type)
        autonomy_level = self.get_autonomy_level(workflow_id)
        min_level = MIN_LEVEL_TO_EXECUTE.get(risk_class, 0)
        requires_approval = risk_class in (RiskClass.HIGH, RiskClass.CRITICAL)

        if required == PermissionTier.COMMIT:
            requires_approval = True

        can_execute = autonomy_level >= min_level and risk_class != RiskClass.CRITICAL
        risk_str = risk_class.value.upper()
        return {
            "can_execute": can_execute,
            "requires_approval": requires_approval,
            "reason": f"{risk_str} action requires autonomy level {min_level}+, current level {autonomy_level}",
            "autonomy_level": autonomy_level,
            "risk_class": risk_str,
            "permission_tier": caller_tier.value,
            "required_tier": required.value,
        }

    def queue_for_approval(self, action_type: str, payload: dict, agent: str) -> str:
        from substrate.state.stores.approval_store import ApprovalStore

        return ApprovalStore().create_approval(
            org_id=self.ctx.org_id,
            request={
                "action_type": action_type,
                "payload": payload,
                "agent": agent,
            },
        )

    def execute_or_queue(self, action_type: str, payload: dict, agent: str, execute_fn) -> dict:
        check = self.check_can_execute(action_type)
        if check["can_execute"] and not check["requires_approval"]:
            result = execute_fn(payload)
            return {"status": "executed", "result": result}
        else:
            approval_id = self.queue_for_approval(action_type, payload, agent)
            return {
                "status": "pending_approval",
                "approval_id": approval_id,
                "reason": check["reason"],
            }

    def approve(self, approval_id: str) -> dict:
        from substrate.state.stores.approval_store import ApprovalStore

        result = ApprovalStore().approve(
            org_id=self.ctx.org_id,
            approval_id=approval_id,
            resolved_by=self.ctx.user_id,
        )
        if not result:
            return {"error": "approval not found"}

        request = result.get("request_json") or {}
        if isinstance(request, str):
            import json as _json

            try:
                request = _json.loads(request)
            except Exception:
                request = {}
        if request.get("action_type") == "new_agent_proposal":
            try:
                agent_spec = request.get("proposed_agent", {})
                self._create_agent_soul_doc(agent_spec)
            except Exception as e:
                print(f"[AuthorityEngine] Soul doc write failed: {e}")

        return {"status": "approved", "request": result.get("request_json")}

    def _create_agent_soul_doc(self, agent_spec: dict) -> None:
        """Write a soul doc to agents/ when a new agent is approved."""
        from pathlib import Path

        agents_dir = Path(__file__).parent.parent / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        name = agent_spec.get("name", "new_agent")
        slug = name.lower().replace(" ", "_").replace("-", "_")
        soul_doc = agents_dir / f"{slug}.md"

        domain_rules = agent_spec.get("domain_rules", [])
        if isinstance(domain_rules, list):
            rules_block = "\n".join(f"- {r}" for r in domain_rules)
        else:
            rules_block = str(domain_rules)

        suggested_skills = agent_spec.get("suggested_skills", [])
        if isinstance(suggested_skills, list):
            skills_block = "\n".join(f"- {s}" for s in suggested_skills)
        else:
            skills_block = str(suggested_skills)

        content = (
            f"# Agent: {name}\n\n"
            f"## Department\n{agent_spec.get('department', 'general')}\n\n"
            f"## Soul\n{agent_spec.get('soul', '')}\n\n"
            f"## Domain Rules\n{rules_block}\n\n"
            f"## Suggested Skills\n{skills_block}\n\n"
            f"## Created\nAuto-generated from evolution engine proposal.\n"
        )
        soul_doc.write_text(content, encoding="utf-8")
        print(f"[AuthorityEngine] Soul doc written → {soul_doc}")

    def reject(self, approval_id: str) -> dict:
        from substrate.state.stores.approval_store import ApprovalStore

        ApprovalStore().reject(
            org_id=self.ctx.org_id,
            approval_id=approval_id,
            resolved_by=self.ctx.user_id,
        )
        return {"status": "rejected", "approval_id": approval_id}

    def get_pending(self) -> list:
        with get_conn(self.ctx.org_id) as cur:
            cur.execute(
                """
                SELECT id, request_json, created_at
                FROM approvals
                WHERE org_id = %s AND status = 'pending'
                ORDER BY created_at ASC
            """,
                (self.ctx.org_id,),
            )
            rows = cur.fetchall()
        result = []
        for r in rows:
            rj = r["request_json"] or {}
            if isinstance(rj, str):
                import json as _json

                try:
                    rj = _json.loads(rj)
                except Exception:
                    rj = {}
            result.append(
                {
                    "id": str(r["id"]),
                    "action_type": rj.get("action_type"),
                    "agent": rj.get("agent"),
                    "created_at": r["created_at"].isoformat(),
                }
            )
        return result
