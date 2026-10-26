import { useCallback, useEffect, useRef, useState } from 'react'
import {
  errorMessage,
  negotiationApi,
  type Blocked,
  type CompanyProfile,
  type NegotiationSummary,
  type NegotiationView,
  type Offer,
  type ReadyPair,
  type Side,
  type StartInfo,
} from '../api'
import { featured } from '../demo'
import { condition, kg, money } from '../format'
import { Ban, Check, Leaf, Lock } from '../icons'
import { InfoTip } from './Results'
import { urgencyLabel } from './BuyPage'

export type Target = { listingId: number; needId: number }

const STATUS_TEXT: Record<NegotiationView['status'], string> = {
  open: 'Negotiating',
  agreed: 'Deal: awaiting approval',
  approved: 'Deal closed',
  walked_away: 'No deal: walked away',
  round_cap: 'No deal: round cap',
  stopped: 'Stopped',
  rejected: 'Deal rejected',
}

const sideName = (s: Side) => (s === 'seller' ? 'seller' : 'buyer')
const agentOf = (name: string) => `${name}${name.endsWith('s') ? '’' : '’s'} agent`

export function NegotiationsPage(props: {
  accountId: number
  profile: CompanyProfile | null
  ready: boolean
  target: Target | null
  onTargetDone: () => void
  selected: number | null
  onSelect: (id: number | null) => void
  onView: (v: NegotiationView | null) => void
  onStart: (t: Target) => void
  onChanged: () => void
}) {
  const { accountId, ready, selected, onSelect } = props
  const [list, setList] = useState<{ negotiations: NegotiationSummary[]; ready: ReadyPair[] } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const tip = featured(accountId)?.negotiate

  const loadList = useCallback(async () => {
    if (!ready) return
    try {
      setList(await negotiationApi.list(accountId))
    } catch (e) {
      setError(errorMessage(e))
    }
  }, [ready, accountId])

  useEffect(() => {
    loadList()
  }, [loadList, selected, props.target])

  // Keep the list fresh while anything of this company is running.
  useEffect(() => {
    if (!list?.negotiations.some((n) => n.running || n.status === 'open')) return
    const t = window.setTimeout(loadList, 2000)
    return () => window.clearTimeout(t)
  }, [list, loadList])

  const approvals = list?.negotiations.filter((n) => n.needs_my_approval) ?? []
  const active = list?.negotiations.filter((n) => !n.needs_my_approval && (n.status === 'open' || n.status === 'agreed')) ?? []
  const closed = list?.negotiations.filter((n) => !n.needs_my_approval && n.status !== 'open' && n.status !== 'agreed') ?? []

  return (
    <main className="main side-neg">
      <header className="band">
        <div className="eyebrow neg-eyebrow">Negotiations</div>
        <h1 className="tagline">Your agent negotiates. You decide.</h1>
        <p className="lede">
          Your agent bargains within your private limit, which only it can see. The other side's limit stays hidden from you,
          too. No deal closes until both companies approve it.
        </p>
      </header>
      {tip && <p className="try-line">{tip}</p>}
      {error && <p className="form-error">{error}</p>}

      <div className="neg-layout">
        <aside className="neg-list">
          <ListGroup title="Needs your approval" items={approvals} selected={selected} onSelect={onSelect} />
          <ListGroup title="In progress" items={active} selected={selected} onSelect={onSelect} />
          <div className="neg-group">
            <div className="neg-group-title">Ready to start</div>
            {list && list.ready.length === 0 && <div className="neg-empty">No open matches for your listings or requests right now.</div>}
            {list?.ready.map((p) => (
              <button
                key={`${p.listing_id}-${p.need_id}`}
                className={`neg-item ${props.target?.listingId === p.listing_id && props.target?.needId === p.need_id ? 'on' : ''}`}
                onClick={() => props.onStart({ listingId: p.listing_id, needId: p.need_id })}
              >
                <span className="neg-item-top">
                  <span className="partno small-partno">{p.part_number}</span>
                  {p.score !== null && <span className="match-badge">{p.score}</span>}
                </span>
                <span className="neg-item-sub">
                  {p.side === 'seller' ? 'Sell to' : 'Buy from'} {p.with}
                </span>
                <span className="muted small">
                  {p.qty} unit{p.qty > 1 ? 's' : ''} · {urgencyLabel(p.urgency)}
                </span>
              </button>
            ))}
          </div>
          <ListGroup title="Closed" items={closed} selected={selected} onSelect={onSelect} />
        </aside>

        <section className="neg-detail">
          {props.target ? (
            <StartPanel
              key={`${props.target.listingId}-${props.target.needId}-${accountId}`}
              accountId={accountId}
              target={props.target}
              onCancel={props.onTargetDone}
              onStarted={(id) => {
                props.onTargetDone()
                onSelect(id)
                props.onChanged()
              }}
            />
          ) : selected ? (
            <LiveView
              key={`${selected}-${accountId}`}
              id={selected}
              accountId={accountId}
              onView={props.onView}
              onStart={props.onStart}
              onChanged={() => {
                loadList()
                props.onChanged()
              }}
            />
          ) : (
            <div className="empty">
              Pick a negotiation on the left, or start one from <b>Ready to start</b>. You can also start from a match alert (the
              bell) or from your matches on Sell and Buy.
            </div>
          )}
        </section>
      </div>
    </main>
  )
}

function ListGroup(props: { title: string; items: NegotiationSummary[]; selected: number | null; onSelect: (id: number) => void }) {
  if (!props.items.length) return null
  return (
    <div className="neg-group">
      <div className="neg-group-title">{props.title}</div>
      {props.items.map((n) => (
        <button key={n.negotiation_id} className={`neg-item ${props.selected === n.negotiation_id ? 'on' : ''}`} onClick={() => props.onSelect(n.negotiation_id)}>
          <span className="neg-item-top">
            <span className="partno small-partno">{n.part_number}</span>
            <span className={`life ${n.needs_my_approval ? 'act' : ''}`}>
              {n.queued ? 'Queued' : n.needs_my_approval ? 'Approve' : n.status === 'open' ? `Round ${n.rounds_used}/${n.max_rounds}` : STATUS_TEXT[n.status].split(':')[0]}
            </span>
          </span>
          <span className="neg-item-sub">
            {n.side === 'seller' ? 'Selling to' : 'Buying from'} {n.counterpart}
          </span>
          {n.price !== null && <span className="muted small">{money(n.price)} / unit × {n.qty}</span>}
        </button>
      ))}
    </div>
  )
}

// ------------------------------------------------------------------ start

function StartPanel(props: { accountId: number; target: Target; onCancel: () => void; onStarted: (id: number) => void }) {
  const [info, setInfo] = useState<StartInfo | null>(null)
  const [limit, setLimit] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    negotiationApi
      .startInfo(props.target.listingId, props.target.needId, props.accountId)
      .then((i) => {
        setInfo(i)
        setLimit(i.my_limit.value !== null ? String(i.my_limit.value) : '')
      })
      .catch((e) => setError(errorMessage(e)))
  }, [props.target, props.accountId])

  async function start() {
    const v = Number(limit.replace(/[$,\s]/g, ''))
    if (!limit.trim() || Number.isNaN(v) || v <= 0) return setError(`Enter your ${info?.side === 'seller' ? 'floor' : 'budget'} as a price per unit.`)
    setBusy(true)
    setError(null)
    try {
      const r = await negotiationApi.start({ listing_id: props.target.listingId, need_id: props.target.needId, company_id: props.accountId, my_limit: v })
      props.onStarted(r.negotiation_id)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  if (!info) return <div className="card section">{error ? <p className="form-error">{error}</p> : <div className="working-line"><span className="spinner" />Loading…</div>}</div>
  const seller = info.side === 'seller'
  return (
    <section className={`card key neg-start side-${info.side}`}>
      <div className="row">
        <h2>Start a negotiation</h2>
        <span className={`you-are ${info.side}`}>You're the {sideName(info.side)}</span>
      </div>
      <div className="start-pair">
        <div>
          <div className="muted small">Part</div>
          <div className="partno small-partno">{info.listing.part_number}</div>
          <div className="small">{info.listing.description}</div>
          <div className="muted small">
            {condition(info.listing.condition)} · {info.listing.asking_price ? `public ask ${money(info.listing.asking_price)} / unit` : 'no public ask'}
          </div>
        </div>
        <div>
          <div className="muted small">{seller ? 'Buyer' : 'Seller'}</div>
          <div className="start-with">{seller ? info.need.buyer_name : info.listing.seller_name}</div>
          <div className="muted small">
            {seller
              ? `${info.need.buyer_location} · needs ${info.need.qty} · ${urgencyLabel(info.need.urgency)}`
              : `${info.listing.location} · has ${info.listing.qty}`}
          </div>
        </div>
        <div>
          <div className="muted small">Quantity</div>
          <div className="start-with">{info.qty} unit{info.qty === 1 ? '' : 's'}</div>
          <div className="muted small">locked for this negotiation</div>
        </div>
      </div>
      <label className="field limit-field">
        <span className="field-label">
          <Lock /> {seller ? 'Your floor: the lowest price per unit you will accept' : 'Your budget: the most you will pay per unit'}
        </span>
        <span className="money-input">
          <span>$</span>
          <input inputMode="decimal" value={limit} onChange={(e) => setLimit(e.target.value)} aria-label={info.my_limit.label} />
        </span>
        <span className="field-help">
          <b>Only your agent sees this.</b> The other side never does, and you never see theirs.
          {info.my_limit.set_by === 'suggested' && ' Pre-filled with the pricing agent\'s suggested floor.'}
        </span>
      </label>
      {info.blocker && <div className="outcome neutral section">{info.blocker}</div>}
      {error && <p className="form-error">{error}</p>}
      <div className="controls">
        <span className="small muted">Your agent moves within this limit. The rules in code block any offer outside it.</span>
        <div className="actions">
          <button className="btn ghost" onClick={props.onCancel}>
            Cancel
          </button>
          <button className={`btn primary ${info.side}`} onClick={start} disabled={busy || !info.can_start}>
            {busy ? 'Starting…' : 'Start negotiation'}
          </button>
        </div>
      </div>
    </section>
  )
}

// ------------------------------------------------------------------ live view

type Item = { kind: 'offer'; o: Offer; t: string } | { kind: 'blocked'; b: Blocked; t: string }

function LiveView(props: { id: number; accountId: number; onView: (v: NegotiationView | null) => void; onStart: (t: Target) => void; onChanged: () => void }) {
  const [v, setV] = useState<NegotiationView | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [deciding, setDeciding] = useState(false)
  const timer = useRef<number | undefined>(undefined)
  const { onView } = props

  const load = useCallback(async () => {
    try {
      const nv = await negotiationApi.view(props.id, props.accountId)
      setV(nv)
      onView(nv)
      setError(null)
      const live = nv.live?.status === 'running' || nv.status === 'open'
      timer.current = window.setTimeout(load, live ? 900 : 4000)
    } catch (e) {
      setError(errorMessage(e))
    }
  }, [props.id, props.accountId, onView])

  useEffect(() => {
    load()
    return () => {
      window.clearTimeout(timer.current)
      onView(null)
    }
  }, [load, onView])

  async function decide(approve: boolean) {
    if (!v) return
    if (!approve && !window.confirm('Reject this deal? The negotiation closes and the listing goes back on the market.')) return
    setDeciding(true)
    try {
      await (approve ? negotiationApi.approve(v.negotiation_id, props.accountId) : negotiationApi.reject(v.negotiation_id, props.accountId))
      window.clearTimeout(timer.current)
      await load()
      props.onChanged()
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setDeciding(false)
    }
  }

  if (!v) return <div className="card section">{error ? <p className="form-error">{error}</p> : <div className="working-line"><span className="spinner" />Loading…</div>}</div>

  const items: Item[] = [
    ...v.offers.map((o) => ({ kind: 'offer' as const, o, t: o.created_at })),
    ...v.my_blocked.map((b) => ({ kind: 'blocked' as const, b, t: b.at })),
  ].sort((a, b) => (a.t < b.t ? -1 : a.t > b.t ? 1 : a.kind === 'blocked' ? -1 : 1))
  const note = (round: number) => v.my_notes.find((n) => n.round === round)?.note
  const queued = v.live?.queued
  const working = v.status === 'open' && v.live?.status === 'running' && !queued
  const names: Record<Side, string> = { seller: v.listing.seller_name, buyer: v.need.buyer_name }
  const round = Math.min(Math.max(v.rounds_used, 1), v.max_rounds)

  return (
    <div className={`neg-live side-${v.side}`}>
      <section className="card key">
        <div className="row wrap">
          <span className="partno">{v.listing.part_number}</span>
          <span className="muted">{v.listing.description}</span>
          <span className={`you-are ${v.side} push`}>You're the {sideName(v.side)}</span>
        </div>
        <div className="row wrap neg-meta">
          <span>
            {v.side === 'seller' ? 'Selling to' : 'Buying from'} <b>{v.counterpart}</b> · {v.qty} unit{v.qty > 1 ? 's' : ''}
            {v.listing.asking_price ? ` · public ask ${money(v.listing.asking_price)}` : ''}
          </span>
          <span className="round-counter push">
            Round {round} of {v.max_rounds}
          </span>
          <span className={`life ${v.status}`}>{queued ? 'Queued' : STATUS_TEXT[v.status]}</span>
        </div>
        <div className="private">
          <Lock /> {v.my_limit.label}: <b>{money(v.my_limit.value)}</b> per unit · only your agent sees this
        </div>
      </section>

      <PriceChart v={v} />

      <section className="card section chat">
        {queued && (
          <div className="queued-line">
            <span className="spinner" /> Queued: three negotiations are already running. Yours starts as soon as one finishes; your
            units are already reserved.
          </div>
        )}
        {items.length === 0 && !queued && <div className="muted small">The seller's agent moves first…</div>}
        {items.map((it, i) =>
          it.kind === 'offer' ? (
            <div key={`o${i}`} className={`bubble-row ${it.o.from_side}`}>
              <div className={`bubble ${it.o.from_side} ${it.o.from_side === v.side ? 'mine' : ''}`}>
                <div className="bubble-head">
                  {it.o.from_side === v.side ? 'Your agent' : agentOf(names[it.o.from_side])} · round {it.o.round}
                </div>
                <div className="bubble-price">
                  {it.o.action === 'offer' && <>Offers {money(it.o.price)} / unit</>}
                  {it.o.action === 'accept' && <>Accepts {money(it.o.price)} / unit</>}
                  {it.o.action === 'walk_away' && <>Walks away</>}
                </div>
                {it.o.message_untrusted && <div className="bubble-msg">“{it.o.message_untrusted}”</div>}
              </div>
              {it.o.from_side === v.side && note(it.o.round) && (
                <div className="bubble-note">
                  <Lock /> Only you see this: {note(it.o.round)}
                </div>
              )}
            </div>
          ) : (
            <div key={`b${i}`} className={`bubble-row ${v.side}`}>
              <div className="bubble blocked">
                <Ban /> {it.b.text}
                <div className="bubble-note-inline">Only you see this. The other side was not told.</div>
              </div>
            </div>
          ),
        )}
        {working && v.next_to_move && (
          <div className={`bubble-row ${v.next_to_move}`}>
            <div className={`bubble thinking ${v.next_to_move}`}>
              <span className="spinner" /> {v.next_to_move === v.side ? 'Your agent' : agentOf(names[v.next_to_move])} is deciding…
            </div>
          </div>
        )}
      </section>

      <Outcome v={v} deciding={deciding} onDecide={decide} onStart={props.onStart} />
      {error && <p className="form-error">{error}</p>}
    </div>
  )
}

function Outcome(props: { v: NegotiationView; deciding: boolean; onDecide: (approve: boolean) => void; onStart: (t: Target) => void }) {
  const { v } = props
  const d = v.deal
  if (d) {
    const closed = d.status === 'approved'
    return (
      <section className={`card section key deal-card ${d.status}`}>
        <div className="row">
          <h2>{closed ? 'Deal closed' : d.status === 'rejected' ? 'Deal rejected' : 'Deal reached: waiting for approval'}</h2>
          {closed && (
            <span className="status pass push">
              <Check /> Both companies approved
            </span>
          )}
        </div>
        <div className="deal-main">
          <span className="deal-price">{money(d.price)}</span>
          <span className="muted"> per unit × {d.qty} = {money(d.total)}</span>
        </div>
        <div className="deal-rel">
          Closed at {money(d.price)}, {d.relative}.
        </div>
        <div className="impact deal-impact">
          <Leaf />
          <span>
            Recovers <b>{money(d.impact.value_recovered)}</b> vs. {money(d.impact.scrap_value_total)} scrap · <b>{kg(d.impact.kg_kept_out_of_scrap)}</b> kept out
            of scrap · est. <b>{kg(d.impact.est_kg_co2e_avoided)} CO2e</b> avoided
          </span>
          <span className="push">
            <InfoTip text={d.impact.method} />
          </span>
        </div>
        {d.status === 'pending_approval' && (
          <div className="approvals">
            <div className="approval-state">
              <span className={d.i_approved ? 'ok' : ''}>{d.i_approved ? '✓ You approved' : 'Your approval: needed'}</span>
              <span className={d.they_approved ? 'ok' : ''}>
                {v.counterpart}: {d.they_approved ? '✓ approved' : 'waiting'}
              </span>
            </div>
            {!d.i_approved && (
              <div className="actions">
                <button className="btn ghost" disabled={props.deciding} onClick={() => props.onDecide(false)}>
                  Reject
                </button>
                <button className={`btn primary ${v.side}`} disabled={props.deciding} onClick={() => props.onDecide(true)}>
                  Approve deal
                </button>
              </div>
            )}
            <p className="small muted">A person at each company approves its own side. Nothing is sold until both approve.</p>
          </div>
        )}
        {closed && (
          <p className="small muted">
            {v.side === 'seller' ? 'Your listing is updated (sold out, or the remaining units stay on the market).' : 'Your request is marked filled.'} Match alerts about it are closed.
          </p>
        )}
      </section>
    )
  }
  if (!v.explanation) return null
  return (
    <section className="outcome neutral section">
      <div className="outcome-title">No deal</div>
      <p>{v.explanation}</p>
      {v.next_best ? (
        <div className="next-best">
          <span>
            Next best match: <b>{v.next_best.with}</b> · {v.next_best.detail}
            {v.next_best.score ? ` · score ${v.next_best.score}` : ''}
          </span>
          <button className={`btn primary ${v.side}`} onClick={() => props.onStart({ listingId: v.next_best!.listing_id, needId: v.next_best!.need_id })}>
            Start negotiation
          </button>
        </div>
      ) : (
        <p className="small muted">No other match right now. You'll get an alert when one appears.</p>
      )}
    </section>
  )
}

// ------------------------------------------------------------------ chart: offers by round + ONLY the viewer's own limit

function PriceChart({ v }: { v: NegotiationView }) {
  const W = 640, H = 170, L = 56, R = 16, T = 14, B = 26
  const seller = v.offers.filter((o) => o.from_side === 'seller' && o.action !== 'walk_away')
  const buyer = v.offers.filter((o) => o.from_side === 'buyer' && o.action !== 'walk_away')
  const prices = [...v.offers.filter((o) => o.action !== 'walk_away').map((o) => o.price), v.my_limit.value ?? NaN, v.listing.asking_price ?? NaN].filter(
    (x) => Number.isFinite(x),
  ) as number[]
  if (!prices.length)
    return (
      <section className="card section chart-card">
        <h2>Price by round</h2>
        <div className="muted small">Offers appear here round by round.</div>
      </section>
    )
  let lo = Math.min(...prices), hi = Math.max(...prices)
  const pad = Math.max((hi - lo) * 0.15, hi * 0.05, 1)
  lo = Math.max(0, lo - pad)
  hi = hi + pad
  const x = (r: number) => L + ((r - 1) / Math.max(v.max_rounds - 1, 1)) * (W - L - R)
  const y = (p: number) => T + (1 - (p - lo) / (hi - lo)) * (H - T - B)
  const path = (os: Offer[]) => os.map((o, i) => `${i ? 'L' : 'M'}${x(o.round).toFixed(1)},${y(o.price).toFixed(1)}`).join(' ')
  const ticks = [lo, (lo + hi) / 2, hi]
  return (
    <section className="card section chart-card">
      <div className="row">
        <h2>Price by round</h2>
        <span className="chart-legend push">
          <span className="lg seller">Seller offers</span>
          <span className="lg buyer">Buyer offers</span>
          <span className={`lg limit ${v.side}`}>{v.my_limit.label}</span>
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img" aria-label={`Offers by round and ${v.my_limit.label.toLowerCase()}`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} className="grid" />
            <text x={L - 6} y={y(t) + 4} className="tick" textAnchor="end">
              {money(t)}
            </text>
          </g>
        ))}
        {Array.from({ length: v.max_rounds }, (_, i) => (
          <text key={i} x={x(i + 1)} y={H - 8} className="tick" textAnchor="middle">
            {i + 1}
          </text>
        ))}
        {v.my_limit.value !== null && (
          <g>
            <line x1={L} x2={W - R} y1={y(v.my_limit.value)} y2={y(v.my_limit.value)} className={`limit-line ${v.side}`} />
            <text x={W - R} y={y(v.my_limit.value) - 5} textAnchor="end" className={`limit-label ${v.side}`}>
              {v.my_limit.label} {money(v.my_limit.value)}
            </text>
          </g>
        )}
        <path d={path(seller)} className="series seller" />
        <path d={path(buyer)} className="series buyer" />
        {v.offers
          .filter((o) => o.action !== 'walk_away')
          .map((o, i) => (
            <circle key={i} cx={x(o.round)} cy={y(o.price)} r={o.action === 'accept' ? 6 : 4} className={`pt ${o.from_side} ${o.action}`} />
          ))}
      </svg>
    </section>
  )
}
