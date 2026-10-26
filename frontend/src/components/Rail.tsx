import type { RunStatus, Session } from '../api'
import { cost, kg, money, num } from '../format'
import { Ban, Check, Dot, Eye, Leaf, Spinner } from '../icons'
import { railItems } from '../pipeline'
import { InfoTip } from './Results'

function AgentActivity({ run }: { run: RunStatus | null }) {
  const items = railItems(run)
  return (
    <section className="card rail-card">
      <h3>Agent activity</h3>
      {!run && <p className="muted small rail-empty">Steps appear here as agents work. "(code)" means no AI model was used.</p>}
      <ul className="steps">
        {items.map((i) => (
          <li key={i.key} className={`step s-${i.state}`}>
            <span className="step-icon">
              {i.state === 'done' && <Check />}
              {i.state === 'working' && <Spinner />}
              {i.state === 'blocked' && <Ban />}
              {i.state === 'review' && <Eye />}
              {(i.state === 'pending' || i.state === 'skipped') && <Dot />}
            </span>
            <span className="step-label">
              {i.label}
              {i.code && <span className="code-tag"> (code)</span>}
            </span>
            <span className="step-note">{i.state === 'working' ? 'working…' : i.note ?? ''}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function CostMeter({ run, session }: { run: RunStatus | null; session: Session | null }) {
  const t = run?.totals
  const input = t ? t.input_tokens + t.cached_tokens + t.cache_write_tokens : 0
  const cachedPct = t && input > 0 ? Math.round((100 * t.cached_tokens) / input) : 0
  const spent = session?.cost_usd ?? 0
  const budget = session?.budget_usd ?? 2
  const pct = Math.min(100, (100 * spent) / budget)
  return (
    <section className="card rail-card">
      <h3>Cost this run</h3>
      <div className="big">{t ? cost(t.cost_usd) : '$0.00'}</div>
      <div className="kv">
        <span>Tokens</span>
        <span>{num(t?.total_tokens ?? 0)}</span>
      </div>
      <div className="kv">
        <span>Cached</span>
        <span>{t ? `${cachedPct}%` : '—'}</span>
      </div>
      <div className="kv">
        <span>Model requests</span>
        <span>{t?.requests ?? 0}</span>
      </div>
      <div className="kv session">
        <span>Session</span>
        <span>
          {cost(spent)} of {money(budget)}
        </span>
      </div>
      <div className="bar" aria-label={`Session budget ${pct.toFixed(1)}% used`}>
        <i style={{ width: `${Math.max(pct, 0.5)}%` }} className={pct > 80 ? 'hot' : ''} />
      </div>
    </section>
  )
}

function SessionImpact({ session }: { session: Session | null }) {
  const i = session?.impact
  return (
    <section className="card rail-card impactbox">
      <h3>
        <Leaf />
        Impact this session
      </h3>
      {!i || i.listings === 0 ? (
        <p className="small teal-muted">List a part to see the value recovered and the emissions avoided.</p>
      ) : (
        <>
          <div className="kv">
            <span>Value recovered</span>
            <b>{money(i.value_recovered)}</b>
          </div>
          <div className="kv">
            <span>vs. scrap value</span>
            <span>{money(i.scrap_value)}</span>
          </div>
          <div className="kv">
            <span>Kept out of scrap</span>
            <span>{kg(i.kg_kept_out_of_scrap)}</span>
          </div>
          <div className="kv">
            <span>CO2e avoided</span>
            <span>
              est. {kg(i.est_kg_co2e_avoided)} <InfoTip text={i.method ?? ''} />
            </span>
          </div>
          {i.est_hazardous_disposal_avoided > 0 && (
            <div className="kv">
              <span>Hazardous disposal avoided</span>
              <span>est. {money(i.est_hazardous_disposal_avoided)}</span>
            </div>
          )}
          <p className="small teal-muted">
            {i.listings} listing{i.listings > 1 ? 's' : ''}
            {i.placeholder_factors && ' · placeholder factors'}
          </p>
        </>
      )}
    </section>
  )
}

export function Rail(props: { run: RunStatus | null; session: Session | null }) {
  return (
    <aside className="rail">
      <AgentActivity run={props.run} />
      <CostMeter run={props.run} session={props.session} />
      <SessionImpact session={props.session} />
    </aside>
  )
}
