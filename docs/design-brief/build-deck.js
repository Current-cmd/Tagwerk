// Tagwerk pitch deck v2: opens on the real site video, then breaks it down. Run: NODE_PATH=./node_modules node build2.js
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const L = require("react-icons/lu");
const { applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js");

const FR = "/Users/anoushk/Developer/hacka/tagwerk/docs/design-brief/site-frames/";
const OUT = "/Users/anoushk/Developer/hacka/tagwerk/docs/design-brief/Tagwerk-Pitch.pptx";

const THEME = {
  name: "Tagwerk", headFontFace: "Arial", bodyFontFace: "Arial",
  colors: { dk1: "0A0A0A", lt1: "FFFFFF", dk2: "141416", lt2: "F5F5F5", accent1: "2563EB", accent2: "16A34A",
    accent3: "F59E0B", accent4: "DC2626", accent5: "8B5CF6", accent6: "737373", hlink: "2563EB", folHlink: "1D4ED8" },
};
const H = {
  ink: "0A0A0A", dark: "141416", dark2: "1F1F23", darkLine: "2E2E33", muted: "737373", border: "E5E5E5", surface: "F5F5F5",
  blue: "2563EB", blueL: "60A5FA", blueTint: "DBEAFE", green: "16A34A", greenTint: "DCFCE7", amber: "F59E0B", amberDk: "92400E",
  amberTint: "FEF3C7", red: "DC2626", redTint: "FEE2E2", violet: "8B5CF6", violetDk: "6D28D9", violetTint: "F5F3FF",
  grey4: "A3A3A3", grey3: "D4D4D4", white: "FFFFFF",
};

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size), strokeWidth: 2 }));
  return "image/png;base64," + (await sharp(Buffer.from(svg)).png().toBuffer()).toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = "Tagwerk – Challenge B pitch";
  pres.author = "Team Tagwerk";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const W = 13.333, M = 0.75;

  // ---------- layouts ----------
  pres.defineSlideMaster({ title: "DARK", background: { color: H.dark }, objects: [] });
  const footer = [{ text: { text: "Tagwerk", options: { x: M, y: 7.0, w: 3, h: 0.3, fontSize: 10, color: H.muted, margin: 0 } } }];
  const sn = { x: W - M - 0.5, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: H.muted, align: "right" };
  pres.defineSlideMaster({
    title: "CONTENT_TITLED", background: { color: H.white }, slideNumber: sn,
    objects: [...footer,
      { placeholder: { options: { name: "kicker", type: "body", x: M, y: 0.5, w: 11.5, h: 0.3, fontSize: 12, bold: true, color: H.blue,
        charSpacing: 2, margin: 0 }, text: "" } },
      { placeholder: { options: { name: "title", type: "title", x: M, y: 0.82, w: 11.8, h: 0.8, fontSize: 36, bold: true, color: H.ink,
        margin: 0, valign: "top", align: "left" }, text: "" } }],
  });
  pres.defineSlideMaster({
    title: "DARK_TITLED", background: { color: H.dark }, slideNumber: { ...sn, color: "71717A" },
    objects: [
      { placeholder: { options: { name: "kicker", type: "body", x: M, y: 0.5, w: 11.5, h: 0.3, fontSize: 12, bold: true, color: H.blueL,
        charSpacing: 2, margin: 0 }, text: "" } },
      { placeholder: { options: { name: "title", type: "title", x: M, y: 0.82, w: 11.8, h: 0.8, fontSize: 32, bold: true, color: H.white,
        margin: 0, valign: "top", align: "left" }, text: "" } }],
  });

  const titled = (master, section, kicker, title) => {
    const s = pres.addSlide({ masterName: master, sectionTitle: section });
    s.addText(kicker.toUpperCase(), { placeholder: "kicker" });
    s.addText(title, { placeholder: "title" });
    return s;
  };
  const content = (sec, k, t) => titled("CONTENT_TITLED", sec, k, t);
  const dark = (sec, k, t) => titled("DARK_TITLED", sec, k, t);
  const card = (s, x, y, w, h, o = {}) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.1,
    fill: { color: o.fill || H.white }, line: { color: o.line || H.border, width: o.lw || 1, dashType: o.dash } });
  const txt = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, color: H.ink, fontSize: 14, ...o });
  const iconCircle = async (s, Comp, x, y, d, bg, fg) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: bg }, line: { type: "none" } });
    s.addImage({ data: await icon(Comp, fg), x: x + d * 0.25, y: y + d * 0.25, w: d * 0.5, h: d * 0.5 });
  };
  const logo = (s, x, y, d, inv) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: d, h: d, rectRadius: d * 0.22, fill: { color: inv ? H.white : "171717" }, line: { type: "none" } });
    s.addText("T", { isTextBox: true, x, y, w: d, h: d, align: "center", valign: "middle", margin: 0, fontSize: d * 40, bold: true, color: inv ? "171717" : H.white });
  };
  const arrow = (s, x1, y1, x2, y2, color = H.grey4) => s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2),
    w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001, flipV: y2 < y1, line: { color, width: 1.5, endArrowType: "triangle" } });
  const line = (s, x1, y1, x2, y2, color = H.grey4, dash, width = 1.25) => s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2),
    y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001, h: Math.abs(y2 - y1) || 0.001, flipV: (y2 < y1) !== (x2 < x1),
    line: { color, width, dashType: dash } });
  const chip = (s, text, x, y, w, fg, bg, o = {}) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: o.h || 0.36, rectRadius: (o.h || 0.36) / 2, fill: { color: bg },
      line: o.line ? { color: o.line, dashType: o.dash } : { type: "none" } });
    txt(s, text, { x, y, w, h: o.h || 0.36, fontSize: o.fs || 12, bold: true, color: fg, align: "center", valign: "middle" });
  };
  const VR = 0.5624; // frame aspect w/h (478x850)

  // ================= 1. The video =================
  pres.addSection({ title: "Opening" });
  {
    const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Opening" });
    const vh = 6.9, vw = vh * VR, vx = (W - vw) / 2, vy = 0.3;
    const poster = "image/png;base64," + fs.readFileSync(FR + "opening-poster.png").toString("base64");
    s.addMedia({ type: "video", path: FR + "opening-baugrube.mp4", x: vx, y: vy, w: vw, h: vh, cover: poster });
    txt(s, "Baugrube · 21.11.2026 · 35 s Handyvideo", { x: M, y: 6.85, w: 4.5, h: 0.3, fontSize: 11, color: "71717A" });
    s.addNotes("Say nothing, or one line: 'This is 35 seconds from a real site this morning.' Let the whole clip play (click to start). The last audible sentence is 'das Einzige ... war das Wasser'.");
  }

  // ================= 2. What the engine saw =================
  {
    const s = dark("Opening", "What Tagwerk sees", "Was Tagwerk im Video erkennt");
    const stats = [["35 s", "video"], ["33", "frames, 1 per second"], ["17", "objects tagged"], ["1", "deviation: Wasser"]];
    stats.forEach((st, i) => {
      const x = M + (i % 2) * 1.95, y = 1.6 + Math.floor(i / 2) * 0.85;
      txt(s, st[0], { x, y, w: 1.9, h: 0.45, fontSize: 22, bold: true, color: i === 3 ? "F87171" : H.white });
      txt(s, st[1], { x, y: y + 0.45, w: 1.9, h: 0.3, fontSize: 11, color: H.grey4 });
    });
    const fw = 1.79, fh = fw / VR, gap = 0.18, fx0 = W - M - 4 * fw - 3 * gap, fy = 1.6;
    const frames = [
      ["det-crane.jpg", "Kran, Pfahlwand"],
      ["det-person.jpg", "Gerüst, Wasser"],
      ["det-dig.jpg", "Bagger ×2, Steifen"],
      ["det-struts.jpg", "Abfuhr, Aushub"],
    ];
    frames.forEach(([f, cap], i) => {
      const x = fx0 + i * (fw + gap);
      s.addImage({ path: FR + f, x, y: fy, w: fw, h: fh, altText: cap });
      chip(s, cap, x, fy + fh + 0.12, fw, H.grey3, H.dark2, { fs: 11, h: 0.34 });
    });
    // left explanation
    const pts = [
      [H.violet, "Geräte & Personen", "Kran, Bagger, Traktor, Bohrgeräte, Personen mit Schutzausrüstung."],
      [H.green, "Bauteile", "Pfahlwand, Schlitzwand, Rohrsteifen, Aushub: the things in the LV and the schedule."],
      [H.red, "Abweichung", "Standing water on the wall crest. Only a proposal until the site manager confirms it."],
    ];
    for (let i = 0; i < pts.length; i++) {
      const y = 3.45 + i * 1.05;
      s.addShape(pres.shapes.RECTANGLE, { x: M, y: y + 0.06, w: 0.22, h: 0.22, fill: { color: H.dark }, line: { color: pts[i][0], width: 2.5 } });
      txt(s, pts[i][1], { x: M + 0.4, y, w: 3.4, h: 0.35, fontSize: 15, bold: true, color: H.white });
      txt(s, pts[i][2], { x: M + 0.4, y: y + 0.36, w: 3.4, h: 0.65, fontSize: 12, color: H.grey4, valign: "top" });
    }
    s.addNotes("The same clip, frame by frame: equipment and people in violet, building elements that exist in the LV and schedule in green, the deviation in red. Everything the camera tags is a proposal until the site manager's words confirm it.");
  }

  // ================= 3. Voice note =================
  {
    const s = content("Opening", "What Tagwerk heard", "Was Tagwerk hört: 15 s Sprachnotiz");
    // left: raw audio
    card(s, M, 1.85, 5.3, 1.6, { fill: H.surface, line: H.surface });
    s.addImage({ data: await icon(L.LuAudioLines, H.muted), x: M + 0.25, y: 2.05, w: 0.36, h: 0.36 });
    txt(s, "Originalton im Video", { x: M + 0.8, y: 2.03, w: 4, h: 0.4, fontSize: 15, bold: true });
    txt(s, "Whisper: „… was weiß, was weiß, was weiß …“  Only one clear sentence: „das Einzige … war das Wasser“.",
      { x: M + 0.8, y: 2.45, w: 4.3, h: 0.85, fontSize: 12, color: H.muted, valign: "top" });
    // voice note
    card(s, M, 3.65, 5.3, 2.95, { fill: H.blueTint, line: H.blueTint });
    await iconCircle(s, L.LuMic, M + 0.25, 3.85, 0.56, H.blue, H.white);
    txt(s, "Sprachnotiz nach dem Rundgang", { x: M + 1.0, y: 3.9, w: 4.1, h: 0.4, fontSize: 15, bold: true, color: "1E3A8A" });
    txt(s, "„Baugrube Abschnitt drei. Aushub dritte Lage unter der zweiten Steifenlage zur Hälfte fertig, zwei Bagger, ein Traktor mit Mulde. Gerüst an Achse zwölf umgesetzt. An der Bohrpfahlwand Nord steht Wasser, die Wasserhaltung reicht nicht.“",
      { x: M + 0.3, y: 4.55, w: 4.75, h: 1.9, fontSize: 13, italic: true, color: "1E3A8A", valign: "top" });
    // right: structured
    arrow(s, 6.2, 4.1, 6.75, 4.1, H.grey4);
    txt(s, "STRUCTURED, LINKED TO THE CLIP", { x: 6.9, y: 1.85, w: 5.6, h: 0.3, fontSize: 11, bold: true, color: H.muted, charSpacing: 1 });
    const ev = [
      [L.LuShovel, "Fortschritt", "Aushub Lage 3 → 50 %", "confirms: Bagger ×2, Aushub", H.green, H.greenTint],
      [L.LuTruck, "Leistung", "Boden laden, abfahren", "confirms: Traktor mit Mulde", H.green, H.greenTint],
      [L.LuConstruction, "Fortschritt", "Gerüst Achse 12 umgesetzt", "confirms: Kran, Gerüst am Haken", H.green, H.greenTint],
      [L.LuDroplets, "Behinderung", "Wasser an Bohrpfahlwand Nord", "confirms: stehendes Wasser", H.red, H.redTint],
      [L.LuDrill, "Offen", "Bohrgerät ×2", "no voice evidence, stays a proposal", H.violetDk, H.violetTint],
    ];
    for (let i = 0; i < ev.length; i++) {
      const y = 2.25 + i * 0.88;
      card(s, 6.9, y, 5.68, 0.76);
      await iconCircle(s, ev[i][0], 7.05, y + 0.13, 0.5, ev[i][5], ev[i][4]);
      txt(s, ev[i][1].toUpperCase(), { x: 7.7, y: y + 0.1, w: 1.6, h: 0.25, fontSize: 10, bold: true, color: ev[i][4], charSpacing: 1 });
      txt(s, ev[i][2], { x: 7.7, y: y + 0.36, w: 2.9, h: 0.3, fontSize: 13, bold: true });
      txt(s, ev[i][3], { x: 10.5, y: y, w: 1.95, h: 0.76, fontSize: 11, color: H.muted, valign: "middle", align: "right" });
    }
    s.addNotes("Construction sites are loud; the wind ate most of the original audio, and Whisper hallucinates on it. The real workflow is a short voice note after the walk. Each sentence confirms or adds to what the camera saw. The piling rigs get no sentence, so they stay a proposal.");
  }

  // ================= 4. The stakes =================
  pres.addSection({ title: "Problem" });
  {
    const s = content("Problem", "Why this sentence matters", "Ohne Tagwerk ist dieser Satz weg");
    const y0 = 2.6, step = (W - 2 * M) / 4;
    line(s, M + 0.3, y0, W - M - 0.3, y0, H.border, undefined, 2);
    const ev = [
      ["07:40", "Wasser an der Wand", "gesehen, gesagt, gefilmt", H.ink, H.surface],
      ["08:00", "Kurzer Anruf", "mündlich, ohne Protokoll", H.ink, H.surface],
      ["18:00", "Nichts schriftlich", "Bautagebuch bleibt leer", H.amber, H.amberTint],
      ["+6 Wochen", "Nachtrag abgelehnt", "keine Anzeige, kein Anspruch", H.red, H.redTint],
    ];
    ev.forEach((e, i) => {
      const cx = M + step * i + step / 2;
      s.addShape(pres.shapes.OVAL, { x: cx - 0.16, y: y0 - 0.16, w: 0.32, h: 0.32, fill: { color: e[3] }, line: { color: H.white, width: 3 } });
      txt(s, e[0], { x: cx - 1.3, y: 1.9, w: 2.6, h: 0.4, fontSize: 18, bold: true, align: "center", color: e[3] });
      card(s, cx - 1.35, 3.0, 2.7, 1.05, { fill: e[4], line: e[4] });
      txt(s, e[1], { x: cx - 1.2, y: 3.12, w: 2.4, h: 0.4, fontSize: 15, bold: true, align: "center" });
      txt(s, e[2], { x: cx - 1.2, y: 3.52, w: 2.4, h: 0.4, fontSize: 13, color: H.muted, align: "center" });
    });
    card(s, M, 4.5, 7.3, 1.95);
    s.addImage({ data: await icon(L.LuScale, H.ink), x: M + 0.3, y: 4.8, w: 0.4, h: 0.4 });
    txt(s, "VOB/B § 6 (1)", { x: M + 0.9, y: 4.75, w: 6, h: 0.4, fontSize: 16, bold: true });
    txt(s, "A hindrance must be reported to the client in writing without undue delay („unverzüglich schriftlich“). Without it, extension of time and compensation can be lost.",
      { x: M + 0.9, y: 5.17, w: 6.2, h: 1.1, fontSize: 14, valign: "top" });
    txt(s, "35 %", { x: 8.45, y: 4.45, w: 4.1, h: 0.95, fontSize: 60, bold: true });
    txt(s, "of construction leaders' time goes to non-productive work such as searching for project data and rework.",
      { x: 8.45, y: 5.4, w: 4.1, h: 0.75, fontSize: 13, valign: "top" });
    txt(s, "FMI / PlanGrid, Construction Disconnected (2018), ~600 leaders", { x: 8.45, y: 6.2, w: 4.1, h: 0.3, fontSize: 10, color: H.muted });
    s.addNotes("Without a tool, this is what happens to the water sentence: seen, said, maybe a phone call, nothing in writing, and weeks later the claim for the extra time is rejected. The 35 % is general non-productive time, not documentation alone.");
  }

  // ================= 5. Pipeline on this clip =================
  pres.addSection({ title: "How it works" });
  {
    const s = content("How it works", "How it works · on this clip", "Vom Video zum Datensatz in sieben Schritten");
    const st = [
      [L.LuSmartphone, "Upload", "2 clips, 35 s, Handy-Browser"],
      [L.LuAudioLines, "Speech", "Whisper int8, Sprachnotiz DE"],
      [L.LuScanEye, "Vision", "33 frames, Kran, Bagger, Steifen"],
      [L.LuCloudSun, "Context", "Wetter zum Ort und Datum"],
      [L.LuBrainCircuit, "Structuring", "4 facts, 1 proposal open"],
      [L.LuDatabase, "Project state", "Graph: Bauteil, Vorgang, LV"],
      [L.LuFileText, "Outputs", "Bericht, Prognose, Anzeige"],
    ];
    const n = st.length, gap = 0.22, bw = (W - 2 * M - gap * (n - 1)) / n, y = 2.0;
    for (let i = 0; i < n; i++) {
      const x = M + i * (bw + gap), hot = i === 4;
      card(s, x, y, bw, 2.55, { fill: hot ? H.blueTint : H.white, line: hot ? H.blue : H.border });
      await iconCircle(s, st[i][0], x + bw / 2 - 0.35, y + 0.3, 0.7, hot ? H.blue : H.surface, hot ? H.white : H.ink);
      txt(s, st[i][1], { x: x + 0.08, y: y + 1.15, w: bw - 0.16, h: 0.4, fontSize: 15, bold: true, align: "center" });
      txt(s, st[i][2], { x: x + 0.1, y: y + 1.55, w: bw - 0.2, h: 0.85, fontSize: 12, color: H.muted, align: "center", valign: "top" });
      if (i < n - 1) arrow(s, x + bw + 0.02, y + 0.65, x + bw + gap - 0.02, y + 0.65);
    }
    const facts = [
      [L.LuCpu, "One laptop GPU", "Everything above ran on a GTX 1060."],
      [L.LuWifiOff, "Works offline", "German keyword rules when no LLM is available."],
      [L.LuRotateCcw, "Replayable", "Every stage cached; any capture replays exactly."],
    ];
    for (let i = 0; i < 3; i++) {
      const x = M + i * 4.0;
      s.addImage({ data: await icon(facts[i][0], H.blue), x, y: 5.1, w: 0.42, h: 0.42 });
      txt(s, facts[i][1], { x: x + 0.6, y: 5.03, w: 3.2, h: 0.35, fontSize: 16, bold: true });
      txt(s, facts[i][2], { x: x + 0.6, y: 5.4, w: 3.2, h: 0.6, fontSize: 13, color: H.muted, valign: "top" });
    }
    s.addNotes("The same clip, stage by stage. Structuring is the heart: Claude with a strict tool schema, or German keyword rules offline. Every stage output is cached, so this exact capture can be replayed without GPU or network.");
  }

  // ================= 6. Mapping to schedule and GAEB =================
  {
    const s = content("How it works", "How the engine connects it", "Vom Video zu Terminplan und LV");
    const cols = [["SIGNAL", 3.1], ["BAUTEIL / ZONE", 2.0], ["P6-VORGANG", 2.2], ["GAEB-POSITION", 2.55], ["WIRKUNG", 1.6]];
    const cg = 0.1; let cx = M; const colX = [];
    cols.forEach(([h, w]) => { colX.push(cx); txt(s, h, { x: cx, y: 1.7, w, h: 0.3, fontSize: 11, bold: true, color: H.muted, charSpacing: 1 }); cx += w + cg; });
    const rows = [
      ["struts-excavator-sq.jpg", "Bagger ×2, Aushub", "„Aushub dritte Lage zur Hälfte“", "Baugrube BA 3\nLage 3", "B2030\nAushub Lage 3", "01.02.0030\nAushub Baugrube BK 3–5 · m³", "Ist 50 %", H.green, H.greenTint],
      ["struts-haul-sq.jpg", "Traktor mit Mulde", "„ein Traktor mit Mulde“", "Baugrube BA 3\nAbfuhr", "B2030\nAushub Lage 3", "01.02.0040\nBoden laden, abfahren · m³", "Fuhren fürs Aufmaß", H.ink, H.surface],
      ["crane-lift-sq.jpg", "Kran, Gerüst am Haken", "„Gerüst an Achse zwölf umgesetzt“", "Achse 12\nArbeitsgerüst", "B2050\nGerüst umsetzen", "03.01.0020\nArbeitsgerüst umsetzen · St", "Erledigt", H.green, H.greenTint],
      ["walk-wall-sq.jpg", "stehendes Wasser", "„Wasser an der Bohrpfahlwand Nord“", "Bohrpfahlwand\nNord", "B2040 Wasserhaltung\n→ B2060 Sohle", "01.04.0010\nWasserhaltung betreiben · h", "Verzug + Anzeige", H.red, H.redTint],
    ];
    const rh = 1.08, ry0 = 2.05;
    for (let i = 0; i < rows.length; i++) {
      const r = rows[i], y = ry0 + i * (rh + 0.1);
      card(s, M, y, W - 2 * M, rh, { fill: i === 3 ? "FFF7F7" : H.white, line: i === 3 ? "FECACA" : H.border });
      s.addImage({ path: FR + r[0], x: colX[0] + 0.12, y: y + 0.12, w: 0.84, h: 0.84 });
      txt(s, [{ text: "◇ " + r[1], options: { color: H.violetDk, bold: true, breakLine: true } }, { text: r[2], options: { color: H.blue, bold: true } }],
        { x: colX[0] + 1.08, y: y + 0.08, w: cols[0][1] - 1.15, h: rh - 0.16, fontSize: 11, valign: "middle" });
      [3, 4, 5].forEach((k, j) => {
        const [a, b] = r[k].split("\n");
        txt(s, [{ text: a, options: { bold: true, breakLine: true } }, { text: b, options: { color: H.muted } }],
          { x: colX[j + 1], y: y + 0.08, w: cols[j + 1][1], h: rh - 0.16, fontSize: 12, valign: "middle" });
      });
      const ew = cols[4][1] - 0.15;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: colX[4], y: y + rh / 2 - 0.22, w: ew, h: 0.44, rectRadius: 0.1, fill: { color: r[8] }, line: { color: r[7], width: 1 } });
      txt(s, r[6], { x: colX[4], y: y + rh / 2 - 0.22, w: ew, h: 0.44, fontSize: 11, bold: true, color: r[7], align: "center", valign: "middle" });
    }
    txt(s, "◇ camera detection   ·   blue = site manager's voice note.   Example LV positions and activity ids for this site; real values come from its GAEB X83 and P6 XML.",
      { x: M, y: 6.72, w: 11.8, h: 0.25, fontSize: 9, color: H.muted });
    s.addNotes("One row per piece of evidence. Camera plus voice confirms progress on the excavation, which updates the P6 activity and the quantity against the GAEB position for the Aufmaß. The water sentence becomes an event on dewatering, and the slab that follows it moves.");
  }

  // ================= 7. Trust =================
  {
    const s = content("How it works", "Human in the loop", "Beweis statt Behauptung");
    const rules = [
      [L.LuMic, "Voice confirms, vision only proposes", "The piling rigs stay a proposal: no sentence backed them.", H.blue, H.blueTint],
      [L.LuQuote, "Every change keeps its quote", "States only go up. Each change stores who said what, when, on which element.", H.ink, H.surface],
      [L.LuLink, "Tied to contract and schedule", "Element → GAEB position → P6 activity. Progress is BoQ-weighted.", H.green, H.greenTint],
      [L.LuUserCheck, "Nothing leaves without sign-off", "Reports and notices are drafts until the site manager approves them.", H.amber, H.amberTint],
    ];
    for (let i = 0; i < rules.length; i++) {
      const y = 1.95 + i * 1.18;
      await iconCircle(s, rules[i][0], M, y, 0.62, rules[i][4], rules[i][3]);
      txt(s, rules[i][1], { x: M + 0.85, y: y - 0.02, w: 5.6, h: 0.35, fontSize: 16, bold: true });
      txt(s, rules[i][2], { x: M + 0.85, y: y + 0.36, w: 5.6, h: 0.65, fontSize: 13, color: H.muted, valign: "top" });
    }
    card(s, 7.45, 1.95, 5.13, 4.65, { fill: "FAFAFA" });
    const N = {
      cap: [10.0, 2.75, "Video 07:40", H.blue, H.blueTint, H.blue],
      el: [8.6, 4.0, "Aushub Lage 3", H.green, H.greenTint, H.green],
      act: [10.0, 5.25, "B2030 Aushub", H.ink, H.white, H.ink],
      boq: [11.5, 4.0, "LV 01.02.0030", H.ink, H.white, H.ink],
      ev: [11.75, 2.75, "Wasser", H.red, H.redTint, H.red],
      prop: [8.25, 2.75, "Bohrgerät?", H.violetDk, H.violetTint, H.violet],
    };
    const E = [["cap", "el"], ["el", "act"], ["el", "boq"], ["boq", "act"], ["cap", "ev"], ["ev", "act"], ["prop", "cap"]];
    E.forEach(([a, b]) => line(s, N[a][0], N[a][1], N[b][0], N[b][1], a === "prop" ? H.violet : "C4C4C4", a === "prop" ? "dash" : undefined));
    Object.entries(N).forEach(([k, n]) => {
      const w = 1.45, h = 0.5;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: n[0] - w / 2, y: n[1] - h / 2, w, h, rectRadius: 0.25, fill: { color: n[4] },
        line: { color: n[5], width: 1.25, dashType: k === "prop" ? "dash" : undefined } });
      txt(s, n[2], { x: n[0] - w / 2, y: n[1] - h / 2, w, h, fontSize: 11, bold: true, color: n[3], align: "center", valign: "middle" });
    });
    txt(s, "Dashed = camera proposal without voice evidence, never applied", { x: 7.7, y: 6.1, w: 4.7, h: 0.3, fontSize: 10, color: H.muted });
    s.addNotes("This answers the hallucination worry with the clip itself: the piling rigs stay a dashed proposal because no sentence confirms them. The LLM cannot claim voice evidence without a matching quote (enforce_evidence).");
  }

  // ================= 8. Deviation =================
  pres.addSection({ title: "Impact" });
  {
    const s = content("Impact", "Deviation detection", "Das Wasser verschiebt die Sohle");
    const gx = M + 2.6, gw = 5.35, gy = 2.25, days = ["20", "21", "22", "23", "24", "25", "26", "27", "28", "29"];
    const dw = gw / days.length;
    days.forEach((d, i) => {
      if (i === 2 || i === 3) s.addShape(pres.shapes.RECTANGLE, { x: gx + i * dw, y: gy + 0.4, w: dw, h: 3.2, fill: { color: "FAFAFA" }, line: { type: "none" } });
      txt(s, d + ".", { x: gx + i * dw, y: gy, w: dw, h: 0.3, fontSize: 11, color: H.muted, align: "center" });
    });
    // [id, name, planStart, planEnd, slipStart, slipEnd, done?]
    const rows = [
      ["B2050", "Gerüst umsetzen", 0, 2, null, null, true],
      ["B2030", "Aushub Lage 3", 0, 4, 4, 6, false],
      ["B2040", "Wasserhaltung", 0, 9, null, null, false],
      ["B2060", "Sohle betonieren", 5, 8, 7, 10, false],
    ];
    rows.forEach((r, i) => {
      const y = gy + 0.55 + i * 0.75;
      txt(s, r[0], { x: M, y, w: 0.8, h: 0.45, fontSize: 12, bold: true, color: H.muted, valign: "middle" });
      txt(s, r[1], { x: M + 0.8, y, w: 1.75, h: 0.45, fontSize: 13, bold: true, valign: "middle" });
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: gx + r[2] * dw + 0.03, y: y + 0.08, w: (r[3] - r[2]) * dw - 0.06, h: 0.3, rectRadius: 0.06,
        fill: { color: r[6] ? H.greenTint : i === 2 ? H.amberTint : H.surface }, line: { color: r[6] ? H.green : i === 2 ? H.amber : "C4C4C4", width: 1 } });
      if (r[4] !== null) s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: gx + r[4] * dw + 0.03, y: y + 0.08, w: (Math.min(r[5], 10) - r[4]) * dw - 0.06,
        h: 0.3, rectRadius: 0.06, fill: { color: H.redTint }, line: { color: H.red, width: 1.25 } });
    });
    line(s, gx + 1.5 * dw, gy + 0.35, gx + 1.5 * dw, gy + 3.65, H.blue, undefined, 2);
    txt(s, "heute 21.11.", { x: gx + 1.5 * dw - 0.6, y: gy + 3.7, w: 1.2, h: 0.3, fontSize: 11, bold: true, color: H.blue, align: "center" });
    card(s, M, 6.0, 7.95, 0.6, { fill: H.redTint, line: H.redTint });
    s.addImage({ data: await icon(L.LuDroplets, H.red), x: M + 0.2, y: 6.13, w: 0.34, h: 0.34 });
    txt(s, "„Die Wasserhaltung reicht nicht“  →  event on B2040, Aushub slows, Sohle (finish-to-start) moves",
      { x: M + 0.7, y: 6.0, w: 7.15, h: 0.6, fontSize: 13, bold: true, color: H.red, valign: "middle" });
    const k = [
      ["+2 AT", "Sohle betonieren", "forecast from today's evidence", H.red],
      ["50 %", "Aushub Lage 3", "confirmed by voice + 2 excavators", H.ink],
      ["4", "facts from 35 s", "1 proposal still open", H.ink],
      ["07:40", "Beleg", "video timestamp + quote, kept", H.ink],
    ];
    k.forEach((kk, i) => {
      const x = 9.1 + (i % 2) * 1.8, y = 2.25 + Math.floor(i / 2) * 1.95;
      card(s, x, y, 1.68, 1.8);
      txt(s, kk[0], { x: x + 0.15, y: y + 0.15, w: 1.45, h: 0.6, fontSize: 26, bold: true, color: kk[3] });
      txt(s, kk[1], { x: x + 0.15, y: y + 0.8, w: 1.45, h: 0.35, fontSize: 12, bold: true });
      txt(s, kk[2], { x: x + 0.15, y: y + 1.13, w: 1.45, h: 0.55, fontSize: 10, color: H.muted, valign: "top" });
    });
    txt(s, "Example schedule for this site, for illustration.", { x: M, y: 6.72, w: 6, h: 0.25, fontSize: 9, color: H.muted });
    s.addNotes("Plan versus actual for this pit. The water event lands on dewatering; excavation slows, and the slab, which can only start after excavation, moves two working days. The schedule here is an example for this site; in the live demo you'll see the forecast engine do this on our seeded project.");
  }

  // ================= 9. Notice =================
  {
    const s = content("Impact", "Correspondence", "Vom Wasser zur Behinderungsanzeige");
    card(s, M, 1.9, 5.1, 4.25, { fill: H.surface, line: H.surface });
    txt(s, "TAGESBERICHT 21.11.2026", { x: M + 0.3, y: 2.1, w: 4.5, h: 0.3, fontSize: 11, bold: true, color: H.muted, charSpacing: 1 });
    txt(s, "5. Behinderungen / Verzug", { x: M + 0.3, y: 2.45, w: 4.5, h: 0.4, fontSize: 17, bold: true });
    const f = [["Vorgang", "B2040 Wasserhaltung"], ["Umstand", "Wasser an Bohrpfahlwand Nord"], ["Seit", "21.11.2026, 07:40"],
      ["Auswirkung", "+2 AT, B2060 Sohle"], ["Beleg", "Video 07:40 + Sprachnotiz"]];
    f.forEach((r, i) => {
      const y = 3.05 + i * 0.58;
      txt(s, r[0], { x: M + 0.3, y, w: 1.3, h: 0.45, fontSize: 12, color: H.muted, valign: "middle" });
      txt(s, r[1], { x: M + 1.6, y, w: 3.3, h: 0.45, fontSize: 13, bold: true, valign: "middle", color: r[0] === "Auswirkung" ? H.red : H.ink });
    });
    await iconCircle(s, L.LuArrowRight, 6.15, 3.7, 0.6, H.ink, H.white);
    card(s, 7.05, 1.9, 5.53, 4.25, { lw: 1.25 });
    txt(s, "Behinderungsanzeige", { x: 7.35, y: 2.05, w: 3.6, h: 0.35, fontSize: 16, bold: true });
    txt(s, "gem. § 6 (1) VOB/B", { x: 7.35, y: 2.4, w: 3.6, h: 0.25, fontSize: 11, color: H.muted });
    chip(s, "ENTWURF", 11.25, 2.1, 1.1, H.amberDk, H.amberTint);
    const lines = ["Bauvorhaben: Baugrube, Abschnitt 3", "Behindernder Umstand: Wasserandrang an der Bohrpfahlwand Nord, Wasserhaltung unzureichend",
      "Betroffen: Aushub Lage 3, Sohle (B2030, B2060)", "Voraussichtlich: +2 Arbeitstage", "Anlage: Video 21.11., 07:40"];
    let ly = 2.75;
    lines.forEach((l, i) => { const h = i === 1 ? 0.6 : 0.36; txt(s, l, { x: 7.35, y: ly, w: 5.0, h, fontSize: 12, valign: "top" }); ly += h + 0.06; });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.35, y: 5.35, w: 1.7, h: 0.5, rectRadius: 0.08, fill: { color: H.white }, line: { color: H.border } });
    txt(s, "Bearbeiten", { x: 7.35, y: 5.35, w: 1.7, h: 0.5, fontSize: 13, bold: true, align: "center", valign: "middle" });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 9.2, y: 5.35, w: 2.4, h: 0.5, rectRadius: 0.08, fill: { color: H.ink }, line: { type: "none" } });
    txt(s, "Freigeben & PDF", { x: 9.2, y: 5.35, w: 2.4, h: 0.5, fontSize: 13, bold: true, color: H.white, align: "center", valign: "middle" });
    txt(s, "Entwurfsunterstützung, keine Rechtsberatung. Prüfung und Versand durch die Bauleitung.",
      { x: M, y: 6.35, w: 11.8, h: 0.35, fontSize: 11, italic: true, color: H.muted });
    s.addNotes("The sentence from the video is now a notice draft with the evidence attached: circumstance, since when, affected works, expected effect, and the clip at 07:40. The site manager edits and approves. We draft; we do not give legal advice.");
  }

  // ================= 10. Live demo =================
  {
    const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Impact" });
    chip(s, "●  LIVE DEMO", M, 0.85, 1.8, H.white, H.blue);
    txt(s, "Jetzt live: ein ganzer Tag", { x: M, y: 1.6, w: 11, h: 1.0, fontSize: 54, bold: true, color: H.white });
    txt(s, "Same engine, our seeded project: Hörsaal-Sanierung, Thursday 26.11.2026", { x: M, y: 2.65, w: 11, h: 0.4, fontSize: 18, color: H.grey4 });
    const beats = [["07:15", "Rundgang", "Film + talk on the phone"], ["07:20", "Live-Graph", "Changes with quotes appear"],
      ["10:30", "Absence", "Forecast moves 30.11. → 01.12."], ["16:45", "Tagesbericht", "Filled automatically"], ["17:00", "Anzeige", "Draft reviewed, PDF out"]];
    const y0 = 4.4, step = (W - 2 * M) / beats.length;
    line(s, M + step / 2, y0, W - M - step / 2, y0, "3F3F46", undefined, 2);
    beats.forEach((b, i) => {
      const cx = M + step * i + step / 2, hot = i === 2 || i === 4;
      s.addShape(pres.shapes.OVAL, { x: cx - 0.13, y: y0 - 0.13, w: 0.26, h: 0.26, fill: { color: hot ? H.blue : "52525B" }, line: { type: "none" } });
      txt(s, b[0], { x: cx - 1.2, y: 3.75, w: 2.4, h: 0.4, fontSize: 18, bold: true, color: H.white, align: "center" });
      txt(s, b[1], { x: cx - 1.2, y: 4.7, w: 2.4, h: 0.35, fontSize: 15, bold: true, color: H.white, align: "center" });
      txt(s, b[2], { x: cx - 1.2, y: 5.05, w: 2.4, h: 0.6, fontSize: 12, color: H.grey4, align: "center", valign: "top" });
    });
    txt(s, "Fallback: cached replay (no GPU, no network)", { x: M, y: 6.6, w: 8, h: 0.3, fontSize: 11, color: "71717A" });
    s.addNotes("Switch to the browser. docs/DEMO.md 3-Minuten-Demo: recording under 'Aufnahmen des Tages', changes with quotes, 'zwei Mann vom Trockenbau sind krank' moves the forecast, red delay in the Gantt, Tagesbericht, notice draft, approve, PDF. Fallback: replay uw-video or cap-e2e-2.");
  }

  // ================= 11. Challenge fit =================
  pres.addSection({ title: "Market" });
  {
    const s = content("Market", "Challenge B", "Challenge B: abgedeckt");
    const items = [
      ["Voice / text capture on mobile", "Phone browser upload, Whisper DE/NL/EN"], ["Daily report analysis vs plan", "Ist/Soll, SPI, forecast from evidence"],
      ["Notice drafts from keywords", "Behinderungs-, Mehrkosten-, Bedenkenanzeige"], ["Structured summaries", "Events: absence, delay, defect, delivery"],
      ["Correspondence on deviation", "Delay detected → draft proposed"], ["Human in the loop", "Vision proposes, voice confirms, manager signs"],
      ["PDF export", "A4 Tagesbericht and notice drafts"], ["“A day in the life” demo", "Real site clip + rehearsed live run"],
    ];
    for (let i = 0; i < items.length; i++) {
      const x = M + (i % 2) * 6.0, y = 1.95 + Math.floor(i / 2) * 1.15;
      card(s, x, y, 5.8, 0.98);
      await iconCircle(s, L.LuCheck, x + 0.2, y + 0.2, 0.58, H.greenTint, H.green);
      txt(s, items[i][0], { x: x + 0.98, y: y + 0.14, w: 4.7, h: 0.38, fontSize: 15, bold: true });
      txt(s, items[i][1], { x: x + 0.98, y: y + 0.52, w: 4.7, h: 0.32, fontSize: 12, color: H.muted });
    }
    s.addNotes("Walk the checklist quickly; the clip and the demo already showed it.");
  }

  // ================= 12. Positioning =================
  {
    const s = content("Market", "Positioning", "Sprache, verknüpft mit Vertrag und Terminplan");
    const px = M + 0.5, py = 1.95, pw = 6.6, ph = 4.4;
    card(s, px, py, pw, ph, { fill: "FAFAFA" });
    line(s, px + pw / 2, py, px + pw / 2, py + ph, H.border);
    line(s, px, py + ph / 2, px + pw, py + ph / 2, H.border);
    txt(s, "Capture effort  →  passive (talk & film)", { x: px, y: py + ph + 0.08, w: pw, h: 0.3, fontSize: 11, color: H.muted, align: "right" });
    txt(s, "Link to contract & schedule  →", { x: px - 0.3 - 2.2, y: py + ph / 2 - 0.15, w: 4.4, h: 0.3, fontSize: 11, color: H.muted, rotate: 270, align: "center" });
    [["Fieldwire", 0.18, 0.2], ["Procore Daily Log", 0.25, 0.32], ["Primavera P6", 0.18, 0.8], ["Capmo KI", 0.72, 0.28], ["PlanRadar", 0.62, 0.18],
      ["Buildots / Doxel*", 0.78, 0.64]].forEach(([n, fx, fy]) => {
      const cx = px + fx * pw, cy = py + (1 - fy) * ph;
      s.addShape(pres.shapes.OVAL, { x: cx - 0.09, y: cy - 0.09, w: 0.18, h: 0.18, fill: { color: H.grey4 }, line: { type: "none" } });
      txt(s, n, { x: cx + 0.15, y: cy - 0.17, w: 2, h: 0.34, fontSize: 12, color: H.muted, valign: "middle" });
    });
    const tx = px + 0.86 * pw, ty = py + 0.12 * ph;
    s.addShape(pres.shapes.OVAL, { x: tx - 0.17, y: ty - 0.17, w: 0.34, h: 0.34, fill: { color: H.blue }, line: { color: H.white, width: 2 } });
    txt(s, "Tagwerk", { x: tx - 1.6, y: ty - 0.18, w: 1.35, h: 0.36, fontSize: 15, bold: true, color: H.blue, align: "right", valign: "middle" });
    txt(s, "* needs BIM model + camera hardware", { x: px, y: py + ph + 0.4, w: 4, h: 0.3, fontSize: 10, color: H.muted });
    [["35 s", "of phone video became 4 linked facts and a notice draft"], ["4", "export formats: P6 XML, GAEB X83/X84, Outlook .ics, PDF"],
      ["0", "BIM or extra hardware required: a phone and a laptop"]].forEach((p, i) => {
      const y = 1.95 + i * 1.5;
      txt(s, p[0], { x: 8.35, y, w: 4.2, h: 0.7, fontSize: 40, bold: true, color: i === 0 ? H.blue : H.ink });
      txt(s, p[1], { x: 8.35, y: y + 0.72, w: 4.2, h: 0.6, fontSize: 13, color: H.muted, valign: "top" });
    });
    txt(s, "Positions based on public vendor information, Nov 2026.", { x: 8.35, y: 6.45, w: 4.3, h: 0.3, fontSize: 9, color: H.muted });
    s.addNotes("Capmo and PlanRadar turn voice into diary entries and tickets, but as free text. Buildots and Doxel link to the model but need BIM and cameras and capture progress, not causes. Tagwerk ties spoken causes to BoQ positions and the schedule.");
  }

  // ================= 13. Close =================
  pres.addSection({ title: "Close" });
  {
    const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Close" });
    s.addImage({ path: FR + "walk-wall.jpg", x: W - 7.5 * VR, y: 0, w: 7.5 * VR, h: 7.5 });
    s.addShape(pres.shapes.RECTANGLE, { x: W - 7.5 * VR, y: 0, w: 7.5 * VR, h: 7.5, fill: { color: H.dark, transparency: 35 }, line: { type: "none" } });
    logo(s, M, 0.75, 0.7, true);
    txt(s, "„Das Einzige war das Wasser.“", { x: M, y: 1.8, w: 8.3, h: 0.8, fontSize: 36, bold: true, color: H.white });
    txt(s, "Jetzt steht es im Bautagebuch, im Terminplan und in der Anzeige.", { x: M, y: 2.6, w: 8.3, h: 0.6, fontSize: 20, color: H.blueL });
    txt(s, "Tagwerk: the day's work, documented.", { x: M, y: 3.35, w: 8.3, h: 0.5, fontSize: 18, color: H.grey3 });
    const nx = [[L.LuHardHat, "Pilot", "This Baugrube, four weeks"], [L.LuHistory, "Audit trail", "Corrections with full history"],
      [L.LuPlug, "Integrations", "P6 import, mail, Capmo / PlanRadar"]];
    for (let i = 0; i < 3; i++) {
      const x = M + i * 2.8;
      card(s, x, 4.45, 2.6, 1.3, { fill: H.dark2, line: H.darkLine });
      s.addImage({ data: await icon(nx[i][0], H.blueL), x: x + 0.2, y: 4.65, w: 0.34, h: 0.34 });
      txt(s, nx[i][1], { x: x + 0.65, y: 4.62, w: 1.85, h: 0.4, fontSize: 15, bold: true, color: H.white });
      txt(s, nx[i][2], { x: x + 0.2, y: 5.1, w: 2.3, h: 0.55, fontSize: 11, color: H.grey4, valign: "top" });
    }
    txt(s, "Team Tagwerk  ·  github.com/Current-cmd/Tagwerk", { x: M, y: 6.3, w: 5.5, h: 0.3, fontSize: 13, color: H.grey4 });
    txt(s, "Entwurfsunterstützung, keine Rechtsberatung.", { x: M, y: 6.65, w: 5.5, h: 0.3, fontSize: 11, italic: true, color: "71717A" });
    s.addNotes("Close the loop on the opening clip. The sentence that would have been lost is now in the daily report, the schedule and a notice draft. Ask: a pilot on a real site like this one.");
  }

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})().catch((e) => { console.error(e); process.exit(1); });
