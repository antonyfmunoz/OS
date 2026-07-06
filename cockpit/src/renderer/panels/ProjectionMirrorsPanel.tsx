// Projection mirror panels — P4S-30.
//
// Cockpit read surface for the LyfeOS and CreatorOS projection activation
// endpoints (GET /api/umh/lyfeos/activation, GET /api/umh/creatoros/activation
// — rules/projection-read-surfaces.md conforming routes). MIRROR, NOT UX
// COLLAPSE: this panel renders read-surface truth only (registration,
// connection status, readiness, a link out to the native app) — it never
// reimplements projection-native UX (no journals, no feeds, no feature
// clusters). Modeled on the EOS approvals mirror (PR #186): same polling
// pattern (usePolling), same wv-* card styling, same per-projection store
// isolation.
import { usePolling } from '../hooks/usePolling'
import { ConnectionBanner } from '../components/ConnectionBanner'
import { ProjectionMirrorCard } from '../components/ProjectionMirrorCard'
import { useLyfeOSMirrorStore, useCreatorOSMirrorStore } from '../stores/projectionMirrorStore'
import { useRealtimeStore } from '../stores/realtimeStore'

export function ProjectionMirrorsPanel() {
  const realtimeStatus = useRealtimeStore((s) => s.status)

  const lyfeosReadiness = useLyfeOSMirrorStore((s) => s.readiness)
  const lyfeosLoading = useLyfeOSMirrorStore((s) => s.loading)
  const lyfeosError = useLyfeOSMirrorStore((s) => s.error)
  const fetchLyfeOS = useLyfeOSMirrorStore((s) => s.fetchReadiness)

  const creatorosReadiness = useCreatorOSMirrorStore((s) => s.readiness)
  const creatorosLoading = useCreatorOSMirrorStore((s) => s.loading)
  const creatorosError = useCreatorOSMirrorStore((s) => s.error)
  const fetchCreatorOS = useCreatorOSMirrorStore((s) => s.fetchReadiness)

  usePolling(
    () => { fetchLyfeOS(); fetchCreatorOS() },
    realtimeStatus === 'connected' ? 15000 : 5000,
  )

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <ConnectionBanner />

      <div className="flex items-center px-4 py-3 flex-shrink-0 border-b border-border">
        <h2 className="text-lg font-semibold">Projection Mirrors</h2>
        <span className="ml-2 text-[10px] text-text-tertiary">read-only — native app is the product surface</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <ProjectionMirrorCard
          displayName="LyfeOS"
          readiness={lyfeosReadiness}
          loading={lyfeosLoading}
          error={lyfeosError}
        />
        <ProjectionMirrorCard
          displayName="CreatorOS"
          readiness={creatorosReadiness}
          loading={creatorosLoading}
          error={creatorosError}
        />
      </div>
    </div>
  )
}
