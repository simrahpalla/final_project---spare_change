import type { ReactNode } from 'react'
import { Search, Tag } from '../icons'

// The page header for Sell and Buy (design.md §4, option B): each side has its own colour, orange for Sell, blue for Buy.
// The tagline is the page heading; the page's job is the small label above it.
const SIDES = {
  sell: { icon: <Tag />, label: 'Sell surplus parts', tagline: 'Turn spare parts into spare change.' },
  buy: { icon: <Search />, label: 'Buy parts', tagline: 'Spare yourself the downtime.' },
}

export function PageBand({ side, children }: { side: keyof typeof SIDES; children: ReactNode }) {
  const s = SIDES[side]
  return (
    <header className={`band band-${side}`}>
      <div className="eyebrow">
        {s.icon}
        {s.label}
      </div>
      <h1 className="tagline">{s.tagline}</h1>
      <p className="lede">{children}</p>
    </header>
  )
}
