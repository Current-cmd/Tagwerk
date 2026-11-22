// Screen recordings of the web dashboard for the 2-minute video (storyboard shots D3, D4, D5, D6, D8, D9).
//   node pitch/rec/record-dashboard.mjs                 all six, in order
//   node pitch/rec/record-dashboard.mjs trace graph     only these (Hörsaal must already be in the flipped state)
// Needs Hörsaal on :8080 (seeded state for `flip`) and Schependomlaan on :8081; see README-dashboard.md.
import { launch, sleep, Recorder, moveTo, moveToEl, pointOf, click, showCursor } from './lib.mjs'

const HS = process.env.HS || 'http://localhost:8080'
const SP = process.env.SP || 'http://localhost:8081'
const DSF = Number(process.env.DSF || 1.35) // 1422x800 CSS px -> 1920x1080
const NOTE = 'Stuhlreihe A ist montiert. Zwei Mann vom Trockenbau sind krank. Kratzer an der Bühne.'
const CAPTURE_ID = 'walk-2611'

const overview = async () => (await fetch(`${HS}/api/overview`)).json()
const text = (page, sel) => page.evaluate(s => document.querySelector(s)?.innerText ?? '', sel)
async function waitText(page, sel, re, ms = 8000) {
  const t0 = Date.now()
  while (Date.now() - t0 < ms) { if (re.test(await text(page, sel))) return true; await sleep(40) }
  return false
}
// element whose own text matches, inside a container
const byText = ([root, needle, tag]) => [...document.querySelector(root).querySelectorAll(tag || '*')]
  .filter(e => e.innerText && e.innerText.trim().startsWith(needle)).pop()

async function open(page, url, settle = 1500) {
  await page.goto('about:blank')
  await page.goto(url, { waitUntil: 'networkidle0' })
  await sleep(settle)
  await showCursor(page)
}

const shots = {
  // D3: dashboard green, the capture arrives over the websocket, cursor walks KPI -> Gantt -> events -> recording
  async flip(page) {
    const before = (await overview()).kpi
    if (before.delay_d !== 0 || before.forecast_finish !== '2026-12-01') throw new Error('Hörsaal is not in the seeded on-plan state: pitch/rec/servers.sh reset')
    await open(page, `${HS}/app#/dashboard`)
    await moveTo(page, 420, 640, 300)
    const rec = new Recorder(page, 'dash-flip'); await rec.start()
    await sleep(900)
    await moveTo(page, 300, 500, 1400) // towards the empty "Aufnahmen des Tages"
    await sleep(500)
    const form = new FormData()
    form.set('capture_id', CAPTURE_ID); form.set('zone_id', 'Z-AUDIENCE'); form.set('note', NOTE)
    if (process.env.CAPTURE_TS) form.set('ts', process.env.CAPTURE_TS)
    rec.mark('capture_posted')
    const post = fetch(`${HS}/captures`, { method: 'POST', body: form }).then(r => r.json())
    const live = await waitText(page, '[data-testid=kpi-strip]', /03\.12\./)
    if (!live) { await rec.stop(); throw new Error('the page did not update over the websocket within 8 s') }
    rec.mark('kpi_red')
    const res = await post
    console.log('  capture result:', JSON.stringify({ changes: res.changes, absences: res.absences, events: res.events }))
    await sleep(1300) // let the viewer see the whole page change
    await moveToEl(page, byText, { arg: ['[data-testid=kpi-strip]', '03.12.', 'div'], rx: 0.3, ry: 0.6, ms: 1100 }); rec.mark('cursor_kpi')
    await sleep(1500)
    await moveToEl(page, '[data-testid=gantt-row-A1080]', { rx: 0.6 }); rec.mark('cursor_gantt_bestuhlung')
    await sleep(700)
    const bar = await pointOf(page, '[data-testid=gantt] svg')
    await moveTo(page, bar.box.x + bar.box.w * 0.72, page.tw.y + 4, 900) // along the red bar
    await sleep(700)
    const abn = await pointOf(page, '[data-testid=gantt-row-A1090]')
    await moveTo(page, bar.box.x + bar.box.w * 0.93, abn.y + 4, 600); rec.mark('cursor_gantt_abnahme')
    await sleep(1100)
    await moveToEl(page, byText, { arg: ['[data-testid=tile-events]', '2× Trockenbau krank', 'li'], rx: 0.45, ry: 0.4 }); rec.mark('cursor_event_absence')
    await sleep(1200)
    await moveToEl(page, byText, { arg: ['[data-testid=tile-events]', 'Kratzer an der Bühne', 'li'], rx: 0.4, ry: 0.45, ms: 600 }); rec.mark('cursor_event_defect')
    await sleep(900)
    await moveToEl(page, `#rec-${CAPTURE_ID}`, { rx: 0.45, ry: 0.55 }); rec.mark('cursor_recording')
    await sleep(1800)
    return rec.stop()
  },

  // D4: click "Bestuhlung neu" -> sheet: Verzug, Ursache, GAEB position, recordings -> open the newest recording
  async trace(page) {
    await open(page, `${HS}/app#/dashboard`)
    await moveTo(page, 620, 300, 300)
    const rec = new Recorder(page, 'dash-trace'); await rec.start()
    await sleep(900)
    await moveToEl(page, '[data-testid=gantt-row-A1080]', { rx: 0.55 })
    await sleep(450)
    rec.mark('click_activity'); await click(page)
    await page.waitForSelector('[data-testid=activity-sheet]')
    await sleep(450); rec.mark('sheet_open')
    const row = k => [...document.querySelectorAll('[data-testid=activity-sheet] div')].filter(e => e.children.length === 2 && e.children[0].innerText === k).pop()
    await moveToEl(page, row, { arg: 'Verzug', rx: 0.8, ms: 1100 }); rec.mark('cursor_delay')
    await sleep(900)
    await moveToEl(page, row, { arg: 'Ursache', rx: 0.72, ry: 0.6, ms: 500 }); rec.mark('cursor_cause')
    await sleep(1700)
    await moveToEl(page, '[data-testid=activity-sheet] ul li span.font-mono', { rx: 0.6, ry: 0.7 }); rec.mark('cursor_gaeb')
    await sleep(600)
    await moveTo(page, page.tw.x + 190, page.tw.y + 2, 900)
    await sleep(900)
    const newest = await text(page, '[data-testid=sheet-recordings] li button')
    if (!newest.includes(CAPTURE_ID)) throw new Error(`newest recording of A1080 is not ${CAPTURE_ID}: ${newest}`)
    await moveToEl(page, '[data-testid=sheet-recordings] li button', { rx: 0.3 }); rec.mark('cursor_recording')
    await sleep(800)
    rec.mark('click_recording'); await click(page)
    await page.waitForFunction(id => location.hash.includes(`rec=${id}`), {}, CAPTURE_ID)
    await sleep(700); rec.mark('recording_open')
    await moveToEl(page, `#rec-${CAPTURE_ID}`, { rx: 0.5, ry: 0.5, ms: 1200 })
    await sleep(1200)
    await moveTo(page, page.tw.x - 40, page.tw.y + 60, 700)
    await sleep(1600)
    return rec.stop()
  },

  // D5: Live-Graph: recording node -> its events -> the red activity -> its GAEB position; a click on the activity opens the sheet
  async graph(page) {
    await open(page, `${HS}/app#/graph`, 2500)
    await page.click('[data-testid=panel-toggle]') // hide the replay panel (a control of the page) so the graph gets the full width
    await sleep(1500)
    // positions of the vis-network nodes (read-only, through the component's network instance)
    const nodes = await page.evaluate(() => {
      const el = document.querySelector('[data-testid=task-graph]')
      const fiber = el[Object.keys(el).find(k => k.startsWith('__reactFiber'))].return
      let net = null
      for (let h = fiber.memoizedState; h; h = h.next) { const c = h.memoizedState?.current; if (c && typeof c.getPositions === 'function') net = c }
      const r = el.getBoundingClientRect()
      return Object.fromEntries(Object.entries(net.getPositions()).map(([id, p]) => { const d = net.canvasToDOM(p); return [id, { x: d.x + r.x, y: d.y + r.y }] }))
    })
    const at = id => { if (!nodes[id]) throw new Error(`graph node ${id} missing`); return nodes[id] }
    await moveTo(page, 1010, 300, 300)
    const rec = new Recorder(page, 'dash-graph'); await rec.start()
    await sleep(1300)
    let p = at(CAPTURE_ID)
    await moveTo(page, p.x + 8, p.y + 3, 1300); rec.mark('hover_recording')
    await sleep(1000)
    rec.mark('click_recording'); await click(page)
    await sleep(1600)
    p = at(`${CAPTURE_ID}:absence:0`)
    await moveTo(page, p.x - 20, p.y + 2, 1000); rec.mark('hover_event_absence')
    await sleep(1300)
    p = at(`${CAPTURE_ID}:event:0`)
    await moveTo(page, p.x - 20, p.y + 2, 550); rec.mark('hover_event_defect')
    await sleep(900)
    p = at('A1080')
    await moveTo(page, p.x + 22, p.y + 2, 1500); rec.mark('hover_activity')
    await sleep(1500)
    p = at('oz:01.06.0010')
    await moveTo(page, p.x + 30, p.y + 2, 1000); rec.mark('hover_gaeb')
    await sleep(1500)
    p = at('A1080')
    await moveTo(page, p.x + 22, p.y + 2, 900)
    await sleep(500)
    rec.mark('click_activity'); await click(page)
    await page.waitForSelector('[data-testid=activity-sheet]')
    await sleep(450); rec.mark('sheet_open')
    await sleep(1900)
    return rec.stop()
  },

  // D6: day slider: three days back (history), drag past Heute into the forecast days, one more day, back to Heute
  async forecast(page) {
    await open(page, `${HS}/app#/dashboard`)
    const days = await (await fetch(`${HS}/api/v2/days`)).json()
    const idx = d => days.days.findIndex(x => x.date === d)
    const date = () => text(page, '[data-testid=current-date]')
    await moveTo(page, 250, 330, 300)
    const rec = new Recorder(page, 'dash-forecast'); await rec.start()
    await sleep(900)
    await moveToEl(page, '[aria-label="Vorheriger Tag"]')
    await sleep(350)
    for (let i = 1; i <= 3; i++) { await click(page); rec.mark(`back_${i}`); await sleep(i < 3 ? 850 : 1300) }
    console.log('  history day:', await date())
    // drag the thumb to Tue 01.12. (a forecast day)
    const track = await pointOf(page, '[data-slot=slider]')
    const thumb = await pointOf(page, '[role=slider]')
    const target = idx('2026-12-01')
    const xOf = i => track.box.x + 8 + (i / (days.days.length - 1)) * (track.box.w - 16) // Radix keeps the thumb inside the track
    await moveTo(page, thumb.x, thumb.y, 800)
    await sleep(300)
    await page.mouse.down(); rec.mark('drag_start')
    let crossed = false
    const t0 = performance.now(), dur = 2600, x0 = thumb.x, x1 = xOf(target)
    for (;;) {
      const t = Math.min(1, (performance.now() - t0) / dur), k = t < 0.5 ? 2 * t * t : 1 - 2 * (1 - t) * (1 - t)
      const x = x0 + (x1 - x0) * k
      await page.mouse.move(x, thumb.y); page.tw.x = x
      if (!crossed && x >= xOf(idx(days.today)) + 4) { crossed = true; rec.mark('past_today') }
      if (t >= 1) break
      await sleep(8)
    }
    await sleep(250)
    await page.mouse.up(); rec.mark('at_forecast')
    console.log('  forecast day:', await date())
    await sleep(1500)
    await moveToEl(page, '[aria-label="Nächster Tag"]')
    await sleep(300)
    await click(page); rec.mark('forward_1')
    await sleep(1300)
    console.log('  forecast day:', await date())
    await moveToEl(page, c => [...document.querySelectorAll('[data-testid=day-slider] button')].pop())
    await sleep(350)
    await click(page); rec.mark('click_heute')
    await sleep(600)
    console.log('  back on:', await date())
    await moveTo(page, page.tw.x - 330, page.tw.y + 110, 900)
    await sleep(1500)
    return rec.stop()
  },

  // D8: Tagesbericht 26.11.: Arbeitskräfte, Ausgeführte Arbeiten, Vorkommnisse, Behinderungen / Verzug; back up to "Druckversion (HTML)"
  async report(page) {
    await open(page, `${HS}/app#/dashboard`)
    await moveTo(page, 900, 330, 300)
    const rec = new Recorder(page, 'dash-report'); await rec.start()
    await sleep(800)
    await moveToEl(page, '[data-testid=report-button]')
    await sleep(350)
    rec.mark('click_report'); await click(page)
    await page.waitForFunction(() => [...document.querySelectorAll('[data-slot=card-title]')].some(e => e.innerText.startsWith('1. Arbeitskr')))
    await sleep(400); rec.mark('report_open')
    const title = t => [...document.querySelectorAll('main [data-slot=card-title]')].find(e => e.innerText.startsWith(t)).closest('[data-slot=card]')
    await sleep(900)
    await moveToEl(page, title, { arg: '1. Arbeitskr', rx: 0.5, ry: 0.78, ms: 1100 }); rec.mark('cursor_labour')
    await sleep(1300)
    const scroll = async (dy, ms) => { // wheel in small steps, eased
      const t0 = performance.now(); let done = 0
      for (;;) {
        const t = Math.min(1, (performance.now() - t0) / ms), k = t < 0.5 ? 2 * t * t : 1 - 2 * (1 - t) * (1 - t)
        const want = Math.round(dy * k)
        if (want !== done) { await page.mouse.wheel({ deltaY: want - done }); done = want }
        if (t >= 1) break
        await sleep(12)
      }
    }
    await scroll(190, 1800); rec.mark('scrolled_work_done')
    await moveToEl(page, title, { arg: '3. Ausgef', rx: 0.3, ry: 0.8, ms: 700 }); rec.mark('cursor_work_done')
    await sleep(1400)
    await scroll(400, 1800); rec.mark('scrolled_bottom')
    await moveToEl(page, title, { arg: '4. Besondere', rx: 0.3, ry: 0.55, ms: 800 }); rec.mark('cursor_incidents')
    await sleep(1200)
    await moveToEl(page, title, { arg: '5. Behinderungen', rx: 0.3, ry: 0.5, ms: 800 }); rec.mark('cursor_delays')
    await sleep(1800)
    await scroll(-600, 1300); rec.mark('scrolled_top')
    await moveToEl(page, () => [...document.querySelectorAll('main a')].find(a => a.innerText.includes('Druckversion')), { rx: 0.55, ms: 1000 }); rec.mark('cursor_print')
    await sleep(2000)
    return rec.stop()
  },

  // D9: Schependomlaan, BIM-Modell: "Bauablauf abspielen" from the first day of the schedule up to its data date
  async bim(page) {
    const days = await (await fetch(`${SP}/api/v2/days`)).json()
    const until = process.env.BIM_UNTIL || days.today
    await open(page, `${SP}/app#/bim?d=${days.first}`, 500)
    await page.waitForSelector('[data-testid=bim-play]', { timeout: 120000 })
    await page.waitForSelector('main canvas', { timeout: 120000 })
    await sleep(5000)
    await moveTo(page, 760, 420, 300)
    const rec = new Recorder(page, 'dash-bim'); await rec.start()
    await sleep(1000)
    await moveToEl(page, '[data-testid=bim-play]', { rx: 0.45 })
    await sleep(450)
    rec.mark('play_pressed'); await click(page)
    await sleep(500)
    await moveTo(page, 1105, 505, 1100) // out of the way, next to the model
    let month = '', cur = days.first
    const t0 = Date.now()
    while (cur < until && Date.now() - t0 < 400000) {
      cur = await page.evaluate(() => new URLSearchParams(location.hash.split('?')[1]).get('d'))
      if (cur.slice(0, 7) !== month) { month = cur.slice(0, 7); if (cur !== days.first) rec.mark(`date_${cur}`) }
      await sleep(60)
    }
    rec.mark(`date_${cur}`)
    await moveToEl(page, '[data-testid=bim-play]', { rx: 0.45, ms: 700 })
    await click(page); rec.mark('paused')
    await sleep(2000)
    return rec.stop()
  },
}

const order = ['flip', 'trace', 'graph', 'forecast', 'report', 'bim']
const want = process.argv.slice(2).length ? process.argv.slice(2) : order
for (const w of want) if (!shots[w]) { console.error(`unknown shot ${w}; one of ${order.join(' ')}`); process.exit(2) }
const { browser, page } = await launch({ dsf: DSF })
try {
  for (const name of order.filter(o => want.includes(o))) {
    console.log(`== ${name}`)
    await shots[name](page)
  }
} finally {
  await browser.close()
}
