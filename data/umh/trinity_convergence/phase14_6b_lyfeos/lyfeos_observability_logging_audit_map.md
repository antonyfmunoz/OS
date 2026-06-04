# LyfeOS Observability, Logging, and Audit Map

**Phase:** 14.6B-LyfeOS
**Artifact:** 42
**Operator Approved:** false
**Allows Implementation:** false
**Provenance:** INFERRED_PROFESSIONAL_GAP

---

## Current State Summary

LyfeOS has minimal observability infrastructure. No error tracking service, no structured logging, no performance monitoring, and no uptime monitoring are confirmed in the codebase. The only audit-adjacent capability is the `userActivityEvents` table which tracks behavioral events for gamification, not operational auditing.

---

## Error Tracking

| Item | Status | Risk |
|------|--------|------|
| Error tracking service (Sentry, Bugsnag, etc.) | NOT implemented | HIGH |
| Unhandled exception capture | NOT confirmed | HIGH |
| Error alerting/notification | NOT implemented | HIGH |
| Client-side error boundary | NOT confirmed | MEDIUM |
| API error response standardization | NOT confirmed | MEDIUM |

**Impact:** Production errors are silent. If NOVA fails, a route crashes, or a database query errors, there is no notification and no record. Debugging requires manually checking Replit logs (if they still exist).

---

## Logging

| Item | Status | Risk |
|------|--------|------|
| Structured logging (JSON format) | NOT implemented | MEDIUM |
| Log levels (debug/info/warn/error) | Basic console assumed | MEDIUM |
| Request/response logging | NOT confirmed | MEDIUM |
| Log persistence beyond Replit console | NOT confirmed | HIGH |
| Log aggregation service | NOT implemented | MEDIUM |

**Impact:** Logs are ephemeral console output. Replit may retain recent logs, but there is no guaranteed persistence. Historical debugging is impossible.

---

## Audit Events

| Item | Status | Details |
|------|--------|---------|
| `userActivityEvents` table | EXISTS | 5 columns: id, user_id, event_type, event_data, created_at |
| Auth event logging (login/logout/failed) | NOT confirmed as audit events | May exist in application code but not verified |
| Admin action audit trail | NOT applicable (no admin panel) | N/A |
| Data modification audit trail | NOT implemented | No record of who changed what and when |
| Integration sync audit trail | NOT confirmed | Google Calendar/Docs sync events not logged |

**Impact:** The `userActivityEvents` table is a gamification/analytics tool, not a security audit trail. There is no record of authentication events, data modifications, or integration sync outcomes.

---

## AI Action Logging

| Item | Status | Risk |
|------|--------|------|
| NOVA tool call logging | NOT explicit | HIGH |
| AI-generated content attribution | NOT implemented | MEDIUM |
| AI decision audit trail | NOT implemented | MEDIUM |
| AI error/fallback logging | NOT confirmed | HIGH |
| Token usage tracking | NOT confirmed | LOW |

**Impact:** NOVA can create missions, update energy logs, search the web, and modify user data. There is no explicit audit trail of which tool calls NOVA made, what data it accessed, or what actions it took. The only record is the conversation history in the `messages` table, which captures the chat flow but not the underlying tool invocations.

---

## Performance Monitoring

| Item | Status | Risk |
|------|--------|------|
| APM (Application Performance Monitoring) | NOT implemented | MEDIUM |
| Database query performance tracking | NOT implemented | LOW |
| API response time monitoring | NOT implemented | MEDIUM |
| AI response latency tracking | NOT implemented | LOW |
| Memory/CPU monitoring | Replit provides basic metrics | LOW |

---

## Uptime Monitoring

| Item | Status | Risk |
|------|--------|------|
| External uptime checker | NOT confirmed | MEDIUM |
| Health check endpoint | NOT confirmed | MEDIUM |
| Downtime alerting | NOT implemented | MEDIUM |
| SSL certificate monitoring | Managed by Replit | LOW |

---

## Required Observability Stack

### P0 — Before Growth

1. **Error tracking** — Sentry (free tier supports 5k events/month) or equivalent. Capture unhandled exceptions on both server and client. Alert via email or Discord webhook.
2. **Health check endpoint** — Simple `/health` route returning 200 with database connectivity check. Required for any external uptime monitoring.
3. **External uptime monitor** — UptimeRobot (free tier, 5-minute intervals) or equivalent hitting the health endpoint.

### P1 — Production Hardening

4. **Structured logging** — Replace console.log with a structured logger (winston or pino). JSON format. Log levels. Include request ID, user ID, and timestamp.
5. **Auth audit events** — Log login, logout, failed login, password reset, 2FA events to a dedicated audit table or structured log stream.
6. **AI action audit** — Log every NOVA tool call with: tool name, input parameters, output summary, user_id, conversation_id, timestamp. Separate from chat history.
7. **Integration sync audit** — Log Google Calendar/Docs sync start, success, failure, and item counts.

### P2 — Scale Readiness

8. **APM** — Response time percentiles, slow query detection, error rate dashboards.
9. **Log aggregation** — Ship structured logs to a searchable service (Datadog, Grafana Cloud, or self-hosted Loki).
10. **AI usage analytics** — Token consumption, model latency, fallback rates, conversation depth metrics.
11. **Performance budgets** — Alert when API p95 exceeds threshold or AI response time degrades.

---

## Operator Decision Required

**DEC-146B-OBS-001:** Observability implementation priority

Options:
1. **Immediate P0** — error tracking + health check + uptime monitor before any growth
2. **Bundled P1** — full observability stack alongside RLS and backup hardening
3. **Deferred** — accept blind operation risk until platform migration

**Recommendation:** Option 1. Error tracking alone (Sentry free tier) takes under an hour to integrate and eliminates the highest-risk blind spot. Health check + uptime monitor adds another 30 minutes. The cost of not knowing when production breaks is higher than the integration effort.
