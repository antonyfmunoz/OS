"""
Document Filing System — intelligently files documents
arriving via email to the correct Drive folder.
Uses LLM to classify then logs to Neon.
"""

import os
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')

FILING_STRUCTURE = {
    'contract': 'Legal/Contracts',
    'nda': 'Legal/NDAs',
    'invoice': 'Finance/Invoices',
    'receipt': 'Finance/Receipts',
    'proposal': 'Sales/Proposals',
    'agreement': 'Legal/Agreements',
    'report': 'Reports',
    'presentation': 'Presentations',
    'research': 'Research',
    'other': 'Inbox/Unfiled',
}


def classify_document(
    filename: str,
    subject: str = '',
    sender: str = '',
) -> dict:
    """Classify a document and determine where to file it."""
    try:
        from execution.runtime.model_router import get_router, TaskType
        router = get_router()

        import json as _json
        result = router.call_with_fallback(TaskType.FAST_RESPONSE, f"""Classify this document for filing.

Filename: {filename}
Email subject: {subject}
From: {sender}

Document types: {', '.join(FILING_STRUCTURE.keys())}

Return JSON only:
{{"type": "document type from list",
  "venture": "lyfe_institute|empyrean_creative|personal_brand|general",
  "priority": "high|medium|low",
  "requires_review": true,
  "confidence": "high|medium|low"}}""").strip()

        if '```' in result:
            result = result.split('```')[1].replace('json', '').strip()
        classification = _json.loads(result)
        doc_type = classification.get('type', 'other')
        classification['folder'] = FILING_STRUCTURE.get(doc_type, 'Inbox/Unfiled')
        return classification
    except Exception as e:
        logger.warning(f'[DocumentFiler] classify failed: {e}')
        return {
            'type': 'other',
            'folder': 'Inbox/Unfiled',
            'priority': 'low',
            'requires_review': False,
            'confidence': 'low',
        }


def log_document(
    filename: str,
    doc_type: str,
    folder: str,
    venture: str,
    sender: str,
    requires_review: bool,
    ctx=None,
) -> bool:
    """Log a filed document to Neon."""
    try:
        from runtime.context import load_context_from_env
        from state.memory.memory import AgentMemory
        ctx = ctx or load_context_from_env()

        AgentMemory().log_event(
            org_id=str(ctx.org_id),
            event_type='document_filed',
            payload={
                'filename': filename,
                'type': doc_type,
                'folder': folder,
                'venture': venture,
                'sender': sender,
                'requires_review': requires_review,
                'filed_at': datetime.now(PDT).isoformat(),
            },
            handled_by='document_filer',
        )
        return True
    except Exception as e:
        logger.warning(f'[DocumentFiler] log failed: {e}')
        return False


def process_email_attachments(
    subject: str,
    sender: str,
    attachment_names: list,
    ctx=None,
) -> list[dict]:
    """
    Process attachments from an email.
    Classifies each, logs to Neon, returns results.
    """
    results = []
    for filename in attachment_names:
        classification = classify_document(
            filename=filename,
            subject=subject,
            sender=sender,
        )
        log_document(
            filename=filename,
            doc_type=classification.get('type', 'other'),
            folder=classification.get('folder', 'Inbox/Unfiled'),
            venture=classification.get('venture', 'general'),
            sender=sender,
            requires_review=classification.get('requires_review', False),
            ctx=ctx,
        )
        results.append({'filename': filename, **classification})
    return results
