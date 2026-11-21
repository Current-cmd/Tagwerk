import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Empty, EventIcon, SeverityBadge } from '@/components/common'
import { eventTypeDe, fmtShort, weekday } from '@/lib/format'
import type { DayResponse, ProjectEvent } from '@/lib/types'
import { cn } from '@/lib/utils'

const ICON_TONE: Record<string, string> = {
  weather: 'bg-sky-50 text-sky-700', absence: 'bg-amber-50 text-amber-700', defect: 'bg-red-50 text-red-700',
  delay: 'bg-orange-50 text-orange-700', accident: 'bg-red-50 text-red-700', delivery: 'bg-violet-50 text-violet-700',
}

interface Props {
  day: DayResponse
  onOpenActivity: (id: string) => void
  onJumpRecording: (captureId: string, date: string) => void
}

export function EventsTile({ day, onOpenActivity, onJumpRecording }: Props) {
  const actName = new Map(day.activities.map(a => [a.id, a.name]))
  const todays = day.events.filter(e => e.date === day.date).length
  return (
    <Card className="flex min-h-0 flex-col gap-0 py-0" data-testid="tile-events">
      <CardHeader className="border-b py-3.5">
        <CardTitle className="flex items-center gap-2">
          Ereignisse
          <Badge variant="secondary" className="tabular-nums">{day.events.length}</Badge>
          {todays > 0 && <Badge variant="outline" className="tabular-nums">{todays} heute</Badge>}
        </CardTitle>
        <CardDescription>Ausfälle, Mängel, Verzug und Wetter, neueste zuerst</CardDescription>
      </CardHeader>
      <CardContent className="min-h-0 flex-1 p-0">
        <ScrollArea className="h-full">
          <div className="p-3">
            {day.events.length === 0 ? (
              <Empty>Bis zu diesem Tag keine Ereignisse.</Empty>
            ) : (
              <ul className="flex flex-col gap-1.5">
                {day.events.map(e => (
                  <EventRow key={e.id} e={e} current={e.date === day.date} actName={actName} onOpenActivity={onOpenActivity} onJumpRecording={onJumpRecording} />
                ))}
              </ul>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}

function EventRow({ e, current, actName, onOpenActivity, onJumpRecording }: {
  e: ProjectEvent; current: boolean; actName: Map<string, string>
  onOpenActivity: (id: string) => void; onJumpRecording: (c: string, d: string) => void
}) {
  return (
    <li className={cn('flex gap-2.5 rounded-lg border p-2.5', current ? 'bg-card' : 'bg-muted/20')}>
      <div className={cn('flex size-7 shrink-0 items-center justify-center rounded-md', ICON_TONE[e.type] ?? 'bg-muted text-muted-foreground')}>
        <EventIcon type={e.type} className="size-3.5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start gap-2">
          <span className="flex-1 text-sm leading-snug">{e.text}</span>
          <SeverityBadge severity={e.severity} className="shrink-0" />
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-muted-foreground">
          <span className="tabular-nums">{weekday(e.date)} {fmtShort(e.date)}</span>
          <span>· {eventTypeDe(e.type)}</span>
          {e.activity_id && (
            <button type="button" className="hover:text-foreground hover:underline" onClick={() => onOpenActivity(e.activity_id!)}>
              · {e.activity_id} {actName.get(e.activity_id) ?? ''}
            </button>
          )}
          {e.capture_id && (
            <button type="button" className="hover:text-foreground hover:underline" onClick={() => onJumpRecording(e.capture_id!, e.date)}>
              · Aufnahme
            </button>
          )}
        </div>
      </div>
    </li>
  )
}
