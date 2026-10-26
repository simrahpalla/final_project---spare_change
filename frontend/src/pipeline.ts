// Turns a run's steps into (1) the right-rail activity list and (2) one outcome the result area can show.
import type { NegotiationView, RunStatus, Step } from './api'

export type RailState = 'done' | 'working' | 'blocked' | 'review' | 'skipped' | 'pending'
export type RailItem = { key: string; label: string; code: boolean; state: RailState; note?: string }

const PIPELINE: { key: string; label: string; code: boolean; agent?: string }[] = [
  { key: 'prescreen', label: 'Pre-screen', code: true },
  { key: 'listing_agent', label: 'Listing agent', code: false, agent: 'listing_agent' },
  { key: 'rules', label: 'Compliance rules', code: true },
  { key: 'guard', label: 'Compliance guard', code: false, agent: 'compliance_guard' },
  { key: 'prefilter', label: 'Buyer pre-filter', code: true },
  { key: 'matching', label: 'Matching agent', code: false, agent: 'matching_agent' },
  { key: 'pricing', label: 'Pricing agent', code: false, agent: 'pricing_agent' },
  { key: 'impact', label: 'Impact estimate', code: true },
  { key: 'alerts', label: 'Alerts', code: true },
  { key: 'auto_negotiate', label: 'Auto-negotiate', code: true },
]

// The buyer side: the same guard, the same matching agent and the same pre-filter code, in reverse.
const NEED_PIPELINE: typeof PIPELINE = [
  { key: 'prescreen', label: 'Pre-screen', code: true },
  { key: 'need_agent', label: 'Need agent', code: false, agent: 'need_agent' },
  { key: 'guard', label: 'Compliance guard', code: false, agent: 'compliance_guard' },
  { key: 'prefilter', label: 'Listing pre-filter', code: true },
  { key: 'matching', label: 'Matching agent', code: false, agent: 'matching_agent' },
  { key: 'alerts', label: 'Alerts', code: true },
  { key: 'auto_negotiate', label: 'Auto-negotiate', code: true },
]

// Named loading states (never a bare spinner).
export const WORKING_TEXT: Record<string, string> = {
  prescreen: 'Checking the post for anything aimed at the AI…',
  listing_agent: 'Listing agent reading your post…',
  rules: 'Checking compliance rules…',
  guard: 'Compliance guard reviewing the listing…',
  prefilter: 'Finding plants that run this part…',
  matching: 'Matching agent ranking buyers…',
  pricing: 'Pricing agent checking new and scrap prices…',
  impact: 'Estimating the impact…',
  alerts: 'Sending alerts…',
  need_agent: 'Need agent reading your post…',
}

const NEED_WORKING: Record<string, string> = {
  guard: 'Compliance guard reviewing the post…',
  prefilter: 'Finding surplus that fits your machine…',
  matching: 'Matching agent ranking listings…',
}

const find = (steps: Step[], name: string) => steps.find((s) => s.step === name)

function note(key: string, s: Step, reverse = false): string | undefined {
  switch (key) {
    case 'prescreen':
      return s.status === 'blocked' ? 'injection found' : 'no injection'
    case 'listing_agent':
      return s.draft?.part_number ? 'part identified' : 'part unclear'
    case 'rules':
      return s.status === 'passed' ? 'passed' : s.status === 'needs_review' ? 'held for review' : 'blocked'
    case 'guard':
      return s.status === 'flagged' ? 'flagged' : 'allowed'
    case 'need_agent':
      return s.draft?.part_number ? 'part identified' : s.draft?.family ? 'machine + family' : 'part unclear'
    case 'prefilter':
      return reverse ? `${s.candidates} listing${s.candidates === 1 ? '' : 's'}` : `${s.candidates} plant${s.candidates === 1 ? '' : 's'}`
    case 'auto_negotiate':
      return s.status === 'started'
        ? `started (${s.started.length})`
        : s.status === 'waiting'
          ? 'after limits confirmed'
          : s.status === 'skipped'
            ? 'not in this app'
            : 'no strong match'
    case 'alerts':
      return s.sent ? `${s.sent} sent${s.duplicates ? ` · ${s.duplicates} dup skipped` : ''}` : s.duplicates ? 'already sent' : 'none (below 70)'
    case 'matching':
      if (s.status === 'no_candidates') return reverse ? 'skipped · no listings' : 'no buyers yet'
      if (s.method === 'rules_fallback') return 'ranked by rules'
      return `${s.ranked?.length ?? 0} ranked · ${s.method === 'agent_retry' ? 'corrected' : 'checked'}`
    case 'pricing':
      return s.ask ? `$${Math.round(s.ask).toLocaleString('en-US')}` : undefined
    case 'impact':
      return 'computed in code'
  }
}

export const isNeedRun = (run: RunStatus | null) => run?.kind === 'need_flow'

export function railItems(run: RunStatus | null, need = isNeedRun(run)): RailItem[] {
  const pipeline = need ? NEED_PIPELINE : PIPELINE
  if (!run) return pipeline.map((p) => ({ ...p, state: 'pending' as RailState }))
  const done = run.status === 'done'
  let working = false // while running, the first step not reached yet is the one in progress
  return pipeline.map((p) => {
    const s = find(run.steps, p.key)
    if (s) {
      const blocked =
        (p.key === 'prescreen' && s.status === 'blocked') ||
        (p.key === 'rules' && s.status === 'blocked') ||
        (p.key === 'guard' && s.status === 'flagged')
      const review = p.key === 'rules' && s.status === 'needs_review'
      if (p.key === 'matching' && s.status === 'no_candidates')
        return { ...p, state: 'skipped' as RailState, note: note(p.key, s, need) }
      return { ...p, state: blocked ? 'blocked' : review ? 'review' : 'done', note: note(p.key, s, need) }
    }
    if (done) return { ...p, state: 'skipped' as RailState, note: 'skipped' }
    if (!working) {
      working = true
      return { ...p, state: 'working' as RailState }
    }
    return { ...p, state: 'pending' as RailState }
  })
}

export function workingText(run: RunStatus | null): string {
  const item = railItems(run).find((i) => i.state === 'working')
  if (!item) return 'Starting…'
  return (isNeedRun(run) && NEED_WORKING[item.key]) || WORKING_TEXT[item.key]
}

export type OutcomeKind = 'listed' | 'posted' | 'no_listings' | 'no_buyers' | 'blocked' | 'review' | 'flagged' | 'clarify' | 'unknown_part' | 'error' | 'stopped'

export function outcomeKind(outcome: string): OutcomeKind {
  if (outcome.startsWith('listed (no matching')) return 'no_buyers'
  if (outcome.startsWith('listed')) return 'listed'
  if (outcome.startsWith('posted (no matching')) return 'no_listings'
  if (outcome.startsWith('posted')) return 'posted'
  if (outcome.startsWith('blocked')) return 'blocked'
  if (outcome.startsWith('needs_review')) return 'review'
  if (outcome.startsWith('flagged')) return 'flagged'
  if (outcome.startsWith('needs_clarification')) return 'clarify'
  if (outcome.startsWith('needs_human')) return 'unknown_part'
  if (outcome.startsWith('stopped')) return 'stopped'
  return 'error'
}

export const stepOf = find

// ------------------------------------------------------------------ negotiation rail (from the company-scoped view)
// Only what this company may see: its own blocked moves, never the other side's.

export function negotiationRail(v: NegotiationView | null): RailItem[] {
  const base: Omit<RailItem, 'state'>[] = [
    { key: 'lock', label: 'Units reserved', code: true },
    { key: 'seller', label: 'Seller agent', code: false },
    { key: 'buyer', label: 'Buyer agent', code: false },
    { key: 'rules', label: 'Limit rules', code: true },
    { key: 'scan', label: 'Message scan', code: true },
    { key: 'approval', label: 'Approval by both companies', code: false },
  ]
  if (!v) return base.map((b) => ({ ...b, state: 'pending' as RailState }))
  const running = v.status === 'open' && v.live?.status === 'running' && !v.live?.queued
  const moves = (side: string) => v.offers.filter((o) => o.from_side === side).length
  const d = v.deal
  return base.map((b): RailItem => {
    switch (b.key) {
      case 'lock':
        return { ...b, state: 'done', note: `${v.qty} unit${v.qty > 1 ? 's' : ''}` }
      case 'seller':
      case 'buyer': {
        const n = moves(b.key)
        if (running && v.next_to_move === b.key) return { ...b, state: 'working' }
        if (v.live?.queued) return { ...b, state: 'pending', note: 'queued' }
        return { ...b, state: n ? 'done' : v.status === 'open' ? 'pending' : 'skipped', note: n ? `${n} move${n > 1 ? 's' : ''}` : undefined }
      }
      case 'rules':
        return v.my_blocked.length
          ? { ...b, state: 'blocked', note: `${v.my_blocked.length} of yours blocked` }
          : { ...b, state: v.offers.length ? 'done' : 'pending', note: v.offers.length ? 'all within limits' : undefined }
      case 'scan':
        return { ...b, state: v.offers.length ? 'done' : 'pending', note: v.offers.length ? 'no limits in messages' : undefined }
      default:
        if (!d) return { ...b, state: v.status === 'open' ? 'pending' : 'skipped', note: v.status === 'open' ? undefined : 'no deal' }
        if (d.status === 'approved') return { ...b, state: 'done', note: 'both approved' }
        if (d.status === 'rejected') return { ...b, state: 'blocked', note: 'rejected' }
        return { ...b, state: 'review', note: d.i_approved ? 'waiting for them' : 'needs you' }
    }
  })
}
