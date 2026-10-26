import { useEffect, useRef, useState } from 'react'
import { api, errorMessage, type CompanyProfile, type Need, type RunStatus, type Step } from '../api'
import { featured, FEATURED } from '../demo'
import { condition, money } from '../format'
import { Check } from '../icons'
import { outcomeKind, stepOf, workingText } from '../pipeline'
import { CompanyStrip } from './CompanyStrip'
import { PageBand } from './PageBand'
import { LimitConfirm } from './LimitConfirm'
import { AlertsSent, AutoNegotiated, OutcomeCard, Skeleton } from './Results'

const URGENCIES: { key: Need['urgency']; label: string }[] = [
  { key: 'low', label: 'Low' },
  { key: 'normal', label: 'Normal' },
  { key: 'high', label: 'High' },
  { key: 'line_down', label: 'Line down' },
]

export const urgencyLabel = (u: string) => URGENCIES.find((x) => x.key === u)?.label ?? u

export type NeedForm = { text: string; urgency: Need['urgency'] | null; downtime: string }

export function needFormFor(accountId: number): NeedForm {
  const n = featured(accountId)?.need
  return n
    ? { text: n.text, urgency: n.urgency, downtime: n.downtime ? String(n.downtime) : '' }
    : { text: '', urgency: null, downtime: '' }
}

const toNumber = (v: string) => (v.trim() === '' ? null : Number(v.replace(/[$,\s]/g, '')))

export function BuyPage(props: {
  accountId: number
  profile: CompanyProfile | null
  ready: boolean
  run: RunStatus | null
  onRun: (r: RunStatus | null) => void
  onRunDone: () => void
  form: NeedForm
  onForm: (f: NeedForm) => void
  onStartNegotiation: (t: { listingId: number; needId: number }) => void
  onOpenNegotiations: () => void
}) {
  const { form, onForm, run, onRun, onRunDone } = props
  const sample = featured(props.accountId)?.need
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const timer = useRef<number | undefined>(undefined)
  useEffect(() => () => window.clearTimeout(timer.current), [])

  async function poll(runId: string) {
    try {
      const r = await api.run(runId)
      onRun(r)
      if (r.status === 'running') timer.current = window.setTimeout(() => poll(runId), 600)
      else onRunDone()
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  async function findSurplus() {
    const downtime = toNumber(form.downtime)
    if (!form.text.trim()) return setError('Describe the part you need first.')
    if (downtime !== null && (Number.isNaN(downtime) || downtime < 0)) return setError('Downtime cost must be a number, or leave it empty.')
    setError(null)
    setStarting(true)
    window.clearTimeout(timer.current)
    onRun(null)
    try {
      const { run_id } = await api.startNeedFlow({
        text: form.text,
        buyer_id: props.accountId,
        urgency: form.urgency,
        downtime_cost_per_day: downtime,
      })
      await poll(run_id)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setStarting(false)
    }
  }

  const running = starting || run?.status === 'running'
  const steps = run?.steps ?? []
  const draft = stepOf(steps, 'need_agent')?.draft
  const matching = stepOf(steps, 'matching')
  const alerts = stepOf(steps, 'alerts')
  const posted: Need | undefined = stepOf(steps, 'need')?.need
  // An alerted need moves from open to matched (in code, after alerts are sent).
  const need = posted && alerts?.pairs > 0 ? { ...posted, status: 'matched' as const } : posted
  const result = run?.result
  const kind = result ? outcomeKind(result.outcome) : null
  const stopped = kind && kind !== 'posted' && kind !== 'no_listings'
  const buyers = FEATURED.filter((f) => f.need).map((f) => f.id)
  const isSampleBuyer = buyers.includes(props.accountId)

  return (
    <main className="main side-buy">
      <PageBand side="buy">
        Describe the part or the machine it goes in. Agents check the post, find surplus that fits your equipment, and alert
        you and the seller when there's a strong match.
      </PageBand>
      <CompanyStrip profile={props.profile} role="buyer" />
      {sample ? (
        <p className="try-line">Click Find to post the sample request. {sample.expect}</p>
      ) : (
        <p className="try-line">
          This demo account is mostly a seller. To see the buyer side, switch to Riverbend Foods or Tidewater Dairy in the account
          menu. You can still post a need here.
        </p>
      )}

      <section className="card input">
        <label className="sr-only" htmlFor="need-post">
          Describe the part you need
        </label>
        <textarea
          id="need-post"
          value={form.text}
          onChange={(e) => onForm({ ...form, text: e.target.value })}
          placeholder={'What do you need? e.g. "2x 1756-ENBT for our ControlLogix rack, line down"'}
        />
        <div className="need-fields">
          <div className="field">
            <span className="field-label">Urgency</span>
            <div className="seg" role="radiogroup" aria-label="Urgency">
              {URGENCIES.map((u) => (
                <button
                  key={u.key}
                  role="radio"
                  aria-checked={form.urgency === u.key}
                  className={`seg-btn ${form.urgency === u.key ? 'on' : ''}`}
                  onClick={() => onForm({ ...form, urgency: form.urgency === u.key ? null : u.key })}
                >
                  {u.label}
                </button>
              ))}
            </div>
            <span className="field-help">Leave unselected to let the agent read it from your post.</span>
          </div>
          <label className="field">
            <span className="field-label">Downtime cost per day</span>
            <span className="money-input">
              <span>$</span>
              <input
                inputMode="decimal"
                value={form.downtime}
                onChange={(e) => onForm({ ...form, downtime: e.target.value })}
                placeholder="optional"
              />
            </span>
            <span className="field-help">Shown to sellers: it explains your urgency. It also shapes your suggested budget.</span>
          </label>
        </div>
        <div className="controls">
          <span />
          <div className="actions">
            <span className="small muted posting-as">
              Posting as <b>{props.profile?.name ?? '…'}</b>
            </span>
            <button className="btn primary" onClick={findSurplus} disabled={running || !props.ready}>
              {!props.ready ? 'Starting up…' : running ? 'Working…' : 'Find'}
            </button>
          </div>
        </div>
        {error && <p className="form-error">{error}</p>}
      </section>

      {!run && !running && <MyNeeds needs={props.profile?.open_needs ?? []} sampleBuyer={isSampleBuyer} />}

      {run && (
        <>
          {need && <NeedCard need={need} />}
          {need && stepOf(steps, 'save')?.budget && (
            <LimitConfirm
              side="buyer"
              limit={stepOf(steps, 'save')?.budget}
              companyId={props.accountId}
              needId={need.need_id}
              autoOn={!!props.profile?.auto_negotiate}
              waitingWith={(stepOf(steps, 'auto_negotiate')?.waiting ?? []).filter((w: any) => w.waiting_for.includes('buyer')).map((w: any) => w.seller)}
              onOpenNegotiations={props.onOpenNegotiations}
            />
          )}
          {!need && draft && running && <Skeleton text={workingText(run)} />}
          {!need && !draft && running && <Skeleton text={workingText(run)} />}
          {result && stopped && (
            <OutcomeCard
              kind={kind!}
              outcome={result.outcome}
              rules={stepOf(steps, 'prescreen')?.status === 'blocked' ? ['injection_pattern'] : undefined}
              reasons={stepOf(steps, 'compliance')?.reasons}
              subject="need"
            />
          )}
          {!stopped && need && (matching ? (
            <ListingMatches matching={matching} onStart={(listingId) => props.onStartNegotiation({ listingId, needId: need.need_id })} />
          ) : (
            running && <Skeleton text={workingText(run)} />
          ))}
          {alerts && <AlertsSent alerts={alerts} />}
          {stepOf(steps, 'auto_negotiate') && <AutoNegotiated step={stepOf(steps, 'auto_negotiate')!} side="buyer" onOpen={props.onOpenNegotiations} />}
        </>
      )}
    </main>
  )
}

function MyNeeds({ needs, sampleBuyer }: { needs: Need[]; sampleBuyer: boolean }) {
  if (!needs.length)
    return (
      <div className="empty section">
        {sampleBuyer
          ? 'Your results appear here: the structured need, surplus that fits your machine, and the alerts sent.'
          : 'No open needs for this account yet. Post one above, and matching surplus appears here.'}
      </div>
    )
  return (
    <section className="card section">
      <div className="row">
        <h2>Your open needs</h2>
        <span className="small muted push">Matching runs again whenever a new listing is posted</span>
      </div>
      <div className="need-list">
        {needs.map((n) => (
          <div className="need-row" key={n.need_id}>
            <span className="partno small-partno">{n.part_number ?? `${n.family} · ${n.platform}`}</span>
            <span className="muted small">
              Need #{n.need_id} · {n.qty} unit{n.qty > 1 ? 's' : ''} · {urgencyLabel(n.urgency)}
              {n.downtime_cost_per_day ? ` · ${money(n.downtime_cost_per_day)}/day downtime` : ''}
            </span>
            <span className={`life push ${n.status}`}>{n.status === 'matched' ? 'Matched' : 'Open'}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

function NeedCard({ need }: { need: Need }) {
  return (
    <section className="card section key">
      <div className="row">
        <h2>Your need</h2>
        <span className="push">
          <span className="status pass">
            <Check />
            Compliance passed
          </span>
        </span>
      </div>
      <div className="row wrap listing-head">
        <span className="partno">{need.part_number ?? need.family ?? 'Part'}</span>
        <span className="muted">
          Need #{need.need_id} · for {need.platform ?? 'your equipment'}
        </span>
        <span className={`life ${need.status}`}>{need.status === 'matched' ? 'Matched' : 'Open'}</span>
      </div>
      <dl className="specs">
        <div className="spec">
          <dt>Quantity</dt>
          <dd>{need.qty} units</dd>
        </div>
        <div className="spec">
          <dt>Urgency</dt>
          <dd>{urgencyLabel(need.urgency)}</dd>
        </div>
        <div className="spec">
          <dt>Downtime cost</dt>
          <dd>{need.downtime_cost_per_day ? `${money(need.downtime_cost_per_day)} / day` : 'Not stated'}</dd>
        </div>
        <div className="spec">
          <dt>Location</dt>
          <dd>{need.buyer_location}</dd>
        </div>
      </dl>
    </section>
  )
}

function ListingMatches({ matching, onStart }: { matching: Step; onStart: (listingId: number) => void }) {
  if (matching.status === 'no_candidates' || !matching.ranked?.length) {
    return (
      <section className="card section key">
        <h2>Surplus that fits</h2>
        <div className="empty">
          No listing fits this need yet, so the matching agent was skipped (no AI call, no cost). Your need is posted, and you
          and the seller get an alert as soon as matching surplus is listed.
        </div>
      </section>
    )
  }
  return (
    <section className="card section key">
      <div className="row">
        <h2>Surplus that fits</h2>
        <span className="small muted">
          {matching.ranked.length} of {matching.candidates} compatible listing{matching.candidates > 1 ? 's' : ''} · same matching
          agent as sellers use
        </span>
      </div>
      <div className={`check-note ${matching.method === 'rules_fallback' ? 'fallback' : ''}`}>
        <Check />
        {matching.method === 'rules_fallback'
          ? "Ranked by rules: the AI's answer failed our fact check twice, so these listings are ranked from listing data alone."
          : matching.method === 'agent_retry'
            ? "Fact-checked: the AI's first answer didn't match the listing data, so it was corrected and checked again."
            : "Fact-checked: every reason below matches that listing's part, condition and price."}
      </div>
      <div className="matches">
        {matching.ranked.map((m: any, i: number) => (
          <div className="match listing-match" key={m.listing_id}>
            <span className={`score ${i === 0 ? 'top' : ''}`}>{m.score}</span>
            <div>
              <div className="buyer">
                {m.part_number} <span className="muted small">· {m.seller_name} · {m.location}</span>
              </div>
              <div className="muted small">
                {m.qty} units · {condition(m.condition)} · {m.asking_price ? `ask ${money(m.asking_price)} / unit` : 'price on request'}
              </div>
              <div className="reason">{m.reason}</div>
            </div>
            <button className="btn ghost" onClick={() => onStart(m.listing_id)}>
              Start negotiation
            </button>
          </div>
        ))}
      </div>
    </section>
  )
}
