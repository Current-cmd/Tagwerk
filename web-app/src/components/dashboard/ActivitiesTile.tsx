import { useState } from 'react'
import { CalendarClock, ChartGantt, Table2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Empty, PctBar } from '@/components/common'
import { addDays, fmtShort, weekday } from '@/lib/format'
import type { Activity, DayResponse, DaysResponse } from '@/lib/types'
import { cn } from '@/lib/utils'
import { Gantt } from './Gantt'

const LARGE_AT = 30
const maxIso = (a: string, b: string) => (a > b ? a : b)
const minIso = (a: string, b: string) => (a < b ? a : b)

interface Props {
  day: DayResponse
  days: DaysResponse
  selected: string | null
  onSelect: (id: string) => void
}

export function ActivitiesTile({ day, days, selected, onSelect }: Props) {
  const [view, setView] = useState<'gantt' | 'table'>('gantt')
  const large = day.activities.length > LARGE_AT
  const [focus, setFocus] = useState(true)
  const delayed = day.activities.filter(a => a.delay_d > 0 && !a.done).length
  // big schedules (Schependomlaan: 100 activities, 239 days): by default only what runs around the chosen day
  const windowed = large && focus
  const wFirst = windowed ? maxIso(days.first, addDays(day.date, -21)) : days.first
  const wLast = windowed ? minIso(days.last, addDays(day.date, 35)) : days.last
  const shown = windowed
    ? day.activities.filter(a => a.planned_start <= wLast && maxIso(a.baseline_finish, a.forecast_finish ?? a.baseline_finish) >= wFirst)
    : day.activities
  return (
    <Card className="flex min-h-0 flex-col gap-0 py-0" data-testid="tile-activities">
      <CardHeader className="border-b py-3.5">
        <CardTitle className="flex items-center gap-2">
          Vorgänge
          <Badge variant="secondary" className="tabular-nums">{day.activities.length}</Badge>
          {delayed > 0 && <Badge variant="destructive" className="tabular-nums">{delayed} im Verzug</Badge>}
          {day.is_future && <Badge variant="outline">nur Plan</Badge>}
        </CardTitle>
        <CardDescription>P6-Terminplan: Basisplan gegen Prognose, Stand Ende {weekday(day.date)} {fmtShort(day.date)}</CardDescription>
        <CardAction className="flex items-center gap-2">
          {large && (
            <Button variant={focus ? 'secondary' : 'outline'} size="sm" onClick={() => setFocus(f => !f)} title="Nur Vorgänge um den gewählten Tag (−3/+5 Wochen)">
              {focus ? `${shown.length} um den Tag` : `alle ${day.activities.length}`}
            </Button>
          )}
          <ToggleGroup type="single" variant="outline" size="sm" value={view} onValueChange={v => v && setView(v as 'gantt' | 'table')}>
            <ToggleGroupItem value="gantt" aria-label="Gantt"><ChartGantt /> Gantt</ToggleGroupItem>
            <ToggleGroupItem value="table" aria-label="Tabelle"><Table2 /> Tabelle</ToggleGroupItem>
          </ToggleGroup>
        </CardAction>
      </CardHeader>
      <CardContent className="min-h-0 flex-1 p-0">
        <ScrollArea className="h-full">
          <div className="p-3">
            {day.activities.length === 0 ? (
              <Empty>Keine Vorgänge im Terminplan.</Empty>
            ) : view === 'gantt' ? (
              <>
                <Gantt activities={shown} first={wFirst} last={wLast} date={day.date} today={day.today} selected={selected} onSelect={onSelect} />
                <Legend />
              </>
            ) : (
              <ActivityTable day={day} activities={shown} selected={selected} onSelect={onSelect} />
            )}
            <Separator className="my-3" />
            <Lookahead day={day} onSelect={onSelect} />
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}

function Legend() {
  const item = (cls: string, label: string) => (
    <span className="flex items-center gap-1.5"><i className={cn('inline-block rounded-sm', cls)} />{label}</span>
  )
  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 pl-1 text-[11px] text-muted-foreground">
      {item('h-1.5 w-4 bg-neutral-300', 'Basisplan')}
      {item('h-2.5 w-4 bg-sky-500', 'Prognose / Ist')}
      {item('h-2.5 w-4 bg-red-500', 'im Verzug')}
      {item('h-2.5 w-4 bg-emerald-500', 'fertig')}
      {item('h-2.5 w-4 bg-[repeating-linear-gradient(45deg,#fca5a5_0_2px,transparent_2px_4px)]', 'Verschiebung')}
      <span className="flex items-center gap-1.5"><i className="inline-block h-3 w-0.5 bg-red-500" />gewählter Tag</span>
    </div>
  )
}

function ActivityTable({ activities, selected, onSelect }: { day: DayResponse; activities: Activity[]; selected: string | null; onSelect: (id: string) => void }) {
  return (
    <Table data-testid="activity-table">
      <TableHeader>
        <TableRow>
          <TableHead className="w-14">ID</TableHead>
          <TableHead>Vorgang</TableHead>
          <TableHead>Gewerk</TableHead>
          <TableHead className="text-right">Start</TableHead>
          <TableHead className="text-right">Plan-Ende</TableHead>
          <TableHead className="text-right">Prognose</TableHead>
          <TableHead className="w-28">Ist / Soll</TableHead>
          <TableHead className="text-right">Verzug</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {activities.map(a => (
          <TableRow key={a.id} onClick={() => onSelect(a.id)} data-state={selected === a.id ? 'selected' : undefined} className="cursor-pointer">
            <TableCell className="text-xs text-muted-foreground tabular-nums">{a.id}</TableCell>
            <TableCell className="max-w-44 truncate font-medium">{a.name}</TableCell>
            <TableCell className="max-w-28 truncate text-muted-foreground">{a.trade ?? '–'}</TableCell>
            <TableCell className="text-right tabular-nums">{fmtShort(a.planned_start)}</TableCell>
            <TableCell className="text-right tabular-nums">{fmtShort(a.baseline_finish)}</TableCell>
            <TableCell className={cn('text-right tabular-nums', a.delay_d > 0 && 'text-red-600')}>{fmtShort(a.forecast_finish)}</TableCell>
            <TableCell>
              <div className="flex items-center gap-2">
                <PctBar pct={a.pct} planned={a.planned_pct} delayed={a.delay_d > 0} className="w-14" />
                <span className="text-xs tabular-nums">{Math.round(a.pct)}/{Math.round(a.planned_pct)}</span>
              </div>
            </TableCell>
            <TableCell className={cn('text-right tabular-nums', a.delay_d > 0 ? 'font-medium text-red-600' : 'text-muted-foreground')}>
              {a.delay_d > 0 ? `+${a.delay_d} AT` : '–'}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function Lookahead({ day, onSelect }: { day: DayResponse; onSelect: (id: string) => void }) {
  return (
    <div data-testid="lookahead">
      <div className="mb-2 flex items-center gap-2 text-sm font-medium">
        <CalendarClock className="size-4 text-muted-foreground" />
        Vorschau: nächste 3 Arbeitstage
      </div>
      <div className="grid grid-cols-3 gap-2">
        {day.lookahead.map(l => (
          <div key={l.date} className="min-w-0 rounded-lg border bg-muted/30 p-2.5">
            <div className="mb-1.5 text-xs font-semibold tabular-nums">{weekday(l.date)}, {fmtShort(l.date)}</div>
            {l.activities.length === 0 ? (
              <div className="text-xs text-muted-foreground">nichts geplant</div>
            ) : (
              <ul className="flex flex-col gap-1.5">
                {l.activities.map(a => (
                  <li key={a.id}>
                    <button type="button" onClick={() => onSelect(a.id)} className="w-full rounded text-left hover:bg-muted">
                      <div className="truncate text-xs font-medium">{a.name}</div>
                      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                        <span className="truncate">{a.trade}{a.zones.length ? ` · ${a.zones.join(', ')}` : ''}</span>
                        <span className="ml-auto shrink-0 tabular-nums">Soll {Math.round(a.planned_pct_by_end)} %</span>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
