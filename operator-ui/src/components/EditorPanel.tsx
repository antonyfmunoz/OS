import React, { useEffect, useState } from 'react'
import Editor from '@monaco-editor/react'
import { readFile, writeFile } from '../api/code-engine'

interface EditorPanelProps {
  filePath: string | null
}

export function EditorPanel({ filePath }: EditorPanelProps) {
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!filePath) return
    setLoading(true)
    setDirty(false)
    readFile(filePath)
      .then((r) => setContent(r.content))
      .catch((err) => setContent(`// Error loading file: ${err.message}`))
      .finally(() => setLoading(false))
  }, [filePath])

  function handleChange(value: string | undefined) {
    if (value !== undefined) {
      setContent(value)
      setDirty(true)
    }
  }

  async function handleSave() {
    if (!filePath || !dirty) return
    setSaving(true)
    try {
      await writeFile(filePath, content)
      setDirty(false)
    } catch (err) {
      console.error('Save error:', err)
    } finally {
      setSaving(false)
    }
  }

  function getLanguage(path: string | null): string {
    if (!path) return 'plaintext'
    const ext = path.split('.').pop()?.toLowerCase()
    const map: Record<string, string> = {
      ts: 'typescript',
      tsx: 'typescript',
      js: 'javascript',
      jsx: 'javascript',
      py: 'python',
      json: 'json',
      md: 'markdown',
      yaml: 'yaml',
      yml: 'yaml',
      sh: 'shell',
      bash: 'shell',
      css: 'css',
      html: 'html',
      sql: 'sql',
      toml: 'toml',
    }
    return map[ext || ''] || 'plaintext'
  }

  if (!filePath) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        Select a file to edit
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header bar */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-panel border-b border-border">
        <span className="text-xs font-mono text-gray-400 truncate">{filePath}</span>
        <div className="flex items-center gap-2">
          {dirty && <span className="text-xs text-yellow-400">modified</span>}
          <button
            onClick={handleSave}
            disabled={!dirty || saving}
            className="px-2 py-0.5 text-xs bg-accent/20 text-accent rounded hover:bg-accent/30 disabled:opacity-40"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
      {/* Editor */}
      <div className="flex-1 monaco-container">
        {loading ? (
          <div className="p-4 text-sm text-gray-500">Loading...</div>
        ) : (
          <Editor
            height="100%"
            language={getLanguage(filePath)}
            value={content}
            onChange={handleChange}
            theme="vs-dark"
            options={{
              fontSize: 13,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              wordWrap: 'on',
              lineNumbers: 'on',
              renderWhitespace: 'selection',
              tabSize: 2,
            }}
          />
        )}
      </div>
    </div>
  )
}
