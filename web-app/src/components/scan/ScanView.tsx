import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertTriangle, ArrowLeft, Box, Loader2, Route as RouteIcon, Tag, FlipVertical2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Toggle } from '@/components/ui/toggle'
import { fetchScan3d } from '@/lib/api'
import { num } from '@/lib/format'
import type { Scan3D, ScanObject } from '@/lib/types'
import { cn } from '@/lib/utils'
import { SceneView } from './SceneView'

const CAT_COLORS: Record<string, string> = {
  'Öffnungen': '#38bdf8', 'Elektro': '#facc15', 'Heizung / Lüftung': '#f87171', 'Ausstattung': '#a78bfa',
  'Bauteile': '#94a3b8', 'Sanitär': '#2dd4bf', 'Baustelle': '#fb923c',
}
const PALETTE = ['#34d399', '#f472b6', '#60a5fa', '#fbbf24', '#c084fc', '#4ade80']
function colorOf(cat: string) {
  if (CAT_COLORS[cat]) return CAT_COLORS[cat]
  let h = 0
  for (const ch of cat) h = (h * 31 + ch.charCodeAt(0)) | 0
  return PALETTE[Math.abs(h) % PALETTE.length]
}

export function ScanView({ cid, onBack }: { cid: string; onBack: () => void }) {
  const [state, setState] = useState<{ loading: boolean; scan: Scan3D | null; demo: boolean; error?: string }>({ loading: true, scan: null, demo: false })
  const [selected, setSelected] = useState<string | null>(null)
  const [showPath, setShowPath] = useState(true)
  const [showLabels, setShowLabels] = useState(true)
  const [flipY, setFlipY] = useState(true)

  useEffect(() => {
    let live = true
    setState({ loading: true, scan: null, demo: false })
    setSelected(null)
    fetchScan3d(cid).then(r => { if (live) setState({ loading: false, scan: r.data, demo: r.demo, error: r.error }) })
    return () => { live = false }
  }, [cid])

  const scan = state.scan
  const groups = useMemo(() => {
    const m = new Map<string, ScanObject[]>()
    scan?.objects.forEach(o => m.set(o.category_de, [...(m.get(o.category_de) ?? []), o]))
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0], 'de'))
  }, [scan])
  const sel = scan?.objects.find(o => o.id === selected) ?? null
  const cOf = useCallback(colorOf, [])

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3" data-testid="scan-view">
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" onClick={onBack}><ArrowLeft /> Zurück</Button>
        <h2 className="flex items-center gap-2 text-base font-semibold"><Box className="size-4 text-muted-foreground" /> 3D-Scan <span className="font-mono text-sm font-normal text-muted-foreground">{cid}</span></h2>
        {state.demo && <Badge className="bg-amber-500 text-white">Demo-Daten</Badge>}
        {scan && (
          <span className="text-xs text-muted-foreground tabular-nums">
            {scan.frames_registered ?? '–'} / {scan.frames_used ?? '–'} Bilder registriert · {scan.points.length.toLocaleString('de-DE')} Punkte · {scan.objects.length} Objekte
            {scan.seconds != null && ` · ${num(scan.seconds, 0)} s Rechenzeit`}
          </span>
        )}
        {scan?.ok && (
          <div className="ml-auto flex items-center gap-1">
            <Toggle size="sm" variant="outline" pressed={showPath} onPressedChange={setShowPath} aria-label="Kamerapfad"><RouteIcon /> Kamerapfad</Toggle>
            <Toggle size="sm" variant="outline" pressed={showLabels} onPressedChange={setShowLabels} aria-label="Beschriftungen"><Tag /> Beschriftungen</Toggle>
            <Toggle size="sm" variant="outline" pressed={flipY} onPressedChange={setFlipY} aria-label="Hochachse umkehren" title="SfM-Koordinaten zeigen nach unten; umkehren, falls der Raum kopfsteht"><FlipVertical2 /> Hochachse</Toggle>
          </div>
        )}
      </div>

      <div className="flex min-h-0 flex-1 gap-3">
        <Card className="relative min-w-0 flex-1 overflow-hidden py-0">
          {state.loading ? (
            <div className="flex flex-1 items-center justify-center"><Loader2 className="size-6 animate-spin text-muted-foreground" /></div>
          ) : !scan ? (
            <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-muted-foreground">
              {state.error ? `3D-Daten konnten nicht geladen werden (${state.error}).` : 'Für diese Aufnahme gibt es keine 3D-Rekonstruktion.'}
            </div>
          ) : scan.ok ? (
            <>
              <SceneView scan={scan} colorOf={cOf} selected={selected} onSelect={setSelected} showPath={showPath} showLabels={showLabels} flipY={flipY} />
              <div className="pointer-events-none absolute bottom-2 left-3 text-[11px] text-white/60">Ziehen: drehen · Rechtsklick/Shift: verschieben · Rad: zoomen · Doppelklick: Auswahl aufheben · Maßstab relativ</div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center p-6">
              <Card className="max-w-md border-amber-200 bg-amber-50 py-4" data-testid="scan-failed">
                <CardContent className="flex gap-3">
                  <AlertTriangle className="mt-0.5 size-5 shrink-0 text-amber-600" />
                  <div>
                    <div className="font-medium text-amber-900">Rekonstruktion nicht möglich: {scan.reason ?? 'unbekannter Grund'}</div>
                    <p className="mt-1 text-sm text-amber-800">
                      {scan.frames_registered ?? 0} von {scan.frames_used ?? '?'} Bildern registriert. Die erkannten Objekte und
                      Beziehungen aus den Einzelbildern stehen rechts.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </Card>

        <Card className="flex w-[330px] shrink-0 flex-col gap-0 overflow-hidden py-0">
          <CardHeader className="border-b py-3">
            <CardTitle className="text-sm">Objekte nach Kategorie</CardTitle>
          </CardHeader>
          <ScrollArea className="min-h-0 flex-1">
            <div className="flex flex-col gap-3 p-3" data-testid="scan-objects">
              {sel && <ObjectDetail o={sel} objects={scan!.objects} color={colorOf(sel.category_de)} onSelect={setSelected} />}
              {groups.length === 0 && !state.loading && <div className="text-sm text-muted-foreground">Keine Objekte erkannt.</div>}
              {groups.map(([cat, objs]) => (
                <div key={cat}>
                  <div className="mb-1 flex items-center gap-2 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
                    <i className="inline-block size-2.5 rounded-full" style={{ background: colorOf(cat) }} /> {cat}
                    <span className="ml-auto tabular-nums">{objs.length}</span>
                  </div>
                  <ul className="flex flex-col gap-0.5">
                    {objs.map(o => (
                      <li key={o.id}>
                        <button
                          type="button"
                          onClick={() => setSelected(o.id === selected ? null : o.id)}
                          className={cn('flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted', o.id === selected && 'bg-muted font-medium')}
                        >
                          <span className="flex-1 truncate">{o.name_de}</span>
                          {o.relations.length > 0 && <span className="text-[11px] text-muted-foreground">{o.relations.length} Bez.</span>}
                          <span className="w-8 text-right text-[11px] text-muted-foreground tabular-nums">{o.detections}×</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </ScrollArea>
        </Card>
      </div>
    </div>
  )
}

function ObjectDetail({ o, objects, color, onSelect }: { o: ScanObject; objects: ScanObject[]; color: string; onSelect: (id: string) => void }) {
  const [nat, setNat] = useState<{ w: number; h: number } | null>(null)
  useEffect(() => setNat(null), [o.thumb])
  const b = o.bbox_in_thumb
  return (
    <div className="rounded-lg border bg-card p-2.5 shadow-sm" data-testid="scan-detail">
      <div className="mb-2 flex items-center gap-2">
        <i className="inline-block size-3 rounded-full" style={{ background: color }} />
        <span className="font-semibold">{o.name_de}</span>
        <span className="text-xs text-muted-foreground">{o.label}</span>
        {o.element_id && <Badge variant="outline" className="ml-auto font-mono text-[10px]">{o.element_id}</Badge>}
      </div>
      {o.thumb && (
        <div className="relative overflow-hidden rounded-md bg-muted">
          <img src={o.thumb} alt={o.name_de} className="block w-full" onLoad={e => setNat({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })} />
          {b && nat && (
            <div
              className="absolute rounded-sm border-2"
              style={{ borderColor: color, left: `${(b[0] / nat.w) * 100}%`, top: `${(b[1] / nat.h) * 100}%`, width: `${((b[2] - b[0]) / nat.w) * 100}%`, height: `${((b[3] - b[1]) / nat.h) * 100}%` }}
            />
          )}
        </div>
      )}
      <div className="mt-2 grid grid-cols-3 gap-1 text-center text-[11px]">
        <Stat k="Erkennungen" v={`${o.detections}`} />
        <Stat k="Konfidenz" v={`${Math.round(o.conf * 100)} %`} />
        <Stat k="im Video" v={o.first_t != null ? `${num(o.first_t)}–${num(o.last_t)} s` : '–'} />
      </div>
      {o.relations.length > 0 && (
        <>
          <Separator className="my-2" />
          <div className="flex flex-wrap gap-1">
            {o.relations.map((r, i) => (
              <button
                key={i}
                type="button"
                onClick={() => objects.some(x => x.id === r.target) && onSelect(r.target)}
                title={`${r.rel} · Score ${num(r.score, 2)} · ${r.count}× · ${r.source === 'geometry' ? 'Geometrie' : 'Modell'}`}
                className="rounded-full border bg-muted/50 px-2 py-0.5 text-xs hover:bg-muted"
              >
                {r.rel_de} {r.target_name}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function Stat({ k, v }: { k: string; v: string }) {
  return (
    <div className="rounded-md bg-muted/50 px-1 py-1">
      <div className="font-medium tabular-nums">{v}</div>
      <div className="text-muted-foreground">{k}</div>
    </div>
  )
}
