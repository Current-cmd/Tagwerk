import { ArrowRight, Film, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { PctBar } from '@/components/common'
import { fmtLong, fmtShort } from '@/lib/format'
import type { Activity, DayResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

interface Props {
  day: DayResponse
  activityId: string | null
  onClose: () => void
  onSelect: (id: string) => void
  onJumpRecording: (captureId: string) => Promise<void>
}

export function ActivitySheet({ day, activityId, onClose, onSelect, onJumpRecording }: Props) {
  const a = day.activities.find(x => x.id === activityId) ?? null
  return (
    <Sheet open={!!a} onOpenChange={o => !o && onClose()}>
      <SheetContent className="w-[440px] gap-0 sm:max-w-[440px]" data-testid="activity-sheet">
        {a && <Body a={a} day={day} onSelect={onSelect} onJumpRecording={onJumpRecording} />}
      </SheetContent>
    </Sheet>
  )
}

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1 text-sm">
      <span className="text-muted-foreground">{k}</span>
      <span className="text-right tabular-nums">{children}</span>
    </div>
  )
}

function Body({ a, day, onSelect, onJumpRecording }: { a: Activity; day: DayResponse; onSelect: (id: string) => void; onJumpRecording: (c: string) => Promise<void> }) {
  const [busy, setBusy] = useState<string | null>(null)
  const name = new Map(day.activities.map(x => [x.id, x.name]))
  const successors = day.activities.filter(x => x.predecessors.includes(a.id))
  const delayed = a.delay_d > 0 && !a.done
  return (
    <>
      <SheetHeader className="border-b">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="tabular-nums">{a.id}</span>
          {a.wbs && <span>· WBS {a.wbs}</span>}
          {a.trade && <span>· {a.trade}</span>}
        </div>
        <SheetTitle className="text-lg">{a.name}</SheetTitle>
        <SheetDescription className="flex flex-wrap gap-1.5">
          {a.done ? <Badge className="bg-emerald-600">fertig</Badge> : delayed ? <Badge variant="destructive">+{a.delay_d} AT Verzug</Badge> : <Badge variant="secondary">im Plan</Badge>}
          {!a.tracked && <Badge variant="outline">nicht verfolgt</Badge>}
          {day.is_future && <Badge variant="outline">Stand {fmtShort(day.today)} (Plan)</Badge>}
        </SheetDescription>
      </SheetHeader>

      <div className="flex-1 overflow-y-auto px-4 py-3">
        <div className="mb-1 flex items-baseline justify-between">
          <span className="text-sm font-medium">Fortschritt</span>
          <span className="text-sm tabular-nums">
            <b>{a.pct.toLocaleString('de-DE', { maximumFractionDigits: 1 })} %</b>
            <span className="text-muted-foreground"> / Soll {a.planned_pct.toLocaleString('de-DE', { maximumFractionDigits: 1 })} %</span>
          </span>
        </div>
        <PctBar pct={a.pct} planned={a.planned_pct} delayed={delayed} className="h-2" />

        <Separator className="my-3" />
        <Row k="Geplanter Start">{fmtLong(a.planned_start)}</Row>
        <Row k="Basisplan-Ende">{fmtLong(a.baseline_finish)}</Row>
        <Row k="Prognose Start">{fmtLong(a.forecast_start)}</Row>
        <Row k="Prognose-Ende"><span className={cn(delayed && 'font-medium text-red-600')}>{fmtLong(a.forecast_finish)}</span></Row>
        <Row k="Verzug">{a.delay_d > 0 ? `${a.delay_d} Arbeitstage` : 'keiner'}</Row>
        {a.cause && <Row k="Ursache"><span className="text-red-700">{a.cause}</span></Row>}

        <Separator className="my-3" />
        <h4 className="mb-1.5 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">GAEB-Positionen</h4>
        {a.gaeb.length === 0 ? <p className="text-sm text-muted-foreground">keine</p> : (
          <ul className="flex flex-col gap-1">
            {a.gaeb.map(g => (
              <li key={g.oz} className="flex gap-2 text-sm"><span className="shrink-0 font-mono text-xs text-muted-foreground">{g.oz}</span>{g.text}</li>
            ))}
          </ul>
        )}

        <h4 className="mt-3 mb-1.5 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">Orte</h4>
        <div className="flex flex-wrap gap-1.5">
          {a.zones.length ? a.zones.map(z => <Badge key={z} variant="outline">{z}</Badge>) : <span className="text-sm text-muted-foreground">keine</span>}
        </div>

        <h4 className="mt-3 mb-1.5 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
          Aufnahmen {a.last_recording && <span className="normal-case">· zuletzt {fmtShort(a.last_recording)}</span>}
        </h4>
        {a.recordings.length === 0 ? <p className="text-sm text-muted-foreground">noch keine</p> : (
          <ul className="flex flex-col gap-1" data-testid="sheet-recordings">
            {[...a.recordings].reverse().map(cid => (
              <li key={cid}>
                <button
                  type="button"
                  className="flex w-full items-center gap-2 rounded-md border px-2 py-1.5 text-left text-sm hover:bg-muted"
                  onClick={async () => { setBusy(cid); try { await onJumpRecording(cid) } finally { setBusy(null) } }}
                >
                  {busy === cid ? <Loader2 className="size-3.5 animate-spin" /> : <Film className="size-3.5 text-muted-foreground" />}
                  <span className="flex-1 truncate font-mono text-xs">{cid}</span>
                  <span className="text-xs text-muted-foreground">zum Tag</span>
                  <ArrowRight className="size-3.5 text-muted-foreground" />
                </button>
              </li>
            ))}
          </ul>
        )}

        <h4 className="mt-3 mb-1.5 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">Vorgänger / Nachfolger</h4>
        <div className="flex flex-col gap-1 text-sm">
          {a.predecessors.length === 0 && successors.length === 0 && <span className="text-muted-foreground">keine</span>}
          {a.predecessors.map(p => (
            <button key={p} type="button" className="text-left hover:underline" onClick={() => onSelect(p)}>
              <span className="text-muted-foreground">← {p}</span> {name.get(p) ?? ''}
            </button>
          ))}
          {successors.map(s => (
            <button key={s.id} type="button" className="text-left hover:underline" onClick={() => onSelect(s.id)}>
              <span className="text-muted-foreground">→ {s.id}</span> {s.name}
            </button>
          ))}
        </div>
      </div>
    </>
  )
}
