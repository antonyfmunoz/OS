# EOS Operating Dashboard — Highest-Leverage Implementation Plan

## What DEX Understood
Operator intent: Build the first EOS operating dashboard for Empyrean Studios.
Classification: create_work (high confidence)
Domain: product
Entities: EOS, Empyrean Studios, dashboard

## Current Known Context
- UMH substrate is production-ready through Phase 13.4
- Cockpit exists with 20+ panels (Electron-based)
- SaaS layer has TypeScript/React foundation in saas/
- EOS projection has venture, client, transaction, offer, agent, skill, analytics schemas
- 87+ API routes across 5 route groups
- Runtime surface with shell and Claude Code adapters

## Recommended Implementation Path
1. **Phase 14.0 — EOS Dashboard Kernel**: Wire existing saas/ routes into a dashboard view
2. **Phase 14.1 — Venture Operating View**: Real-time portfolio, venture, and client data
3. **Phase 14.2 — Agent Performance View**: Agent utilization, task throughput, quality scores
4. **Phase 14.3 — Financial View**: Revenue, expenses, profit tracking per venture

## Proposed Work Packet Structure
- WP-1: EOS Dashboard Layout (React component, route, navigation)
- WP-2: Portfolio Summary Widget (venture count, active clients, revenue)
- WP-3: Agent Performance Widget (active agents, tasks completed, quality)
- WP-4: Financial Summary Widget (revenue, expenses, P&L)
- WP-5: Activity Feed Widget (recent actions, approvals, completions)

## Needed Workcells
- Frontend Developer Workcell (React/TypeScript)
- API Integration Workcell (bridge handlers, route wiring)
- Data Aggregation Workcell (query composition, caching)

## Dependencies
- saas/ schema (ventures, clients, transactions, offers)
- transports/api/http/ route infrastructure
- cockpit component system (or saas/ standalone)
- Auth: Clerk operator authentication

## Validation Plan
- Each widget renders with real data from API
- Dashboard loads in < 2 seconds
- No hardcoded data
- Responsive layout
- Operator auth required

## Human Decisions Required
1. Dashboard location: cockpit panel vs saas/ standalone page
2. Priority widgets for MVP
3. Financial data source (manual entry vs API integration)
4. Refresh frequency (polling vs websocket)

## Approval Gates
- Design review before implementation
- API route review before deployment
- Security review for financial data access

## Risks
- saas/ schema may need migrations for dashboard-specific queries
- Clerk auth integration complexity
- Financial data sensitivity requires careful access control

## Next Highest-Leverage Action
Start with WP-1 (Dashboard Layout) + WP-2 (Portfolio Summary) as the MVP.
These prove the full stack works end-to-end with real data.
