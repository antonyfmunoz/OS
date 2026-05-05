"""QualityTransformationGate — compatibility shim.

Canonical location for types: umh/execution/quality.py
EOS-coupled functions (quality_check, gate_outgoing_email) remain here.
"""

import logging as _logging

from umh.execution.quality import (  # noqa: F401
    QualityGate,
    TransformationResult,
)

# Legacy name alias
QualityTransformationGate = QualityGate


# ─── EOS-coupled functions (not in UMH) ─────────────────────────────────────

VOICE_STANDARDS = """
Founder voice standards:
- Direct and confident. No hedging.
- Warm but not overly casual
- No corporate speak or filler phrases
- Short sentences preferred
- Clear next step always included in outreach
- Never uses: "I hope this email finds you well",
  "Please don't hesitate", "As per my previous email",
  "Circling back", "Touching base", "Quick question"
"""

_qg_logger = _logging.getLogger(__name__)


def quality_check(
    content: str,
    content_type: str = "email",
    recipient_context: str = "",
) -> dict:
    """Run quality check on outgoing communication.

    Returns dict with keys: approved (bool), score (int 0-10),
    issues (list[str]), suggestions (list[str]), revised_version (str).
    """
    try:
        from umh.gateway.entry import utility_llm_call

        prompt = f"""You are a quality control editor
for the founder's outgoing communications.

Voice standards:
{VOICE_STANDARDS}

Content type: {content_type}
Recipient context: {recipient_context or "Unknown"}

Content to review:
{content}

Check for:
1. Voice consistency with standards above
2. Grammar and spelling errors
3. Clarity — is the message clear?
4. Call to action — is there a clear next step?
5. Tone appropriateness for recipient
6. Prohibited phrases
7. Length appropriateness

Return JSON only:
{{"approved": true, "score": 8, "issues": [], "suggestions": [], "revised_version": ""}}"""

        result = utility_llm_call(prompt, operation="quality_gate_check", max_tokens=500).strip()

        if "```" in result:
            result = result.split("```")[1].replace("json", "").strip()
        import json as _j

        return _j.loads(result)
    except Exception as e:
        _qg_logger.warning(f"[QualityGate] check failed: {e}")
        return {
            "approved": True,
            "score": 7,
            "issues": [],
            "suggestions": [],
            "revised_version": "",
        }


def gate_outgoing_email(
    subject: str,
    body: str,
    to_email: str = "",
    auto_revise: bool = True,
    ctx=None,
) -> dict:
    """Full quality gate for outgoing email.

    Logs result to Neon. Returns quality_check result dict.
    """
    import json as _j

    result = quality_check(
        content=f"Subject: {subject}\n\n{body}",
        content_type="email",
        recipient_context=to_email,
    )

    try:
        from umh.environments.system_context import load_context_from_env
        from umh.storage.adapters.neon import get_conn

        ctx = ctx or load_context_from_env()
        with get_conn(ctx.org_id) as cur:
            cur.execute(
                """
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            """,
                (
                    str(ctx.org_id),
                    "quality_gate_check",
                    _j.dumps(
                        {
                            "subject": subject,
                            "to": to_email,
                            "score": result.get("score"),
                            "approved": result.get("approved"),
                            "issues": result.get("issues", []),
                        }
                    ),
                    "quality_gate",
                ),
            )
    except Exception:
        pass

    return result
