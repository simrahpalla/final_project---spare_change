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

export type Alert = {
  closed_reason?: string | null
  id: number
  kind: string
  message: string
  read: number
  created_at: string
  listing_id: number | null
  need_id: number | null
  score: number | null
  run_id: string | null
}

export type Need = {
  need_id: number
  status: 'open' | 'matched' | 'filled' | 'cancelled'
  buyer_id: number
  buyer_name: string
  buyer_location: string
  part_number: string | null
  platform: string | null
  family: string | null
  qty: number
  urgency: 'line_down' | 'high' | 'normal' | 'low'
  downtime_cost_per_day: number
  created_at: string
}

export type Listing = {
  listing_id: number
  status: string
  seller_id: number
  seller_name: string
  location: string
  part_number: string
  manufacturer: string
  family: string
  description: string
  qty: number
  condition: string
  asking_price: number | null
  new_price: number | null
  fits_platforms: string[]
  expiry_date: string | null
  hazmat: boolean | null
}

type ImpactTotals = { value_recovered: number; scrap_value: number; kg_kept_out_of_scrap: number; est_kg_co2e_avoided: number }

export type Board = {
  listings: Listing[]
  needs: Need[]
  pairs: { listing_id: number; need_id: number; why: string }[]
  impact: ImpactTotals & { deals: number; method: string }
  potential: ImpactTotals & { listings: number; note: string }
}

export type NeedInput = {
  text: string
  buyer_id: number
  max_price?: number | null
  urgency?: Need['urgency'] | null
  downtime_cost_per_day?: number | null
}

export type CompanyProfile = {
  company_id: number
  name: string
  type: string
  location: string
  industry: string
  auto_negotiate: boolean
  installed_equipment: { platform: string; qty: number; years_in_use: number }[]
  open_needs: Need[]
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
  startNeedFlow: (body: NeedInput) => post<{ run_id: string }>('/api/need-flow/start', body),
  marketplace: () => request<Board>('/api/marketplace'),
  run: (runId: string) => request<RunStatus>(`/api/runs/${runId}`),
  session: () => request<Session>('/api/session'),
  reset: () => post<{ ok: boolean; message: string }>('/api/reset'),
  llmCheck: () => post<LlmCheck>('/api/llm-check'),
}

export function errorMessage(e: unknown): string {
  return e instanceof ApiError ? e.message : 'Something went wrong. Please try again.'
}

// ------------------------------------------------------------------ negotiations (Phase 6)
// Every negotiation view is scoped to ONE company: its own limit, notes and blocked moves; never the other side's.

export type Side = 'seller' | 'buyer'

export type Offer = { round: number; from_side: Side; action: 'offer' | 'accept' | 'walk_away'; price: number; message_untrusted: string | null; created_at: string }

export type Blocked = { at: string; code: string; price: number | null; text: string }

export type Deal = {
  deal_id: number
  price: number
  qty: number
  total: number
  status: 'pending_approval' | 'approved' | 'rejected'
  relative: string
  i_approved: boolean
  they_approved: boolean
  impact: { value_recovered: number | null; scrap_value_total: number; kg_kept_out_of_scrap: number; est_kg_co2e_avoided: number | null; method: string }
}

export type NegotiationView = {
  negotiation_id: number
  side: Side
  counterpart: string
  run_id: string | null
  listing: { listing_id: number; part_number: string; description: string; condition: string; asking_price: number | null; seller_name: string; location: string }
  need: { need_id: number; buyer_name: string; urgency: string; qty: number; downtime_cost_per_day: number }
  qty: number
  status: 'open' | 'agreed' | 'walked_away' | 'round_cap' | 'stopped' | 'approved' | 'rejected'
  rounds_used: number
  max_rounds: number
  next_to_move: Side | null
  final_offer_pending: boolean
  agreed_price: number | null
  offers: Offer[]
  my_limit: { label: string; value: number | null }
  my_notes: { round: number; note: string }[]
  my_blocked: Blocked[]
  deal: Deal | null
  explanation: string | null
  next_best: { listing_id: number; need_id: number; with: string; score: number | null; detail: string } | null
  cost: { cost_usd: number; tokens: number; requests: number }
  live: { status: 'running' | 'done'; queued: boolean; working: string | null; totals: Totals } | null
}

export type NegotiationSummary = {
  negotiation_id: number
  side: Side
  counterpart: string
  part_number: string
  qty: number
  status: NegotiationView['status']
  rounds_used: number
  max_rounds: number
  deal_status: Deal['status'] | null
  price: number | null
  needs_my_approval: boolean
  queued: boolean
  running: boolean
}

export type ReadyPair = {
  listing_id: number
  need_id: number
  side: Side
  with: string
  part_number: string
  description: string
  qty: number
  urgency: string
  asking_price: number | null
  score: number | null
  why: string
}

export type StartInfo = {
  side: Side
  listing_id: number
  need_id: number
  why_it_fits: string | null
  listing: { part_number: string; description: string; condition: string; asking_price: number | null; qty: number; seller_name: string; location: string }
  need: { buyer_name: string; qty: number; urgency: string; downtime_cost_per_day: number; buyer_location: string }
  qty: number
  my_limit: { label: string; value: number | null; set_by: string | null; reason: string | null }
  can_start: boolean
  blocker: string | null
  open_negotiation_id: number | null
}

export const negotiationApi = {
  list: (companyId: number) => request<{ negotiations: NegotiationSummary[]; ready: ReadyPair[] }>(`/api/companies/${companyId}/negotiations`),
  startInfo: (listingId: number, needId: number, companyId: number) =>
    request<StartInfo>(`/api/negotiations/start-info?listing_id=${listingId}&need_id=${needId}&company_id=${companyId}`),
  start: (body: { listing_id: number; need_id: number; company_id: number; my_limit: number | null }) =>
    post<{ negotiation_id: number; run_id: string; queued: boolean }>('/api/negotiations/start', body),
  view: (id: number, companyId: number) => request<NegotiationView>(`/api/negotiations/${id}?company_id=${companyId}`),
  approve: (id: number, companyId: number) => post(`/api/negotiations/${id}/approve`, { company_id: companyId }),
  reject: (id: number, companyId: number, note = '') => post(`/api/negotiations/${id}/reject`, { company_id: companyId, note }),
}

// ------------------------------------------------------------------ private limits + auto-negotiate (human touchpoint 1)

export type Limit = { value: number; set_by: 'suggested' | 'seller' | 'buyer'; reason: string | null }

export type AutoStarted = { listing_id: number; need_id: number; negotiation_id: number; seller: string; buyer: string; queued?: boolean }

export const limitsApi = {
  confirm: (body: { company_id: number; value: number; listing_id: number | null; need_id: number | null }) =>
    post<{ ok: boolean; value: number; started: AutoStarted[] }>('/api/limits', body),
  setAuto: (companyId: number, on: boolean) =>
    post<{ ok: boolean; auto_negotiate: boolean; started: AutoStarted[] }>(`/api/companies/${companyId}/auto-negotiate`, { on }),
}
