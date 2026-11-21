import { useEffect, useMemo, useRef } from 'react'
import { DataSet, Network, type Edge, type Node, type Options } from 'vis-network/standalone'
import type { TaskGraph as TG, TaskNode } from '@/lib/types'
import { addDays } from '@/lib/format'

const LEVEL: Record<string, number> = { gaeb: 0, activity: 1, zone: 2, recording: 3, event: 4, proposal: 4 }
const FONT = 'Geist Variable, system-ui, -apple-system, Segoe UI, sans-serif'
export const LARGE_GRAPH_AT = 40

function activityFill(pct: number, done: boolean) {
  if (done || pct >= 100) return { bg: '#dcfce7', border: '#16a34a' }
  if (pct <= 0) return { bg: '#f5f5f5', border: '#a3a3a3' }
  const hue = 38 + (pct / 100) * (142 - 38) // amber -> green
  return { bg: `hsl(${hue}, 85%, 88%)`, border: `hsl(${hue}, 55%, 42%)` }
}

const SEV = {
  high: { bg: '#fee2e2', border: '#dc2626' },
  medium: { bg: '#fef3c7', border: '#d97706' },
  low: { bg: '#f5f5f5', border: '#a3a3a3' },
} as Record<string, { bg: string; border: string }>

function visNode(n: TaskNode): Node {
  const base: Node = {
    id: n.id, level: LEVEL[n.type] ?? 4, shape: 'box', margin: { top: 7, bottom: 7, left: 10, right: 10 },
    font: { face: FONT, size: 13, color: '#171717' }, borderWidth: 1, widthConstraint: { maximum: 230 },
    shapeProperties: { borderRadius: 6 },
  }
  switch (n.type) {
    case 'gaeb':
      return { ...base, label: n.label, color: { background: '#ffffff', border: '#d4d4d4', highlight: { background: '#fafafa', border: '#525252' } }, font: { face: FONT, size: 12, color: '#404040' }, title: `GAEB-Position\n${n.label}` }
    case 'activity': {
      const c = activityFill(n.pct ?? 0, !!n.done)
      const delayed = (n.delay_d ?? 0) > 0 && !n.done
      return {
        ...base,
        label: `<b>${n.label}</b>\n${Math.round(n.pct ?? 0)} %${delayed ? `  ·  +${n.delay_d} AT` : n.done ? '  ·  fertig' : ''}`,
        font: { face: FONT, size: 13, color: '#171717', multi: 'html', bold: { face: FONT, size: 13, color: '#0a0a0a' } },
        color: { background: c.bg, border: delayed ? '#dc2626' : c.border, highlight: { background: c.bg, border: '#0a0a0a' } },
        borderWidth: delayed ? 3 : 1,
        title: `${n.id} ${n.label}\n${n.pct ?? 0} %${n.delay_d ? `, Verzug ${n.delay_d} AT` : ''}\nStart ${n.planned_start ?? '–'}, Prognose-Ende ${n.forecast_finish ?? '–'}`,
      }
    }
    case 'zone':
      return { ...base, label: n.label, shapeProperties: { borderRadius: 14 }, color: { background: '#f0f9ff', border: '#7dd3fc', highlight: { background: '#e0f2fe', border: '#0284c7' } }, font: { face: FONT, size: 13, color: '#0c4a6e' }, title: `Ort\n${n.label}` }
    case 'recording':
      return { ...base, label: n.label, color: { background: '#2563eb', border: '#1d4ed8', highlight: { background: '#1d4ed8', border: '#1e3a8a' } }, font: { face: FONT, size: 13, color: '#ffffff' }, title: `Aufnahme ${n.id}` }
    case 'event': {
      const c = SEV[n.severity ?? 'low'] ?? SEV.low
      return { ...base, label: n.label, color: { background: c.bg, border: c.border, highlight: { background: c.bg, border: '#0a0a0a' } }, title: `Ereignis\n${n.label}` }
    }
    case 'proposal':
      return { ...base, label: n.label, color: { background: '#f5f3ff', border: '#8b5cf6', highlight: { background: '#ede9fe', border: '#5b21b6' } }, font: { face: FONT, size: 12, color: '#4c1d95' }, shapeProperties: { borderRadius: 6, borderDashes: [5, 4] }, title: `Vorschlag (nur Bild, zu bestätigen)\n${n.label}` }
    default:
      return { ...base, label: n.label }
  }
}

const EDGE_STYLE: Record<string, Partial<Edge>> = {
  PRICES: { color: { color: '#d4d4d4' }, width: 1 },
  IN_ZONE: { color: { color: '#bae6fd' }, width: 1 },
  PRECEDES: { color: { color: '#a3a3a3' }, width: 1, dashes: [4, 4], arrows: { to: { enabled: true, scaleFactor: 0.5 } }, smooth: { enabled: true, type: 'curvedCW', roundness: 0.3 } },
  PROGRESSED: { color: { color: '#16a34a' }, width: 2.5, arrows: { to: { enabled: true, scaleFactor: 0.6 } } },
  AFFECTS: { color: { color: '#ef4444' }, width: 1.5, dashes: [5, 4], arrows: { to: { enabled: true, scaleFactor: 0.5 } } },
  PROPOSES: { color: { color: '#8b5cf6' }, width: 1.5, dashes: [5, 4], arrows: { to: { enabled: true, scaleFactor: 0.5 } } },
  RAISED: { color: { color: '#93c5fd' }, width: 1, dashes: [2, 3] },
}

const OPTIONS: Options = {
  layout: { hierarchical: { enabled: true, direction: 'LR', sortMethod: 'directed', levelSeparation: 230, nodeSpacing: 40, treeSpacing: 60, blockShifting: true, edgeMinimization: true, parentCentralization: true } },
  physics: { enabled: false },
  interaction: { hover: true, tooltipDelay: 200, navigationButtons: false, keyboard: false, zoomView: true, dragView: true, multiselect: false },
  edges: { smooth: { enabled: true, type: 'cubicBezier', forceDirection: 'horizontal', roundness: 0.5 }, font: { face: FONT, size: 10, color: '#15803d', strokeWidth: 3, strokeColor: '#ffffff', align: 'middle' }, selectionWidth: 1.5 },
  nodes: { chosen: true },
}

/** Large projects: only the activities around the day (and everything linked to today's recordings). */
export function focusGraph(g: TG, all: boolean): TG {
  const acts = g.nodes.filter(n => n.type === 'activity')
  if (all || acts.length <= LARGE_GRAPH_AT) return g
  const lo = addDays(g.date, -7), hi = addDays(g.date, 14)
  const dayKinds = new Set(['recording', 'event', 'proposal'])
  const touched = new Set<string>()
  const kindOf = new Map(g.nodes.map(n => [n.id, n.type]))
  for (const e of g.edges) {
    if (dayKinds.has(kindOf.get(e.src) ?? '') && kindOf.get(e.dst) === 'activity') touched.add(e.dst)
  }
  const keepAct = new Set(acts.filter(a => touched.has(a.id) || ((a.planned_start ?? '9999') <= hi && (a.forecast_finish ?? '0000') >= lo)).map(a => a.id))
  const keep = new Set<string>(keepAct)
  for (const n of g.nodes) if (dayKinds.has(n.type)) keep.add(n.id)
  for (const e of g.edges) {
    if (keepAct.has(e.dst) && kindOf.get(e.src) === 'gaeb') keep.add(e.src)
    if (keepAct.has(e.src) && kindOf.get(e.dst) === 'zone') keep.add(e.dst)
    if (keep.has(e.src) && kindOf.get(e.src) === 'recording' && kindOf.get(e.dst) === 'zone') keep.add(e.dst)
  }
  return { ...g, nodes: g.nodes.filter(n => keep.has(n.id)), edges: g.edges.filter(e => keep.has(e.src) && keep.has(e.dst)) }
}

/** Events/proposals the API left without an edge get a dotted link to the recording that raised them. */
function withRaisedLinks(g: TG): TG {
  const ids = new Set(g.nodes.map(n => n.id))
  const linked = new Set(g.edges.flatMap(e => [e.src, e.dst]))
  const extra = g.nodes
    .filter(n => (n.type === 'event' || n.type === 'proposal') && !linked.has(n.id))
    .map(n => ({ n, cid: n.type === 'proposal' ? n.id.split(':')[1] : n.id.split(':')[0] }))
    .filter(x => x.cid && ids.has(x.cid))
    .map(x => ({ src: x.cid, dst: x.n.id, type: 'RAISED' }))
  return extra.length ? { ...g, edges: [...g.edges, ...extra] } : g
}

interface Props {
  graph: TG
  onSelectActivity: (id: string) => void
}

export function TaskGraph({ graph, onSelectActivity }: Props) {
  const box = useRef<HTMLDivElement>(null)
  const net = useRef<Network | null>(null)
  const nodes = useRef(new DataSet<Node>())
  const edges = useRef(new DataSet<Edge>())
  const lastIds = useRef('')
  const onSel = useRef(onSelectActivity)
  onSel.current = onSelectActivity

  const g = useMemo(() => withRaisedLinks(graph), [graph])

  useEffect(() => {
    if (!box.current) return
    const n = new Network(box.current, { nodes: nodes.current, edges: edges.current }, OPTIONS)
    n.on('click', p => {
      const id = p.nodes?.[0] as string | undefined
      if (id && nodes.current.get(id) && (nodes.current.get(id) as Node).level === LEVEL.activity) onSel.current(id)
    })
    n.on('hoverNode', () => { if (box.current) box.current.style.cursor = 'pointer' })
    n.on('blurNode', () => { if (box.current) box.current.style.cursor = 'default' })
    net.current = n
    const ro = new ResizeObserver(() => { n.redraw() })
    ro.observe(box.current)
    const fit = () => n.fit({ animation: { duration: 300, easingFunction: 'easeInOutQuad' } })
    window.addEventListener('tw-fit', fit)
    return () => { window.removeEventListener('tw-fit', fit); ro.disconnect(); n.destroy(); net.current = null; lastIds.current = '' }
  }, [])

  useEffect(() => {
    const n = net.current
    if (!n) return
    const vn = g.nodes.map(visNode)
    const ve: Edge[] = g.edges.map(e => ({
      id: `${e.src}|${e.type}|${e.dst}`, from: e.src, to: e.dst, label: e.label,
      ...(EDGE_STYLE[e.type] ?? { color: { color: '#d4d4d4' } }),
    }))
    const ids = vn.map(x => x.id).sort().join(',') + '#' + ve.map(x => x.id).sort().join(',')
    if (ids === lastIds.current) {
      nodes.current.update(vn)
      edges.current.update(ve)
      return
    }
    lastIds.current = ids
    nodes.current = new DataSet<Node>(vn)
    edges.current = new DataSet<Edge>(ve)
    n.setData({ nodes: nodes.current, edges: edges.current })
    n.once('afterDrawing', () => n.fit({ animation: false }))
  }, [g])

  return <div ref={box} className="absolute inset-0" data-testid="task-graph" />
}

export function fitGraph() {
  window.dispatchEvent(new Event('tw-fit'))
}
