// three.js scene for a scan: coloured point cloud, camera path with frustums, one box + label per object.
// Objects the speaker named are amber with a halo and the spoken phrase; the ones being talked about now pulse.
import { useEffect, useRef } from 'react'
import {
  AmbientLight, BoxGeometry, BufferGeometry, Color, EdgesGeometry, Float32BufferAttribute, Group, Line, LineBasicMaterial,
  LineSegments, Mesh, MeshBasicMaterial, PerspectiveCamera, Points, PointsMaterial, SRGBColorSpace, Scene, SphereGeometry, Vector3,
  WebGLRenderer,
} from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { CSS2DObject, CSS2DRenderer } from 'three/addons/renderers/CSS2DRenderer.js'
import type { Scan3D } from '@/lib/types'

interface Props {
  scan: Scan3D
  colorOf: (category: string) => string
  selected: string | null
  onSelect: (id: string | null) => void
  showPath: boolean
  showLabels: boolean
  flipY: boolean
  talking?: string[] // ids of the objects being talked about at the current video time
}

const SAID_COLOR = '#f59e0b'

function percentile(sorted: number[], p: number) {
  if (!sorted.length) return 0
  return sorted[Math.min(sorted.length - 1, Math.max(0, Math.round((sorted.length - 1) * p)))]
}

export function SceneView({ scan, colorOf, selected, onSelect, showPath, showLabels, flipY, talking }: Props) {
  const host = useRef<HTMLDivElement>(null)
  const api = useRef<{
    select: (id: string | null) => void
    setPath: (v: boolean) => void
    setLabels: (v: boolean) => void
    setFlip: (v: boolean) => void
    setTalking: (ids: string[]) => void
  } | null>(null)
  const onSel = useRef(onSelect)
  onSel.current = onSelect

  useEffect(() => {
    const el = host.current
    if (!el) return
    const W = () => el.clientWidth, H = () => el.clientHeight

    const scene = new Scene()
    scene.background = new Color('#141416')
    scene.add(new AmbientLight(0xffffff, 1))
    const root = new Group()
    scene.add(root)

    // robust scene extent (ignore SfM outliers)
    const src = scan.points.length ? scan.points.map(p => [p[0], p[1], p[2]]) : scan.objects.filter(o => o.position).map(o => o.position!)
    const axes = [0, 1, 2].map(i => src.map(p => p[i]).sort((a, b) => a - b))
    const lo = axes.map(a => percentile(a, 0.03)), hi = axes.map(a => percentile(a, 0.97))
    const center = new Vector3((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2)
    const diag = Math.max(1e-3, Math.hypot(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]))

    // points
    if (scan.points.length) {
      const pos = new Float32Array(scan.points.length * 3), col = new Float32Array(scan.points.length * 3)
      const c = new Color()
      scan.points.forEach((p, i) => {
        pos.set([p[0], p[1], p[2]], i * 3)
        c.setRGB(p[3] / 255, p[4] / 255, p[5] / 255, SRGBColorSpace) // sRGB bytes -> linear working space
        col.set([c.r, c.g, c.b], i * 3)
      })
      const g = new BufferGeometry()
      g.setAttribute('position', new Float32BufferAttribute(pos, 3))
      g.setAttribute('color', new Float32BufferAttribute(col, 3))
      root.add(new Points(g, new PointsMaterial({ size: diag * 0.006, vertexColors: true, sizeAttenuation: true })))
    }

    // camera path + frustums
    const pathGroup = new Group()
    if (scan.cameras.length) {
      const line = new BufferGeometry().setFromPoints(scan.cameras.map(c => new Vector3(...c.position)))
      pathGroup.add(new Line(line, new LineBasicMaterial({ color: '#22d3ee' })))
      const s = diag * 0.025
      const seg: Vector3[] = []
      for (const c of scan.cameras) {
        const p = new Vector3(...c.position)
        const look = new Vector3(...c.look).normalize()
        const worldUp = Math.abs(look.y) > 0.95 ? new Vector3(0, 0, 1) : new Vector3(0, -1, 0)
        const right = new Vector3().crossVectors(look, worldUp).normalize()
        const up = new Vector3().crossVectors(right, look).normalize()
        const base = p.clone().addScaledVector(look, s)
        const corners = [[1, 1], [1, -1], [-1, -1], [-1, 1]].map(([a, b]) => base.clone().addScaledVector(right, a * s * 0.6).addScaledVector(up, b * s * 0.45))
        corners.forEach((c2, i) => { seg.push(p, c2, c2, corners[(i + 1) % 4]) })
      }
      pathGroup.add(new LineSegments(new BufferGeometry().setFromPoints(seg), new LineBasicMaterial({ color: '#67e8f9', transparent: true, opacity: 0.7 })))
    }
    root.add(pathGroup)

    // objects
    const objGroup = new Group()
    const boxes = new Map<string, { edges: LineSegments; dot: Mesh; label: CSS2DObject; color: string; halo: Mesh | null }>()
    const dotGeo = new SphereGeometry(diag * 0.006, 12, 8)
    const haloGeo = new SphereGeometry(diag * 0.018, 16, 12)
    for (const o of scan.objects) {
      if (!o.position) continue
      const said = !!o.mentioned
      const color = said ? SAID_COLOR : colorOf(o.category_de)
      const ext = o.extent ?? [diag * 0.02, diag * 0.02, diag * 0.02]
      const edges = new LineSegments(
        new EdgesGeometry(new BoxGeometry(Math.max(ext[0], 0.01), Math.max(ext[1], 0.01), Math.max(ext[2], 0.01))),
        new LineBasicMaterial({ color, transparent: true, opacity: 0.85 }),
      )
      edges.position.set(...o.position)
      const dot = new Mesh(dotGeo, new MeshBasicMaterial({ color }))
      dot.position.set(...o.position)
      let halo: Mesh | null = null
      if (said) {
        dot.scale.setScalar(2)
        halo = new Mesh(haloGeo, new MeshBasicMaterial({ color: SAID_COLOR, transparent: true, opacity: 0.28, depthWrite: false }))
        halo.position.set(...o.position)
        objGroup.add(halo)
      }
      const div = document.createElement('button')
      div.type = 'button'
      div.className = 'tw-scan-label'
      div.style.setProperty('--c', color)
      div.textContent = o.name_de
      if (said) {
        div.dataset.said = '1'
        const small = document.createElement('small')
        small.textContent = `„${o.spoken_phrase ?? o.name_de}“${o.spoken_state_de ? ` · ${o.spoken_state_de}` : ''}`
        div.appendChild(small)
      }
      div.dataset.obj = o.id
      div.addEventListener('pointerdown', e => e.stopPropagation())
      div.addEventListener('click', e => { e.stopPropagation(); onSel.current(o.id) })
      const label = new CSS2DObject(div)
      label.position.set(o.position[0], o.position[1] - (ext[1] / 2) * (flipY ? 1 : -1) - diag * 0.01, o.position[2])
      label.center.set(0.5, 1)
      objGroup.add(edges, dot, label)
      boxes.set(o.id, { edges, dot, label, color, halo })
    }
    root.add(objGroup)

    const renderer = new WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio))
    renderer.setSize(W(), H())
    el.appendChild(renderer.domElement)
    const labels = new CSS2DRenderer()
    labels.setSize(W(), H())
    Object.assign(labels.domElement.style, { position: 'absolute', inset: '0', pointerEvents: 'none' })
    el.appendChild(labels.domElement)

    const camera = new PerspectiveCamera(55, W() / H(), diag * 0.005, diag * 20)
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.12

    const applyFlip = (on: boolean) => {
      root.scale.set(1, on ? -1 : 1, 1)
      const c = center.clone().multiply(root.scale)
      controls.target.copy(c)
      // look from behind the camera path (mean viewing direction, levelled), slightly above: reads like the video
      const mean = scan.cameras.reduce((v, k) => v.add(new Vector3(...k.look)), new Vector3())
      const dir = mean.lengthSq() > 1e-6 ? mean.multiply(root.scale).setY(0) : new Vector3(0, 0, 1)
      const back = (dir.lengthSq() > 1e-6 ? dir : new Vector3(0, 0, 1)).normalize().multiplyScalar(-1)
      camera.position.copy(c).addScaledVector(back, diag * 0.7).add(new Vector3(0, diag * 0.32, 0))
      camera.up.set(0, 1, 0)
      controls.update()
    }
    applyFlip(flipY)

    let target: Vector3 | null = null
    let camDest: Vector3 | null = null
    let talkingIds = new Set<string>()
    const select = (id: string | null) => {
      boxes.forEach((b, k) => {
        const on = k === id
        ;(b.edges.material as LineBasicMaterial).color.set(on ? '#ffffff' : b.color)
        ;(b.edges.material as LineBasicMaterial).opacity = id && !on ? 0.35 : 0.9
        ;(b.label.element as HTMLElement).dataset.active = on ? '1' : id ? 'dim' : ''
      })
      const b = id ? boxes.get(id) : null
      if (b) { // fly: look at the object from the current direction, closer in
        target = b.dot.getWorldPosition(new Vector3())
        const dir = camera.position.clone().sub(controls.target)
        if (dir.lengthSq() < 1e-9) dir.set(0, 0, 1)
        camDest = target.clone().addScaledVector(dir.normalize(), diag * 0.32)
      }
    }
    api.current = {
      select,
      setPath: v => { pathGroup.visible = v },
      setLabels: v => { boxes.forEach(b => { b.label.visible = v }) },
      setFlip: v => applyFlip(v),
      setTalking: ids => {
        talkingIds = new Set(ids)
        boxes.forEach((b, k) => { (b.label.element as HTMLElement).dataset.talking = talkingIds.has(k) ? '1' : '' })
      },
    }

    let raf = 0
    const tick = () => {
      raf = requestAnimationFrame(tick)
      if (target) {
        controls.target.lerp(target, 0.12)
        if (controls.target.distanceTo(target) < diag * 0.002) target = null
      }
      if (camDest) {
        camera.position.lerp(camDest, 0.1)
        if (camera.position.distanceTo(camDest) < diag * 0.003) camDest = null
      }
      const pulse = 1 + 0.6 * (0.5 + 0.5 * Math.sin(performance.now() / 150))
      boxes.forEach((b, k) => {
        if (!b.halo) return
        const on = talkingIds.has(k)
        b.halo.scale.setScalar(on ? pulse * 1.4 : 1)
        ;(b.halo.material as MeshBasicMaterial).opacity = on ? 0.5 : 0.28
      })
      controls.update()
      renderer.render(scene, camera)
      labels.render(scene, camera)
    }
    tick()

    const ro = new ResizeObserver(() => {
      camera.aspect = W() / Math.max(1, H())
      camera.updateProjectionMatrix()
      renderer.setSize(W(), H())
      labels.setSize(W(), H())
    })
    ro.observe(el)

    return () => {
      cancelAnimationFrame(raf)
      ro.disconnect()
      controls.dispose()
      renderer.dispose()
      scene.traverse(o => {
        const m = o as Mesh
        m.geometry?.dispose?.()
        const mat = m.material as { dispose?: () => void } | undefined
        mat?.dispose?.()
      })
      el.replaceChildren()
      api.current = null
    }
    // flipY is applied through the api below; the scene is rebuilt only for a new scan
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scan, colorOf])

  useEffect(() => { api.current?.select(selected) }, [selected, scan])
  useEffect(() => { api.current?.setPath(showPath) }, [showPath, scan])
  useEffect(() => { api.current?.setLabels(showLabels) }, [showLabels, scan])
  useEffect(() => { api.current?.setFlip(flipY) }, [flipY])
  useEffect(() => { api.current?.setTalking(talking ?? []) }, [talking, scan])

  return <div ref={host} className="absolute inset-0 overflow-hidden" data-testid="scan-canvas" onDoubleClick={() => onSelect(null)} />
}
