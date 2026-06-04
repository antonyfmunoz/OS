# LyfeOS Security, Trust, Privacy, and Compliance Assessment

**Phase:** 14.6B-LyfeOS
**Artifact:** 41
**Operator Approved:** false
**Allows Implementation:** false
**Provenance:** SYNTHESIZED_CANON (derived from schema.ts analysis and replit.md documentation)

---

## Personal Data Categories

LyfeOS collects and stores some of the most sensitive personal data of any consumer application. The user_profile table alone has 99 columns spanning identity, beliefs, trauma, health, finances, and relationships.

### Category 1: Identity Data (MEDIUM sensitivity)
- Name, email, phone number, birthday, location, timezone
- Auth provider, Firebase UID
- Avatar, display name, title
- **Tables:** users, user_profile
- **Provenance:** MANUAL_INPUT

### Category 2: Psychological/Identity Profile (HIGH sensitivity)
- Primary/secondary/shadow archetypes
- Primary instincts, key drivers, shadow distortions
- Core/limiting/empowering beliefs
- Life roles, defining role
- Personality patterns, habits, urges
- Trait to reprogram, desired trait
- **Tables:** user_profile
- **Privacy risk:** Deeply personal psychological profiling data

### Category 3: Trauma/Shadow Patterns (CRITICAL sensitivity)
- Shadow patterns (pattern + lesson)
- Shadow distortions
- Coping practices, coping essential
- Historical context (timeline with age markers)
- Upbringing, cultural context, key experiences
- Relationship drains, conflict style
- Money memory (memory + impact)
- **Tables:** user_profile
- **Privacy risk:** Therapy-level personal data. Disclosure could cause serious personal harm.

### Category 4: Financial Data (HIGH sensitivity)
- Career/vocation
- Active ventures
- Financial position (income, expenses, savings, debt)
- Financial constraints
- Money confidence (score + habit shift)
- Money relationship
- Financial security (reflection + eliminate)
- Financial habits (current + to reprogram)
- Wealth tokens (current/max)
- Stripe customer/subscription IDs (legacy stubs)
- **Tables:** user_profile, user_stats, users
- **Privacy risk:** Financial position data. Potential regulatory implications.

### Category 5: Health Data (HIGH sensitivity)
- Physical metrics (height, weight, body type, features)
- Fitness/movement practices
- Nutrition/recovery practices
- Health/vitality (conditions, energy patterns, somatic awareness, longevity focus)
- Health baseline (sleep, exercise, nutrition scores)
- Injuries
- Daily mental/physical/emotional state (1-10)
- Wake/sleep times
- **Tables:** user_profile, user_daily_logs
- **Privacy risk:** Health data has regulatory implications (HIPAA in US, GDPR Article 9 in EU).

### Category 6: Behavioral Data (MEDIUM sensitivity)
- Daily logs (reflections, gratitude, goals, research)
- Quests/missions completed
- XP, level, streak history
- Widget states, activity events
- Smart reminder preferences
- **Tables:** user_daily_logs, quests, user_stats, user_activity_events, widget_states, smart_reminders
- **Privacy risk:** Behavioral pattern reconstruction possible.

### Category 7: Contact/Relationship Data (HIGH sensitivity)
- Full contact details (name, email, phone, address)
- Relationship type, trust level, how met
- Contact frequency, strengths
- Social media links
- **Tables:** contacts
- **Privacy risk:** Third-party personal data stored without their consent.

### Category 8: AI Interaction Data (HIGH sensitivity)
- All NOVA conversations and messages
- AI-generated character affirmation
- AI personality profile
- Dismissed knowledge items
- **Tables:** conversations, messages, ai_messages, user_profile
- **Privacy risk:** AI has access to all user data. Conversations may contain additional sensitive disclosures.

### Category 9: Location/Schedule Data (MEDIUM sensitivity)
- Calendar events with location
- Contact addresses and cities
- User timezone and location
- Quest locations
- Media item locations (GPS coordinates)
- **Tables:** calendar_events, contacts, user_profile, quests, media_items
- **Privacy risk:** Movement and schedule patterns.

---

## AI Data Access Assessment

### What NOVA Can Access (CODE_RESOLVED_CURRENT_TRUTH)
Per replit.md, NOVA has "full data ingestion capabilities":
- User profile (all 99 columns)
- User stats (all tokens, XP, level)
- Missions/quests (all history)
- Daily logs (all entries)
- Vision milestones
- Calendar events
- Conversation history
- Knowledge base (16 domains)
- Inline images from missions, goals, and logs

### AI Permission Model: NONE
- No tiered access control for AI
- No user consent granularity for data access
- No AI action approval workflow
- No AI action audit trail (beyond conversation history)
- NOVA can read everything the user has entered
- **Classification:** INFERRED_PROFESSIONAL_GAP

### AI Action Capabilities
NOVA has tool functions that can **write** data:
- createMission — create quests
- updateEnergyLog — modify energy data
- batch mission creation
- vision goal creation
- uncomplete missions
- Web search (external network access)
- **No approval required for any action**
- **Classification:** INFERRED_PROFESSIONAL_GAP

---

## Privacy and Compliance Implications

### GDPR (if serving EU users)
- **Article 9:** Health data, psychological profiling data = "special categories" requiring explicit consent
- **Right to be forgotten:** No data deletion mechanism for user data
- **Data portability:** No data export feature
- **Data processing records:** No documented processing purposes
- **DPO requirement:** If processing special categories at scale
- **Classification:** INFERRED_PROFESSIONAL_GAP

### CCPA (if serving California users)
- **Right to know:** What data is collected (no privacy policy confirmed)
- **Right to delete:** No deletion mechanism
- **Right to opt-out:** No opt-out mechanism for data sale (though likely no data sale)
- **Classification:** INFERRED_PROFESSIONAL_GAP

### HIPAA (if health data used for health purposes)
- LyfeOS stores health-adjacent data (conditions, medications implicitly via injuries)
- If marketed as health tool: potential HIPAA implications
- Currently: gamification context reduces HIPAA applicability
- **Classification:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

---

## Encryption Assessment

| Layer | Status | Provenance |
|-------|--------|------------|
| In transit (HTTPS) | Assumed via Replit deployment | INFERRED_PROFESSIONAL_GAP |
| At rest (database) | Neon provides encryption at rest | CODE_RESOLVED_CURRENT_TRUTH (Neon default) |
| Application-level encryption | NOT confirmed for sensitive fields | INFERRED_PROFESSIONAL_GAP |
| Password hashing | bcrypt v6.0.0 | CODE_RESOLVED_CURRENT_TRUTH |
| OAuth token encryption | UNKNOWN — schema says "encrypted" but implementation unverified | INFERRED_PROFESSIONAL_GAP |

### Fields That Should Be Encrypted at Application Level
- `integrations.access_token`
- `integrations.refresh_token`
- `users.two_factor_email_code`
- `users.two_factor_phone_code`
- `users.email_verification_token`
- `users.password_reset_token`
- Arguably: `user_profile.financial_position`, `user_profile.shadow_patterns`

---

## Recommendations

### P0 — Before Any Growth
1. Verify HTTPS is properly configured (Replit default, but confirm)
2. Verify OAuth token encryption in application code
3. Document what data NOVA can access

### P1 — Production Hardening
4. Implement data export/portability feature
5. Add privacy policy and terms of service
6. Implement AI permission tiers (what NOVA can read/write)
7. Add AI action audit trail beyond conversation history
8. Implement RLS (see artifact 39)

### P2 — Compliance
9. GDPR compliance review if serving EU users
10. Privacy classification for each data field
11. Data retention policy (how long is data kept)
12. Data deletion mechanism (right to be forgotten)
13. Third-party data handling policy (contacts table stores others' data)

### P3 — Advanced
14. Field-level encryption for financial and health data
15. AI context boundaries (limit what NOVA can access per conversation)
16. User consent granularity for data sharing with AI
17. Security audit / penetration testing
