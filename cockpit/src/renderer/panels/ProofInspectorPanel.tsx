import { useEffect, useState } from 'react'
import { useProofInspectorStore } from '../stores/proofInspectorStore'

const TABS = ['overview', 'packages', 'detail', 'timeline', 'evidence', 'raw'] as const
type Tab = typeof TABS[number]

const statusColor: Record<string, string> = {
  pending: 'text-yellow-400',
  approved: 'text-green-400',
  rejected: 'text-red-400',
}

function OverviewTab() {
  const { summary } = useProofInspectorStore()
  if (!summary) return <div className="wv-card p-4 text-gray-400">Loading summary...</div>
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Total Proofs</div>
          <div className="text-lg font-bold text-white">{summary.total}</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Pending</div>
          <div className="text-lg font-bold text-yellow-400">{summary.by_status?.pending || 0}</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Approved</div>
          <div className="text-lg font-bold text-green-400">{summary.by_status?.approved || 0}</div>
        </div>
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400">Rejected</div>
          <div className="text-lg font-bold text-red-400">{summary.by_status?.rejected || 0}</div>
        </div>
      </div>
      <div className="wv-card p-3">
        <div className="text-xs text-gray-400 mb-1">Store Status</div>
        <div className={`text-sm ${summary.store_available ? 'text-green-400' : 'text-red-400'}`}>
          {summary.store_available ? 'Available' : 'Unavailable'}
        </div>
      </div>
    </div>
  )
}

function PackagesTab() {
  const { packages, loading, fetchProofDetail } = useProofInspectorStore()
  const [filter, setFilter] = useState('')

  const filtered = filter ? packages.filter((p) => p.status === filter) : packages

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        {['', 'pending', 'approved', 'rejected'].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-2 py-1 text-xs rounded ${filter === s ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'}`}
          >
            {s || 'All'}
          </button>
        ))}
      </div>
      {loading && <div className="text-gray-400 text-sm">Loading...</div>}
      {filtered.length === 0 && !loading && (
        <div className="wv-card p-4 text-gray-400">No proof packages found</div>
      )}
      {filtered.map((pkg) => (
        <div
          key={pkg.proof_id}
          className="wv-card p-3 cursor-pointer hover:border-blue-500 transition-colors"
          onClick={() => fetchProofDetail(pkg.proof_id)}
        >
          <div className="flex justify-between items-start">
            <div>
              <div className="text-sm font-mono text-gray-300">{pkg.proof_id}</div>
              <div className="text-xs text-gray-400 mt-1">{pkg.description || 'No description'}</div>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded ${statusColor[pkg.status] || 'text-gray-400'} bg-gray-800`}>
              {pkg.status}
            </span>
          </div>
          <div className="flex gap-4 mt-2 text-xs text-gray-500">
            <span>{pkg.files_changed?.length || 0} files</span>
            <span>{pkg.commands_run?.length || 0} commands</span>
            <span>{new Date(pkg.created_at * 1000).toLocaleString()}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

function DetailTab() {
  const { selectedProof, approveProof, rejectProof } = useProofInspectorStore()
  const [notes, setNotes] = useState('')

  if (!selectedProof) return <div className="wv-card p-4 text-gray-400">Select a proof from the Packages tab</div>

  const p = selectedProof
  return (
    <div className="space-y-4">
      <div className="wv-card p-4">
        <div className="flex justify-between items-start mb-3">
          <div>
            <div className="text-sm font-mono text-white">{p.proof_id}</div>
            <div className="text-xs text-gray-400 mt-1">{p.description || 'No description'}</div>
          </div>
          <span className={`text-xs px-2 py-0.5 rounded ${statusColor[p.status] || 'text-gray-400'} bg-gray-800`}>
            {p.status}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div><span className="text-gray-400">Execution ID:</span> <span className="text-gray-300 font-mono">{p.execution_id || '—'}</span></div>
          <div><span className="text-gray-400">Packet ID:</span> <span className="text-gray-300 font-mono">{p.packet_id || '—'}</span></div>
          <div><span className="text-gray-400">Request ID:</span> <span className="text-gray-300 font-mono">{p.request_id || '—'}</span></div>
          <div><span className="text-gray-400">Created:</span> <span className="text-gray-300">{new Date(p.created_at * 1000).toLocaleString()}</span></div>
        </div>
      </div>

      {p.files_changed && p.files_changed.length > 0 && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Files Changed ({p.files_changed.length})</div>
          <div className="space-y-1">
            {p.files_changed.map((f, i) => (
              <div key={i} className="text-xs font-mono text-gray-300">{f}</div>
            ))}
          </div>
        </div>
      )}

      {p.commands_run && p.commands_run.length > 0 && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Commands Run ({p.commands_run.length})</div>
          <div className="space-y-1">
            {p.commands_run.map((c, i) => (
              <div key={i} className="text-xs font-mono text-gray-300 bg-gray-800 p-1 rounded">{c}</div>
            ))}
          </div>
        </div>
      )}

      {p.verification_results && p.verification_results.length > 0 && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Verification Results</div>
          {p.verification_results.map((v, i) => (
            <div key={i} className="text-xs text-gray-300 bg-gray-800 p-2 rounded mb-1">
              <pre className="whitespace-pre-wrap">{JSON.stringify(v, null, 2)}</pre>
            </div>
          ))}
        </div>
      )}

      {p.review_notes && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-1">Review Notes</div>
          <div className="text-sm text-gray-300">{p.review_notes}</div>
          <div className="text-xs text-gray-500 mt-1">by {p.reviewed_by} at {new Date(p.reviewed_at * 1000).toLocaleString()}</div>
        </div>
      )}

      {p.status === 'pending' && (
        <div className="wv-card p-3 space-y-2">
          <div className="text-xs text-gray-400">Review Actions</div>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Review notes (optional)"
            className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-xs text-gray-300"
            rows={2}
          />
          <div className="flex gap-2">
            <button
              onClick={() => approveProof(p.proof_id, notes)}
              className="px-3 py-1 text-xs bg-green-700 hover:bg-green-600 text-white rounded"
            >
              Approve
            </button>
            <button
              onClick={() => rejectProof(p.proof_id, notes)}
              className="px-3 py-1 text-xs bg-red-700 hover:bg-red-600 text-white rounded"
            >
              Reject
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function TimelineTab() {
  const { timeline, selectedProof } = useProofInspectorStore()
  if (!selectedProof) return <div className="wv-card p-4 text-gray-400">Select a proof first</div>
  if (timeline.length === 0) return <div className="wv-card p-4 text-gray-400">No timeline entries for this proof</div>
  return (
    <div className="space-y-2">
      {timeline.map((entry, i) => (
        <div key={i} className="wv-card p-3 flex items-start gap-3">
          <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
          <div className="flex-1">
            <div className="flex justify-between">
              <span className="text-xs font-bold text-gray-300">{entry.phase}</span>
              <span className="text-xs text-gray-500">{new Date(entry.timestamp * 1000).toLocaleString()}</span>
            </div>
            {entry.source && <div className="text-xs text-gray-400 mt-0.5">Source: {entry.source}</div>}
            {entry.details && <div className="text-xs text-gray-400 mt-0.5">{String(entry.details)}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}

function EvidenceTab() {
  const { selectedProof } = useProofInspectorStore()
  if (!selectedProof) return <div className="wv-card p-4 text-gray-400">Select a proof first</div>

  const files = selectedProof.evidence_files || []
  const browser = selectedProof.browser_evidence || []

  if (files.length === 0 && browser.length === 0) {
    return <div className="wv-card p-4 text-gray-400">No evidence files for this proof</div>
  }

  return (
    <div className="space-y-4">
      {files.length > 0 && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Evidence Files ({files.length})</div>
          <div className="space-y-1">
            {files.map((f, i) => (
              <div key={i} className="flex justify-between items-center text-xs bg-gray-800 p-2 rounded">
                <div className="flex items-center gap-2">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] ${f.type === 'image' ? 'bg-purple-900 text-purple-300' : f.type === 'json' ? 'bg-blue-900 text-blue-300' : 'bg-gray-700 text-gray-300'}`}>
                    {f.type}
                  </span>
                  <span className="font-mono text-gray-300">{f.name}</span>
                </div>
                <span className="text-gray-500">{(f.size / 1024).toFixed(1)} KB</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {browser.length > 0 && (
        <div className="wv-card p-3">
          <div className="text-xs text-gray-400 mb-2">Browser Evidence ({browser.length})</div>
          <div className="space-y-1">
            {browser.map((b, i) => (
              <div key={i} className="text-xs font-mono text-gray-300 bg-gray-800 p-2 rounded">{b}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function RawTab() {
  const { selectedProof } = useProofInspectorStore()
  if (!selectedProof) return <div className="wv-card p-4 text-gray-400">Select a proof first</div>
  return (
    <div className="wv-card p-3">
      <div className="text-xs text-gray-400 mb-2">Raw JSON</div>
      <pre className="text-xs text-gray-300 bg-gray-800 p-3 rounded overflow-auto max-h-[600px] whitespace-pre-wrap">
        {JSON.stringify(selectedProof, null, 2)}
      </pre>
    </div>
  )
}

export function ProofInspectorPanel() {
  const [tab, setTab] = useState<Tab>('overview')
  const { fetchSummary, fetchPackages, selectedProof, fetchTimeline } = useProofInspectorStore()

  useEffect(() => {
    fetchSummary()
    fetchPackages()
  }, [])

  useEffect(() => {
    if (selectedProof && tab === 'detail') {
      // auto-loaded by fetchProofDetail
    }
    if (selectedProof && tab === 'timeline') {
      fetchTimeline(selectedProof.proof_id)
    }
  }, [selectedProof, tab])

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 px-4 py-2 border-b border-gray-700">
        <h2 className="text-sm font-bold text-white">Proof Inspector</h2>
        <div className="flex gap-1 ml-auto">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-2 py-1 text-xs rounded ${tab === t ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        {tab === 'overview' && <OverviewTab />}
        {tab === 'packages' && <PackagesTab />}
        {tab === 'detail' && <DetailTab />}
        {tab === 'timeline' && <TimelineTab />}
        {tab === 'evidence' && <EvidenceTab />}
        {tab === 'raw' && <RawTab />}
      </div>
    </div>
  )
}
