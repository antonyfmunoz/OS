from substrate.state.context.context import EntrepreneurOSContext
from substrate.state.storage.db import get_conn
import json, uuid
from datetime import datetime, timezone

RISK_CLASSES = {
    'CRITICAL': [
        'send_message','send_email',
        'execute_payment','delete_records',
        'bulk_update','mass_outreach','publish_content'
    ],
    'HIGH': [
        'send_dm',
        'create_outreach','post_content',
        'update_external_crm','book_call'
    ],
    'MEDIUM': [
        'draft_message','draft_content',
        'create_task','create_document'
    ],
    'LOW': [
        'analyze','research','score','classify',
        'summarize','read','query','report',
        'draft_brief','generate_brief',
        'research_prospect','extract_profile'
    ]
}

AUTONOMY_LEVEL_MAP = {
    'manual': 1,
    'hybrid': 3,
    'autonomous': 4
}

# Minimum autonomy level required per risk class
MIN_LEVEL_TO_EXECUTE = {
    'LOW': 0,
    'MEDIUM': 1,
    'HIGH': 3,
    'CRITICAL': 999  # never auto-execute
}


class AuthorityEngine:

    def __init__(self, ctx: EntrepreneurOSContext):
        self.ctx = ctx
        self._org_autonomy = self._load_org_autonomy()

    def _load_org_autonomy(self) -> int:
        with get_conn(self.ctx.org_id) as cur:
            cur.execute(
                "SELECT autonomy_stage FROM organizations WHERE id = %s",
                (self.ctx.org_id,)
            )
            row = cur.fetchone()
            stage = row['autonomy_stage'] if row else 'manual'
            return AUTONOMY_LEVEL_MAP.get(stage, 1)

    def classify_action(self, action_type: str) -> str:
        for risk_class, actions in RISK_CLASSES.items():
            if action_type in actions:
                return risk_class
        return 'LOW'  # unknown actions default to LOW

    def get_autonomy_level(self,
        workflow_id: str | None = None) -> int:
        if workflow_id:
            try:
                with get_conn(self.ctx.org_id) as cur:
                    cur.execute(
                        "SELECT autonomy_stage FROM workflows WHERE id = %s AND org_id = %s",
                        (workflow_id, self.ctx.org_id)
                    )
                    row = cur.fetchone()
                    if row:
                        return AUTONOMY_LEVEL_MAP.get(row['autonomy_stage'], 1)
            except Exception:
                pass
        return self._org_autonomy

    def check_can_execute(self,
        action_type: str,
        workflow_id: str | None = None) -> dict:
        risk_class = self.classify_action(action_type)
        autonomy_level = self.get_autonomy_level(workflow_id)
        min_level = MIN_LEVEL_TO_EXECUTE[risk_class]
        requires_approval = risk_class in ('HIGH', 'CRITICAL')
        can_execute = (
            autonomy_level >= min_level
            and risk_class not in ('CRITICAL',)
        )
        return {
            'can_execute': can_execute,
            'requires_approval': requires_approval,
            'reason': f'{risk_class} action requires autonomy level {min_level}+, current level {autonomy_level}',
            'autonomy_level': autonomy_level,
            'risk_class': risk_class
        }

    def queue_for_approval(self,
        action_type: str,
        payload: dict,
        agent: str) -> str:
        from substrate.state.stores.approval_store import ApprovalStore
        return ApprovalStore().create_approval(
            org_id=self.ctx.org_id,
            request={
                'action_type': action_type,
                'payload': payload,
                'agent': agent,
            },
        )

    def execute_or_queue(self,
        action_type: str,
        payload: dict,
        agent: str,
        execute_fn) -> dict:
        check = self.check_can_execute(action_type)
        if check['can_execute'] and not check['requires_approval']:
            result = execute_fn(payload)
            return {'status': 'executed', 'result': result}
        else:
            approval_id = self.queue_for_approval(
                action_type, payload, agent
            )
            return {
                'status': 'pending_approval',
                'approval_id': approval_id,
                'reason': check['reason']
            }

    def approve(self, approval_id: str) -> dict:
        from substrate.state.stores.approval_store import ApprovalStore
        result = ApprovalStore().approve(
            org_id=self.ctx.org_id,
            approval_id=approval_id,
            resolved_by=self.ctx.user_id,
        )
        if not result:
            return {'error': 'approval not found'}

        request = result.get('request_json') or {}
        if isinstance(request, str):
            import json as _json
            try:
                request = _json.loads(request)
            except Exception:
                request = {}
        if request.get('action_type') == 'new_agent_proposal':
            try:
                agent_spec = request.get('proposed_agent', {})
                self._create_agent_soul_doc(agent_spec)
            except Exception as e:
                print(f"[AuthorityEngine] Soul doc write failed: {e}")

        return {'status': 'approved', 'request': result.get('request_json')}

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
        return {'status': 'rejected', 'approval_id': approval_id}

    def get_pending(self) -> list:
        with get_conn(self.ctx.org_id) as cur:
            cur.execute("""
                SELECT id, request_json, created_at
                FROM approvals
                WHERE org_id = %s AND status = 'pending'
                ORDER BY created_at ASC
            """, (self.ctx.org_id,))
            rows = cur.fetchall()
        result = []
        for r in rows:
            rj = r['request_json'] or {}
            if isinstance(rj, str):
                import json as _json
                try:
                    rj = _json.loads(rj)
                except Exception:
                    rj = {}
            result.append({
                'id':          str(r['id']),
                'action_type': rj.get('action_type'),
                'agent':       rj.get('agent'),
                'created_at':  r['created_at'].isoformat(),
            })
        return result
