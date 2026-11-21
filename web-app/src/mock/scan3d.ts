// Mock for GET /api/v2/scan3d/{cid}: a believable lecture-room corner, generated deterministically.
// Coordinates follow the COLMAP convention (x right, y DOWN, z forward); the viewer flips y for display.
import type { Scan3D, ScanObject, ScanRelation } from '@/lib/types'

type V3 = [number, number, number]

function rng(seed: number) {
  return () => {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const FLOOR = 1.5, CEIL = -1.4, X0 = -3, X1 = 3, Z0 = 0, Z1 = 8

interface ObjDef { id: string; label: string; name_de: string; category_de: string; pos: V3; ext: V3; rgb: V3; element_id: string | null; conf: number; t: [number, number] }

const OBJECTS: ObjDef[] = [
  { id: 'obj-1', label: 'door', name_de: 'Tür', category_de: 'Öffnungen', pos: [-1.8, 0.47, 7.95], ext: [0.95, 2.05, 0.1], rgb: [120, 86, 60], element_id: 'E-DOOR-1', conf: 0.86, t: [16.5, 22.0] },
  { id: 'obj-2', label: 'window', name_de: 'Fenster', category_de: 'Öffnungen', pos: [2.95, -0.25, 3.0], ext: [0.1, 1.4, 1.6], rgb: [170, 200, 225], element_id: null, conf: 0.79, t: [5.0, 9.5] },
  { id: 'obj-3', label: 'window', name_de: 'Fenster', category_de: 'Öffnungen', pos: [2.95, -0.25, 6.0], ext: [0.1, 1.4, 1.6], rgb: [170, 200, 225], element_id: null, conf: 0.74, t: [11.0, 14.0] },
  { id: 'obj-4', label: 'radiator', name_de: 'Heizkörper', category_de: 'Heizung / Lüftung', pos: [2.9, 1.1, 3.0], ext: [0.1, 0.6, 1.2], rgb: [235, 235, 230], element_id: null, conf: 0.71, t: [5.5, 9.0] },
  { id: 'obj-5', label: 'socket', name_de: 'Steckdose', category_de: 'Elektro', pos: [-2.97, 1.2, 2.5], ext: [0.03, 0.08, 0.08], rgb: [245, 245, 245], element_id: null, conf: 0.58, t: [2.0, 3.5] },
  { id: 'obj-6', label: 'lamp', name_de: 'Leuchte', category_de: 'Elektro', pos: [0, -1.33, 3.0], ext: [1.2, 0.08, 0.3], rgb: [255, 250, 225], element_id: 'E-EMLIGHT', conf: 0.69, t: [3.0, 8.0] },
  { id: 'obj-7', label: 'lamp', name_de: 'Leuchte', category_de: 'Elektro', pos: [0, -1.33, 6.0], ext: [1.2, 0.08, 0.3], rgb: [255, 250, 225], element_id: null, conf: 0.66, t: [9.0, 15.0] },
  { id: 'obj-8', label: 'chair', name_de: 'Stuhl', category_de: 'Ausstattung', pos: [-0.8, 1.05, 4.5], ext: [0.5, 0.9, 0.5], rgb: [60, 70, 90], element_id: 'E-ROW-A', conf: 0.9, t: [6.0, 12.0] },
  { id: 'obj-9', label: 'chair', name_de: 'Stuhl', category_de: 'Ausstattung', pos: [0.6, 1.05, 4.6], ext: [0.5, 0.9, 0.5], rgb: [60, 70, 90], element_id: 'E-ROW-A', conf: 0.88, t: [6.5, 12.5] },
  { id: 'obj-10', label: 'table', name_de: 'Tisch', category_de: 'Ausstattung', pos: [0, 1.12, 5.4], ext: [1.6, 0.75, 0.8], rgb: [175, 140, 100], element_id: null, conf: 0.83, t: [8.0, 14.5] },
  { id: 'obj-11', label: 'wall', name_de: 'Wand', category_de: 'Bauteile', pos: [0, 0.05, 8.0], ext: [6, 2.9, 0.1], rgb: [215, 212, 205], element_id: 'E-PANELS-E', conf: 0.62, t: [15.0, 24.0] },
]

const REL: [string, string, string, string, number, number, string][] = [
  // src, rel, rel_de, target, score, count, source
  ['obj-1', 'next to', 'neben', 'obj-11', 0.52, 4, 'model'],
  ['obj-1', 'on', 'in', 'obj-11', 0.61, 6, 'geometry'],
  ['obj-2', 'above', 'über', 'obj-4', 0.71, 5, 'geometry'],
  ['obj-4', 'below', 'unter', 'obj-2', 0.71, 5, 'geometry'],
  ['obj-3', 'next to', 'neben', 'obj-2', 0.44, 2, 'model'],
  ['obj-6', 'above', 'über', 'obj-8', 0.48, 3, 'geometry'],
  ['obj-7', 'above', 'über', 'obj-10', 0.57, 4, 'geometry'],
  ['obj-8', 'next to', 'neben', 'obj-9', 0.66, 7, 'model'],
  ['obj-8', 'in front of', 'vor', 'obj-10', 0.55, 4, 'model'],
  ['obj-9', 'next to', 'neben', 'obj-8', 0.66, 7, 'model'],
  ['obj-9', 'in front of', 'vor', 'obj-10', 0.51, 3, 'model'],
  ['obj-10', 'below', 'unter', 'obj-7', 0.57, 4, 'geometry'],
  ['obj-11', 'next to', 'neben', 'obj-1', 0.52, 4, 'model'],
]

function thumbSvg(o: ObjDef, frame: number): { thumb: string; bbox: [number, number, number, number] } {
  // 320x240 placeholder "frame" with the object drawn where its box is
  const w = Math.min(220, Math.max(26, o.ext[0] * 60 + o.ext[2] * 60))
  const h = Math.min(180, Math.max(22, o.ext[1] * 70))
  const x1 = Math.round(160 - w / 2), y1 = Math.round(130 - h / 2)
  const [r, g, b] = o.rgb
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="320" height="240" viewBox="0 0 320 240">
<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d9d6cf"/><stop offset=".62" stop-color="#c9c4ba"/><stop offset=".63" stop-color="#8d8579"/><stop offset="1" stop-color="#6f675c"/></linearGradient></defs>
<rect width="320" height="240" fill="url(#g)"/><rect x="${x1}" y="${y1}" width="${Math.round(w)}" height="${Math.round(h)}" rx="3" fill="rgb(${r},${g},${b})" stroke="rgba(0,0,0,.25)"/>
<text x="8" y="232" font-family="sans-serif" font-size="11" fill="#fff" opacity=".85">Bild ${String(frame).padStart(4, '0')} · Demo</text></svg>`
  return { thumb: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`, bbox: [x1 - 4, y1 - 4, Math.round(x1 + w + 4), Math.round(y1 + h + 4)] }
}

function buildObjects(): ScanObject[] {
  const name = new Map(OBJECTS.map(o => [o.id, o.name_de]))
  return OBJECTS.map((o, i) => {
    const { thumb, bbox } = thumbSvg(o, 4 + i * 5)
    const relations: ScanRelation[] = REL.filter(r => r[0] === o.id).map(r => ({
      rel: r[1], rel_de: r[2], target: r[3], target_name: name.get(r[3]) ?? r[3], score: r[4], count: r[5], source: r[6],
    }))
    return {
      id: o.id, label: o.label, name_de: o.name_de, category_de: o.category_de, position: o.pos, extent: o.ext,
      detections: Math.round(4 + o.conf * 12), first_t: o.t[0], last_t: o.t[1], conf: o.conf, thumb, bbox_in_thumb: bbox,
      element_id: o.element_id, relations,
    }
  })
}

function buildPoints(r: () => number): Scan3D['points'] {
  const pts: Scan3D['points'] = []
  const jitter = (c: number, a = 12) => Math.max(0, Math.min(255, Math.round(c + (r() - 0.5) * 2 * a)))
  const push = (p: V3, c: V3, a?: number) => pts.push([+p[0].toFixed(3), +p[1].toFixed(3), +p[2].toFixed(3), jitter(c[0], a), jitter(c[1], a), jitter(c[2], a)])
  const n = (s: number) => (r() - 0.5) * s
  for (let i = 0; i < 820; i++) push([X0 + r() * (X1 - X0), FLOOR + n(0.02), Z0 + r() * (Z1 - Z0)], [96, 92, 104]) // needle felt
  for (let i = 0; i < 380; i++) push([X0 + r() * (X1 - X0), CEIL + n(0.02), Z0 + r() * (Z1 - Z0)], [232, 232, 228], 6) // ceiling tiles
  for (let i = 0; i < 520; i++) push([X0 + n(0.02), CEIL + r() * (FLOOR - CEIL), Z0 + r() * (Z1 - Z0)], [176, 158, 132]) // acoustic panels W
  for (let i = 0; i < 480; i++) push([X1 + n(0.02), CEIL + r() * (FLOOR - CEIL), Z0 + r() * (Z1 - Z0)], [214, 210, 202]) // wall E
  for (let i = 0; i < 420; i++) push([X0 + r() * (X1 - X0), CEIL + r() * (FLOOR - CEIL), Z1 + n(0.02)], [215, 212, 205]) // back wall
  // object surfaces (denser, own colour)
  for (const o of OBJECTS) {
    if (o.label === 'wall') continue
    const k = Math.round(Math.min(90, 14 + o.ext[0] * o.ext[1] * 30 + o.ext[1] * o.ext[2] * 30))
    for (let i = 0; i < k; i++) push([o.pos[0] + n(o.ext[0]), o.pos[1] + n(o.ext[1]), o.pos[2] + n(o.ext[2])], o.rgb, 10)
  }
  // a few outliers like real SfM
  for (let i = 0; i < 40; i++) push([n(9), n(5), 4 + n(12)], [150, 150, 150], 60)
  return pts
}

function buildCameras(): Scan3D['cameras'] {
  const cams: Scan3D['cameras'] = []
  const N = 16
  for (let i = 0; i < N; i++) {
    const f = i / (N - 1)
    const z = 0.6 + f * 4.6
    const x = -0.4 + Math.sin(f * Math.PI) * 0.8
    const yaw = -0.9 + f * 2.2 // sweep from left wall across the room to the right, then the back
    const look: V3 = [Math.sin(yaw), 0.08, Math.cos(yaw)]
    const len = Math.hypot(...look)
    cams.push({ t: +(f * 24).toFixed(1), position: [+x.toFixed(3), +(0.02 * Math.sin(i)).toFixed(3), +z.toFixed(3)], look: look.map(v => +(v / len).toFixed(3)) as V3, frame: null })
  }
  return cams
}

let cached: Scan3D | null = null

/** Mock scans: cap-e2e-2 is a good reconstruction, cap-1120-a failed (objects only from 2D). */
export function mockScan3d(cid: string): Scan3D | null {
  if (cid === 'cap-1120-a') {
    const objects = buildObjects().filter(o => ['obj-8', 'obj-9', 'obj-10', 'obj-6'].includes(o.id)).map(o => ({ ...o, position: null, extent: null }))
    return {
      capture_id: cid, ok: false, reason: 'zu wenig Überlappung zwischen den Bildern (9 von 48 registriert)', seconds: 38.5,
      frames_used: 48, frames_registered: 9, points: [], cameras: [], objects, units: 'relative (SfM scale is arbitrary)',
    }
  }
  if (cid !== 'cap-e2e-2' && !cid.startsWith('demo')) return null
  cached ??= {
    capture_id: 'cap-e2e-2', ok: true, reason: null, seconds: 74.2, frames_used: 61, frames_registered: 55,
    points: buildPoints(rng(42)), cameras: buildCameras(), objects: buildObjects(), units: 'relative (SfM scale is arbitrary)',
  }
  return { ...cached, capture_id: cid }
}

export const MOCK_3D_IDS = new Set(['cap-e2e-2', 'cap-1120-a'])
