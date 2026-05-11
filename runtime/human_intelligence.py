"""
HumanIntelligenceEngine — behavioral profiling for every person the system
interacts with.

Reads lead files from 03_CRM/Leads/, synthesizes communication style,
dominant pain, objection risk, and next best action into a stored profile.
Every outreach message can then be adapted to that specific human.

Extended to cover the full ecosystem: leads, team members, collaborators,
partners, investors, and prospects. Each human_type gets its own profiling
logic and communication adaptation.

Profiles stored in memory.db table: human_profiles
Profiles older than 48 hours are refreshed on the next cycle.

human_type values:
  'lead' | 'team_member' | 'collaborator' | 'partner' | 'investor' | 'prospect'
"""

import glob
import json
import os
import re
import sys
import datetime
from pathlib import Path
from typing import Literal

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from eos_ai.agent_runtime import AgentRuntime, TaskType
from eos_ai.context import EOSContext, load_context_from_env
from eos_ai.db import get_conn, resolve_venture, ORG_ID, USER_ID

LEADS_DIR      = Path(_REPO_ROOT) / "03_CRM" / "Leads"
PROFILE_TTL_H  = 48  # hours before a profile is considered stale


def _utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ─── Engine ───────────────────────────────────────────────────────────────────

class HumanIntelligenceEngine:

    def __init__(self, ctx: EOSContext | None = None) -> None:
        self._ctx = ctx or load_context_from_env()
        self._runtime = AgentRuntime(self._ctx)

    # ─── Internal: file discovery ────────────────────────────────────────────

    def _find_lead_file(self, username: str) -> str | None:
        """
        Find the most recent lead file for a username.
        First tries an exact filename prefix match, then falls back to scanning
        all lead files and matching the frontmatter `name` field — handles
        usernames with trailing underscores that overlap with the date separator.
        """
        # Try direct glob first (fast path)
        for pattern in [
            str(LEADS_DIR / f"lead_{username}_*.md"),
            str(LEADS_DIR / f"lead_{username}*.md"),
        ]:
            matches = sorted(m for m in glob.glob(pattern) if "_lead_index" not in m)
            if matches:
                return matches[-1]

        # Fallback: scan all files and match frontmatter name field
        for filepath in self._all_lead_files():
            try:
                lead = self._parse_lead_file(filepath)
                if lead["username"] == username:
                    return filepath
            except Exception:
                continue
        return None

    def _all_lead_files(self) -> list[str]:
        """Return all lead files, excluding the index."""
        files = sorted(glob.glob(str(LEADS_DIR / "lead_*.md")))
        return [f for f in files if "_lead_index" not in f]

    # ─── Internal: lead file parser ───────────────────────────────────────────

    def _parse_lead_file(self, filepath: str) -> dict:
        """
        Parse frontmatter + body of a lead .md file.
        Returns a flat dict with all fields needed for profiling.
        """
        with open(filepath, encoding="utf-8") as f:
            raw = f.read()

        # ── Frontmatter ──────────────────────────────────────────────────────
        fm: dict = {}
        if raw.startswith("---"):
            end = raw.find("---", 3)
            if end != -1:
                for line in raw[3:end].strip().splitlines():
                    if ":" in line:
                        k, _, v = line.partition(":")
                        fm[k.strip()] = v.strip().strip('"')

        # ── Pain signals list (YAML inline list) ─────────────────────────────
        pain_signals: list[str] = []
        in_pain = False
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("pain_signals:"):
                in_pain = True
                continue
            if in_pain:
                if stripped.startswith("- "):
                    pain_signals.append(stripped[2:])
                elif stripped and not stripped.startswith("-"):
                    in_pain = False

        # ── Body sections ────────────────────────────────────────────────────
        def _extract_section(text: str, heading: str) -> str:
            pattern = re.compile(
                rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##|\Z)",
                re.DOTALL,
            )
            m = pattern.search(text)
            return m.group(1).strip() if m else ""

        comment_section    = _extract_section(raw, "Their Comment")
        icp_section        = _extract_section(raw, "ICP Analysis")
        opener_section     = _extract_section(raw, "Opening DM")
        activity_section   = _extract_section(raw, "Activity Log")
        conversation_section = _extract_section(raw, "Conversation")

        return {
            "username":       fm.get("name", Path(filepath).stem),
            "venture_id":     "lyfe_institute",   # all current leads are for LI
            "platform":       fm.get("platform", "instagram"),
            "status":         fm.get("status", "new"),
            "kanban_stage":   fm.get("kanban_stage", "New"),
            "icp_score":      fm.get("icp_score", ""),
            "archetype":      fm.get("archetype", ""),
            "pain_signals":   pain_signals,
            "comment":        fm.get("comment", ""),
            "opener_sent":    fm.get("opener_sent", ""),
            "last_contact":   fm.get("last_contact", ""),
            "next_action":    fm.get("next_action", ""),
            "source":         fm.get("source", ""),
            "comment_text":   comment_section,
            "icp_analysis":   icp_section,
            "opening_dm":     opener_section,
            "activity_log":   activity_section,
            "conversation":   conversation_section,
            "raw_file":       filepath,
        }

    # ─── Internal: profile DB ops ─────────────────────────────────────────────

    def _store_profile(self, username: str, venture_id_slug: str, profile: dict) -> None:
        """Upsert profile into Neon human_profiles. venture_id_slug is a string like 'lyfe_institute'."""
        venture_uuid = resolve_venture(venture_id_slug)
        if not venture_uuid:
            print(f"  [HumanIntel] Warning: venture slug '{venture_id_slug}' not found — skipping Neon write.")
            return
        with get_conn(self._ctx.org_id) as cur:
            cur.execute(
                """
                INSERT INTO human_profiles (org_id, username, venture_id, profile_json, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (org_id, username)
                DO UPDATE SET venture_id   = EXCLUDED.venture_id,
                              profile_json = EXCLUDED.profile_json,
                              updated_at   = EXCLUDED.updated_at
                """,
                (self._ctx.org_id, username, venture_uuid, json.dumps(profile), _utcnow()),
            )

    def _fetch_profile_row(self, username: str, venture_id: str = "lyfe_institute") -> dict | None:
        with get_conn(self._ctx.org_id) as cur:
            cur.execute(
                """
                SELECT profile_json, updated_at
                FROM human_profiles
                WHERE org_id = %s AND username = %s
                ORDER BY updated_at DESC LIMIT 1
                """,
                (self._ctx.org_id, username),
            )
            row = cur.fetchone()
        if not row:
            return None
        return {
            "profile_json": json.dumps(row["profile_json"]) if isinstance(row["profile_json"], dict) else row["profile_json"],
            "updated_at":   row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else str(row["updated_at"]),
        }

    def _is_stale(self, updated_at: str) -> bool:
        try:
            ts = datetime.datetime.fromisoformat(updated_at)
            age = datetime.datetime.now(datetime.timezone.utc) - ts
            return age.total_seconds() > PROFILE_TTL_H * 3600
        except Exception:
            return True

    # ─── Internal: AI synthesis ───────────────────────────────────────────────

    def _build_profile_prompt(self, lead: dict) -> str:
        pain_block  = "\n".join(f"  - {p}" for p in lead["pain_signals"]) or "  (none logged)"
        convo_block = lead["conversation"] or "(no conversation recorded yet)"

        return (
            f"You are profiling a sales lead for Initiate Arena — a 90-day discipline and "
            f"execution program for ambitious men 18–25.\n\n"
            f"LEAD DATA:\n"
            f"  Username     : @{lead['username']}\n"
            f"  Platform     : {lead['platform']}\n"
            f"  Pipeline stage: {lead['kanban_stage']}\n"
            f"  ICP score    : {lead['icp_score']}/10\n"
            f"  Archetype    : {lead['archetype']}\n"
            f"  Source       : {lead['source']}\n"
            f"  Last contact : {lead['last_contact'] or 'never'}\n"
            f"  Next action  : {lead['next_action']}\n\n"
            f"THEIR EXACT WORDS (original comment):\n"
            f"  \"{lead['comment']}\"\n\n"
            f"PAIN SIGNALS DETECTED:\n{pain_block}\n\n"
            f"ICP ANALYSIS:\n{lead['icp_analysis']}\n\n"
            f"OPENER SENT:\n  {lead['opening_dm'] or '(not yet sent)'}\n\n"
            f"CONVERSATION HISTORY:\n{convo_block}\n\n"
            f"TASK:\n"
            f"Synthesize this data into a behavioral profile. "
            f"Return ONLY valid JSON — no commentary, no markdown fences — "
            f"with exactly these keys:\n\n"
            f"{{\n"
            f'  "dominant_pain": "their single most pressing stated problem in their own language",\n'
            f'  "communication_style": "formal|casual|brief|expressive — pick one with a one-sentence description",\n'
            f'  "objection_risk": ["most likely objection 1", "most likely objection 2", "most likely objection 3"],\n'
            f'  "recommended_tone": "how to speak to this specific person — 2-3 sentences",\n'
            f'  "next_best_action": "the single most effective thing to say or do right now — concrete and specific"\n'
            f"}}"
        )

    # ─── Public: build_profile ───────────────────────────────────────────────

    def build_profile(self, username: str) -> dict:
        """
        Read the lead file, synthesize via AI, store in memory.db, return profile.
        Returns the profile dict, or raises FileNotFoundError if no lead file found.
        """
        filepath = self._find_lead_file(username)
        if not filepath:
            raise FileNotFoundError(
                f"No lead file found for @{username} in {LEADS_DIR}"
            )

        lead   = self._parse_lead_file(filepath)

        # Enrich with any Gmail threads from this lead
        email_context = ""
        try:
            from eos_ai.gws_connector import GWSConnector
            gws    = GWSConnector()
            emails = gws.search_emails_from(username)
            if emails:
                email_context = "\nEMAIL HISTORY:\n" + "\n".join(
                    f"  [{e['date'][:16]}] {e['from'][:40]}: {e['subject']}"
                    for e in emails
                )
        except Exception as e:
            print(f"  [HumanIntel] Gmail check failed for @{username}: {e}")

        prompt = self._build_profile_prompt(lead)
        if email_context:
            prompt += email_context

        result = self._runtime.run(
            task_type=TaskType.ANALYZE,
            prompt=prompt,
            venture_id=lead["venture_id"],
            max_tokens=600,
            agent="human_intelligence",
        )

        # Parse JSON from model output
        raw_output = result.output.strip()
        # Strip markdown fences if model returns them despite instruction
        if raw_output.startswith("```"):
            raw_output = re.sub(r"^```[a-z]*\n?", "", raw_output)
            raw_output = raw_output.rstrip("`").strip()

        try:
            profile_core = json.loads(raw_output)
        except json.JSONDecodeError:
            # Fallback: extract JSON block with regex
            m = re.search(r"\{.*\}", raw_output, re.DOTALL)
            if m:
                profile_core = json.loads(m.group(0))
            else:
                raise ValueError(
                    f"Could not parse profile JSON for @{username}. "
                    f"Raw output: {raw_output[:200]}"
                )

        profile = {
            **profile_core,
            "username":     username,
            "venture_id":   lead["venture_id"],
            "icp_score":    lead["icp_score"],
            "archetype":    lead["archetype"],
            "kanban_stage": lead["kanban_stage"],
            "last_contact": lead["last_contact"],
            "source":       lead["source"],
        }

        self._store_profile(username, lead["venture_id"], profile)
        print(f"  [HumanIntel] @{username} — profile built and stored.")
        return profile

    # ─── Public: get_profile ────────────────────────────────────────────────

    def get_profile(self, username: str, venture_id: str = "lyfe_institute") -> dict | None:
        """Return stored profile dict, or None if not yet built."""
        row = self._fetch_profile_row(username, venture_id)
        if not row:
            return None
        try:
            return json.loads(row["profile_json"])
        except (json.JSONDecodeError, KeyError):
            return None

    # ─── Public: get_adapted_message ────────────────────────────────────────

    def get_adapted_message(self, username: str, base_message: str) -> str:
        """
        Adapt a base outreach message to this specific person's communication
        style and dominant pain. Falls back to base_message if no profile exists.
        """
        profile = self.get_profile(username)
        if not profile:
            print(f"  [HumanIntel] @{username} — no profile found, returning base message.")
            return base_message

        prompt = (
            f"You are adapting an outreach message for a specific person.\n\n"
            f"THEIR PROFILE:\n"
            f"  Dominant pain       : {profile.get('dominant_pain', 'unknown')}\n"
            f"  Communication style : {profile.get('communication_style', 'unknown')}\n"
            f"  Recommended tone    : {profile.get('recommended_tone', 'unknown')}\n"
            f"  Objection risks     : {', '.join(profile.get('objection_risk', []))}\n\n"
            f"BASE MESSAGE:\n{base_message}\n\n"
            f"TASK:\n"
            f"Rewrite the base message adapted to this person's communication style and dominant pain. "
            f"Keep the same intent and offer. Match their energy — if they're brief, be brief. "
            f"If they're expressive, match that. Pre-empt their most likely objection if it fits naturally. "
            f"Return ONLY the adapted message — no commentary, no labels, no preamble."
        )

        result = self._runtime.run(
            task_type=TaskType.GENERATE,
            prompt=prompt,
            venture_id=profile.get("venture_id", "lyfe_institute"),
            max_tokens=300,
            agent="human_intelligence",
        )
        return result.output.strip()

    # ─── Public: run_profile_cycle ──────────────────────────────────────────

    def run_profile_cycle(self) -> dict:
        """
        Loop all lead files. Build or refresh profiles older than 48 hours.
        Returns {"built": N, "skipped": M, "errors": K}.
        """
        files  = self._all_lead_files()
        built  = 0
        skipped = 0
        errors  = 0

        print(f"[HumanIntel] Profile cycle — {len(files)} lead files found.")

        for filepath in files:
            # Parse the lead file to get the canonical username from frontmatter
            # rather than deriving it from the filename (handles trailing underscores)
            try:
                lead     = self._parse_lead_file(filepath)
                username = lead["username"]
            except Exception as e:
                print(f"  [HumanIntel] {Path(filepath).name} — parse error: {e}")
                errors += 1
                continue

            try:
                row = self._fetch_profile_row(username)
                if row and not self._is_stale(row["updated_at"]):
                    print(f"  [HumanIntel] @{username} — profile fresh, skipping.")
                    skipped += 1
                    continue

                self.build_profile(username)
                built += 1

            except FileNotFoundError as e:
                print(f"  [HumanIntel] @{username} — {e}")
                errors += 1
            except Exception as e:
                print(f"  [HumanIntel] @{username} — error: {e}")
                errors += 1

        print(f"[HumanIntel] Cycle complete — built: {built}, skipped: {skipped}, errors: {errors}")
        return {"built": built, "skipped": skipped, "errors": errors}


    # ─── Public: profile_all_crm_leads ──────────────────────────────────────

    def profile_all_crm_leads(self) -> dict:
        """
        Alias for run_profile_cycle. Profiles all leads in 03_CRM/Leads/,
        writes to Neon human_profiles.
        Returns {"leads_processed": N, "profiles_written": N, "errors": K}.
        """
        result = self.run_profile_cycle()
        return {
            "leads_processed":  result["built"] + result["skipped"] + result["errors"],
            "profiles_written": result["built"],
            "skipped":          result["skipped"],
            "errors":           result["errors"],
        }

    # ─── Public: profile_team_member ────────────────────────────────────────

    def profile_team_member(self, user_id: str, org_id: str) -> dict:
        """
        Profile a team member from their org_members entry and interaction
        history with the system (tasks completed, notes, communication pattern).

        Returns:
            user_id:                  str
            work_style:               str — how they operate
            strengths:                list[str] — what they do well
            communication_preference: str — how to assign work effectively
            reliability_score:        int (0-10) — completed vs assigned tasks
            human_type:               'team_member'
        """
        # ── Load org_members data ─────────────────────────────────────────────
        member_data: dict = {}
        try:
            with get_conn(org_id) as cur:
                cur.execute(
                    """
                    SELECT id, role, created_at
                    FROM org_members
                    WHERE user_id = %s AND org_id = %s
                    LIMIT 1
                    """,
                    (user_id, org_id),
                )
                row = cur.fetchone()
                if row:
                    member_data = {
                        "id":         str(row["id"]),
                        "role":       row["role"] or "unknown",
                        "member_since": str(row["created_at"])[:10] if row["created_at"] else "unknown",
                    }
        except Exception as e:
            print(f"[HumanIntel] org_members query failed: {e}")
            member_data = {"role": "unknown", "member_since": "unknown"}

        # ── Load their interaction footprint in the system ────────────────────
        interactions: list[dict] = []
        try:
            with get_conn(org_id) as cur:
                cur.execute(
                    """
                    SELECT task_type, agent_label, input_summary, created_at
                    FROM interactions
                    WHERE user_id = %s AND org_id = %s
                    ORDER BY created_at DESC
                    LIMIT 50
                    """,
                    (user_id, org_id),
                )
                rows = cur.fetchall()
                interactions = [
                    {
                        "task_type": row["task_type"] or "unknown",
                        "agent":     row["agent_label"] or "unknown",
                        "input":     (row["input_summary"] or "")[:150],
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"[HumanIntel] Team member interaction query failed: {e}")

        # ── Reliability: tasks completed vs assigned (approvals as proxy) ─────
        reliability_score = 5  # default midpoint
        try:
            with get_conn(org_id) as cur:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM approvals WHERE org_id = %s AND status = 'approved'",
                    (org_id,),
                )
                row = cur.fetchone()
                completed = int((row["cnt"] if row else 0) or 0)
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM approvals WHERE org_id = %s",
                    (org_id,),
                )
                row = cur.fetchone()
                total = int((row["cnt"] if row else 0) or 0)
                if total > 0:
                    reliability_score = min(10, round(completed / total * 10))
        except Exception:
            pass

        # ── AI synthesis ──────────────────────────────────────────────────────
        interaction_summary = "\n".join(
            f"  [{i['task_type']}] {i['input']}" for i in interactions[:15]
        ) or "(no interaction history)"

        prompt = (
            "You are profiling a team member in a founder-operator's AI system.\n\n"
            f"MEMBER DATA:\n"
            f"  User ID: {user_id}\n"
            f"  Role: {member_data.get('role', 'unknown')}\n"
            f"  Member since: {member_data.get('member_since', 'unknown')}\n"
            f"  Reliability score: {reliability_score}/10\n\n"
            f"INTERACTION HISTORY (tasks they run):\n{interaction_summary}\n\n"
            "Synthesize a behavioral profile. Return ONLY valid JSON:\n"
            "{\n"
            '  "work_style": "how they operate — 2 sentences",\n'
            '  "strengths": ["strength1", "strength2", "strength3"],\n'
            '  "communication_preference": "how to assign work to them effectively — 1-2 sentences"\n'
            "}"
        )

        ai_profile: dict = {}
        try:
            result = self._runtime.run(
                task_type=TaskType.ANALYZE,
                prompt=prompt,
                max_tokens=400,
                agent="human_intelligence.team",
            )
            raw = result.output.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-z]*\n?", "", raw)
                raw = raw.rstrip("`").strip()
            ai_profile = json.loads(raw)
        except Exception as e:
            print(f"[HumanIntel] Team member AI synthesis failed: {e}")
            ai_profile = {
                "work_style":               "Could not synthesize — insufficient data.",
                "strengths":                [],
                "communication_preference": "unknown",
            }

        profile = {
            "user_id":                  user_id,
            "human_type":               "team_member",
            "role":                     member_data.get("role", "unknown"),
            "work_style":               ai_profile.get("work_style", "unknown"),
            "strengths":                ai_profile.get("strengths", []),
            "communication_preference": ai_profile.get("communication_preference", "unknown"),
            "reliability_score":        reliability_score,
        }

        # Store in memory.db under username = user_id, venture = 'team'
        self._store_profile(user_id, "team", profile)
        return profile

    # ─── Public: adapt_communication ────────────────────────────────────────

    def adapt_communication(
        self,
        target_human: str,
        human_type: Literal[
            "lead", "team_member", "collaborator",
            "partner", "investor", "prospect"
        ],
        message: str,
        context: str = "",
    ) -> str:
        """
        Adapt a message to this specific human's style and role context.

        A message to an investor reads differently than the same message
        to a team member or a lead. Routes through Sonnet.

        Returns adapted message string, or original if profile not found.
        """
        venture_id = "lyfe_institute" if human_type in ("lead", "prospect") else "team"
        profile    = self.get_profile(target_human, venture_id)

        # Fall back: just use human_type context if no profile
        profile_block = ""
        if profile:
            if human_type == "lead":
                profile_block = (
                    f"  Dominant pain       : {profile.get('dominant_pain', 'unknown')}\n"
                    f"  Communication style : {profile.get('communication_style', 'unknown')}\n"
                    f"  Recommended tone    : {profile.get('recommended_tone', 'unknown')}\n"
                )
            elif human_type == "team_member":
                profile_block = (
                    f"  Work style          : {profile.get('work_style', 'unknown')}\n"
                    f"  Comm preference     : {profile.get('communication_preference', 'unknown')}\n"
                    f"  Strengths           : {', '.join(profile.get('strengths', []))}\n"
                )
            else:
                profile_block = json.dumps(profile, indent=2)[:400]

        type_context = {
            "lead":         "a potential customer in the sales funnel",
            "team_member":  "a team member who needs task-oriented, clear instructions",
            "collaborator": "an external collaborator — professional but relationship-aware",
            "partner":      "a strategic business partner — mutual value framing required",
            "investor":     "an investor — ROI focus, risk awareness, confidence and precision",
            "prospect":     "a warm prospect — discovery-oriented, no pressure",
        }.get(human_type, human_type)

        prompt = (
            f"You are adapting a message for a specific human in a founder's ecosystem.\n\n"
            f"TARGET: @{target_human}\n"
            f"TYPE: {human_type} — {type_context}\n\n"
            + (f"THEIR PROFILE:\n{profile_block}\n\n" if profile_block else "")
            + (f"CONTEXT: {context}\n\n" if context else "")
            + f"ORIGINAL MESSAGE:\n{message}\n\n"
            "Rewrite this message adapted to this person's type and profile. "
            "Keep the same intent. Adjust: tone, formality, framing, and emphasis "
            "based on who they are and what they need to hear. "
            "Return ONLY the adapted message — no labels, no commentary."
        )

        try:
            result = self._runtime.run(
                task_type=TaskType.GENERATE,
                prompt=prompt,
                max_tokens=400,
                agent="human_intelligence.adapt",
            )
            return result.output.strip()
        except Exception as e:
            print(f"[HumanIntel] adapt_communication failed: {e}")
            return message

    # ─── Public: get_relationship_context ───────────────────────────────────

    def get_relationship_context(self, username: str) -> str:
        """
        Returns a brief for any human in the system:

        "Here is what we know about [name]:
         communication style, relationship history,
         last interaction, recommended approach"

        Injected into agent calls when this human is involved.
        Checks both lead profiles and team profiles.
        """
        # Check lead profile first
        profile = self.get_profile(username, "lyfe_institute")
        if profile:
            human_type = profile.get("human_type", "lead")
            last = profile.get("last_contact", "unknown")
            stage = profile.get("kanban_stage", "unknown")
            style = profile.get("communication_style", "unknown")
            pain  = profile.get("dominant_pain", "unknown")
            tone  = profile.get("recommended_tone", "unknown")
            nba   = profile.get("next_best_action", "unknown")

            return (
                f"RELATIONSHIP BRIEF: @{username}\n"
                f"  Type:           {human_type}\n"
                f"  Pipeline stage: {stage}\n"
                f"  Last contact:   {last}\n"
                f"  Comm style:     {style}\n"
                f"  Dominant pain:  {pain}\n"
                f"  Recommended tone: {tone}\n"
                f"  Next action:    {nba}"
            )

        # Check team profile
        profile = self.get_profile(username, "team")
        if profile:
            return (
                f"RELATIONSHIP BRIEF: @{username}\n"
                f"  Type:           team_member\n"
                f"  Role:           {profile.get('role', 'unknown')}\n"
                f"  Work style:     {profile.get('work_style', 'unknown')}\n"
                f"  Comm preference: {profile.get('communication_preference', 'unknown')}\n"
                f"  Reliability:    {profile.get('reliability_score', '?')}/10"
            )

        return (
            f"RELATIONSHIP BRIEF: @{username}\n"
            f"  No profile found. This person has not been profiled yet.\n"
            f"  Recommend: run build_profile('{username}') before engaging."
        )


# ─── Profile formatting helper (used by orchestrator + status) ────────────────

def format_profile(profile: dict) -> str:
    lines = [
        f"  Username        : @{profile.get('username', '?')}",
        f"  Archetype       : {profile.get('archetype', '?')}",
        f"  ICP Score       : {profile.get('icp_score', '?')}/10",
        f"  Pipeline Stage  : {profile.get('kanban_stage', '?')}",
        f"  Dominant Pain   : {profile.get('dominant_pain', '?')}",
        f"  Comm Style      : {profile.get('communication_style', '?')}",
        f"  Recommended Tone: {profile.get('recommended_tone', '?')}",
        f"  Objection Risk  : {', '.join(profile.get('objection_risk', []))}",
        f"  Next Best Action: {profile.get('next_best_action', '?')}",
    ]
    return "\n".join(lines)
