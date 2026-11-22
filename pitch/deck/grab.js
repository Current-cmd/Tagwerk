const puppeteer = require("puppeteer-core");
const OUT = require("path").resolve(__dirname, "../../docs/design-brief/app-grabs") + "/";
const shots = [
  ["dashboard", "http://localhost:8080/app#/dashboard", 0],
  ["dashboard-lower", "http://localhost:8080/app#/dashboard", 900],
  ["graph", "http://localhost:8080/app#/graph", 0],
  ["bim-hoersaal", "http://localhost:8080/app#/bim", 0],
  ["report", "http://localhost:8080/app#/report/2026-11-26", 0],
  ["report-delays", "http://localhost:8080/app#/report/2026-11-26", "Behinderungen"],
  ["bim-schependomlaan", "http://localhost:8081/app#/bim", 0],
  ["scan-hackathon", "http://localhost:8082/app#/scan/site-hackathon", 0],
];
(async () => {
  const b = await puppeteer.launch({ executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: "new", args: ["--use-angle=metal", "--enable-webgl", "--ignore-gpu-blocklist"] });
  const p = await b.newPage();
  await p.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 2 });
  for (const [name, url, scroll] of shots) {
    await p.goto("about:blank");
    await p.goto(url, { waitUntil: "networkidle2", timeout: 60000 });
    await new Promise(r => setTimeout(r, name.startsWith("bim") || name.startsWith("scan") ? 9000 : 3500));
    if (typeof scroll === "number" && scroll) await p.evaluate(y => { const el = document.scrollingElement; el.scrollTo(0, y); document.querySelectorAll("main, [data-scroll], .overflow-auto, .overflow-y-auto").forEach(e => e.scrollTo && e.scrollTo(0, y)); }, scroll);
    if (typeof scroll === "string") await p.evaluate(t => { const el = [...document.querySelectorAll("h1,h2,h3,h4,div,section")].find(e => e.textContent.trim().startsWith("5.") && e.textContent.includes(t) && e.children.length < 3); if (el) el.scrollIntoView({ block: "start" }); }, scroll);
    await new Promise(r => setTimeout(r, 800));
    const badge = await p.evaluate(() => document.body.innerText.includes("Demo-Daten"));
    await p.screenshot({ path: OUT + name + ".png" });
    console.log(name, badge ? "WARNING Demo-Daten badge" : "live");
  }
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
