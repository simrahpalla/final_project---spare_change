import { useState, type ReactNode } from 'react'
import type { Company, Step } from '../api'
import { condition, date, kg, money } from '../format'
import { Ban, Check, Copy, Eye, Help, Info, Leaf, Lock } from '../icons'
import type { OutcomeKind } from '../pipeline'

export function InfoTip({ text }: { text: string }) {
  if (!text) return null
  return (
    <span className="tip" tabIndex={0} aria-label={text}>
      <Info />
      <span className="tip-body" role="tooltip">
        {text}
      </span>
    </span>
  )
}

// ------------------------------------------------------------------ listing

export function ListingCard({ listing, draft, status }: { listing?: any; draft?: any; status: 'passed' | 'blocked' | 'review' | 'flagged' | 'pending' }) {
  const part = listing?.part_number ?? draft?.part_number
  const badge =
    status === 'passed' ? (
      <span className="status pass">
        <Check />
        Compliance passed
      </span>
    ) : status === 'blocked' || status === 'flagged' ? (
      <span className="status blocked">
        <Ban />
        Blocked
      </span>
    ) : status === 'review' ? (
      <span className="status neutral">
        <Eye />
        Held for review
      </span>
    ) : null
  return (
    <section className="card section key">
      <div className="row">
        <h2>Listing</h2>
        <span className="push">{badge}</span>
      </div>
      <div className="row wrap listing-head">
        <span className="partno">{part ?? 'Part not identified'}</span>
        {listing && (
          <span className="muted">
            {listing.manufacturer} · {listing.family} · {listing.description}
          </span>
        )}
        {listing?.hazmat && <span className="tag">Hazmat {listing.hazmat_class ? `· ${listing.hazmat_class}` : ''}</span>}
      </div>
      <dl className="specs">
        <div className="spec">
          <dt>Quantity</dt>
          <dd>{listing?.qty ?? draft?.qty ?? '—'} units</dd>
        </div>
        <div className="spec">
          <dt>Condition</dt>
          <dd>{condition(listing?.condition ?? draft?.condition)}</dd>
        </div>
        <div className="spec">
          <dt>Seller's ask</dt>
          <dd>{(listing?.asking_price ?? draft?.asking_price) ? `${money(listing?.asking_price ?? draft?.asking_price)} / unit` : 'Not stated'}</dd>
        </div>
        <div className="spec">
          <dt>Location</dt>
          <dd>{listing?.location ?? '—'}</dd>
        </div>
        <div className="spec">
          <dt>Fits</dt>
          <dd>{listing?.fits_platforms?.length ? listing.fits_platforms.join(', ') : 'General use'}</dd>
        </div>
        {(listing?.expiry_date || draft?.expiry_date || draft?.manufacture_date) && (
          <div className="spec">
            <dt>{listing?.expiry_date || draft?.expiry_date ? 'Expires' : 'Manufactured'}</dt>
            <dd>{date(listing?.expiry_date ?? draft?.expiry_date ?? draft?.manufacture_date)}</dd>
          </div>
        )}
        {listing?.hazmat && (
          <div className="spec">
            <dt>Safety data sheet</dt>
            <dd>{listing.sds_available === 1 ? 'On file' : 'Missing'}</dd>
          </div>
        )}
        {draft?.confidence !== undefined && (
          <div className="spec">
            <dt>Agent confidence</dt>
            <dd>{Math.round(draft.confidence * 100)}%</dd>
          </div>
        )}
      </dl>
    </section>
  )
}

// ------------------------------------------------------------------ outcome cards (blocked, review, …)

const FRIENDLY_RULE: Record<string, string> = {
  injection_pattern: 'The post contains instructions aimed at the AI (prompt injection), so it was stopped before any AI read it.',
  expired: 'This chemical is past its expiry date. Expired chemicals can\'t be listed.',
  hazmat_no_sds: 'This is a hazardous material and no safety data sheet (SDS) is on file. Add the SDS and post again.',
  price_gt_3x_new: 'The asking price is more than 3× the new price, which looks like a pricing error or fraud.',
  counterfeit_risk: 'A discontinued part offered new-sealed far below list price is a common counterfeit pattern.',
}

export function OutcomeCard({ kind, outcome, rules, reasons }: { kind: OutcomeKind; outcome: string; rules?: string[]; reasons?: string[] }) {
  const detail = (rules ?? []).map((r) => FRIENDLY_RULE[r]).filter(Boolean)
  if (kind === 'blocked' || kind === 'flagged') {
    return (
      <section className="outcome blocked section">
        <div className="outcome-title">
          <Ban />
          {kind === 'flagged' ? 'Blocked by the compliance guard' : 'Blocked'}
        </div>
        <ul>
          {(detail.length ? detail : reasons ?? [outcome.replace(/^blocked:\s*/, '')]).map((d) => (
            <li key={d}>{d}</li>
          ))}
        </ul>
        <div className="skipped-line">Matching, pricing and outreach were skipped. Nothing was published.</div>
      </section>
    )
  }
  const neutral: Record<string, { icon: ReactNode; title: string; body: string }> = {
    review: {
      icon: <Eye />,
      title: 'Held for a person to review',
      body: detail[0] ?? 'This listing needs a human check before it can go live.',
    },
    clarify: {
      icon: <Help />,
      title: 'Post one item per listing',
      body: outcome.replace(/^needs_clarification:\s*/, '').replace(/^this post/, 'This post'),
    },
    unknown_part: {
      icon: <Help />,
      title: "We couldn't identify the part",
      body: 'Add the part number or the model (for example "Siemens 6ES7 315-2AG10") and try again. Nothing was published.',
    },
    stopped: {
      icon: <Info />,
      title: 'Stopped to stay within the run budget',
      body: 'This run reached its safety cap on AI calls. Nothing was published. Try again, or contact the team if it keeps happening.',
    },
    error: {
      icon: <Info />,
      title: 'Something went wrong',
      body: outcome.replace(/^error:\s*/, ''),
    },
  }
  const n = neutral[kind] ?? neutral.error
  return (
    <section className="outcome neutral section">
      <div className="outcome-title">
        {n.icon}
        {n.title}
      </div>
      <p>{n.body}</p>
      {kind !== 'error' && kind !== 'stopped' && <div className="skipped-line">Matching and pricing were skipped.</div>}
    </section>
  )
}

// ------------------------------------------------------------------ buyers

export function BuyerMatches({ matching, companies }: { matching: Step; companies: Company[] }) {
  const where = (id: number) => {
    const c = companies.find((x) => x.id === id)
    return c ? `${c.city}, ${c.state}` : ''
  }
  if (matching.status === 'no_candidates' || !matching.ranked?.length) {
    return (
      <section className="card section key">
        <h2>Top buyers</h2>
        <div className="empty">
          No plant on Spare Change runs this part yet. Your listing is live, and you'll get an alert when a matching need is
          posted.
        </div>
      </section>
    )
  }
  return (
    <section className="card section key">
      <div className="row">
        <h2>Top buyers</h2>
        <span className="small muted">
          {matching.ranked.length} of {matching.candidates} compatible plant{matching.candidates > 1 ? 's' : ''} · checked against
          installed equipment
        </span>
      </div>
      <div className={`check-note ${matching.method === 'rules_fallback' ? 'fallback' : ''}`}>
        <Check />
        {matching.method === 'rules_fallback'
          ? "Ranked by rules: the AI's answer failed our fact check twice, so these buyers are ranked from plant data alone."
          : matching.method === 'agent_retry'
            ? "Fact-checked: the AI's first answer didn't match the plant data, so it was corrected and checked again."
            : "Fact-checked: every reason below matches that plant's installed equipment and open needs."}
      </div>
      <div className="matches">
        {matching.ranked.map((m: any, i: number) => (
          <div className="match" key={m.buyer_id}>
            <span className={`score ${i === 0 ? 'top' : ''}`}>{m.score}</span>
            <div>
              <div className="buyer">
                {m.buyer_name} <span className="muted small">· {where(m.buyer_id)}</span>
              </div>
              <div className="reason">{m.reason}</div>
            </div>
            {m.need_id ? <span className="needchip">Open need #{m.need_id}</span> : <span />}
          </div>
        ))}
      </div>
    </section>
  )
}

// ------------------------------------------------------------------ price

export function PriceCards({ pricing }: { pricing: Step }) {
  return (
    <section className="card section key">
      <h2>Price</h2>
      <div className="prices">
        <div className="price">
          <div className="lbl">New (list)</div>
          <div className="val">{money(pricing.new_price)}</div>
        </div>
        <div className="price suggested">
          <div className="lbl">Suggested ask</div>
          <div className="val">{money(pricing.ask)}</div>
        </div>
        <div className="price">
          <div className="lbl">Scrap value</div>
          <div className="val">{money(pricing.scrap_value)}</div>
        </div>
      </div>
      <p className="why">{pricing.rationale}</p>
      <div className="private">
        <Lock />
        Suggested floor: <b>{money(pricing.floor_suggestion)}</b> · only you see this
      </div>
    </section>
  )
}

// ------------------------------------------------------------------ impact

export function ImpactStrip({ impact }: { impact: Step }) {
  return (
    <section className="impact section">
      <Leaf />
      <span>
        Recovers <b>{money(impact.value_recovered)}</b> vs. {money(impact.scrap_value_total)} scrap · <b>{kg(impact.kg_kept_out_of_scrap)}</b>{' '}
        kept out of scrap · est. <b>{kg(impact.est_kg_co2e_avoided)} CO2e</b> avoided
        {impact.est_hazardous_disposal_avoided ? (
          <>
            {' '}
            · hazardous waste disposal avoided: est. <b>{money(impact.est_hazardous_disposal_avoided)}</b>
          </>
        ) : null}
      </span>
      <span className="push">
        <InfoTip text={impact.method} />
      </span>
    </section>
  )
}

// ------------------------------------------------------------------ outreach

export function OutreachEmail({ outreach }: { outreach: Step }) {
  const [copied, setCopied] = useState(false)
  const text = `Subject: ${outreach.subject}\n\n${outreach.body}`
  return (
    <section className="card section">
      <div className="row">
        <h2>Outreach email to {outreach.to}</h2>
        <button
          className="btn ghost push"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(text)
              setCopied(true)
              setTimeout(() => setCopied(false), 1500)
            } catch {
              /* clipboard blocked: the text is still selectable */
            }
          }}
        >
          {copied ? <Check /> : <Copy />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <div className="email">
        <b>Subject:</b> {outreach.subject}
        {'\n\n'}
        {outreach.body}
      </div>
    </section>
  )
}

export function Skeleton({ text }: { text: string }) {
  return (
    <section className="card section skeleton-card">
      <div className="working-line">
        <span className="spinner" />
        {text}
      </div>
      <div className="skel w60" />
      <div className="skel w90" />
      <div className="skel w40" />
    </section>
  )
}
