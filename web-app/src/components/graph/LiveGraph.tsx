import { useMemo, useState } from 'react'
import { Maximize2, PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Toggle } from '@/components/ui/toggle'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { fmtShort, weekday } from '@/lib/format'
import type { TaskGraph as TG } from '@/lib/types'
import { cn } from '@/lib/utils'
import { ReplayPanel } from './ReplayPanel'
import { LARGE_GRAPH_AT, TaskGraph, fitGraph, focusGraph } from './TaskGraph'

const COLUMNS = ['GAEB-Position', 'P6-Vorgang', 'Ort', 'Aufnahme', 'Ereignis / Vorschlag']

function Swatch({ className, label }: { className: string; label: string }) {
  return <span className="flex items-center gap-1.5 whitespace-nowrap"><i className={cn('inline-block size-3 rounded-[3px] border', className)} />{label}</span>
}

export function LiveGraph({ graph, onSelectActivity }: { graph: TG; onSelectActivity: (id: string) => void }) {
  const [panel, setPanel] = useState(true)
  const [all, setAll] = useState(false)
  const nActs = graph.nodes.filter(n => n.type === 'activity').length
  const large = nActs > LARGE_GRAPH_AT
  const shown = useMemo(() => focusGraph(graph, all), [graph, all])
  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    shown.nodes.forEach(n => { c[n.type] = (c[n.type] ?? 0) + 1 })
    return c
  }, [shown])

  return (
    <div className="flex min-h-0 flex-1 gap-3" data-testid="live-graph">
      {panel && (
        <Card className="w-[340px] shrink-0 gap-0 overflow-hidden py-0 2xl:w-[400px]">
          <ReplayPanel onActivity={() => setPanel(true)} />
        </Card>
      )}
      <Card className="relative flex min-w-0 flex-1 flex-col gap-0 overflow-hidden py-0">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 border-b px-3 py-2 text-xs text-muted-foreground">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon-sm" onClick={() => setPanel(p => !p)} aria-label="Video-Panel ein-/ausblenden" data-testid="panel-toggle">
                {panel ? <PanelLeftClose /> : <PanelLeftOpen />}
              </Button>
            </TooltipTrigger>
            <TooltipContent>Video-Panel {panel ? 'ausblenden' : 'einblenden'}</TooltipContent>
          </Tooltip>
          <span className="font-medium text-foreground">Aufgaben-Graph · {weekday(graph.date)} {fmtShort(graph.date)}</span>
          <span className="tabular-nums">{counts.activity ?? 0} Vorgänge · {counts.recording ?? 0} Aufnahmen · {(counts.event ?? 0) + (counts.proposal ?? 0)} Ereignisse/Vorschläge</span>
          <div className="ml-auto flex flex-wrap items-center gap-3">
            <Swatch className="border-neutral-300 bg-neutral-100" label="nicht begonnen" />
            <Swatch className="border-amber-500 bg-amber-100" label="in Arbeit" />
            <Swatch className="border-green-600 bg-green-100" label="fertig" />
            <Swatch className="border-2 border-red-600 bg-white" label="verspätet" />
            <Swatch className="border-blue-700 bg-blue-600" label="Aufnahme" />
            <Swatch className="border-dashed border-violet-500 bg-violet-50" label="Vorschlag" />
            {large && (
              <Toggle size="sm" variant="outline" pressed={all} onPressedChange={setAll} title="Große Projekte: standardmäßig nur Vorgänge um den Tag">
                alle {nActs} Vorgänge
              </Toggle>
            )}
            <Button variant="outline" size="icon-sm" onClick={fitGraph} aria-label="Einpassen"><Maximize2 /></Button>
          </div>
        </div>
        <div className="flex items-center gap-2 border-b bg-muted/30 px-3 py-1 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
          {COLUMNS.map((c, i) => <span key={c} className="whitespace-nowrap">{i > 0 && <span className="mr-2 text-muted-foreground/50">→</span>}{c}</span>)}
          <span className="ml-auto hidden normal-case tracking-normal xl:inline">Klick auf einen Vorgang öffnet die Details</span>
        </div>
        <div className="relative min-h-0 flex-1">
          <TaskGraph graph={shown} onSelectActivity={onSelectActivity} />
        </div>
      </Card>
    </div>
  )
}
