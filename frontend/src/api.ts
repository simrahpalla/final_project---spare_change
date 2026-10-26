// Thin client for the FastAPI backend (backend/main.py). Same origin, so no base URL. No API keys live here.

export type Health = {
  ok: boolean
  model: string
  key_found: boolean
  key_source: string
  frontend_built: boolean
  mcp: { status: 'starting' | 'ready' | 'failed' | 'stopped'; error?: string | null; startup_seconds?: number | null }
  active_runs?: number
}

export type Company = {
  id: number
  name: string
  type: 'plant' | 'distributor'
  city: string
  state: string
  industry: string
  active_listings: number
  open_needs: number
  unread_alerts: number
}

export type Alert = { id: number; kind: string; message: string; read: number; created_at: string }

export type CompanyProfile = {
  company_id: number
  name: string
  type: string
  location: string
  industry: string
  installed_equipment: { platform: string; qty: number; years_in_use: number }[]
  open_needs: { need_id: number; part_number: string | null; platform: string | null; urgency: string }[]
  active_listing_ids: number[]
  alerts: Alert[]
  unread_alerts: number
}

export type Step = { step: string; status: string; [k: string]: any }

export type Totals = {
  requests: number
  input_tokens: number
  cached_tokens: number
  cache_write_tokens: number
  output_tokens: number
  total_tokens: number
  cost_usd: number
}

export type RunResult = { run_id: string; outcome: string; steps: Step[]; totals: Totals; listing_id?: number; draft?: any }

export type RunStatus = {
  run_id: string
  kind: string
  status: 'running' | 'done'
  current: string | null
  steps: Step[]
  totals: Totals
  result: RunResult | null
}

export type Session = {
  cost_usd: number
  budget_usd: number
  requests: number
  runs: number
  impact: {
    listings: number
    value_recovered: number
    scrap_value: number
    kg_kept_out_of_scrap: number
    est_kg_co2e_avoided: number
    est_hazardous_disposal_avoided: number
    placeholder_factors: boolean
    method: string | null
  }
}

export type LlmCheck = {
  run_id: string
  model: string
  reply: string
  input_tokens: number
  cached_tokens: number
  output_tokens: number
  cost_usd: number
}

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) } })
  } catch {
    throw new ApiError("Can't reach Spare Change. Is the app still running?")
  }
  if (!res.ok) {
    let detail = 'Something went wrong. Please try again.'
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* keep the friendly default */
    }
    throw new ApiError(detail)
  }
  return res.json() as Promise<T>
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

export const api = {
  health: () => request<Health>('/api/health'),
  companies: () => request<{ companies: Company[] }>('/api/companies'),
  company: (id: number) => request<CompanyProfile>(`/api/companies/${id}`),
  markAlertsRead: (id: number) => post(`/api/companies/${id}/alerts/read`),
  startSellerFlow: (text: string, sellerId: number) =>
    post<{ run_id: string }>('/api/seller-flow/start', { text, seller_id: sellerId }),
  run: (runId: string) => request<RunStatus>(`/api/runs/${runId}`),
  session: () => request<Session>('/api/session'),
  reset: () => post<{ ok: boolean; message: string }>('/api/reset'),
  llmCheck: () => post<LlmCheck>('/api/llm-check'),
}

export function errorMessage(e: unknown): string {
  return e instanceof ApiError ? e.message : 'Something went wrong. Please try again.'
}
