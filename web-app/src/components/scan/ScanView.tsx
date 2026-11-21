import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, ArrowLeft, Box, EyeOff, Layers, Loader2, MessageSquareQuote, Route as RouteIcon, Tag, FlipVertical2, Upload, Video } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Toggle } from '@/components/ui/toggle'
import { fetchScan3d, uploadLayout } from '@/lib/api'
import { num } from '@/lib/format'
import type { Scan3D, ScanMention, ScanObject, ScanSection } from '@/lib/types'
import { cn } from '@/lib/utils'
import { SceneView } from './SceneView'

const CAT_COLORS: Record<string, string> = {
  'Öffnungen': '#38bdf8', 'Elektro': '#facc15', 'Heizung / Lüftung': '#f87171', 'Ausstattung': '#a78bfa',
  'Bauteile': '#94a3b8', 'Sanitär': '#2dd4bf', 'Baustelle': '#fb923c',
}
const PALETTE = ['#34d399', '#f472b6', '#60a5fa', '#fbbf24', '#c084fc', '#4ade80']
const SAID = '#f59e0b' // objects the speaker named (same amber as in SceneView)
const TALK_BEFORE_S = 1, TALK_AFTER_S = 3 // a mention "is being said" from 1 s before to 3 s after its estimated second

function mmss(t: number | null | undefined) {
  if (t == null) return '–'
  const s = Math.max(0, Math.round(t))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
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
  const [sectionId, setSectionId] = useState(0) // -1 = the phone-scan room (layout)
  const [reload, setReload] = useState(0)
  const [uploadMsg, setUploadMsg] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const [follow, setFollow] = useState(true) // the section follows the video time

  useEffect(() => {
    let live = true
    setState({ loading: true, scan: null, demo: false })
    setSelected(null)
    setSectionId(0)
    fetchScan3d(cid).then(r => {
      if (!live) return
      setState({ loading: false, scan: r.data, demo: r.demo, error: r.error })
      setFlipY(!r.data?.gravity_aligned && !r.data?.layout) // levelled scans already have +y up; raw SfM points down
      if (r.data?.layout) { setSectionId(-1); setFollow(false) } // the joined room first
    })
    return () => { live = false }
  }, [cid, reload])

  const scan = state.scan
  const sel = scan?.objects.find(o => o.id === selected) ?? null
  const sections: ScanSection[] = useMemo(() => scan?.sections?.length ? scan.sections : [], [scan])
  const view = useMemo<Scan3D | null>(() => { // the scene shows one section: its points, cameras and objects
    if (scan && sectionId === -1 && scan.layout) return { ...scan, points: [], cameras: [], objects: [] }
    if (!scan || !sections.length) return scan
    const s = sections.find(x => x.id === sectionId) ?? sections[0]
    return { ...scan, points: s.points, cameras: s.cameras, objects: scan.objects.filter(o => (o.section ?? 0) === s.id) }
  }, [scan, sections, sectionId])
  const groups = useMemo(() => { // the object list follows the section shown ("Gesagt" stays global)
    const m = new Map<string, ScanObject[]>()
    view?.objects.forEach(o => m.set(o.category_de, [...(m.get(o.category_de) ?? []), o]))
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0], 'de'))
  }, [view])
  const choose = (id: string | null) => { // select an object, switching to its section
    const o = id ? scan?.objects.find(x => x.id === id) : null
    if (o && sections.length && (o.section ?? 0) !== sectionId) { setSectionId(o.section ?? 0); setFollow(false) }
    setSelected(id)
  }
  const onVideoTime = (t: number) => {
    setVt(t)
    if (!follow || !sections.length) return
    const s = sections.filter(x => t >= x.t_start - 0.5 && t <= x.t_end + 0.5).sort((a, b) => b.frames_registered - a.frames_registered)[0]
    if (s && s.id !== sectionId) setSectionId(s.id)
  }
  const videoRef = useRef<HTMLVideoElement>(null)
  const seekTo = useRef<number | null>(null) // set by a "Gesagt" click: seek there instead of the first sighting
  useEffect(() => { // jump the walkthrough video to where the selected object was first seen (or was named)
    const v = videoRef.current
    const t = seekTo.current ?? sel?.first_t
    seekTo.current = null
    if (v && sel && t != null) { v.currentTime = Math.max(0, t); v.play().catch(() => {}) }
  }, [sel])
  const mentions = useMemo(() => [...(scan?.mentions ?? [])].sort((a, b) => (a.t ?? 0) - (b.t ?? 0)), [scan])
  const unseen = scan?.unseen_mentions ?? []
  const [vt, setVt] = useState<number | null>(null) // current video time while it plays
  const talkingMentions = useMemo(
    () => (vt == null ? [] : mentions.filter(m => m.t != null && vt >= m.t - TALK_BEFORE_S && vt <= m.t + TALK_AFTER_S)),
    [mentions, vt],
  )
  const talking = useMemo(() => [...new Set(talkingMentions.flatMap(m => m.object_ids))], [talkingMentions])
  // banner: the item named most recently (several can overlap: "tables …, slab …, dustbins" within 3 s)
  const nowSaid = useMemo(
    () => talkingMentions.filter(m => vt != null && (m.t ?? 0) <= vt).at(-1) ?? talkingMentions[0] ?? null,
    [talkingMentions, vt],
  )
  const openMention = (m: ScanMention) => {
    const id = m.object_ids[0]
    if (!id) return
    seekTo.current = Math.max(0, (m.t ?? m.t_start ?? 0) - 0.5)
    if (id === selected) { // already selected: the effect will not run again, seek directly
      const v = videoRef.current
      if (v) { v.currentTime = seekTo.current; seekTo.current = null; v.play().catch(() => {}) }
    }
    choose(id)
  }
  const seekOnly = (t: number | null) => {
    const v = videoRef.current
    if (v && t != null) { v.currentTime = Math.max(0, t - 0.5); v.play().catch(() => {}) }
  }
  const cOf = useCallback(colorOf, [])

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3" data-testid="scan-view">
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" onClick={onBack}><ArrowLeft /> Zurück</Button>
        <h2 className="flex items-center gap-2 text-base font-semibold"><Box className="size-4 text-muted-foreground" /> 3D-Scan <span className="font-mono text-sm font-normal text-muted-foreground">{cid}</span></h2>
        {state.demo && <Badge className="bg-amber-500 text-white">Demo-Daten</Badge>}
        {scan && (
          <span className="text-xs text-muted-foreground tabular-nums">
            {scan.frames_registered ?? '–'} / {scan.frames_used ?? '–'} Bilder registriert
            {sections.length > 1 && ` in ${sections.length} Abschnitten`} · {sectionId === -1 && scan.layout ? `${scan.layout.faces.toLocaleString('de-DE')} Dreiecke (Raumscan)` : `${(view ?? scan).points.length.toLocaleString('de-DE')} Punkte`} · {scan.objects.length} Objekte
            {scan.gravity_aligned && ' · Boden waagrecht, Maße ≈ m'}
            {scan.seconds != null && ` · ${num(scan.seconds, 0)} s Rechenzeit`}
          </span>
        )}
        {scan?.ok && (
          <div className="ml-auto flex items-center gap-1">
            <input ref={fileRef} type="file" accept=".glb,.gltf,.obj,.ply" className="hidden" data-testid="layout-file"
              onChange={async e => {
                const f = e.currentTarget.files?.[0]
                if (!f) return
                setUploadMsg('lädt …')
                const err = await uploadLayout(cid, f)
                setUploadMsg(err ? `Fehler: ${err}` : null)
                if (!err) setReload(x => x + 1)
              }} />
            <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()} title="Raumscan vom Handy (GLB/OBJ/PLY, z. B. Polycam) als zusammenhängendes Raumlayout"><Upload /> {scan.layout ? 'Raumscan ersetzen' : 'Raumscan hinzufügen'}</Button>
            {uploadMsg && <span className="text-xs text-muted-foreground">{uploadMsg}</span>}
            <Toggle size="sm" variant="outline" pressed={showPath} onPressedChange={setShowPath} aria-label="Kamerapfad"><RouteIcon /> Kamerapfad</Toggle>
            <Toggle size="sm" variant="outline" pressed={showLabels} onPressedChange={setShowLabels} aria-label="Beschriftungen"><Tag /> Beschriftungen</Toggle>
            <Toggle size="sm" variant="outline" pressed={flipY} onPressedChange={setFlipY} aria-label="Hochachse umkehren" title="SfM-Koordinaten zeigen nach unten; umkehren, falls der Raum kopfsteht"><FlipVertical2 /> Hochachse</Toggle>
          </div>
        )}
      </div>

      {scan?.ok && (sections.length > 1 || scan.layout) && (
        <div className="flex items-center gap-2" data-testid="scan-sections">
          <span className="flex shrink-0 items-center gap-1 text-xs font-medium text-muted-foreground"><Layers className="size-3.5" /> Abschnitte</span>
          <div className="flex min-w-0 flex-1 gap-1 overflow-x-auto pb-0.5">
            {scan.layout && (
              <button type="button" data-testid="scan-layout-chip" onClick={() => { setSectionId(-1); setFollow(false); setSelected(null) }}
                title={`${scan.layout.source} · ${scan.layout.faces.toLocaleString('de-DE')} Dreiecke`}
                className={cn('shrink-0 rounded-full border px-2.5 py-0.5 text-xs hover:bg-muted', sectionId === -1 && 'border-emerald-500 bg-emerald-50 font-medium text-emerald-900')}>
                Raum (Scan) · {scan.layout.size[0].toFixed(1)}×{scan.layout.size[2].toFixed(1)} m
              </button>
            )}
            {[...sections].sort((a, b) => a.t_start - b.t_start).map(s => (
              <button key={s.id} type="button" onClick={() => { setSectionId(s.id); setFollow(false); setSelected(null) }}
                title={`${s.frames_registered} Bilder · ${s.points.length.toLocaleString('de-DE')} Punkte · ${s.objects} Objekte`}
                className={cn('shrink-0 rounded-full border px-2.5 py-0.5 text-xs tabular-nums hover:bg-muted',
                  s.id === sectionId && 'border-cyan-500 bg-cyan-50 font-medium text-cyan-900',
                  vt != null && vt >= s.t_start && vt <= s.t_end && s.id !== sectionId && 'border-cyan-300')}>
                {mmss(s.t_start)}–{mmss(s.t_end)} <span className="text-muted-foreground">· {s.frames_registered} B.</span>
              </button>
            ))}
          </div>
          <Toggle size="sm" variant="outline" pressed={follow} onPressedChange={setFollow} aria-label="Video folgen" title="Abschnitt passend zur Videozeit wählen"><Video /> Video folgen</Toggle>
        </div>
      )}

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
              <SceneView key={sectionId === -1 ? 'layout' : 'sfm'} layout={sectionId === -1 ? scan.layout : null} scan={view!} colorOf={cOf} selected={selected} onSelect={choose} showPath={showPath} showLabels={showLabels} flipY={flipY} talking={talking} />
              {nowSaid && (
                <div className="pointer-events-none absolute top-3 left-1/2 max-w-[80%] -translate-x-1/2 rounded-full bg-amber-500/95 px-3 py-1 text-sm font-medium text-white shadow" data-testid="scan-talking">
                  <MessageSquareQuote className="mr-1 inline size-4" /> „{nowSaid.phrase}“ → {nowSaid.name_de}
                  {nowSaid.state_de && ` · ${nowSaid.state_de}`}
                </div>
              )}
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
          {scan?.video && (
            <video ref={videoRef} src={scan.video} controls playsInline muted preload="metadata"
              onTimeUpdate={e => onVideoTime(e.currentTarget.currentTime)} onSeeked={e => onVideoTime(e.currentTarget.currentTime)}
              className="aspect-video w-full shrink-0 bg-black" data-testid="scan-video" />
          )}
          <CardHeader className="border-b py-3">
            <CardTitle className="text-sm">Objekte nach Kategorie{sections.length > 1 && <span className="font-normal text-muted-foreground"> · dieser Abschnitt</span>}</CardTitle>
          </CardHeader>
          <ScrollArea className="min-h-0 flex-1">
            <div className="flex flex-col gap-3 p-3" data-testid="scan-objects">
              {sel && <ObjectDetail o={sel} objects={scan!.objects} color={sel.mentioned ? SAID : colorOf(sel.category_de)} onSelect={choose} />}
              {(mentions.length > 0 || unseen.length > 0) && (
                <div data-testid="scan-said">
                  <div className="mb-1 flex items-center gap-2 text-[11px] font-medium tracking-wide text-amber-700 uppercase">
                    <MessageSquareQuote className="size-3.5" /> Gesagt
                    <span className="ml-auto tabular-nums">{mentions.length}</span>
                  </div>
                  <ul className="flex flex-col gap-0.5">
                    {mentions.map((m, i) => {
                      const on = talkingMentions.includes(m)
                      return (
                        <li key={i}>
                          <button type="button" onClick={() => openMention(m)} title={m.text}
                            className={cn('flex w-full items-start gap-2 rounded-md border border-transparent px-2 py-1.5 text-left text-sm hover:bg-amber-50',
                              on && 'border-amber-400 bg-amber-100', m.object_ids.includes(selected ?? '') && 'bg-amber-50 font-medium')}>
                            <span className="w-9 shrink-0 font-mono text-[11px] leading-5 text-muted-foreground tabular-nums">{mmss(m.t)}</span>
                            <span className="min-w-0 flex-1">
                              <span className="font-medium">„{m.phrase}“</span> <span className="text-muted-foreground">→ {m.name_de}</span>
                              {m.object_ids.length > 1 && <span className="text-[11px] text-muted-foreground"> ({m.object_ids.length}×)</span>}
                            </span>
                            {m.state_de && <Badge variant="outline" className="shrink-0 border-amber-400 text-[10px] text-amber-800">{m.state_de}</Badge>}
                          </button>
                        </li>
                      )
                    })}
                  </ul>
                  {unseen.length > 0 && (
                    <>
                      <div className="mt-2 mb-1 flex items-center gap-2 text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
                        <EyeOff className="size-3.5" /> Genannt, nicht im Bild
                      </div>
                      <ul className="flex flex-col gap-0.5" data-testid="scan-unseen">
                        {unseen.map((u, i) => (
                          <li key={i}>
                            <button type="button" onClick={() => seekOnly(u.t)} title={u.text}
                              className="flex w-full items-start gap-2 rounded-md px-2 py-1 text-left text-sm text-muted-foreground hover:bg-muted">
                              <span className="w-9 shrink-0 font-mono text-[11px] leading-5 tabular-nums">{mmss(u.t)}</span>
                              <span className="min-w-0 flex-1">„{u.phrase}“ → {u.name}{(u.times?.length ?? 0) > 1 && <span className="text-[11px]"> ({u.times!.length}×)</span>}</span>
                              {u.state_de && <span className="text-[11px]">{u.state_de}</span>}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                  <Separator className="mt-3" />
                </div>
              )}
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
                          onClick={() => choose(o.id === selected ? null : o.id)}
                          className={cn('flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted', o.id === selected && 'bg-muted font-medium')}
                        >
                          <span className="flex-1 truncate">{o.name_de}</span>
                          {o.mentioned && <i className={cn('inline-block size-2 rounded-full', talking.includes(o.id) && 'animate-ping')} style={{ background: SAID }} title={`gesagt: „${o.spoken_phrase ?? o.name_de}“`} />}
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
      {o.mentioned && (
        <div className="mb-2 rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-900" data-testid="scan-detail-said">
          gesagt bei {(o.mention_times ?? []).map(mmss).join(', ')}: „{o.spoken_phrase ?? o.name_de}“{o.spoken_state_de ? ` · ${o.spoken_state_de}` : ''}
        </div>
      )}
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
