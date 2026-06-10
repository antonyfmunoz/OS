import { create } from 'zustand'
import { fetchApi } from '../api/client'

interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileNode[]
}

interface OpenFile {
  path: string
  name: string
  content: string
  language: string
  dirty: boolean
  node?: string
}

interface SessionInfo {
  name: string
  type: 'tmux' | 'claude-code'
  status: string
}

interface EditorState {
  fileTree: FileNode[]
  openFiles: OpenFile[]
  activeFile: string | null
  showPreview: boolean
  showTerminal: boolean
  gitBranch: string
  gitChangedCount: number
  activeNode: string
  sessions: SessionInfo[]
  ccDelegating: boolean
  setFileTree: (tree: FileNode[]) => void
  openFile: (file: OpenFile) => void
  closeFile: (path: string) => void
  setActiveFile: (path: string) => void
  updateContent: (path: string, content: string) => void
  markClean: (path: string) => void
  togglePreview: () => void
  toggleTerminal: () => void
  fetchFileTree: (root?: string) => Promise<void>
  fetchFileContent: (path: string) => Promise<void>
  saveFile: (path: string) => Promise<void>
  fetchGitStatus: () => Promise<void>
  fetchSessions: () => Promise<void>
  delegateToClaudeCode: (sessionName: string, prompt: string) => Promise<{ ok: boolean; error?: string }>
  captureSession: (sessionName: string) => Promise<string>
}

function detectLanguage(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const map: Record<string, string> = {
    ts: 'typescript', tsx: 'typescriptreact', js: 'javascript', jsx: 'javascriptreact',
    py: 'python', md: 'markdown', json: 'json', css: 'css', html: 'html',
    yaml: 'yaml', yml: 'yaml', toml: 'toml', sql: 'sql', sh: 'shellscript',
    rs: 'rust', go: 'go', rb: 'ruby', java: 'java', c: 'c', cpp: 'cpp',
  }
  return map[ext] || 'plaintext'
}

export const useEditorStore = create<EditorState>((set, get) => ({
  fileTree: [],
  openFiles: [],
  activeFile: null,
  showPreview: false,
  showTerminal: true,
  gitBranch: '',
  gitChangedCount: 0,
  activeNode: 'vps',
  sessions: [],
  ccDelegating: false,

  setFileTree: (tree) => set({ fileTree: tree }),

  openFile: (file) => {
    const { openFiles } = get()
    if (!openFiles.find((f) => f.path === file.path)) {
      set({ openFiles: [...openFiles, file], activeFile: file.path })
    } else {
      set({ activeFile: file.path })
    }
  },

  closeFile: (path) => {
    const { openFiles, activeFile } = get()
    const filtered = openFiles.filter((f) => f.path !== path)
    const newActive = activeFile === path
      ? filtered.length > 0 ? filtered[filtered.length - 1].path : null
      : activeFile
    set({ openFiles: filtered, activeFile: newActive })
  },

  setActiveFile: (path) => set({ activeFile: path }),

  updateContent: (path, content) => {
    set((s) => ({
      openFiles: s.openFiles.map((f) =>
        f.path === path ? { ...f, content, dirty: true } : f
      ),
    }))
  },

  markClean: (path) => {
    set((s) => ({
      openFiles: s.openFiles.map((f) =>
        f.path === path ? { ...f, dirty: false } : f
      ),
    }))
  },

  togglePreview: () => set((s) => ({ showPreview: !s.showPreview })),
  toggleTerminal: () => set((s) => ({ showTerminal: !s.showTerminal })),

  fetchFileTree: async (root?: string) => {
    try {
      const res = await window.cockpit?.readDir?.(root || '/opt/OS')
      if (res) { set({ fileTree: res }); return }
    } catch { /* IPC not available in web mode */ }
    try {
      const qs = root ? `?path=${encodeURIComponent(root)}` : ''
      const data = await fetchApi<{ ok: boolean; entries: FileNode[] }>(`/workspace/browse${qs}`)
      if (data.ok && data.entries) {
        set({ fileTree: data.entries.map((e) => ({ name: e.name, path: e.path, type: e.type })) })
      }
    } catch { /* API fallback failed — auth or network */ }
  },

  fetchFileContent: async (path: string) => {
    try {
      const content = await window.cockpit?.readFile?.(path)
      if (content !== undefined) {
        const name = path.split('/').pop() || path
        get().openFile({ path, name, content, language: detectLanguage(name), dirty: false })
        return
      }
    } catch { /* IPC not available */ }
    try {
      const data = await fetchApi<{ ok: boolean; content: string }>(`/workspace/read-file?path=${encodeURIComponent(path)}`)
      if (data.ok && data.content !== undefined) {
        const name = path.split('/').pop() || path
        get().openFile({ path, name, content: data.content, language: detectLanguage(name), dirty: false })
      }
    } catch { /* API fallback failed */ }
  },

  saveFile: async (path: string) => {
    const file = get().openFiles.find((f) => f.path === path)
    if (!file) return
    try {
      await window.cockpit?.writeFile?.(path, file.content)
      get().markClean(path)
    } catch { /* IPC not available */ }
  },

  fetchGitStatus: async () => {
    try {
      const data = await fetchApi<{ branch?: string; changed_count?: number }>('/workspace/git-status')
      set({ gitBranch: data.branch || '', gitChangedCount: data.changed_count || 0 })
    } catch { /* silent */ }
  },

  fetchSessions: async () => {
    try {
      const data = await fetchApi<{ sessions?: Record<string, unknown>[] }>('/claude-session/list')
      const sessions = (data.sessions || []).map((s: Record<string, unknown>) => ({
        name: (s.name as string) || (s.session_name as string) || '',
        type: ((s.type as string) || 'tmux') as 'tmux' | 'claude-code',
        status: (s.status as string) || 'unknown',
      }))
      set({ sessions })
    } catch { /* silent */ }
  },

  delegateToClaudeCode: async (sessionName, prompt) => {
    set({ ccDelegating: true })
    try {
      const data = await fetchApi<{ ok: boolean; error?: string }>('/claude-session/send', {
        method: 'POST',
        body: JSON.stringify({ session_name: sessionName, text: prompt }),
      })
      set({ ccDelegating: false })
      return data
    } catch (e) {
      set({ ccDelegating: false })
      return { ok: false, error: e instanceof Error ? e.message : 'failed' }
    }
  },

  captureSession: async (sessionName) => {
    try {
      const data = await fetchApi<Record<string, string>>('/claude-session/capture', {
        method: 'POST',
        body: JSON.stringify({ session_name: sessionName }),
      })
      return data.output || data.content || ''
    } catch { return '' }
  },
}))
