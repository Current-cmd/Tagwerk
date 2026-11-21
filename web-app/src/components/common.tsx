import { AlertTriangle, CloudRain, Clock, HardHat, Truck, UserX, Zap } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { severityDe } from '@/lib/format'
import { cn } from '@/lib/utils'

const SEV_CLASS: Record<string, string> = {
  high: 'border-red-200 bg-red-50 text-red-700',
  medium: 'border-amber-200 bg-amber-50 text-amber-800',
  low: 'border-border bg-muted text-muted-foreground',
}

export function SeverityBadge({ severity, className }: { severity: string; className?: string }) {
  return (
    <Badge variant="outline" className={cn('font-medium', SEV_CLASS[severity] ?? SEV_CLASS.low, className)}>
      {severityDe(severity)}
    </Badge>
  )
}

const EV_ICON = { absence: UserX, delay: Clock, defect: AlertTriangle, weather: CloudRain, delivery: Truck, accident: HardHat }

export function EventIcon({ type, className }: { type: string; className?: string }) {
  const I = (EV_ICON as Record<string, typeof Zap>)[type] ?? Zap
  return <I className={cn('size-4', className)} />
}

/** Activity progress bar coloured like the graph nodes. */
export function PctBar({ pct, planned, delayed, className }: { pct: number; planned?: number; delayed?: boolean; className?: string }) {
  return (
    <div className={cn('relative h-1.5 w-full overflow-hidden rounded-full bg-muted', className)}>
      <div
        className={cn('absolute inset-y-0 left-0 rounded-full', pct >= 100 ? 'bg-emerald-500' : delayed ? 'bg-red-500' : 'bg-sky-500')}
        style={{ width: `${Math.min(100, pct)}%` }}
      />
      {planned != null && planned > 0 && planned < 100 && (
        <div className="absolute inset-y-0 w-0.5 bg-foreground/60" style={{ left: `${planned}%` }} />
      )}
    </div>
  )
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="flex h-full min-h-24 items-center justify-center rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">{children}</div>
}
