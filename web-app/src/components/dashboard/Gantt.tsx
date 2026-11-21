import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { addDays, dayDiff, fmtShort, isWeekend, monthName, toDate } from '@/lib/format'
import type { Activity } from '@/lib/types'
import { cn } from '@/lib/utils'

const LABEL_W = 156
const ROW_H = 30
const HEAD_H = 32
const MIN_DAY_W = 7

interface Props {
  activities: Activity[]
  first: string
  last: string
  date: string
  today: string
  selected: string | null
  onSelect: (id: string) => void
}

/** Plain SVG Gantt: thin grey baseline bar, thick forecast bar with progress fill, links, day line. */
export function Gantt({ activities, first, last, date, today, selected, onSelect }: Props) {
  const box = useRef<HTMLDivElement>(null)
  const [w, setW] = useState(600)
  useLayoutEffect(() => {
    const el = box.current
    if (!el) return
    const ro = new ResizeObserver(() => setW(el.clientWidth))
    ro.observe(el)
    setW(el.clientWidth)
    return () => ro.disconnect()
  }, [])

  const nDays = dayDiff(first, last) + 1
  const avail = Math.max(200, w - LABEL_W)
  const dw = Math.max(avail / nDays, MIN_DAY_W) // long plans scroll horizontally
  const chartW = dw * nDays
  const scroller = useRef<HTMLDivElement>(null)
  useEffect(() => { // keep the selected day in view
    const sc = scroller.current
    if (!sc || chartW <= avail) return
    const target = dayDiff(first, date) * dw - sc.clientWidth / 2
    sc.scrollTo({ left: Math.max(0, target), behavior: 'smooth' })
  }, [date, first, dw, chartW, avail])
  const x = (iso: string) => dayDiff(first, iso) * dw // start of day
  const xe = (iso: string) => x(iso) + dw // end of day
  const H = HEAD_H + activities.length * ROW_H
  const row = new Map(activities.map((a, i) => [a.id, i]))
  const yMid = (i: number) => HEAD_H + i * ROW_H + ROW_H / 2 + 4

  const days: string[] = []
  for (let i = 0; i < nDays; i++) days.push(addDays(first, i))
  const labelEvery = dw >= 18 ? 1 : dw >= 10 ? 2 : 7
  const shadeWeekends = dw >= 4

  return (
    <div ref={box} className="relative w-full select-none" data-testid="gantt">
      <div className="flex">
        {/* label column */}
        <div className="shrink-0" style={{ width: LABEL_W }}>
          <div style={{ height: HEAD_H }} className="flex items-end pb-1 pl-1 text-[11px] font-medium text-muted-foreground">Vorgang</div>
          {activities.map(a => (
            <button
              key={a.id}
              type="button"
              onClick={() => onSelect(a.id)}
              className={cn(
                'flex w-full items-center gap-1.5 rounded-l-md pr-2 pl-1 text-left text-xs hover:bg-muted',
                selected === a.id && 'bg-muted',
              )}
              style={{ height: ROW_H }}
              data-testid={`gantt-row-${a.id}`}
            >
              <span className="w-10 shrink-0 text-[10px] text-muted-foreground tabular-nums">{a.id}</span>
              <span className={cn('truncate', a.delay_d > 0 && !a.done && 'text-red-700')}>{a.name}</span>
            </button>
          ))}
        </div>

        <div ref={scroller} className="min-w-0 flex-1 overflow-x-auto overflow-y-hidden">
        <svg width={chartW} height={H} className="block">
          <defs>
            <marker id="g-arrow" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="5" markerHeight="5" orient="auto">
              <path d="M0,0 L6,3 L0,6 z" className="fill-muted-foreground/60" />
            </marker>
            <pattern id="g-hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="2" height="5" className="fill-red-300/70" />
            </pattern>
          </defs>

          {/* weekend shading + header */}
          {days.map((d, i) => (
            <g key={d}>
              {shadeWeekends && isWeekend(d) && <rect x={i * dw} y={HEAD_H} width={dw} height={H - HEAD_H} className="fill-muted/70" />}
              {(labelEvery === 7 ? toDate(d).getUTCDay() === 1 : i % labelEvery === 0) && (
                <text x={i * dw + dw / 2} y={HEAD_H - 6} textAnchor="middle" className={cn('text-[10px] tabular-nums', isWeekend(d) ? 'fill-muted-foreground/60' : 'fill-muted-foreground')}>
                  {toDate(d).getUTCDate()}
                </text>
              )}
              {(i === 0 || toDate(d).getUTCDate() === 1) && (
                <text x={i * dw + 2} y={11} className="fill-foreground text-[10px] font-medium">{monthName(d)}</text>
              )}
            </g>
          ))}
          <line x1={0} x2={chartW} y1={HEAD_H - 0.5} y2={HEAD_H - 0.5} className="stroke-border" />
          {activities.map((_, i) => (
            <line key={i} x1={0} x2={chartW} y1={HEAD_H + (i + 1) * ROW_H - 0.5} y2={HEAD_H + (i + 1) * ROW_H - 0.5} className="stroke-border/60" />
          ))}

          {/* links (forecast finish of predecessor -> forecast start of successor) */}
          {activities.flatMap(a =>
            a.predecessors.map(p => {
              const pi = row.get(p), ai = row.get(a.id)
              if (pi == null || ai == null) return null
              const pa = activities[pi]
              const x1 = xe(pa.forecast_finish ?? pa.baseline_finish), y1 = yMid(pi)
              const x2 = x(a.forecast_start ?? a.planned_start), y2 = yMid(ai)
              const d = x2 >= x1 + 8
                ? `M${x1},${y1} h4 V${y2} H${x2 - 1}`
                : `M${x1},${y1} h4 V${y2 - ROW_H / 2 + 2} H${x2 - 6} V${y2} H${x2 - 1}`
              return <path key={`${p}-${a.id}`} d={d} fill="none" className="stroke-muted-foreground/40" strokeWidth={1} markerEnd="url(#g-arrow)" />
            }),
          )}

          {/* bars */}
          {activities.map((a, i) => {
            const y = HEAD_H + i * ROW_H
            const bx = x(a.planned_start), bw = Math.max(2, xe(a.baseline_finish) - bx)
            const fs = a.forecast_start ?? a.planned_start, ff = a.forecast_finish ?? a.baseline_finish
            const fx = x(fs), fw = Math.max(3, xe(ff) - fx)
            const delayed = a.delay_d > 0 && !a.done
            const tone = a.done ? 'emerald' : delayed ? 'red' : 'sky'
            const fill = { emerald: 'fill-emerald-500', red: 'fill-red-500', sky: 'fill-sky-500' }[tone]
            const bg = { emerald: 'fill-emerald-100', red: 'fill-red-100', sky: 'fill-sky-100' }[tone]
            const slip = ff > a.baseline_finish ? { x: xe(a.baseline_finish), w: xe(ff) - xe(a.baseline_finish) } : null
            return (
              <g key={a.id} className="cursor-pointer" onClick={() => onSelect(a.id)}>
                <title>
                  {`${a.id} ${a.name}\nPlan ${fmtShort(a.planned_start)}–${fmtShort(a.baseline_finish)}\nPrognose ${fmtShort(fs)}–${fmtShort(ff)}\n${a.pct} % (Soll ${a.planned_pct} %)${a.delay_d ? `\nVerzug ${a.delay_d} AT` : ''}`}
                </title>
                <rect x={0} y={y} width={chartW} height={ROW_H} className={cn('fill-transparent hover:fill-muted/40', selected === a.id && 'fill-muted/60')} />
                <rect x={bx} y={y + 5} width={bw} height={5} rx={2} className="fill-neutral-300" />
                {slip && <rect x={slip.x} y={y + 12} width={slip.w} height={12} rx={2} fill="url(#g-hatch)" />}
                <rect x={fx} y={y + 12} width={fw} height={12} rx={3} className={bg} />
                <rect x={fx} y={y + 12} width={(fw * Math.min(100, a.pct)) / 100} height={12} rx={3} className={fill} />
                {fw > 34 && (
                  <text x={fx + fw + 4} y={y + 22} className="fill-muted-foreground text-[10px] tabular-nums">{Math.round(a.pct)} %</text>
                )}
              </g>
            )
          })}

          {/* project today (dashed) and the selected day (solid) */}
          {today !== date && today >= first && today <= last && (
            <line x1={xe(today)} x2={xe(today)} y1={HEAD_H - 4} y2={H} strokeDasharray="3 3" className="stroke-muted-foreground" />
          )}
          {date >= first && date <= last && (
            <g>
              <line x1={xe(date)} x2={xe(date)} y1={HEAD_H - 4} y2={H} strokeWidth={1.5} className="stroke-red-500" />
              <circle cx={xe(date)} cy={HEAD_H - 4} r={3} className="fill-red-500" />
            </g>
          )}
        </svg>
        </div>
      </div>
    </div>
  )
}
