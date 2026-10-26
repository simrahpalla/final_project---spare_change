import type { CompanyProfile } from '../api'
import { Factory } from '../icons'

// "What a real company sees": who you are signed in as, and the machines that drive your matches.
export function CompanyStrip({ profile, role }: { profile: CompanyProfile | null; role: 'seller' | 'buyer' }) {
  if (!profile) return <div className="company-strip skel-strip" />
  const machines = profile.installed_equipment
    .map((e) => `${e.qty}× ${e.platform}`)
    .slice(0, 3)
    .join(', ')
  const n = profile.active_listing_ids.length
  const listings = `${n} active listing${n === 1 ? '' : 's'}`
  const needs = `${profile.open_needs.length} open need${profile.open_needs.length === 1 ? '' : 's'}`
  return (
    <div className="company-strip">
      <Factory />
      <span>
        <b>{profile.name}</b>
        <span className="muted">
          {' '}
          · {profile.location} · {profile.industry}
        </span>
      </span>
      <span className="muted strip-machines">Runs {machines || 'no tracked equipment'}</span>
      <span className="strip-counts">
        {(role === 'seller' ? [listings, needs] : [needs, listings]).join(' · ')}
      </span>
    </div>
  )
}
