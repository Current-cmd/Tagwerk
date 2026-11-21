// Port of the replay video panel of web/graph/index.html: picker from /api/replays, "▶ Abspielen" starts the video,
// and once the video really plays (`playing`) the replay is POSTed with replay_of + sync=1 so the server publishes each
// change at its second of the video. Captions come from the entry's segments; "Erfasst" is fed by the websocket.
import { useCallback, useEffect, useRef, useState } from 'react'
import { Loader2, Play } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { fetchCapture, fetchReplays, getElementNames, postReplay } from '@/lib/api'
import { useEvents } from '@/lib/events'
import { mmss, stateDe } from '@/lib/format'
import type { ReplayEntry, ReplaySegment, WsEvent } from '@/lib/types'
import { mockReplayFindings } from '@/mock'
import { cn } from '@/lib/utils'
import { EventIcon } from '@/components/common'

interface Session {
  cid: string
  start: number
  video: boolean
  segs: ReplaySegment[]
  note: string | null
  quotes: string[]
}
interface Found { t: number | null; text: string; cls: '' | 'p' | 'e'; icon?: string }

export function ReplayPanel({ onActivity }: { onActivity?: () => void }) {
  const [list, setList] = useState<ReplayEntry[]>([])
  const [simulated, setSimulated] = useState(false)
  const [sel, setSel] = useState('')
  const [running, setRunning] = useState(false)
  const [title, setTitle] = useState<string | null>(null)
  const [mode, setMode] = useState<'none' | 'video' | 'note'>('none')
  const [noteText, setNoteText] = useState('')
  const [needClick, setNeedClick] = useState(false)
  const [caption, setCaption] = useState<{ text: string; idle: boolean; quotes: string[] }>({ text: '–', idle: true, quotes: [] })
  const [found, setFound] = useState<Found[]>([])
  const [status, setStatus] = useState<{ text: string; err?: boolean } | null>(null)
  const vid = useRef<HTMLVideoElement>(null)
  const session = useRef<Session | null>(null)
  const timers = useRef<ReturnType<typeof setTimeout>[]>([])
  const foundEnd = useRef<HTMLDivElement>(null)
  const names = useRef<Map<string, string>>(new Map())

  useEffect(() => {
    fetchReplays().then(r => {
      setList(r.list)
      setSimulated(r.simulated)
      if (r.list.length) setSel(r.list[0].id)
    })
    getElementNames().then(m => { names.current = m })
  }, [])

  const clock = () => {
    const s = session.current
    if (!s) return 0
    return s.video && vid.current ? vid.current.currentTime : (performance.now() - s.start) / 1000
  }

  // captions, every 200 ms like the old page
  useEffect(() => {
    const iv = setInterval(() => {
      const s = session.current
      if (!s) return
      const t = clock()
      const seg = s.segs.find(g => t >= g.start && t <= g.end + 0.4)
      if (!seg) {
        if (!s.segs.length) setCaption({ text: s.note ? '' : 'Keine Sprache erkannt.', idle: true, quotes: [] })
        return
      }
      setCaption({ text: seg.text, idle: false, quotes: [...s.quotes] })
    }, 200)
    return () => clearInterval(iv)
  }, [])

  useEffect(() => { foundEnd.current?.scrollIntoView({ block: 'nearest' }) }, [found])

  const addFound = useCallback((text: string, cls: Found['cls'] = '', t: number | null = clock(), icon?: string) => {
    setFound(f => [...f, { t, text, cls, icon }])
  }, [])

  function begin(s: Omit<Session, 'quotes'>, label: string) {
    timers.current.forEach(clearTimeout)
    timers.current = []
    session.current = { ...s, quotes: [] }
    setFound([])
    setCaption({ text: '–', idle: true, quotes: [] })
    setNeedClick(false)
    setTitle(label)
    setStatus(null)
    onActivity?.()
  }

  function showVideo(url: string) {
    const v = vid.current!
    setMode('video')
    v.muted = false
    v.src = url
    v.currentTime = 0
  }
  function showNote(text: string) {
    vid.current?.pause()
    setMode('note')
    setNoteText(text)
  }
  function playVideo() {
    const v = vid.current!
    const p = v.play()
    if (p && p.catch) p.catch(() => { v.muted = true; v.play().catch(() => setNeedClick(true)) })
  }

  async function startReplay() {
    const entry = list.find(r => r.id === sel)
    if (!entry) return
    setRunning(true)
    const cid = `replay-ui-${Date.now()}`
    begin({ cid, start: performance.now(), video: !!entry.video, segs: entry.segments || [], note: entry.note }, entry.label || entry.id)
    if (entry.video) { // start the server clock when the picture really moves (loading takes a moment)
      showVideo(entry.video)
      const v = vid.current!
      const started = new Promise<void>(res => { v.addEventListener('playing', () => res(), { once: true }); setTimeout(res, 4000) })
      playVideo()
      await started
    } else showNote(entry.note || entry.label || entry.id)

    if (simulated) { // no backend: replay the fixture's findings on the same clock
      const items = mockReplayFindings(entry.id)
      const t0 = clock()
      items.forEach(it => timers.current.push(setTimeout(() => {
        if (session.current?.cid !== cid) return
        if (it.quote) session.current.quotes.push(it.quote)
        addFound(it.text, it.cls, it.t, it.cls === 'e' ? (it.text.includes('krank') ? 'absence' : 'delay') : undefined)
      }, Math.max(0, (it.t - t0) * 1000))))
      const end = Math.max(7, ...items.map(i => i.t)) - t0
      await new Promise(res => timers.current.push(setTimeout(res, end * 1000)))
      setStatus({ text: `fertig (Demo): ${items.filter(i => i.cls === '').length} Änderungen` })
    } else {
      try {
        const r = await postReplay(entry.id, cid)
        setStatus(r.ok ? { text: `fertig: ${r.changes} Änderungen` } : { text: `Fehler ${r.status}`, err: true })
      } catch {
        setStatus({ text: 'Fehler: keine Verbindung', err: true })
      }
    }
    setRunning(false)
  }

  // a new upload finished elsewhere: show its video and what was captured
  const liveCapture = useCallback(async (cid: string) => {
    let r
    try { r = await fetchCapture(cid) } catch { return }
    const v = (r.capture?.media ?? []).find(m => m.type === 'video')
    if (!v) return
    begin({ cid, start: performance.now(), video: true, segs: r.transcript?.segments ?? [], note: null }, `Aufnahme ${cid}`)
    showVideo(`/media/${cid}/${v.path.split('/').pop()}`)
    playVideo()
    for (const c of (r.changes ?? []).filter(c => ['confirmed', 'proposed', 'unchanged'].includes(c.action))) {
      if (c.quote) session.current!.quotes.push(c.quote)
      addFound(`${names.current.get(c.element_id) ?? c.element_id} → ${stateDe(c.state)}${c.action === 'proposed' ? '?' : ''}`, c.action === 'proposed' ? 'p' : '', c.t ?? null)
    }
    for (const a of r.structured?.absences ?? []) addFound(`${a.count}× ${a.trade} ${a.reason ?? ''}`.trim(), 'e', null, 'absence')
    for (const e of r.structured?.special_events ?? []) addFound(e.text, 'e', null, e.type)
  }, [addFound])

  useEvents(useCallback((ev: WsEvent, live: boolean) => {
    const p = (ev.props ?? {}) as Record<string, string | undefined>
    const s = session.current
    if (s && ev.type === 'edge' && p.src === s.cid && (ev.label === 'CONFIRMED' || ev.label === 'PROPOSES')) {
      if (p.quote) s.quotes.push(p.quote)
      const nm = names.current.get(p.dst ?? '') ?? p.name_de ?? p.dst ?? ''
      addFound(`${nm} → ${stateDe(p.state)}${ev.label === 'PROPOSES' ? '?' : ''}`, ev.label === 'PROPOSES' ? 'p' : '')
    } else if (s && ev.type === 'node' && ev.label === 'Event' && p.capture === s.cid) {
      addFound(p.name || p.text || '', 'e', clock(), p.type)
    } else if (ev.type === 'status' && p.step === 'done' && live && !(s && s.cid === ev.id) && !String(ev.id).startsWith('manual-')) {
      liveCapture(String(ev.id))
    }
  }, [addFound, liveCapture]))

  useEffect(() => () => timers.current.forEach(clearTimeout), [])

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-3" data-testid="replay-panel">
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">Aufnahme wiederholen</span>
          {simulated && <Badge variant="outline" className="text-[10px]">Demo</Badge>}
        </div>
        {list.length === 0 ? (
          <div className="text-xs text-muted-foreground">Keine gespeicherten Aufnahmen.</div>
        ) : (
          <div className="flex gap-1.5">
            <select
              value={sel}
              onChange={e => setSel(e.target.value)}
              disabled={running}
              title="Gespeicherte Aufnahme wiederholen"
              data-testid="replay-select"
              className="h-8 min-w-0 flex-1 truncate rounded-md border bg-background px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
            >
              {list.map(r => <option key={r.id} value={r.id}>{r.label || r.id}</option>)}
            </select>
            <Button size="sm" onClick={startReplay} disabled={running || !sel} data-testid="replay-go" className="h-8">
              {running ? <><Loader2 className="animate-spin" /> läuft…</> : <><Play /> Abspielen</>}
            </Button>
          </div>
        )}
      </div>

      {title && <div className="truncate text-sm font-medium" title={title}>{title}</div>}

      <div className={cn('relative overflow-hidden rounded-lg bg-black', mode !== 'video' && 'hidden')}>
        <video ref={vid} playsInline controls preload="auto" className="aspect-video w-full" />
        {needClick && (
          <button
            type="button"
            className="absolute inset-0 m-auto h-10 w-48 rounded-md bg-white/90 text-sm font-medium"
            onClick={() => { setNeedClick(false); if (vid.current) { vid.current.muted = false; vid.current.play().catch(() => {}) } }}
          >
            ▶ Klick zum Abspielen
          </button>
        )}
      </div>
      {mode === 'note' && <div className="rounded-lg border bg-muted/40 p-3 text-sm whitespace-pre-wrap">{noteText}</div>}
      {mode === 'none' && (
        <div className="flex aspect-video items-center justify-center rounded-lg border border-dashed p-4 text-center text-xs text-muted-foreground">
          Aufnahme wählen und abspielen: der Graph baut sich im Takt des Videos auf.
        </div>
      )}

      <div className={cn('min-h-12 rounded-lg border px-3 py-2 text-sm leading-snug', caption.idle ? 'text-muted-foreground' : 'bg-muted/30')} data-testid="caption">
        <Caption text={caption.text} quotes={caption.quotes} />
      </div>

      <div className="flex min-h-0 flex-1 flex-col">
        <div className="mb-1.5 flex items-center justify-between">
          <span className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">Erfasst</span>
          {status && <span className={cn('text-xs', status.err ? 'text-red-600' : 'text-emerald-700')}>{status.text}</span>}
        </div>
        <ScrollArea className="min-h-0 flex-1 rounded-lg border">
          <ul className="flex flex-col p-1.5 text-sm" data-testid="found-list">
            {found.length === 0 && <li className="p-2 text-xs text-muted-foreground">Noch nichts erfasst.</li>}
            {found.map((f, i) => (
              <li key={i} className={cn('flex items-center gap-2 rounded px-2 py-1', f.cls === 'p' && 'text-violet-700', f.cls === 'e' && 'text-amber-800')}>
                <small className="w-10 shrink-0 text-[11px] text-muted-foreground tabular-nums">{mmss(f.t)}</small>
                {f.cls === 'e' && <EventIcon type={f.icon ?? ''} className="size-3.5 shrink-0" />}
                <span className={cn('min-w-0 flex-1', f.cls === 'p' && 'rounded border border-dashed border-violet-300 px-1')}>{f.text}</span>
              </li>
            ))}
            <div ref={foundEnd} />
          </ul>
        </ScrollArea>
      </div>
    </div>
  )
}

/** Caption text with the quotes that produced a change highlighted. */
function Caption({ text, quotes }: { text: string; quotes: string[] }) {
  const qs = [...new Set(quotes.filter(q => q && text.includes(q)))]
  if (!qs.length) return <>{text}</>
  const re = new RegExp(`(${qs.map(q => q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`)
  return <>{text.split(re).map((part, i) => (qs.includes(part) ? <mark key={i} className="rounded bg-emerald-100 px-0.5 text-emerald-900">{part}</mark> : <span key={i}>{part}</span>))}</>
}
