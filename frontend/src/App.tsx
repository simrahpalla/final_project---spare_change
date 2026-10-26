import { useEffect, useState } from 'react'
import { api, type Health, type LlmCheck } from './api'

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [offline, setOffline] = useState(false)
  const [check, setCheck] = useState<LlmCheck | null>(null)
  const [checking, setChecking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Poll health until the marketplace tools (MCP servers) finish starting, then stop polling.
  useEffect(() => {
    let stop = false
    let timer: number | undefined
    const tick = () =>
      api
        .health()
        .then((h) => {
          if (stop) return
          setHealth(h)
          setOffline(false)
          if (h.mcp?.status === 'starting') timer = window.setTimeout(tick, 1500)
        })
        .catch(() => {
          if (stop) return
          setOffline(true)
          timer = window.setTimeout(tick, 3000)
        })
    tick()
    return () => {
      stop = true
      window.clearTimeout(timer)
    }
  }, [])

  async function runCheck() {
    setChecking(true)
    setError(null)
    try {
      setCheck(await api.llmCheck())
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setChecking(false)
    }
  }

  const pill = offline
    ? { cls: 'pill bad', text: 'Backend offline' }
    : !health
      ? { cls: 'pill', text: 'Connecting…' }
      : !health.key_found
        ? { cls: 'pill bad', text: 'PORTKEY_API_KEY not found' }
        : health.mcp?.status === 'starting'
          ? { cls: 'pill', text: 'Starting up… loading marketplace tools' }
          : health.mcp?.status === 'failed'
            ? { cls: 'pill bad', text: `Tools failed to start: ${health.mcp.error ?? 'unknown error'}` }
            : { cls: 'pill good', text: `${health.model} · key from ${health.key_source} · tools ready` }

  return (
    <div className="page">
      <header className="header">
        <div className="brand">
          <span className="mark">SX</span>
          <div>
            <h1>Surplus Exchange</h1>
            <p className="sub">Industrial surplus, matched and negotiated by AI agents</p>
          </div>
        </div>
        <span className={pill.cls}>{pill.text}</span>
      </header>

      <main className="main">
        <section className="card">
          <h2>Setup check</h2>
          <p className="muted">
            One small call to <code>{health?.model ?? 'gpt-6-luna'}</code> through Portkey, to confirm the key and model
            work. Tokens and cost are shown so every run is measured.
          </p>
          <button className="primary" onClick={runCheck} disabled={checking || offline}>
            {checking ? 'Calling the model…' : 'Test model connection'}
          </button>
          {error && <p className="error">{error}</p>}
          {check && (
            <div className="result">
              <p className="reply">“{check.reply}”</p>
              <dl className="stats">
                <div><dt>Input</dt><dd>{check.input_tokens}</dd></div>
                <div><dt>Cached</dt><dd>{check.cached_tokens}</dd></div>
                <div><dt>Output</dt><dd>{check.output_tokens}</dd></div>
                <div><dt>Cost</dt><dd>${check.cost_usd.toFixed(6)}</dd></div>
              </dl>
              <p className="muted small">Run {check.run_id} · logged to the audit trail</p>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
