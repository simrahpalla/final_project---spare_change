import { useCallback, useEffect, useState } from 'react'
import { api, errorMessage, type Company, type CompanyProfile, type Health, type RunStatus, type Session } from './api'
import { ComingSoon } from './components/ComingSoon'
import { MarketplacePage } from './components/MarketplacePage'
import { Nav, type Tab } from './components/Nav'
import { Rail } from './components/Rail'
import { SellPage } from './components/SellPage'
import { BuyPage, needFormFor, type NeedForm } from './components/BuyPage'
import { DEFAULT_ACCOUNT, featured, type Scenario } from './demo'

// Remembers the demo account between visits; works (without remembering) where storage is blocked.
const storage = {
  get: (k: string) => {
    try {
      return localStorage.getItem(k)
    } catch {
      return null
    }
  },
  set: (k: string, v: string) => {
    try {
      localStorage.setItem(k, v)
    } catch {
      /* private mode or blocked storage */
    }
  },
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [offline, setOffline] = useState(false)
  const [tab, setTab] = useState<Tab>('sell')
  const [companies, setCompanies] = useState<Company[]>([])
  const [accountId, setAccountId] = useState<number>(() => Number(storage.get('sc.account')) || DEFAULT_ACCOUNT)
  const [profile, setProfile] = useState<CompanyProfile | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [run, setRun] = useState<RunStatus | null>(null) // seller flow (Sell tab)
  const [needRun, setNeedRun] = useState<RunStatus | null>(null) // buyer flow (Buy tab)
  const [needForm, setNeedForm] = useState<NeedForm>(() => needFormFor(accountId))
  const [boardVersion, setBoardVersion] = useState(0)
  const [resetting, setResetting] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  // The paste box starts with the signed-in company's own example post, so a visitor can just click Find buyers.
  const [post, setPost] = useState<string>(() => featured(accountId)?.post ?? '')
  const ready = health?.mcp?.status === 'ready'

  // Poll health until the marketplace tools (MCP servers) have started.
  useEffect(() => {
    let stop = false
    let timer: number | undefined
    const tick = () =>
      api
        .health()
        .then((h) => {
          if (stop) return
          setHealth(h)
          setOffline(false)
          if (h.mcp?.status === 'starting') timer = window.setTimeout(tick, 1500)
        })
        .catch(() => {
          if (stop) return
          setOffline(true)
          timer = window.setTimeout(tick, 3000)
        })
    tick()
    return () => {
      stop = true
      window.clearTimeout(timer)
    }
  }, [])

  const refresh = useCallback(async () => {
    if (!ready) return
    try {
      const [c, p, s] = await Promise.all([api.companies(), api.company(accountId), api.session()])
      setCompanies(c.companies)
      setProfile(p)
      setSession(s)
    } catch (e) {
      setNotice(errorMessage(e))
    }
  }, [ready, accountId])

  useEffect(() => {
    refresh()
  }, [refresh])

  const runDone = useCallback(() => {
    refresh()
    setBoardVersion((v) => v + 1)
  }, [refresh])

  function switchAccount(id: number, text?: string) {
    storage.set('sc.account', String(id))
    setPost(text ?? featured(id)?.post ?? '')
    if (id === accountId) return
    setAccountId(id)
    setNeedForm(needFormFor(id))
    setProfile(null)
    setRun(null)
    setNeedRun(null)
  }

  function runScenario(s: Scenario) {
    if (s.account === null) setPost(s.text) // the injection test keeps the current account
    else switchAccount(s.account, s.text)
  }

  async function resetDemo() {
    setResetting(true)
    try {
      const r = await api.reset()
      setRun(null)
      setNeedRun(null)
      setPost(featured(accountId)?.post ?? '')
      setNeedForm(needFormFor(accountId))
      setNotice(`${r.message} Every account starts clean.`)
      runDone()
    } catch (e) {
      setNotice(errorMessage(e))
    } finally {
      setResetting(false)
    }
  }

  async function openAlerts() {
    if (!profile?.unread_alerts) return
    try {
      await api.markAlertsRead(accountId)
      refresh()
    } catch {
      /* the list still shows; the count updates next time */
    }
  }

  return (
    <div className="page">
      <Nav
        tab={tab}
        onTab={setTab}
        companies={companies}
        accountId={accountId}
        onAccount={(id) => switchAccount(id)}
        profile={profile}
        onOpenAlerts={openAlerts}
        onReset={resetDemo}
        resetting={resetting}
      />
      {(offline || !ready) && (
        <div className={`banner ${offline || health?.mcp?.status === 'failed' ? 'bad' : ''}`} role="status">
          {offline
            ? "Can't reach Spare Change. Check that the app is running, then this page reconnects by itself."
            : health?.mcp?.status === 'failed'
              ? `The marketplace tools didn't start: ${health.mcp.error ?? 'unknown error'}. Restart the app.`
              : !health?.key_found && health
                ? 'PORTKEY_API_KEY was not found. Add it to a .env file (see the README) and restart the app.'
                : 'Starting up… loading marketplace tools. This takes a few seconds the first time.'}
        </div>
      )}
      {notice && (
        <div className="banner" role="status" onClick={() => setNotice(null)}>
          {notice} <span className="muted">(click to dismiss)</span>
        </div>
      )}
      <div className="layout">
        {tab === 'sell' ? (
          <SellPage
            accountId={accountId}
            profile={profile}
            companies={companies}
            ready={ready}
            run={run}
            onRun={setRun}
            onRunDone={runDone}
            text={post}
            onText={setPost}
            onScenario={runScenario}
          />
        ) : tab === 'buy' ? (
          <BuyPage
            accountId={accountId}
            profile={profile}
            ready={ready}
            run={needRun}
            onRun={setNeedRun}
            onRunDone={runDone}
            form={needForm}
            onForm={setNeedForm}
          />
        ) : tab === 'marketplace' ? (
          <MarketplacePage ready={ready} accountId={accountId} version={boardVersion} />
        ) : (
          <ComingSoon tab={tab} profile={profile} />
        )}
        <Rail run={tab === 'buy' ? needRun : tab === 'sell' ? run : null} need={tab === 'buy'} session={session} />
      </div>
    </div>
  )
}
