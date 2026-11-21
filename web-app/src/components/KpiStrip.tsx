import { CloudRain, CloudSun, Snowflake, Wind } from 'lucide-react'
import type { ReactNode } from 'react'
import { fmtShort, num } from '@/lib/format'
import type { DayResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

function Kpi({ label, children, sub, tone }: { label: string; children: ReactNode; sub?: ReactNode; tone?: 'bad' | 'good' }) {
  return (
    <div className="flex min-w-0 flex-1 flex-col justify-center rounded-lg border bg-card px-3.5 py-2">
      <div className="truncate text-[11px] font-medium tracking-wide text-muted-foreground uppercase">{label}</div>
      <div className={cn('flex items-baseline gap-1.5 truncate text-lg font-semibold tabular-nums', tone === 'bad' && 'text-red-600', tone === 'good' && 'text-emerald-600')}>
        {children}
      </div>
      {sub && <div className="truncate text-xs text-muted-foreground">{sub}</div>}
    </div>
  )
}

export function KpiStrip({ day }: { day: DayResponse }) {
  const k = day.kpi
  const w = day.weather
  const behind = !(day.info && !day.info.has_data) && k.pct_actual + 0.05 < k.pct_planned
  const WIcon = !w ? CloudSun : (w.tempC ?? 9) <= 0 ? Snowflake : (w.precipMm ?? 0) >= 1 ? CloudRain : (w.windKmh ?? 0) >= 40 ? Wind : CloudSun
  return (
    <div className="flex gap-2.5" data-testid="kpi-strip">
      <Kpi label="Fortschritt Ist / Soll" tone={behind ? 'bad' : undefined} sub={<Bar actual={k.pct_actual} planned={k.pct_planned} />}>
        {day.info && !day.info.has_data ? '–' : `${num(k.pct_actual)} %`}<span className="text-sm font-normal text-muted-foreground">/ {num(k.pct_planned)} %</span>
      </Kpi>
      <Kpi label="SPI" tone={k.spi == null ? undefined : k.spi < 0.95 ? 'bad' : k.spi >= 1 ? 'good' : undefined} sub="Termintreue (Ist ÷ Soll)">
        {k.spi == null ? '–' : num(k.spi, 2)}
      </Kpi>
      <Kpi label="Prognose-Ende" tone={k.delay_d > 0 ? 'bad' : 'good'} sub={`Basisplan ${fmtShort(k.baseline_finish)}`}>
        {fmtShort(k.forecast_finish)}
        <span className="text-sm font-medium">{k.delay_d > 0 ? `+${k.delay_d} AT Verzug` : 'im Plan'}</span>
      </Kpi>
      <Kpi label="Offene Mängel" tone={k.open_defects > 0 ? 'bad' : undefined} sub={k.open_defects ? 'aus Aufnahmen gemeldet' : 'keine gemeldet'}>
        {k.open_defects}
      </Kpi>
      <Kpi
        label={day.date === day.today ? 'Wetter heute' : 'Wetter am Tag'}
        sub={w ? `${num(w.precipMm)} mm · Wind ${num(w.windKmh, 0)} km/h` : day.is_future ? 'keine Messung (Zukunft)' : 'keine Messung'}
      >
        <WIcon className="size-4 self-center text-muted-foreground" />
        {w && w.tempC != null ? `${num(w.tempC)} °C` : '–'}
      </Kpi>
    </div>
  )
}

function Bar({ actual, planned }: { actual: number; planned: number }) {
  return (
    <span className="relative mt-1 block h-1.5 w-full overflow-hidden rounded-full bg-muted">
      <span className="absolute inset-y-0 left-0 rounded-full bg-foreground/80" style={{ width: `${Math.min(100, actual)}%` }} />
      <span className="absolute inset-y-[-2px] w-0.5 bg-red-500" style={{ left: `${Math.min(100, planned)}%` }} title="Soll" />
    </span>
  )
}
