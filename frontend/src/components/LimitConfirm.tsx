import { useEffect, useState } from 'react'
import { errorMessage, limitsApi, type Limit, type Side } from '../api'
import { money } from '../format'
import { Check, Lock } from '../icons'

// Human touchpoint 1 of 2: the company confirms (or edits) the private limit an agent or code suggested. Only its own
// negotiator agent ever reads it. Touchpoint 2 is approving the deal. Agents do the work in between.
export function LimitConfirm(props: {
  side: Side
  limit: Limit | null | undefined
  companyId: number
  listingId?: number
  needId?: number
  autoOn: boolean
  waitingWith?: string[] // counterparts whose negotiation starts when this limit is confirmed
  onOpenNegotiations: () => void
}) {
  const { side, limit } = props
  const word = side === 'seller' ? 'floor' : 'budget'
  const [value, setValue] = useState(limit?.value != null ? String(limit.value) : '')
  const [confirmed, setConfirmed] = useState(!!limit && limit.set_by !== 'suggested')
  const [editing, setEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [started, setStarted] = useState<{ negotiation_id: number; seller: string; buyer: string; queued?: boolean }[]>([])

  useEffect(() => {
    setValue(limit?.value != null ? String(limit.value) : '')
    setConfirmed(!!limit && limit.set_by !== 'suggested')
  }, [limit?.value, limit?.set_by])

  if (!limit) return null
  const suggested = limit.set_by === 'suggested'

  async function confirm() {
    const v = Number(value.replace(/[$,\s]/g, ''))
    if (!value.trim() || Number.isNaN(v) || v <= 0) return setError(`Enter your ${word} as a price per unit.`)
    setBusy(true)
    setError(null)
    try {
      const r = await limitsApi.confirm({ company_id: props.companyId, value: v, listing_id: props.listingId ?? null, need_id: props.needId ?? null })
      setConfirmed(true)
      setEditing(false)
      setStarted(r.started)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const other = (s: { seller: string; buyer: string }) => (side === 'seller' ? s.buyer : s.seller)
  return (
    <section className={`limit-card section side-${side}`}>
      <div className="limit-head">
        <Lock />
        <b>Your private {word}</b>
        <span className="muted small">Only your agent sees this.</span>
        {confirmed && !editing && (
          <span className="status pass push">
            <Check /> Confirmed
          </span>
        )}
      </div>
      {confirmed && !editing ? (
        <div className="limit-row">
          <span className="limit-value">{money(Number(value))}</span>
          <span className="muted small">per unit · your agent negotiates within it</span>
          <button className="btn ghost push" onClick={() => setEditing(true)}>
            Edit
          </button>
        </div>
      ) : (
        <div className="limit-row">
          <span className="money-input limit-input">
            <span>$</span>
            <input inputMode="decimal" value={value} onChange={(e) => setValue(e.target.value)} aria-label={`Your ${word}`} />
          </span>
          <button className={`btn primary ${side}`} onClick={confirm} disabled={busy}>
            {busy ? 'Saving…' : `Confirm ${word}`}
          </button>
        </div>
      )}
      {suggested && limit.reason && !(confirmed && !editing) && (
        <p className="limit-reason">
          Suggested{side === 'seller' ? ' by the pricing agent' : ''}: {limit.reason}
        </p>
      )}
      {error && <p className="form-error">{error}</p>}
      {!confirmed && !!props.waitingWith?.length && (
        <p className="limit-next">
          Confirm it and your agent starts negotiating with <b>{props.waitingWith.join(', ')}</b> (auto-negotiate is on).
        </p>
      )}
      {started.length > 0 ? (
        <div className="limit-started">
          Your agent started negotiating with <b>{started.map(other).join(', ')}</b>
          {started.some((s) => s.queued) ? ' (queued: it starts when a slot frees up)' : ''}.{' '}
          <button className="linklike" onClick={props.onOpenNegotiations}>
            Watch it on Negotiations
          </button>
        </div>
      ) : (
        confirmed &&
        !editing && (
          <p className="small muted">
            {props.autoOn
              ? 'Auto-negotiate is on: a strong match starts a negotiation by itself once the other side has confirmed its limit too.'
              : 'Auto-negotiate is off: start a negotiation from a match when you are ready.'}
          </p>
        )
      )}
    </section>
  )
}
