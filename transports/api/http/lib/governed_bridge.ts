/**
 * Governed mutation bridge — TypeScript equivalent of transports/api/governed.py.
 *
 * Routes all TypeScript-side mutations through the GovernedExecutionSpine
 * via the organism bridge's governed_execute action.
 *
 * UMH transport layer. Instance-agnostic.
 */

import { callOrganism, type BridgeResult } from './python_bridge.js'

export interface GovernedMutationParams {
  mutation_name: string
  intent: string
  source?: string
  payload?: Record<string, unknown>
  metadata?: Record<string, unknown>
}

export interface GovernedResult {
  success: boolean
  output?: string
  envelope_id?: string
  status?: string
  awaiting_approval?: boolean
  rejected_reason?: string
}

export async function governedMutation(params: GovernedMutationParams): Promise<GovernedResult> {
  const result: BridgeResult = await callOrganism('organism.governed_execute', {
    mutation_name: params.mutation_name,
    intent: params.intent,
    source: params.source ?? 'cockpit',
    mutation_payload: params.payload ?? {},
    metadata: params.metadata ?? {},
  })

  if (!result.success) {
    return {
      success: false,
      output: result.error ?? 'governed_execute failed',
      status: 'failed',
    }
  }

  const data = result.data as Record<string, unknown> | undefined
  return {
    success: (data?.success as boolean) ?? false,
    output: (data?.output as string) ?? '',
    envelope_id: (data?.envelope_id as string) ?? '',
    status: (data?.status as string) ?? 'unknown',
    awaiting_approval: (data?.awaiting_approval as boolean) ?? false,
    rejected_reason: (data?.rejected_reason as string) ?? undefined,
  }
}
