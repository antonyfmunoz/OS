import React, { useEffect, useState } from 'react'
import { listDir, type FileEntry } from '../api/code-engine'

interface FileTreeProps {
  rootPath: string
  onFileSelect: (path: string) => void
}

interface TreeNode extends FileEntry {
  children?: TreeNode[]
  expanded?: boolean
}

export function FileTree({ rootPath, onFileSelect }: FileTreeProps) {
  const [tree, setTree] = useState<TreeNode[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDir(rootPath)
  }, [rootPath])

  async function loadDir(path: string) {
    try {
      setLoading(true)
      const result = await listDir(path)
      const nodes: TreeNode[] = result.entries
        .sort((a, b) => {
          if (a.type !== b.type) return a.type === 'directory' ? -1 : 1
          return a.name.localeCompare(b.name)
        })
        .map((e) => ({ ...e, expanded: false }))
      setTree(nodes)
    } catch (err) {
      console.error('FileTree load error:', err)
    } finally {
      setLoading(false)
    }
  }

  async function toggleDir(node: TreeNode) {
    if (node.type !== 'directory') {
      onFileSelect(node.path)
      return
    }
    if (!node.expanded && !node.children) {
      const result = await listDir(node.path)
      node.children = result.entries
        .sort((a, b) => {
          if (a.type !== b.type) return a.type === 'directory' ? -1 : 1
          return a.name.localeCompare(b.name)
        })
        .map((e) => ({ ...e, expanded: false }))
    }
    node.expanded = !node.expanded
    setTree([...tree])
  }

  function renderNode(node: TreeNode, depth: number) {
    const indent = depth * 16
    const icon = node.type === 'directory' ? (node.expanded ? '▼' : '▶') : '  '
    return (
      <div key={node.path}>
        <div
          className="flex items-center px-2 py-0.5 cursor-pointer hover:bg-border/40 text-sm font-mono truncate"
          style={{ paddingLeft: `${indent + 8}px` }}
          onClick={() => toggleDir(node)}
        >
          <span className="w-4 text-xs text-gray-500 mr-1">{icon}</span>
          <span className={node.type === 'directory' ? 'text-accent' : 'text-gray-300'}>
            {node.name}
          </span>
        </div>
        {node.expanded && node.children?.map((child) => renderNode(child, depth + 1))}
      </div>
    )
  }

  if (loading) {
    return <div className="p-4 text-sm text-gray-500">Loading...</div>
  }

  return (
    <div className="overflow-y-auto h-full">
      {tree.map((node) => renderNode(node, 0))}
    </div>
  )
}
