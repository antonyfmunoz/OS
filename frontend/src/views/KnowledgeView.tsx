import { useEffect, useState } from 'react'
import { Search, X, Database, Tag, Shield, Globe } from 'lucide-react'
import clsx from 'clsx'
import { useKnowledgeStore, type MemoryEntry } from '../stores/knowledgeStore'

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string
  value: string | number
  icon: typeof Database
}) {
  return (
    <div className="bg-zinc-800 rounded-lg p-4 border border-zinc-700">
      <div className="flex items-center gap-2 text-zinc-400 text-xs uppercase tracking-wide mb-1">
        <Icon size={14} />
        {label}
      </div>
      <div className="text-2xl font-bold text-zinc-100">{value}</div>
    </div>
  )
}

function EntryRow({
  entry,
  isSelected,
  onClick,
}: {
  entry: MemoryEntry
  isSelected: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full text-left px-4 py-3 border-b border-zinc-800 hover:bg-zinc-800/50 transition-colors',
        isSelected && 'bg-zinc-800'
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs px-2 py-0.5 rounded bg-indigo-600/20 text-indigo-300">
          {entry.primitive_type}
        </span>
        <span className="text-xs text-zinc-500">{entry.memory_type}</span>
      </div>
      <p className="text-sm text-zinc-200 truncate">{entry.label}</p>
      <p className="text-xs text-zinc-500 mt-0.5">
        {entry.confidence !== undefined && `Conf: ${(entry.confidence * 100).toFixed(0)}%`}
        {entry.source_document_id && ` | ${entry.source_document_id}`}
      </p>
    </button>
  )
}

function DetailPanel({ entry, onClose }: { entry: MemoryEntry; onClose: () => void }) {
  return (
    <div className="w-96 border-l border-zinc-800 bg-zinc-900 overflow-y-auto">
      <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
        <h3 className="text-sm font-medium text-zinc-200">Entry Detail</h3>
        <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
          <X size={16} />
        </button>
      </div>
      <div className="p-4 space-y-4 text-sm">
        <div>
          <label className="text-xs text-zinc-500 uppercase">Label</label>
          <p className="text-zinc-200 mt-1">{entry.label}</p>
        </div>
        <div>
          <label className="text-xs text-zinc-500 uppercase">Content</label>
          <p className="text-zinc-300 mt-1 whitespace-pre-wrap">{entry.content}</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-zinc-500 uppercase">Type</label>
            <p className="text-zinc-200 mt-1">{entry.primitive_type}</p>
          </div>
          <div>
            <label className="text-xs text-zinc-500 uppercase">Memory Type</label>
            <p className="text-zinc-200 mt-1">{entry.memory_type}</p>
          </div>
          <div>
            <label className="text-xs text-zinc-500 uppercase">Confidence</label>
            <p className="text-zinc-200 mt-1">
              {entry.confidence !== undefined ? `${(entry.confidence * 100).toFixed(0)}%` : 'N/A'}
            </p>
          </div>
          <div>
            <label className="text-xs text-zinc-500 uppercase">Memory ID</label>
            <p className="text-zinc-400 mt-1 font-mono text-xs break-all">{entry.memory_id}</p>
          </div>
        </div>
        {entry.source_document_id && (
          <div>
            <label className="text-xs text-zinc-500 uppercase">Source Document</label>
            <p className="text-zinc-400 mt-1 font-mono text-xs">{entry.source_document_id}</p>
          </div>
        )}
        <div>
          <label className="text-xs text-zinc-500 uppercase">Raw JSON</label>
          <pre className="mt-1 text-xs text-zinc-500 bg-zinc-950 p-3 rounded overflow-x-auto">
            {JSON.stringify(entry, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  )
}

export default function KnowledgeView() {
  const {
    entries,
    stats,
    total,
    isLoading,
    searchQuery,
    selectedEntry,
    fetchEntries,
    fetchStats,
    search,
    selectEntry,
  } = useKnowledgeStore()

  const [localQuery, setLocalQuery] = useState(searchQuery)

  useEffect(() => {
    fetchEntries()
    fetchStats()
  }, [fetchEntries, fetchStats])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    search(localQuery)
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Stats cards */}
        {stats && (
          <div className="p-4 grid grid-cols-4 gap-3 border-b border-zinc-800">
            <StatCard icon={Database} label="Total Entries" value={stats.total} />
            <StatCard
              icon={Tag}
              label="Primitive Types"
              value={Object.keys(stats.by_type).length}
            />
            <StatCard
              icon={Shield}
              label="Authority Tiers"
              value={Object.keys(stats.by_tier).length}
            />
            <StatCard
              icon={Globe}
              label="Domains"
              value={Object.keys(stats.by_domain).length}
            />
          </div>
        )}

        {/* Search bar */}
        <form onSubmit={handleSearch} className="p-4 border-b border-zinc-800">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input
                type="text"
                value={localQuery}
                onChange={(e) => setLocalQuery(e.target.value)}
                placeholder="Search knowledge entries..."
                className="w-full bg-zinc-800 border border-zinc-700 rounded-lg pl-10 pr-4 py-2 text-sm text-zinc-100 focus:outline-none focus:border-indigo-500 placeholder:text-zinc-600"
              />
            </div>
            <button
              type="submit"
              className="bg-zinc-700 hover:bg-zinc-600 text-zinc-200 rounded-lg px-4 py-2 text-sm transition-colors"
            >
              Search
            </button>
          </div>
        </form>

        {/* Entry list */}
        <div className="flex-1 overflow-y-auto">
          {isLoading && (
            <div className="p-4 text-sm text-zinc-500">Loading...</div>
          )}
          {!isLoading && entries.length === 0 && (
            <div className="p-4 text-sm text-zinc-500">No entries found</div>
          )}
          {entries.map((entry) => (
            <EntryRow
              key={entry.memory_id}
              entry={entry}
              isSelected={selectedEntry?.memory_id === entry.memory_id}
              onClick={() => selectEntry(entry)}
            />
          ))}
          {!isLoading && entries.length > 0 && (
            <div className="p-3 text-xs text-zinc-600 text-center">
              Showing {entries.length} of {total} entries
            </div>
          )}
        </div>
      </div>

      {/* Detail panel */}
      {selectedEntry && (
        <DetailPanel entry={selectedEntry} onClose={() => selectEntry(null)} />
      )}
    </div>
  )
}
