// Shared helpers for the screen recordings: headless Chrome via puppeteer-core, a visible cursor that
// follows the real (CDP) mouse, a CDP screencast recorder and an H.264 encoder (Remotion's bundled ffmpeg).
import fs from 'node:fs'
import path from 'node:path'
import { spawn } from 'node:child_process'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
export const REPO = path.resolve(HERE, '../..')
export const OUT = path.resolve(HERE, '../video/public/rec')

// A folder whose node_modules has puppeteer-core and @remotion/compositor-* (for ffmpeg).
const TOOL_DIRS = [process.env.TW_TOOLS, path.join(HERE, '../video'), path.resolve(REPO, '../demo-video')].filter(Boolean)
function findTool(rel) {
  for (const d of TOOL_DIRS) {
    const p = path.join(d, 'node_modules', rel)
    if (fs.existsSync(p)) return p
  }
  throw new Error(`${rel} not found in ${TOOL_DIRS.join(', ')} (set TW_TOOLS to a folder with node_modules)`)
}
const require = createRequire(findTool('puppeteer-core/package.json'))
const puppeteer = require('puppeteer-core')
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

export const sleep = ms => new Promise(r => setTimeout(r, ms))
export const FPS = 30

/** 1920x1080 device pixels: CSS viewport = 1920/dsf x 1080/dsf. */
export async function launch({ dsf = 1.2 } = {}) {
  const width = Math.round(1920 / dsf), height = Math.round(1080 / dsf)
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: true, defaultViewport: null,
    // the screencast delivers device pixels only when the scale factor is forced at browser level too
    args: [`--window-size=${width},${height}`, `--force-device-scale-factor=${dsf}`, '--hide-scrollbars', '--enable-unsafe-swiftshader', '--force-color-profile=srgb'],
  })
  const page = (await browser.pages())[0]
  await page.setViewport({ width, height, deviceScaleFactor: dsf })
  await installCursor(page)
  page.tw = { x: width * 0.55, y: height * 0.5, width, height }
  return { browser, page }
}

// ---------- cursor ----------
// Headless Chrome draws no pointer. This overlay is the only thing added to the page: an arrow that follows the
// real pointer events (the ones puppeteer sends through CDP) and a ripple on pointerdown. pointer-events: none.
const CURSOR_JS = `(() => {
  if (window.__twCursor) return
  window.__twCursor = true
  const make = () => {
    const c = document.createElement('div')
    c.id = 'tw-rec-cursor'
    c.style.cssText = 'position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;width:26px;height:26px;display:none;will-change:transform;filter:drop-shadow(0 1px 2px rgba(0,0,0,.45))'
    c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M4 2.5v17.2l4.6-4.3 2.9 6.6 2.9-1.3-2.9-6.4h6.3z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>'
    document.documentElement.appendChild(c)
    const place = e => { c.style.display = 'block'; c.style.transform = 'translate(' + (e.clientX - 4) + 'px,' + (e.clientY - 2.5) + 'px)' }
    // pointer events: a control that calls preventDefault on pointerdown (the Radix slider) gets no mousemove while dragging
    window.addEventListener('pointermove', place, true)
    window.addEventListener('pointerdown', e => {
      place(e)
      const r = document.createElement('div')
      r.style.cssText = 'position:fixed;z-index:2147483646;pointer-events:none;border-radius:50%;width:44px;height:44px;left:' + (e.clientX - 22) + 'px;top:' + (e.clientY - 22) + 'px;background:rgba(37,99,235,.28);border:2px solid rgba(37,99,235,.85)'
      document.documentElement.appendChild(r)
      r.animate([{ transform: 'scale(.25)', opacity: 1 }, { transform: 'scale(1.25)', opacity: 0 }], { duration: 520, easing: 'ease-out' }).onfinish = () => r.remove()
    }, true)
  }
  if (document.documentElement && document.readyState !== 'loading') make()
  else document.addEventListener('DOMContentLoaded', make)
})()`

async function installCursor(page) {
  await page.evaluateOnNewDocument(CURSOR_JS)
}

const ease = t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)

/** Glide the mouse to (x, y); duration grows with the distance unless given. */
export async function moveTo(page, x, y, ms) {
  const s = page.tw
  const dx = x - s.x, dy = y - s.y, dist = Math.hypot(dx, dy)
  const dur = ms ?? Math.min(1300, Math.max(380, 260 + dist * 1.15))
  const t0 = performance.now()
  // a slight arc so the path does not look like a ruler
  const bend = Math.min(40, dist * 0.08), nx = dist ? -dy / dist : 0, ny = dist ? dx / dist : 0
  for (;;) {
    const t = Math.min(1, (performance.now() - t0) / dur), k = ease(t), arc = Math.sin(Math.PI * k) * bend
    await page.mouse.move(s.x + dx * k + nx * arc, s.y + dy * k + ny * arc)
    if (t >= 1) break
    await sleep(8)
  }
  s.x = x; s.y = y
}

/** Centre (or a relative point) of the first element matching the selector / returned by the function. */
export async function pointOf(page, target, { rx = 0.5, ry = 0.5, arg } = {}) {
  const box = await page.evaluate((t, a) => {
    const el = typeof t === 'string' && !t.startsWith('(') ? document.querySelector(t) : (0, eval)(t)(a)
    if (!el) return null
    const r = el.getBoundingClientRect()
    return { x: r.x, y: r.y, w: r.width, h: r.height }
  }, typeof target === 'function' ? `(${target})` : target, arg)
  if (!box) throw new Error(`element not found: ${target}`)
  return { x: box.x + box.w * rx, y: box.y + box.h * ry, box }
}

export async function moveToEl(page, target, opts = {}) {
  const p = await pointOf(page, target, opts)
  await moveTo(page, p.x + (opts.dx ?? 0), p.y + (opts.dy ?? 0), opts.ms)
  return p
}

export async function click(page) {
  await page.mouse.down()
  await sleep(70)
  await page.mouse.up()
}

/** Show the cursor at its current position (after a page load the overlay is new and hidden). */
export async function showCursor(page) {
  await page.mouse.move(page.tw.x + 0.5, page.tw.y)
  await page.mouse.move(page.tw.x, page.tw.y)
}

// ---------- recorder ----------
export class Recorder {
  constructor(page, id) { this.page = page; this.id = id; this.frames = []; this.marks = {} }

  async start() {
    this.cdp = await this.page.createCDPSession()
    this.cdp.on('Page.screencastFrame', f => {
      this.frames.push({ ts: f.metadata.timestamp, data: Buffer.from(f.data, 'base64') })
      this.cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => {})
    })
    await this.cdp.send('Page.startScreencast', { format: 'jpeg', quality: 93, everyNthFrame: 1, maxWidth: 1920, maxHeight: 1080 })
    // the first frame defines t = 0
    const t0 = Date.now()
    while (!this.frames.length && Date.now() - t0 < 5000) await sleep(20)
    if (!this.frames.length) throw new Error('screencast delivered no frame')
    this.t0 = this.frames[0].ts // epoch seconds, same clock as Date.now() (measured: within 10 ms)
  }

  /** Seconds since the first frame. */
  now() { return Date.now() / 1000 - this.t0 }
  mark(name) { this.marks[name] = +this.now().toFixed(2); console.log(`  mark ${name} @ ${this.marks[name]}s`) }

  async stop({ tail = 0 } = {}) {
    if (tail) await sleep(tail)
    const end = this.now()
    await this.cdp.send('Page.stopScreencast')
    await sleep(150)
    await this.cdp.detach()
    const seconds = Math.floor(end * FPS) / FPS
    const n = Math.round(seconds * FPS)
    // resample to constant 30 fps: output frame i shows the last captured frame at or before i/30
    const seq = []
    let j = 0
    for (let i = 0; i < n; i++) {
      const t = this.t0 + i / FPS
      while (j + 1 < this.frames.length && this.frames[j + 1].ts <= t) j++
      seq.push(j)
    }
    const used = new Set(seq).size
    const gaps = this.frames.slice(1).map((f, i) => f.ts - this.frames[i].ts)
    const stats = {
      captured_frames: this.frames.length, distinct_frames_in_output: used,
      // the screencast only sends a frame when the picture changes, so the average counts the still moments too
      capture_fps_avg: +(this.frames.length / (this.frames.at(-1).ts - this.t0)).toFixed(1),
      fps_while_changing: +(1 / [...gaps].sort((a, b) => a - b)[Math.floor(gaps.length / 2)]).toFixed(1), // 1 / median gap
      longest_still_s: +Math.max(0, ...gaps).toFixed(2),
    }
    fs.mkdirSync(OUT, { recursive: true })
    const mp4 = path.join(OUT, `${this.id}.mp4`)
    await encode(seq.map(k => this.frames[k].data), mp4)
    const meta = { seconds: +seconds.toFixed(2), marks: this.marks, capture: stats }
    fs.writeFileSync(path.join(OUT, `${this.id}.json`), JSON.stringify(meta, null, 1) + '\n')
    console.log(`${this.id}: ${meta.seconds}s`, JSON.stringify(this.marks), JSON.stringify(stats))
    this.frames = []
    return meta
  }
}

function ffmpegBin() {
  const dir = path.dirname(findTool(`@remotion/compositor-${process.platform}-${process.arch}/ffmpeg`))
  const env = { ...process.env, DYLD_LIBRARY_PATH: dir, LD_LIBRARY_PATH: dir }
  return { bin: path.join(dir, 'ffmpeg'), probe: path.join(dir, 'ffprobe'), env }
}

/** JPEG buffers (all 1920x1080) -> H.264 yuv420p, constant 30 fps, no audio. */
export function encode(jpegs, file) {
  const { bin, env } = ffmpegBin()
  return new Promise((resolve, reject) => {
    const ff = spawn(bin, ['-y', '-hide_banner', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-color_range', 'tv', '-r', String(FPS), '-movflags', '+faststart', file],
    { env, stdio: ['pipe', 'inherit', 'inherit'] })
    ff.on('error', reject)
    ff.on('close', c => (c === 0 ? resolve() : reject(new Error(`ffmpeg exit ${c}`))))
    ff.stdin.on('error', reject)
    ;(async () => {
      for (const b of jpegs) if (!ff.stdin.write(b)) await new Promise(r => ff.stdin.once('drain', r))
      ff.stdin.end()
    })()
  })
}

export function ffrun(args, which = 'bin') {
  const f = ffmpegBin()
  return new Promise((resolve, reject) => {
    let out = ''
    const p = spawn(f[which], args, { env: f.env })
    p.stdout.on('data', d => (out += d)); p.stderr.on('data', d => (out += d))
    p.on('close', c => (c === 0 ? resolve(out) : reject(new Error(out))))
  })
}
