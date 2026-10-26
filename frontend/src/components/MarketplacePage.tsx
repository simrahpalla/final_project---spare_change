import { useCallback, useEffect, useState } from 'react'
import { api, errorMessage, type Board } from '../api'
import { condition, kg, money } from '../format'
import { Leaf } from '../icons'
import { InfoTip } from './Results'
import { urgencyLabel } from './BuyPage'

type Sel = { kind: 'listing' | 'need'; id: number } | null

const LISTING_STATUS: Record<string, string> = {
  active: 'Available',
  in_negotiation: 'In negotiation',
  pending_deal: 'Deal pending',
}

export function MarketplacePage({ ready, accountId, version }: { ready: boolean; accountId: number; version: number }) {
  const [board, setBoard] = useState<Board | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sel, setSel] = useState<Sel>(null)

  const load = useCallback(async () => {
    if (!ready) return
    try {
      setBoard(await api.marketplace())
      setError(null)
    } catch (e) {
      setError(errorMessage(e))
    }
  }, [ready])

  useEffect(() => {
    load()
  }, [load, version])

  const pairs = board?.pairs ?? []
  const partnersOf = (kind: 'listing' | 'need', id: number) =>
    pairs.filter((p) => (kind === 'listing' ? p.listing_id === id : p.need_id === id)).map((p) => (kind === 'listing' ? p.need_id : p.listing_id))
  const lit = (kind: 'listing' | 'need', id: number) => {
    if (!sel) return ''
    if (sel.kind === kind && sel.id === id) return 'selected'
    if (sel.kind !== kind && partnersOf(sel.kind, sel.id).includes(id)) return 'partner'
    return 'dim'
  }
  const toggle = (kind: 'listing' | 'need', id: number) =>
    setSel(sel && sel.kind === kind && sel.id === id ? null : { kind, id })
  const why = (lid: number, nid: number) => pairs.find((p) => p.listing_id === lid && p.need_id === nid)?.why

  return (
    <main className="main">
      <h1>Marketplace</h1>
      <p className="lede">
        Everything for sale and everything plants want to buy, side by side. Click any item to see what it matches. Prices shown are public
        asks: a buyer's max price and a seller's floor are never on this board.
      </p>

      {error && <div className="banner bad">{error}</div>}
      {!board && !error && <div className="company-strip skel-strip" />}

      {board && (
        <>
          <section className="impact board-impact section">
            <Leaf />
            <div className="board-impact-body">
              <div>
                <b>{board.potential.listings}</b> listings fill a buy request. If they sell at their asks: <b>{money(board.potential.value_recovered)}</b>{' '}
                recovered vs. {money(board.potential.scrap_value)} scrap · <b>{kg(board.potential.kg_kept_out_of_scrap)}</b> kept out of scrap ·
                est. <b>{kg(board.potential.est_kg_co2e_avoided)} CO2e</b> avoided
              </div>
              <div className="small teal-muted">
                Closed deals: {board.impact.deals}
                {board.impact.deals > 0
                  ? ` · ${money(board.impact.value_recovered)} recovered · ${kg(board.impact.est_kg_co2e_avoided)} CO2e avoided`
                  : ' (agent negotiation and approval open in Phase 6)'}{' '}
                · placeholder factors
              </div>
            </div>
            <span className="push">
              <InfoTip text={`${board.impact.method} Potential = ${board.potential.note}.`} />
            </span>
          </section>

          <div className="board">
            <section className="board-col">
              <div className="board-head">
                <h2>For sale</h2>
                <span className="muted small">{board.listings.length} listings</span>
              </div>
              {board.listings.map((l) => {
                const n = partnersOf('listing', l.listing_id)
                const mine = l.seller_id === accountId
                return (
                  <button
                    key={l.listing_id}
                    className={`board-item ${lit('listing', l.listing_id)}`}
                    onClick={() => toggle('listing', l.listing_id)}
                    aria-pressed={sel?.kind === 'listing' && sel.id === l.listing_id}
                  >
                    <div className="board-top">
                      <span className="partno small-partno">{l.part_number}</span>
                      {n.length > 0 && (
                        <span className="match-badge">
                          {n.length} match{n.length > 1 ? 'es' : ''}
                        </span>
                      )}
                    </div>
                    <div className="board-desc">{l.description}</div>
                    <div className="muted small">
                      {l.qty} × {condition(l.condition)} · {l.asking_price ? `${money(l.asking_price)} / unit` : 'price on request'}
                    </div>
                    <div className="muted small">
                      {l.seller_name}
                      {mine && <span className="you-tag">you</span>} · {l.location}
                    </div>
                    {l.status !== 'active' && <span className="life in_negotiation">{LISTING_STATUS[l.status] ?? l.status}</span>}
                    {sel?.kind === 'need' && lit('listing', l.listing_id) === 'partner' && (
                      <div className="pair-why">Fits: {why(l.listing_id, sel.id)}</div>
                    )}
                  </button>
                )
              })}
            </section>

            <section className="board-col">
              <div className="board-head">
                <h2>To buy</h2>
                <span className="muted small">{board.needs.length} requests</span>
              </div>
              {board.needs.map((nd) => {
                const n = partnersOf('need', nd.need_id)
                const mine = nd.buyer_id === accountId
                return (
                  <button
                    key={nd.need_id}
                    className={`board-item ${lit('need', nd.need_id)}`}
                    onClick={() => toggle('need', nd.need_id)}
                    aria-pressed={sel?.kind === 'need' && sel.id === nd.need_id}
                  >
                    <div className="board-top">
                      <span className="partno small-partno">{nd.part_number ?? nd.family}</span>
                      {n.length > 0 ? (
                        <span className="match-badge">
                          {n.length} match{n.length > 1 ? 'es' : ''}
                        </span>
                      ) : (
                        <span className="no-match">no surplus yet</span>
                      )}
                    </div>
                    <div className="board-desc">
                      {nd.qty} unit{nd.qty > 1 ? 's' : ''} for {nd.platform ?? 'general use'}
                    </div>
                    <div className="muted small">
                      <span className={nd.urgency === 'line_down' ? 'urgent' : ''}>{urgencyLabel(nd.urgency)}</span>
                      {nd.downtime_cost_per_day ? ` · ${money(nd.downtime_cost_per_day)}/day downtime` : ''}
                    </div>
                    <div className="muted small">
                      {nd.buyer_name}
                      {mine && <span className="you-tag">you</span>} · {nd.buyer_location}
                    </div>
                    {nd.status === 'matched' && <span className="life matched">Matched</span>}
                    {sel?.kind === 'listing' && lit('need', nd.need_id) === 'partner' && (
                      <div className="pair-why">Fits: {why(sel.id, nd.need_id)}</div>
                    )}
                  </button>
                )
              })}
            </section>
          </div>
        </>
      )}
    </main>
  )
}
