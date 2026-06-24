import { useState, useRef, useEffect, useCallback } from 'react'
import { useEditorStore } from '../stores/editorStore'
import { useMetaIDEStore } from '../stores/metaIDEStore'
import { fetchApi } from '../api/client'

// ─── Types ──────────────────────────────────────────────────────

interface MenuItem {
  label: string
  shortcut?: string
  disabled?: boolean
  separator?: boolean
  action?: () => void
}

interface MenuGroup {
  label: string
  items: MenuItem[]
}

// ─── Save helper (mirrors EditorContent Ctrl+S) ─────────────────

async function saveActiveFile() {
  const { openFiles, activeFile } = useEditorStore.getState()
  const file = openFiles.find((f) => f.path === activeFile)
  if (!file) return

  const node = file.node
  let ok = false
  if (node === 'windows') {
    try {
      const data = await fetchApi<{ ok: boolean }>('/workspace/remote-write-file', {
        method: 'POST',
        body: JSON.stringify({ node: 'windows', path: file.path, content: file.content }),
      })
      ok = data.ok === true
    } catch { /* */ }
  } else {
    try {
      const ipc = window.cockpit?.writeFile
      if (ipc) { await ipc(file.path, file.content); ok = true }
    } catch { /* */ }
    if (!ok) {
      try {
        const data = await fetchApi<{ ok: boolean }>('/workspace/write-file', {
          method: 'POST',
          body: JSON.stringify({ path: file.path, content: file.content }),
        })
        ok = data.ok === true
      } catch { /* */ }
    }
  }
  if (ok) useEditorStore.getState().markClean(file.path)
}

// ─── Menu definitions ───────────────────────────────────────────

function buildMenus(): MenuGroup[] {
  const editorStore = useEditorStore.getState()
  const ideStore = useMetaIDEStore.getState()
  const hasActiveFile = !!editorStore.activeFile

  return [
    {
      label: 'File',
      items: [
        { label: 'New File', shortcut: 'Ctrl+N', disabled: true },
        { label: 'Open File', shortcut: 'Ctrl+O', disabled: true },
        { label: '', separator: true },
        { label: 'Save', shortcut: 'Ctrl+S', disabled: !hasActiveFile, action: saveActiveFile },
        { label: 'Save All', disabled: true },
        { label: '', separator: true },
        { label: 'Close Editor', shortcut: 'Ctrl+W', disabled: !hasActiveFile, action: () => {
          const af = useEditorStore.getState().activeFile
          if (af) useEditorStore.getState().closeFile(af)
        }},
        { label: 'Close All', action: () => useEditorStore.getState().closeAllFiles() },
      ],
    },
    {
      label: 'Edit',
      items: [
        { label: 'Undo', shortcut: 'Ctrl+Z', disabled: true },
        { label: 'Redo', shortcut: 'Ctrl+Shift+Z', disabled: true },
        { label: '', separator: true },
        { label: 'Cut', shortcut: 'Ctrl+X', disabled: true },
        { label: 'Copy', shortcut: 'Ctrl+C', disabled: true },
        { label: 'Paste', shortcut: 'Ctrl+V', disabled: true },
        { label: '', separator: true },
        { label: 'Find', shortcut: 'Ctrl+F', disabled: true },
      ],
    },
    {
      label: 'Selection',
      items: [
        { label: 'Select All', shortcut: 'Ctrl+A', disabled: true },
        { label: 'Expand Selection', disabled: true },
        { label: 'Shrink Selection', disabled: true },
      ],
    },
    {
      label: 'View',
      items: [
        { label: 'Explorer', shortcut: 'Ctrl+B', action: () => ideStore.toggleSidebarTab('files') },
        { label: 'Toggle Sidebar', shortcut: 'Ctrl+B', action: () => ideStore.setShowSidebar(!ideStore.showSidebar) },
        { label: '', separator: true },
        { label: 'Toggle Panel', shortcut: 'Ctrl+`', action: () => ideStore.togglePanel() },
        { label: 'Toggle Preview', shortcut: 'Ctrl+\\', action: () => useEditorStore.getState().togglePreview() },
        { label: '', separator: true },
        { label: 'Next Tab', shortcut: 'Ctrl+Tab', action: () => {
          const { openFiles: files, activeFile: current } = useEditorStore.getState()
          if (files.length < 2) return
          const idx = files.findIndex((f) => f.path === current)
          const next = files[(idx + 1) % files.length]
          useEditorStore.getState().setActiveFile(next.path)
        }},
      ],
    },
    {
      label: 'Go',
      items: [
        { label: 'Go to File', shortcut: 'Ctrl+P', disabled: true },
        { label: 'Go to Line', shortcut: 'Ctrl+G', disabled: true },
        { label: 'Go to Symbol', shortcut: 'Ctrl+Shift+O', disabled: true },
      ],
    },
    {
      label: 'Run',
      items: [
        { label: 'Start Debugging', shortcut: 'F5', disabled: true },
        { label: 'Run Without Debugging', disabled: true },
      ],
    },
    {
      label: 'Terminal',
      items: [
        { label: 'New Terminal', disabled: true },
        { label: 'Toggle Terminal', shortcut: 'Ctrl+`', action: () => useMetaIDEStore.getState().togglePanel() },
      ],
    },
    {
      label: 'Help',
      items: [
        { label: 'Keyboard Shortcuts', disabled: true },
        { label: 'About', disabled: true },
      ],
    },
  ]
}

// ─── Component ──────────────────────────────────────────────────

export function IDEMenuBar() {
  const [openMenu, setOpenMenu] = useState<string | null>(null)
  const barRef = useRef<HTMLDivElement>(null)

  const close = useCallback(() => setOpenMenu(null), [])

  useEffect(() => {
    if (!openMenu) return
    const handler = (e: MouseEvent) => {
      if (barRef.current && !barRef.current.contains(e.target as Node)) close()
    }
    const keyHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('mousedown', handler)
    document.addEventListener('keydown', keyHandler)
    return () => {
      document.removeEventListener('mousedown', handler)
      document.removeEventListener('keydown', keyHandler)
    }
  }, [openMenu, close])

  const menus = buildMenus()

  return (
    <div
      ref={barRef}
      className="flex items-center h-7 shrink-0 border-b border-border px-1 select-none"
      style={{ background: 'var(--color-surface)' }}
    >
      {menus.map((menu) => (
        <div key={menu.label} className="relative">
          <button
            onClick={() => setOpenMenu(openMenu === menu.label ? null : menu.label)}
            onMouseEnter={() => { if (openMenu) setOpenMenu(menu.label) }}
            className={`px-2 py-1 text-[11px] rounded transition-colors ${
              openMenu === menu.label
                ? 'bg-surface-raised text-text-primary'
                : 'text-text-secondary hover:text-text-primary hover:bg-surface-raised'
            }`}
          >
            {menu.label}
          </button>

          {openMenu === menu.label && (
            <div
              className="absolute top-full left-0 mt-0.5 rounded shadow-lg z-50 min-w-[220px] py-1"
              style={{
                background: 'var(--color-surface-raised)',
                border: '1px solid var(--color-border)',
              }}
            >
              {menu.items.map((item, i) =>
                item.separator ? (
                  <div key={i} className="my-1 border-t border-border" />
                ) : (
                  <button
                    key={item.label}
                    onClick={() => {
                      if (!item.disabled && item.action) {
                        item.action()
                        close()
                      }
                    }}
                    disabled={item.disabled}
                    className={`w-full flex items-center justify-between px-3 py-1.5 text-[11px] transition-colors ${
                      item.disabled
                        ? 'text-text-tertiary opacity-50 cursor-default'
                        : 'text-text-primary hover:bg-cyan-glow hover:text-cyan'
                    }`}
                  >
                    <span>{item.label}</span>
                    {item.shortcut && (
                      <span className="ml-4 text-[10px] text-text-tertiary font-mono">
                        {item.shortcut}
                      </span>
                    )}
                  </button>
                ),
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
