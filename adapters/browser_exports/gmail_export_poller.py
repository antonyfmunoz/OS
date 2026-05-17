"""Gmail export email poller — finds export download links in inbox."""

import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from dotenv import load_dotenv

load_dotenv(_REPO_ROOT / "runtime" / ".env")
load_dotenv(_REPO_ROOT / "services" / ".env", override=True)

logger = logging.getLogger(__name__)

# Known sender addresses for export notification emails
_SERVICE_SENDERS: dict[str, str] = {
    "claude": "noreply@anthropic.com",
    "chatgpt": "noreply@openai.com",
}

# Search query keywords per service
_SERVICE_KEYWORDS: dict[str, str] = {
    "claude": "export OR download",
    "chatgpt": "export OR download",
}


async def poll_for_export_emails(service: str) -> list[dict]:
    """Poll Gmail for data export notification emails from a service.

    Searches for emails from the service's notification address that
    contain export/download keywords. Extracts download URLs from
    email snippets.

    Args:
        service: "claude" or "chatgpt"

    Returns:
        List of dicts with keys: url, service, timestamp, email_id.
        Empty list if no matching emails found.

    Note:
        TODO: gws_connector needs a get_email_body() method for full body
        parsing. Currently only snippet/subject text is available, which may
        not contain the download URL. When get_email_body is added, update
        this function to parse the full HTML body for download links.
    """
    sender = _SERVICE_SENDERS.get(service)
    if not sender:
        logger.warning(f"[gmail_poller] No known sender for service: {service}")
        return []

    keywords = _SERVICE_KEYWORDS.get(service, "export OR download")

    try:
        from adapters.google_workspace.gws_connector import GWSConnector

        gws = GWSConnector()

        # Search for emails matching service + keywords
        query = f"from:{sender} ({keywords})"
        emails = gws.get_recent_emails(max_results=10, query=query)

        if not emails:
            logger.info(f"[gmail_poller] No export emails found for {service}")
            return []

        results: list[dict] = []
        for email in emails:
            email_id = email.get("id", "")
            snippet = email.get("snippet", "")
            subject = email.get("subject", "")
            date = email.get("date", "")
            combined_text = f"{subject} {snippet}"

            # Extract URLs from snippet text
            # TODO: Use get_email_body() for full body URL extraction
            urls = re.findall(r"https?://[^\s<>\"']+", combined_text)

            # Filter for likely download URLs
            download_urls = [
                url
                for url in urls
                if any(kw in url.lower() for kw in ["download", "export", "data", "archive"])
            ]

            if download_urls:
                for url in download_urls:
                    results.append(
                        {
                            "url": url,
                            "service": service,
                            "timestamp": date or datetime.now(timezone.utc).isoformat(),
                            "email_id": email_id,
                        }
                    )
            elif urls:
                # If no download-specific URLs, include first URL as candidate
                results.append(
                    {
                        "url": urls[0],
                        "service": service,
                        "timestamp": date or datetime.now(timezone.utc).isoformat(),
                        "email_id": email_id,
                    }
                )

        logger.info(f"[gmail_poller] Found {len(results)} export email(s) for {service}")
        return results

    except ImportError as e:
        logger.error(f"[gmail_poller] Cannot import GWSConnector: {e}")
        return []
    except Exception as e:
        logger.error(f"[gmail_poller] Failed to poll emails for {service}: {e}")
        return []
