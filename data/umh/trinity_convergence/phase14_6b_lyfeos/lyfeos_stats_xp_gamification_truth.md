# LyfeOS Stats, XP, and Gamification System Truth

**Phase:** 14.6B-LyfeOS
**Artifact:** 34
**Operator Approved:** false
**Allows Implementation:** false
**Provenance:** CODE_RESOLVED_CURRENT_TRUTH (verified from schema.ts, xp-calculations.test.ts, replit.md)

---

## Stats HUD — 5 Token Pairs + 3 Progression Metrics

All stat tokens use current/max integer pairs, default 100/100.

| Stat | DB Columns | Default | Color (PRD) | Provenance |
|------|-----------|---------|-------------|------------|
| Energy Points | energy_points_current / max | 100/100 | #FF9500 (orange) | COMPUTED_FROM_APP_BEHAVIOR |
| Health Points | health_points_current / max | 100/100 | green | USER_SELF_REPORT |
| Wealth Tokens | wealth_tokens_current / max | 100/100 | #FFD700 (gold) | MANUAL_INPUT |
| Time Tokens | time_tokens_current / max | 100/100 | cyan | COMPUTED_FROM_APP_BEHAVIOR |
| Attention Tokens | attention_tokens_current / max | 100/100 | blue gradient | COMPUTED_FROM_APP_BEHAVIOR |

Additional progression metrics:

| Metric | DB Column | Default | Provenance |
|--------|----------|---------|------------|
| XP | experience_current / experience_max | 0 / 1000 | COMPUTED_FROM_APP_BEHAVIOR |
| Level | level | 1 | COMPUTED_FROM_APP_BEHAVIOR |
| Streak | streak_days + last_active_date | 0 | COMPUTED_FROM_APP_BEHAVIOR |
| Efficiency | efficiency_score | 0 | COMPUTED_FROM_APP_BEHAVIOR |

---

## XP System — 3-Tier Exponential Growth

**Provenance:** CODE_RESOLVED_CURRENT_TRUTH — verified in xp-calculations.test.ts

### Formula (code-proven)

```
Tier 1 (Levels 1-10):   XP_required = 1000 * 1.0372^(level - 1)
Tier 2 (Levels 11-50):  XP_required = Level10_XP * 1.0572^(level - 10)
Tier 3 (Levels 51-100): XP_required = Level50_XP * 1.0872^(level - 50)
```

### Key Properties

- Level cap: **100**
- Level 1 XP threshold: **1000**
- Growth is exponential within each tier, with steeper multipliers at higher tiers
- Monotonically increasing: each level always requires more XP than the previous
- Total XP tracked separately in user_profile.total_xp

### XP Sources

| Source | Default XP | Notes |
|--------|-----------|-------|
| Quest completion | 10 (experience_reward column) | Configurable per quest |
| Vision goal completion | bonus_xp field | Variable, set per goal |
| Mission page completion | 5 (xp_value column) | Fixed per mission page |
| Reflection log | +5 (per PRD) | PRD claim, code verification needed |

### PRD Streak Bonuses (NOT code-verified)

The PRD describes streak multipliers. Whether these are implemented in application code requires verification.

| Streak Duration | Multiplier |
|----------------|------------|
| 7 days | 1.1x |
| 30 days | 1.25x |
| 90 days | 1.5x |
| 365 days | 2.0x |

**Provenance:** SOURCE_PRESERVED_TRUTH (from PRD) — implementation status unknown

---

## Difficulty Ranks

| Rank | Name | Notes |
|------|------|-------|
| S | Supreme | Highest difficulty |
| A | Advanced | High difficulty |
| B | Balanced | Medium-high |
| C | Casual | Medium-low |
| D | Default | Lowest, default rank |

Valid values enforced in UMH integration code: `frozenset({"S", "A", "B", "C", "D"})`

---

## Streak Tracking

- **Mechanism:** `streak_days` integer + `last_active_date` date comparison
- **Increment:** When user performs activity on consecutive calendar days
- **Reset:** Drops to 0 if a day is missed
- **Philosophy (per PRD):** "Focus on momentum, not perfection"

---

## Efficiency Score

- **Type:** Integer (0-100)
- **Storage:** `efficiency_score` in user_stats table
- **Description:** Rolling performance metric, likely 30-day window (per PRD "rolling 30-day")
- **Tiers (per PRD):** Developing, Capable, Proficient, Masterful, Legendary
- **Provenance:** PRD describes tiers; whether application code implements the tier labels requires verification

---

## Gamification Feedback

### Haptic Feedback (CODE_RESOLVED_CURRENT_TRUTH)
- Web Vibration API with configurable patterns
- Patterns: light tap, medium, heavy, success, level-up, notification
- Toggle: `haptic_feedback` boolean in user_profile (default: true)
- Module: `client/src/lib/haptics.ts`

### Sound Effects (CODE_RESOLVED_CURRENT_TRUTH)
- Web Audio API — all sounds synthesized programmatically (OscillatorNode + GainNode)
- No external audio files
- Events: mission completion, level-ups, XP gain, streaks, achievements, push notifications
- Toggle: `sound_effects` boolean in user_profile (default: true)
- Module: `client/src/lib/sounds.ts`

### Celebration Overlay (CODE_RESOLVED_CURRENT_TRUTH)
- Confetti via canvas-confetti library
- Level-up modal component
- Component: `client/src/components/CelebrationOverlay.tsx`
- Component: `client/src/components/dashboard/LevelUpModal.tsx`

---

## Archetype System

| Property | Value | Provenance |
|----------|-------|------------|
| Total archetypes | 6 | SOURCE_PRESERVED_TRUTH |
| Names | Warrior, Architect, Creator, Monarch, Oracle, Alchemist | SOURCE_PRESERVED_TRUTH |
| Calibration | 54-question quiz | SOURCE_PRESERVED_TRUTH |
| Scoring | direct (+), weighted (x1.5), reverse (R), scenario chips (+5) | SOURCE_PRESERVED_TRUTH |
| Outputs | Dominant, Secondary, Shadow archetypes | CODE_RESOLVED_CURRENT_TRUTH (schema fields) |
| Combo Profile | If top 2 within 3 points | SOURCE_PRESERVED_TRUTH |

Archetype data stored in user_profile: `archetype_primary`, `archetype_secondary`, `archetype_shadow`, `archetype_scores` (JSONB).

---

## PRD vs Code Contradictions

1. **Stats HUD count:** PRD says 8 stats, code has 5 token pairs + level/XP + streak + efficiency = 8 display items. Consistent.
2. **XP per level formula:** PRD describes flat tiers (100/250/500/1000 per level). Code uses exponential growth (1000 * multiplier^level). **Code is canonical** — test file proves the exponential formula.
3. **Anti-patterns:** PRD explicitly says NO badges, confetti, praise language. But code has confetti (canvas-confetti), celebration overlay, and level-up modal. **Code contradicts PRD anti-pattern guidance.** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED.
4. **Streak bonuses:** PRD describes multipliers (1.1x to 2.0x). Whether these are implemented in application code is unverified. Classification: OPEN_QUESTION_OPERATOR_DECISION_REQUIRED.

---

## Data Provenance Warning

Stats displayed in the LyfeOS HUD are NOT live-verified device data. They are a mix of user self-report and app behavior computation. This distinction matters for:
- UMH integration accuracy claims
- User trust calibration
- Future Apple Health / wearable integration planning

See artifact 33 (lyfeos_data_provenance_model.md) for full classification.
