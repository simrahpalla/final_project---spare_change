import { useEffect, useRef, useState } from 'react'
import type { Company, CompanyProfile } from '../api'
import { FEATURED } from '../demo'
import { Bell, Check, Chevron } from '../icons'

export type Tab = 'sell' | 'buy' | 'marketplace' | 'negotiations'
const TABS: { key: Tab; label: string }[] = [
  { key: 'sell', label: 'Sell' },
  { key: 'buy', label: 'Buy' },
  { key: 'marketplace', label: 'Marketplace' },
  { key: 'negotiations', label: 'Negotiations' },
]

function useOutsideClose(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && close()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close()
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open, close])
  return ref
}

const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter((w) => /^[A-Z]/.test(w))
    .slice(0, 2)
    .map((w) => w[0])
    .join('')

function AccountSwitcher(props: { companies: Company[]; accountId: number; onChange: (id: number) => void }) {
  const [open, setOpen] = useState(false)
  const [showAll, setShowAll] = useState(false)
  const ref = useOutsideClose(open, () => setOpen(false))
  const me = props.companies.find((c) => c.id === props.accountId)
  const featuredIds = new Set(FEATURED.map((f) => f.id))
  const rest = props.companies.filter((c) => !featuredIds.has(c.id))
  const sellers = rest.filter((c) => c.active_listings > 0)
  const buyers = rest.filter((c) => c.active_listings === 0 && c.open_needs > 0)
  const others = rest.filter((c) => c.active_listings === 0 && c.open_needs === 0)
  const group = (title: string, list: Company[]) =>
    list.length > 0 && (
      <div className="menu-group">
        <div className="menu-title">{title}</div>
        {list.map((c) => (
          <button
            key={c.id}
            className={`menu-item ${c.id === props.accountId ? 'on' : ''}`}
            onClick={() => {
              props.onChange(c.id)
              setOpen(false)
            }}
          >
            <span className="avatar small">{initials(c.name)}</span>
            <span className="menu-main">
              <span>{c.name}</span>
              <span className="muted small">
                {c.city}, {c.state}
                {c.active_listings > 0 && ` · ${c.active_listings} listing${c.active_listings > 1 ? 's' : ''}`}
                {c.open_needs > 0 && ` · ${c.open_needs} need${c.open_needs > 1 ? 's' : ''}`}
              </span>
            </span>
            {c.id === props.accountId && <Check className="menu-check" />}
          </button>
        ))}
      </div>
    )
  return (
    <div className="switcher" ref={ref}>
      <button className="switcher-btn" onClick={() => setOpen(!open)} aria-haspopup="menu" aria-expanded={open}>
        <span className="avatar">{me ? initials(me.name) : '·'}</span>
        <span className="switcher-name">{me?.name ?? 'Choose an account'}</span>
        <span className="demo-tag">demo</span>
        <Chevron />
      </button>
      {open && (
        <div className="menu switcher-menu" role="menu">
          <div className="menu-head">
            Signed in as <b>(demo account, no password)</b>
            <div className="muted small">Pick any company to see Spare Change the way it would.</div>
          </div>
          <div className="menu-scroll">
            <div className="menu-group">
              <div className="menu-title">Demo accounts</div>
              {FEATURED.map((f) => {
                const c = props.companies.find((x) => x.id === f.id)
                if (!c) return null
                return (
                  <button
                    key={c.id}
                    className={`menu-item featured ${c.id === props.accountId ? 'on' : ''}`}
                    onClick={() => {
                      props.onChange(c.id)
                      setOpen(false)
                    }}
                  >
                    <span className="avatar small">{initials(c.name)}</span>
                    <span className="menu-main">
                      <span>
                        {c.name} <span className="role-tag">{f.role}</span>
                      </span>
                      <span className="muted small">{f.whatToTry}</span>
                    </span>
                    {c.id === props.accountId && <Check className="menu-check" />}
                  </button>
                )
              })}
            </div>
            {showAll ? (
              <>
                {group('Other sellers with surplus', sellers)}
                {group('Other buyers with open needs', buyers)}
                {group('Other plants', others)}
              </>
            ) : (
              <button className="menu-more" onClick={() => setShowAll(true)}>
                Show all companies ({props.companies.length})
              </button>
            )}
          </div>
          <div className="menu-foot">Demo only: switching accounts is not real sign-in. Use Reset demo to start clean.</div>
        </div>
      )}
    </div>
  )
}

function AlertsBell(props: {
  profile: CompanyProfile | null
  onOpen: () => void
  onStart: (t: { listingId: number; needId: number }) => void
  onOpenNegotiations: () => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useOutsideClose(open, () => setOpen(false))
  const unread = props.profile?.unread_alerts ?? 0
  return (
    <div className="bell-wrap" ref={ref}>
      <button
        className="bell"
        aria-label={`Alerts${unread ? `, ${unread} unread` : ''}`}
        onClick={() => {
          if (!open) props.onOpen()
          setOpen(!open)
        }}
      >
        <Bell />
        {unread > 0 && <span className="badge">{unread}</span>}
      </button>
      {open && (
        <div className="menu bell-menu" role="menu">
          <div className="menu-head">Alerts for {props.profile?.name ?? 'this account'}</div>
          {props.profile && props.profile.alerts.length > 0 ? (
            props.profile.alerts.map((a) => (
              <div key={a.id} className={`alert ${a.read ? '' : 'unread'}`}>
                <div>{a.message}</div>
                <div className="alert-actions">
                  <span className="muted small">{a.kind.replace('_', ' ')}</span>
                  {a.kind === 'new_match' && !a.closed_reason && a.listing_id && a.need_id && (
                    <button
                      className="btn ghost push"
                      onClick={() => {
                        setOpen(false)
                        props.onStart({ listingId: a.listing_id!, needId: a.need_id! })
                      }}
                    >
                      Start negotiation
                    </button>
                  )}
                  {a.kind === 'new_match' && a.closed_reason && <span className="muted small push">Closed: {a.closed_reason}</span>}
                  {(a.kind === 'deal_pending' || a.kind === 'deal_approved' || a.kind === 'deal_rejected') && (
                    <button
                      className="btn ghost push"
                      onClick={() => {
                        setOpen(false)
                        props.onOpenNegotiations()
                      }}
                    >
                      Open negotiations
                    </button>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="empty-small">
              No alerts yet. You'll get one here when a buyer or listing matches this account.
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function Nav(props: {
  tab: Tab
  onTab: (t: Tab) => void
  companies: Company[]
  accountId: number
  onAccount: (id: number) => void
  profile: CompanyProfile | null
  onOpenAlerts: () => void
  onReset: () => void
  resetting: boolean
  onStartNegotiation: (t: { listingId: number; needId: number }) => void
  onOpenNegotiations: () => void
}) {
  return (
    <nav className="nav">
      <div className="logo">
        <span className="coin">¢</span>Spare Change
      </div>
      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={props.tab === t.key}
            className={`tab tab-${t.key} ${props.tab === t.key ? 'on' : ''}`}
            onClick={() => props.onTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="nav-right">
        <button
          className="btn reset"
          title="Restore the seeded marketplace for every account"
          disabled={props.resetting}
          onClick={() => {
            if (window.confirm('Reset the demo? This restores the original listings, needs and alerts for every account.')) props.onReset()
          }}
        >
          {props.resetting ? 'Resetting…' : 'Reset demo'}
        </button>
        <AccountSwitcher companies={props.companies} accountId={props.accountId} onChange={props.onAccount} />
        <AlertsBell
          profile={props.profile}
          onOpen={props.onOpenAlerts}
          onStart={props.onStartNegotiation}
          onOpenNegotiations={props.onOpenNegotiations}
        />
      </div>
    </nav>
  )
}
