# LyfeOS Full End-State Canon

**Phase:** 14.6B-LyfeOS
**Operator Approved:** false
**Allows Implementation:** false

This document describes the complete vision for LyfeOS including everything that exists today and everything planned for the future. Each section clearly labels what is current vs future.

---

## 1. Product Identity (End State)

**LyfeOS** — the Personal Life Operating System. A gamified platform that treats human life as a stateful system, providing measurement, planning, execution, reflection, and progression tools with AI-augmented coaching.

| Attribute | Current | End State |
|-----------|---------|-----------|
| Domain | lyfeos.net | lyfeos.net (same) |
| Hosting | Replit | Fly.io |
| Auth | Passport.js + Firebase | Clerk |
| AI Runtime | Local Anthropic SDK | UMH substrate AI runtime |
| Error Tracking | None | PostHog / Sentry |
| Analytics | None | PostHog |
| Backups | Unverified | Neon verified + tested recovery |
| CI/CD | None | GitHub Actions |
| RLS | None | Full RLS on all user-scoped tables |
| UMH Integration | None (from LyfeOS perspective) | Full projection registration |

---

## 2. Navigation (End State)

### Primary Navigation (5 tabs) [CODE_RESOLVED_CURRENT_TRUTH]
1. Dashboard
2. Missions
3. AI
4. Chronilog
5. Profile

### Secondary Navigation [CODE_RESOLVED_CURRENT_TRUTH + SOURCE_PRESERVED_TRUTH]
- Document Vault
- Tracker (analytics/milestone progress)
- Settings
- Contacts
- Kanban
- Spreadsheets
- Canvases
- Graphs
- Media

### Future Navigation Candidates [SOURCE_PRESERVED_TRUTH]
- Transformation Thread — a dedicated view tracking the user's transformation journey over time, connecting missions, reflections, and milestone completions into a narrative arc

---

## 3. AI Companion (End State)

### Current [CODE_RESOLVED_CURRENT_TRUTH]
- Default name: NOVA (user-renamable)
- Anthropic SDK (Haiku + Sonnet) + OpenAI SDK
- Threaded conversations with streaming
- 5+ AI tools (web search, page reading, goal creation, batch missions, uncomplete)
- 16-domain knowledge base
- Image analysis capability
- Full user data ingestion (salience engine)

### Future [UMH_INTEGRATION_DEPENDENT_GAP]
- NOVA connects to UMH agent runtime
- UMH governs AI tool execution (risk classification, audit trail)
- Cross-life intelligence: UMH correlates LyfeOS data with other projections
- Memory persistence through UMH memory subsystem
- Governed capability expansion (new tools registered through UMH)
- Multi-model routing through UMH model_router (CC SDK -> Gemini -> Ollama fallback chain)
- Deterministic fallback for all AI-powered features

### Future [INFERRED_PROFESSIONAL_GAP]
- Proactive AI (NOVA initiates conversations based on user patterns)
- AI-driven daily briefing (morning context from logs, calendar, missions)
- AI coaching curriculum (structured improvement programs)
- Natural language mission creation ("schedule a workout every Tuesday at 7am")

---

## 4. Gamification System (End State)

### Current [CODE_RESOLVED_CURRENT_TRUTH]
- 5 stat tokens (Energy, Health, Wealth, Time, Attention) at 100/100
- 3-tier XP system (levels 1-100)
- Mission difficulty ranks (S/A/B/C/D)
- Mission resource costs (energy, attention, time)
- XP rewards per mission
- Streaks and efficiency scoring
- Haptic feedback and sound effects
- Vision goals with 5 time horizons and bonus XP
- Canvas-confetti celebrations

### Future [INFERRED_PROFESSIONAL_GAP]
- Stat token decay mechanics (tokens decrease without maintenance)
- Achievement system (badges, milestones beyond XP)
- Leaderboards (opt-in social comparison)
- Seasonal challenges (time-limited missions with special rewards)
- Skill tree visualization (unlockable capabilities)
- Character class progression (archetype-based skill paths)

---

## 5. Onboarding (End State)

### Current [CODE_RESOLVED_CURRENT_TRUTH]
- 8 missions (0-7) with step-level tracking
- Mission 0: Demographics
- Mission 1: 54-question archetype calibration (6 archetypes)
- Missions 2-7: Progressive character sheet completion
- AI-generated character affirmation

### Future [INFERRED_PROFESSIONAL_GAP]
- Adaptive onboarding (skip sections based on existing data)
- Re-calibration option (retake archetype assessment)
- Onboarding analytics (completion rates, drop-off points)

---

## 6. Character Sheet (End State)

### Current [CODE_RESOLVED_CURRENT_TRUTH]
~90 named fields across 16 sections in user_profile table. Comprehensive coverage of identity, personality, vision, skills, health, wealth, performance, style, history, rituals, emotions.

### Future [INFERRED_PROFESSIONAL_GAP]
- Character sheet versioning (track changes over time)
- AI-powered field suggestions based on usage patterns
- Export as PDF/document
- Public profile option (shareable character card)

---

## 7. Integrations (End State)

### Current [CODE_RESOLVED_CURRENT_TRUTH]
- Google Calendar (read/write sync)
- Google Tasks (read-only import)
- Firebase Push Notifications (FCM)

### Current Placeholders [CODE_RESOLVED_CURRENT_TRUTH]
- Apple Health (boolean flag, no implementation)
- Notion (boolean flag, no implementation)

### Documented [SOURCE_PRESERVED_TRUTH]
- Obsidian import/export
- Evernote import/export

### Future [INFERRED_PROFESSIONAL_GAP]
- Apple Health data sync (sleep, activity, heart rate -> stat tokens)
- Notion bidirectional sync (pages <-> documents)
- Todoist/TickTick import (existing task migration)
- Spotify integration (music tracking for mood/productivity correlation)
- Strava/fitness tracker integration
- Banking API integration (wealth token automation)
- Calendar providers beyond Google (Outlook, Apple Calendar)

### Future [UMH_INTEGRATION_DEPENDENT_GAP]
- UMH event bus for cross-projection data flow
- UMH-governed integration activation
- Audit trail for all external data access

---

## 8. Authentication (End State)

### Current [CODE_RESOLVED_CURRENT_TRUTH]
- Passport.js + bcrypt (local)
- Firebase (Google/Apple/Facebook OAuth, email verification, 2FA)
- Express sessions + Postgres session store

### Future [SYNTHESIZED_CANON]
- **Clerk migration** — standardized auth across all Trinity apps
- Single Sign-On across LyfeOS, CreatorOS, EOS
- Role-based access control (admin, premium, free)
- API key management for third-party integrations
- Session management dashboard

### Migration Priority [SYNTHESIZED_CANON]
Lower than CreatorOS (LyfeOS auth works, no security bypass vulnerability). Migrate after CreatorOS proves the Clerk pattern.

---

## 9. Security (End State)

### Current [CODE_RESOLVED_CURRENT_TRUTH]
- Helmet security headers
- bcrypt password hashing
- Drizzle parameterized queries (SQL injection prevention)
- Zod input validation
- HTTPS (via Replit hosting)

### Future [INFERRED_PROFESSIONAL_GAP]
- **RLS on all 35 user-scoped tables** — critical for multi-user scenarios
- CSP (Content Security Policy) headers
- CORS configuration review
- Rate limiting on all public endpoints, strict limits on AI endpoints
- Security audit and penetration testing
- Secret rotation policy
- Session timeout configuration
- IP-based anomaly detection

---

## 10. Infrastructure (End State)

### Current [CODE_RESOLVED_CURRENT_TRUTH]
- Replit hosting
- Neon Postgres (serverless)
- Manual deployment (build.sh)
- /api/health endpoint

### Future [SYNTHESIZED_CANON]
- **Fly.io deployment** with Dockerfile and fly.toml
- **GitHub Actions CI/CD** — build, test, lint on PR; deploy on merge
- **Neon backup verification** — confirm plan, test recovery
- **PostHog** — product analytics + error tracking
- **Structured logging** (Winston or Pino)
- **Uptime monitoring** (UptimeRobot, Better Uptime, or similar)
- **Zero-downtime deploys** via Fly.io rolling updates
- **Database connection pooling** (Neon serverless handles this but verify)
- **CDN for static assets** (Fly.io edge or Cloudflare)

---

## 11. Test Coverage (End State)

### Current [CODE_RESOLVED_CURRENT_TRUTH]
- 2 test files, 21 test cases
- api-auth.test.ts: 10 integration tests
- xp-calculations.test.ts: 11 unit tests
- Framework: Vitest

### Future [INFERRED_PROFESSIONAL_GAP]
- API route test coverage for all endpoints (quests, daily logs, vision goals, documents, contacts, kanban, etc.)
- Component tests (React Testing Library)
- E2E tests (Playwright)
- XP/gamification edge case tests
- Auth flow tests (OAuth, 2FA, email verification)
- Google integration tests (mock OAuth flow)
- AI response tests (mock Anthropic SDK)
- Schema migration tests
- Performance tests (API response times under load)

---

## 12. UMH Connection (End State)

### Current [CODE_RESOLVED_CURRENT_TRUTH]
UMH has a one-way integration layer at projections/lyfeos/integration/ (1184 lines). Direct Postgres polling. LyfeOS is unaware of UMH.

### Future [UMH_INTEGRATION_DEPENDENT_GAP]
Full details in `lyfeos_umh_connected_future_canon.md`. Summary:

1. LyfeOS registers as UMH projection
2. NOVA connects to UMH agent runtime
3. Auth flows through UMH (Clerk)
4. Memory persists through UMH memory subsystem
5. All AI tool executions governed by UMH risk classification
6. Cross-life intelligence from UMH (correlate LyfeOS with CreatorOS, EOS data)
7. Audit trail for all automated actions
8. Failover mode: LyfeOS works standalone if UMH is unavailable

---

## 13. Transformation Thread (Future Candidate)

**Provenance:** SOURCE_PRESERVED_TRUTH

Not implemented in code. Design concept: a dedicated narrative thread that connects a user's daily missions, reflections, milestone completions, and archetype evolution into a visible transformation story. Would pull from:
- user_daily_logs (reflections)
- quests (completed missions)
- vision_goals (milestone achievements)
- user_profile (archetype changes, vision updates)
- conversations (key AI coaching moments)

This would be the "proof of transformation" that makes LyfeOS unique — not just tracking life, but showing you how you have changed.

---

## 14. Monetization (End State)

### Current [CODE_RESOLVED_CURRENT_TRUTH]
- Stripe removed (stub fields and endpoints preserved)
- No active payment processing
- Waitlist email collection active

### Future [INFERRED_PROFESSIONAL_GAP]
- Freemium model with premium tier
- Premium features: advanced AI (Sonnet-level), unlimited conversations, advanced analytics, custom integrations
- Stripe reconnection for subscription management
- stripeCustomerId and stripeSubscriptionId fields already in schema (ready for reconnection)
