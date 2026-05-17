import React, { useState } from 'react'
import { FileTree } from '../components/FileTree'
import { EditorPanel } from '../components/EditorPanel'
import { TerminalPanel } from '../components/TerminalPanel'

const ROOT_PATH = '/app'

export function CodeView() {
  const [selectedFile, setSelectedFile] = useState<string | null>(null)

  return (
    <div className="h-screen w-screen flex flex-col bg-surface text-white">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 py-2 bg-panel border-b border-border">
        <h1 className="text-sm font-bold tracking-wide">UMH Operator / Code</h1>
        <span className="text-xs text-gray-500 font-mono">{ROOT_PATH}</span>
      </header>

      {/* Main content: 3-column layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: File tree */}
        <aside className="w-64 border-r border-border flex flex-col bg-panel">
          <div className="px-3 py-2 text-xs font-bold text-gray-400 uppercase tracking-wider border-b border-border">
            Explorer
          </div>
          <FileTree rootPath={ROOT_PATH} onFileSelect={setSelectedFile} />
        </aside>

        {/* Center: Editor */}
        <main className="flex-1 flex flex-col min-w-0">
          <EditorPanel filePath={selectedFile} />
        </main>

        {/* Right: Terminal */}
        <aside className="w-96 border-l border-border flex flex-col">
          <div className="px-3 py-2 text-xs font-bold text-gray-400 uppercase tracking-wider border-b border-border bg-panel">
            Terminal
          </div>
          <TerminalPanel />
        </aside>
      </div>
    </div>
  )
}
