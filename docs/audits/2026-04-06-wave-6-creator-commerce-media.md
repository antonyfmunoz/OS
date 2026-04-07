# Wave 6 — Creator, Commerce, Finance, Ads & Media Tool Mastery
Date: 2026-04-06
Author: Developer Agent
Scope: Business-surface Tool Mastery Engine skills for EOS.

## Objective

Fill the business surface of EOS's Tool Mastery Engine: the platforms
Antony actually uses to run Munoz Conglomerate day-to-day — content
distribution, ecommerce, banking, payroll, ads, analytics, and creative
production. Wave 5 covered the runtime substrate; Wave 6 covers the
revenue surface.

This is a **mega wave**: 33 new skills + 1 refresh = **34 skill
operations** in a single pass, executed via parallel end-to-end
subagent dispatch (research + synthesis merged per tool to eliminate
handoff loss).

## Skills delivered

| Skill | Action | SKILL.md | best_practices.md |
|---|---|---:|---:|
| kit | create | 255 | 1113 |
| tiktok | create | 226 | 1071 |
| youtube | create | 211 | 912 |
| twitch | create | 271 | 1228 |
| pinterest | create | 252 | 1226 |
| rumble | create | 242 | 998 |
| kick | create | 237 | 880 |
| whop | create | 288 | 1098 |
| meta_graph_api | create | 277 | 1577 |
| instagram | refresh | 379 | 1185 |
| shopify | create | 306 | 1507 |
| amazon_seller_central | create | 323 | 1392 |
| amazon_ads | create | 317 | 1121 |
| amazon_associates | create | 259 | 1074 |
| aws | create | 309 | 1027 |
| quickbooks | create | 253 | 1362 |
| mercury | create | 203 | 1038 |
| gusto | create | 238 | 944 |
| relay | create | 200 | 912 |
| google_ads | create | 259 | 904 |
| youtube_ads | create | 229 | 816 |
| meta_ads | create | 243 | 1248 |
| tiktok_ads | create | 339 | 970 |
| google_analytics | create | 255 | 1099 |
| higgsfield | create | 216 | 670 |
| photoshop | create | 281 | 1265 |
| illustrator | create | 228 | 942 |
| lightroom | create | 312 | 1416 |
| acrobat | create | 286 | 955 |
| canva | create | 326 | 1101 |
| clo3d | create | 229 | 774 |
| davinci_resolve | create | 256 | 1318 |
| obs | create | 234 | 906 |
| fl_studio | create | 231 | 808 |

Total: **~37,000 lines** of creator-level operational knowledge across
34 tools.

## Scope discipline

- ✅ SKILL.md (6 sections + 10-field frontmatter)
- ✅ references/best_practices.md (19 sections + EOS Usage Patterns + Gotchas)
- ❌ examples.md / anti_patterns.md / integrations.md — intentionally
  omitted, absorbed into best_practices.md depth (Wave 5 convention)

## Decomposition decisions

- **Amazon** split into 4 skills: `amazon_seller_central`, `amazon_ads`,
  `amazon_associates`, `aws` — each has a distinct API surface and
  auth model.
- **Facebook** resolved as: refresh existing `instagram` skill in place
  + create new `meta_graph_api` skill for the unified cross-Meta auth
  layer (Pages, Groups, Messenger, WhatsApp, Threads). Instagram now
  cross-references meta_graph_api for auth/token/webhook mechanics.
- **GUI-only tools** (higgsfield, clo3d, fl_studio, parts of
  photoshop/illustrator/lightroom/acrobat) framed as "human operator
  skills" per Wave 5 convention — agents draft briefs, Antony executes.
- **Ad surfaces** use `_ads` suffix consistently (google_ads, youtube_ads,
  meta_ads, tiktok_ads). `youtube_ads` cross-references `google_ads`
  for base mechanics since YouTube video ads run through the Google
  Ads API.
- **AWS** intentionally coarse (operator's-eye view) — per-service
  decomposition deferred to a future wave.

## Execution method

Parallel end-to-end subagents (research + synthesis per tool in a
single agent context), capped at 6 concurrent. WebSearch only —
WebFetch is permission-denied in subagent context. Total wall-clock
dispatch-to-last-completion measured in hours, not days.

## Verification status

| Check | Result |
|---|---|
| All 34 SKILL.md files have valid YAML frontmatter | ✅ |
| All 34 `last_researched` set to 2026-04-06 | ✅ |
| All 34 `version` = 1.0 | ✅ |
| All 34 best_practices.md have 19 sections | ✅ (whop uses `###` subsections under 2 `##` tier headers — structurally equivalent) |
| best_practices.md line floor (>600 for GUI, >800 for API) | ✅ |
| No examples.md / anti_patterns.md / integrations.md created | ✅ |
| instagram existing Playwright/Apify/ManyChat content preserved | ✅ |

## Commits

34 individual commits on main, naming convention:
`Add tool skill: {name}` (33) + `Refresh tool skill: instagram` (1).
Plus this audit report commit.

## Key business capabilities unlocked

**Creator/Social (Batch A)** — EOS now reasons about every platform
Antony publishes on: Kit email campaigns, TikTok/YouTube/Twitch/Kick/
Rumble/Pinterest organic posting, Whop creator monetization, and the
unified Meta Graph API surface (Pages/Groups/Messenger/WhatsApp/
Threads). Instagram refreshed with Reels/Stories/Insights/Shopping
endpoints and post-April-2025 metric deprecations.

**Commerce (Batch B)** — Lyfe Spectrum ecommerce surface fully mapped:
Shopify Admin GraphQL + Functions + Storefront, Amazon SP-API for
multi-marketplace inventory/orders/feeds, Amazon Ads v3 for
launch-phase sponsored campaigns, Amazon Associates PA-API 5.0 for
affiliate revenue (with sunset warning — hard shutdown 2026-05-15,
successor is Creators API), and the coarse AWS operator skill for
when VPS-first architecture hits its limits.

**Finance & Operations (Batch C)** — QuickBooks Online (multi-entity
realmId support, JournalEntry draft-for-approval pattern), Mercury
(primary banking, read/write split, HIGH-risk authority class),
Gusto Payroll (CRITICAL risk — agents draft, humans submit), and
Relay (honestly documented as no-public-API, Plaid/QBO bank feed is
the read path).

**Ads & Analytics (Batch D)** — Google Ads API v23.1 (Feb 2026),
YouTube video ads as Google Ads sub-surface, Meta Marketing API v23+
(ODAX objectives, CAPI with deduplication, Advantage+ campaigns),
TikTok Marketing API v1.3 (Spark Ads as the canonical organic-boost
pattern), GA4 Data API + Admin API + Measurement Protocol. Every ad
surface enforces `budget = CRITICAL risk, human-approved` at the
skill level.

**AI Media (Batch E)** — Higgsfield AI video generation documented
as human operator skill with the 50+ camera-move catalog as the core
prompt reference. No public API confirmed.

**Adobe Creative Suite (Batch F)** — Photoshop (hybrid: GUI + UXP +
Photoshop API + Firefly), Illustrator (GUI-primary + UXP), Lightroom
(three flavors: Classic, Cloud, Firefly Services Lightroom API),
Acrobat (hybrid: PDF Services API for headless + Acrobat Pro GUI +
Acrobat Sign). IMS OAuth Server-to-Server as the shared auth model.

**Other Creative Production (Batch G)** — Canva Connect API (with
Enterprise-tier autofill paywall documented as binding cost
constraint), CLO 3D (Lyfe Spectrum garment workflow, GUI-only),
DaVinci Resolve (hybrid: GUI + Python scripting API — real
agent-callable surface for headless render dispatch), OBS Studio
(hybrid: GUI + obs-websocket v5 as real agent surface), FL Studio
(GUI-only DAW for future music venture and brand content audio).

## Issues / follow-ups

1. **Neon sync gap persists.** Wave 5 flagged it; Wave 6 did not
   resolve it. Skill registry rows for these 34 skills must be
   inserted/updated via a future automation pass or manual insert.
2. **Verification script gap.** Only `scaffold_tool_skill.py` exists
   in the Tool Mastery Engine. A linter checking 19-section presence
   + frontmatter validity + line floors should be built as a meta wave.
3. **whop structure quirk.** whop's best_practices.md uses `### `
   subsections under 2 `## ` tier headers rather than 19 top-level
   `## ` sections. Structurally equivalent content but future
   verification scripts should count both `##` and `###` or the
   whop file should be refactored.
4. **higgsfield and clo3d under 800-line floor.** Content-justified
   by GUI-tool N/A sections, but worth flagging for future expansion
   if these tools ship real APIs.
5. **Amazon Associates sunset 2026-05-15.** PA-API 5.0 hard shutdown.
   Successor is Creators API with new credentials. Skill marked with
   `speed_category: sunset` and sunset-countdown pattern documented.
   Follow-up wave needed when Creators API matures.
6. **Canva autofill paywalled behind Enterprise tier** (~$30/user/mo).
   Binding cost constraint for pre-revenue solo founder. Skill
   documents GUI Bulk Create on Pro tier as interim workaround.
7. **AWS skill is intentionally coarse.** Per-service decomposition
   (IAM, S3, Lambda, EC2, CloudWatch, etc.) deferred — flag only,
   not blocking.
8. **MEMORY.md recent_builds index** should be updated to reference
   Wave 6 (34 new/refreshed tool mastery skills) — separate task.
