import { useEffect, useState } from 'react'
import { Box, Camera, FileText, MapPin, Mic, Sparkles, Video } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Empty, EventIcon, SeverityBadge } from '@/components/common'
import { actionDe, evidenceDe, fmtTime, kindDe, stateDe } from '@/lib/format'
import type { DayResponse, Recording } from '@/lib/types'

const KIND_ICON: Record<string, typeof Video> = { video: Video, photo: Camera, voice: Mic, note: FileText }

interface Props {
  day: DayResponse
  focusRec: string | null
  onOpenActivity: (id: string) => void
  onOpenScan: (captureId: string) => void
}

export function RecordingsTile({ day, focusRec, onOpenActivity, onOpenScan }: Props) {
  const [open, setOpen] = useState<string>(focusRec ?? '')
  useEffect(() => {
    if (focusRec) {
      setOpen(focusRec)
      setTimeout(() => document.getElementById(`rec-${focusRec}`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), 120)
    }
  }, [focusRec, day.date])

  const actName = new Map(day.activities.map(a => [a.id, a.name]))

  return (
    <Card className="flex min-h-0 flex-col gap-0 py-0" data-testid="tile-recordings">
      <CardHeader className="border-b py-3.5">
        <CardTitle className="flex items-center gap-2">
          Aufnahmen des Tages
          <Badge variant="secondary" className="tabular-nums">{day.recordings.length}</Badge>
        </CardTitle>
        <CardDescription>Was vor Ort aufgenommen wurde und was der Agent daraus erkannt hat</CardDescription>
      </CardHeader>
      <CardContent className="min-h-0 flex-1 p-0">
        <ScrollArea className="h-full">
          <div className="p-3">
            {day.recordings.length === 0 ? (
              <Empty>{day.is_future ? 'Zukünftiger Tag: noch keine Aufnahmen.' : 'Keine Aufnahmen an diesem Tag.'}</Empty>
            ) : (
              <Accordion type="single" collapsible value={open} onValueChange={setOpen} className="flex flex-col gap-2">
                {day.recordings.map(r => (
                  <RecordingItem key={r.capture_id} r={r} date={day.date} onOpenScan={onOpenScan} actName={actName} onOpenActivity={onOpenActivity} highlight={r.capture_id === focusRec} />
                ))}
              </Accordion>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}

function RecordingItem({ r, date, actName, onOpenActivity, onOpenScan, highlight }: { r: Recording; date: string; onOpenScan: (c: string) => void; actName: Map<string, string>; onOpenActivity: (id: string) => void; highlight: boolean }) {
  const Icon = KIND_ICON[r.kind] ?? FileText
  const acts = [...new Set([...r.changes, ...r.proposals, ...r.absences, ...r.events].map(x => x.activity_id).filter(Boolean) as string[])]
  const findings = r.changes.length + r.proposals.length + r.absences.length + r.events.length
  return (
    <AccordionItem
      value={r.capture_id}
      id={`rec-${r.capture_id}`}
      className={`rounded-lg border bg-card px-3 data-[state=open]:shadow-sm ${highlight ? 'ring-2 ring-sky-400/50' : ''}`}
    >
      <AccordionTrigger className="py-2.5 hover:no-underline">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted">
            <Icon className="size-4 text-muted-foreground" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 text-sm font-medium">
              <span className="tabular-nums">{fmtTime(date, r.time)}</span>
              <span className="text-muted-foreground">·</span>
              <span className="truncate">{kindDe(r.kind)}</span>
            </div>
            <div className="flex items-center gap-1 truncate text-xs text-muted-foreground">
              <MapPin className="size-3" /> {r.zone_name ?? r.zone_id ?? 'ohne Ort'}
            </div>
          </div>
          {findings > 0 && (
            <Badge variant="outline" className="shrink-0 tabular-nums">
              <Sparkles className="size-3" /> {findings}
            </Badge>
          )}
        </div>
      </AccordionTrigger>
      <AccordionContent className="flex flex-col gap-3 pb-3">
        {r.has_3d && (
          <Button variant="outline" size="sm" className="self-start" onClick={() => onOpenScan(r.capture_id)} data-testid="open-3d">
            <Box /> 3D ansehen
          </Button>
        )}
        {r.video && (
          <video src={r.video} controls playsInline preload="none" className="aspect-video w-full rounded-md bg-black" />
        )}
        {r.photos.length > 0 && (
          <div className="flex gap-2 overflow-x-auto">
            {r.photos.map(p => <img key={p} src={p} alt="" className="h-20 rounded-md border object-cover" />)}
          </div>
        )}
        {(r.transcript || r.note) && (
          <blockquote className="rounded-md border-l-2 border-sky-400 bg-muted/50 px-3 py-2 text-sm italic">
            {r.transcript ?? r.note}
            {!r.transcript && r.note && <span className="ml-1 text-xs not-italic text-muted-foreground">(Notiz)</span>}
          </blockquote>
        )}

        {r.changes.length > 0 && (
          <Section title="Erfasst">
            {r.changes.map((c, i) => (
              <li key={i} className="flex flex-col gap-0.5">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="font-medium">{c.element_name}</span>
                  <span className="text-muted-foreground">→</span>
                  <Badge variant="secondary">{stateDe(c.state)}</Badge>
                  <span className="text-xs text-muted-foreground">{actionDe(c.action)}{c.evidence ? ` · ${evidenceDe(c.evidence)}` : ''}</span>
                </div>
                {c.quote && <div className="text-xs text-muted-foreground">„{c.quote}“</div>}
              </li>
            ))}
          </Section>
        )}
        {r.proposals.length > 0 && (
          <Section title="Vorschläge (nur Bild, zu bestätigen)">
            {r.proposals.map((p, i) => (
              <li key={i} className="flex items-center gap-1.5">
                <span className="rounded border border-dashed border-violet-400 px-1.5 text-violet-700">{p.element_name}</span>
                <span className="text-muted-foreground">→ {stateDe(p.state)}?</span>
              </li>
            ))}
          </Section>
        )}
        {r.absences.length > 0 && (
          <Section title="Ausfälle">
            {r.absences.map((a, i) => (
              <li key={i} className="flex items-center gap-1.5">
                <EventIcon type="absence" className="text-amber-600" />
                {a.count}× {a.trade} {a.reason}
              </li>
            ))}
          </Section>
        )}
        {r.events.length > 0 && (
          <Section title="Ereignisse">
            {r.events.map((e, i) => (
              <li key={i} className="flex items-center gap-1.5">
                <EventIcon type={e.type} className="shrink-0 text-muted-foreground" />
                <span className="flex-1">{e.text}</span>
                <SeverityBadge severity={e.severity} />
              </li>
            ))}
          </Section>
        )}
        {acts.length > 0 && (
          <Section title="Verknüpfte Vorgänge">
            <li className="flex flex-wrap gap-1.5">
              {acts.map(id => (
                <button key={id} type="button" onClick={() => onOpenActivity(id)} className="rounded-md border px-2 py-0.5 text-xs hover:bg-muted">
                  <span className="text-muted-foreground">{id}</span> {actName.get(id) ?? ''}
                </button>
              ))}
            </li>
          </Section>
        )}
        {findings === 0 && !r.transcript && !r.note && <div className="text-xs text-muted-foreground">Nichts erkannt.</div>}
      </AccordionContent>
    </AccordionItem>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">{title}</div>
      <ul className="flex flex-col gap-1.5 text-sm">{children}</ul>
    </div>
  )
}
