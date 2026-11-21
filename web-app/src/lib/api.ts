// Data access. Mode is decided once at startup:
//   - forced mock: `?mock=1` in the URL or VITE_MOCK=1 at build/dev time -> everything from src/mock, no network.
//   - real: /api/v2/*; if /api/v2/days answers 404 (backend not deployed yet) or the API is unreachable, fall back
//     to mocks for the v2 data and show the "Demo-Daten" badge. /api/replays and POST /captures stay real then.
import { mockDay, mockDays, mockReplays, mockReport, mockScan3d, mockTaskGraph } from '@/mock'
import type { DayResponse, DaysResponse, ReplayEntry, Report, Scan3D, TaskGraph } from './types'

export type DataMode = 'real' | 'fallback' | 'mock'

const params = new URLSearchParams(location.search || location.hash.split('?')[1] || '')
export const FORCED_MOCK = params.get('mock') === '1' || import.meta.env.VITE_MOCK === '1'

let mode: DataMode = FORCED_MOCK ? 'mock' : 'real'
export const getMode = () => mode

const delay = <T,>(v: T) => new Promise<T>(res => setTimeout(() => res(v), 60))

async function getJson<T>(url: string): Promise<T> {
  const r = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!r.ok) throw Object.assign(new Error(`${url}: HTTP ${r.status}`), { status: r.status })
  return (await r.json()) as T
}

export async function fetchDays(): Promise<DaysResponse> {
  if (mode !== 'real') return delay(mockDays())
  try {
    return await getJson<DaysResponse>('/api/v2/days')
  } catch (e) {
    console.warn('[tagwerk] /api/v2 nicht verfügbar, Demo-Daten aktiv:', (e as Error).message)
    mode = 'fallback'
    return mockDays()
  }
}

export async function fetchDay(date: string): Promise<DayResponse> {
  if (mode !== 'real') return delay(mockDay(date))
  return getJson<DayResponse>(`/api/v2/day?date=${encodeURIComponent(date)}`)
}

export async function fetchTaskGraph(date: string): Promise<TaskGraph> {
  if (mode !== 'real') return delay(mockTaskGraph(date))
  return getJson<TaskGraph>(`/api/v2/taskgraph?date=${encodeURIComponent(date)}`)
}

/** Replays come from the existing API; only forced mock mode (or an unreachable API) uses the fixture. */
export async function fetchReplays(): Promise<{ list: ReplayEntry[]; simulated: boolean }> {
  if (mode === 'mock') return { list: mockReplays(), simulated: true }
  try {
    const l = await getJson<ReplayEntry[]>('/api/replays')
    return { list: Array.isArray(l) ? l : [], simulated: false }
  } catch {
    return { list: mockReplays(), simulated: true }
  }
}

/** Starts a replay on the server: the server publishes each change at its second of the video (sync=1). */
export async function postReplay(replayOf: string, captureId: string) {
  const fd = new FormData()
  fd.append('replay_of', replayOf)
  fd.append('sync', '1')
  fd.append('capture_id', captureId)
  const r = await fetch('/captures', { method: 'POST', body: fd })
  const body = r.ok ? ((await r.json()) as { changes?: unknown[] }) : null
  return { ok: r.ok, status: r.status, changes: body?.changes?.length ?? 0 }
}

export interface CaptureDetail {
  capture?: { media?: { type: string; path: string }[] }
  transcript?: { segments?: { start: number; end: number; text: string }[] }
  changes?: { element_id: string; action: string; state: string; quote?: string; t?: number }[]
  structured?: { absences?: { count: number; trade: string; reason?: string }[]; special_events?: { type: string; text: string }[] }
}

export const fetchCapture = (cid: string) => getJson<CaptureDetail>(`/captures/${encodeURIComponent(cid)}`)

/** Element display names (for the "Erfasst" list during a live replay); loaded lazily from the existing /api/graph. */
let elementNames: Promise<Map<string, string>> | null = null
export function getElementNames() {
  if (mode === 'mock') return Promise.resolve(new Map<string, string>())
  elementNames ??= getJson<{ nodes: { id: string; label: string; props?: Record<string, unknown> }[] }>('/api/graph')
    .then(g => new Map(g.nodes.filter(n => n.label === 'Element').map(n => [n.id, String(n.props?.name_de ?? n.props?.name ?? n.id)])))
    .catch(() => new Map<string, string>())
  return elementNames
}

/** 404 from FastAPI for a route that does not exist yet ({"detail": "Not Found"}), as opposed to the endpoint's own
 *  404 ("no scan for this capture"), which must carry a different detail. */
async function routeMissing(r: Response) {
  if (r.status !== 404) return false
  try { return ((await r.json()) as { detail?: unknown }).detail === 'Not Found' } catch { return true }
}

export type Loaded<T> = { data: T | null; demo: boolean; error?: string }

export async function fetchScan3d(cid: string): Promise<Loaded<Scan3D>> {
  if (mode === 'mock') return { data: mockScan3d(cid), demo: true }
  try {
    const r = await fetch(`/api/v2/scan3d/${encodeURIComponent(cid)}`)
    if (r.ok) return { data: (await r.json()) as Scan3D, demo: false }
    if (await routeMissing(r)) return { data: mockScan3d(cid) ?? mockScan3d('demo'), demo: true }
    if (r.status === 404) return { data: null, demo: false }
    return { data: null, demo: false, error: `HTTP ${r.status}` }
  } catch (e) {
    return { data: mockScan3d(cid), demo: true, error: (e as Error).message }
  }
}

export async function fetchReport(date: string): Promise<Loaded<Report>> {
  if (mode === 'mock') return { data: mockReport(date), demo: true }
  try {
    const r = await fetch(`/api/v2/report?date=${encodeURIComponent(date)}`)
    if (r.ok) return { data: (await r.json()) as Report, demo: false }
    if (await routeMissing(r)) return { data: mockReport(date), demo: true }
    return { data: null, demo: false, error: `HTTP ${r.status}` }
  } catch (e) {
    return { data: mockReport(date), demo: true, error: (e as Error).message }
  }
}

// ---------- BIM model (IFC tessellated by scripts/ifc_to_bim.py) ----------
export interface BimIndex {
  source: string
  elements: { gid: string; cls: string; name: string; v: [number, number]; i: [number, number] }[]
  bbox: [[number, number, number], [number, number, number]]
  vertices: number
  triangles: number
}
export interface BimModel { index: BimIndex; buffer: ArrayBuffer }
export interface BimState {
  gid: string; element_id: string; name: string; pct: number; done: boolean; planned: boolean; state: string | null; state_de: string
  activity_id: string | null; activity_name: string | null; zone: string | null
}
let bimModel: Promise<BimModel> | null = null
/** The model is large (several MB) and the same for every day: load it once per page. */
export function fetchBimModel(): Promise<BimModel> {
  bimModel ??= Promise.all([
    getJson<BimIndex>('/api/v2/bim/model.json'),
    fetch('/api/v2/bim/model.bin').then(r => {
      if (!r.ok) throw new Error(`/api/v2/bim/model.bin: HTTP ${r.status}`)
      return r.arrayBuffer()
    }),
  ]).then(([index, buffer]) => ({ index, buffer }))
  bimModel.catch(() => { bimModel = null })
  return bimModel
}
export function fetchBim(date: string): Promise<{ available: boolean; is_future: boolean; elements: BimState[] }> {
  return getJson(`/api/v2/bim?date=${encodeURIComponent(date)}`)
}
