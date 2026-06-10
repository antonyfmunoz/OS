import { useState, useCallback } from 'react'
import { clsx } from 'clsx'
import {
  Eye, EyeOff, Tag, Bell, BellOff,
  UserCheck, UserX, Crosshair, Search, Trash2,
} from 'lucide-react'
import { useVisionStore } from '../stores/visionStore'
import { getVisionClient } from '../hooks/useVisionConnection'

const STATUS_COLORS: Record<string, string> = {
  visible: 'text-ok',
  likely_visible: 'text-ok/70',
  lost: 'text-danger',
  occluded: 'text-warning',
  moved: 'text-cyan',
  stationary: 'text-text-secondary',
  unknown: 'text-text-tertiary',
}

export function TrackingPanel() {
  const {
    detectedObjects, trackedObjects, labeledItems,
    activeWatches, followMode, sceneSummary,
    sceneTimestamp, sceneExpired, analysisResult,
    analysisStatus, connected,
  } = useVisionStore()

  const [trackInput, setTrackInput] = useState('')
  const [labelInput, setLabelInput] = useState('')
  const [watchInput, setWatchInput] = useState('')
  const [queryInput, setQueryInput] = useState('')

  const handleTrackStart = useCallback(() => {
    if (!trackInput.trim()) return
    getVisionClient()?.trackStart(trackInput.trim())
    setTrackInput('')
  }, [trackInput])

  const handleTrackStop = useCallback((label: string) => {
    getVisionClient()?.trackStop(label)
  }, [])

  const handleLabelItem = useCallback(() => {
    if (!labelInput.trim()) return
    getVisionClient()?.labelItem(labelInput.trim())
    setLabelInput('')
  }, [labelInput])

  const handleWatchStart = useCallback(() => {
    if (!watchInput.trim()) return
    getVisionClient()?.watchStart(watchInput.trim())
    setWatchInput('')
  }, [watchInput])

  const handleWatchStop = useCallback((target: string) => {
    getVisionClient()?.watchStop(target)
  }, [])

  const handleFollowToggle = useCallback(() => {
    const client = getVisionClient()
    if (!client?.connected) return
    if (followMode.active) {
      client.followStop()
    } else {
      client.followStart()
    }
  }, [followMode.active])

  const handleAnalyze = useCallback(() => {
    getVisionClient()?.analyzeFrame('what do you see?')
  }, [])

  const handleQuery = useCallback(() => {
    if (!queryInput.trim()) return
    getVisionClient()?.queryVisual(queryInput.trim())
    setQueryInput('')
  }, [queryInput])

  const sceneAge = sceneTimestamp ? Math.round((Date.now() / 1000 - sceneTimestamp)) : -1

  return (
    <div className="flex flex-col gap-3">
      {/* Scene summary */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider">Scene State</span>
          <span className={clsx(
            'text-[9px] font-mono',
            sceneExpired ? 'text-danger' : 'text-ok',
          )}>
            {sceneTimestamp ? (sceneExpired ? `expired (${sceneAge}s ago)` : `${sceneAge}s ago`) : 'no scene'}
          </span>
        </div>
        {sceneSummary && (
          <div className="text-[10px] font-mono text-text-secondary px-2 py-1 rounded bg-surface-hover border border-border">
            {sceneSummary}
          </div>
        )}
      </div>

      {/* Follow mode */}
      <div className="flex items-center gap-2">
        <button
          onClick={handleFollowToggle}
          disabled={!connected}
          className={clsx(
            'flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider transition-colors',
            followMode.active
              ? 'bg-cyan/20 text-cyan border border-cyan/30'
              : 'bg-surface-hover text-text-secondary hover:text-text-primary border border-transparent',
            !connected && 'opacity-50 cursor-not-allowed',
          )}
        >
          {followMode.active ? <UserCheck size={10} /> : <UserX size={10} />}
          {followMode.active ? `Following ${followMode.target}` : 'Follow Me'}
        </button>
        <button
          onClick={handleAnalyze}
          disabled={!connected}
          className={clsx(
            'flex items-center gap-1 px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider transition-colors',
            analysisStatus === 'analyzing'
              ? 'bg-warning/20 text-warning'
              : 'bg-surface-hover text-text-secondary hover:text-text-primary',
            !connected && 'opacity-50 cursor-not-allowed',
          )}
        >
          <Eye size={10} />
          What Do You See?
        </button>
      </div>

      {/* Analysis result */}
      {analysisResult && analysisStatus !== 'idle' && (
        <div className="text-[10px] font-mono text-text-secondary px-2 py-1.5 rounded bg-surface-hover border border-cyan/20">
          <span className="text-[9px] text-cyan uppercase tracking-wider">Analysis: </span>
          {analysisResult}
        </div>
      )}

      {/* Detected objects */}
      {detectedObjects.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider">Detected</span>
          <div className="flex flex-wrap gap-1">
            {detectedObjects.map((obj) => (
              <span
                key={obj.track_id}
                className={clsx(
                  'px-1.5 py-0.5 rounded text-[10px] font-mono bg-surface-hover border border-border',
                  STATUS_COLORS[obj.status] || 'text-text-secondary',
                )}
                title={`${obj.label} — ${obj.status} — ${Math.round(obj.confidence * 100)}%`}
              >
                {obj.label} <span className="text-text-tertiary">{Math.round(obj.confidence * 100)}%</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Tracked objects */}
      <div className="flex flex-col gap-1.5">
        <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider">Tracked Items</span>
        {trackedObjects.length === 0 && labeledItems.length === 0 ? (
          <span className="text-[10px] font-mono text-text-tertiary">No items being tracked</span>
        ) : (
          <div className="flex flex-col gap-1">
            {[...trackedObjects, ...labeledItems].map((obj) => (
              <div
                key={obj.track_id}
                className="flex items-center justify-between px-2 py-1 rounded bg-surface-hover border border-border"
              >
                <div className="flex items-center gap-2">
                  <Crosshair size={10} className={STATUS_COLORS[obj.status] || 'text-text-tertiary'} />
                  <span className={clsx('text-[10px] font-mono', STATUS_COLORS[obj.status] || 'text-text-secondary')}>
                    {obj.label}
                  </span>
                  <span className="text-[9px] font-mono text-text-tertiary">
                    {obj.status} — {Math.round(obj.confidence * 100)}%
                  </span>
                  {obj.operator_confirmed && (
                    <Tag size={8} className="text-cyan" title="Operator labeled" />
                  )}
                </div>
                <button
                  onClick={() => handleTrackStop(obj.label)}
                  className="p-0.5 text-text-tertiary hover:text-danger transition-colors"
                  title="Stop tracking"
                >
                  <Trash2 size={10} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Track input */}
        <div className="flex items-center gap-1.5">
          <input
            type="text"
            value={trackInput}
            onChange={(e) => setTrackInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleTrackStart()}
            placeholder="Track item..."
            className="flex-1 px-2 py-1 rounded bg-surface border border-border text-[10px] font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-cyan/50"
          />
          <button
            onClick={handleTrackStart}
            disabled={!connected || !trackInput.trim()}
            className="px-2 py-1 rounded bg-cyan/10 text-cyan text-[10px] font-mono uppercase tracking-wider hover:bg-cyan/20 disabled:opacity-50"
          >
            Track
          </button>
        </div>
      </div>

      {/* Label input */}
      <div className="flex items-center gap-1.5">
        <Tag size={10} className="text-text-tertiary" />
        <input
          type="text"
          value={labelInput}
          onChange={(e) => setLabelInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleLabelItem()}
          placeholder="Label visible item..."
          className="flex-1 px-2 py-1 rounded bg-surface border border-border text-[10px] font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-cyan/50"
        />
        <button
          onClick={handleLabelItem}
          disabled={!connected || !labelInput.trim()}
          className="px-2 py-1 rounded bg-cyan/10 text-cyan text-[10px] font-mono uppercase tracking-wider hover:bg-cyan/20 disabled:opacity-50"
        >
          Label
        </button>
      </div>

      {/* Watch mode */}
      <div className="flex flex-col gap-1.5">
        <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider">Watch Mode</span>
        {activeWatches.length > 0 && (
          <div className="flex flex-col gap-1">
            {activeWatches.map((watch) => (
              <div
                key={watch.watch_id}
                className="flex items-center justify-between px-2 py-1 rounded bg-warning/5 border border-warning/20"
              >
                <div className="flex items-center gap-2">
                  <Bell size={10} className="text-warning" />
                  <span className="text-[10px] font-mono text-warning">
                    {watch.target_label}
                  </span>
                  <span className="text-[9px] font-mono text-text-tertiary">
                    → {watch.condition}
                  </span>
                </div>
                <button
                  onClick={() => handleWatchStop(watch.target_label)}
                  className="p-0.5 text-text-tertiary hover:text-danger transition-colors"
                  title="Stop watching"
                >
                  <BellOff size={10} />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-center gap-1.5">
          <input
            type="text"
            value={watchInput}
            onChange={(e) => setWatchInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleWatchStart()}
            placeholder="Watch item..."
            className="flex-1 px-2 py-1 rounded bg-surface border border-border text-[10px] font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-cyan/50"
          />
          <button
            onClick={handleWatchStart}
            disabled={!connected || !watchInput.trim()}
            className="px-2 py-1 rounded bg-warning/10 text-warning text-[10px] font-mono uppercase tracking-wider hover:bg-warning/20 disabled:opacity-50"
          >
            Watch
          </button>
        </div>
      </div>

      {/* Visual query */}
      <div className="flex items-center gap-1.5">
        <Search size={10} className="text-text-tertiary" />
        <input
          type="text"
          value={queryInput}
          onChange={(e) => setQueryInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
          placeholder="Where is my...?"
          className="flex-1 px-2 py-1 rounded bg-surface border border-border text-[10px] font-mono text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-cyan/50"
        />
        <button
          onClick={handleQuery}
          disabled={!connected || !queryInput.trim()}
          className="px-2 py-1 rounded bg-cyan/10 text-cyan text-[10px] font-mono uppercase tracking-wider hover:bg-cyan/20 disabled:opacity-50"
        >
          Ask
        </button>
      </div>
    </div>
  )
}
