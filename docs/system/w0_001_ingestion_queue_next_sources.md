# W0-001 Ingestion Queue — Next Sources

**Date**: 2026-05-04
**Purpose**: Sources referenced in ingested documents that should be crawled
for a complete understanding of the business and operational context.

---

## Priority 1: Direct Business Assets (Needed for Revenue)

| # | Source | Type | Referenced In | Why |
|---|--------|------|---------------|-----|
| Q1 | WHOP account (curriculum hosting) | Platform | Life Coaching doc | If Initiate Arena curriculum is hosted here, need to know what's built vs planned |
| Q2 | Discord server (community) | Platform | Life Coaching doc | Community structure, channels, existing members if any |
| Q3 | Instagram account (outreach) | Platform | Hormozi conversation | DM templates, follower count, engagement data, ICP conversations |
| Q4 | Calendly booking page | Platform | AI Tools | What calls are bookable, current scheduling configuration |

## Priority 2: Product/Tech Assets

| # | Source | Type | Referenced In | Why |
|---|--------|------|---------------|-----|
| Q5 | lyfeos.net (beta app) | Web app | LyfeOS doc | Current state of the app, what's built, what's broken |
| Q6 | LYFEOS_Product_Development_Roadmap.docx | Word doc | Drive inventory | NEEDS_SEPARATE_EXPORT_APPROVAL — product roadmap for LyfeOS |
| Q7 | Notion workspace (referenced in Life Coaching) | Platform | Life Coaching doc | "Onboarding To Community / Explain System Philosophy / Set-Up Player Sheet" — may have curriculum content |

## Priority 3: Collaborator/External Accounts

| # | Source | Type | Referenced In | Why |
|---|--------|------|---------------|-----|
| Q8 | personalbrandlaunch (Google account) | Collaborator | Script Storytelling Structures | Who is this? Former business partner? Content coach? |
| Q9 | jeremy.ness (Google account) | Collaborator | Email Sequence | Email copywriter who wrote Game of Lyfe sequence |
| Q10 | connorsincoaching (Google account) | Contact | SEMAX doc | Fitness coach who shared nootropic content |
| Q11 | Hunter Hoffman | Client | Service Contract | Status of agency relationship — active, completed, churned? |

## Priority 4: Referenced Platforms (Tool Intelligence)

| # | Source | Type | Referenced In | Why |
|---|--------|------|---------------|-----|
| Q12 | GoHighLevel | CRM | AI Tools | Was this adopted? Active account? |
| Q13 | Apify account | Scraping | AI Tools | Active? What scrapers configured? |
| Q14 | Fathom.video | Meeting recording | AI Tools | Active? Coaching call recordings? |
| Q15 | PostHog | Analytics | AI Tools | Active? What's being tracked? |

## Priority 5: Content Archives

| # | Source | Type | Referenced In | Why |
|---|--------|------|---------------|-----|
| Q16 | YouTube/Instagram content archive | Published content | Content doc | What content has actually been published? Gap between plan and execution? |
| Q17 | Google Forms (intake forms?) | Forms | AI Tools | Client intake? Lead qualification? |

## Export Approvals Needed

| # | Item | Reason |
|---|------|--------|
| E1 | LYFEOS_Product_Development_Roadmap.docx | Word doc — requires export/download to read content. Currently marked NEEDS_SEPARATE_EXPORT_APPROVAL. |

## Blocked Sources (Do Not Crawl Without Explicit Approval)

| Source | Reason |
|--------|--------|
| Gmail | Blocked by W0-001 policy |
| Google Calendar | Not in approved scope |
| Browser history/cookies | Blocked |
| Other Google accounts | Not approved |
| Financial accounts (bank, Stripe, etc.) | Not in scope |
| Phone contacts/messages | Not in scope |

## Recommended Next Ingestion Priority

1. **Export LYFEOS_Product_Development_Roadmap.docx** — only unread doc from Drive
2. **WHOP account** — is curriculum actually built?
3. **Discord server** — is community active?
4. **Instagram DM history** — actual outreach results and ICP conversations
5. **Notion workspace** — may contain more curriculum/framework content
