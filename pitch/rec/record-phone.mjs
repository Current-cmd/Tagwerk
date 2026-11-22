// Records the site manager app (Expo web build, 375x812 @2x) driving the real API: storyboard shots D1, D2, D7
// and the Bericht tab. Real touch events, real typing, real server answers; nothing is mocked.
// Needs (see README-phone.md): API on :8090 in its seeded state, cors-proxy on :8099, Expo web on :19006.
//   node pitch/rec/record-phone.mjs
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import { createRequire } from 'node:module'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const REPO = path.resolve(HERE, '../..')
const APP = process.env.TW_APP || 'http://localhost:19006'
const API = process.env.TW_API || 'http://localhost:8099' // the CORS proxy in front of :8090
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const OUT = path.join(REPO, 'pitch/video/public/rec')
const STILLS = path.join(REPO, 'pitch/deck/deck7/img')
const NOTE = 'Stuhlreihe A ist montiert. Zwei Mann vom Trockenbau sind krank. Kratzer an der Bühne.'
const W = 375, H = 812, DSF = 2, FPS = 30

// puppeteer-core and Remotion's bundled ffmpeg come from whichever of these folders has node_modules
const TOOLS = [process.env.TW_TOOLS, HERE, path.join(REPO, 'pitch/video'), path.resolve(REPO, '../demo-video')]
  .filter(Boolean).find((d) => fs.existsSync(path.join(d, 'node_modules/puppeteer-core')) && fs.existsSync(path.join(d, 'node_modules/.bin/remotion')))
if (!TOOLS) throw new Error('No folder with puppeteer-core and @remotion/cli found; set TW_TOOLS=<folder with node_modules>')
const puppeteer = createRequire(path.join(TOOLS, 'x.js'))('puppeteer-core')

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const now = () => Date.now() / 1000
const getJson = async (p) => (await fetch(`${API}${p}`)).json()
let seed = 7 // fixed jitter so two runs look the same
const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647)

// ---------- the project must be in its seeded state ----------
const before = await getJson('/api/overview')
const rowA0 = before.zones.flatMap((z) => z.elements).find((e) => e.id === 'E-ROW-A')
const clean = before.kpi.delay_d === 0 && before.today_capture_ids.length === 0 && rowA0?.pct === 50
  && before.proposals.some((p) => p.element_id === 'E-ROW-F')
if (!clean) throw new Error('API is not in its seeded state (need: on plan, no capture today, Stuhlreihe A 50 %, proposal for Stuhlreihe F). Reset it, see README-phone.md')

fs.mkdirSync(OUT, { recursive: true }); fs.mkdirSync(STILLS, { recursive: true })
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'tw-phone-'))

const browser = await puppeteer.launch({
  executablePath: CHROME, headless: true,
  // without --force-device-scale-factor the screencast frames come back at 1x (375x812)
  args: [`--window-size=${W},${H}`, `--force-device-scale-factor=${DSF}`, '--hide-scrollbars', '--enable-unsafe-swiftshader', '--lang=de-DE'],
})
const page = await browser.newPage()
await page.setViewport({ width: W, height: H, deviceScaleFactor: DSF, hasTouch: true, isMobile: true })
await page.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'light' }])
page.on('pageerror', (e) => console.log('pageerror:', String(e).slice(0, 300)))

// server setting + the "show taps" overlay (a soft circle under the finger, a ripple on touch down)
await page.evaluateOnNewDocument((api) => {
  localStorage.setItem('tw.settings', JSON.stringify({ server: api, token: '' }))
  const css = `
    #tw-touch{position:fixed;left:0;top:0;width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;pointer-events:none;z-index:2147483647;
      background:rgba(150,150,150,.45);border:2px solid rgba(255,255,255,.95);box-shadow:0 0 0 1px rgba(0,0,0,.22),0 2px 10px rgba(0,0,0,.18);
      opacity:0;transform:translate(-100px,-100px) scale(1.25);transition:opacity .28s ease-out}
    #tw-touch.on{opacity:1;transition:opacity .06s linear}
    .tw-ripple{position:fixed;width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;pointer-events:none;z-index:2147483646;
      border:2px solid rgba(115,115,115,.55);animation:tw-ripple .5s ease-out forwards}
    @keyframes tw-ripple{from{transform:scale(1);opacity:.9}to{transform:scale(2.3);opacity:0}}`
  const setup = () => {
    const style = document.createElement('style'); style.textContent = css; document.head.appendChild(style)
    const dot = document.createElement('div'); dot.id = 'tw-touch'; document.body.appendChild(dot)
    const at = (t, down) => { dot.style.transform = `translate(${t.clientX}px,${t.clientY}px) scale(${down ? 1 : 1.25})` }
    const opt = { capture: true, passive: true }
    window.addEventListener('touchstart', (e) => {
      const t = e.touches[0]; at(t, true); dot.classList.add('on')
      const r = document.createElement('div'); r.className = 'tw-ripple'; r.style.left = `${t.clientX}px`; r.style.top = `${t.clientY}px`
      document.body.appendChild(r); setTimeout(() => r.remove(), 600)
    }, opt)
    window.addEventListener('touchmove', (e) => at(e.touches[0], true), opt)
    const up = () => dot.classList.remove('on')
    window.addEventListener('touchend', up, opt); window.addEventListener('touchcancel', up, opt)
  }
  if (document.body) setup(); else document.addEventListener('DOMContentLoaded', setup)
}, API)

await page.goto(APP, { waitUntil: 'networkidle2', timeout: 180000 })
await page.waitForFunction(() => document.querySelector('[aria-label^="Zone Zuschauerraum"]'), { timeout: 60000 })
await sleep(1500)

// ---------- recorder: CDP screencast (lossless PNG frames with timestamps), resampled to 30 fps afterwards ----------
const cdp = await page.createCDPSession()
const frames = [] // { t, file }
let writes = Promise.resolve()
cdp.on('Page.screencastFrame', ({ data, metadata, sessionId }) => {
  cdp.send('Page.screencastFrameAck', { sessionId }).catch(() => {})
  const file = path.join(TMP, `raw_${String(frames.length).padStart(6, '0')}.png`)
  frames.push({ t: metadata.timestamp, file })
  writes = writes.then(() => fs.promises.writeFile(file, Buffer.from(data, 'base64')))
})
await cdp.send('Page.startScreencast', { format: 'png', everyNthFrame: 1 })
await sleep(600)

const clips = {} // id -> { start, end, marks }
let cur = null
const begin = (id) => { cur = clips[id] = { start: now(), marks: {} }; return cur }
const end = () => { cur.end = now() }
const mark = (name, clip = cur) => { clip.marks[name] = +(now() - clip.start).toFixed(2) }
const stills = {} // name -> time
const still = (name) => { stills[name] = now() }

// ---------- finger ----------
const rect = (sel) => page.evaluate((s) => {
  const el = typeof s === 'string' ? document.querySelector(s) : null
  if (!el) return null
  const r = el.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }
}, sel)
const rectByText = (role, text) => page.evaluate((role, text) => {
  const el = [...document.querySelectorAll(`[role=${role}], button`)].find((e) => (e.getAttribute('aria-label') || e.textContent || '').includes(text))
  if (!el) return null
  const r = el.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }
}, role, text)
async function tap(r, { fx = 0.5, fy = 0.5, hold = 90 } = {}) {
  if (!r) throw new Error('tap target not found')
  const x = r.x + r.w * fx + (rnd() - 0.5) * 6, y = r.y + r.h * fy + (rnd() - 0.5) * 4
  await page.touchscreen.touchStart(x, y)
  await sleep(hold + rnd() * 40)
  await page.touchscreen.touchEnd()
}
/** Drag the content up by `dy` CSS px (finger moves up), slowing down at the end so there is no fling. */
async function swipeUp(dy, { x = 205, y0 = 610, ms = 650 } = {}) {
  await page.touchscreen.touchStart(x, y0)
  await sleep(50)
  const t0 = Date.now()
  for (let p = 0; p < 1;) { // by the clock: a touchMove round trip takes longer than a frame
    p = Math.min(1, (Date.now() - t0) / ms)
    const e = 1 - Math.pow(1 - p, 3) // ease-out
    await page.touchscreen.touchMove(x + Math.sin(p * 3) * 3, y0 - dy * e)
    await sleep(8)
  }
  await sleep(140)
  await page.touchscreen.touchEnd()
}
async function typeHuman(text) {
  for (const ch of text) {
    await page.keyboard.type(ch)
    await sleep(ch === '.' ? 170 + rnd() * 80 : ch === ' ' ? 45 + rnd() * 35 : 26 + rnd() * 34)
  }
}
const scrollInfo = () => page.evaluate(() => {
  const s = [...document.querySelectorAll('div')].find((e) => e.scrollHeight > e.clientHeight + 4 && /auto|scroll/.test(getComputedStyle(e).overflowY))
  return s ? { top: s.scrollTop, max: s.scrollHeight - s.clientHeight } : { top: 0, max: 0 }
})

// ---------- D1 phone-capture: zone, typed note, Senden, pipeline status ----------
begin('phone-capture')
await sleep(900)
mark('tap_zone'); await tap(await rect('[aria-label^="Zone Zuschauerraum"]'))
await sleep(750)
mark('tap_note'); await tap(await rect('textarea'), { fx: 0.3, fy: 0.4 })
await sleep(450)
mark('type_start'); await typeHuman(NOTE); mark('type_end')
await sleep(650)
still('phone-capture')
await sleep(150)
mark('tap_senden'); await tap(await rectByText('button', 'Senden an Zuschauerraum'), { fx: 0.55 })
await page.waitForFunction(() => document.body.innerText.includes('Verarbeitet'), { timeout: 60000 })
mark('processed')
await sleep(1100)
end()

// ---------- D2 phone-result: bring the result card into view, hold ----------
const capClip = clips['phone-capture']
begin('phone-result')
await sleep(350)
const card = await page.evaluate(() => {
  const badge = [...document.querySelectorAll('*')].filter((e) => e.children.length === 0 && e.textContent.trim() === 'Verarbeitet').pop()
  let el = badge; while (el && !/rounded-xl/.test(el.className?.toString?.() ?? '')) el = el.parentElement
  const r = (el ?? badge).getBoundingClientRect(); return { top: r.top, bottom: r.bottom }
})
const tabBarTop = (await rectByText('tab', 'Heute')).y
const need = Math.max(0, card.top - 150) // card starts a little under the header
mark('swipe'); await swipeUp(need + 16) // + touch slop
await sleep(500)
mark('result_visible')
const info = await scrollInfo()
console.log('result card', card, 'tab bar', tabBarTop, 'scrolled', info)
await sleep(3000) // the "Wird gesendet" toast is gone ~3.1 s after Senden
still('phone-result')
await sleep(2600)
end()

// ---------- D7 phone-confirm: Heute, camera proposal, Bestätigen, the bar moves ----------
begin('phone-confirm')
await sleep(700)
mark('tap_heute'); await tap(await rectByText('tab', 'Heute'))
await page.waitForFunction(() => document.body.innerText.includes('Vorschläge der Kamera'), { timeout: 20000 })
mark('proposal_visible')
await sleep(1500)
still('phone-confirm')
await sleep(1300)
const barBefore = await page.evaluate(() => document.querySelector('.bg-info.absolute')?.style.width)
mark('tap_bestaetigen'); await tap(await rectByText('button', 'Bestätigen'))
await page.waitForFunction((w) => { const b = document.querySelector('.bg-info.absolute'); return b && b.style.width !== w }, { timeout: 20000 }, barBefore)
mark('bar_moved')
const barAfter = await page.evaluate(() => document.querySelector('.bg-info.absolute')?.style.width)
console.log('Bestuhlung neu bar', barBefore, '->', barAfter)
await sleep(4200)
end()

// ---------- optional: Bericht tab ----------
begin('phone-report')
await sleep(600)
mark('tap_bericht'); await tap(await rectByText('tab', 'Bericht'))
await page.waitForFunction(() => document.body.innerText.includes('Bautagebuch'), { timeout: 20000 })
mark('report_visible')
await sleep(2600)
mark('scroll_1'); await swipeUp(330, { ms: 900 })
await sleep(2200)
mark('scroll_2'); await swipeUp(330, { ms: 900 })
await sleep(2400)
end()

await sleep(300)
await cdp.send('Page.stopScreencast')
await writes
await browser.close()

// ---------- what the server holds now (printed for the report; the recording shows the same) ----------
const after = await getJson('/api/overview')
const el = (id) => after.zones.flatMap((z) => z.elements).find((e) => e.id === id)
console.log(JSON.stringify({
  kpi_before: before.kpi.delay_d, kpi_after: after.kpi.delay_d, forecast_finish: after.kpi.forecast_finish,
  rowA: [rowA0.pct, el('E-ROW-A').pct], rowF: el('E-ROW-F'), proposals_left: after.proposals.length,
  A1080: after.activities.filter((a) => a.id === 'A1080').map((a) => ({ pct: a.pct, forecast_finish: a.forecast_finish, delay_d: a.delay_d, cause: a.cause }))[0],
}))

// ---------- resample to constant 30 fps and encode ----------
const gaps = frames.slice(1).map((f, i) => f.t - frames[i].t)
console.log(`screencast: ${frames.length} frames in ${(frames.at(-1).t - frames[0].t).toFixed(1)} s, clock offset ${(now() - frames.at(-1).t).toFixed(2)} s`)
const frameAt = (t) => { // latest frame shown at time t
  let lo = 0, hi = frames.length - 1
  while (lo < hi) { const m = (lo + hi + 1) >> 1; if (frames[m].t <= t) lo = m; else hi = m - 1 }
  return frames[lo]
}
const ffmpeg = (args) => {
  try { execFileSync(path.join(TOOLS, 'node_modules/.bin/remotion'), ['ffmpeg', ...args], { cwd: TOOLS, stdio: ['ignore', 'ignore', 'pipe'] }) }
  catch (e) { throw new Error(`ffmpeg failed (frames kept in ${TMP}):\n${String(e.stderr).split('\n').slice(-8).join('\n')}`) }
}
for (const [id, c] of Object.entries(clips)) {
  const dir = path.join(TMP, id); fs.mkdirSync(dir)
  const n = Math.round((c.end - c.start) * FPS)
  for (let k = 0; k < n; k++) fs.linkSync(frameAt(c.start + k / FPS).file, path.join(dir, `f_${String(k).padStart(5, '0')}.png`))
  const mp4 = path.join(OUT, `${id}.mp4`)
  ffmpeg(['-y', '-framerate', String(FPS), '-i', path.join(dir, 'f_%05d.png'), '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '14',
    '-pix_fmt', 'yuv420p', '-r', String(FPS), '-movflags', '+faststart', mp4])
  const unique = new Set(Array.from({ length: n }, (_, k) => frameAt(c.start + k / FPS).file)).size
  fs.writeFileSync(path.join(OUT, `${id}.json`), JSON.stringify({ seconds: +(n / FPS).toFixed(2), fps: FPS, width: W * DSF, height: H * DSF, marks: c.marks }, null, 1) + '\n')
  console.log(`${id}.mp4  ${(n / FPS).toFixed(2)} s  ${n} frames (${unique} distinct)  ${(fs.statSync(mp4).size / 1024).toFixed(0)} kB  marks ${JSON.stringify(c.marks)}`)
}
for (const [name, t] of Object.entries(stills)) fs.copyFileSync(frameAt(t).file, path.join(STILLS, `${name}.png`))
console.log('stills:', Object.keys(stills).join(', '), '->', path.relative(REPO, STILLS))
if (!process.env.TW_KEEP_TMP) fs.rmSync(TMP, { recursive: true, force: true }); else console.log('frames kept in', TMP)
