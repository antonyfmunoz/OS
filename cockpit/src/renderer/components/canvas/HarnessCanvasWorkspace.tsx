import { useEffect, useState, useCallback, type ReactNode } from 'react'
import { ArrowLeft, Cpu, Server, Database, Monitor, Terminal, Globe, Wifi, WifiOff, ChevronRight, ChevronDown } from 'lucide-react'
import { BaseCanvas } from './BaseCanvas'
import { CanvasToolbar } from './CanvasToolbar'
import { useHarnessCanvasStore, type RuntimeNode } from '../../stores/harnessCanvasStore'
import { clampZoom } from '../../utils/canvasCoords'
interface HarnessCanvasWorkspaceProps {
  palette?: ReactNode
  paletteOpen?: boolean
  onTogglePalette?: () => void
}

const HARNESS_NAMES: Record<string, string> = {
  cc_sdk: 'Claude Code',
  codex: 'Codex',
  hermes: 'Hermes',
  opencode: 'OpenCode',
}

const CLASS_LABELS: Record<string, { label: string; icon: typeof Server }> = {
  AI_API: { label: 'AI APIs', icon: Globe },
  LOCAL_MODEL: { label: 'Local Models', icon: Database },
  CONTAINER: { label: 'Containers', icon: Server },
  PROCESS: { label: 'Processes', icon: Terminal },
  REMOTE_NODE: { label: 'Remote Nodes', icon: Monitor },
}

function harnessName(runtimeId: string): string {
  return HARNESS_NAMES[runtimeId] ?? runtimeId
}

function formatCost(cost: RuntimeNode['cost']): string {
  if (cost?.is_subscription) return 'Subscription'
  const parts: string[] = []
  if (cost?.cost_per_1k_input != null) parts.push(`$${cost.cost_per_1k_input}/1k in`)
  if (cost?.cost_per_1k_output != null) parts.push(`$${cost.cost_per_1k_output}/1k out`)
  return parts.length > 0 ? parts.join(' · ') : 'Free'
}

function AvailabilityDot({ available }: { available: boolean }) {
  return available ? (
    <Wifi size={12} style={{ color: '#22c55e' }} />
  ) : (
    <WifiOff size={12} style={{ color: '#ef4444' }} />
  )
}

function HarnessListOverlay() {
  const runtimes = useHarnessCanvasStore((s) => s.runtimes)
  const loading = useHarnessCanvasStore((s) => s.loading)
  const openHarness = useHarnessCanvasStore((s) => s.openHarness)

  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const aiHarnesses = runtimes.filter((r) => r.runtime_class === 'AI_CLI')
  const infraRuntimes = runtimes.filter((r) => r.runtime_class !== 'AI_CLI')

  const groups: Record<string, RuntimeNode[]> = {}
  for (const rt of infraRuntimes) {
    ;(groups[rt.runtime_class] ??= []).push(rt)
  }

  const toggleGroup = useCallback((cls: string) => {
    setExpanded((prev) => ({ ...prev, [cls]: !prev[cls] }))
  }, [])

  return (
    <div className="absolute inset-0 flex items-start justify-center z-[5] pointer-events-none overflow-auto pt-12 pb-20 px-8">
      <div className="pointer-events-auto w-full max-w-[900px]">
        {runtimes.length === 0 && !loading ? (
          <div className="flex flex-col items-center gap-3 mt-16" style={{ color: 'var(--color-text-tertiary)' }}>
            <Cpu size={32} />
            <span className="text-[13px]">No runtimes detected</span>
            <span className="text-[11px]">Connect the organism to discover runtimes</span>
          </div>
        ) : (
          <>
            {aiHarnesses.length > 0 && (
              <div className="mb-6">
                <div className="flex items-center gap-3 mb-4">
                  <h2 className="text-[14px] font-medium" style={{ color: 'var(--color-text-primary)' }}>AI Harnesses</h2>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {aiHarnesses.map((rt) => (
                    <div
                      key={rt.runtime_id}
                      className="p-3 rounded-lg cursor-pointer"
                      style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
                      onClick={() => openHarness(rt.runtime_id)}
                    >
                      <div className="flex items-center gap-2">
                        <AvailabilityDot available={rt.available} />
                        <span className="text-[13px] font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>{harnessName(rt.runtime_id)}</span>
                      </div>
                      <div className="text-[10px] mt-0.5" style={{ color: 'var(--color-text-tertiary)' }}>{rt.runtime_id}</div>
                      {rt.capabilities.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {rt.capabilities.map((cap) => (
                            <span key={cap} className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-tertiary)' }}>
                              {cap}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="text-[10px] mt-2" style={{ color: 'var(--color-text-tertiary)' }}>{formatCost(rt.cost)}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {infraRuntimes.length > 0 && (
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <h2 className="text-[14px] font-medium" style={{ color: 'var(--color-text-primary)' }}>Infrastructure Runtimes</h2>
                </div>
                <div className="flex flex-col gap-2">
                  {Object.entries(groups).map(([cls, items]) => {
                    const meta = CLASS_LABELS[cls] ?? { label: cls, icon: Server }
                    const Icon = meta.icon
                    const isOpen = expanded[cls] ?? false
                    const availableCount = items.filter((i) => i.available).length
                    return (
                      <div key={cls} className="rounded-lg overflow-hidden" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
                        <div className="flex items-center gap-2 px-3 py-2 cursor-pointer" onClick={() => toggleGroup(cls)}>
                          {isOpen ? <ChevronDown size={12} style={{ color: 'var(--color-text-tertiary)' }} /> : <ChevronRight size={12} style={{ color: 'var(--color-text-tertiary)' }} />}
                          <Icon size={13} style={{ color: 'var(--color-text-secondary)' }} />
                          <span className="text-[12px] font-medium" style={{ color: 'var(--color-text-primary)' }}>{meta.label}</span>
                          <div className="flex-1" />
                          <span className="text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>{availableCount}/{items.length} available</span>
                        </div>
                        {isOpen && (
                          <div style={{ borderTop: '1px solid var(--color-border)' }}>
                            {items.map((rt) => (
                              <div key={rt.runtime_id} className="flex items-center gap-2 px-3 py-2 cursor-pointer" onClick={() => openHarness(rt.runtime_id)}>
                                <AvailabilityDot available={rt.available} />
                                <span className="text-[12px] truncate" style={{ color: 'var(--color-text-primary)' }}>{rt.runtime_id}</span>
                                <div className="flex-1" />
                                <span className="text-[10px]" style={{ color: 'var(--color-text-tertiary)' }}>{rt.capabilities.length} caps</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function HarnessList({ palette, paletteOpen = false, onTogglePalette }: HarnessCanvasWorkspaceProps) {
  const panX = useHarnessCanvasStore((s) => s.panX)
  const panY = useHarnessCanvasStore((s) => s.panY)
  const zoom = useHarnessCanvasStore((s) => s.zoom)
  const setPan = useHarnessCanvasStore((s) => s.setPan)
  const setZoom = useHarnessCanvasStore((s) => s.setZoom)

  const handleZoomIn = useCallback(() => setZoom(clampZoom(zoom + 0.1)), [zoom, setZoom])
  const handleZoomOut = useCallback(() => setZoom(clampZoom(zoom - 0.1)), [zoom, setZoom])
  const handleZoomReset = useCallback(() => { setZoom(1); setPan(0, 0) }, [setZoom, setPan])

  return (
    <>
      <BaseCanvas panX={panX} panY={panY} zoom={zoom} setPan={setPan} setZoom={setZoom} palette={palette}
        toolbar={<CanvasToolbar zoom={zoom} onZoomIn={handleZoomIn} onZoomOut={handleZoomOut} onZoomReset={handleZoomReset} onTogglePalette={onTogglePalette ?? (() => {})} paletteOpen={paletteOpen} />}
      >{null}</BaseCanvas>
      <HarnessListOverlay />
    </>
  )
}

function HarnessDetailView() {
  const runtimes = useHarnessCanvasStore((s) => s.runtimes)
  const activeHarnessId = useHarnessCanvasStore((s) => s.activeHarnessId)
  const closeHarness = useHarnessCanvasStore((s) => s.closeHarness)
  const runtime = runtimes.find((r) => r.runtime_id === activeHarnessId)

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 px-3 h-8 shrink-0" style={{ borderBottom: '1px solid var(--color-border)', background: 'var(--color-surface)' }}>
        <button onClick={closeHarness} className="flex items-center gap-1 text-[11px]" style={{ color: 'var(--color-text-secondary)' }}><ArrowLeft size={12} /> All Harnesses</button>
        {runtime && <span className="text-[11px] font-medium" style={{ color: 'var(--color-text-primary)' }}>{harnessName(runtime.runtime_id)}</span>}
      </div>
      <div className="flex-1 overflow-auto p-6">
        {!runtime ? (
          <div className="flex flex-col items-center gap-2 mt-16" style={{ color: 'var(--color-text-tertiary)' }}><Cpu size={28} /><span className="text-[12px]">Runtime not found</span></div>
        ) : (
          <div className="max-w-[700px] mx-auto p-4 rounded-lg" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
            <div className="flex items-center gap-2 mb-4">
              <AvailabilityDot available={runtime.available} />
              <span className="text-[15px] font-medium" style={{ color: 'var(--color-text-primary)' }}>{harnessName(runtime.runtime_id)}</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
              <DetailField label="Runtime ID" value={runtime.runtime_id} />
              <DetailField label="Class" value={runtime.runtime_class} />
              <DetailField label="Available" value={runtime.available ? 'Yes' : 'No'} />
              <DetailField label="Cost" value={formatCost(runtime.cost)} />
              {typeof runtime.metadata.device_id === 'string' && <DetailField label="Device" value={runtime.metadata.device_id} />}
            </div>
            {runtime.capabilities.length > 0 && (
              <div className="mb-4">
                <div className="text-[10px] uppercase tracking-wide mb-2" style={{ color: 'var(--color-text-tertiary)' }}>Capabilities</div>
                <div className="flex flex-wrap gap-1">
                  {runtime.capabilities.map((cap) => (
                    <span key={cap} className="text-[11px] px-2 py-0.5 rounded" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-secondary)' }}>{cap}</span>
                  ))}
                </div>
              </div>
            )}
            {Object.entries(runtime.metadata).filter(([, v]) => v != null && v !== '').length > 0 && (
              <div>
                <div className="text-[10px] uppercase tracking-wide mb-2" style={{ color: 'var(--color-text-tertiary)' }}>Metadata</div>
                <div className="flex flex-col gap-1">
                  {Object.entries(runtime.metadata).filter(([, v]) => v != null && v !== '').map(([k, v]) => (
                    <div key={k} className="flex items-start gap-2 text-[11px]">
                      <span style={{ color: 'var(--color-text-tertiary)', minWidth: 120 }}>{k}</span>
                      <span style={{ color: 'var(--color-text-secondary)' }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide mb-0.5" style={{ color: 'var(--color-text-tertiary)' }}>{label}</div>
      <div className="text-[12px]" style={{ color: 'var(--color-text-primary)' }}>{value}</div>
    </div>
  )
}

export function HarnessCanvasWorkspace(props: HarnessCanvasWorkspaceProps) {
  const activeHarnessId = useHarnessCanvasStore((s) => s.activeHarnessId)
  useEffect(() => { useHarnessCanvasStore.getState().fetchRuntimes() }, [])
  if (activeHarnessId) return <HarnessDetailView />
  return <HarnessList {...props} />
}
