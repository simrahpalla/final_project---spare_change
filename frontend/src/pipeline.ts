// Turns a run's steps into (1) the right-rail activity list and (2) one outcome the result area can show.
import type { RunStatus, Step } from './api'

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
}

const find = (steps: Step[], name: string) => steps.find((s) => s.step === name)

function note(key: string, s: Step): string | undefined {
  switch (key) {
    case 'prescreen':
      return s.status === 'blocked' ? 'injection found' : 'no injection'
    case 'listing_agent':
      return s.draft?.part_number ? 'part identified' : 'part unclear'
    case 'rules':
      return s.status === 'passed' ? 'passed' : s.status === 'needs_review' ? 'held for review' : 'blocked'
    case 'guard':
      return s.status === 'flagged' ? 'flagged' : 'allowed'
    case 'prefilter':
      return `${s.candidates} plant${s.candidates === 1 ? '' : 's'}`
    case 'matching':
      return s.status === 'no_candidates' ? 'no buyers yet' : `${s.ranked?.length ?? 0} ranked`
    case 'pricing':
      return s.ask ? `$${Math.round(s.ask).toLocaleString('en-US')}` : undefined
    case 'impact':
      return 'computed in code'
  }
}

export function railItems(run: RunStatus | null): RailItem[] {
  if (!run) return PIPELINE.map((p) => ({ ...p, state: 'pending' as RailState }))
  const done = run.status === 'done'
  let working = false // while running, the first step not reached yet is the one in progress
  return PIPELINE.map((p) => {
    const s = find(run.steps, p.key)
    if (s) {
      const blocked =
        (p.key === 'prescreen' && s.status === 'blocked') ||
        (p.key === 'rules' && s.status === 'blocked') ||
        (p.key === 'guard' && s.status === 'flagged')
      const review = p.key === 'rules' && s.status === 'needs_review'
      return { ...p, state: blocked ? 'blocked' : review ? 'review' : 'done', note: note(p.key, s) }
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
  return item ? WORKING_TEXT[item.key] : 'Starting…'
}

export type OutcomeKind = 'listed' | 'no_buyers' | 'blocked' | 'review' | 'flagged' | 'clarify' | 'unknown_part' | 'error' | 'stopped'

export function outcomeKind(outcome: string): OutcomeKind {
  if (outcome.startsWith('listed (no matching')) return 'no_buyers'
  if (outcome.startsWith('listed')) return 'listed'
  if (outcome.startsWith('blocked')) return 'blocked'
  if (outcome.startsWith('needs_review')) return 'review'
  if (outcome.startsWith('flagged')) return 'flagged'
  if (outcome.startsWith('needs_clarification')) return 'clarify'
  if (outcome.startsWith('needs_human')) return 'unknown_part'
  if (outcome.startsWith('stopped')) return 'stopped'
  return 'error'
}

export const stepOf = find
