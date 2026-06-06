import { useEffect, useRef, useState } from 'react'
import { useEditorStore } from '../stores/editorStore'
import { useProviderRegistryStore } from '../stores/providerRegistryStore'
import { useViewContextStore } from '../stores/viewContextStore'
import { fetchApi } from '../api/client'

type FileEntry = { name: string; path: string; type: 'file' | 'directory' }

interface FileNodeProps {
  name: string
  path: string
  type: 'file' | 'directory'
  depth: number
  node?: string
}

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
    const res = await window.cockpit?.readDir?.(path)
    if (res) return res
  } catch { /* IPC unavailable */ }
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

interface MeshNode { id: string; name: string; os: string; status: string; ip: string }

function FileTreeNode({ name, path, type, depth, node }: FileNodeProps) {
  const [expanded, setExpanded] = useState(false)
  const [children, setChildren] = useState<FileEntry[]>([])

  const handleClick = async () => {
    if (type === 'directory') {
      if (!expanded) {
        setChildren(await browseDir(path, node))
      }
      setExpanded(!expanded)
    } else {
      const result = await readFileContent(path, node)
      if (result) {
        useEditorStore.getState().openFile({
          path, name: result.name, content: result.content,
          language: detectLang(result.name), dirty: false,
        })
      }
    }
  }

  return (
    <>
      <button
        onClick={handleClick}
        className={`w-full text-left flex items-center gap-1 py-0.5 hover:bg-surface-raised transition-colors text-xs ${
          type === 'directory' ? 'text-text-primary' : 'text-text-secondary'
        }`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <span className="text-text-tertiary w-3.5 text-center">
          {type === 'directory' ? (expanded ? '▾' : '▸') : '·'}
        </span>
        <span className="truncate">{name}</span>
      </button>
      {expanded && children.map((child) => (
        <FileTreeNode
          key={child.path}
          name={child.name}
          path={child.path}
          type={child.type}
          depth={depth + 1}
          node={node}
        />
      ))}
    </>
  )
}

export function EditorPanel() {
  const openFiles = useEditorStore((s) => s.openFiles)
  const activeFile = useEditorStore((s) => s.activeFile)
  const showTerminal = useEditorStore((s) => s.showTerminal)
  const showPreview = useEditorStore((s) => s.showPreview)
  const setActiveFile = useEditorStore((s) => s.setActiveFile)
  const closeFile = useEditorStore((s) => s.closeFile)
  const updateContent = useEditorStore((s) => s.updateContent)
  const saveFile = useEditorStore((s) => s.saveFile)
  const toggleTerminal = useEditorStore((s) => s.toggleTerminal)
  const togglePreview = useEditorStore((s) => s.togglePreview)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const gitBranch = useEditorStore((s) => s.gitBranch)
  const gitChangedCount = useEditorStore((s) => s.gitChangedCount)
  const sessions = useEditorStore((s) => s.sessions)
  const activeNode = useEditorStore((s) => s.activeNode)
  const ccDelegating = useEditorStore((s) => s.ccDelegating)
  const fetchGitStatus = useEditorStore((s) => s.fetchGitStatus)
  const fetchSessions = useEditorStore((s) => s.fetchSessions)
  const delegateToClaudeCode = useEditorStore((s) => s.delegateToClaudeCode)
  const captureSession = useEditorStore((s) => s.captureSession)
  const setViewContext = useViewContextStore((s) => s.setContext)

  const [sidebarTab, setSidebarTab] = useState<'files' | 'sessions' | 'proof' | 'recent'>('files')
  const [ccPrompt, setCcPrompt] = useState('')
  const [ccTarget, setCcTarget] = useState('')
  const [capturedOutput, setCapturedOutput] = useState('')
  const [meshNodes, setMeshNodes] = useState<MeshNode[]>([])
  const [vpsTree, setVpsTree] = useState<FileEntry[]>([])
  const [windowsTree, setWindowsTree] = useState<FileEntry[]>([])
  const [vpsExpanded, setVpsExpanded] = useState(true)
  const [windowsExpanded, setWindowsExpanded] = useState(true)

  useEffect(() => {
    browseDir('').then((entries) => { if (entries.length) setVpsTree(entries) })
    browseDir('C:\\', 'windows').then((entries) => { if (entries.length) setWindowsTree(entries) })
  }, [])

  useEffect(() => {
    fetchGitStatus()
    fetchSessions()
    const fetchMesh = async () => {
      try {
        const data = await fetchApi<{ ok: boolean; nodes: MeshNode[] }>('/workspace/mesh-nodes')
        if (data.ok && data.nodes) setMeshNodes(data.nodes)
      } catch { /* silent */ }
    }
    fetchMesh()
    const id = setInterval(() => { fetchGitStatus(); fetchSessions(); fetchMesh() }, 15000)
    return () => clearInterval(id)
  }, [fetchGitStatus, fetchSessions])

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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.ctrlKey && e.key === 's' && activeFile) {
      e.preventDefault()
      saveFile(activeFile)
    }
  }

  return (
    <div className="flex h-full" onKeyDown={handleKeyDown}>
      {/* Left sidebar — topology */}
      <div className="w-56 shrink-0 flex flex-col overflow-hidden border-r border-border bg-canvas">
        <div className="px-3 py-2 border-b border-border">
          <div className="flex items-center gap-2 mb-1">
            <p className="wv-label flex-1">META IDE</p>
            {gitBranch && (
              <span className="text-[9px] font-mono text-cyan">
                {gitBranch}{gitChangedCount > 0 ? ` +${gitChangedCount}` : ''}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1 text-[9px] font-mono text-text-tertiary flex-wrap">
            <span className="text-ok">●</span> VPS
            {meshNodes.filter((n) => n.os === 'windows').map((n) => (
              <span key={n.id} className="ml-1">
                <span className="text-text-tertiary mx-0.5">·</span>
                <span className={n.status === 'connected' || n.status === 'online' ? 'text-ok' : 'text-danger'}>●</span>
                {' '}{n.name || 'Windows'}
              </span>
            ))}
          </div>
        </div>
        <div className="flex items-center border-b border-border">
          {(['files', 'sessions', 'proof', 'recent'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setSidebarTab(tab)}
              className={`flex-1 py-1 text-[9px] font-mono uppercase tracking-wider transition-colors ${
                sidebarTab === tab ? 'text-cyan border-b border-cyan' : 'text-text-tertiary'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
        <div className="flex-1 overflow-y-auto py-1">
          {sidebarTab === 'files' && (
            <>
              <button
                onClick={() => setVpsExpanded(!vpsExpanded)}
                className="w-full flex items-center gap-1.5 px-2 pt-1.5 pb-1 hover:bg-surface-raised transition-colors"
              >
                <span className="text-text-tertiary text-[9px]">{vpsExpanded ? '▾' : '▸'}</span>
                <span className="text-ok text-[9px]">●</span>
                <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider flex-1 text-left">VPS</span>
              </button>
              {vpsExpanded && (
                <>
                  {vpsTree.map((f) => (
                    <FileTreeNode key={f.path} name={f.name} path={f.path} type={f.type} depth={1} />
                  ))}
                  {vpsTree.length === 0 && (
                    <p className="text-xs px-3 py-2 text-center text-text-tertiary">Loading...</p>
                  )}
                </>
              )}
              {meshNodes.some((n) => n.os === 'windows' && (n.status === 'connected' || n.status === 'online')) && (
                <>
                  <button
                    onClick={() => setWindowsExpanded(!windowsExpanded)}
                    className="w-full flex items-center gap-1.5 px-2 pt-1.5 pb-1 hover:bg-surface-raised transition-colors border-t border-border mt-1"
                  >
                    <span className="text-text-tertiary text-[9px]">{windowsExpanded ? '▾' : '▸'}</span>
                    <span className="text-ok text-[9px]">●</span>
                    <span className="text-[9px] font-mono text-text-tertiary uppercase tracking-wider flex-1 text-left">Beast PC</span>
                  </button>
                  {windowsExpanded && (
                    <>
                      {windowsTree.map((f) => (
                        <FileTreeNode key={f.path} name={f.name} path={f.path} type={f.type} depth={1} node="windows" />
                      ))}
                      {windowsTree.length === 0 && (
                        <p className="text-xs px-3 py-2 text-center text-text-tertiary">Loading Beast PC files...</p>
                      )}
                    </>
                  )}
                </>
              )}
            </>
          )}
          {sidebarTab === 'sessions' && (
            <div className="px-2 py-1 space-y-1">
              {sessions.length === 0 && <p className="text-xs text-text-tertiary text-center py-4">No active sessions</p>}
              {sessions.map((s) => (
                <div key={s.name} className="flex items-center gap-2 py-1 px-1 rounded hover:bg-surface-raised text-xs">
                  <span className={`w-2 h-2 rounded-full ${s.status === 'active' ? 'bg-ok' : 'bg-text-tertiary'}`} />
                  <span className="text-text-primary flex-1 truncate font-mono text-[10px]">{s.name}</span>
                  <span className="text-[8px] text-text-tertiary uppercase">{s.type}</span>
                  <button
                    onClick={async () => {
                      const output = await captureSession(s.name)
                      setCapturedOutput(output)
                      setViewContext({ selected_object_type: 'session', selected_session_id: s.name })
                    }}
                    className="text-[8px] text-cyan hover:underline"
                  >
                    capture
                  </button>
                </div>
              ))}
              {/* Claude Code delegation section */}
              <div className="mt-3 pt-2 border-t border-border">
                <p className="wv-label mb-1">DELEGATE TO CC</p>
                <select
                  value={ccTarget}
                  onChange={(e) => setCcTarget(e.target.value)}
                  className="w-full mb-1 text-[10px] bg-surface-raised border border-border rounded px-1 py-0.5 text-text-primary"
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
                  className="w-full text-[10px] bg-surface-raised border border-border rounded px-2 py-1 text-text-primary placeholder-text-tertiary resize-none h-16"
                />
                <button
                  onClick={async () => {
                    if (ccTarget && ccPrompt.trim()) {
                      await delegateToClaudeCode(ccTarget, ccPrompt)
                      setCcPrompt('')
                    }
                  }}
                  disabled={!ccTarget || !ccPrompt.trim() || ccDelegating}
                  className="mt-1 w-full text-[10px] px-2 py-1 bg-cyan-glow text-cyan border border-cyan/30 rounded hover:bg-cyan/20 disabled:opacity-30 font-mono uppercase tracking-wider"
                >
                  {ccDelegating ? 'Sending...' : 'Send Prompt'}
                </button>
              </div>
              {/* Captured output display */}
              {capturedOutput && (
                <div className="mt-2 pt-2 border-t border-border">
                  <p className="wv-label mb-1">CAPTURED OUTPUT</p>
                  <pre className="text-[9px] font-mono text-text-secondary bg-canvas p-2 rounded max-h-32 overflow-y-auto whitespace-pre-wrap">
                    {capturedOutput}
                  </pre>
                </div>
              )}
            </div>
          )}
          {sidebarTab === 'proof' && (
            <p className="text-xs px-3 py-4 text-center text-text-tertiary">Proof artifacts coming soon</p>
          )}
          {sidebarTab === 'recent' && (
            <div className="px-2 py-1">
              {gitChangedCount > 0 ? (
                <p className="text-xs text-text-secondary">{gitChangedCount} file(s) changed on {gitBranch}</p>
              ) : (
                <p className="text-xs text-text-tertiary text-center py-4">No recent changes</p>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Editor area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Tab bar */}
        <div className="flex items-center h-8 shrink-0 overflow-x-auto border-b border-border bg-canvas">
          {openFiles.map((file) => (
            <button
              key={file.path}
              onClick={() => setActiveFile(file.path)}
              className={`flex items-center gap-1.5 px-3 h-full text-xs shrink-0 border-r border-border transition-colors ${
                activeFile === file.path ? 'text-text-primary bg-surface' : 'text-text-tertiary'
              }`}
            >
              <span>{file.name}</span>
              {file.dirty && <span className="text-warn">●</span>}
              <span
                onClick={(e) => { e.stopPropagation(); closeFile(file.path) }}
                className="ml-1 text-text-tertiary hover:text-white"
              >
                ×
              </span>
            </button>
          ))}

          <div className="flex-1" />

          <button
            onClick={togglePreview}
            className={`px-2 h-full text-xs transition-colors ${showPreview ? 'text-cyan' : 'text-text-tertiary'}`}
            title="Toggle Preview"
          >
            ⊞
          </button>
          <button
            onClick={toggleTerminal}
            className={`px-2 h-full text-xs transition-colors ${showTerminal ? 'text-cyan' : 'text-text-tertiary'}`}
            title="Toggle Terminal"
          >
            ⌘
          </button>
        </div>

        {/* Main editor content */}
        <div className="flex-1 flex min-h-0">
          {/* Code editor */}
          <div className="flex-1 flex flex-col min-w-0">
            {activeContent ? (
              <div className="flex-1 relative overflow-hidden">
                <div className="absolute inset-0 flex">
                  {/* Line numbers */}
                  <div className="shrink-0 text-right pr-2 pt-2 font-mono text-xs select-none overflow-hidden w-12 text-text-tertiary bg-canvas">
                    {activeContent.content.split('\n').map((_, i) => (
                      <div key={i} className="h-5">{i + 1}</div>
                    ))}
                  </div>
                  {/* Editor textarea */}
                  <textarea
                    ref={textareaRef}
                    value={activeContent.content}
                    onChange={(e) => updateContent(activeContent.path, e.target.value)}
                    spellCheck={false}
                    className="flex-1 resize-none p-2 font-mono text-xs text-text-primary bg-surface outline-none"
                    style={{ lineHeight: '1.25rem', tabSize: 2, caretColor: 'var(--color-cyan)' }}
                  />
                </div>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <p className="font-mono text-lg mb-2 text-cyan">META IDE</p>
                  <p className="text-xs text-text-tertiary">Open a file, session, or proof artifact</p>
                  <p className="text-xs mt-1 text-text-tertiary">
                    Ctrl+S to save · Ctrl+K for command palette
                    {gitBranch && ` · ${gitBranch}`}
                  </p>
                </div>
              </div>
            )}

            {/* Terminal — tmux bridge */}
            {showTerminal && <TerminalSection />}
          </div>

          {/* Right sidebar: Preview or Provider Registry */}
          {showPreview && (
            <div className="w-1/2 shrink-0 flex flex-col border-l border-border">
              <RightSidebar />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function TerminalSection() {
  const [cmd, setCmd] = useState('')
  const [output, setOutput] = useState<string[]>([])
  const [sending, setSending] = useState(false)
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

  return (
    <div className="h-48 shrink-0 flex flex-col border-t border-border bg-canvas">
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 font-mono text-[10px] text-text-secondary">
        <div className="flex items-center gap-2 mb-2">
          <span className="wv-label">Terminal</span>
          <span className="text-text-tertiary text-[9px]">tmux bridge</span>
        </div>
        {output.length === 0 && <p className="text-text-tertiary">Commands run via governed tmux bridge</p>}
        {output.map((line, i) => (
          <pre key={i} className={`whitespace-pre-wrap ${line.startsWith('$') ? 'text-cyan' : line.startsWith('err:') ? 'text-danger' : ''}`}>{line}</pre>
        ))}
      </div>
      <div className="flex items-center gap-1 px-3 py-1.5 border-t border-border">
        <span className="text-cyan text-[10px] font-mono">$</span>
        <input
          value={cmd}
          onChange={(e) => setCmd(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          placeholder="command..."
          disabled={sending}
          className="flex-1 text-[10px] font-mono px-1.5 py-0.5 bg-surface-raised text-text-primary border border-border rounded outline-none placeholder:text-text-tertiary"
        />
        <button onClick={send} disabled={sending || !cmd.trim()} className="text-[10px] font-mono px-2 py-0.5 text-cyan border border-border rounded hover:bg-cyan/10 disabled:opacity-30">
          {sending ? '...' : 'Run'}
        </button>
      </div>
    </div>
  )
}

function RightSidebar() {
  const [tab, setTab] = useState<'preview' | 'runtimes'>('runtimes')
  return (
    <>
      <div className="flex items-center h-8 px-3 shrink-0 border-b border-border bg-canvas gap-2">
        <button onClick={() => setTab('runtimes')}
          className={`wv-label text-[10px] ${tab === 'runtimes' ? 'text-cyan' : 'text-text-tertiary'}`}>
          Runtimes
        </button>
        <button onClick={() => setTab('preview')}
          className={`wv-label text-[10px] ${tab === 'preview' ? 'text-cyan' : 'text-text-tertiary'}`}>
          Preview
        </button>
      </div>
      {tab === 'runtimes' ? <ProviderRegistrySurface /> : (
        <div className="flex-1 flex items-center justify-center bg-surface-raised">
          <div className="text-center">
            <p className="text-xs text-text-tertiary">Live preview server integration coming in Phase 5.</p>
            <p className="text-xs mt-1 text-text-tertiary">Will render running web apps with hot reload (Replit pattern).</p>
          </div>
        </div>
      )}
    </>
  )
}

const STATUS_BADGE: Record<string, { color: string; label: string }> = {
  operational: { color: 'bg-ok', label: 'OK' },
  configured: { color: 'bg-cyan', label: 'CFG' },
  not_configured: { color: 'bg-text-tertiary', label: 'N/A' },
  error: { color: 'bg-danger', label: 'ERR' },
  unknown: { color: 'bg-text-tertiary', label: '?' },
}

function ProviderRegistrySurface() {
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
    <div className="flex-1 overflow-y-auto p-3 space-y-2">
      <div className="flex items-center justify-between mb-2">
        <p className="wv-label">Provider Registry</p>
        <button onClick={fetchProviders}
          className="text-[10px] text-cyan font-mono hover:underline">refresh</button>
      </div>
      {providers.map((p) => {
        const badge = STATUS_BADGE[p.status] || STATUS_BADGE.unknown
        return (
          <div key={p.id} className="border border-border rounded p-2 bg-surface-secondary">
            <div className="flex items-center gap-2 mb-1">
              <span className={`w-2 h-2 rounded-full shrink-0 ${badge.color}`} />
              <span className="text-xs font-medium text-text-primary">{p.name}</span>
              <span className="text-[9px] font-mono text-text-tertiary">{p.type}</span>
              <span className="ml-auto text-[9px] font-mono text-text-tertiary">{badge.label}</span>
            </div>
            <div className="flex flex-wrap gap-1 mb-1.5">
              {p.capabilities.map((c) => (
                <span key={c} className="px-1 py-0.5 text-[9px] rounded bg-surface-raised text-text-secondary">{c}</span>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => runSmoke(p.id)}
                className="px-1.5 py-0.5 text-[10px] rounded text-cyan border border-border hover:bg-cyan/10">
                smoke test
              </button>
              {testResult[p.id] && (
                <span className={`text-[10px] font-mono ${testResult[p.id] === 'pass' ? 'text-ok' : testResult[p.id] === 'testing...' ? 'text-text-tertiary' : 'text-danger'}`}>
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
