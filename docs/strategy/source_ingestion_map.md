# Source Ingestion Map

**Date**: 2026-05-03
**Status**: Planning artifact — no scraping performed, no accounts connected

This document maps every known data source the user owns or controls, prioritized for future ingestion into the UMH second-brain / user instance layer.

---

## Legend

| Priority | Meaning |
|----------|---------|
| Critical | Must be ingested before or during first workflow activation |
| High | Important for full operating capability |
| Medium | Valuable for complete second brain but not blocking |
| Low | Historical/archival value |

| Sensitivity | Meaning |
|-------------|---------|
| Public | Content already visible to the world |
| Private | Personal/business data not publicly visible |
| Sensitive | Contains credentials, financials, personal details |
| Mixed | Contains both public and private data |

---

## AI Chats

| Platform | Data Type | Priority | War Sprint? | First Workflow? | Full Brain? | Best Method | Computer Control? | Sensitivity | Review? | Notes |
|----------|-----------|----------|-------------|-----------------|-------------|-------------|-------------------|-------------|---------|-------|
| ChatGPT | Conversations, prompts, outputs, strategy discussions | Critical | YES | YES | YES | Export via Settings → Data Export (ZIP) | No | Private | YES | Contains years of strategic evolution, architecture decisions, doctrine |
| Claude (claude.ai) | Conversations, prompts, outputs | Critical | YES | YES | YES | Manual export / conversation history download | No | Private | YES | Architecture decisions, phase planning, strategy |
| Claude Code | Terminal logs, session history | Critical | YES | YES | YES | Local files at ~/.claude/ and project .claude/ dirs | No | Private | YES | Implementation reports, phase history, codebase decisions |
| Cursor | Chat history, codebase conversations | High | Partial | Partial | YES | Local files / export if available | No | Private | YES | Implementation details, code-level decisions |
| Replit Agent | Chat history, project conversations | Medium | No | No | YES | Export / manual copy | No | Private | YES | Historical build conversations |
| Local AI logs | Ollama, local model outputs | Low | No | No | YES | Local files on VPS | No | Private | No | Utility outputs, less strategic |

---

## Email

| Platform | Data Type | Priority | War Sprint? | First Workflow? | Full Brain? | Best Method | Computer Control? | Sensitivity | Review? | Notes |
|----------|-----------|----------|-------------|-----------------|-------------|-------------|-------------------|-------------|---------|-------|
| Gmail / Google Workspace | All email, lead/client correspondence | High | Partial | YES | YES | Gmail API or Google Takeout export | No | Sensitive | YES | Lead conversations, client emails, account notifications |
| Business emails | Domain-specific email if any | High | Partial | YES | YES | Same as Gmail if routed through GWS | No | Sensitive | YES | Business correspondence |

---

## Docs/Files

| Platform | Data Type | Priority | War Sprint? | First Workflow? | Full Brain? | Best Method | Computer Control? | Sensitivity | Review? | Notes |
|----------|-----------|----------|-------------|-----------------|-------------|-------------|-------------------|-------------|---------|-------|
| Google Drive | Strategy docs, decks, spreadsheets, shared files | Critical | YES | YES | YES | Google Drive API or Takeout export | No | Mixed | YES | Contains company strategy, product docs, business plans |
| Local folders | PDFs, Word docs, spreadsheets, media | High | Partial | Partial | YES | Direct file system read | No | Mixed | YES | Scattered across devices — need inventory |
| /opt/OS repo docs | Phase reports, architecture docs, CLAUDE.md, skills | Critical | YES | YES | YES | Already accessible — in repo | No | Private | No | Primary codebase documentation |
| Screenshots | UI screenshots, AI chat screenshots, design refs | Medium | No | No | YES | File system scan, OCR if needed | No | Mixed | Partial | May contain strategic context not captured elsewhere |
| Decks/Presentations | Pitch decks, strategy presentations | High | Partial | Partial | YES | Google Slides API or file export | No | Private | YES | Business strategy artifacts |

---

## Knowledge Systems

| Platform | Data Type | Priority | War Sprint? | First Workflow? | Full Brain? | Best Method | Computer Control? | Sensitivity | Review? | Notes |
|----------|-----------|----------|-------------|-----------------|-------------|-------------|-------------------|-------------|---------|-------|
| Obsidian | Notes, wiki, linked knowledge | Critical | YES | YES | YES | Direct file read (markdown vault) | No | Private | YES | Core knowledge base — may duplicate or conflict with other sources |
| Notion | Databases, pages, project management | Critical | YES | YES | YES | Notion API (integration token) | No | Mixed | YES | Contains business planning, product specs, task management |
| Miro | Boards, diagrams, brainstorms | High | Partial | Partial | YES | Miro API or board export | No | Private | YES | Visual strategy artifacts, architecture diagrams |
| Apple Notes / phone notes | Quick captures, ideas, voice-to-text | Medium | No | No | YES | iCloud export or manual transfer | Possibly | Private | YES | May contain unprocessed strategic ideas |
| Google Keep | Quick notes if used | Low | No | No | YES | Google Takeout | No | Private | Partial | |

---

## Media

| Platform | Data Type | Priority | War Sprint? | First Workflow? | Full Brain? | Best Method | Computer Control? | Sensitivity | Review? | Notes |
|----------|-----------|----------|-------------|-----------------|-------------|-------------|-------------------|-------------|---------|-------|
| Raw video | Unedited footage | Low | No | No | YES | File system scan | No | Private | No | Large files — metadata more useful than full ingest |
| Edited video | Published content | Medium | No | Partial | YES | File system + platform archives | No | Public | No | Content library for analysis |
| Content drafts | Scripts, outlines, captions | High | Partial | YES | YES | File system / Notion / Google Docs | No | Private | YES | Active content pipeline |
| Thumbnails/brand assets | Visual brand elements | Medium | No | Partial | YES | File system / Canva | No | Private | No | Brand asset library |
| Voice notes | Audio captures, ideas | Medium | No | No | YES | Phone file transfer, transcription | No | Private | YES | May contain strategic ideas |

---

## Social Media

| Platform | Data Type | Priority | War Sprint? | First Workflow? | Full Brain? | Best Method | Computer Control? | Sensitivity | Review? | Notes |
|----------|-----------|----------|-------------|-----------------|-------------|-------------|-------------------|-------------|---------|-------|
| Instagram | Posts, stories, reels, DMs, comments, analytics | Critical | Partial | YES | YES | Instagram API (limited), data download, manual export | Read-only if API insufficient | Mixed | YES | Primary distribution channel for first workflow |
| TikTok | Videos, comments, analytics | High | No | Partial | YES | Data download request | No | Public | Partial | Distribution channel |
| YouTube | Videos, comments, analytics | High | No | Partial | YES | YouTube Data API | No | Public | Partial | Distribution channel |
| X/Twitter | Posts, DMs, analytics | Medium | No | Partial | YES | Data export or API | No | Mixed | YES | |
| LinkedIn | Posts, connections, DMs | Medium | No | Partial | YES | Data export | No | Mixed | YES | Professional network |
| Discord | Messages, server content, community interactions | High | Partial | YES | YES | Bot API (already have os-discord) | No | Private | YES | Community fulfillment channel |
| Telegram | Messages, channels | Medium | No | No | YES | Telegram API / export | No | Private | YES | |
| Comments (all platforms) | Engagement data | High | No | YES | YES | Per-platform API or export | No | Public | Partial | Lead signals |
| DMs (all platforms) | Private conversations | Critical | Partial | YES | YES | Per-platform export | Possibly | Sensitive | YES | Lead conversations, client interactions |
| Analytics (all platforms) | Performance data | High | No | YES | YES | Per-platform API | No | Private | No | Content performance tracking |
| Saved posts | Bookmarks, collections | Low | No | No | YES | Per-platform export | No | Mixed | No | Reference material |

---

## Business Systems

| Platform | Data Type | Priority | War Sprint? | First Workflow? | Full Brain? | Best Method | Computer Control? | Sensitivity | Review? | Notes |
|----------|-----------|----------|-------------|-----------------|-------------|-------------|-------------------|-------------|---------|-------|
| CRM (if any) | Lead/client records | Critical | YES | YES | YES | API or export | No | Sensitive | YES | If using a CRM — else spreadsheet |
| Typeform / forms | Survey responses, applications | High | Partial | YES | YES | API or export | No | Private | YES | Lead qualification data |
| Stripe / payment | Transaction records, revenue | Critical | YES | YES | YES | Stripe API or dashboard export | No | Sensitive | YES | Revenue tracking |
| Calendly / scheduling | Booked calls, availability | High | Partial | YES | YES | API or export | No | Private | Partial | Sales pipeline data |
| Community platform | Member data, engagement | High | Partial | YES | YES | Platform API or export | No | Private | YES | Fulfillment tracking |
| Course platform (if any) | Student progress, curriculum | High | Partial | YES | YES | Platform API or export | No | Private | YES | Fulfillment delivery |

---

## Development

| Platform | Data Type | Priority | War Sprint? | First Workflow? | Full Brain? | Best Method | Computer Control? | Sensitivity | Review? | Notes |
|----------|-----------|----------|-------------|-----------------|-------------|-------------|-------------------|-------------|---------|-------|
| GitHub | Repos, commits, issues, PRs | Critical | YES | Partial | YES | GitHub API (gh CLI already available) | No | Private | No | Code history, architecture evolution |
| /opt/OS | Full project directory | Critical | YES | YES | YES | Direct file system | No | Private | No | Primary codebase — already accessible |
| Replit | Projects, deployments | Low | No | No | YES | Export or API | No | Private | No | Historical projects |
| VS Code | Settings, extensions, local workspace | Low | No | No | YES | File system | No | Private | No | Dev environment config |
| Deployment logs | Docker, service logs | Medium | Partial | Partial | YES | Docker logs, journalctl | No | Private | No | Runtime behavior |
| Claude Code logs | Session transcripts | Critical | YES | YES | YES | ~/.claude/ directory | No | Private | YES | Phase history, implementation decisions |

---

## Social Algorithm / Saved Media Intelligence

| Platform | Data Type | Priority | War Sprint? | First Workflow? | Full Brain? | Best Method | Computer Control? | Sensitivity | Review? | Notes |
|----------|-----------|----------|-------------|-----------------|-------------|-------------|-------------------|-------------|---------|-------|
| Instagram saved videos | Saved reels, posts, collections | High | No | Partial | YES | Data download / manual export | Only if export unavailable | Private | YES | Taste, aesthetic preferences, creative references |
| Instagram liked posts/videos | Liked content history | High | No | Partial | YES | Data download / manual export | Only if export unavailable | Private | YES | Subconscious interests, content pattern recognition |
| Instagram Reels feed samples | Algorithmic feed snapshot | Medium | No | No | YES | Manual screenshot/record + export | Only if export unavailable | Private | YES | What the algorithm believes about the user |
| Instagram Explore page samples | Discovery feed snapshot | Medium | No | No | YES | Manual screenshot/record + export | Only if export unavailable | Private | YES | Emerging trends, market awareness |
| Instagram search history | Search terms if accessible | Low | No | No | YES | Data download | No | Private | YES | Interest signals |
| Instagram follows/following | Account list | Medium | No | Partial | YES | Data download | No | Private | YES | Creator references, audience avatars |
| Instagram comments/DMs (business) | Business-related interactions | High | Partial | YES | YES | Data download / manual export | Possibly | Sensitive | YES | Lead signals, client interactions |
| TikTok saved/liked videos | Saved and liked content | High | No | No | YES | Data download request | No | Private | YES | Trend signals, content hooks, formats |
| YouTube watch history/saved | Watch history, playlists, saved | High | No | No | YES | Google Takeout | No | Private | YES | Learning interests, content consumption patterns |
| X/Twitter bookmarks | Bookmarked posts | Medium | No | No | YES | Data export | No | Mixed | Partial | Market awareness, thought leadership references |
| LinkedIn saved posts | Saved articles and posts | Low | No | No | YES | Data export | No | Mixed | Partial | Professional references |
| Discord/Telegram saved links | Bookmarked messages/links | Medium | No | No | YES | Bot API or manual export | No | Private | Partial | Community references, resource collection |

**Purpose**: The user's saved videos and recommendation feeds reveal taste, aesthetic preferences, subconscious interests, content pattern recognition, market awareness, creative references, algorithmic identity, attention loops, emerging trends, and brand/worldbuilding references.

**Extraction targets**: recurring topics, creators, hooks, formats, aesthetics, sounds/music, emotional triggers, business models, offer angles, audience avatars, visual references, worldbuilding references, content ideas, trend signals, attention loops, what the algorithm appears to believe about the user.

**Future capability**: Personal Algorithm Mirror / Attention Graph Reconstruction

**Safety rules for this category**:
- Read-only first — no auto-liking, auto-commenting, auto-following, auto-DMing
- No mass scraping
- No bypassing rate limits or protections
- No posting without approval
- Computer use only when export/API/manual collection is insufficient

---

## Multimodal Course / Content Sources

| Source Type | Data Type | Priority | War Sprint? | First Workflow? | Full Brain? | Best Method | Computer Control? | Sensitivity | Review? | Notes |
|-------------|-----------|----------|-------------|-----------------|-------------|-------------|-------------------|-------------|---------|-------|
| YouTube videos | Video content, transcripts | High | No | No | YES | YouTube API / manual transcript | No | Public | Partial | Learning, research, content references |
| Online courses | Course modules, lessons | High | No | No | YES | Manual export / platform download | Possibly | Private | YES | Frameworks, examples, tools, resources |
| Podcasts | Audio content, show notes | Medium | No | No | YES | RSS feed / transcript services | No | Public | Partial | Mental models, interviews, market insight |
| Saved social videos | Short-form content | Medium | No | No | YES | Data download / manual export | Only if export unavailable | Private | YES | Hooks, formats, aesthetics |
| Documents / PDFs | Written content | High | Partial | Partial | YES | Direct file read | No | Mixed | YES | Research, guides, reports |
| Screenshots / whiteboards | Visual captures | Medium | No | No | YES | OCR + file system scan | No | Private | YES | Ideas, frameworks, visual notes |
| Voice notes | Audio captures | Medium | No | No | YES | Transcription service | No | Private | YES | Unprocessed ideas, strategic thinking |
| Screen recordings | Video captures of workflows | Low | No | No | YES | File system | No | Private | Partial | Process documentation |
| Webinars | Live/recorded presentations | Medium | No | No | YES | Recording + transcript | Possibly | Mixed | YES | Industry insight, competitor analysis |
| Charts / dashboards | Data visualizations | Medium | No | No | YES | Screenshot + OCR | No | Mixed | YES | Market data, performance metrics |

**Future capability**: Multimodal Perception + Content Assimilation Engine

**Important distinction**: Perception is not execution. Watching, reading, extracting, and summarizing are perception/ingestion. Clicking, posting, sending, buying, editing, deleting, or changing account state is execution and must be governed.

---

## Physical Product / Manufacturing / Robotics Sources (Future)

| Source Type | Data Type | Priority | War Sprint? | First Workflow? | Full Brain? | Best Method | Computer Control? | Sensitivity | Review? | Notes |
|-------------|-----------|----------|-------------|-----------------|-------------|-------------|-------------------|-------------|---------|-------|
| CNC/prototyping references | Reference images, sketches, 3D scans, concept models | Medium | No | No | YES | File system / manual import | No | Private | YES | Product design references for CNC and prototyping workflows |
| Manufacturing videos | Process videos, machine operation, technique references | Medium | No | No | YES | File system / YouTube download | No | Mixed | Partial | Visual manufacturing knowledge, process references |
| Robotics component references | Actuator datasheets, motor specs, sensor references, gripper catalogs | Medium | No | No | YES | File system / manufacturer sites | No | Public | Partial | Component selection intelligence |
| Actuator datasheets | Technical specifications, performance curves, torque/speed data, dimensions | Medium | No | No | YES | Manufacturer downloads / PDF import | No | Public | No | Engineering reference data for actuator selection and custom design |
| CAD files | STEP, IGES, STL, Fusion 360, SolidWorks files | High | No | No | YES | File system import / CAD tool export | No | Private | YES | Engineering design artifacts — visual mesh ≠ manufacturing-ready CAD |
| BOMs (Bills of Materials) | Part lists, quantities, costs, suppliers, lead times | High | No | No | YES | Spreadsheet / ERP export | No | Private | YES | Manufacturing cost and supply chain intelligence |
| Supplier quotes | Pricing, lead times, MOQs, terms, certifications | High | No | No | YES | Email / file system / manual entry | No | Sensitive | YES | Procurement intelligence — contains pricing and terms |
| Test results | QC reports, stress tests, tolerance measurements, certification results | High | No | No | YES | Lab reports / file system | No | Private | YES | Quality validation data — required before manufacturing decisions |
| Machine logs | CNC operation logs, 3D printer logs, robot controller logs | Medium | No | No | YES | Machine interface export / USB | No | Private | No | Production monitoring and optimization data |
| Production QC records | Inspection results, defect logs, yield rates, batch records | High | No | No | YES | QC system export / manual entry | No | Private | YES | Manufacturing quality intelligence |

**Future capability**: Physical Product Intelligence Layer + Manufacturing Intelligence + Robotics/Actuator Component Intelligence

**Important distinctions**:
- AI-generated 3D meshes are NOT manufacturing-ready CAD
- Visual prototypes are NOT validated engineering artifacts
- Manufacturing decisions require engineering validation, tolerances, material selection, stress checks, quality testing, supplier review, safety review, and compliance review
- Actuator/component specifications require empirical testing — datasheet specs alone are insufficient

**Safety rules for this category**:
- No automated purchasing or ordering
- No automated manufacturing execution
- No automated firmware deployment to physical hardware
- All manufacturing/production decisions require human approval
- Supplier data treated as sensitive (pricing, terms, relationships)
- Test results and QC records require engineering review before action

---

## Local Workstation Baseline (Onboarding / Device Source)

| Source Type | Data Type | Priority | War Sprint? | First Workflow? | Full Brain? | Best Method | Computer Control? | Sensitivity | Review? | Notes |
|-------------|-----------|----------|-------------|-----------------|-------------|-------------|-------------------|-------------|---------|-------|
| Storage inventory | Disk usage, large files, cache sizes | High | No | Partial | YES | OS APIs / file system scan | No | Private | YES | Baseline for optimization recommendations |
| Installed apps | App list, versions, sizes, last used | High | No | Partial | YES | OS APIs / package manager query | No | Private | YES | Cleanup and startup audit |
| Startup items | Boot services, login items, scheduled tasks | High | No | Partial | YES | OS APIs / system config | No | Private | YES | Performance and boot time audit |
| Running processes | Process list, resource usage, service health | Medium | No | No | YES | OS APIs / process inspection | No | Private | No | Runtime health baseline |
| Thermal/power state | CPU temp, fan speed, power profile, throttling | Medium | No | No | YES | OS APIs / hardware sensors | No | Private | No | Hardware health baseline |
| Developer environment | node_modules, caches, Docker images, virtualenvs | High | No | Partial | YES | File system scan / tool queries | No | Private | YES | Developer storage optimization |
| Backup status | Backup freshness, coverage, destinations | High | No | Partial | YES | OS APIs / backup tool query | No | Private | YES | Safety net verification before optimization |
| Network config | Active connections, DNS, VPN, firewall state | Medium | No | No | YES | OS APIs / network inspection | No | Private | YES | Security and connectivity baseline |

**Phase**: 87C (planning-only — no real scanning in this phase)

**Governing doctrines**:
- **Local Workstation Onboarding Doctrine** (Phase 87C) — workstation baseline is part of onboarding, not optional later maintenance
- **Device Literacy Doctrine** (Phase 87C) — plain-language explanations precede any optimization action
- **Performance Tuning Safety Doctrine** (Phase 87C) — overclocking/undervolting/BIOS/fan/driver changes require explicit approval + expert review + stability testing + rollback plan
- **Destructive Action Approval Doctrine** (Phase 87C) — unknown = preserve, sensitive = preserve, system-critical = preserve, credential = preserve, user-created = review, generated/cache/temp = cleanup candidate with approval

**Safety rules for this category**:
- Planning-only in Phase 87C — no real device scanning, no execution
- No deletion, no process killing, no settings changes, no overclocking
- All optimization candidates are advisory — human approval required before any action
- Irreversible actions require rollback/backup plan or are blocked

---

## Computer Control Policy

Computer control (browser automation, screen interaction) is:
- **ONLY** used if export/API/local files are not available for a critical source
- **Read-only collection first** — no posting, sending, deleting, editing
- **Requires explicit user approval** per source before activation
- **Not part of this phase** — this is a planning artifact only

---

## Governing Doctrines

This source map is governed by and supports the following doctrines (see `docs/strategy/current_doctrine_index.md` for full descriptions):

- **Parallel Operating Cell Doctrine** — each operating cell may have its own data sources, ingestion cadence, and memory policy
- **Always-On Intelligence Doctrine** — background intelligence loops consume these sources continuously under governance
- **Algorithmic Self-Modeling Doctrine** — Social Algorithm / Saved Media Intelligence category serves this doctrine directly
- **Multimodal Course / Content Assimilation Doctrine** — Multimodal Course / Content Sources category serves this doctrine directly
- **Physical Product Sovereignty Doctrine** — future physical product sources (reference images, sketches, 3D scans, supplier catalogs) will be added as this capability develops
- **Human Evaluation + Negotiation Intelligence Doctrine** — meeting recordings, call transcripts, advisor correspondence are future ingestion sources governed by consent/compliance
- **Family Office / Capital Intelligence Doctrine** — market data feeds, portfolio reports, deal memos, and financial research are future ingestion sources
- **Distributed Runtime Doctrine** (Phase 87A) — source ingestion routes to the correct node based on capability requirements (e.g., Instagram scraping → Local PC with browser/accounts, API calls → VPS)
- **Local Embodiment Doctrine** (Phase 87A) — sources dependent on local browser sessions, saved passwords, or logged-in accounts default to Local PC node
- **Node-Aware Routing Doctrine** (Phase 87A) — tasks declare required capabilities and the routing advisory selects the safest valid node
- **Source-Class Abstraction Doctrine** (Phase 87B) — apps are not the primitive, source classes are. Gmail/Outlook/Apple Mail are all "email" implementations. System is tool-agnostic.
- **Permission-First Ingestion Doctrine** (Phase 87B) — no source ingested until user approves scope, access method, node location, sensitivity, and review behavior
- **User Instance Onboarding Ingestion Doctrine** (Phase 87B) — ingestion is part of first boot (progressive Tier 0–5), not optional later utility
- **Raw Before Memory Doctrine** (Phase 87B) — raw artifacts → parsed candidates → review → confidence/conflict/supersession checks → promotion. No raw-to-memory shortcut
- **Anti-Copycat Moat Doctrine** (Amendment v2) — product features alone are not defensible in the AI copycat economy; moat comes from proprietary data, distribution, execution speed, operating history, physical infrastructure, manufacturing, fulfillment, robotics, and capital allocation
- **Physical Infrastructure Moat Doctrine** (Amendment v2) — owned physical capabilities become more strategically valuable as digital products become easier to copy; progression from software to manufacturing to robotics to capital allocation
- **Custom Actuator / Robotics Component Doctrine** (Amendment v2) — buy commodity parts, customize strategic parts, own bottleneck parts, manufacture moat-critical parts
- **Physical Product Intelligence Layer** (Amendment v2) — future UMH capability for reference/sketch → 3D reconstruction → CAD brief → BOM → DFM/DFA → prototype → CNC/CAM → supplier matching → manufacturing memory → robotics integration
