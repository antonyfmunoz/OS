"""EOS Legal Agent — contract review, compliance tracking, entity management.

Permission tier: COMMIT — legal actions require human approval.
"""

from __future__ import annotations

from typing import Any

from substrate import Substrate
from substrate.types import Component, ComponentType, PermissionTier, RegistrationResult

from projections.eos.agents.base import DepartmentAgent, SkillResult


class LegalAgent(DepartmentAgent):
    DEPARTMENT = "legal"
    PERMISSION_TIER = PermissionTier.COMMIT

    def _register_skills(self) -> None:
        self._add_skill(
            "contract_review",
            "analyze",
            "Review a contract for risks and obligations",
            self._contract_review,
        )
        self._add_skill(
            "compliance_check",
            "analyze",
            "Check compliance status against requirements",
            self._compliance_check,
        )
        self._add_skill(
            "entity_status",
            "report",
            "Report on entity registration status",
            self._entity_status,
        )
        self._add_skill(
            "terms_draft",
            "draft_content",
            "Draft terms of service or privacy policy",
            self._terms_draft,
        )
        self._add_skill(
            "ip_audit",
            "analyze",
            "Audit IP assets and protections",
            self._ip_audit,
        )
        self._add_skill(
            "contract_execute",
            "execute_payment",
            "Execute a contract (requires human approval)",
            self._contract_execute,
        )

    def _contract_review(self, **kwargs: Any) -> SkillResult:
        contract_text = kwargs.get("text", "")
        if not contract_text:
            return SkillResult(success=False, error="No contract text provided")

        risks = []
        obligations = []
        text_lower = contract_text.lower()

        risk_signals = {
            "indemnif": "Indemnification clause detected",
            "unlimited liabilit": "Unlimited liability risk",
            "non-compete": "Non-compete restriction",
            "auto-renew": "Auto-renewal clause",
            "exclusive": "Exclusivity requirement",
            "penalty": "Penalty clause",
            "termination for convenience": "Unilateral termination right",
        }
        for signal, desc in risk_signals.items():
            if signal in text_lower:
                risks.append(desc)

        obligation_signals = {
            "shall": "Contractual obligation",
            "must deliver": "Delivery obligation",
            "payment due": "Payment obligation",
            "within": "Time-bound obligation",
            "confidential": "Confidentiality obligation",
        }
        for signal, desc in obligation_signals.items():
            if signal in text_lower:
                obligations.append(desc)

        risk_level = "high" if len(risks) > 3 else "medium" if risks else "low"

        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=(
                    f"Review this contract excerpt for key risks and obligations. "
                    f"Be specific and concise (3-5 bullet points):\n\n{contract_text[:2000]}"
                ),
                system="Legal contract reviewer. Identify risks, obligations, and red flags.",
                task_type="fast_response",
            )
            if result.output:
                return SkillResult(
                    success=True,
                    output={
                        "risk_level": risk_level,
                        "risks": risks,
                        "obligations": obligations,
                        "ai_analysis": result.output.strip()[:1000],
                    },
                )
        except Exception:
            pass

        return SkillResult(
            success=True,
            output={
                "risk_level": risk_level,
                "risks": risks,
                "obligations": obligations,
            },
        )

    def _compliance_check(self, **kwargs: Any) -> SkillResult:
        domain = kwargs.get("domain", "general")

        requirements: dict[str, list[str]] = {
            "general": [
                "Terms of Service published",
                "Privacy Policy published",
                "Data processing records maintained",
            ],
            "payments": [
                "PCI DSS compliance",
                "Refund policy published",
                "Payment processor agreement",
            ],
            "data": [
                "User data deletion process",
                "Data breach notification plan",
                "Encryption at rest and in transit",
            ],
        }

        reqs = requirements.get(domain, requirements["general"])
        return SkillResult(
            success=True,
            output={
                "domain": domain,
                "requirements": reqs,
                "status": "needs_review",
                "note": "Compliance requirements listed — manual verification needed",
            },
        )

    def _entity_status(self, **kwargs: Any) -> SkillResult:
        entities = [
            {
                "name": "Munoz Conglomerate LLC",
                "type": "LLC",
                "state": "Oregon",
                "status": "active",
            },
            {"name": "Lyfe Institute LLC", "type": "LLC", "state": "Oregon", "status": "active"},
            {"name": "Empyrean Studio LLC", "type": "LLC", "state": "Oregon", "status": "active"},
        ]
        return SkillResult(success=True, output={"entities": entities})

    def _terms_draft(self, **kwargs: Any) -> SkillResult:
        doc_type = kwargs.get("type", "tos")
        product = kwargs.get("product", "")

        try:
            from adapters.models.model_router import call_with_fallback

            result = call_with_fallback(
                prompt=(
                    f"Draft a {doc_type} document outline for {product}. "
                    f"Include key sections that are legally required. "
                    f"Return section headers with 1-line description each."
                ),
                system="Legal document drafter. Create clear, comprehensive legal documents.",
                task_type="fast_response",
            )
            if result.output:
                return SkillResult(
                    success=True,
                    output={
                        "type": doc_type,
                        "product": product,
                        "draft": result.output.strip()[:2000],
                        "status": "draft",
                    },
                )
        except Exception:
            pass

        sections = {
            "tos": [
                "Acceptance",
                "User Obligations",
                "Prohibited Use",
                "Limitation of Liability",
                "Termination",
                "Governing Law",
            ],
            "privacy": [
                "Data Collection",
                "Data Use",
                "Data Sharing",
                "Data Retention",
                "User Rights",
                "Contact Information",
            ],
        }
        return SkillResult(
            success=True,
            output={
                "type": doc_type,
                "sections": sections.get(doc_type, sections["tos"]),
                "status": "draft_outline",
            },
        )

    def _ip_audit(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            success=True,
            output={
                "trademarks": [],
                "copyrights": [],
                "trade_secrets": ["UMH substrate architecture", "Agent coordination protocols"],
                "recommendations": [
                    "Register trademark for Initiate Arena",
                    "Register trademark for Lyfe Institute",
                    "Document trade secrets formally",
                ],
            },
        )

    def _contract_execute(self, **kwargs: Any) -> SkillResult:
        return SkillResult(
            success=True,
            output={
                "status": "pending_approval",
                "contract_id": kwargs.get("contract_id", ""),
                "counterparty": kwargs.get("counterparty", ""),
                "note": "Contract execution queued for human approval (COMMIT tier)",
            },
        )


async def register_legal_agent(substrate: Substrate) -> RegistrationResult:
    agent = LegalAgent()
    component = Component(
        component_type=ComponentType.AGENT,
        name="eos-legal",
        capabilities=[
            "contract_review",
            "compliance_tracking",
            "entity_management",
            "terms_drafting",
            "ip_protection",
            "contract_execution",
        ],
        metadata=agent.metadata(),
    )
    return await substrate.register(component)
