import { create } from 'zustand'
import { authHeader } from '../api/client'
import type {
  Detections,
  Edl,
  HighlightCandidate,
  Job,
  Project,
  Transcript,
  Word,
} from '../utils/cutAlgorithms'
import {
  applyFillerStrikes,
  applySilenceStrikes,
  edlDuration,
  outputToSource,
  restoreWords,
  strikeWords,
} from '../utils/cutAlgorithms'

/**
 * CutStudio API base. Deliberately local, NOT `client.ts`'s API_BASE — the
 * CutStudio backend is a separate service reached at its own edge prefix
 * (`/api/cut` -> 127.0.0.1:8931), while API_BASE points at the UMH operator API.
 */
export const CUT_API = (import.meta.env.VITE_CUT_API_URL as string) || '/api/cut'

const AUTOSAVE_MS = 800
const JOB_POLL_MS = 1500
const UNDO_DEPTH = 50

export interface CutChatMessage {
  id: string
  role: 'operator' | 'assistant'
  text: string
  /** Present on an assistant message that carries an EDL proposal. */
  proposal?: Edl
  note?: string
}

/** A word range selected in the transcript (inclusive of both ends). */
export interface WordSelection {
  words: Word[]
  struck: boolean
}

interface CutStudioState {
  projects: Project[]
  project: Project | null
  transcript: Transcript | null
  edl: Edl | null
  /** Server rev of the last successfully saved EDL — the If-Match value. */
  savedRev: number
  dirty: boolean
  saving: boolean
  /** Source-time playhead, driven by the preview player. */
  playhead: number
  selection: WordSelection | null
  jobs: Job[]
  chat: CutChatMessage[]
  chatSending: boolean
  pendingAiEdl: Edl | null
  pendingAiNote: string
  detections: Detections | null
  highlights: HighlightCandidate[]
  mediaUrl: string
  uploading: boolean
  uploadProgress: number
  loading: boolean
  error: string | null
  notice: string | null
  undoStack: Edl[]
  redoStack: Edl[]
  _autosaveTimer: ReturnType<typeof setTimeout> | null
  _jobTimer: ReturnType<typeof setInterval> | null

  loadProjects: () => Promise<void>
  openProject: (id: string) => Promise<void>
  closeProject: () => void
  upload: (file: File, name?: string) => Promise<void>
  deleteProject: (id: string) => Promise<void>
  transcribe: () => Promise<void>
  saveEdl: () => Promise<void>
  toggleStrike: (words: Word[], struck: boolean) => void
  setSelection: (sel: WordSelection | null) => void
  setClips: (edl: Edl) => void
  aiEdit: (instruction: string) => Promise<void>
  applyAiEdl: () => void
  discardAiEdl: () => void
  runDetect: (silenceThreshold: number) => Promise<void>
  applyDetections: (fillers: boolean, silences: boolean) => void
  runHighlights: (count: number, targetSeconds: number) => Promise<void>
  renderCut: (opts: RenderOptions) => Promise<void>
  undo: () => void
  redo: () => void
  setPlayhead: (t: number) => void
  seekOutput: (outputTime: number) => void
  mediaTokenUrl: (name: string, projectId?: string) => Promise<string>
  startJobPolling: () => void
  stopJobPolling: () => void
  clearNotice: () => void
}

export interface RenderOptions {
  aspect: 'source' | '9:16' | '1:1' | '16:9'
  captions: boolean
  caption_style: 1 | 2 | 3
  clean_audio: boolean
  clip?: { start: number; end: number }
}

/**
 * JSON request against the CutStudio service, with the Clerk bearer attached.
 * Returns the parsed body alongside the response so callers that need a header
 * (the EDL revision arrives as `X-EDL-Rev`, never in the body) can read it.
 */
async function cutRequest<T>(path: string, options?: RequestInit): Promise<{ data: T; res: Response }> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(await authHeader()),
    ...((options?.headers as Record<string, string>) ?? {}),
  }
  const res = await fetch(`${CUT_API}${path}`, { ...options, headers })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* not JSON — statusText stands */
    }
    const err = new Error(detail) as Error & { status: number }
    err.status = res.status
    throw err
  }
  return { data: (await res.json()) as T, res }
}

async function cutApi<T>(path: string, options?: RequestInit): Promise<T> {
  const { data } = await cutRequest<T>(path, options)
  return data
}

/**
 * The EDL revision is the optimistic-lock token. It lives in the `X-EDL-Rev`
 * header — reading it off the body would yield `undefined` and turn every save
 * into `If-Match: undefined`, which the server rejects as a 400.
 */
function revOf(res: Response, fallback: number): number {
  const raw = res.headers.get('X-EDL-Rev')
  if (raw === null) return fallback
  const parsed = Number.parseInt(raw, 10)
  return Number.isFinite(parsed) ? parsed : fallback
}

function errText(e: unknown): string {
  return e instanceof Error ? e.message : String(e)
}

/** Optimistic job record so the poller has something to track from submit. */
function queuedJob(id: string, kind: string, projectId: string): Job {
  return {
    id,
    kind,
    project_id: projectId,
    state: 'queued',
    detail: '',
    progress: 0,
    artifact: null,
    created: Date.now() / 1000,
    started: null,
    finished: null,
  }
}

export const useCutStudioStore = create<CutStudioState>((set, get) => ({
  projects: [],
  project: null,
  transcript: null,
  edl: null,
  savedRev: 0,
  dirty: false,
  saving: false,
  playhead: 0,
  selection: null,
  jobs: [],
  chat: [],
  chatSending: false,
  pendingAiEdl: null,
  pendingAiNote: '',
  detections: null,
  highlights: [],
  mediaUrl: '',
  uploading: false,
  uploadProgress: 0,
  loading: false,
  error: null,
  notice: null,
  undoStack: [],
  redoStack: [],
  _autosaveTimer: null,
  _jobTimer: null,

  loadProjects: async () => {
    set({ loading: true, error: null })
    try {
      const projects = await cutApi<Project[]>('/projects')
      set({ projects, loading: false })
    } catch (e) {
      set({ error: errText(e), loading: false })
    }
  },

  openProject: async (id) => {
    set({ loading: true, error: null, highlights: [], detections: null, chat: [], pendingAiEdl: null })
    try {
      // Fetched rather than read from the cached list: opening a project must
      // work without a prior list load, and `media` is required for playback.
      const project = await cutApi<Project>(`/projects/${id}`)
      const { data: edl, res: edlRes } = await cutRequest<Edl>(`/projects/${id}/edl`)
      let transcript: Transcript | null = null
      try {
        transcript = await cutApi<Transcript>(`/projects/${id}/transcript`)
      } catch {
        // No transcript yet — the operator transcribes from the panel.
        transcript = null
      }
      // An empty `name` lets the server fall back to the project's own media
      // file, which is exactly what the player wants.
      const mediaUrl = await get().mediaTokenUrl(project.media ?? '', id)
      set({
        project,
        edl,
        savedRev: revOf(edlRes, 0),
        transcript,
        mediaUrl,
        dirty: false,
        playhead: 0,
        selection: null,
        undoStack: [],
        redoStack: [],
        loading: false,
      })
      get().startJobPolling()
    } catch (e) {
      set({ error: errText(e), loading: false })
    }
  },

  closeProject: () => {
    get().stopJobPolling()
    const timer = get()._autosaveTimer
    if (timer) clearTimeout(timer)
    set({
      project: null,
      edl: null,
      transcript: null,
      mediaUrl: '',
      selection: null,
      detections: null,
      highlights: [],
      chat: [],
      pendingAiEdl: null,
      undoStack: [],
      redoStack: [],
      dirty: false,
      _autosaveTimer: null,
    })
  },

  /**
   * XHR rather than fetch: only XMLHttpRequest reports upload progress
   * (`upload.onprogress`), and a multi-GB VOD upload with no progress bar reads
   * as a hung UI. The Clerk bearer rides along via authHeader() — the route is
   * operator-gated, and a bare POST would 403.
   */
  upload: async (file, name) => {
    set({ uploading: true, uploadProgress: 0, error: null })
    const headers = await authHeader()
    try {
      const created = await new Promise<Project>((resolve, reject) => {
        const form = new FormData()
        form.append('file', file)
        if (name) form.append('name', name)

        const xhr = new XMLHttpRequest()
        xhr.open('POST', `${CUT_API}/projects`)
        for (const [k, v] of Object.entries(headers)) xhr.setRequestHeader(k, v)

        xhr.upload.onprogress = (evt) => {
          if (evt.lengthComputable) {
            set({ uploadProgress: Math.round((evt.loaded / evt.total) * 100) })
          }
        }
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              resolve(JSON.parse(xhr.responseText) as Project)
            } catch {
              reject(new Error('Upload succeeded but the response was unreadable'))
            }
          } else {
            let detail = xhr.statusText || `Upload failed (${xhr.status})`
            try {
              const body = JSON.parse(xhr.responseText)
              if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
            } catch {
              /* not JSON — statusText stands */
            }
            reject(new Error(detail))
          }
        }
        xhr.onerror = () => reject(new Error('Upload failed — network error'))
        xhr.onabort = () => reject(new Error('Upload cancelled'))
        xhr.send(form)
      })

      set({ uploading: false, uploadProgress: 100 })
      await get().loadProjects()
      await get().openProject(created.id)
    } catch (e) {
      set({ error: errText(e), uploading: false, uploadProgress: 0 })
    }
  },

  deleteProject: async (id) => {
    try {
      await cutApi<{ ok: boolean }>(`/projects/${id}`, { method: 'DELETE' })
      if (get().project?.id === id) get().closeProject()
      await get().loadProjects()
    } catch (e) {
      set({ error: errText(e) })
    }
  },

  transcribe: async () => {
    const project = get().project
    if (!project) return
    try {
      const { job_id } = await cutApi<{ job_id: string }>(`/projects/${project.id}/transcribe`, {
        method: 'POST',
        body: JSON.stringify({}),
      })
      set((s) => ({
        jobs: [...s.jobs, queuedJob(job_id, 'transcribe', project.id)],
        notice: `Transcription queued (${job_id.slice(0, 8)})`,
      }))
      get().startJobPolling()
    } catch (e) {
      set({ error: errText(e) })
    }
  },

  saveEdl: async () => {
    const { project, edl, savedRev, saving } = get()
    if (!project || !edl || saving) return
    set({ saving: true })
    try {
      const { data: saved, res } = await cutRequest<Edl>(`/projects/${project.id}/edl`, {
        method: 'PUT',
        headers: { 'If-Match': String(savedRev) },
        body: JSON.stringify(edl),
      })
      set({ edl: saved, savedRev: revOf(res, savedRev + 1), dirty: false, saving: false })
    } catch (e) {
      const status = (e as { status?: number }).status
      if (status === 409) {
        // Another operator (or tab) moved the EDL forward. Reload rather than
        // clobber — single-operator-per-project is a convention, not a lock.
        try {
          const { data: fresh, res } = await cutRequest<Edl>(`/projects/${project.id}/edl`)
          set({
            edl: fresh,
            savedRev: revOf(res, savedRev),
            dirty: false,
            saving: false,
            notice: 'This project changed elsewhere — reloaded the latest cut.',
          })
          return
        } catch (reloadErr) {
          set({ error: errText(reloadErr), saving: false })
          return
        }
      }
      set({ error: errText(e), saving: false })
    }
  },

  /** Push the current EDL onto the undo stack and schedule an autosave. */
  setClips: (next) => {
    const { edl, undoStack, _autosaveTimer } = get()
    if (!edl) return
    const undo = [...undoStack, edl].slice(-UNDO_DEPTH)
    if (_autosaveTimer) clearTimeout(_autosaveTimer)
    const timer = setTimeout(() => {
      set({ _autosaveTimer: null })
      void get().saveEdl()
    }, AUTOSAVE_MS)
    set({ edl: next, undoStack: undo, redoStack: [], dirty: true, _autosaveTimer: timer })
  },

  toggleStrike: (words, struck) => {
    const edl = get().edl
    if (!edl || words.length === 0) return
    const next = struck ? restoreWords(edl, words) : strikeWords(edl, words)
    get().setClips(next)
    set({ selection: null })
  },

  setSelection: (selection) => set({ selection }),

  aiEdit: async (instruction) => {
    const project = get().project
    if (!project || !instruction.trim()) return
    const operatorMsg: CutChatMessage = {
      id: `op-${Date.now()}`,
      role: 'operator',
      text: instruction.trim(),
    }
    // Synchronous latch: a second submit before the first resolves must no-op.
    if (get().chatSending) return
    set((s) => ({ chat: [...s.chat, operatorMsg], chatSending: true, error: null }))
    try {
      const res = await cutApi<{ edl: Edl; note: string }>(`/projects/${project.id}/ai-edit`, {
        method: 'POST',
        body: JSON.stringify({ instruction: instruction.trim() }),
      })
      const reply: CutChatMessage = {
        id: `ai-${Date.now()}`,
        role: 'assistant',
        text: res.note || 'Proposed a new cut.',
        proposal: res.edl,
        note: res.note,
      }
      set((s) => ({
        chat: [...s.chat, reply],
        chatSending: false,
        pendingAiEdl: res.edl,
        pendingAiNote: res.note ?? '',
      }))
    } catch (e) {
      set((s) => ({
        chat: [...s.chat, { id: `err-${Date.now()}`, role: 'assistant', text: errText(e) }],
        chatSending: false,
      }))
    }
  },

  applyAiEdl: () => {
    const proposal = get().pendingAiEdl
    if (!proposal) return
    get().setClips(proposal)
    set({ pendingAiEdl: null, pendingAiNote: '' })
  },

  discardAiEdl: () => set({ pendingAiEdl: null, pendingAiNote: '' }),

  runDetect: async (silenceThreshold) => {
    const project = get().project
    if (!project) return
    try {
      const detections = await cutApi<Detections>(`/projects/${project.id}/detect`, {
        method: 'POST',
        body: JSON.stringify({ fillers: true, silences: { threshold: silenceThreshold } }),
      })
      set({ detections })
    } catch (e) {
      set({ error: errText(e) })
    }
  },

  applyDetections: (fillers, silences) => {
    const { edl, detections } = get()
    if (!edl || !detections) return
    let next = edl
    if (fillers) next = applyFillerStrikes(next, detections.filler_words)
    if (silences) next = applySilenceStrikes(next, detections.silence_gaps)
    if (next === edl) return
    get().setClips(next)
  },

  runHighlights: async (count, targetSeconds) => {
    const project = get().project
    if (!project) return
    try {
      const { job_id } = await cutApi<{ job_id: string }>(`/projects/${project.id}/highlights`, {
        method: 'POST',
        body: JSON.stringify({ count, target_seconds: targetSeconds }),
      })
      set((s) => ({
        jobs: [...s.jobs, queuedJob(job_id, 'highlights', project.id)],
        notice: `Finding highlights (${job_id.slice(0, 8)})`,
      }))
      get().startJobPolling()
    } catch (e) {
      set({ error: errText(e) })
    }
  },

  renderCut: async (opts) => {
    const { project, dirty } = get()
    if (!project) return
    try {
      if (dirty) await get().saveEdl()
      const { job_id } = await cutApi<{ job_id: string }>(`/projects/${project.id}/render`, {
        method: 'POST',
        body: JSON.stringify(opts),
      })
      set((s) => ({
        jobs: [...s.jobs, queuedJob(job_id, 'render', project.id)],
        notice: `Render queued (${job_id.slice(0, 8)})`,
      }))
      get().startJobPolling()
    } catch (e) {
      set({ error: errText(e) })
    }
  },

  undo: () => {
    const { undoStack, redoStack, edl } = get()
    if (undoStack.length === 0 || !edl) return
    const prev = undoStack[undoStack.length - 1]
    set({
      edl: prev,
      undoStack: undoStack.slice(0, -1),
      redoStack: [...redoStack, edl].slice(-UNDO_DEPTH),
      dirty: true,
    })
    void get().saveEdl()
  },

  redo: () => {
    const { undoStack, redoStack, edl } = get()
    if (redoStack.length === 0 || !edl) return
    const next = redoStack[redoStack.length - 1]
    set({
      edl: next,
      redoStack: redoStack.slice(0, -1),
      undoStack: [...undoStack, edl].slice(-UNDO_DEPTH),
      dirty: true,
    })
    void get().saveEdl()
  },

  setPlayhead: (t) => set({ playhead: t }),

  seekOutput: (outputTime) => {
    const edl = get().edl
    if (!edl) return
    set({ playhead: outputToSource(edl, outputTime) })
  },

  /**
   * Media is served by link token, not header auth: a <video src> cannot send a
   * bearer, and blob-fetching a multi-GB VOD before playback is unacceptable.
   * The token IS the auth on /media, and it expires.
   */
  mediaTokenUrl: async (name, projectId) => {
    // The project id is passed explicitly on the open path: `project` is not in
    // the store yet at that point, and reading it there would silently yield an
    // empty media URL and a player that never loads.
    const id = projectId ?? get().project?.id
    if (!id) return ''
    try {
      const res = await cutApi<{ token: string; url?: string }>(
        `/projects/${id}/media-token?name=${encodeURIComponent(name)}`,
      )
      return res.url || `${CUT_API}/media?tok=${encodeURIComponent(res.token)}`
    } catch (e) {
      set({ error: errText(e) })
      return ''
    }
  },

  startJobPolling: () => {
    if (get()._jobTimer) return
    const tick = async () => {
      const project = get().project
      if (!project) return
      const active = get().jobs.filter((j) => j.state === 'queued' || j.state === 'running')
      if (active.length === 0) {
        get().stopJobPolling()
        return
      }
      try {
        const before = get().jobs
        const refreshed = await Promise.all(
          before.map(async (j) => {
            if (j.state === 'done' || j.state === 'error') return j
            try {
              return await cutApi<Job>(`/jobs/${j.id}`)
            } catch {
              return j
            }
          }),
        )
        set({ jobs: refreshed })

        for (const j of refreshed) {
          const was = before.find((p) => p.id === j.id)
          if (j.state === 'done' && was?.state !== 'done') {
            if (j.kind === 'transcribe') {
              try {
                const transcript = await cutApi<Transcript>(`/projects/${project.id}/transcript`)
                set({ transcript, notice: 'Transcript ready.' })
              } catch {
                set({ notice: 'Transcription finished but the transcript could not be loaded.' })
              }
            } else if (j.kind === 'highlights') {
              const artifact = j.artifact as { candidates?: HighlightCandidate[] } | null
              set({ highlights: artifact?.candidates ?? [], notice: 'Highlights ready.' })
            } else if (j.kind === 'render') {
              set({ notice: 'Render complete.' })
              void get().loadProjects()
            }
          }
        }
      } catch {
        /* transient poll failure — the next tick retries */
      }
    }
    const timer = setInterval(() => void tick(), JOB_POLL_MS)
    set({ _jobTimer: timer })
  },

  stopJobPolling: () => {
    const timer = get()._jobTimer
    if (timer) clearInterval(timer)
    set({ _jobTimer: null })
  },

  clearNotice: () => set({ notice: null, error: null }),
}))

/** Output duration of the current cut, for readouts that don't need the EDL. */
export function currentOutputDuration(): number {
  return edlDuration(useCutStudioStore.getState().edl)
}
