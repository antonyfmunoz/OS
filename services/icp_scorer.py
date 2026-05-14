import os
import sys
import json
import time
import shutil
import datetime
import glob
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Add repo root to path so runtime is importable regardless of working directory
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from execution.runtime.agent_runtime import AgentRuntime
from state.memory.memory import AgentMemory

_mem = AgentMemory()

MAX_LEADS_PER_RUN = 200
MAX_RETRIES = 3
BASE_BACKOFF = 2

RAW_SIGNALS_DIR = "01_Inbox/raw_signals"
PROCESSED_SIGNALS_DIR = "01_Inbox/processed_signals"
LEADS_DIR = "03_CRM/Leads"
OUTREACH_DIR = "03_CRM/Outreach_Messages"
LEAD_INDEX = "03_CRM/Leads/_lead_index.md"

class RateLimiter:
    def __init__(self, calls_per_minute):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0

    def wait(self):
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)
        self.last_call_time = time.time()


# Claude Haiku rate limit is 1000 RPM but stay conservative to avoid costs spiraling
claude_limiter = RateLimiter(calls_per_minute=40)



def parse_frontmatter(content):
    """Parse YAML frontmatter from markdown content. Returns (metadata dict, body)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    fm_text = content[3:end].strip()
    body = content[end + 3:].strip()
    metadata = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            metadata[key.strip()] = value.strip()
    return metadata, body


def extract_comment_text(body):
    """Extract comment text from signal file body."""
    for line in body.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("**"):
            return line
    # Fallback: find the line after "**Comment:**"
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if "**Comment:**" in line and i + 1 < len(lines):
            return lines[i + 1].strip()
    return body.strip()


def get_processed_filenames():
    """Return set of filenames already in processed_signals/."""
    if not os.path.exists(PROCESSED_SIGNALS_DIR):
        return set()
    return {os.path.basename(f) for f in glob.glob(f"{PROCESSED_SIGNALS_DIR}/*.md")}


def lead_exists(username):
    """Return True if a lead file for this username already exists."""
    lead_files = glob.glob(os.path.join(LEADS_DIR, f"lead_{username}_*.md"))
    return len(lead_files) > 0


def already_contacted(username):
    """Check if we already sent a DM to this person."""
    leads_dir = os.path.join(
        os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))),
        "03_CRM/Leads"
    )
    for filepath in glob.glob(
            os.path.join(leads_dir, "lead_*.md")):
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        meta, _ = parse_frontmatter(content)
        file_username = meta.get("name", "")
        file_status = meta.get("status", "new")
        if file_username.lower() == username.lower():
            if file_status != "new":
                return True
            created = meta.get("next_action_date", "")
            today = datetime.date.today().isoformat()
            if created and created != today:
                return True
    return False


def in_pipeline(username):
    """Return True if username appears anywhere in Pipeline.md."""
    pipeline_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "03_CRM/Pipeline.md"
    )
    if not os.path.exists(pipeline_file):
        return False
    with open(pipeline_file, encoding="utf-8") as f:
        content = f.read()
    return username.lower() in content.lower()


def load_outreach_messages():
    """Load the latest outreach_messages file. Returns raw text."""
    files = sorted(glob.glob(f"{OUTREACH_DIR}/outreach_messages_*.md"), reverse=True)
    if not files:
        return ""
    with open(files[0], encoding="utf-8") as f:
        return f.read()


PAIN_SIGNAL_KEYWORDS = {
    "wast":       ["wasting", "disappears", "wasted"],
    "stuck":      ["stuck", "capable", "potential"],
    "finish":     ["finish", "start", "complete"],
    "lazy":       ["discipline", "structure", "lazy"],
    "consistent": ["consistent", "routine", "system"],
    "lost":       ["direction", "lost", "drift"],
    "potential":  ["potential", "capable", "more"],
}

FALLBACK_OPENER = "Saw your comment — want to connect?"


def _extract_openers(outreach_text, archetype):
    """Return list of opener strings from the matching archetype segment."""
    archetype_lower = archetype.lower()
    if "frustrated drifter" in archetype_lower:
        segment_marker = "## Segment 2 — Frustrated Drifter"
    else:
        segment_marker = "## Segment 1 — Ambitious but Stuck"

    idx = outreach_text.find(segment_marker)
    if idx == -1:
        idx = outreach_text.find("## Segment 1")
    if idx == -1:
        return []

    # Isolate this segment (stop at the next ## heading)
    segment = outreach_text[idx:]
    next_section = segment.find("\n## ", 1)
    if next_section != -1:
        segment = segment[:next_section]

    openers_idx = segment.find("### Openers")
    if openers_idx == -1:
        return []

    openers_block = segment[openers_idx:]
    openers = []
    for line in openers_block.splitlines():
        stripped = line.strip()
        # Match numbered list items: "1. ...", "2. ...", etc.
        if stripped and stripped[0].isdigit() and ". " in stripped:
            _, _, text = stripped.partition(". ")
            openers.append(text.strip().strip('"'))
    return openers


def pick_opener(outreach_text, archetype, pain_signals, comment_text):
    """Score all openers in the matching segment and return (opener_text, opener_index)."""
    openers = _extract_openers(outreach_text, archetype)
    if not openers:
        return FALLBACK_OPENER, 0

    comment_lower = comment_text.lower()
    comment_words = set(comment_lower.split())

    # Build set of active pain signal keyword lists
    active_keywords = []
    for signal in pain_signals:
        signal_lower = signal.lower()
        for trigger, keywords in PAIN_SIGNAL_KEYWORDS.items():
            if trigger in signal_lower:
                active_keywords.extend(keywords)

    scored = []
    for idx, opener in enumerate(openers):
        opener_lower = opener.lower()
        score = 0

        # +3 if opener shares a word with the comment (min 4 chars to avoid noise)
        opener_words = set(w for w in opener_lower.split() if len(w) >= 4)
        if opener_words & comment_words:
            score += 3

        # +2 for each matched pain signal keyword found in opener
        for kw in active_keywords:
            if kw in opener_lower:
                score += 2
                break  # one pain bonus per opener

        # +1 if opener is short (under 100 chars)
        if len(opener) < 100:
            score += 1

        # +1 if opener ends with a question mark
        if opener.rstrip().endswith("?"):
            score += 1

        scored.append((score, len(opener), idx + 1, opener))

    # Sort by score desc, then length asc (shorter wins ties)
    scored.sort(key=lambda x: (-x[0], x[1]))
    best = scored[0]
    return best[3], best[2]


_ICP_SCORE_PROMPT = """\
Score this Instagram comment against the Initiate Arena ICP. \
Respond ONLY with valid JSON, no other text.

SCORING RUBRIC:
8-10 (HIGH): Specific pain expressed, urgency present, self-ownership language, \
"This is me" / "I needed this" / "I keep starting and never finishing" energy. Vulnerable and honest.
5-7  (MEDIUM): Mild interest, no urgency, vague positivity without personal pain.
1-4  (LOW): Emoji-only, generic praise, ego-defender language ("I'm already doing this"), spam.

ARCHETYPES:
- Frustrated Drifter: "wasting my life", "start everything, finish nothing"
- Ambitious but Stuck: "capable of more but weeks just disappear", "scrolling instead of building"
- Ego Defender: "I'm already doing this" — disqualify immediately

OUTPUT FORMAT (JSON only):
{
  "score": <number 1-10>,
  "archetype": "<Frustrated Drifter|Ambitious but Stuck|Ego Defender|Other>",
  "pain_signals": ["<signal1>", "<signal2>"],
  "disqualify": <true|false>,
  "reason": "<one sentence explanation>"
}

Comment to score: %s"""


def score_comment(runtime, comment_text, api_call_counter):
    """
    Score a comment using the sales.icp_qualifier sub-agent.
    Returns (result dict or None, input_tokens, output_tokens).
    """
    claude_limiter.wait()
    try:
        prompt = _ICP_SCORE_PROMPT % comment_text
        result = runtime.run_team_task(
            team="sales",
            sub_agent="icp_qualifier",
            prompt=prompt,
            venture_id="lyfe_institute",
        )
        api_call_counter[0] += 1
        raw = result.output.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        return (
            json.loads(raw),
            result.tokens_used["input"],
            result.tokens_used["output"],
        )
    except Exception as e:
        print(f"  [score_comment] Error: {e}")
        return None, 0, 0


def update_opener_stats_sent(opener_text):
    """Increment sent count for an opener in opener_stats.json."""
    opener_stats_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "opener_stats.json")
    try:
        if os.path.exists(opener_stats_path):
            with open(opener_stats_path, encoding="utf-8") as f:
                stats = json.load(f)
        else:
            stats = {"openers": {}}
        key = opener_text[:50]
        openers = stats.setdefault("openers", {})
        openers.setdefault(key, {"sent": 0, "replies": 0, "reply_rate": 0.0})
        openers[key]["sent"] += 1
        with open(opener_stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        print(f"  [OPENER STATS] Failed to update: {e}")


def push_lead_to_notion(username: str, score: int, archetype: str, pain_signals: list, channel: str = "Instagram DM") -> bool:
    """Push a scored lead into the Notion Pipeline database."""
    import requests
    from datetime import date

    api_key = os.getenv("NOTION_API_KEY")
    database_id = os.getenv("NOTION_LYFE_PIPELINE_ID")

    if not api_key or not database_id:
        return False

    notes = f"Score: {score}/100 | Archetype: {archetype}"
    if pain_signals:
        notes += f" | Pain: {', '.join(pain_signals[:3])}"

    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {
                "title": [{"text": {"content": f"@{username}"}}]
            },
            "Stage": {
                "select": {"name": "New Lead"}
            },
            "Channel": {
                "select": {"name": channel}
            },
            "Value": {
                "number": 750
            },
            "Last Contact": {
                "date": {"start": date.today().isoformat()}
            },
            "Notes": {
                "rich_text": [{"text": {"content": notes}}]
            },
            "Archetype": {
                "rich_text": [{"text": {"content": archetype}}]
            },
            "Score": {
                "number": score
            },
            "AI Qualified": {
                "checkbox": True
            },
        }
    }

    try:
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10,
        )
        return response.status_code == 200
    except Exception as e:
        print(f"[Notion] Push failed for @{username}: {e}")
        return False


def create_lead_file(username, comment_text, source, post_url, timestamp, result, opener, opener_index=0):
    """Write lead markdown file and return filepath."""
    os.makedirs(LEADS_DIR, exist_ok=True)
    today = datetime.date.today().isoformat()
    safe_username = username.replace("/", "_").replace("\\", "_")
    filename = f"{LEADS_DIR}/lead_{safe_username}_{today}.md"

    pain_signals_yaml = "\n".join(f"  - {s}" for s in result["pain_signals"])
    pain_signals_inline = ", ".join(result["pain_signals"])

    content = f"""---
type: lead
name: {username}
platform: instagram
status: new
offer: Initiate Arena
source: {source}
icp_score: {result['score']}
archetype: {result['archetype']}
pain_signals:
{pain_signals_yaml}
post_url: {post_url}
comment: "{comment_text}"
opener_sent: "{opener[:50]}"
opener_index: {opener_index}
last_contact:
next_action: send_opener
next_action_date: {today}
tags:
  - crm
  - lead
  - initiate-arena
kanban_stage: New
---

# Lead: @{username}

## Their Comment
"{comment_text}"

## ICP Analysis
- Score: {result['score']}/10
- Archetype: {result['archetype']}
- Pain Signals: {pain_signals_inline}
- Reason: {result['reason']}

## Opening DM
{opener}

## Activity Log
| Date | Action | Notes |
|---|---|---|
| {today} | Lead created | Score: {result['score']}/10 — Auto-qualified by ICP scorer |
"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    update_opener_stats_sent(opener[:50])

    # Log to memory.db so reply outcomes can be linked back to this lead
    try:
        _mem.log_lead_scored(
            username=username,
            venture_id="lyfe_institute",
            comment_text=comment_text,
            score=result["score"],
            archetype=result["archetype"],
            model_used="claude-haiku-4-5-20251001",
        )
    except Exception as e:
        print(f"  [MEMORY] log_lead_scored failed for @{username}: {e}")

    # Push to Notion Pipeline
    push_lead_to_notion(
        username=username,
        score=result.get("score", 0),
        archetype=result.get("archetype", "Unknown"),
        pain_signals=result.get("pain_signals", []),
    )

    # Publish new_lead event — triggers icp_qualifier handler async (non-blocking)
    try:
        from runtime.event_bus import EventBus
        EventBus().publish_async("new_lead", {
            "username":   username,
            "score":      result["score"],
            "state":      result["archetype"],
            "venture_id": "lyfe_institute",
        })
    except Exception as e:
        print(f"  [EVENT BUS] new_lead publish failed for @{username}: {e}")

    return filename


PIPELINE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "03_CRM/Pipeline.md")


def add_to_kanban(username, score, archetype, comment_text, lead_filename):
    """Insert a card into the ## New column of Pipeline.md."""
    if not os.path.exists(PIPELINE_FILE):
        print(f"  [KANBAN] Warning: Pipeline.md not found at {PIPELINE_FILE}")
        return

    with open(PIPELINE_FILE, encoding="utf-8") as f:
        content = f.read()

    preview = comment_text[:50]
    card = f"- [ ] [[{lead_filename}|@{username}]] — {score}/10 — {archetype} — {preview}...\n"

    marker = "## New\n\n**Complete**\nfalse\n"
    if marker in content:
        content = content.replace(marker, marker + card, 1)
        with open(PIPELINE_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  [KANBAN] @{username} added to Pipeline board")
    else:
        print(f"  [KANBAN] Warning: Could not find ## New section in Pipeline.md")


def main():
    runtime = AgentRuntime()

    os.makedirs(PROCESSED_SIGNALS_DIR, exist_ok=True)
    os.makedirs(LEADS_DIR, exist_ok=True)

    processed = get_processed_filenames()
    signal_files = sorted(glob.glob(f"{RAW_SIGNALS_DIR}/*.md"))
    unprocessed = [f for f in signal_files if os.path.basename(f) not in processed]

    if not unprocessed:
        print("No new signal files to process.")
        return

    outreach_text = load_outreach_messages()

    qualified = 0
    disqualified = 0
    duplicate_count = 0
    total = 0
    api_call_counter = [0]  # mutable so score_comment can increment it
    total_input_tokens = 0
    total_output_tokens = 0

    for filepath in unprocessed:
        if qualified >= MAX_LEADS_PER_RUN:
            print(f"Daily lead limit reached ({MAX_LEADS_PER_RUN}). Stopping to control costs.")
            break

        with open(filepath, encoding="utf-8") as f:
            raw = f.read()

        meta, body = parse_frontmatter(raw)
        username = meta.get("username", "unknown")
        source = meta.get("source", "unknown")
        post_url = meta.get("post_url", "")
        timestamp = meta.get("timestamp", "")
        comment_text = extract_comment_text(body)

        if not comment_text:
            print(f"@{username} — skipped (no comment text found)")
            shutil.move(filepath, os.path.join(PROCESSED_SIGNALS_DIR, os.path.basename(filepath)))
            total += 1
            continue

        result, input_toks, output_toks = score_comment(runtime, comment_text, api_call_counter)
        total_input_tokens += input_toks
        total_output_tokens += output_toks
        if result is None:
            print(f"@{username} — ERROR scoring: all retries failed, skipping")
            continue

        score = result.get("score", 0)
        archetype = result.get("archetype", "Other")
        reason = result.get("reason", "")
        disqualify = result.get("disqualify", True)

        if score >= 7 and not disqualify:
            if lead_exists(username) or in_pipeline(username) \
                    or already_contacted(username):
                print(f"@{username} — DUPLICATE — "
                      f"already in system, skipping")
                shutil.move(filepath, os.path.join(
                    PROCESSED_SIGNALS_DIR,
                    os.path.basename(filepath)))
                duplicate_count += 1
                total += 1
                continue

            opener, opener_index = pick_opener(outreach_text, archetype, result["pain_signals"], comment_text)
            lead_filepath = create_lead_file(username, comment_text, source, post_url, timestamp, result, opener, opener_index)
            add_to_kanban(username, score, archetype, comment_text, os.path.basename(lead_filepath).replace(".md", ""))
            qualified += 1
            print(f"@{username} — score: {score}/10 — {archetype} — QUALIFIED")
        else:
            disqualified += 1
            print(f"@{username} — score: {score}/10 — {reason} — DISQUALIFIED")

        shutil.move(filepath, os.path.join(PROCESSED_SIGNALS_DIR, os.path.basename(filepath)))
        total += 1

    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    import cost_tracker

    scorer_cost = cost_tracker.log_scraper_costs(
        apify_results=0,
        haiku_calls=api_call_counter[0],
        haiku_input_tokens=total_input_tokens,
        haiku_output_tokens=total_output_tokens,
    )
    print()
    print("ICP scoring complete.")
    print(f"Qualified: {qualified} leads added to {LEADS_DIR}/")
    print(f"Disqualified: {disqualified} comments filtered out")
    print(f"Duplicates skipped: {duplicate_count}")
    print(f"Total processed: {total}")
    print(f"Total API calls: {api_call_counter[0]}")
    print(f"Scorer cost logged: ${scorer_cost:.4f}")


if __name__ == "__main__":
    main()
