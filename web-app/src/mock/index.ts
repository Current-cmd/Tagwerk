// Mock implementation of /api/v2/*: derives the contract responses for any day from base.json, so the day slider
// shows work and schedule building up just like the real backend would.
import { addDays, dayDiff, isWeekend, kindDe, stateDe } from '@/lib/format'
import type {
  Activity, DayInfo, DayResponse, DaysResponse, LookaheadDay, ProjectEvent, Recording, Report, ReplayEntry, TaskEdge,
  TaskGraph, TaskNode, Weather,
} from '@/lib/types'
import base from './base.json'
import { MOCK_3D_IDS, mockScan3d } from './scan3d'
import replays from './replays.json'

type BaseActivity = (typeof base.activities)[number]
type BaseRecording = (typeof base.recordings)[number]

const TODAY = base.today
const ZONES = base.zones as Record<string, string>
const GAEB = base.gaeb as Record<string, string>
const r1 = (v: number) => Math.round(v * 10) / 10
const minIso = (a: string, b: string) => (a < b ? a : b)

/** working days in [a, b], both inclusive (0 if b < a) */
function wdIncl(a: string, b: string) {
  let n = 0
  for (let d = a; d <= b; d = addDays(d, 1)) if (!isWeekend(d)) n++
  return n
}
function addWorkdays(iso: string, n: number) {
  let d = iso
  while (n > 0) {
    d = addDays(d, 1)
    if (!isWeekend(d)) n--
  }
  return d
}
function nextWorkdays(iso: string, n: number) {
  const out: string[] = []
  let d = iso
  while (out.length < n) {
    d = addDays(d, 1)
    if (!isWeekend(d)) out.push(d)
  }
  return out
}

function recActivities(r: BaseRecording) {
  const ids = [...r.changes, ...r.proposals, ...r.absences, ...r.events].map(x => x.activity_id).filter(Boolean) as string[]
  return [...new Set(ids)]
}

function plannedPct(a: { planned_start: string; baseline_finish: string }, d: string) {
  if (d < a.planned_start) return 0
  if (d >= a.baseline_finish) return 100
  return r1((100 * wdIncl(a.planned_start, d)) / Math.max(1, wdIncl(a.planned_start, a.baseline_finish)))
}

function activityAt(a: BaseActivity, d: string): Activity {
  const dd = minIso(d, TODAY) // no actuals beyond project today
  const as = a.mock_actual_start, af = a.mock_actual_finish
  let pct = 0
  if (as && dd >= as) {
    if (af && dd >= af) pct = 100
    else {
      const end = af ?? TODAY
      const target = af ? 100 : a.mock_pct_today
      pct = r1((target * wdIncl(as, dd)) / Math.max(1, wdIncl(as, end)))
    }
  }
  let delay = 0
  if (dd >= a.planned_start) {
    const ref = af ?? TODAY
    const frac = dd >= ref ? 1 : wdIncl(a.planned_start, dd) / Math.max(1, wdIncl(a.planned_start, ref))
    delay = Math.round(a.mock_delay_today * frac)
  }
  const recs = base.recordings.filter(r => r.date <= dd && recActivities(r).includes(a.id))
  return {
    id: a.id,
    name: a.name,
    wbs: a.wbs,
    trade: a.trade,
    zones: a.zones.map(z => ZONES[z] ?? z),
    gaeb: a.gaeb.map(oz => ({ oz, text: GAEB[oz] ?? '' })),
    planned_start: a.planned_start,
    baseline_finish: a.baseline_finish,
    forecast_start: as && dd >= as ? as : delay > 0 ? addWorkdays(a.planned_start, delay) : a.planned_start,
    forecast_finish: addWorkdays(a.baseline_finish, delay),
    pct,
    planned_pct: plannedPct(a, d),
    delay_d: delay,
    tracked: true,
    done: pct >= 100,
    cause: delay > 0 ? a.mock_cause : null,
    recordings: recs.map(r => r.capture_id),
    last_recording: recs.length ? recs[recs.length - 1].date : null,
    predecessors: a.predecessors,
  }
}

function weatherAt(d: string): Weather | null {
  if (d > TODAY || d < base.first) return null
  const o = (base.weather_overrides as Record<string, { tempC: number; precipMm: number; windKmh: number }>)[d]
  if (o) return { ...o, source: 'open-meteo' }
  const i = dayDiff(base.first, d)
  return { tempC: r1(4 + 3 * Math.sin(i * 0.9)), precipMm: r1(((i * 7) % 5) * 0.6), windKmh: r1(8 + ((i * 13) % 20)), source: 'open-meteo' }
}

function weatherEvent(d: string): ProjectEvent | null {
  const w = weatherAt(d)
  if (!w) return null
  const mk = (text: string, severity: string): ProjectEvent => ({
    id: `weather:${d}`, date: d, type: 'weather', text, severity, activity_id: null, capture_id: null, source: 'weather',
  })
  const n = (v: number) => v.toLocaleString('de-DE', { maximumFractionDigits: 1 })
  if ((w.windKmh ?? 0) >= 50) return mk(`Sturm ${n(w.windKmh!)} km/h: kein Kranbetrieb`, 'high')
  if ((w.precipMm ?? 0) >= 5) return mk(`Starkregen ${n(w.precipMm!)} mm: Außenarbeiten und Anlieferung eingeschränkt`, 'medium')
  if ((w.tempC ?? 99) <= 0) return mk(`Frost ${n(w.tempC!)} °C: kein Estrich, Beton oder Außenanstrich`, 'medium')
  return null
}

function recordingEvents(r: BaseRecording): ProjectEvent[] {
  const ev: ProjectEvent[] = []
  r.absences.forEach((a, i) =>
    ev.push({
      id: `${r.capture_id}:absence:${i}`, date: r.date, type: 'absence', text: `${a.count}× ${a.trade} ${a.reason ?? ''}`.trim(),
      severity: 'medium', activity_id: a.activity_id, capture_id: r.capture_id, source: 'capture',
    }))
  r.events.forEach((e, i) =>
    ev.push({
      id: `${r.capture_id}:${e.type}:${i}`, date: r.date, type: e.type, text: e.text, severity: e.severity,
      activity_id: e.activity_id, capture_id: r.capture_id, source: 'capture',
    }))
  return ev
}

const lastDay = () => {
  const acts = base.activities.map(a => activityAt(a, TODAY))
  return acts.reduce((m, a) => (a.forecast_finish && a.forecast_finish > m ? a.forecast_finish : m), acts.reduce((m, a) => (a.baseline_finish > m ? a.baseline_finish : m), base.first))
}

export function mockDays(): DaysResponse {
  const last = lastDay()
  const days: DayInfo[] = []
  for (let d = base.first; d <= last; d = addDays(d, 1)) {
    const recs = d <= TODAY ? base.recordings.filter(r => r.date === d) : []
    const events = recs.flatMap(recordingEvents).length + (weatherEvent(d) ? 1 : 0)
    days.push({ date: d, workday: !isWeekend(d), recordings: recs.length, events })
  }
  return { today: TODAY, first: base.first, last, days }
}

function toRecording(r: BaseRecording, acts: Map<string, Activity>): Recording {
  const { date: _date, ...rest } = r
  void _date
  return {
    ...rest,
    zone_name: ZONES[r.zone_id] ?? r.zone_id,
    changes: r.changes.map(c => ({ ...c, activity_name: acts.get(c.activity_id)?.name ?? null })),
    material: [],
    labour: [],
    has_3d: MOCK_3D_IDS.has(r.capture_id),
  }
}

export function mockDay(date?: string): DayResponse {
  const d = date ?? TODAY
  const dd = minIso(d, TODAY)
  const activities = base.activities.map(a => activityAt(a, d)).sort((a, b) => a.planned_start.localeCompare(b.planned_start) || a.id.localeCompare(b.id))
  const byId = new Map(activities.map(a => [a.id, a]))
  const weights = new Map(base.activities.map(a => [a.id, a.mock_weight]))
  const W = activities.reduce((s, a) => s + (weights.get(a.id) ?? 0), 0)
  const pctActual = r1(activities.reduce((s, a) => s + a.pct * (weights.get(a.id) ?? 0), 0) / W)
  const pctPlanned = r1(activities.reduce((s, a) => s + a.planned_pct * (weights.get(a.id) ?? 0), 0) / W)
  const ff = activities.reduce((m, a) => (a.forecast_finish && a.forecast_finish > m ? a.forecast_finish : m), '')
  const bf = activities.reduce((m, a) => (a.baseline_finish > m ? a.baseline_finish : m), '')
  const pastRecs = base.recordings.filter(r => r.date <= dd)
  const events: ProjectEvent[] = [...pastRecs.flatMap(recordingEvents)]
  for (let x = base.first; x <= dd; x = addDays(x, 1)) {
    const w = weatherEvent(x)
    if (w) events.push(w)
  }
  const recTime = new Map(base.recordings.map(r => [r.capture_id, r.time]))
  events.sort((a, b) => b.date.localeCompare(a.date) || (recTime.get(b.capture_id ?? '') ?? '').localeCompare(recTime.get(a.capture_id ?? '') ?? ''))

  const lookahead: LookaheadDay[] = nextWorkdays(d, 3).map(day => ({
    date: day,
    activities: activities
      .filter(a => !a.done && (a.forecast_start ?? a.planned_start) <= day && (a.forecast_finish ?? a.baseline_finish) >= day)
      .map(a => ({
        id: a.id, name: a.name, trade: a.trade, zones: a.zones,
        planned_pct_by_end: plannedPct({ planned_start: a.forecast_start ?? a.planned_start, baseline_finish: a.forecast_finish ?? a.baseline_finish }, day),
      })),
  }))

  return {
    date: d,
    today: TODAY,
    is_future: d > TODAY,
    project: base.project,
    kpi: {
      pct_actual: pctActual,
      pct_planned: pctPlanned,
      spi: pctPlanned > 0 ? Math.round((pctActual / pctPlanned) * 100) / 100 : null,
      forecast_finish: ff || null,
      baseline_finish: bf || null,
      delay_d: ff && bf && ff > bf ? wdIncl(addDays(bf, 1), ff) : 0,
      open_defects: events.filter(e => e.type === 'defect').length,
    },
    weather: weatherAt(d),
    recordings: (d <= TODAY ? base.recordings.filter(r => r.date === d) : [])
      .slice()
      .sort((a, b) => b.time.localeCompare(a.time))
      .map(r => toRecording(r, byId)),
    activities,
    lookahead,
    events,
  }
}

export function mockTaskGraph(date?: string): TaskGraph {
  const d = date ?? TODAY
  const day = mockDay(d)
  const nodes: TaskNode[] = []
  const edges: TaskEdge[] = []
  const seen = new Set<string>()
  const add = (n: TaskNode) => {
    if (!seen.has(n.id)) { seen.add(n.id); nodes.push(n) }
  }
  const zoneId = new Map(Object.entries(ZONES).map(([id, name]) => [name, id]))
  for (const a of day.activities) {
    add({ id: a.id, type: 'activity', label: a.name, pct: a.pct, delay_d: a.delay_d, done: a.done, planned_start: a.planned_start, forecast_finish: a.forecast_finish ?? undefined })
    for (const g of a.gaeb) {
      add({ id: `oz:${g.oz}`, type: 'gaeb', label: `${g.oz} ${g.text}` })
      edges.push({ src: `oz:${g.oz}`, dst: a.id, type: 'PRICES' })
    }
    for (const z of a.zones) {
      const zid = zoneId.get(z) ?? z
      add({ id: zid, type: 'zone', label: z })
      edges.push({ src: a.id, dst: zid, type: 'IN_ZONE' })
    }
    for (const p of a.predecessors) edges.push({ src: p, dst: a.id, type: 'PRECEDES' })
  }
  for (const r of day.recordings) {
    add({ id: r.capture_id, type: 'recording', label: `${r.time} ${kindDe(r.kind)}`, date: d })
    const byAct = new Map<string, string[]>()
    for (const c of r.changes) if (c.activity_id) byAct.set(c.activity_id, [...(byAct.get(c.activity_id) ?? []), `${c.element_name} ${stateDe(c.state)}`])
    byAct.forEach((labels, act) => edges.push({ src: r.capture_id, dst: act, type: 'PROGRESSED', label: labels.join(', ') }))
    for (const p of r.proposals) {
      const id = `prop:${r.capture_id}:${p.element_id}`
      add({ id, type: 'proposal', label: `${p.element_name}: ${stateDe(p.state)}? (nur Bild)` })
      if (p.activity_id) edges.push({ src: id, dst: p.activity_id, type: 'PROPOSES' })
      edges.push({ src: r.capture_id, dst: id, type: 'RAISED' })
    }
  }
  for (const e of day.events.filter(e => e.date === d && e.source === 'capture')) {
    add({ id: e.id, type: 'event', label: e.text, severity: e.severity })
    if (e.activity_id) edges.push({ src: e.id, dst: e.activity_id, type: 'AFFECTS' })
    if (e.capture_id) edges.push({ src: e.capture_id, dst: e.id, type: 'RAISED' })
  }
  return { date: d, nodes, edges }
}

export function mockReplays(): ReplayEntry[] {
  return replays as ReplayEntry[]
}

/** What the mock "replay" of an entry captures, with the second at which each item appears. */
export function mockReplayFindings(id: string) {
  const r = base.recordings.find(x => x.capture_id === id)
  if (!r) return []
  const out: { t: number; text: string; cls: '' | 'p' | 'e'; quote?: string }[] = []
  r.changes.forEach((c, i) => out.push({ t: 1.6 + i * 3.4, text: `${c.element_name} → ${stateDe(c.state)}`, cls: '', quote: c.quote ?? undefined }))
  r.proposals.forEach(p => out.push({ t: 6.2, text: `${p.element_name} → ${stateDe(p.state)}?`, cls: 'p' }))
  r.absences.forEach(a => out.push({ t: 3.8, text: `${a.count}× ${a.trade} ${a.reason ?? ''}`.trim(), cls: 'e' }))
  r.events.forEach(e => out.push({ t: 5, text: e.text, cls: 'e' }))
  return out.sort((a, b) => a.t - b.t)
}

export { mockScan3d }

/** Mock for GET /api/v2/report?date=D (Tagesbericht), derived from the mock day. */
export function mockReport(date?: string): Report {
  const day = mockDay(date)
  const d = day.date
  const absent = day.recordings.flatMap(r => r.absences.map(a => ({ trade: a.trade, count: a.count, reason: a.reason })))
  const running = day.is_future ? [] : day.activities.filter(a => (a.forecast_start ?? a.planned_start) <= d && (a.forecast_finish ?? a.baseline_finish) >= d && !isWeekend(d))
  const crew = new Map<string, number>()
  running.forEach((a, i) => a.trade && crew.set(a.trade, (crew.get(a.trade) ?? 0) + 2 + (i % 3)))
  absent.forEach(a => crew.has(a.trade) && crew.set(a.trade, Math.max(0, crew.get(a.trade)! - a.count)))
  const inventory = new Map<string, Report['inventory'][number]>()
  for (const r of day.recordings) {
    const sc = r.has_3d ? mockScan3d(r.capture_id) : null
    for (const o of sc?.objects ?? []) {
      const cur = inventory.get(o.name_de)
      const rels = o.relations.map(x => `${x.rel_de} ${x.target_name}`)
      if (cur) { cur.count++; cur.relations = [...new Set([...cur.relations, ...rels])] }
      else inventory.set(o.name_de, { name_de: o.name_de, count: 1, relations: rels, thumb: o.thumb, capture_id: r.capture_id })
    }
  }
  const project = { name: day.project.name, site: 'Hörsaal 1, Arcisstraße 21, 80333 München', client: 'Freistaat Bayern, vertreten durch das Staatliche Bauamt' }
  return {
    date: d,
    project,
    weather: day.weather ? { tempC: day.weather.tempC, precipMm: day.weather.precipMm, windKmh: day.weather.windKmh } : null,
    recordings: day.recordings.map(r => ({ capture_id: r.capture_id, time: r.time, zone_name: r.zone_name, kind: r.kind, has_3d: !!r.has_3d })),
    work_done: day.recordings.flatMap(r => r.changes.map(c => ({
      activity_id: c.activity_id, activity_name: c.activity_name, element_name: c.element_name, state_de: stateDe(c.state), quote: c.quote, capture_id: r.capture_id,
    }))),
    workforce: { present: [...crew].map(([trade, count]) => ({ trade, count })), absent },
    inventory: [...inventory.values()],
    events: day.events.filter(e => e.date === d).map(e => ({ type: e.type, text: e.text, severity: e.severity })),
    photos: day.recordings.flatMap(r => r.photos),
    delays: day.activities.filter(a => a.delay_d > 0 && !a.done).map(a => ({ activity_id: a.id, activity_name: a.name, delay_d: a.delay_d, cause: a.cause })),
    lookahead: day.lookahead.map(l => ({ date: l.date, activities: l.activities.map(a => a.name) })),
  }
}
