// IFC model of the project (tessellated by scripts/ifc_to_bim.py), every element coloured by its state on the chosen day.
// Click an element for its state and activity; "Vorgang öffnen" opens the activity sheet of the dashboard.
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  AmbientLight, Box3, BufferAttribute, BufferGeometry, Color, DirectionalLight, HemisphereLight, Mesh, MeshLambertMaterial,
  PerspectiveCamera, Raycaster, Scene, SRGBColorSpace, Vector2, Vector3, WebGLRenderer,
} from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { AlertCircle, Box as BoxIcon, Loader2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { fetchBim, fetchBimModel, type BimModel, type BimState } from '@/lib/api'
import { fmtLong } from '@/lib/format'

const COLORS = {
  done: '#16a34a', // 100 %
  progress: '#f59e0b', // started
  open: '#cbd5e1', // project element, not started
  context: '#e2e8f0', // geometry without a project element
  selected: '#2563eb',
}
type Bucket = 'done' | 'progress' | 'open'
const bucketOf = (s: BimState): Bucket => (s.done ? 'done' : s.pct > 0 ? 'progress' : 'open')  // done: target state reached
const LABEL: Record<Bucket, string> = { done: 'fertig', progress: 'begonnen', open: 'nicht begonnen' }

interface Props {
  date: string
  onOpenActivity: (id: string) => void
}

export function BimView({ date, onOpenActivity }: Props) {
  const [model, setModel] = useState<BimModel | null>(null)
  const [states, setStates] = useState<Map<string, BimState> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [hideContext, setHideContext] = useState(false)

  useEffect(() => {
    let live = true
    fetchBimModel().then(m => { if (live) setModel(m) }).catch(e => live && setError((e as Error).message))
    return () => { live = false }
  }, [])
  useEffect(() => {
    let live = true
    fetchBim(date).then(b => { if (live) setStates(new Map(b.elements.map(e => [e.gid, e]))) })
      .catch(e => live && setError((e as Error).message))
    return () => { live = false }
  }, [date])

  const counts = useMemo(() => {
    const c = { done: 0, progress: 0, open: 0 }
    states?.forEach(s => { c[bucketOf(s)]++ })
    return c
  }, [states])

  if (error) {
    return (
      <Card className="m-4 flex flex-row items-center gap-3 p-4 text-sm">
        <AlertCircle className="size-5 text-destructive" /> BIM-Modell nicht verfügbar: {error}
      </Card>
    )
  }
  const sel = selected ? states?.get(selected) : null
  const selMeta = selected ? model?.index.elements.find(e => e.gid === selected) : null
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 p-3 lg:flex-row" data-testid="bim-view">
      <Card className="relative min-h-[60vh] flex-1 overflow-hidden p-0">
        {model && states ? (
          <BimScene model={model} states={states} selected={selected} onSelect={setSelected} hideContext={hideContext} />
        ) : (
          <div className="flex h-full min-h-[60vh] items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-5 animate-spin" /> BIM-Modell wird geladen …
          </div>
        )}
        <div className="pointer-events-none absolute bottom-2 left-3 text-xs text-muted-foreground">
          Ziehen: drehen · Rechtsklick: verschieben · Rad: zoomen · Klick: Bauteil
        </div>
      </Card>
      <div className="flex w-full flex-col gap-3 lg:w-80">
        <Card className="gap-2 p-4">
          <div className="flex items-center gap-2 font-medium"><BoxIcon className="size-4" /> BIM-Modell</div>
          <div className="text-xs text-muted-foreground">
            {model ? `${model.index.source} · ${model.index.elements.length} IFC-Bauteile` : '…'} · Stand {fmtLong(date)}
          </div>
          <ul className="mt-1 flex flex-col gap-1 text-sm">
            {(['done', 'progress', 'open'] as Bucket[]).map(b => (
              <li key={b} className="flex items-center gap-2">
                <span className="size-3 rounded-sm" style={{ background: COLORS[b] }} />
                <span className="flex-1">{LABEL[b]}</span>
                <span className="tabular-nums text-muted-foreground">{counts[b]}</span>
              </li>
            ))}
            <li className="flex items-center gap-2">
              <span className="size-3 rounded-sm border" style={{ background: COLORS.context }} />
              <span className="flex-1">ohne Vorgang (Kontext)</span>
            </li>
          </ul>
          <Button variant="outline" size="sm" className="mt-1" onClick={() => setHideContext(v => !v)}>
            {hideContext ? 'Kontext einblenden' : 'Kontext ausblenden'}
          </Button>
        </Card>
        <Card className="gap-2 p-4" data-testid="bim-selection">
          {sel ? (
            <>
              <div className="font-medium">{sel.name}</div>
              <div className="flex flex-wrap gap-1.5">
                <Badge variant="secondary">{sel.state_de}</Badge>
                <Badge variant="outline">{Math.round(sel.pct)} %</Badge>
                {sel.zone && <Badge variant="outline">{sel.zone}</Badge>}
              </div>
              <div className="text-xs text-muted-foreground">{selMeta?.cls} · {sel.element_id}</div>
              {sel.activity_id && (
                <Button size="sm" className="mt-1" onClick={() => onOpenActivity(sel.activity_id!)}>
                  Vorgang öffnen: {sel.activity_name}
                </Button>
              )}
            </>
          ) : selMeta ? (
            <>
              <div className="font-medium">{selMeta.name || selMeta.cls}</div>
              <div className="text-xs text-muted-foreground">{selMeta.cls} · kein Vorgang zugeordnet</div>
            </>
          ) : (
            <div className="text-sm text-muted-foreground">Bauteil im Modell anklicken.</div>
          )}
        </Card>
      </div>
    </div>
  )
}

function BimScene({ model, states, selected, onSelect, hideContext }: {
  model: BimModel; states: Map<string, BimState>; selected: string | null; onSelect: (gid: string | null) => void
  hideContext: boolean
}) {
  const host = useRef<HTMLDivElement>(null)
  const meshes = useRef(new Map<string, Mesh>())
  const mats = useRef<Record<string, MeshLambertMaterial>>({})
  const onSel = useRef(onSelect)
  useEffect(() => { onSel.current = onSelect }, [onSelect])

  // build the scene once per model
  useEffect(() => {
    const el = host.current!
    const W = () => el.clientWidth || 800
    const H = () => el.clientHeight || 600
    const { index, buffer } = model
    const pos = new Float32Array(buffer, 0, index.vertices * 3)
    const idx = new Uint32Array(buffer, index.vertices * 12, index.triangles * 3)
    const mk = (c: string, opacity = 1) => new MeshLambertMaterial({ color: new Color(c), transparent: opacity < 1, opacity })
    mats.current = {
      done: mk(COLORS.done), progress: mk(COLORS.progress), open: mk(COLORS.open, 0.85), context: mk(COLORS.context, 0.25),
      selected: mk(COLORS.selected),
    }
    const scene = new Scene()
    scene.background = new Color('#f8fafc')
    scene.add(new AmbientLight('#ffffff', 0.55), new HemisphereLight('#ffffff', '#94a3b8', 0.6))
    const sun = new DirectionalLight('#ffffff', 0.9)
    sun.position.set(1, 2, 1.5)
    scene.add(sun)
    for (const e of index.elements) {
      const g = new BufferGeometry()
      g.setAttribute('position', new BufferAttribute(pos.slice(e.v[0] * 3, (e.v[0] + e.v[1]) * 3), 3))
      g.setIndex(new BufferAttribute(idx.slice(e.i[0], e.i[0] + e.i[1]), 1))
      g.computeVertexNormals()
      const m = new Mesh(g, mats.current.context)
      m.userData.gid = e.gid
      scene.add(m)
      meshes.current.set(e.gid, m)
    }
    const box = new Box3(new Vector3(...index.bbox[0]), new Vector3(...index.bbox[1]))
    const center = box.getCenter(new Vector3())
    const diag = box.getSize(new Vector3()).length() || 10
    const renderer = new WebGLRenderer({ antialias: true })
    renderer.outputColorSpace = SRGBColorSpace
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio))
    renderer.setSize(W(), H())
    el.appendChild(renderer.domElement)
    const camera = new PerspectiveCamera(45, W() / H(), diag * 0.002, diag * 20)
    camera.position.copy(center).add(new Vector3(diag * 0.6, diag * 0.45, diag * 0.75))
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.target.copy(center)
    controls.enableDamping = true
    controls.update()

    const ray = new Raycaster()
    const ptr = new Vector2()
    let down: [number, number] | null = null
    const onDown = (ev: PointerEvent) => { down = [ev.clientX, ev.clientY] }
    const onUp = (ev: PointerEvent) => {
      if (!down || Math.hypot(ev.clientX - down[0], ev.clientY - down[1]) > 4) return // a drag, not a click
      const r = renderer.domElement.getBoundingClientRect()
      ptr.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1)
      ray.setFromCamera(ptr, camera)
      const hit = ray.intersectObjects([...meshes.current.values()].filter(m => m.visible), false)[0]
      onSel.current(hit ? (hit.object.userData.gid as string) : null)
    }
    renderer.domElement.addEventListener('pointerdown', onDown)
    renderer.domElement.addEventListener('pointerup', onUp)
    const ro = new ResizeObserver(() => {
      camera.aspect = W() / H()
      camera.updateProjectionMatrix()
      renderer.setSize(W(), H())
    })
    ro.observe(el)
    let raf = 0
    const tick = () => { raf = requestAnimationFrame(tick); controls.update(); renderer.render(scene, camera) }
    tick()
    const owned = meshes.current
    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      controls.dispose()
      owned.forEach(m => m.geometry.dispose())
      owned.clear()
      Object.values(mats.current).forEach(m => m.dispose())
      renderer.dispose()
      renderer.domElement.remove()
    }
  }, [model])

  // colours follow the day's states, the selection and the context toggle
  useEffect(() => {
    meshes.current.forEach((m, gid) => {
      const s = states.get(gid)
      m.material = gid === selected ? mats.current.selected : s ? mats.current[bucketOf(s)] : mats.current.context
      m.visible = !(hideContext && !s)
    })
  }, [states, selected, hideContext, model])

  return <div ref={host} className="absolute inset-0" />
}
