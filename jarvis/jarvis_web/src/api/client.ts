const BASE = '/api/jarvis'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string }>('/health'),
  pulse: () => request<{ pulse: unknown }>('/pulse'),
  traces: () => request<{ traces: unknown[] }>('/traces'),
  approvals: () => request<{ approvals: unknown[] }>('/approvals'),
  models: () => request<{ models: unknown[] }>('/models'),
  infra: () => request<{ nodes: unknown[] }>('/infra'),

  submitSignal: (payload: { content: string; risk?: string }) =>
    request<{ id: string }>('/signal', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  approveItem: (id: string) =>
    request<{ ok: boolean }>(`/approvals/${id}/approve`, { method: 'POST' }),

  denyItem: (id: string) =>
    request<{ ok: boolean }>(`/approvals/${id}/deny`, { method: 'POST' }),
}
