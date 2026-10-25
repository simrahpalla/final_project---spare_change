// Thin client for the FastAPI backend (backend/main.py). Same origin, so no base URL. No API keys live here.

export type Health = {
  ok: boolean
  model: string
  key_found: boolean
  key_source: string
  frontend_built: boolean
}

export type LlmCheck = {
  run_id: string
  model: string
  reply: string
  requests: number
  input_tokens: number
  cached_tokens: number
  output_tokens: number
  total_tokens: number
  cost_usd: number
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, { ...init, headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) } })
  } catch {
    throw new Error("Can't reach the backend. Is uvicorn running?")
  }
  if (!res.ok) {
    let detail = res.statusText || `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* keep statusText */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<Health>('/api/health'),
  llmCheck: () => request<LlmCheck>('/api/llm-check', { method: 'POST' }),
}
