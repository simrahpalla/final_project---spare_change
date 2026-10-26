import type { CompanyProfile } from '../api'
import { CompanyStrip } from './CompanyStrip'

const COPY = {
  wanted: {
    title: 'Post what your plant needs',
    lede: 'Describe the part or the machine it goes in. Agents find surplus that fits and alert you when new matches appear.',
    soon: 'Posting needs opens in the next build (Phase 5). Until then, sellers can already find you: plants with open needs show up as top buyers on the Sell tab.',
  },
  marketplace: {
    title: 'Marketplace',
    lede: 'Everything available and everything wanted, side by side, with the matches between them.',
    soon: 'The two-column board and the total impact across deals open in the next build (Phase 5).',
  },
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
      <CompanyStrip profile={profile} role={tab === 'wanted' ? 'buyer' : 'seller'} />
      <div className="empty section">{c.soon}</div>
    </main>
  )
}
