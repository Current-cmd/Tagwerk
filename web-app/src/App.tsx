import { Suspense, lazy, useCallback, useEffect, useRef, useState } from 'react'
import { AlertCircle, ExternalLink, FileText, Loader2, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { DaySlider } from '@/components/DaySlider'
import { KpiStrip } from '@/components/KpiStrip'
import { ActivitySheet } from '@/components/dashboard/ActivitySheet'
import { Dashboard } from '@/components/dashboard/Dashboard'
import { fetchDay, fetchDays, fetchTaskGraph, getMode, type DataMode } from '@/lib/api'
import { startEvents, useConnected, useEvents } from '@/lib/events'
import { useRoute, type View } from '@/lib/route'
import type { DayResponse, DaysResponse, TaskGraph, WsEvent } from '@/lib/types'
import { cn } from '@/lib/utils'

// vis-network is the bulk of the bundle: load it only when the graph tab opens
const LiveGraph = lazy(() => import('@/components/graph/LiveGraph').then(m => ({ default: m.LiveGraph })))
// three.js likewise only for the 3D scan page
const ScanView = lazy(() => import('@/components/scan/ScanView').then(m => ({ default: m.ScanView })))
const ReportView = lazy(() => import('@/components/report/ReportView').then(m => ({ default: m.ReportView })))
const spinner = <div className="flex flex-1 items-center justify-center"><Loader2 className="size-6 animate-spin text-muted-foreground" /></div>

const OLD_PAGES = [
  { href: '/dashboard', label: 'Dashboard (alt)' },
  { href: '/graph', label: 'Graph (alt)' },
  { href: '/upload', label: 'Upload' },
  { href: '/scan', label: 'Scan' },
]

export default function App() {
  const [route, navigate] = useRoute()
  const [days, setDays] = useState<DaysResponse | null>(null)
  const [day, setDay] = useState<DayResponse | null>(null)
  const [graph, setGraph] = useState<TaskGraph | null>(null)
  const [mode, setMode] = useState<DataMode>(getMode())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activity, setActivity] = useState<string | null>(null)
  const recDates = useRef(new Map<string, string>()) // capture_id -> date, filled from every day we load
  const req = useRef(0)

  const loadDays = useCallback(async () => {
    try {
      const d = await fetchDays()
      setDays(d)
      setMode(getMode())
      setError(null)
      return d
    } catch (e) {
      setError((e as Error).message)
      return null
    }
  }, [])

  useEffect(() => { loadDays() }, [loadDays])

  const date = days
    ? route.date && days.days.some(d => d.date === route.date) ? route.date : days.today
    : null

  const loadDay = useCallback(async (d: string) => {
    const id = ++req.current
    setLoading(true)
    try {
      const [dy, g] = await Promise.all([fetchDay(d), fetchTaskGraph(d)])
      if (id !== req.current) return
      dy.recordings.forEach(r => recDates.current.set(r.capture_id, dy.date))
      setDay(dy)
      setGraph(g)
      setError(null)
    } catch (e) {
      if (id === req.current) setError((e as Error).message)
    } finally {
      if (id === req.current) setLoading(false)
    }
  }, [])

  useEffect(() => { if (date) loadDay(date) }, [date, loadDay])

  // live updates: websocket only when a backend is there
  useEffect(() => { if (mode !== 'mock') startEvents() }, [mode])
  const connected = useConnected()
  const refetchTimer = useRef<ReturnType<typeof setTimeout>>(undefined)
  useEvents(useCallback((ev: WsEvent, live: boolean) => {
    if (ev.type !== 'status' || (ev.props as { step?: string } | undefined)?.step !== 'done' || !live) return
    clearTimeout(refetchTimer.current)
    refetchTimer.current = setTimeout(async () => {
      await loadDays()
      if (date) loadDay(date)
    }, 300)
  }, [date, loadDay, loadDays]))

  const setDate = useCallback((d: string) => {
    if (route.view === 'scan') navigate({ view: 'dashboard', date: d, rec: null })
    else navigate({ date: d, rec: null }, true)
  }, [navigate, route.view])
  const openScan = useCallback((cid: string) => navigate({ view: 'scan', param: cid }), [navigate])

  /** Jump to the day of a recording and open it. The contract gives activity recordings as ids only, so unknown ids
   *  are looked up day by day (days with recordings, nearest first). */
  const jumpRecording = useCallback(async (cid: string, known?: string) => {
    let d = known ?? recDates.current.get(cid)
    if (!d && days) {
      const cur = date ?? days.today
      const cands = days.days.filter(x => x.recordings > 0).map(x => x.date)
        .sort((a, b) => Math.abs(Date.parse(a) - Date.parse(cur)) - Math.abs(Date.parse(b) - Date.parse(cur)))
      for (const c of cands) {
        try {
          const dy = await fetchDay(c)
          dy.recordings.forEach(r => recDates.current.set(r.capture_id, dy.date))
          if (recDates.current.has(cid)) { d = c; break }
        } catch { /* keep looking */ }
      }
    }
    setActivity(null)
    navigate({ view: 'dashboard', date: d ?? date, rec: cid })
  }, [days, date, navigate])

  if (!days) {
    return (
      <div className="flex h-dvh items-center justify-center">
        {error ? <ErrorCard msg={error} onRetry={loadDays} /> : <Loader2 className="size-6 animate-spin text-muted-foreground" />}
      </div>
    )
  }

  return (
    <div className="flex h-dvh min-h-[640px] flex-col bg-muted/40">
      <header className="border-b bg-background">
        <div className="flex h-12 items-center gap-3 px-4">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-md bg-foreground text-sm font-bold text-background">T</div>
            <span className="font-semibold tracking-tight">Tagwerk</span>
          </div>
          <Separator orientation="vertical" className="h-5!" />
          <span className="truncate text-sm font-medium" data-testid="project-name">{day?.project.name ?? '…'}</span>
          {day?.project.bim === false && <Badge variant="outline" className="hidden text-[10px] lg:inline-flex">ohne BIM</Badge>}
          {mode !== 'real' && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge className="bg-amber-500 text-white" data-testid="demo-badge">Demo-Daten</Badge>
              </TooltipTrigger>
              <TooltipContent>
                {mode === 'mock' ? 'Mock-Modus (?mock=1): alle Daten aus der App selbst.' : '/api/v2 nicht erreichbar: Demo-Daten statt Live-Stand.'}
              </TooltipContent>
            </Tooltip>
          )}
          {mode !== 'mock' && (
            <Tooltip>
              <TooltipTrigger asChild>
                <span className={cn('size-2 rounded-full', connected ? 'bg-emerald-500' : 'bg-red-500')} aria-label={connected ? 'verbunden' : 'getrennt'} />
              </TooltipTrigger>
              <TooltipContent>Live-Verbindung {connected ? 'aktiv' : 'getrennt'}</TooltipContent>
            </Tooltip>
          )}

          <Tabs activationMode="manual" value={route.view === 'dashboard' || route.view === 'graph' ? route.view : ''} onValueChange={v => navigate({ view: v as View, rec: null })} className="mx-auto">
            <TabsList>
              <TabsTrigger value="dashboard" className="px-4" data-testid="tab-dashboard">Dashboard</TabsTrigger>
              <TabsTrigger value="graph" className="px-4" data-testid="tab-graph">Live-Graph</TabsTrigger>
            </TabsList>
          </Tabs>

          {loading && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
          <Button
            variant={route.view === 'report' ? 'secondary' : 'outline'}
            size="sm"
            onClick={() => navigate({ view: 'report', date })}
            data-testid="report-button"
          >
            <FileText /> Tagesbericht
          </Button>
          <nav className="flex items-center gap-0.5 text-xs">
            {OLD_PAGES.map(p => (
              <a key={p.href} href={p.href} className="flex items-center gap-1 rounded px-1.5 py-1 text-muted-foreground hover:bg-muted hover:text-foreground">
                {p.label}
              </a>
            ))}
            <ExternalLink className="ml-0.5 size-3 text-muted-foreground" />
          </nav>
        </div>
        <div className="border-t px-4 py-2">
          {date && <DaySlider days={days} date={date} onChange={setDate} />}
        </div>
      </header>

      <main className={cn('flex min-h-0 flex-1 flex-col gap-3 overflow-auto p-3', route.view !== 'report' && 'xl:overflow-hidden')}>
        {error && <ErrorCard msg={error} onRetry={() => date && loadDay(date)} inline />}
        {day && (route.view === 'dashboard' || route.view === 'graph') && <KpiStrip day={day} />}
        {day && route.view === 'dashboard' && (
          <Dashboard
            day={day}
            days={days}
            focusRec={route.rec}
            selectedActivity={activity}
            onSelectActivity={setActivity}
            onJumpRecording={jumpRecording}
            onOpenScan={openScan}
          />
        )}
        {route.view === 'scan' && route.param && (
          <Suspense fallback={spinner}>
            <ScanView cid={route.param} onBack={() => history.length > 1 ? history.back() : navigate({ view: 'dashboard' })} />
          </Suspense>
        )}
        {route.view === 'report' && date && (
          <Suspense fallback={spinner}>
            <ReportView date={date} onOpenScan={openScan} onOpenRecording={c => navigate({ view: 'dashboard', date, rec: c })} />
          </Suspense>
        )}
        {graph && route.view === 'graph' && (
          <Suspense fallback={spinner}>
            <LiveGraph graph={graph} onSelectActivity={setActivity} />
          </Suspense>
        )}
      </main>

      {day && (
        <ActivitySheet day={day} activityId={activity} onClose={() => setActivity(null)} onSelect={setActivity} onJumpRecording={c => jumpRecording(c)} />
      )}
    </div>
  )
}

function ErrorCard({ msg, onRetry, inline }: { msg: string; onRetry: () => void; inline?: boolean }) {
  return (
    <Card className={cn('flex-row items-center gap-3 border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800', !inline && 'max-w-md')}>
      <AlertCircle className="size-4 shrink-0" />
      <span className="flex-1">Daten konnten nicht geladen werden: {msg}</span>
      <Button size="sm" variant="outline" onClick={onRetry}><RefreshCw /> Erneut</Button>
    </Card>
  )
}
