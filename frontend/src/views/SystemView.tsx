import { useEffect } from 'react'
import { Container as ContainerIcon, DollarSign, Database, RefreshCw } from 'lucide-react'
import clsx from 'clsx'
import { useSystemStore, type Container } from '../stores/systemStore'

function ContainerCard({ container }: { container: Container }) {
  const isRunning = (container.State || '').toLowerCase() === 'running'
  return (
    <div className="bg-zinc-800 rounded-lg p-4 border border-zinc-700">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-zinc-200">{container.Names}</h3>
        <span
          className={clsx(
            'text-xs px-2 py-0.5 rounded',
            isRunning ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
          )}
        >
          {container.State || 'unknown'}
        </span>
      </div>
      <div className="space-y-1 text-xs text-zinc-400">
        <p>
          <span className="text-zinc-500">Image:</span> {container.Image}
        </p>
        <p>
          <span className="text-zinc-500">Status:</span> {container.Status}
        </p>
        {container.Ports && (
          <p>
            <span className="text-zinc-500">Ports:</span> {container.Ports}
          </p>
        )}
      </div>
    </div>
  )
}

export default function SystemView() {
  const {
    containers,
    costs,
    costsAvailable,
    ingestionStatus,
    isLoading,
    fetchContainers,
    fetchCosts,
    fetchIngestionStatus,
  } = useSystemStore()

  useEffect(() => {
    fetchContainers()
    fetchCosts()
    fetchIngestionStatus()
  }, [fetchContainers, fetchCosts, fetchIngestionStatus])

  const handleRefresh = () => {
    fetchContainers()
    fetchCosts()
    fetchIngestionStatus()
  }

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium text-zinc-100">System Status</h2>
        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="flex items-center gap-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg px-3 py-2 text-sm transition-colors"
        >
          <RefreshCw size={14} className={clsx(isLoading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Containers */}
      <section>
        <h3 className="flex items-center gap-2 text-sm font-medium text-zinc-300 uppercase tracking-wide mb-3">
          <ContainerIcon size={16} />
          Docker Containers
        </h3>
        {containers.length === 0 ? (
          <p className="text-sm text-zinc-500">No containers found or Docker not accessible</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {containers.map((c) => (
              <ContainerCard key={c.ID || c.Names} container={c} />
            ))}
          </div>
        )}
      </section>

      {/* Costs */}
      <section>
        <h3 className="flex items-center gap-2 text-sm font-medium text-zinc-300 uppercase tracking-wide mb-3">
          <DollarSign size={16} />
          Cost Tracking
        </h3>
        {!costsAvailable ? (
          <div className="bg-zinc-800 rounded-lg p-4 border border-zinc-700 text-sm text-zinc-500">
            Cost log not available. Start tracking to see data here.
          </div>
        ) : (
          <div className="bg-zinc-800 rounded-lg p-4 border border-zinc-700">
            <pre className="text-xs text-zinc-400 overflow-x-auto">
              {JSON.stringify(costs, null, 2)}
            </pre>
          </div>
        )}
      </section>

      {/* Ingestion Status */}
      <section>
        <h3 className="flex items-center gap-2 text-sm font-medium text-zinc-300 uppercase tracking-wide mb-3">
          <Database size={16} />
          Ingestion Status
        </h3>
        {!ingestionStatus.available ? (
          <div className="bg-zinc-800 rounded-lg p-4 border border-zinc-700 text-sm text-zinc-500">
            No ingestion proof data available
          </div>
        ) : (
          <div className="space-y-2">
            {ingestionStatus.latest_proofs?.map((proof) => (
              <div
                key={proof.name}
                className="bg-zinc-800 rounded-lg px-4 py-3 border border-zinc-700 text-sm"
              >
                <span className="text-zinc-200">{proof.name}</span>
                <span className="text-xs text-zinc-500 ml-2">{proof.path}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
