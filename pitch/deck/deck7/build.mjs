// Builds the 7-slide submission deck: deck.html -> docs/design-brief/Tagwerk-Pitch-7.pdf
//   node pitch/deck/deck7/build.mjs [--allow-missing] [--png <dir>]
// --allow-missing: images that do not exist yet (the phone stills) become labelled empty frames instead of
//                  failing the build; the missing files are printed.
// --png <dir>:     also writes one PNG per slide for review.
// Needs puppeteer-core (taken from ../../video, ../ or the demo-video checkout) and Google Chrome.
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import { fileURLToPath, pathToFileURL } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const REPO = path.resolve(HERE, '../../..')
const OUT = path.join(REPO, 'docs/design-brief/Tagwerk-Pitch-7.pdf')
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const args = process.argv.slice(2)
const allowMissing = args.includes('--allow-missing')
const pngDir = args.includes('--png') ? path.resolve(args[args.indexOf('--png') + 1]) : null

function loadPuppeteer() {
  const roots = [HERE, path.join(REPO, 'pitch/deck'), path.join(REPO, 'pitch/video'),
    path.resolve(REPO, '../demo-video'), process.env.PUPPETEER_ROOT].filter(Boolean)
  for (const r of roots) {
    try { return createRequire(path.join(r, 'x.js'))('puppeteer-core') } catch { /* next */ }
  }
  throw new Error('puppeteer-core not found; set PUPPETEER_ROOT to a folder whose node_modules has it')
}

let html = fs.readFileSync(path.join(HERE, 'deck.html'), 'utf8')
const missing = []
html = html.replace(/<img src="([^"]+)"[^>]*>/g, (tag, src) => {
  if (fs.existsSync(path.join(HERE, src))) return tag
  missing.push(src)
  return `<div class="missing">${src}<br>not delivered yet</div>`
})
if (missing.length) {
  console.log('MISSING images:', missing.join(', '))
  if (!allowMissing) { console.error('Build stopped. Use --allow-missing to build with empty frames.'); process.exit(1) }
}
const slides = (html.match(/<section class="slide/g) || []).length
if (slides > 7) { console.error(`${slides} slides: the submission allows at most 7`); process.exit(1) }

const tmp = path.join(HERE, '.deck.build.html')
fs.writeFileSync(tmp, html)
const puppeteer = loadPuppeteer()
const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--hide-scrollbars'] })
try {
  const page = await browser.newPage()
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 })
  await page.goto(pathToFileURL(tmp).href, { waitUntil: 'networkidle0' })
  await page.evaluate(() => document.fonts.ready)
  // Report content that spills out of a slide or a box.
  const overflow = await page.evaluate(() => {
    const out = []
    document.querySelectorAll('.slide').forEach((s, i) => {
      const foot = s.querySelector('.foot').getBoundingClientRect()
      const sr = s.getBoundingClientRect()
      s.querySelectorAll('*').forEach((el) => {
        if (el.closest('.foot') || el.closest('svg')) return
        const r = el.getBoundingClientRect()
        if (!r.width || !r.height) return
        if (r.bottom > foot.top - 4 || r.right > sr.right - 90 || r.left < sr.left + 90) {
          out.push(`slide ${i + 1}: <${el.tagName.toLowerCase()} class="${el.className}"> ` +
            `bottom ${Math.round(r.bottom - sr.top)} right ${Math.round(r.right)} "${el.textContent.trim().slice(0, 40)}"`)
        }
      })
    })
    return out
  })
  if (overflow.length) console.log('OVERFLOW:\n  ' + overflow.join('\n  '))
  await page.pdf({ path: OUT, width: '1920px', height: '1080px', printBackground: true, preferCSSPageSize: true })
  console.log(`wrote ${path.relative(REPO, OUT)} (${slides} slides, ${(fs.statSync(OUT).size / 1e6).toFixed(1)} MB)`)
  if (pngDir) {
    fs.mkdirSync(pngDir, { recursive: true })
    const els = await page.$$('.slide')
    for (let i = 0; i < els.length; i++) await els[i].screenshot({ path: path.join(pngDir, `slide-${i + 1}.png`) })
    console.log(`wrote ${els.length} PNGs to ${pngDir}`)
  }
} finally {
  await browser.close()
  fs.rmSync(tmp, { force: true })
}
