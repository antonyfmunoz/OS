# CRM — How It Works

## Structure

```
03_CRM/
├── Pipeline.md           ← Kanban board — open this daily
├── README.md             ← this file
├── Leads/                ← one file per lead, auto-created by icp_scorer.py
├── Conversations/        ← DM conversation logs, one file per person
├── Outreach_Messages/    ← batch outreach scripts, generated per pipeline run
└── Archive/              ← old index files and deprecated docs
```

Pipeline stages (New → Contacted → Replied → Qualifying → Booked → Won → Lost) live entirely in `Pipeline.md` as Kanban columns. There are no separate stage folders.

---

## The Kanban Board (Pipeline.md)

Open `Pipeline.md` in Obsidian to see your full pipeline as a drag-and-drop board.

**Columns and what they mean:**

| Stage | Meaning | Action |
|---|---|---|
| New | Identified, opener not sent | Send the opener DM |
| Contacted | Opener sent, no reply yet | Follow up after 48h |
| Replied | Conversation active | Continue qualifying |
| Qualifying | Deep pain discovery underway | Confirm ICP fit |
| Booked | Discovery call scheduled | Prepare and show up |
| Won | Converted to paying client | Move to 08_Clients |
| Lost | No-fit or ghosted after follow-up | Archive |

**Moving a lead:** Drag the card to the next column, or manually edit the `kanban_stage` field in the lead file's frontmatter.

---

## Lead File Frontmatter Fields

Every lead file in `03_CRM/Leads/` has this frontmatter:

```yaml
---
type: lead                     # Always "lead" — used by Dataview queries
name: username                 # Instagram handle (no @)
platform: instagram            # Where they came from
status: new                    # Lowercase stage: new / contacted / replied / qualifying / booked / won / lost
offer: Initiate Arena          # Which offer they're being qualified for
source: "#hashtag"             # Hashtag or @competitor account where signal was found
icp_score: 8                   # Claude's score 1–10 (8+ = qualified)
archetype: Ambitious but Stuck # Frustrated Drifter | Ambitious but Stuck | Ego Defender | Other
pain_signals:                  # Array of pain signals Claude identified
  - signal one
  - signal two
post_url: https://...          # Instagram post URL where comment was found
comment: "their comment text"  # The raw comment that triggered qualification
last_contact:                  # ISO date of last DM sent (fill manually)
next_action: send_opener       # What to do next
next_action_date: 2026-03-16   # When to do it
kanban_stage: New              # Mirrors the Kanban column — update when you move the card
tags:
  - crm
  - lead
  - initiate-arena
---
```

**When you move a lead through stages, update two things:**
1. Drag the card in `Pipeline.md`
2. Update `kanban_stage:` and `status:` in the lead file frontmatter

---

## How Leads Are Created (Automated Flow)

```
Instagram comments
      ↓
apify_scraper.py     — scrapes comments from hashtags / competitor accounts
      ↓
01_Inbox/raw_signals/ — saved as signal_*.md files
      ↓
icp_scorer.py        — Claude Haiku scores each comment against ICP profile
      ↓
Score ≥ 7 → lead_*.md created in 03_CRM/Leads/
           → card added to ## New column in Pipeline.md
Score < 7 → disqualified, moved to 01_Inbox/processed_signals/
```

Run the full pipeline:
```bash
python 13_Scripts/apify_scraper.py   # scrape
python 13_Scripts/icp_scorer.py      # score + qualify
```

---

## Daily Workflow

1. **Open Pipeline.md** — review the New column
2. **For each New lead:** open the lead file, read their comment and the suggested opener
3. **Send the opener DM** on Instagram
4. **Drag the card to Contacted**
5. **Update `kanban_stage: Contacted`** and `last_contact: YYYY-MM-DD` in the file
6. **When they reply:** drag to Replied, log the conversation in `03_CRM/Conversations/`
7. **Qualifying → Booked:** invite to a 20-min call once pain is confirmed
8. **Won/Lost:** move the card and file accordingly

---

## Archetypes

| Archetype | Core Pain | Opener Angle |
|---|---|---|
| Ambitious but Stuck | Capable but weeks disappear, no output | Architecture problem, not motivation |
| Frustrated Drifter | Starts things, never finishes, shame compounding | Finishing is a built skill, not a trait |
| Ego Defender | "I'm already doing this" — deflects | Disqualify immediately, do not pursue |

Opener scripts for each archetype are in `03_CRM/Outreach_Messages/`.

---

## Dataview Queries

The dashboards in `00_Dashboard/` query lead files using these fields:
- `type = "lead"` — filters to lead files only
- `kanban_stage` — current pipeline stage
- `icp_score` — qualification score
- `archetype` — buyer type
- `next_action_date` — used for sorting by urgency
