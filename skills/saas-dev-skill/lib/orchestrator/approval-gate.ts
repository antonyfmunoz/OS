// lib/orchestrator/approval-gate.ts
// Approval gates are not interactive prompts in this codebase. The orchestrator
// runs inside Claude Code as a library, and Claude is responsible for pausing,
// relaying the approval message to the human, and only continuing once the
// human gives an explicit go-ahead.
//
// This module's job is purely to FORMAT the approval request and the
// pre/post-phase summary as plain strings. It has no I/O.
//
// Callers throw `ApprovalRequiredError` when they hit a gate; the wrapping
// skill catches it, surfaces the message to the user, and either retries the
// orchestrator with `approved: true` or aborts.

export class ApprovalRequiredError extends Error {
  constructor(
    message: string,
    public readonly phase: string,
    public readonly action: string,
  ) {
    super(message);
    this.name = "ApprovalRequiredError";
  }
}

export interface ApprovalRequest {
  phase: string;
  action: string;
  details: string;
}

/**
 * Builds the message Claude shows the user when an approval gate is hit.
 * Lead with WHAT will happen, then WHY it needs approval, then the DETAILS.
 */
export function formatApprovalRequest(
  phase: string,
  action: string,
  details: string,
): string {
  const lines = [
    `═══ APPROVAL REQUIRED ═══`,
    `Phase:  ${phase}`,
    `Action: ${action}`,
    ``,
    details,
    ``,
    `Reply with "approve" to proceed or "abort" to stop the pipeline.`,
  ];
  return lines.join("\n");
}

/**
 * Pre/post-phase summary used to give the user a quick read on where the
 * pipeline is. `completed` lists what's already done; `pending` lists what
 * still has to run.
 */
export function formatApprovalSummary(
  completed: string[],
  pending: string[],
): string {
  const lines = [`═══ PIPELINE STATUS ═══`];
  lines.push("Completed phases:");
  if (completed.length === 0) {
    lines.push("  (none)");
  } else {
    for (const c of completed) lines.push(`  ✓ ${c}`);
  }
  lines.push("");
  lines.push("Pending phases:");
  if (pending.length === 0) {
    lines.push("  (none — pipeline complete)");
  } else {
    for (const p of pending) lines.push(`  • ${p}`);
  }
  return lines.join("\n");
}
