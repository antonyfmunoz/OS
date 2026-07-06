// Projection mirror card — P4S-30.
//
// Renders the read-surface truth for ONE projection (registration, runtime
// registration, connection status, seed info) and nothing else. MIRROR, NOT
// UX COLLAPSE: this card points AT the projection's own native app via
// public_url — it does not absorb the projection's UX (no journals, no
// feeds, no feature clusters). One parameterized component, used once per
// projection (LyfeOS, CreatorOS) from ProjectionMirrorsPanel.
import { ExternalLink } from 'lucide-react'
import type { ProjectionMirrorReadiness } from '../stores/projectionMirrorStore'

const CONNECTION_BADGE: Record<string, string> = {
  configured: 'wv-badge-ok',
  disconnected: 'wv-badge-danger',
}

interface ProjectionMirrorCardProps {
  displayName: string
  readiness: ProjectionMirrorReadiness | null
  loading: boolean
  error: string | null
}

export function ProjectionMirrorCard({ displayName, readiness, loading, error }: ProjectionMirrorCardProps) {
  const connectionStatus = readiness?.connection_status ?? 'disconnected'
  const publicUrl = readiness?.seed?.public_url ?? null
  const appName = readiness?.seed?.app_name ?? null

  return (
    <div className="wv-card p-4" data-testid={`projection-mirror-${readiness?.projection_id ?? 'unknown'}`}>
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-sm font-semibold">{displayName}</h3>
        <span className={`wv-badge ${CONNECTION_BADGE[connectionStatus] ?? 'wv-badge-warn'}`}>
          {connectionStatus}
        </span>
        {loading && <span className="text-[10px] text-text-tertiary">refreshing…</span>}
      </div>

      {error && (
        <p className="text-xs text-danger mb-2" data-testid="projection-mirror-error">{error}</p>
      )}

      {!readiness && !loading && !error && (
        <p className="text-xs text-text-tertiary">No readiness data available</p>
      )}

      {readiness && (
        <div className="space-y-2">
          <div className="flex flex-wrap gap-3 text-[11px]">
            <span className="wv-label">registered in seed</span>
            <span className={readiness.registered_in_seed ? 'text-ok' : 'text-danger'}>
              {readiness.registered_in_seed ? 'yes' : 'no'}
            </span>
          </div>
          <div className="flex flex-wrap gap-3 text-[11px]">
            <span className="wv-label">runtime registered</span>
            <span className={readiness.runtime_registered ? 'text-ok' : 'text-text-tertiary'}>
              {readiness.runtime_registered ? 'yes' : 'no'}
            </span>
          </div>
          {appName && (
            <div className="flex flex-wrap gap-3 text-[11px]">
              <span className="wv-label">app</span>
              <span className="text-text-secondary font-mono">{appName}</span>
            </div>
          )}
          {readiness.seed?.l4_workflow && (
            <div className="flex flex-wrap gap-3 text-[11px]">
              <span className="wv-label">l4 workflow</span>
              <span className="text-text-secondary font-mono">{readiness.seed.l4_workflow}</span>
            </div>
          )}

          {/* Native app is the product surface — the mirror points AT the
              projection, it does not absorb it. */}
          {publicUrl ? (
            <a
              href={publicUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 mt-2 px-3 py-2 text-xs font-mono uppercase rounded bg-cyan-glow text-cyan border border-border"
              data-testid="projection-mirror-open-native"
            >
              Open native app <ExternalLink size={12} />
            </a>
          ) : (
            <p className="text-[11px] text-text-tertiary mt-2">No public URL registered</p>
          )}
        </div>
      )}
    </div>
  )
}
