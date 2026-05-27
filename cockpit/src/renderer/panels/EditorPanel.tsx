import { useEffect, useRef, useState } from 'react'
import { useEditorStore } from '../stores/editorStore'

interface FileNodeProps {
  name: string
  path: string
  type: 'file' | 'directory'
  depth: number
}

function FileTreeNode({ name, path, type, depth }: FileNodeProps) {
  const [expanded, setExpanded] = useState(false)
  const [children, setChildren] = useState<{ name: string; path: string; type: 'file' | 'directory' }[]>([])
  const fetchFileContent = useEditorStore((s) => s.fetchFileContent)

  const handleClick = async () => {
    if (type === 'directory') {
      if (!expanded) {
        try {
          const items = await window.cockpit?.readDir?.(path)
          if (items) setChildren(items)
        } catch { /* noop */ }
      }
      setExpanded(!expanded)
    } else {
      fetchFileContent(path)
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
        />
      ))}
    </>
  )
}

export function EditorPanel() {
  const fileTree = useEditorStore((s) => s.fileTree)
  const openFiles = useEditorStore((s) => s.openFiles)
  const activeFile = useEditorStore((s) => s.activeFile)
  const showTerminal = useEditorStore((s) => s.showTerminal)
  const showPreview = useEditorStore((s) => s.showPreview)
  const setActiveFile = useEditorStore((s) => s.setActiveFile)
  const closeFile = useEditorStore((s) => s.closeFile)
  const updateContent = useEditorStore((s) => s.updateContent)
  const saveFile = useEditorStore((s) => s.saveFile)
  const fetchFileTree = useEditorStore((s) => s.fetchFileTree)
  const toggleTerminal = useEditorStore((s) => s.toggleTerminal)
  const togglePreview = useEditorStore((s) => s.togglePreview)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    fetchFileTree()
  }, [fetchFileTree])

  const activeContent = openFiles.find((f) => f.path === activeFile)

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.ctrlKey && e.key === 's' && activeFile) {
      e.preventDefault()
      saveFile(activeFile)
    }
  }

  return (
    <div className="flex h-full" onKeyDown={handleKeyDown}>
      {/* File tree */}
      <div className="w-56 shrink-0 overflow-y-auto border-r border-border bg-canvas">
        <div className="px-3 py-2 border-b border-border">
          <p className="wv-label">Explorer</p>
        </div>
        <div className="py-1">
          {fileTree.map((node) => (
            <FileTreeNode key={node.path} name={node.name} path={node.path} type={node.type} depth={0} />
          ))}
          {fileTree.length === 0 && (
            <p className="text-xs px-3 py-4 text-center text-text-tertiary">No file tree loaded</p>
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
                  <p className="font-mono text-lg mb-2 text-cyan">UMH IDE</p>
                  <p className="text-xs text-text-tertiary">Open a file from the explorer to begin editing</p>
                  <p className="text-xs mt-1 text-text-tertiary">Ctrl+S to save · Ctrl+K for command palette</p>
                </div>
              </div>
            )}

            {/* Terminal */}
            {showTerminal && (
              <div className="h-48 shrink-0 overflow-y-auto p-3 font-mono text-xs border-t border-border bg-canvas text-text-secondary">
                <div className="flex items-center gap-2 mb-2">
                  <span className="wv-label">Terminal</span>
                  <span className="text-text-tertiary">·</span>
                  <span className="text-ok">●</span>
                  <span className="text-text-tertiary">bash</span>
                </div>
                <p className="text-text-tertiary">Terminal integration via xterm.js + node-pty coming in Phase 5.</p>
                <p className="text-text-tertiary">$ <span className="text-cyan">_</span></p>
              </div>
            )}
          </div>

          {/* Live preview */}
          {showPreview && (
            <div className="w-1/2 shrink-0 flex flex-col border-l border-border">
              <div className="flex items-center h-8 px-3 shrink-0 border-b border-border bg-canvas">
                <p className="wv-label">Live Preview</p>
              </div>
              <div className="flex-1 flex items-center justify-center bg-surface-raised">
                <div className="text-center">
                  <p className="text-xs text-text-tertiary">Live preview server integration coming in Phase 5.</p>
                  <p className="text-xs mt-1 text-text-tertiary">Will render running web apps with hot reload (Replit pattern).</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
