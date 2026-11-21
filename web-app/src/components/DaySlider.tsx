import { useEffect } from 'react'
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { fmtLong, fmtShort, weekday } from '@/lib/format'
import type { DaysResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

interface Props {
  days: DaysResponse
  date: string
  onChange: (date: string) => void
}

export function DaySlider({ days, date, onChange }: Props) {
  const list = days.days
  const idx = Math.max(0, list.findIndex(d => d.date === date))
  const go = (i: number) => onChange(list[Math.min(list.length - 1, Math.max(0, i))].date)
  const todayIdx = list.findIndex(d => d.date === days.today)
  const n = Math.max(1, list.length - 1)

  // ←/→ step through the days unless focus is in something that uses the arrows itself
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
      if (e.altKey || e.metaKey || e.ctrlKey) return
      const t = e.target as HTMLElement | null
      if (t && (t.closest('input, textarea, select, video, [role="slider"], [contenteditable="true"], [role="dialog"]'))) return
      e.preventDefault()
      go(idx + (e.key === 'ArrowLeft' ? -1 : 1))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const cur = list[idx]
  const isFuture = date > days.today

  return (
    <div className="flex items-center gap-3" data-testid="day-slider">
      <div className="flex items-center gap-1">
        <Button variant="outline" size="icon-sm" onClick={() => go(idx - 1)} disabled={idx === 0} aria-label="Vorheriger Tag">
          <ChevronLeft />
        </Button>
        <Button variant="outline" size="icon-sm" onClick={() => go(idx + 1)} disabled={idx === list.length - 1} aria-label="Nächster Tag">
          <ChevronRight />
        </Button>
      </div>

      <div className="w-[156px] shrink-0 leading-tight">
        <div className="flex items-center gap-1.5 text-sm font-semibold tabular-nums" data-testid="current-date">
          <CalendarDays className="size-3.5 text-muted-foreground" />
          {fmtLong(date)}
        </div>
        <div className="text-xs text-muted-foreground">
          {date === days.today ? 'Heute (Stichtag)' : isFuture ? 'Plan (Zukunft)' : cur && !cur.workday ? 'Wochenende' : 'Rückblick'}
          {cur && cur.recordings > 0 && ` · ${cur.recordings} Aufn.`}
        </div>
      </div>

      <div className="relative min-w-0 flex-1 px-1.5 pt-1 pb-5">
        {/* future part of the range (plan only), hatched */}
        {todayIdx >= 0 && todayIdx < list.length - 1 && (
          <div className="pointer-events-none absolute inset-x-1.5 top-[7px] h-[7px]">
            <div
              className="absolute inset-y-0 right-0 rounded-full bg-[repeating-linear-gradient(135deg,var(--color-border)_0_2px,transparent_2px_5px)]"
              style={{ left: `${(todayIdx / n) * 100}%` }}
            />
          </div>
        )}
        <Slider
          min={0}
          max={list.length - 1}
          step={1}
          value={[idx]}
          onValueChange={v => go(v[0])}
          aria-label="Tag wählen"
          className="relative z-10"
        />
        {/* tick row: weekends lighter, dots on days with recordings, today marker */}
        <div className="pointer-events-none absolute inset-x-1.5 top-[18px] h-4">
          {list.map((d, i) => {
            const left = `${(i / n) * 100}%`
            return (
              <div key={d.date} className="absolute -translate-x-1/2" style={{ left }}>
                {d.recordings > 0 ? (
                  <span className={cn('block size-1.5 rounded-full', d.date === date ? 'bg-primary' : 'bg-sky-500')} />
                ) : (
                  <span className={cn('mx-auto block h-1 w-px', d.workday ? 'bg-border' : 'bg-transparent')} />
                )}
              </div>
            )
          })}
        </div>
        <div className="absolute inset-x-1.5 top-[26px] h-3 text-[10px] text-muted-foreground tabular-nums">
          <span className="absolute left-0">{fmtShort(days.first)}</span>
          <span className="absolute right-0">{fmtShort(days.last)}</span>
          {todayIdx >= 0 && (
            <Tooltip>
              <TooltipTrigger asChild>
                <span
                  className="absolute -translate-x-1/2 cursor-default rounded bg-foreground px-1 font-medium text-background"
                  style={{ left: `${(todayIdx / n) * 100}%` }}
                >
                  Heute
                </span>
              </TooltipTrigger>
              <TooltipContent>Stichtag {weekday(days.today)}, {fmtShort(days.today)}</TooltipContent>
            </Tooltip>
          )}
        </div>
      </div>

      <Button variant={date === days.today ? 'secondary' : 'outline'} size="sm" onClick={() => onChange(days.today)}>
        Heute
      </Button>
    </div>
  )
}
