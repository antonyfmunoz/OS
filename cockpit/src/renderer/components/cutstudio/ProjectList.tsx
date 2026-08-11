import { useCallback, useEffect, useRef, useState } from 'react'
import { Film, Trash2, Upload } from 'lucide-react'
import { useCutStudioStore } from '../../stores/cutStudioStore'
import { fmtTime } from '../../utils/cutAlgorithms'

/** Drag-drop + XHR-progress upload, and the grid of existing projects. */
export function ProjectList() {
  const projects = useCutStudioStore((s) => s.projects)
  const loading = useCutStudioStore((s) => s.loading)
  const uploading = useCutStudioStore((s) => s.uploading)
  const uploadProgress = useCutStudioStore((s) => s.uploadProgress)
  const loadProjects = useCutStudioStore((s) => s.loadProjects)
  const openProject = useCutStudioStore((s) => s.openProject)
  const upload = useCutStudioStore((s) => s.upload)
  const deleteProject = useCutStudioStore((s) => s.deleteProject)

  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    void loadProjects()
  }, [loadProjects])

  const handleFiles = useCallback(
    (files: FileList | null) => {
      const file = files?.[0]
      if (file) void upload(file)
    },
    [upload],
  )

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault()
      setDragging(false)
      handleFiles(e.dataTransfer.files)
    },
    [handleFiles],
  )

  return (
    <div
      className="flex flex-col h-full p-4 gap-4 relative"
      onDragOver={(e) => {
        e.preventDefault()
        if (!dragging) setDragging(true)
      }}
      onDragLeave={(e) => {
        // Only clear when the pointer truly leaves the drop surface, not when it
        // crosses onto a child element.
        if (e.currentTarget.contains(e.relatedTarget as Node)) return
        setDragging(false)
      }}
      onDrop={onDrop}
    >
      <div className="flex items-center gap-3 shrink-0">
        <span className="text-[11px] font-mono uppercase tracking-wider" style={{ color: 'var(--color-violet)' }}>
          CutStudio
        </span>
        <span className="text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
          {projects.length} project{projects.length === 1 ? '' : 's'}
        </span>
        <div className="flex-1" />
        {/* Hidden-input fallback: drag-drop is the fast path, but a click target
            is required for touch and for operators who never drag. */}
        <input
          ref={inputRef}
          type="file"
          accept="video/*,audio/*"
          className="hidden"
          onChange={(e) => {
            handleFiles(e.target.files)
            e.target.value = ''
          }}
        />
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="flex items-center gap-2 px-3 py-1.5 text-[10px] font-mono uppercase transition-colors"
          style={{
            background: 'var(--color-surface-raised)',
            border: '1px solid var(--color-border)',
            color: uploading ? 'var(--color-text-tertiary)' : 'var(--color-violet)',
          }}
        >
          <Upload size={11} />
          {uploading ? 'Uploading' : 'Upload'}
        </button>
      </div>

      {uploading && (
        <div className="shrink-0">
          <div className="h-1 w-full" style={{ background: 'var(--color-border)' }}>
            <div
              className="h-full transition-[width]"
              style={{ width: `${uploadProgress}%`, background: 'var(--color-violet)' }}
            />
          </div>
          <div className="text-[10px] font-mono mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
            {uploadProgress}%
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {loading && projects.length === 0 ? (
          <p className="text-[11px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
            Loading projects...
          </p>
        ) : projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2">
            <Film size={20} style={{ color: 'var(--color-text-tertiary)' }} />
            <p className="text-[11px] font-mono" style={{ color: 'var(--color-text-secondary)' }}>
              Drop a video or audio file to start a cut
            </p>
          </div>
        ) : (
          <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))' }}>
            {projects.map((p) => (
              <div
                key={p.id}
                className="p-3 cursor-pointer transition-colors group"
                style={{ background: 'var(--color-surface-raised)', border: '1px solid var(--color-border)' }}
                onClick={() => void openProject(p.id)}
                onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--color-violet)' }}
                onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--color-border)' }}
              >
                <div className="flex items-start gap-2">
                  <Film size={12} className="shrink-0 mt-0.5" style={{ color: 'var(--color-violet)' }} />
                  <span
                    className="text-[11px] font-mono truncate flex-1"
                    style={{ color: 'var(--color-text-primary)' }}
                    title={p.name}
                  >
                    {p.name}
                  </span>
                  <button
                    type="button"
                    className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                    style={{ color: 'var(--color-text-tertiary)' }}
                    title="Delete project"
                    onClick={(e) => {
                      e.stopPropagation()
                      void deleteProject(p.id)
                    }}
                  >
                    <Trash2 size={11} />
                  </button>
                </div>
                <div className="flex items-center gap-3 mt-2 text-[10px] font-mono" style={{ color: 'var(--color-text-tertiary)' }}>
                  <span>{fmtTime(p.duration)}</span>
                  <span>{p.has_transcript ? 'transcript' : 'no transcript'}</span>
                  {(p.renders?.length ?? 0) > 0 && (
                    <span>{p.renders?.length} render{p.renders?.length === 1 ? '' : 's'}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {dragging && (
        <div
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
          style={{ background: 'rgba(168, 85, 247, 0.08)', border: '2px dashed var(--color-violet)' }}
        >
          <span className="text-[12px] font-mono uppercase tracking-wider" style={{ color: 'var(--color-violet)' }}>
            Drop to upload
          </span>
        </div>
      )}
    </div>
  )
}
