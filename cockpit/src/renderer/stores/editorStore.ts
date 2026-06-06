import { create } from 'zustand'

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

  fetchFileTree: async (root = '/opt/OS') => {
    try {
      const res = await window.cockpit?.readDir?.(root)
      if (res) set({ fileTree: res })
    } catch { /* IPC not available in web mode */ }
  },

  fetchFileContent: async (path: string) => {
    try {
      const content = await window.cockpit?.readFile?.(path)
      if (content !== undefined) {
        const name = path.split('/').pop() || path
        get().openFile({ path, name, content, language: detectLanguage(name), dirty: false })
      }
    } catch { /* IPC not available */ }
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
      const res = await fetch('/api/umh/workspace/git-status')
      if (res.ok) {
        const data = await res.json()
        set({ gitBranch: data.branch || '', gitChangedCount: data.changed_count || 0 })
      }
    } catch { /* silent */ }
  },

  fetchSessions: async () => {
    try {
      const res = await fetch('/api/umh/claude-session/list')
      if (res.ok) {
        const data = await res.json()
        const sessions = (data.sessions || []).map((s: Record<string, unknown>) => ({
          name: (s.name as string) || (s.session_name as string) || '',
          type: ((s.type as string) || 'tmux') as 'tmux' | 'claude-code',
          status: (s.status as string) || 'unknown',
        }))
        set({ sessions })
      }
    } catch { /* silent */ }
  },

  delegateToClaudeCode: async (sessionName, prompt) => {
    set({ ccDelegating: true })
    try {
      const res = await fetch('/api/umh/claude-session/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_name: sessionName, text: prompt }),
      })
      const data = await res.json()
      set({ ccDelegating: false })
      return data as { ok: boolean; error?: string }
    } catch (e) {
      set({ ccDelegating: false })
      return { ok: false, error: e instanceof Error ? e.message : 'failed' }
    }
  },

  captureSession: async (sessionName) => {
    try {
      const res = await fetch('/api/umh/claude-session/capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_name: sessionName }),
      })
      const data = await res.json() as Record<string, string>
      return data.output || data.content || ''
    } catch { return '' }
  },
}))
