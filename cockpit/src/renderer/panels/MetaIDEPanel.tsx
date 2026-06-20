import { useEffect, useRef, useState, useCallback } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useMetaIDEStore } from '../stores/metaIDEStore'
import { useEditorStore } from '../stores/editorStore'
import { useProviderRegistryStore } from '../stores/providerRegistryStore'
import { useViewContextStore } from '../stores/viewContextStore'
import { fetchApi } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { VPS, BEAST } from '../constants/devices'

const TABS = [
  'files', 'editor', 'sessions', 'workspace', 'repositories',
  'roadmap', 'risks', 'terminals', 'containers', 'runtimes', 'previews',
] as const

const RISK_COLORS: Record<string, string> = {
  none: 'text-zinc-400',
  low: 'text-green-400',
  medium: 'text-amber-400',
  high: 'text-orange-400',
  critical: 'text-red-400',
}

const HEALTH_COLORS: Record<string, string> = {
  healthy: 'text-green-400',
  dirty: 'text-amber-400',
  stale: 'text-orange-400',
  detached: 'text-red-400',
  unknown: 'text-zinc-500',
  degraded: 'text-orange-400',
  crashed: 'text-red-400',
}

const STATE_COLORS: Record<string, string> = {
  completed: 'text-green-400',
  in_progress: 'text-cyan-400',
  planned: 'text-zinc-400',
  blocked: 'text-red-400',
  unknown: 'text-zinc-500',
}

type FileEntry = { name: string; path: string; type: 'file' | 'directory' }

async function browseDir(path: string, node?: string): Promise<FileEntry[]> {
  if (node === 'windows') {
    try {
      const data = await fetchApi<{ ok: boolean; entries: FileEntry[] }>(
        `/workspace/remote-browse?node=windows&path=${encodeURIComponent(path)}`,
      )
      if (data.ok && data.entries) return data.entries.map((e) => ({ name: e.name, path: e.path, type: e.type }))
    } catch { /* remote browse failed */ }
    return []
  }
  try {
    const qs = path ? `?path=${encodeURIComponent(path)}` : ''
    const data = await fetchApi<{ ok: boolean; entries: FileEntry[] }>(`/workspace/browse${qs}`)
    if (data.ok && data.entries) return data.entries.map((e) => ({ name: e.name, path: e.path, type: e.type }))
  } catch { /* API fallback failed */ }
  return []
}

function detectLang(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const map: Record<string, string> = {
    ts: 'typescript', tsx: 'typescriptreact', js: 'javascript', jsx: 'javascriptreact',
    py: 'python', md: 'markdown', json: 'json', css: 'css', html: 'html',
    yaml: 'yaml', yml: 'yaml', toml: 'toml', sql: 'sql', sh: 'shellscript',
    rs: 'rust', go: 'go', rb: 'ruby', java: 'java', c: 'c', cpp: 'cpp',
    ps1: 'powershell', bat: 'bat', cmd: 'bat', xml: 'xml', txt: 'plaintext',
  }
  return map[ext] || 'plaintext'
}

async function readFileContent(path: string, node?: string): Promise<{ content: string; name: string } | null> {
  const sep = node === 'windows' ? '\\' : '/'
  const fname = path.split(sep).pop() || path
  if (node === 'windows') {
    try {
      const data = await fetchApi<{ ok: boolean; content: string }>(`/workspace/remote-read-file?node=windows&path=${encodeURIComponent(path)}`)
      if (data.ok && data.content !== undefined) return { content: data.content, name: fname }
    } catch { /* remote read failed */ }
    return null
  }
  try {
    const content = await window.cockpit?.readFile?.(path)
    if (content !== undefined) return { content, name: fname }
  } catch { /* IPC unavailable */ }
  try {
    const data = await fetchApi<{ ok: boolean; content: string }>(`/workspace/read-file?path=${encodeURIComponent(path)}`)
    if (data.ok && data.content !== undefined) return { content: data.content, name: fname }
  } catch { /* API fallback failed */ }
  return null
}

async function writeFileContent(path: string, content: string, node?: string): Promise<boolean> {
  if (node === 'windows') {
    try {
      const data = await fetchApi<{ ok: boolean }>('/workspace/remote-write-file', {
        method: 'POST', body: JSON.stringify({ node: 'windows', path, content }),
      })
      return data.ok === true
    } catch { return false }
  }
  try {
    await window.cockpit?.writeFile?.(path, content)
    return true
  } catch { /* IPC unavailable */ }
  try {
    const data = await fetchApi<{ ok: boolean }>('/workspace/write-file', {
      method: 'POST', body: JSON.stringify({ path, content }),
    })
    return data.ok === true
  } catch { return false }
}

interface MeshNode { id: string; name: string; os: string; status: string; ip?: string; device_type?: string }

// --- File tree node (used by Files tab) ---

function IDEFileTreeNode({ name, path, type, depth, node, onFileOpen }: {
  name: string; path: string; type: 'file' | 'directory'; depth: number; node?: string
  onFileOpen?: (path: string, node?: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [children, setChildren] = useState<FileEntry[]>([])

  const handleClick = async () => {
    if (type === 'directory') {
      if (!expanded) setChildren(await browseDir(path, node))
      setExpanded(!expanded)
    } else if (onFileOpen) {
      onFileOpen(path, node)
    }
  }

  return (
    <>
      <button
        onClick={handleClick}
        className={`w-full text-left flex items-center gap-1 py-0.5 hover:bg-zinc-800 transition-colors text-[11px] ${
          type === 'directory' ? 'text-zinc-200' : 'text-zinc-400'
        }`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <span className="text-zinc-500 w-3 text-center text-[9px]">
          {type === 'directory' ? (expanded ? '▾' : '▸') : '·'}
        </span>
        <span className="truncate">{name}</span>
      </button>
      {expanded && children.map((child) => (
        <IDEFileTreeNode
          key={child.path}
          name={child.name}
          path={child.path}
          type={child.type}
          depth={depth + 1}
          node={node}
          onFileOpen={onFileOpen}
        />
      ))}
    </>
  )
}

// --- Files Tab ---

function FilesTab() {
  const [vpsTree, setVpsTree] = useState<FileEntry[]>([])
  const [windowsTree, setWindowsTree] = useState<FileEntry[]>([])
  const [vpsExpanded, setVpsExpanded] = useState(true)
  const [windowsExpanded, setWindowsExpanded] = useState(true)
  const [meshNodes, setMeshNodes] = useState<MeshNode[]>([])
  const [windowsOnline, setWindowsOnline] = useState(false)
  const setActiveTab = useMetaIDEStore((s) => s.setActiveTab)

  useEffect(() => {
    browseDir('/').then((entries) => { if (entries.length) setVpsTree(entries) })
    browseDir('C:\\', 'windows').then((entries) => { if (entries.length) setWindowsTree(entries) })

    fetchApi<{ ok: boolean; nodes: MeshNode[] }>('/workspace/mesh-nodes')
      .then((data) => {
        if (data.ok && data.nodes) {
          setMeshNodes(data.nodes)
          setWindowsOnline(data.nodes.some((n) => n.os === 'windows' && (n.status === 'connected' || n.status === 'online')))
        }
      })
      .catch(() => {})
  }, [])

  const openFileInEditor = async (path: string, node?: string) => {
    const result = await readFileContent(path, node)
    if (result) {
      useEditorStore.getState().openFile({
        path, name: result.name, content: result.content,
        language: detectLang(result.name), dirty: false, node,
      })
      setActiveTab('editor')
    }
  }

  const vpsName = meshNodes.find((n) => n.id === 'vps')?.name || VPS.displayName
  const windowsName = meshNodes.find((n) => n.os === 'windows')?.name || BEAST.displayName

  return (
    <div className="py-1">
      <button
        onClick={() => setVpsExpanded(!vpsExpanded)}
        className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-zinc-800 transition-colors"
      >
        <span className="text-zinc-500 text-[9px]">{vpsExpanded ? '▾' : '▸'}</span>
        <span className="text-green-400 text-[9px]">●</span>
        <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider flex-1 text-left">{vpsName}</span>
      </button>
      {vpsExpanded && (
        <>
          {vpsTree.map((f) => (
            <IDEFileTreeNode key={f.path} name={f.name} path={f.path} type={f.type} depth={1} onFileOpen={openFileInEditor} />
          ))}
          {vpsTree.length === 0 && <p className="text-[11px] px-4 py-2 text-zinc-600">Loading...</p>}
        </>
      )}

      <button
        onClick={() => setWindowsExpanded(!windowsExpanded)}
        className="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-zinc-800 transition-colors border-t border-zinc-800 mt-1"
      >
        <span className="text-zinc-500 text-[9px]">{windowsExpanded ? '▾' : '▸'}</span>
        <span className={`text-[9px] ${windowsOnline ? 'text-green-400' : 'text-zinc-600'}`}>●</span>
        <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider flex-1 text-left">{windowsName}</span>
        {!windowsOnline && <span className="text-[9px] text-zinc-600">offline</span>}
      </button>
      {windowsExpanded && (
        <>
          {windowsOnline ? (
            <>
              {windowsTree.map((f) => (
                <IDEFileTreeNode key={f.path} name={f.name} path={f.path} type={f.type} depth={1} node="windows" onFileOpen={openFileInEditor} />
              ))}
              {windowsTree.length === 0 && <p className="text-[11px] px-4 py-2 text-zinc-600">Loading files...</p>}
            </>
          ) : (
            <p className="text-[11px] px-4 py-2 text-zinc-600">Device offline — connect to view files</p>
          )}
        </>
      )}
    </div>
  )
}

// --- Editor Tab (code editing capability) ---

function EditorTab() {
  const openFiles = useEditorStore((s) => s.openFiles)
  const activeFile = useEditorStore((s) => s.activeFile)
  const setActiveFile = useEditorStore((s) => s.setActiveFile)
  const closeFile = useEditorStore((s) => s.closeFile)
  const updateContent = useEditorStore((s) => s.updateContent)
  const gitBranch = useEditorStore((s) => s.gitBranch)
  const activeNode = useEditorStore((s) => s.activeNode)
  const setViewContext = useViewContextStore((s) => s.setContext)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (activeFile) {
      setViewContext({
        selected_object_type: 'file',
        selected_path: activeFile,
        selected_node: activeNode,
        selected_branch: gitBranch,
      })
    }
  }, [activeFile, activeNode, gitBranch, setViewContext])

  const activeContent = openFiles.find((f) => f.path === activeFile)

  const handleKeyDown = async (e: React.KeyboardEvent) => {
    if (e.ctrlKey && e.key === 's' && activeFile) {
      e.preventDefault()
      const file = openFiles.find((f) => f.path === activeFile)
      if (!file) return
      const ok = await writeFileContent(file.path, file.content, file.node)
      if (ok) useEditorStore.getState().markClean(file.path)
    }
  }

  if (openFiles.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="font-mono text-lg mb-2 text-cyan-400">META IDE</p>
          <p className="text-xs text-zinc-500">Open a file from the Files tab to begin editing</p>
          <p className="text-xs mt-1 text-zinc-500">
            Ctrl+S to save{gitBranch && ` · ${gitBranch}`}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-w-0" onKeyDown={handleKeyDown}>
      {/* Tab bar */}
      <div className="flex items-center h-8 shrink-0 overflow-x-auto border-b border-zinc-800 bg-zinc-950">
        {openFiles.map((file) => (
          <button
            key={file.path}
            onClick={() => setActiveFile(file.path)}
            className={`flex items-center gap-2 px-3 h-full text-xs shrink-0 border-r border-zinc-800 transition-colors ${
              activeFile === file.path ? 'text-zinc-200 bg-zinc-900' : 'text-zinc-500'
            }`}
          >
            <span>{file.name}</span>
            {file.dirty && <span className="text-amber-400">●</span>}
            <span
              onClick={(e) => { e.stopPropagation(); closeFile(file.path) }}
              className="ml-1 text-zinc-500 hover:text-white"
            >
              ×
            </span>
          </button>
        ))}
      </div>

      {/* Code editor */}
      {activeContent ? (
        <div className="flex-1 relative overflow-hidden">
          <div className="absolute inset-0 flex">
            <div className="shrink-0 text-right pr-2 pt-2 font-mono text-xs select-none overflow-hidden w-12 text-zinc-600 bg-zinc-950">
              {activeContent.content.split('\n').map((_, i) => (
                <div key={i} className="h-5">{i + 1}</div>
              ))}
            </div>
            <textarea
              ref={textareaRef}
              value={activeContent.content}
              onChange={(e) => updateContent(activeContent.path, e.target.value)}
              spellCheck={false}
              className="flex-1 resize-none p-2 font-mono text-xs text-zinc-200 bg-zinc-900 outline-none"
              style={{ lineHeight: '1.25rem', tabSize: 2, caretColor: '#00e5ff' }}
            />
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-zinc-500 text-xs">
          Select a file tab above
        </div>
      )}

      {/* Terminal bridge */}
      <TerminalSection />
    </div>
  )
}

// --- Sessions Tab (tmux sessions + CC delegation) ---

function SessionsTab() {
  const sessions = useEditorStore((s) => s.sessions)
  const ccDelegating = useEditorStore((s) => s.ccDelegating)
  const fetchSessions = useEditorStore((s) => s.fetchSessions)
  const delegateToClaudeCode = useEditorStore((s) => s.delegateToClaudeCode)
  const captureSession = useEditorStore((s) => s.captureSession)
  const gitBranch = useEditorStore((s) => s.gitBranch)
  const gitChangedCount = useEditorStore((s) => s.gitChangedCount)
  const fetchGitStatus = useEditorStore((s) => s.fetchGitStatus)
  const setViewContext = useViewContextStore((s) => s.setContext)

  const [ccPrompt, setCcPrompt] = useState('')
  const [ccTarget, setCcTarget] = useState('')
  const [capturedOutput, setCapturedOutput] = useState('')

  useEffect(() => {
    fetchGitStatus()
    fetchSessions()
    const id = setInterval(() => { fetchGitStatus(); fetchSessions() }, 15000)
    return () => clearInterval(id)
  }, [fetchGitStatus, fetchSessions])

  return (
    <div className="p-4 space-y-4">
      {/* Git status */}
      {gitBranch && (
        <div className="border border-zinc-700 rounded p-3">
          <div className="text-xs text-zinc-500 mb-1">Git</div>
          <div className="text-sm text-cyan-400 font-mono">
            {gitBranch}{gitChangedCount > 0 ? <span className="text-amber-400 ml-2">+{gitChangedCount} changed</span> : ''}
          </div>
        </div>
      )}

      {/* Active sessions */}
      <div>
        <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-2">Active Sessions</div>
        {sessions.length === 0 && <p className="text-xs text-zinc-600 text-center py-4">No active sessions</p>}
        {sessions.map((s) => (
          <div key={s.name} className="flex items-center gap-2 py-2 px-3 rounded hover:bg-zinc-800 text-xs border border-zinc-800 mb-1">
            <span className={`w-2 h-2 rounded-full ${s.status === 'active' ? 'bg-green-400' : 'bg-zinc-600'}`} />
            <span className="text-zinc-200 flex-1 truncate font-mono text-[10px]">{s.name}</span>
            <span className="text-[8px] text-zinc-500 uppercase">{s.type}</span>
            <button
              onClick={async () => {
                const output = await captureSession(s.name)
                setCapturedOutput(output)
                setViewContext({ selected_object_type: 'session', selected_session_id: s.name })
              }}
              className="text-[9px] text-cyan-400 hover:underline"
            >
              capture
            </button>
          </div>
        ))}
      </div>

      {/* Claude Code delegation */}
      <div className="border border-zinc-700 rounded p-3">
        <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-2">Delegate to Claude Code</div>
        <select
          value={ccTarget}
          onChange={(e) => setCcTarget(e.target.value)}
          className="w-full mb-2 text-[10px] bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-zinc-200"
        >
          <option value="">Select session...</option>
          {sessions.map((s) => (
            <option key={s.name} value={s.name}>{s.name}</option>
          ))}
        </select>
        <textarea
          value={ccPrompt}
          onChange={(e) => setCcPrompt(e.target.value)}
          placeholder="Enter prompt for Claude Code..."
          className="w-full text-[10px] bg-zinc-800 border border-zinc-700 rounded px-2 py-1.5 text-zinc-200 placeholder-zinc-600 resize-none h-20"
        />
        <button
          onClick={async () => {
            if (ccTarget && ccPrompt.trim()) {
              await delegateToClaudeCode(ccTarget, ccPrompt)
              setCcPrompt('')
            }
          }}
          disabled={!ccTarget || !ccPrompt.trim() || ccDelegating}
          className="mt-2 w-full text-[10px] px-2 py-1.5 bg-cyan-950 text-cyan-400 border border-cyan-800 rounded hover:bg-cyan-900 disabled:opacity-30 font-mono uppercase tracking-wider"
        >
          {ccDelegating ? 'Sending...' : 'Send Prompt'}
        </button>
      </div>

      {/* Captured output */}
      {capturedOutput && (
        <div className="border border-zinc-700 rounded p-3">
          <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Captured Output</div>
          <pre className="text-[9px] font-mono text-zinc-400 bg-zinc-950 p-2 rounded max-h-40 overflow-y-auto whitespace-pre-wrap">
            {capturedOutput}
          </pre>
        </div>
      )}
    </div>
  )
}

// --- Terminal Section (tmux bridge — shared by editor) ---

function TerminalSection() {
  const [cmd, setCmd] = useState('')
  const [output, setOutput] = useState<string[]>([])
  const [sending, setSending] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => { scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight) }, [output])

  const send = async () => {
    const text = cmd.trim()
    if (!text) return
    setOutput((p) => [...p, `$ ${text}`])
    setCmd('')
    setSending(true)
    try {
      const res = await fetchApi<{ ok?: boolean; output?: string; error?: string }>('/tmux/send', {
        method: 'POST',
        body: JSON.stringify({ session_name: 'main', text }),
      })
      if (res.error) {
        setOutput((p) => [...p, `err: ${res.error}`])
      } else {
        await new Promise((r) => setTimeout(r, 1500))
        try {
          const cap = await fetchApi<{ output?: string; content?: string }>('/claude-session/capture', {
            method: 'POST',
            body: JSON.stringify({ session_name: 'main' }),
          })
          const out = cap.output || cap.content || '(no output captured)'
          setOutput((p) => [...p, out])
        } catch { setOutput((p) => [...p, '(capture failed)']) }
      }
    } catch (e) {
      setOutput((p) => [...p, `err: ${e instanceof Error ? e.message : 'send failed'}`])
    }
    setSending(false)
  }

  if (!expanded) {
    return (
      <div className="shrink-0 border-t border-zinc-800 bg-zinc-950">
        <button
          onClick={() => setExpanded(true)}
          className="w-full flex items-center gap-2 px-3 py-1.5 text-[9px] font-mono text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <span>▸</span>
          <span className="uppercase tracking-wider">Terminal</span>
        </button>
      </div>
    )
  }

  return (
    <div className="h-48 shrink-0 flex flex-col border-t border-zinc-800 bg-zinc-950">
      <div className="flex items-center gap-2 px-3 py-1 border-b border-zinc-800">
        <button onClick={() => setExpanded(false)} className="text-zinc-500 hover:text-zinc-300 text-[9px]">▾</button>
        <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-wider">Terminal</span>
        <span className="text-zinc-600 text-[9px]">tmux bridge</span>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 font-mono text-[10px] text-zinc-400">
        {output.length === 0 && <p className="text-zinc-600">Commands run via governed tmux bridge</p>}
        {output.map((line, i) => (
          <pre key={i} className={`whitespace-pre-wrap ${line.startsWith('$') ? 'text-cyan-400' : line.startsWith('err:') ? 'text-red-400' : ''}`}>{line}</pre>
        ))}
      </div>
      <div className="flex items-center gap-1 px-3 py-2 border-t border-zinc-800">
        <span className="text-cyan-400 text-[10px] font-mono">$</span>
        <input
          value={cmd}
          onChange={(e) => setCmd(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          placeholder="command..."
          disabled={sending}
          className="flex-1 text-[10px] font-mono px-2 py-1 bg-zinc-800 text-zinc-200 border border-zinc-700 rounded outline-none placeholder:text-zinc-600"
        />
        <button onClick={send} disabled={sending || !cmd.trim()} className="text-[10px] font-mono px-2 py-1 text-cyan-400 border border-zinc-700 rounded hover:bg-cyan-950 disabled:opacity-30">
          {sending ? '...' : 'Run'}
        </button>
      </div>
    </div>
  )
}

// --- Workspace Tab ---

function WorkspaceTab() {
  const { workspace, fetchWorkspace, loading } = useMetaIDEStore()

  useEffect(() => { fetchWorkspace() }, [])

  if (loading && !workspace) return <div className="p-4 text-zinc-500">Loading workspace...</div>
  if (!workspace) return <div className="p-4 text-zinc-500">No workspace data</div>

  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Dirty Files" value={workspace.totals.dirty_files} warn={workspace.totals.dirty_files > 0} />
        <StatCard label="Branches" value={workspace.totals.branches} />
        <StatCard label="Worktrees" value={workspace.totals.worktrees} />
        <StatCard label="Stale Branches" value={workspace.totals.stale_branches} warn={workspace.totals.stale_branches > 0} />
        <StatCard label="Detached WTs" value={workspace.totals.detached_worktrees} warn={workspace.totals.detached_worktrees > 0} />
        <div className="border border-zinc-700 rounded p-3">
          <div className="text-xs text-zinc-500 mb-1">Overall Risk</div>
          <div className={`text-lg font-bold ${RISK_COLORS[workspace.overall_risk] || 'text-zinc-400'}`}>
            {workspace.overall_risk.toUpperCase()}
          </div>
        </div>
      </div>

      {workspace.repos.map((repo) => (
        <div key={repo.path} className="border border-zinc-700 rounded p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-zinc-200">{repo.name}</span>
            <span className={`text-xs px-2 py-0.5 rounded ${HEALTH_COLORS[repo.health] || 'text-zinc-500'}`}>
              {repo.health}
            </span>
          </div>
          <div className="text-xs text-zinc-500 space-y-0.5">
            <div>Branch: <span className="text-zinc-300">{repo.branch}</span></div>
            <div>Dirty: {repo.dirty} | Staged: {repo.staged} | Branches: {repo.branches} | WTs: {repo.worktrees}</div>
            {repo.issues.length > 0 && (
              <div className="text-amber-400 mt-1">{repo.issues.join(' · ')}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

// --- Repositories Tab ---

function RepositoriesTab() {
  const { repositories, fetchRepositories, loading } = useMetaIDEStore()

  useEffect(() => { fetchRepositories() }, [])

  if (loading && repositories.length === 0) return <div className="p-4 text-zinc-500">Loading...</div>
  if (repositories.length === 0) return <div className="p-4 text-zinc-500">No repositories found</div>

  return (
    <div className="p-4 space-y-4">
      {repositories.map((repo) => (
        <div key={repo.repo_path} className="border border-zinc-700 rounded p-3 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-zinc-200">{repo.repo_name}</span>
            <span className={`text-xs ${HEALTH_COLORS[repo.health.status]}`}>{repo.health.status}</span>
          </div>

          <div className="text-xs text-zinc-400">
            <span className="text-zinc-300">{repo.current_branch}</span> @ {repo.head_commit.slice(0, 8)}
          </div>

          {repo.dirty_files.length > 0 && (
            <div className="text-xs">
              <div className="text-amber-400 mb-1">Dirty ({repo.dirty_files.length})</div>
              <div className="max-h-24 overflow-y-auto space-y-0.5">
                {repo.dirty_files.slice(0, 10).map((f) => (
                  <div key={f} className="text-zinc-500 font-mono truncate">{f}</div>
                ))}
                {repo.dirty_files.length > 10 && <div className="text-zinc-600">...and {repo.dirty_files.length - 10} more</div>}
              </div>
            </div>
          )}

          {repo.worktrees.length > 1 && (
            <div className="text-xs">
              <div className="text-cyan-400 mb-1">Worktrees ({repo.worktrees.length})</div>
              {repo.worktrees.map((w) => (
                <div key={w.path} className="flex items-center gap-2 text-zinc-500">
                  <span className="font-mono truncate flex-1">{w.branch || '(detached)'}</span>
                  {w.locked && <span className="text-amber-400 text-[10px]">LOCKED</span>}
                  {w.detached && <span className="text-red-400 text-[10px]">DETACHED</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// --- Roadmap Tab ---

function RoadmapTab() {
  const { roadmap, fetchRoadmap, loading } = useMetaIDEStore()

  useEffect(() => { fetchRoadmap() }, [])

  if (loading && !roadmap) return <div className="p-4 text-zinc-500">Loading roadmap...</div>
  if (!roadmap) return <div className="p-4 text-zinc-500">No roadmap data</div>

  return (
    <div className="p-4 space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Total Phases" value={roadmap.total_phases} />
        <StatCard label="Completed" value={roadmap.completed_phases.length} />
      </div>

      <div className="border border-zinc-700 rounded p-3">
        <div className="text-xs text-zinc-500 mb-1">Progress</div>
        <div className="h-2 bg-zinc-800 rounded overflow-hidden">
          <div className="h-full bg-green-500 rounded" style={{ width: `${Math.round(roadmap.completion_ratio * 100)}%` }} />
        </div>
        <div className="text-xs text-zinc-400 mt-1">{Math.round(roadmap.completion_ratio * 100)}% complete</div>
      </div>

      {roadmap.current_phase && (
        <div className="border border-cyan-800 rounded p-3">
          <div className="text-xs text-cyan-400 mb-1">Current Phase</div>
          <div className="text-sm text-zinc-200">Phase {roadmap.current_phase.phase_number}: {roadmap.current_phase.phase_name}</div>
        </div>
      )}

      {roadmap.completed_phases.length > 0 && (
        <div>
          <div className="text-xs text-zinc-500 mb-2">Completed ({roadmap.completed_phases.length})</div>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {roadmap.completed_phases.map((p) => <PhaseRow key={p.phase_number} phase={p} />)}
          </div>
        </div>
      )}

      {roadmap.planned_phases.length > 0 && (
        <div>
          <div className="text-xs text-zinc-500 mb-2">Planned ({roadmap.planned_phases.length})</div>
          <div className="space-y-1">
            {roadmap.planned_phases.map((p) => <PhaseRow key={p.phase_number} phase={p} />)}
          </div>
        </div>
      )}

      {roadmap.blocked_phases.length > 0 && (
        <div>
          <div className="text-xs text-red-400 mb-2">Blocked ({roadmap.blocked_phases.length})</div>
          <div className="space-y-1">
            {roadmap.blocked_phases.map((p) => <PhaseRow key={p.phase_number} phase={p} />)}
          </div>
        </div>
      )}
    </div>
  )
}

// --- Risks Tab ---

function RisksTab() {
  const { risks, overallRisk, fetchRisks, loading } = useMetaIDEStore()

  useEffect(() => { fetchRisks() }, [])

  if (loading && risks.length === 0) return <div className="p-4 text-zinc-500">Loading risks...</div>

  return (
    <div className="p-4 space-y-4">
      <div className="border border-zinc-700 rounded p-3 flex items-center justify-between">
        <span className="text-xs text-zinc-500">Overall Risk</span>
        <span className={`text-sm font-bold ${RISK_COLORS[overallRisk] || 'text-zinc-400'}`}>{overallRisk.toUpperCase()}</span>
      </div>
      {risks.length === 0 ? (
        <div className="text-zinc-500 text-sm">No engineering risks detected.</div>
      ) : (
        <div className="space-y-2">
          {risks.map((r) => (
            <div key={r.id} className="border border-zinc-700 rounded p-3">
              <div className="flex items-center justify-between mb-1">
                <span className={`text-xs font-medium ${RISK_COLORS[r.level]}`}>{r.level.toUpperCase()}</span>
                <span className="text-xs text-zinc-600">{r.category}</span>
              </div>
              <div className="text-sm text-zinc-300">{r.description}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// --- Terminals Tab ---

function TerminalsTab() {
  const { observation, fetchObservation, loading } = useMetaIDEStore()

  useEffect(() => { fetchObservation() }, [])

  const terminals = observation?.terminals || []
  if (loading && terminals.length === 0) return <div className="p-4 text-zinc-500">Loading terminals...</div>
  if (terminals.length === 0) return <div className="p-4 text-zinc-500">No active terminals</div>

  return (
    <div className="p-4 space-y-2">
      {terminals.map((t) => (
        <div key={t.terminal_id} className="border border-zinc-700 rounded p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-zinc-200">{t.session_name}</span>
            <span className={`text-xs ${t.is_active ? 'text-green-400' : 'text-zinc-600'}`}>
              {t.is_active ? '● active' : '○ idle'}
            </span>
          </div>
          <div className="text-xs text-zinc-500 space-y-0.5">
            <div>Window: <span className="text-zinc-300">{t.window_name || '—'}</span> Pane: {t.pane_index}</div>
            {t.current_command && <div>Command: <span className="text-cyan-400 font-mono">{t.current_command}</span></div>}
            {t.cwd && <div className="text-zinc-600 font-mono truncate">{t.cwd}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}

// --- Containers Tab ---

function ContainersTab() {
  const { observation, fetchObservation, loading } = useMetaIDEStore()

  useEffect(() => { fetchObservation() }, [])

  const containers = observation?.containers || []
  if (loading && containers.length === 0) return <div className="p-4 text-zinc-500">Loading containers...</div>
  if (containers.length === 0) return <div className="p-4 text-zinc-500">No containers found</div>

  return (
    <div className="p-4 space-y-2">
      {containers.map((c) => (
        <div key={c.container_id} className="border border-zinc-700 rounded p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-zinc-200">{c.container_name}</span>
            <span className={`text-xs ${HEALTH_COLORS[c.health] || 'text-zinc-500'}`}>● {c.health}</span>
          </div>
          <div className="text-xs text-zinc-500 space-y-0.5">
            <div>Image: <span className="text-zinc-400 font-mono">{c.image}</span></div>
            <div>Status: <span className="text-zinc-300">{c.status}</span></div>
            {c.ports.length > 0 && <div>Ports: <span className="text-cyan-400">{c.ports.join(', ')}</span></div>}
            {c.restart_count > 0 && <div className="text-amber-400">Restarts: {c.restart_count}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}

// --- Runtimes Tab (provider registry) ---

const STATUS_BADGE: Record<string, { color: string; label: string }> = {
  operational: { color: 'bg-green-400', label: 'OK' },
  configured: { color: 'bg-cyan-400', label: 'CFG' },
  not_configured: { color: 'bg-zinc-600', label: 'N/A' },
  error: { color: 'bg-red-400', label: 'ERR' },
  unknown: { color: 'bg-zinc-600', label: '?' },
}

function RuntimesTab() {
  const providers = useProviderRegistryStore((s) => s.providers)
  const fetchProviders = useProviderRegistryStore((s) => s.fetchProviders)
  const smokeTest = useProviderRegistryStore((s) => s.smokeTest)
  const [testResult, setTestResult] = useState<Record<string, string>>({})

  useEffect(() => { fetchProviders() }, [fetchProviders])

  const runSmoke = async (id: string) => {
    setTestResult((p) => ({ ...p, [id]: 'testing...' }))
    const res = await smokeTest(id)
    setTestResult((p) => ({ ...p, [id]: res.success ? 'pass' : res.detail }))
  }

  return (
    <div className="p-4 space-y-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] text-zinc-400 uppercase tracking-wider">Provider Registry</span>
        <button onClick={fetchProviders} className="text-[10px] text-cyan-400 font-mono hover:underline">refresh</button>
      </div>
      {providers.map((p) => {
        const badge = STATUS_BADGE[p.status] || STATUS_BADGE.unknown
        return (
          <div key={p.id} className="border border-zinc-700 rounded p-3">
            <div className="flex items-center gap-2 mb-1">
              <span className={`w-2 h-2 rounded-full shrink-0 ${badge.color}`} />
              <span className="text-xs font-medium text-zinc-200">{p.name}</span>
              <span className="text-[9px] font-mono text-zinc-500">{p.type}</span>
              <span className="ml-auto text-[9px] font-mono text-zinc-500">{badge.label}</span>
            </div>
            <div className="flex flex-wrap gap-1 mb-2">
              {p.capabilities.map((c) => (
                <span key={c} className="px-1 py-0.5 text-[9px] rounded bg-zinc-800 text-zinc-400">{c}</span>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => runSmoke(p.id)} className="px-2 py-1 text-[10px] rounded text-cyan-400 border border-zinc-700 hover:bg-cyan-950">
                smoke test
              </button>
              {testResult[p.id] && (
                <span className={`text-[10px] font-mono ${testResult[p.id] === 'pass' ? 'text-green-400' : testResult[p.id] === 'testing...' ? 'text-zinc-500' : 'text-red-400'}`}>
                  {testResult[p.id]}
                </span>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// --- Previews Tab ---

function PreviewsTab() {
  const { observation, fetchObservation, loading } = useMetaIDEStore()

  useEffect(() => { fetchObservation() }, [])

  const previews = observation?.previews || []
  if (loading && previews.length === 0) return <div className="p-4 text-zinc-500">Loading previews...</div>
  if (previews.length === 0) return <div className="p-4 text-zinc-500">No dev servers detected</div>

  return (
    <div className="p-4 space-y-2">
      {previews.map((p) => (
        <div key={p.preview_id} className="border border-zinc-700 rounded p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm font-medium text-zinc-200">{p.name}</span>
            <span className={`text-xs ${HEALTH_COLORS[p.health] || 'text-zinc-500'}`}>● {p.health}</span>
          </div>
          <div className="text-xs text-zinc-500 space-y-0.5">
            <div>URL: <span className="text-cyan-400 font-mono">{p.url}</span></div>
            <div>Port: {p.port} | Process: <span className="text-zinc-300">{p.process_name || '—'}</span></div>
            {p.restart_count > 0 && <div className="text-amber-400">Restarts: {p.restart_count}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}

// --- Shared components ---

function StatCard({ label, value, warn }: { label: string; value: number; warn?: boolean }) {
  return (
    <div className="border border-zinc-700 rounded p-3">
      <div className="text-xs text-zinc-500 mb-1">{label}</div>
      <div className={`text-lg font-bold ${warn ? 'text-amber-400' : 'text-zinc-200'}`}>{value}</div>
    </div>
  )
}

function PhaseRow({ phase }: { phase: { phase_number: string; phase_name: string; state: string } }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={`${STATE_COLORS[phase.state] || 'text-zinc-500'}`}>●</span>
      <span className="text-zinc-400 w-8">P{phase.phase_number}</span>
      <span className="text-zinc-300 truncate flex-1">{phase.phase_name}</span>
    </div>
  )
}

// --- Context Sidebar ---

function ContextSidebar() {
  const [ctx, setCtx] = useState<Record<string, unknown> | null>(null)
  const [collapsed, setCollapsed] = useState(false)

  usePolling(useCallback(() => {
    fetchApi('/meta-ide-context/context').then(setCtx).catch(() => {})
  }, []), 10000, true, 1000)

  if (collapsed) {
    return (
      <div className="w-8 border-r border-zinc-800 flex flex-col items-center pt-2 shrink-0 bg-surface">
        <button onClick={() => setCollapsed(false)} className="p-1 text-zinc-500 hover:text-zinc-300">
          <ChevronRight size={14} />
        </button>
      </div>
    )
  }

  const project = (ctx?.active_project as string) || ''
  const repo = (ctx?.active_repo as string) || ''
  const goals = (ctx?.related_goals as Array<Record<string, string>>) || []
  const decisions = (ctx?.related_decisions as Array<Record<string, string>>) || []
  const constraints = (ctx?.constraints as string[]) || []

  return (
    <div className="w-[240px] border-r border-zinc-800 overflow-y-auto p-3 shrink-0 bg-surface">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-zinc-400 uppercase tracking-wider">Context</span>
        <button onClick={() => setCollapsed(true)} className="p-0.5 text-zinc-500 hover:text-zinc-300">
          <ChevronLeft size={12} />
        </button>
      </div>

      {project && <div className="text-[11px] mb-1"><span className="text-zinc-500">Project</span> <span className="text-zinc-200">{project}</span></div>}
      {repo && <div className="text-[11px] mb-3"><span className="text-zinc-500">Repo</span> <span className="text-zinc-200">{repo}</span></div>}

      {goals.length > 0 && (
        <div className="mb-3">
          <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Goals</div>
          {goals.slice(0, 5).map((g, i) => (
            <div key={i} className="text-[11px] text-zinc-300 py-0.5">{g.title || g.description || ''}</div>
          ))}
        </div>
      )}

      {decisions.length > 0 && (
        <div className="mb-3">
          <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Decisions</div>
          {decisions.slice(0, 5).map((d, i) => (
            <div key={i} className="text-[11px] text-zinc-300 py-0.5">{d.title || d.description || ''}</div>
          ))}
        </div>
      )}

      {constraints.length > 0 && (
        <div className="mb-3">
          <div className="text-[10px] text-zinc-400 uppercase tracking-wider mb-1">Constraints</div>
          {constraints.slice(0, 5).map((c, i) => (
            <div key={i} className="text-[11px] text-amber-400 py-0.5">{c}</div>
          ))}
        </div>
      )}

      {!project && !repo && goals.length === 0 && (
        <div className="text-[11px] text-zinc-600 text-center py-4">No context available</div>
      )}
    </div>
  )
}

// --- Main Meta IDE Panel ---

export function MetaIDEPanel() {
  const { activeTab, setActiveTab } = useMetaIDEStore()

  return (
    <div className="h-full flex flex-col overflow-hidden bg-surface">
      <div className="flex items-center gap-1 px-4 py-2 border-b border-zinc-800 overflow-x-auto shrink-0">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-1.5 text-xs rounded transition-colors whitespace-nowrap ${
              activeTab === tab
                ? 'bg-zinc-700 text-zinc-100'
                : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      <div className="flex-1 flex overflow-hidden">
        <ContextSidebar />
        <div className="flex-1 overflow-y-auto">
          {activeTab === 'files' && <FilesTab />}
          {activeTab === 'editor' && <EditorTab />}
          {activeTab === 'sessions' && <SessionsTab />}
          {activeTab === 'workspace' && <WorkspaceTab />}
          {activeTab === 'repositories' && <RepositoriesTab />}
          {activeTab === 'roadmap' && <RoadmapTab />}
          {activeTab === 'risks' && <RisksTab />}
          {activeTab === 'terminals' && <TerminalsTab />}
          {activeTab === 'containers' && <ContainersTab />}
          {activeTab === 'runtimes' && <RuntimesTab />}
          {activeTab === 'previews' && <PreviewsTab />}
        </div>
      </div>
    </div>
  )
}
