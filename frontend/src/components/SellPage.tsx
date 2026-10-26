import { useEffect, useRef, useState } from 'react'
import { api, errorMessage, type Company, type CompanyProfile, type RunStatus } from '../api'
import { featured, SCENARIOS, type Scenario } from '../demo'
import { outcomeKind, stepOf, workingText } from '../pipeline'
import { CompanyStrip } from './CompanyStrip'
import { PageBand } from './PageBand'
import { LimitConfirm } from './LimitConfirm'
import { AlertsSent, AutoNegotiated, BuyerMatches, ImpactStrip, ListingCard, OutcomeCard, OutreachEmail, PriceCards, Skeleton } from './Results'

export function SellPage(props: {
  accountId: number
  profile: CompanyProfile | null
  companies: Company[]
  ready: boolean
  run: RunStatus | null
  onRun: (r: RunStatus | null) => void
  onRunDone: () => void
  onStartNegotiation: (t: { listingId: number; needId: number }) => void
  onOpenNegotiations: () => void
  text: string
  onText: (t: string) => void
  onScenario: (s: Scenario) => void
}) {
  const { text, onText: setText } = props
  const tip = featured(props.accountId)?.whatToTry
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const timer = useRef<number | undefined>(undefined)
  const { run, onRun, onRunDone } = props

  useEffect(() => () => window.clearTimeout(timer.current), [])

  async function poll(runId: string) {
    try {
      const r = await api.run(runId, props.accountId)
      onRun(r)
      if (r.status === 'running') timer.current = window.setTimeout(() => poll(runId), 600)
      else onRunDone()
    } catch (e) {
      setError(errorMessage(e))
    }
  }

  async function findBuyers() {
    if (!text.trim()) {
      setError('Paste a description of the part first, or try one of the examples.')
      return
    }
    setError(null)
    setStarting(true)
    window.clearTimeout(timer.current)
    onRun(null)
    try {
      const { run_id } = await api.startSellerFlow(text, props.accountId)
      await poll(run_id)
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setStarting(false)
    }
  }

  const running = starting || run?.status === 'running'
  const steps = run?.steps ?? []
  const draft = stepOf(steps, 'listing_agent')?.draft
  const compliance = stepOf(steps, 'compliance')
  const listingStep = stepOf(steps, 'listing')
  const listing = listingStep?.listing ?? compliance?.listing
  const matching = stepOf(steps, 'matching')
  const pricing = stepOf(steps, 'pricing')
  const impact = stepOf(steps, 'impact')
  const outreach = stepOf(steps, 'outreach')
  const alerts = stepOf(steps, 'alerts')
  const result = run?.result
  const kind = result ? outcomeKind(result.outcome) : null
  const stopped = kind && kind !== 'listed' && kind !== 'no_buyers'
  const listingStatus =
    kind === 'blocked' || kind === 'flagged' ? 'blocked' : kind === 'review' ? 'review' : listing && !stopped ? 'passed' : 'pending'
  const prescreenBlocked = stepOf(steps, 'prescreen')?.status === 'blocked'

  return (
    <main className="main side-sell">
      <PageBand side="sell">
        Paste what you have. Agents identify the part, check it's safe to sell, find plants that run it, and suggest a price.
      </PageBand>
      <CompanyStrip profile={props.profile} role="seller" />
      {tip && <p className="try-line">{tip}</p>}

      <section className="card input">
        <label className="sr-only" htmlFor="post">
          Describe the part
        </label>
        <textarea
          id="post"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={'Describe a part you no longer need, e.g. "3x CPU 315-2DP pulled working, ~$1425 ea", or pick an example below.'}
        />
        <div className="controls">
          <div className="chips">
          <span className="small muted">Try:</span>
          {SCENARIOS.map((sc) => (
            <button
              key={sc.label}
              className="chip"
              title={sc.accountName ? `Signs in as ${sc.accountName} and fills in its post` : 'A prompt-injection attack, to test the defenses'}
              onClick={() => props.onScenario(sc)}
            >
              {sc.label}
              <span className="chip-sub">{sc.accountName ? ` · as ${sc.accountName}` : ' · test'}</span>
            </button>
          ))}
          </div>
          <div className="actions">
          <span className="small muted posting-as">
            Posting as <b>{props.profile?.name ?? '…'}</b>
          </span>
          <button className="btn primary" onClick={findBuyers} disabled={running || !props.ready}>
            {!props.ready ? 'Starting up…' : running ? 'Working…' : 'Find buyers'}
          </button>
          </div>
        </div>
        {error && <p className="form-error">{error}</p>}
      </section>

      {!run && !running && (
        <div className="empty section">
          Your results appear here: the cleaned-up listing, a compliance check, the plants that run this part, a suggested price,
          and a ready-to-send email.
        </div>
      )}

      {run && (
        <>
          {(draft || listing) && !prescreenBlocked && <ListingCard listing={listing} draft={draft} status={listingStatus} />}
          {!draft && !listing && running && <Skeleton text={workingText(run)} />}

          {result && stopped && (
            <OutcomeKindCard kind={kind!} outcome={result.outcome} compliance={compliance} prescreen={prescreenBlocked} />
          )}

          {!stopped && (
            <>
              {matching ? (
                <BuyerMatches
                  matching={matching}
                  companies={props.companies}
                  onStart={result && listing?.listing_id ? (needId) => props.onStartNegotiation({ listingId: listing.listing_id, needId }) : undefined}
                />
              ) : running && listing && <Skeleton text={workingText(run)} />}
              {pricing ? <PriceCards pricing={pricing} /> : running && matching && <Skeleton text={workingText(run)} />}
              {impact && <ImpactStrip impact={impact} />}
              {stepOf(steps, 'floor') && listing?.listing_id && (
                <LimitConfirm
                  side="seller"
                  limit={stepOf(steps, 'floor') as any}
                  companyId={props.accountId}
                  listingId={listing.listing_id}
                  autoOn={!!props.profile?.auto_negotiate}
                  waitingWith={(stepOf(steps, 'auto_negotiate')?.waiting ?? []).filter((w: any) => w.waiting_for.includes('seller')).map((w: any) => w.buyer)}
                  onOpenNegotiations={props.onOpenNegotiations}
                />
              )}
              {alerts && <AlertsSent alerts={alerts} />}
              {stepOf(steps, 'auto_negotiate') && (
                <AutoNegotiated step={stepOf(steps, 'auto_negotiate')!} side="seller" onOpen={props.onOpenNegotiations} />
              )}
              {outreach && <OutreachEmail outreach={outreach} />}
            </>
          )}
        </>
      )}
    </main>
  )
}

function OutcomeKindCard(props: { kind: ReturnType<typeof outcomeKind>; outcome: string; compliance?: any; prescreen: boolean }) {
  const rules = props.prescreen ? ['injection_pattern'] : props.compliance?.rules
  return <OutcomeCard kind={props.kind} outcome={props.outcome} rules={rules} reasons={props.compliance?.reasons} />
}
