// Shapes of docs/UI-V2-CONTRACT.md. Field names match the API exactly.

export interface DayInfo {
  date: string
  workday: boolean
  recordings: number
  events: number
}

export interface DaysResponse {
  today: string
  first: string
  last: string
  days: DayInfo[]
}

export interface Kpi {
  pct_actual: number
  pct_planned: number
  spi: number | null
  forecast_finish: string | null
  baseline_finish: string | null
  delay_d: number
  open_defects: number
}

export interface Weather {
  tempC: number | null
  precipMm: number | null
  windKmh: number | null
  source: string
}

export interface Change {
  element_id: string
  element_name: string
  action: string // confirmed | proposed | unchanged | ...
  state: string
  activity_id: string | null
  activity_name: string | null
  quote: string | null
  evidence: string | null
}

export interface RecProposal {
  element_id: string
  element_name: string
  state: string
  activity_id: string | null
}

export interface Absence {
  trade: string
  count: number
  reason: string | null
  activity_id: string | null
}

export interface RecEvent {
  type: string
  text: string
  severity: Severity
  activity_id: string | null
}

export interface Recording {
  capture_id: string
  time: string
  zone_id: string | null
  zone_name: string | null
  kind: 'video' | 'photo' | 'voice' | 'note' | string
  transcript: string | null
  note: string | null
  video: string | null
  photos: string[]
  changes: Change[]
  proposals: RecProposal[]
  absences: Absence[]
  events: RecEvent[]
  material: unknown[]
  labour: unknown[]
  /** not in the day contract yet (only in /api/v2/report recordings); read when present */
  has_3d?: boolean
}

export interface GaebRef {
  oz: string
  text: string
}

export interface Activity {
  id: string
  name: string
  wbs: string | null
  trade: string | null
  zones: string[]
  gaeb: GaebRef[]
  planned_start: string
  baseline_finish: string
  forecast_start: string | null
  forecast_finish: string | null
  pct: number
  planned_pct: number
  delay_d: number
  tracked: boolean
  done: boolean
  cause: string | null
  recordings: ActivityRecording[]
  last_recording: string | null
  predecessors: string[]
}

/** A capture that touched the activity (any day up to D), oldest first. */
export interface ActivityRecording {
  capture_id: string
  date: string
  time: string
}

export interface LookaheadActivity {
  id: string
  name: string
  trade: string | null
  zones: string[]
  planned_pct_by_end: number
}

export interface LookaheadDay {
  date: string
  activities: LookaheadActivity[]
}

export type Severity = 'low' | 'medium' | 'high' | string

export interface ProjectEvent {
  id: string
  date: string
  type: string // absence | delay | defect | weather | delivery | accident | ...
  text: string
  severity: Severity
  activity_id: string | null
  capture_id: string | null
  source: string // capture | weather | history | ...
}

export interface DayResponse {
  date: string
  today: string
  is_future: boolean
  info?: { has_data: boolean; first: string | null } // no evidence before `first`: the app shows the plan
  project: { name: string; bim: boolean }
  kpi: Kpi
  weather: Weather | null
  recordings: Recording[]
  activities: Activity[]
  lookahead: LookaheadDay[]
  events: ProjectEvent[]
}

export type TaskNodeType = 'gaeb' | 'activity' | 'zone' | 'recording' | 'event' | 'proposal'

export interface TaskNode {
  id: string
  type: TaskNodeType
  label: string
  pct?: number
  delay_d?: number
  done?: boolean
  planned_start?: string
  forecast_finish?: string
  date?: string
  severity?: Severity
}

export interface TaskEdge {
  src: string
  dst: string
  type: 'PRICES' | 'IN_ZONE' | 'PRECEDES' | 'PROGRESSED' | 'AFFECTS' | 'PROPOSES' | string
  label?: string
}

export interface TaskGraph {
  date: string
  nodes: TaskNode[]
  edges: TaskEdge[]
}

// Existing endpoint GET /api/replays
export interface ReplaySegment {
  start: number
  end: number
  text: string
}

export interface ReplayEntry {
  id: string
  label: string
  zone_id: string | null
  ts: string | null
  video: string | null
  photos: string[]
  note: string | null
  segments: ReplaySegment[]
}

// Websocket /events messages (the subset the app reads)
export interface WsEvent {
  type: 'node' | 'edge' | 'status' | string
  id?: string
  label?: string
  props?: Record<string, unknown>
}

// GET /api/v2/scan3d/{cid}
export interface ScanRelation {
  rel: string
  rel_de: string
  target: string
  target_name: string
  score: number
  count: number
  source: string // model | geometry
}

export interface ScanObject {
  id: string
  label: string
  name_de: string
  category_de: string
  position: [number, number, number] | null
  extent: [number, number, number] | null
  detections: number
  first_t: number | null
  last_t: number | null
  conf: number
  thumb: string | null
  bbox_in_thumb: [number, number, number, number] | null
  element_id: string | null
  relations: ScanRelation[]
}

export interface ScanCamera {
  t: number
  position: [number, number, number]
  look: [number, number, number]
  frame: string | null
}

export interface Scan3D {
  capture_id: string
  ok: boolean
  reason: string | null
  seconds: number | null
  frames_used: number | null
  frames_registered: number | null
  points: [number, number, number, number, number, number][]
  cameras: ScanCamera[]
  objects: ScanObject[]
  units: string
  video?: string | null // kept walkthrough video (/media/<cid>/<file>)
}

// GET /api/v2/report?date=D
export interface Report {
  date: string
  project: { name: string; site: string | null; client: string | null }
  weather: { tempC: number | null; precipMm: number | null; windKmh: number | null } | null
  recordings: { capture_id: string; time: string; zone_name: string | null; kind: string; has_3d: boolean }[]
  work_done: { activity_id: string | null; activity_name: string | null; element_name: string; state_de: string; quote: string | null; capture_id: string | null }[]
  workforce: { present: { trade: string; count: number }[]; absent: { trade: string; count: number; reason: string | null }[] }
  inventory: { name_de: string; count: number; relations: string[]; thumb: string | null; capture_id: string | null }[]
  events: { type: string; text: string; severity: Severity }[]
  photos: string[]
  delays: { activity_id: string; activity_name: string; delay_d: number; cause: string | null }[]
  lookahead: { date: string; activities: string[] }[]
}
