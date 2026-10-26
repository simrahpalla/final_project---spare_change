import type { CompanyProfile } from '../api'
import { CompanyStrip } from './CompanyStrip'

const COPY = {
  negotiations: {
    title: 'Negotiations',
    lede: 'A seller agent and a buyer agent negotiate within private limits. A person approves every deal.',
    soon: 'Live negotiations with Approve and Reject open in a later build (Phase 6).',
  },
}

export function ComingSoon({ tab, profile }: { tab: keyof typeof COPY; profile: CompanyProfile | null }) {
  const c = COPY[tab]
  return (
    <main className="main">
      <h1>{c.title}</h1>
      <p className="lede">{c.lede}</p>
      <CompanyStrip profile={profile} role="seller" />
      <div className="empty section">{c.soon}</div>
    </main>
  )
}
