---
name: icp-signal-detection
description: "Identify high-probability Initiate Arena leads from Instagram content, profiles, and engagement — run during prospecting scans to build the qualified lead list."
allowed-tools: "Read"
trigger: scheduled
version: 1.0
---

# Skill: ICP Signal Detection

## Purpose

Identify accounts that are high-probability Initiate Arena leads based on content they post, comments they leave, and signals visible in their profile. Outputs a qualified prospect list ready for dm_opener.

---

## Outcome

A list of qualified accounts with signal classification (HIGH / MEDIUM / LOW signal strength) and the specific signal observed — ready for outreach sequencing.

---

## Best-Practice Benchmark

The best lead sourcing is pain-first, not demographic-first. An account that looks right (male, 22, gym content) but expresses no pain is a worse lead than an account that expresses explicit ownership of a struggle. Signal quality over account aesthetics.

---

## Decision Criteria

**ICP Profile:**
- Male, 18-25, English-speaking
- Posting about: discipline, self-improvement, fitness, business ideation, personal development
- Not already coaching, not already successful at the thing Initiate Arena solves
- Not a pure entertainment or humor account

**Signal Strength Classification:**

HIGH SIGNAL — pursue immediately
- Explicitly posts about a pattern of starting and stopping ("third time this year starting over")
- Comments expressing frustration with their own execution ("I have the plan, I just can't stick to it")
- Posts about "wasting time", "needing accountability", "getting serious this time"
- Ownership language present: "I keep", "I always", "I can't seem to", "I need to figure out"
- Posts showing self-awareness of the problem without blaming externals

MEDIUM SIGNAL — add to watch list, outreach within 7 days
- Regular gym or morning routine content without explicit pain expression
- Business ideation content (starting something, working on a project)
- Motivational content they post for themselves, not for an audience
- Bio signals: "building", "figuring it out", "work in progress"

LOW SIGNAL — do not pursue now
- Pure motivation reposting without personal context
- Fitness content with no execution struggle expressed
- Business content with success framing only
- Professional-looking account that appears further along than the ICP

NEGATIVE SIGNAL — disqualify
- Already coaches others (even casually — "helping guys get fit")
- Already successful at discipline/fitness/business at a high level
- Pure entertainment, humor, or lifestyle content with no development angle
- Engagement farming patterns (rapid generic commenting across many accounts)
- Bot signals: follower/following ratio anomaly, generic English, no personal content

---

## Execution Steps

1. Load the prospect batch from: `03_CRM/Leads/` or from Apify scrape output
2. For each account, review:
   - Last 9 posts (content and captions)
   - Bio text
   - Recent comments they've left on other accounts (if visible)
   - Story highlights if visible
3. Score against signal classification above
4. For HIGH and MEDIUM signals: extract the specific signal observed (exact quote if possible)
5. Output lead list with:
   - Account handle
   - Signal strength: HIGH / MEDIUM / LOW
   - Signal observed (specific, quoted if possible)
   - Recommended opener angle (what observation to reference)
   - Platform priority: Instagram DM first, then X/Twitter reply if available
6. Save output to: `03_CRM/Leads/qualified_YYYY-MM-DD.md`
7. Pass HIGH signal accounts to dm_opener immediately

---

## Platform Priority

Instagram (primary): DM is the primary conversion channel for this ICP. Instagram engagement signals (comments, captions) are highest quality.

X/Twitter (secondary): Reply to threads where ICP is expressing pain publicly. Lower conversion than DM but scales differently.

---

## Failure Modes

- Pursuing LOW signal accounts to hit volume targets — this is a data contamination error, not a volume win
- Classifying based on aesthetic (good photos, big following) instead of signal
- Missing NEGATIVE signals — sending outreach to an account that's already coaching or successful makes the brand look out of touch
- Not recording the specific signal observed — without it, dm_opener can't write a personalized opener
- Classifying a MEDIUM as HIGH to justify immediate outreach — this inflates the lead list quality and depresses reply rate over time

---

## Measurement

- HIGH signal account → reply rate (target: 20%+)
- MEDIUM signal account → reply rate (track separately from HIGH)
- Qualification accuracy: % of HIGH accounts that advance to discovery conversation
- Signal detection speed: accounts identified per hour of scan time

---

## Improvement Opportunities

- Build a signal pattern library from successful outreach — which signal types produce the highest reply rates
- Add recency weighting: a post from today with HIGH signal beats a post from 6 months ago with HIGH signal
- Track which account types consistently false-positive (look like HIGH but don't reply) and refine the classification criteria

---

## Gotchas

- An account that posts a lot is not a signal. The content of what they post is the signal. High-frequency posting of generic content is a NEGATIVE signal for engagement quality, not a POSITIVE one.
- Ownership language is only valid when it's about themselves, not advice they're giving others. "You need to hold yourself accountable" is advice content. "I need to hold myself accountable" is ownership language.
- Gym content alone is MEDIUM at best. Gym content plus frustration language is HIGH. Gym content plus success framing is LOW.
- The "getting serious" signal is real but fleeting. Accounts that post "new me starting today" without follow-through over weeks are HIGH signal — that's exactly the start-stop pattern Initiate Arena solves.
- Accounts with 10K+ followers who are posting about struggling with discipline may already have an audience who sees them as the authority. Approach carefully — the pain may be performative rather than genuine.
- Never infer pain that isn't explicitly expressed. If you're guessing they're struggling based on the type of content they post — that's not a signal, that's a projection.