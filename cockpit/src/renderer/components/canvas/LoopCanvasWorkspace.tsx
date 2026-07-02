import { useState, useCallback, useEffect, lazy, Suspense, type ReactNode } from 'react'
import {
  ArrowLeft, Play, Square, SkipForward, FlaskConical, Plus, Trash2, Pencil,
  RefreshCcw, Hammer, RotateCcw, Brain, Activity, ChevronUp, ChevronDown,
} from 'lucide-react'
import { BaseCanvas } from './BaseCanvas'
import { CanvasToolbar } from './CanvasToolbar'
import { useLoopCanvasStore, type PersistentLoopStatus } from '../../stores/loopCanvasStore'
import { clampZoom } from '../../utils/canvasCoords'
interface LoopCanvasWorkspaceProps {
  palette?: ReactNode
  paletteOpen?: boolean
  onTogglePalette?: () => void
}

const BuildLoopPanel = lazy(() => import('../../panels/BuildLoopPanel').then((m) => ({ default: m.BuildLoopPanel })))
const OperatingLoopPanel = lazy(() => import('../../panels/OperatingLoopPanel').then((m) => ({ default: m.OperatingLoopPanel })))
const OrganismLoopPanel = lazy(() => import('../../panels/OrganismLoopPanel').then((m) => ({ default: m.OrganismLoopPanel })))
const TickLoopPanel = lazy(() => import('../../panels/TickLoopPanel').then((m) => ({ default: m.TickLoopPanel })))

const STATE_COLOR: Record<PersistentLoopStatus['state'], string> = {
  running: '#22c55e', stopped: '#6b7280', error: '#ef4444', paused: '#eab308',
}

const LIFECYCLE_CARDS: Array<{ id: string; name: string; icon: typeof Hammer; description: string }> = [
  { id: 'build', name: 'Build Loop', icon: Hammer, description: 'Plan → execute → verify build cycles' },
  { id: 'operating', name: 'Operating Loop', icon: RotateCcw, description: 'Continuous operational cadence' },
  { id: 'organism', name: 'Organism Loop', icon: Brain, description: 'Whole-system coherence and health' },
  { id: 'tick', name: 'Tick Loop', icon: Activity, description: 'Heartbeat scheduling and pacing' },
]

function StatePill({ state }: { state: PersistentLoopStatus['state'] }) {
  return <span className="text-[10px] px-1.5 py-0.5 rounded capitalize" style={{ background: 'var(--color-surface-raised)', color: STATE_COLOR[state] }}>{state}</span>
}

function IconButton({ title, onClick, children, color }: { title: string; onClick: (e: React.MouseEvent) => void; children: ReactNode; color?: string }) {
  return <button title={title} onClick={onClick} className="flex items-center justify-center w-6 h-6 rounded" style={{ background: 'var(--color-surface-raised)', color: color ?? 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }}>{children}</button>
}

function CycleReport({ cycle, title }: { cycle: NonNullable<PersistentLoopStatus['last_cycle']>; title: string }) {
  return (
    <div className="p-4 rounded-lg" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
      <div className="text-[12px] font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>{title}</div>
      <div className="grid grid-cols-2 gap-y-1 text-[11px]" style={{ color: 'var(--color-text-secondary)' }}>
        <span>Started</span><span style={{ color: 'var(--color-text-tertiary)' }}>{cycle.started_at}</span>
        <span>Finished</span><span style={{ color: 'var(--color-text-tertiary)' }}>{cycle.finished_at}</span>
        <span>Actions taken</span><span style={{ color: 'var(--color-text-tertiary)' }}>{cycle.actions_taken}</span>
        <span>Errors</span><span style={{ color: cycle.errors > 0 ? '#ef4444' : 'var(--color-text-tertiary)' }}>{cycle.errors}</span>
      </div>
      {cycle.details.length > 0 && (
        <div className="mt-2 flex flex-col gap-1">
          {cycle.details.map((d, i) => <pre key={i} className="text-[10px] p-1.5 rounded overflow-auto" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-tertiary)' }}>{JSON.stringify(d, null, 2)}</pre>)}
        </div>
      )}
    </div>
  )
}

function StageCheckboxes({ availableStages, selected, onToggle }: { availableStages: Record<string, string>; selected: string[]; onToggle: (stage: string) => void }) {
  return (
    <div className="grid grid-cols-2 gap-1">
      {Object.entries(availableStages).map(([key, label]) => (
        <label key={key} className="flex items-center gap-1.5 text-[11px] cursor-pointer" style={{ color: 'var(--color-text-secondary)' }}>
          <input type="checkbox" checked={selected.includes(key)} onChange={() => onToggle(key)} />
          <span title={label}>{key}</span>
        </label>
      ))}
    </div>
  )
}

function LoopListOverlay() {
  const persistentLoops = useLoopCanvasStore((s) => s.persistentLoops)
  const availableStages = useLoopCanvasStore((s) => s.availableStages)
  const openLoop = useLoopCanvasStore((s) => s.openLoop)
  const startLoop = useLoopCanvasStore((s) => s.startLoop)
  const stopLoop = useLoopCanvasStore((s) => s.stopLoop)
  const runOnce = useLoopCanvasStore((s) => s.runOnce)
  const dryRun = useLoopCanvasStore((s) => s.dryRun)
  const createLoop = useLoopCanvasStore((s) => s.createLoop)

  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [domain, setDomain] = useState('')
  const [interval, setInterval] = useState(3600)
  const [description, setDescription] = useState('')
  const [stages, setStages] = useState<string[]>([])

  const toggleStage = useCallback((stage: string) => { setStages((prev) => (prev.includes(stage) ? prev.filter((s) => s !== stage) : [...prev, stage])) }, [])
  const resetForm = useCallback(() => { setName(''); setDomain(''); setInterval(3600); setDescription(''); setStages([]); setShowCreate(false) }, [])
  const handleCreate = useCallback(async () => {
    if (!name.trim()) return
    await createLoop({ name: name.trim(), domain: domain.trim(), interval_seconds: interval, stages, description: description.trim() })
    resetForm()
  }, [name, domain, interval, stages, description, createLoop, resetForm])

  const loops = Object.values(persistentLoops)

  return (
    <div className="absolute inset-0 flex items-start justify-center z-[5] pointer-events-none overflow-auto pt-12 pb-20 px-8">
      <div className="pointer-events-auto w-full max-w-[900px] flex flex-col gap-8">
        <section>
          <div className="flex items-center gap-3 mb-4">
            <h2 className="text-[14px] font-medium" style={{ color: 'var(--color-text-primary)' }}>Persistent Loops</h2>
            <div className="flex-1" />
            <button onClick={() => setShowCreate((v) => !v)} className="flex items-center gap-1 px-2 py-1 rounded text-[12px]" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }}><Plus size={12} /> New Loop</button>
          </div>
          {showCreate && (
            <div className="p-4 rounded-lg mb-4 flex flex-col gap-2" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Loop name" className="px-2 py-1 text-[12px] rounded" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)', outline: 'none' }} />
              <input type="text" value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="Domain" className="px-2 py-1 text-[12px] rounded" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)', outline: 'none' }} />
              <label className="text-[11px]" style={{ color: 'var(--color-text-secondary)' }}>Interval (seconds)</label>
              <input type="number" value={interval} onChange={(e) => setInterval(Number(e.target.value))} className="px-2 py-1 text-[12px] rounded" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)', outline: 'none' }} />
              <label className="text-[11px]" style={{ color: 'var(--color-text-secondary)' }}>Stages</label>
              <StageCheckboxes availableStages={availableStages} selected={stages} onToggle={toggleStage} />
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description" rows={2} className="px-2 py-1 text-[12px] rounded resize-none" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)', outline: 'none' }} />
              <div className="flex gap-2">
                <button onClick={handleCreate} className="flex items-center gap-1 px-2 py-1 rounded text-[12px]" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)' }}><Plus size={12} /> Create</button>
                <button onClick={resetForm} className="px-2 py-1 rounded text-[12px]" style={{ background: 'var(--color-surface)', color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }}>Cancel</button>
              </div>
            </div>
          )}
          {loops.length === 0 ? (
            <div className="flex flex-col items-center gap-3 mt-8" style={{ color: 'var(--color-text-tertiary)' }}><RefreshCcw size={32} /><span className="text-[13px]">No persistent loops</span><span className="text-[11px]">Create one to get started</span></div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {loops.map((loop) => {
                const isRunning = loop.state === 'running'
                return (
                  <div key={loop.name} className="p-3 rounded-lg cursor-pointer" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }} onClick={() => openLoop(loop.name, 'persistent')}>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full" style={{ background: STATE_COLOR[loop.state] }} />
                      <span className="text-[13px] font-medium truncate" style={{ color: 'var(--color-text-primary)' }}>{loop.name}</span>
                      {loop.domain && <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-tertiary)' }}>{loop.domain}</span>}
                    </div>
                    <div className="text-[10px] mt-1.5" style={{ color: 'var(--color-text-tertiary)' }}>{loop.interval_seconds}s interval · {loop.cycle_count} cycles</div>
                    {loop.error_count > 0 && <div className="text-[10px] mt-1" style={{ color: '#ef4444' }}>{loop.error_count} errors</div>}
                    <div className="flex gap-1 mt-2" onClick={(e) => e.stopPropagation()}>
                      {!isRunning && <IconButton title="Start" color="#22c55e" onClick={() => startLoop(loop.name)}><Play size={12} /></IconButton>}
                      {isRunning && <IconButton title="Stop" color="#ef4444" onClick={() => stopLoop(loop.name)}><Square size={12} /></IconButton>}
                      <IconButton title="Run once" onClick={() => runOnce(loop.name)}><SkipForward size={12} /></IconButton>
                      <IconButton title="Dry run" onClick={() => dryRun(loop.name)}><FlaskConical size={12} /></IconButton>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </section>
        <section>
          <h2 className="text-[14px] font-medium mb-4" style={{ color: 'var(--color-text-primary)' }}>Lifecycle Loops</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {LIFECYCLE_CARDS.map((card) => { const Icon = card.icon; return (
              <div key={card.id} className="p-3 rounded-lg cursor-pointer" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }} onClick={() => openLoop(card.id, 'lifecycle')}>
                <div className="flex items-center gap-2"><Icon size={16} style={{ color: 'var(--color-text-secondary)' }} /><span className="text-[13px] font-medium" style={{ color: 'var(--color-text-primary)' }}>{card.name}</span></div>
                <div className="text-[11px] mt-1.5" style={{ color: 'var(--color-text-tertiary)' }}>{card.description}</div>
              </div>
            )})}
          </div>
        </section>
      </div>
    </div>
  )
}

function LoopList({ palette, paletteOpen = false, onTogglePalette }: LoopCanvasWorkspaceProps) {
  const panX = useLoopCanvasStore((s) => s.panX)
  const panY = useLoopCanvasStore((s) => s.panY)
  const zoom = useLoopCanvasStore((s) => s.zoom)
  const setPan = useLoopCanvasStore((s) => s.setPan)
  const setZoom = useLoopCanvasStore((s) => s.setZoom)
  const handleZoomIn = useCallback(() => setZoom(clampZoom(zoom + 0.1)), [zoom, setZoom])
  const handleZoomOut = useCallback(() => setZoom(clampZoom(zoom - 0.1)), [zoom, setZoom])
  const handleZoomReset = useCallback(() => { setZoom(1); setPan(0, 0) }, [setZoom, setPan])

  return (
    <>
      <BaseCanvas panX={panX} panY={panY} zoom={zoom} setPan={setPan} setZoom={setZoom} palette={palette}
        toolbar={<CanvasToolbar zoom={zoom} onZoomIn={handleZoomIn} onZoomOut={handleZoomOut} onZoomReset={handleZoomReset} onTogglePalette={onTogglePalette ?? (() => {})} paletteOpen={paletteOpen} />}
      >{null}</BaseCanvas>
      <LoopListOverlay />
    </>
  )
}

function PersistentLoopDetail({ loop }: { loop: PersistentLoopStatus }) {
  const availableStages = useLoopCanvasStore((s) => s.availableStages)
  const lastDryRun = useLoopCanvasStore((s) => s.lastDryRun)
  const startLoop = useLoopCanvasStore((s) => s.startLoop)
  const stopLoop = useLoopCanvasStore((s) => s.stopLoop)
  const runOnce = useLoopCanvasStore((s) => s.runOnce)
  const dryRun = useLoopCanvasStore((s) => s.dryRun)
  const deleteLoop = useLoopCanvasStore((s) => s.deleteLoop)
  const updateLoop = useLoopCanvasStore((s) => s.updateLoop)
  const closeLoop = useLoopCanvasStore((s) => s.closeLoop)

  const [editing, setEditing] = useState(false)
  const [editInterval, setEditInterval] = useState(loop.interval_seconds)
  const [editDescription, setEditDescription] = useState(loop.description)
  const [editDomain, setEditDomain] = useState(loop.domain)
  const [editStages, setEditStages] = useState<string[]>(loop.stages)
  const isRunning = loop.state === 'running'

  const toggleStage = useCallback((stage: string) => { setEditStages((prev) => (prev.includes(stage) ? prev.filter((s) => s !== stage) : [...prev, stage])) }, [])
  const moveStage = useCallback((index: number, dir: -1 | 1) => {
    setEditStages((prev) => { const next = [...prev]; const target = index + dir; if (target < 0 || target >= next.length) return prev; [next[index], next[target]] = [next[target], next[index]]; return next })
  }, [])
  const handleSave = useCallback(async () => { await updateLoop(loop.name, { interval_seconds: editInterval, description: editDescription, domain: editDomain, stages: editStages }); setEditing(false) }, [loop.name, editInterval, editDescription, editDomain, editStages, updateLoop])
  const handleDelete = useCallback(async () => { if (!confirm(`Delete loop "${loop.name}"?`)) return; await deleteLoop(loop.name); closeLoop() }, [loop.name, deleteLoop, closeLoop])

  return (
    <div className="flex flex-col gap-4 max-w-[900px] mx-auto w-full p-6 overflow-auto">
      <div className="p-4 rounded-lg" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
        <div className="flex items-center gap-2 mb-3">
          <StatePill state={loop.state} />
          <span className="text-[14px] font-medium" style={{ color: 'var(--color-text-primary)' }}>{loop.name}</span>
          <div className="flex-1" />
          <button onClick={() => setEditing((v) => !v)} className="flex items-center justify-center w-6 h-6 rounded" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }} title="Edit"><Pencil size={12} /></button>
        </div>
        {editing ? (
          <div className="flex flex-col gap-2">
            <label className="text-[11px]" style={{ color: 'var(--color-text-secondary)' }}>Domain</label>
            <input type="text" value={editDomain} onChange={(e) => setEditDomain(e.target.value)} className="px-2 py-1 text-[12px] rounded" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)', outline: 'none' }} />
            <label className="text-[11px]" style={{ color: 'var(--color-text-secondary)' }}>Interval (seconds)</label>
            <input type="number" value={editInterval} onChange={(e) => setEditInterval(Number(e.target.value))} className="px-2 py-1 text-[12px] rounded" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)', outline: 'none' }} />
            <label className="text-[11px]" style={{ color: 'var(--color-text-secondary)' }}>Description</label>
            <textarea value={editDescription} onChange={(e) => setEditDescription(e.target.value)} rows={2} className="px-2 py-1 text-[12px] rounded resize-none" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)', outline: 'none' }} />
            <label className="text-[11px]" style={{ color: 'var(--color-text-secondary)' }}>Add / remove stages</label>
            <StageCheckboxes availableStages={availableStages} selected={editStages} onToggle={toggleStage} />
            <label className="text-[11px]" style={{ color: 'var(--color-text-secondary)' }}>Order</label>
            <div className="flex flex-col gap-1">
              {editStages.map((stage, i) => (
                <div key={stage} className="flex items-center gap-2 px-2 py-1 rounded text-[11px]" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-secondary)' }}>
                  <span className="flex-1">{i + 1}. {stage}</span>
                  <button onClick={() => moveStage(i, -1)} title="Move up" style={{ color: 'var(--color-text-tertiary)' }}><ChevronUp size={12} /></button>
                  <button onClick={() => moveStage(i, 1)} title="Move down" style={{ color: 'var(--color-text-tertiary)' }}><ChevronDown size={12} /></button>
                </div>
              ))}
            </div>
            <button onClick={handleSave} className="self-start px-2 py-1 rounded text-[12px] mt-1" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-primary)', border: '1px solid var(--color-border)' }}>Save</button>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-y-1 text-[11px]" style={{ color: 'var(--color-text-secondary)' }}>
            <span>Domain</span><span style={{ color: 'var(--color-text-tertiary)' }}>{loop.domain || '—'}</span>
            <span>Interval</span><span style={{ color: 'var(--color-text-tertiary)' }}>{loop.interval_seconds}s</span>
            <span>Cycles</span><span style={{ color: 'var(--color-text-tertiary)' }}>{loop.cycle_count}</span>
            <span>Errors</span><span style={{ color: loop.error_count > 0 ? '#ef4444' : 'var(--color-text-tertiary)' }}>{loop.error_count}</span>
            <span>Started</span><span style={{ color: 'var(--color-text-tertiary)' }}>{loop.started_at ?? '—'}</span>
            <span className="col-span-2 mt-1" style={{ color: 'var(--color-text-secondary)' }}>Stages</span>
            <ol className="col-span-2 list-decimal list-inside" style={{ color: 'var(--color-text-tertiary)' }}>{loop.stages.map((s) => <li key={s}>{s}</li>)}</ol>
            {loop.description && <span className="col-span-2 mt-1" style={{ color: 'var(--color-text-tertiary)' }}>{loop.description}</span>}
          </div>
        )}
      </div>
      <div className="flex gap-2 flex-wrap">
        {!isRunning ? <button onClick={() => startLoop(loop.name)} className="flex items-center gap-1 px-3 py-1.5 rounded text-[12px]" style={{ background: 'var(--color-surface-raised)', color: '#22c55e', border: '1px solid var(--color-border)' }}><Play size={12} /> Start</button>
         : <button onClick={() => stopLoop(loop.name)} className="flex items-center gap-1 px-3 py-1.5 rounded text-[12px]" style={{ background: 'var(--color-surface-raised)', color: '#ef4444', border: '1px solid var(--color-border)' }}><Square size={12} /> Stop</button>}
        <button onClick={() => runOnce(loop.name)} className="flex items-center gap-1 px-3 py-1.5 rounded text-[12px]" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }}><SkipForward size={12} /> Run Once</button>
        <button onClick={() => dryRun(loop.name)} className="flex items-center gap-1 px-3 py-1.5 rounded text-[12px]" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-secondary)', border: '1px solid var(--color-border)' }}><FlaskConical size={12} /> Dry Run</button>
        <button onClick={handleDelete} className="flex items-center gap-1 px-3 py-1.5 rounded text-[12px]" style={{ background: 'var(--color-surface-raised)', color: '#ef4444', border: '1px solid var(--color-border)' }}><Trash2 size={12} /> Delete</button>
      </div>
      {loop.last_cycle && <CycleReport cycle={loop.last_cycle} title="Last Cycle Report" />}
      {lastDryRun && (loop.name === lastDryRun.loop_name || lastDryRun.loop_name === undefined) && (
        <div className="p-4 rounded-lg" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
          <div className="text-[12px] font-medium mb-2" style={{ color: 'var(--color-text-primary)' }}>Dry Run Results</div>
          <pre className="text-[10px] p-1.5 rounded overflow-auto" style={{ background: 'var(--color-surface-raised)', color: 'var(--color-text-tertiary)' }}>{JSON.stringify(lastDryRun, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}

function LifecycleLoopDetail({ id }: { id: string }) {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-full text-[12px]" style={{ color: 'var(--color-text-tertiary)' }}>Loading…</div>}>
      {id === 'build' && <BuildLoopPanel />}
      {id === 'operating' && <OperatingLoopPanel />}
      {id === 'organism' && <OrganismLoopPanel />}
      {id === 'tick' && <TickLoopPanel />}
    </Suspense>
  )
}

function LoopDetailView() {
  const activeLoopId = useLoopCanvasStore((s) => s.activeLoopId)
  const activeLoopType = useLoopCanvasStore((s) => s.activeLoopType)
  const persistentLoops = useLoopCanvasStore((s) => s.persistentLoops)
  const closeLoop = useLoopCanvasStore((s) => s.closeLoop)
  const loop = activeLoopId ? persistentLoops[activeLoopId] : undefined

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 px-3 h-8 shrink-0" style={{ borderBottom: '1px solid var(--color-border)', background: 'var(--color-surface)' }}>
        <button onClick={closeLoop} className="flex items-center gap-1 text-[11px]" style={{ color: 'var(--color-text-secondary)' }}><ArrowLeft size={12} /> All Loops</button>
        <span className="text-[11px]" style={{ color: 'var(--color-text-tertiary)' }}>{activeLoopId}</span>
      </div>
      <div className="flex-1 overflow-auto">
        {activeLoopType === 'persistent' ? (loop ? <PersistentLoopDetail loop={loop} /> : <div className="flex items-center justify-center h-full text-[12px]" style={{ color: 'var(--color-text-tertiary)' }}>Loop not found</div>) : (activeLoopId && <LifecycleLoopDetail id={activeLoopId} />)}
      </div>
    </div>
  )
}

export function LoopCanvasWorkspace(props: LoopCanvasWorkspaceProps) {
  const activeLoopId = useLoopCanvasStore((s) => s.activeLoopId)
  useEffect(() => { useLoopCanvasStore.getState().fetchLoops(); useLoopCanvasStore.getState().fetchStages() }, [])
  if (activeLoopId) return <LoopDetailView />
  return <LoopList {...props} />
}
