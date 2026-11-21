// Date and label helpers. Dates are ISO "YYYY-MM-DD" strings handled in UTC so no timezone shifts creep in.

const WD = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']
const MON = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']

export const toDate = (iso: string) => new Date(iso + 'T00:00:00Z')
export const toIso = (d: Date) => d.toISOString().slice(0, 10)
export const addDays = (iso: string, n: number) => {
  const d = toDate(iso)
  d.setUTCDate(d.getUTCDate() + n)
  return toIso(d)
}
export const dayDiff = (a: string, b: string) => Math.round((toDate(b).getTime() - toDate(a).getTime()) / 86400000)
export const isWeekend = (iso: string) => {
  const w = toDate(iso).getUTCDay()
  return w === 0 || w === 6
}
export const weekday = (iso: string) => WD[toDate(iso).getUTCDay()]

/** "26.11." */
export const fmtShort = (iso: string | null | undefined) => {
  if (!iso) return '–'
  const d = toDate(iso)
  return `${String(d.getUTCDate()).padStart(2, '0')}.${String(d.getUTCMonth() + 1).padStart(2, '0')}.`
}
/** "Do, 26.11.2026" */
export const fmtLong = (iso: string | null | undefined) => {
  if (!iso) return '–'
  const d = toDate(iso)
  return `${weekday(iso)}, ${fmtShort(iso)}${d.getUTCFullYear()}`
}
export const monthName = (iso: string) => MON[toDate(iso).getUTCMonth()]

export const pct = (v: number | null | undefined, digits = 0) =>
  v == null || Number.isNaN(v) ? '–' : `${v.toLocaleString('de-DE', { maximumFractionDigits: digits })} %`

export const num = (v: number | null | undefined, digits = 1) =>
  v == null || Number.isNaN(v) ? '–' : v.toLocaleString('de-DE', { maximumFractionDigits: digits, minimumFractionDigits: 0 })

export const mmss = (s: number | null | undefined) =>
  s == null || Number.isNaN(s)
    ? '–'
    : `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(Math.floor(s % 60)).padStart(2, '0')}`

// same labels as the API (tagwerk/labels.py)
const STATE_DE: Record<string, string> = {
  started: 'begonnen', installed: 'montiert', mounted: 'montiert', connected: 'angeschlossen', wired: 'verkabelt',
  tested: 'geprüft', commissioned: 'in Betrieb', checked: 'abgenommen', painted: 'gestrichen', primed: 'grundiert',
  prepared: 'vorbereitet', covered: 'verlegt', levelled: 'nivelliert', substructure: 'Unterkonstruktion',
  framed: 'Unterkonstruktion', boarded: 'beplankt', removed: 'ausgebaut', stripped: 'entfernt', done: 'fertig',
  finished: 'fertig', planned: 'geplant',
}
export const stateDe = (s: string | null | undefined) => (s ? STATE_DE[s] ?? s : 'nicht begonnen')

const ACTION_DE: Record<string, string> = {
  confirmed: 'bestätigt', proposed: 'vorgeschlagen', unchanged: 'unverändert', manual: 'manuell',
}
export const actionDe = (s: string) => ACTION_DE[s] ?? s

const EVIDENCE_DE: Record<string, string> = { voice: 'Sprache', vision: 'Bild', both: 'Sprache + Bild', manual: 'manuell', note: 'Notiz' }
export const evidenceDe = (s: string | null | undefined) => (s ? EVIDENCE_DE[s] ?? s : '')

const KIND_DE: Record<string, string> = { video: 'Video', photo: 'Foto', voice: 'Sprachnotiz', note: 'Notiz', manual: 'manuell', plan: 'Terminplan' }
export const kindDe = (s: string) => KIND_DE[s] ?? s

const EVENT_DE: Record<string, string> = {
  absence: 'Ausfall', delay: 'Verzug', defect: 'Mangel', weather: 'Wetter', delivery: 'Lieferung', accident: 'Unfall',
}
export const eventTypeDe = (s: string) => EVENT_DE[s] ?? s

const SEV_DE: Record<string, string> = { low: 'gering', medium: 'mittel', high: 'hoch' }
export const severityDe = (s: string) => SEV_DE[s] ?? s

/** API times are UTC "hh:mm" on the given date; show them in site time (Europe/Berlin). */
export const fmtTime = (date: string, hhmm: string | null | undefined) => {
  if (!hhmm || !/^\d{1,2}:\d{2}$/.test(hhmm)) return hhmm ?? ''
  const d = new Date(`${date}T${hhmm.padStart(5, '0')}:00Z`)
  if (Number.isNaN(d.getTime())) return hhmm
  return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Berlin' })
}
