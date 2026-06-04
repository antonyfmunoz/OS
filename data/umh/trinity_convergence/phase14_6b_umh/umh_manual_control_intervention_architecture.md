# UMH Manual Control and Intervention Architecture

Phase: 14.6B-UMH
Status: DRAFT

## Approval/Denial

- Operator approves or denies pending actions via cockpit UI or Discord
- Governance lifecycle: proposed -> approved/denied -> executed/cancelled
- Cockpit: approval buttons on pending items in governance panel
- Discord: reaction-based or command-based approval in Founders Office channel

## Pause/Resume/Abort

- Stub implementations exist for pause, resume, and abort controls
- Not yet wired to active execution interruption
- Future: real-time execution control through organism coordinator

## Governance Override

- `PATCH /governance` endpoint allows operator to override governance decisions
- Modifies risk classification, approval thresholds, or policy parameters
- Changes take effect on next governance evaluation cycle

## Organism Control

- `/organism/control` endpoint for direct organism state manipulation
- Operator can adjust workcell assignments, coordinator behavior, runtime graph
- Control actions are themselves governed (logged, auditable)

## Loop Management

- Create, start, stop, delete execution loops
- Loops are managed through organism coordinator
- Each loop has defined cadence, scope, and governance constraints
- `dry_run_only` constraint enforced on autonomous cadence loops

## Workflow Triggers

- Operator can manually trigger any registered workflow
- Bypasses scheduled cadence to execute on demand
- Trigger actions route through standard governance pipeline

## Agent Task Handoff

- Operator can take over any agent task manually
- Handoff transfers context and partial results to human operator
- Agent marks task as handed-off, stops autonomous work on it

## Rate Limiting

- All mutation endpoints are rate-limited
- Prevents accidental rapid-fire state changes
- Rate limits apply per-operator, per-endpoint

## Dev Bypass

- Private IP addresses (Tailscale network) bypass rate limits
- Dev bypass for local development and testing only
- Production governance still applies regardless of network origin
