/**
 * Random id generation that works in BOTH secure and insecure contexts.
 *
 * crypto.randomUUID() only exists in secure contexts (https / localhost).
 * The cockpit is also served over plain-http tailnet origins (local
 * verification runtimes, LAN dev), where calling it throws and silently
 * breaks any feature that mints ids (canvas windows could never spawn —
 * found by WP-P4-COCKPIT-BROWSER-VERIFY-001). Use this helper instead of
 * calling crypto.randomUUID() directly.
 */
export function randomId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  const rand = Math.random().toString(36).slice(2, 14)
  return `id-${Date.now().toString(36)}-${rand}`
}
