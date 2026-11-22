// Tagwerk pitch deck generator (pptxgenjs). Run: node build.js
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const L = require("react-icons/lu");
const { applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js");

const THEME = {
  name: "Tagwerk",
  headFontFace: "Arial",
  bodyFontFace: "Arial",
  colors: {
    dk1: "0A0A0A", lt1: "FFFFFF", dk2: "141416", lt2: "F5F5F5",
    accent1: "2563EB", accent2: "16A34A", accent3: "F59E0B", accent4: "DC2626",
    accent5: "8B5CF6", accent6: "737373", hlink: "2563EB", folHlink: "1D4ED8",
  },
};
// hex constants (for tints not in the theme)
const H = {
  ink: "0A0A0A", dark: "141416", dark2: "1F1F23", muted: "737373", border: "E5E5E5", surface: "F5F5F5",
  blue: "2563EB", blueTint: "DBEAFE", green: "16A34A", greenTint: "DCFCE7", amber: "F59E0B", amberTint: "FEF3C7",
  red: "DC2626", redTint: "FEE2E2", violet: "8B5CF6", violetTint: "F5F3FF", sky: "7DD3FC", skyTint: "F0F9FF",
  grey4: "A3A3A3", white: "FFFFFF",
};

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(Comp, { color: "#" + color, size: String(size), strokeWidth: 2 })
  );
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
  pres.title = "Tagwerk – Challenge B pitch";
  pres.author = "Team Tagwerk";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;
  const W = 13.333, M = 0.75;

  // ---------- layouts ----------
  pres.defineSlideMaster({
    title: "DARK",
    background: { color: H.dark },
    objects: [],
  });
  pres.defineSlideMaster({
    title: "CONTENT",
    background: { color: H.white },
    objects: [
      { text: { text: "Tagwerk", options: { x: M, y: 7.0, w: 3, h: 0.3, fontSize: 10, color: H.muted, margin: 0 } } },
    ],
    slideNumber: { x: W - M - 0.5, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: H.muted, align: "right" },
    placeholders: [],
  });
  pres.defineSlideMaster({
    title: "CONTENT_TITLED",
    background: { color: H.white },
    objects: [
      { text: { text: "Tagwerk", options: { x: M, y: 7.0, w: 3, h: 0.3, fontSize: 10, color: H.muted, margin: 0 } } },
      { placeholder: { options: { name: "kicker", type: "body", x: M, y: 0.5, w: 11.5, h: 0.3, fontSize: 12, bold: true,
          color: H.blue, charSpacing: 2, margin: 0 }, text: "" } },
      { placeholder: { options: { name: "title", type: "title", x: M, y: 0.82, w: 11.8, h: 0.8, fontSize: 36, bold: true,
          color: H.ink, margin: 0, valign: "top", align: "left" }, text: "" } },
    ],
    slideNumber: { x: W - M - 0.5, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: H.muted, align: "right" },
  });

  const content = (section, kicker, title) => {
    const s = pres.addSlide({ masterName: "CONTENT_TITLED", sectionTitle: section });
    s.addText(kicker.toUpperCase(), { placeholder: "kicker" });
    s.addText(title, { placeholder: "title" });
    return s;
  };
  const card = (s, x, y, w, h, opts = {}) =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w, h, rectRadius: 0.1,
      fill: { color: opts.fill || H.white }, line: { color: opts.line || H.border, width: opts.lw || 1, dashType: opts.dash },
      objectName: opts.name,
    });
  const txt = (s, text, o) => s.addText(text, { isTextBox: true, margin: 0, color: H.ink, fontSize: 14, ...o });
  const iconCircle = async (s, Comp, x, y, d, bg, fg) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: bg }, line: { type: "none" } });
    s.addImage({ data: await icon(Comp, fg), x: x + d * 0.25, y: y + d * 0.25, w: d * 0.5, h: d * 0.5 });
  };
  const logo = (s, x, y, d, inverted) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: d, h: d, rectRadius: d * 0.22,
      fill: { color: inverted ? H.white : "171717" }, line: { type: "none" } });
    s.addText("T", { isTextBox: true, x, y, w: d, h: d, align: "center", valign: "middle", margin: 0,
      fontSize: d * 40, bold: true, color: inverted ? "171717" : H.white });
  };
  const arrow = (s, x1, y1, x2, y2, color = H.grey4, dash) =>
    s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001,
      h: Math.abs(y2 - y1) || 0.001, flipV: y2 < y1, line: { color, width: 1.5, endArrowType: "triangle", dashType: dash } });
  const line = (s, x1, y1, x2, y2, color = H.grey4, dash, width = 1.25) =>
    s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.abs(x2 - x1) || 0.001,
      h: Math.abs(y2 - y1) || 0.001, flipV: (y2 < y1) !== (x2 < x1), line: { color, width, dashType: dash } });
  const chip = (s, text, x, y, w, fg, bg) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.36, rectRadius: 0.18, fill: { color: bg }, line: { type: "none" } });
    txt(s, text, { x, y, w, h: 0.36, fontSize: 12, bold: true, color: fg, align: "center", valign: "middle" });
  };

  // ================= 1. Title =================
  pres.addSection({ title: "Opening" });
  {
    const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Opening" });
    logo(s, M, 0.75, 0.7, true);
    txt(s, "Tagwerk", { x: M, y: 2.0, w: 6.5, h: 1.2, fontSize: 72, bold: true, color: H.white });
    txt(s, "Reden statt tippen: der Tagesbericht schreibt sich beim Rundgang.",
      { x: M, y: 3.25, w: 6.2, h: 0.9, fontSize: 22, color: "D4D4D4" });
    txt(s, "Talk instead of type: the daily report writes itself during the site walk.",
      { x: M, y: 4.2, w: 6.2, h: 0.4, fontSize: 14, italic: true, color: H.grey4 });
    txt(s, "CHALLENGE B  ·  AI SITE MANAGER ASSISTANT", { x: M, y: 6.25, w: 6.5, h: 0.3, fontSize: 12, bold: true,
      color: H.grey4, charSpacing: 2 });
    // right: dictation -> outcome composition
    card(s, 7.6, 1.35, 4.95, 1.55, { fill: H.dark2, line: "2E2E33", name: "quote" });
    s.addShape(pres.shapes.OVAL, { x: 7.9, y: 1.65, w: 0.6, h: 0.6, fill: { color: H.blue }, line: { type: "none" } });
    s.addImage({ data: await icon(L.LuMic, H.white), x: 8.05, y: 1.8, w: 0.3, h: 0.3 });
    txt(s, "„Zwei Mann vom Trockenbau sind krank.“", { x: 8.7, y: 1.6, w: 3.7, h: 0.7, fontSize: 18, bold: true, color: H.white });
    txt(s, "10:30 · Sprachnotiz beim Rundgang", { x: 8.7, y: 2.35, w: 3.7, h: 0.3, fontSize: 12, color: H.grey4 });
    arrow(s, 10.05, 3.0, 10.05, 3.55, "52525B");
    const outs = [
      [L.LuCalendarClock, "Prognose-Ende", "30.11. → 01.12.", H.red],
      [L.LuFileText, "Tagesbericht", "Abschnitt Verzug befüllt", H.white],
      [L.LuTriangleAlert, "Behinderungsanzeige", "Entwurf zur Freigabe", H.amber],
    ];
    for (let i = 0; i < outs.length; i++) {
      const y = 3.7 + i * 0.85;
      card(s, 7.6, y, 4.95, 0.7, { fill: H.dark2, line: "2E2E33" });
      s.addImage({ data: await icon(outs[i][0], outs[i][3]), x: 7.85, y: y + 0.2, w: 0.3, h: 0.3 });
      txt(s, outs[i][1], { x: 8.35, y: y, w: 2.2, h: 0.7, fontSize: 14, bold: true, color: H.white, valign: "middle" });
      txt(s, outs[i][2], { x: 10.4, y: y, w: 2.0, h: 0.7, fontSize: 13, color: outs[i][3] === H.white ? "D4D4D4" : outs[i][3],
        valign: "middle", align: "right" });
    }
    s.addNotes("Introduce the team in one sentence. 'We built this for the person who leaves the site last.' If demoing live, start the phone upload now so processing finishes by the demo slide.");
  }

  // ================= 2. Problem =================
  pres.addSection({ title: "Problem" });
  {
    const s = content("Problem", "The problem", "16:30 im Baucontainer");
    txt(s, "The walk is over. The documentation hasn't started.", { x: M, y: 1.6, w: 11, h: 0.4, fontSize: 18, color: H.muted });
    const ins = [
      [L.LuCamera, "47 Fotos", "on the phone, unsorted"],
      [L.LuMic, "6 Sprachmemos", "nobody will relisten"],
      [L.LuNotebookPen, "Bautagebuch", "paper notes, half filled"],
      [L.LuMail, "E-Mails & Anrufe", "deliveries, subs, client"],
    ];
    for (let i = 0; i < ins.length; i++) {
      const y = 2.35 + i * 1.02;
      card(s, M, y, 4.6, 0.86);
      await iconCircle(s, ins[i][0], M + 0.2, y + 0.16, 0.54, H.surface, H.ink);
      txt(s, ins[i][1], { x: M + 0.95, y: y + 0.13, w: 3.5, h: 0.35, fontSize: 16, bold: true });
      txt(s, ins[i][2], { x: M + 0.95, y: y + 0.47, w: 3.5, h: 0.3, fontSize: 13, color: H.muted });
    }
    for (let i = 0; i < 4; i++) arrow(s, M + 4.7, 2.78 + i * 1.02, 6.55, 3.95, "D4D4D4");
    // empty form
    card(s, 6.65, 2.35, 2.9, 3.9, { fill: H.surface });
    txt(s, "TAGESBERICHT 26.11.", { x: 6.9, y: 2.55, w: 2.5, h: 0.3, fontSize: 11, bold: true, color: H.muted, charSpacing: 1 });
    for (let i = 0; i < 6; i++) {
      s.addShape(pres.shapes.RECTANGLE, { x: 6.9, y: 3.05 + i * 0.5, w: i % 2 ? 1.6 : 2.4, h: 0.14, fill: { color: H.border }, line: { type: "none" } });
    }
    txt(s, "≈ 2 h typing ahead", { x: 6.9, y: 5.75, w: 2.5, h: 0.3, fontSize: 13, bold: true, color: H.ink });
    // stat
    txt(s, "35 %", { x: 10.0, y: 2.35, w: 2.6, h: 1.2, fontSize: 72, bold: true, color: H.ink });
    txt(s, "of construction leaders' working time goes to non-productive work such as searching for project data and rework.",
      { x: 10.0, y: 3.6, w: 2.6, h: 1.6, fontSize: 14, color: H.ink, valign: "top" });
    txt(s, "FMI / PlanGrid, Construction Disconnected (2018), survey of ~600 leaders",
      { x: 10.0, y: 5.4, w: 2.6, h: 0.8, fontSize: 10, color: H.muted, valign: "top" });
    s.addNotes("Tell it as a moment: 16:30, back in the container, two hours of typing ahead. The 35 % is non-productive work in general, not documentation time only; say it that way.");
  }

  // ================= 3. Stakes =================
  {
    const s = content("Problem", "Why it matters", "Ein vergessener Satz kostet Wochen");
    const y0 = 2.75;
    line(s, M + 0.3, y0, W - M - 0.3, y0, H.border, undefined, 2);
    const ev = [
      ["10:00", "Bagger steht still", "Leitungsfund, Freigabe fehlt", H.ink, H.surface],
      ["10:05", "Kurzer Anruf beim AG", "mündlich, ohne Protokoll", H.ink, H.surface],
      ["18:00", "Nichts schriftlich", "Bautagebuch bleibt leer", H.amber, H.amberTint],
      ["+6 Wochen", "Nachtrag abgelehnt", "keine Anzeige, kein Anspruch", H.red, H.redTint],
    ];
    const step = (W - 2 * M) / 4;
    ev.forEach((e, i) => {
      const cx = M + step * i + step / 2;
      s.addShape(pres.shapes.OVAL, { x: cx - 0.16, y: y0 - 0.16, w: 0.32, h: 0.32, fill: { color: e[3] }, line: { color: H.white, width: 3 } });
      txt(s, e[0], { x: cx - 1.3, y: 2.0, w: 2.6, h: 0.4, fontSize: 18, bold: true, align: "center", color: e[3] });
      card(s, cx - 1.35, 3.15, 2.7, 1.1, { fill: e[4], line: e[4] });
      txt(s, e[1], { x: cx - 1.2, y: 3.28, w: 2.4, h: 0.4, fontSize: 15, bold: true, align: "center" });
      txt(s, e[2], { x: cx - 1.2, y: 3.7, w: 2.4, h: 0.4, fontSize: 13, color: H.muted, align: "center" });
    });
    card(s, M, 4.75, 7.3, 1.75);
    s.addImage({ data: await icon(L.LuScale, H.ink), x: M + 0.3, y: 5.05, w: 0.4, h: 0.4 });
    txt(s, "VOB/B § 6 (1)", { x: M + 0.9, y: 5.0, w: 6, h: 0.4, fontSize: 16, bold: true });
    txt(s, "A hindrance must be reported to the client in writing without undue delay („unverzüglich schriftlich“). Without it, extension of time and compensation can be lost.",
      { x: M + 0.9, y: 5.42, w: 6.2, h: 0.95, fontSize: 14, color: H.ink, valign: "top" });
    const notices = [["§ 6", "Behinderungsanzeige"], ["§ 2", "Mehrkostenanzeige"], ["§ 4 (3)", "Bedenkenanzeige"]];
    notices.forEach((n, i) => {
      const y = 4.75 + i * 0.6;
      card(s, 8.35, y, 4.23, 0.5, { fill: H.surface, line: H.surface });
      txt(s, n[0], { x: 8.55, y, w: 0.9, h: 0.5, fontSize: 13, bold: true, color: H.muted, valign: "middle" });
      txt(s, n[1], { x: 9.45, y, w: 3, h: 0.5, fontSize: 15, bold: true, valign: "middle" });
    });
    s.addNotes("The evidence existed: it was said out loud on site at 10:00. It just never reached a formal document. That gap costs claims. Sources: VOB/B §6(1), hoai.de, forum-verlag.");
  }

  // ================= 4. Solution =================
  pres.addSection({ title: "Solution" });
  {
    const s = content("Solution", "The solution", "Reden statt tippen");
    txt(s, "One capture on the walk. Four outputs by evening.", { x: M, y: 1.6, w: 11, h: 0.4, fontSize: 18, color: H.muted });
    // phone
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 1.3, y: 2.3, w: 2.3, h: 4.3, rectRadius: 0.3, fill: { color: H.ink }, line: { type: "none" } });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 1.42, y: 2.45, w: 2.06, h: 4.0, rectRadius: 0.22, fill: { color: H.dark2 }, line: { type: "none" } });
    s.addShape(pres.shapes.OVAL, { x: 2.05, y: 3.3, w: 0.8, h: 0.8, fill: { color: H.blue }, line: { type: "none" } });
    s.addImage({ data: await icon(L.LuMic, H.white), x: 2.25, y: 3.5, w: 0.4, h: 0.4 });
    const bars = [0.25, 0.5, 0.8, 0.45, 0.7, 0.35, 0.6, 0.3];
    bars.forEach((b, i) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 1.75 + i * 0.18, y: 4.75 - b / 2, w: 0.09, h: b,
      rectRadius: 0.04, fill: { color: "60A5FA" }, line: { type: "none" } }));
    txt(s, "30 s Video + Sprache", { x: 1.42, y: 5.45, w: 2.06, h: 0.3, fontSize: 12, bold: true, color: H.white, align: "center" });
    txt(s, "Handy-Browser, kein App-Install", { x: 1.42, y: 5.75, w: 2.06, h: 0.5, fontSize: 10, color: H.grey4, align: "center" });
    const outs = [
      [L.LuNetwork, "Evidence graph", "Every sentence linked to element, GAEB position and P6 activity", H.blue, H.blueTint],
      [L.LuLayoutDashboard, "Dashboard & forecast", "Ist/Soll, SPI, forecast finish moved by today's evidence", H.green, H.greenTint],
      [L.LuFileText, "Tagesbericht", "German daily report, filled and ready to print as PDF", H.ink, H.surface],
      [L.LuTriangleAlert, "Notice draft", "Behinderungsanzeige from the detected delay, for review", H.amber, H.amberTint],
    ];
    for (let i = 0; i < 4; i++) {
      const y = 2.3 + i * 1.1;
      arrow(s, 3.75, 4.45, 5.55, y + 0.47, "D4D4D4");
      card(s, 5.65, y, 6.95, 0.94);
      await iconCircle(s, outs[i][0], 5.85, y + 0.17, 0.6, outs[i][4], outs[i][3]);
      txt(s, outs[i][1], { x: 6.7, y: y + 0.12, w: 5.7, h: 0.35, fontSize: 16, bold: true });
      txt(s, outs[i][2], { x: 6.7, y: y + 0.5, w: 5.7, h: 0.32, fontSize: 13, color: H.muted });
    }
    s.addNotes("The promise in one breath: one capture, four outputs. Then hand over to the live demo.");
  }

  // ================= 4b. Real site footage =================
  const FR = require("path").resolve(__dirname, "../../docs/design-brief/site-frames") + "/";
  {
    const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Solution" });
    txt(s, "REAL SITE · BAUGRUBE · 21.11.2026", { x: M, y: 0.5, w: 8, h: 0.3, fontSize: 12, bold: true, color: "60A5FA", charSpacing: 2 });
    txt(s, "35 Sekunden Video. Ein ganzer Bautagebuch-Eintrag.", { x: M, y: 0.82, w: 11.8, h: 0.7, fontSize: 30, bold: true, color: H.white });
    const fw = 2.62, fh = fw / 0.5624, gap = (W - 2 * M - 4 * fw) / 3, fy = 1.7;
    const frames = [
      ["walk-wall.jpg", "07:40 · Kontrollgang Pfahlwand", [["mic", "„… das Einzige war das Wasser“", H.blue]], [["vision", "safety vest", 0.30, 0.62]]],
      ["crane-lift.jpg", "08:15 · Gerüst umsetzen", [], [["vision", "crane", 0.06, 0.18], ["vision", "scaffold lift", 0.52, 0.42]]],
      ["struts-excavator.jpg", "09:30 · Aushub unter Steifen", [["mic", "„Aushub dritte Lage halb fertig“", H.blue]], [["vision", "pipe → Steife", 0.30, 0.12], ["vision", "excavator ×2", 0.42, 0.55]]],
      ["struts-haul.jpg", "09:45 · Abfuhr", [], [["vision", "excavator", 0.40, 0.48], ["vision", "dump trailer", 0.60, 0.60]]],
    ];
    for (let i = 0; i < frames.length; i++) {
      const [f, cap, voice, det] = frames[i];
      const x = M + i * (fw + gap);
      s.addImage({ path: FR + f, x, y: fy, w: fw, h: fh, altText: cap });
      // detection chips (dashed violet = vision proposes)
      det.forEach(([, label, fx, fy2]) => {
        const cw = Math.min(fw - 0.2, 0.25 + label.length * 0.085);
        const cx = Math.min(x + fx * fw, x + fw - cw - 0.08);
        s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx, y: fy + fy2 * fh, w: cw, h: 0.3, rectRadius: 0.06,
          fill: { color: H.violetTint, transparency: 10 }, line: { color: H.violet, width: 1.25, dashType: "dash" } });
        txt(s, label, { x: cx, y: fy + fy2 * fh, w: cw, h: 0.3, fontSize: 10, bold: true, color: "6D28D9", align: "center", valign: "middle" });
      });
      // voice chip
      voice.forEach(([, q]) => {
        s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.1, y: fy + fh - 1.25, w: fw - 0.2, h: 0.55, rectRadius: 0.08,
          fill: { color: H.blue }, line: { type: "none" } });
        txt(s, q, { x: x + 0.2, y: fy + fh - 1.25, w: fw - 0.4, h: 0.55, fontSize: 11, bold: true, color: H.white, valign: "middle" });
      });
      // caption band
      s.addShape(pres.shapes.RECTANGLE, { x, y: fy + fh - 0.6, w: fw, h: 0.6, fill: { color: H.dark, transparency: 15 }, line: { type: "none" } });
      txt(s, cap, { x: x + 0.12, y: fy + fh - 0.6, w: fw - 0.24, h: 0.6, fontSize: 11, bold: true, color: H.white, valign: "middle" });
    }
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 6.55, w: 0.3, h: 0.22, rectRadius: 0.05, fill: { color: H.violetTint }, line: { color: H.violet, dashType: "dash" } });
    txt(s, "Camera detection, proposal only", { x: M + 0.4, y: 6.5, w: 3.2, h: 0.32, fontSize: 11, color: H.grey4, valign: "middle" });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M + 3.7, y: 6.55, w: 0.3, h: 0.22, rectRadius: 0.05, fill: { color: H.blue }, line: { type: "none" } });
    txt(s, "Site manager's voice, confirms", { x: M + 4.1, y: 6.5, w: 3.4, h: 0.32, fontSize: 11, color: H.grey4, valign: "middle" });
    txt(s, "Footage: own phone recordings. Overlays show the classes Tagwerk's vision stage looks for.", { x: 7.6, y: 6.5, w: 5.0, h: 0.32, fontSize: 9, color: "71717A", align: "right", valign: "middle" });
    s.addNotes("This is a real deep excavation we filmed: pile wall, steel struts, two excavators, a crane moving scaffolding, and standing water on the wall crest. Only the site manager's words, not the camera, turn this into confirmed facts. The real audio says the only problem was the water. That one sentence is what the next slide follows.");
  }

  // ================= 4c. Footage to schedule and GAEB =================
  {
    const s = content("Solution", "How the engine connects it", "Vom Video zu Terminplan und LV");
    const cols = [
      ["SIGNAL", 3.1], ["BAUTEIL / ZONE", 2.0], ["P6-VORGANG", 2.2], ["GAEB-POSITION", 2.55], ["WIRKUNG", 1.6],
    ];
    const cg = 0.1;
    let cx = M; const colX = [];
    cols.forEach(([h, w]) => { colX.push(cx); txt(s, h, { x: cx, y: 1.7, w, h: 0.3, fontSize: 11, bold: true, color: H.muted, charSpacing: 1 }); cx += w + cg; });
    const rows = [
      ["struts-excavator.jpg", "excavator ×2, pipe → Steife", "„Aushub dritte Lage halb fertig“", "Baugrube BA 3\nLage 3", "B2030\nAushub Lage 3", "01.02.0030\nAushub Baugrube BK 3–5 · m³", "Ist 50 %", H.green, H.greenTint],
      ["struts-haul.jpg", "dump trailer, excavator", "", "Baugrube BA 3\nAbfuhr", "B2030\nAushub Lage 3", "01.02.0040\nBoden laden, abfahren · m³", "Fuhren fürs Aufmaß", H.ink, H.surface],
      ["crane-lift.jpg", "crane, scaffold lift", "", "Achse 12\nArbeitsgerüst", "B2050\nGerüst umsetzen", "03.01.0020\nArbeitsgerüst umsetzen · St", "Vorschlag", H.violet, H.violetTint],
      ["walk-wall.jpg", "Foto: Wasser an der Wand", "„… das Einzige war das Wasser“", "Bohrpfahlwand\nNord", "B2040 Wasserhaltung\n→ B2060 Sohle", "01.04.0010\nWasserhaltung betreiben · h", "Verzug + Anzeige", H.red, H.redTint],
    ];
    const rh = 1.08, ry0 = 2.05;
    for (let i = 0; i < rows.length; i++) {
      const r = rows[i], y = ry0 + i * (rh + 0.1);
      card(s, M, y, W - 2 * M, rh, { fill: i === 3 ? "FFF7F7" : H.white, line: i === 3 ? "FECACA" : H.border });
      // thumb (cropped square from vertical frame)
      s.addImage({ path: FR + r[0].replace(".jpg", "-sq.jpg"), x: colX[0] + 0.12, y: y + 0.12, w: 0.84, h: 0.84 });
      txt(s, [{ text: "◇ " + r[1], options: { color: "6D28D9", bold: true, breakLine: !!r[2] } },
        ...(r[2] ? [{ text: r[2], options: { color: H.blue, bold: true } }] : [])],
        { x: colX[0] + 1.08, y: y + 0.08, w: cols[0][1] - 1.15, h: rh - 0.16, fontSize: 11, valign: "middle" });
      [3, 4, 5].forEach((k, j) => {
        const [a, b] = r[k].split("\n");
        txt(s, [{ text: a, options: { bold: true, breakLine: true } }, { text: b, options: { color: H.muted } }],
          { x: colX[j + 1], y: y + 0.08, w: cols[j + 1][1], h: rh - 0.16, fontSize: 12, valign: "middle" });
      });
      const ew = cols[4][1] - 0.15;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: colX[4], y: y + rh / 2 - 0.22, w: ew, h: 0.44, rectRadius: 0.1,
        fill: { color: r[8] }, line: { color: r[7], width: 1, dashType: r[7] === H.violet ? "dash" : undefined } });
      txt(s, r[6], { x: colX[4], y: y + rh / 2 - 0.22, w: ew, h: 0.44, fontSize: 11, bold: true, color: r[7], align: "center", valign: "middle" });
    }
    txt(s, "Example LV positions and activity ids for this site. Real values come from the site's own GAEB X83 and P6 XML on import.",
      { x: M, y: 6.75, w: 9, h: 0.25, fontSize: 9, color: H.muted });
    s.addNotes("Each row is one piece of evidence from the clips. Camera detections land as proposals on an element; the site manager's sentence confirms progress on the excavation, which updates the P6 activity and the quantity against the GAEB position for the Aufmaß. The water remark becomes an event on the dewatering activity, shifts the slab successor, and that is the delay that gets a notice draft.");
  }

  // ================= 5. Demo =================
  {
    const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Solution" });
    chip(s, "●  LIVE DEMO", M, 0.85, 1.8, H.white, H.blue);
    txt(s, "Ein Tag auf der Baustelle", { x: M, y: 1.6, w: 11, h: 1.0, fontSize: 54, bold: true, color: H.white });
    txt(s, "A day in the life of a site manager: Hörsaal-Sanierung, Thursday 26.11.2026",
      { x: M, y: 2.65, w: 11, h: 0.4, fontSize: 18, color: H.grey4 });
    const beats = [
      ["07:15", "Rundgang", "Film + talk on the phone"],
      ["07:20", "Live-Graph", "Changes with quotes appear"],
      ["10:30", "Absence", "Forecast moves 30.11. → 01.12."],
      ["16:45", "Tagesbericht", "Filled automatically"],
      ["17:00", "Anzeige", "Draft reviewed, PDF out"],
    ];
    const y0 = 4.4, step = (W - 2 * M) / beats.length;
    line(s, M + step / 2, y0, W - M - step / 2, y0, "3F3F46", undefined, 2);
    beats.forEach((b, i) => {
      const cx = M + step * i + step / 2;
      const hot = i === 2 || i === 4;
      s.addShape(pres.shapes.OVAL, { x: cx - 0.13, y: y0 - 0.13, w: 0.26, h: 0.26, fill: { color: hot ? H.blue : "52525B" }, line: { type: "none" } });
      txt(s, b[0], { x: cx - 1.2, y: 3.75, w: 2.4, h: 0.4, fontSize: 18, bold: true, color: H.white, align: "center" });
      txt(s, b[1], { x: cx - 1.2, y: 4.7, w: 2.4, h: 0.35, fontSize: 15, bold: true, color: H.white, align: "center" });
      txt(s, b[2], { x: cx - 1.2, y: 5.05, w: 2.4, h: 0.6, fontSize: 12, color: H.grey4, align: "center", valign: "top" });
    });
    txt(s, "Fallback: cached replay (no GPU, no network)", { x: M, y: 6.6, w: 8, h: 0.3, fontSize: 11, color: "71717A" });
    s.addNotes("Switch to the browser. Follow docs/DEMO.md 3-Minuten-Demo: recording under 'Aufnahmen des Tages', changes with quotes, 'zwei Mann vom Trockenbau sind krank' moves the forecast, red delay in the Gantt, open the Tagesbericht, generate the Behinderungsanzeige draft, approve, export PDF. Fallback: replay uw-video or cap-e2e-2.");
  }

  // ================= 6. How it works =================
  pres.addSection({ title: "How it works" });
  {
    const s = content("How it works", "How it works", "Vom Satz zum Bauteil");
    const st = [
      [L.LuSmartphone, "Upload", "Video, Foto, Audio, Notiz"],
      [L.LuAudioLines, "Speech", "Whisper int8, DE/NL/EN"],
      [L.LuScanEye, "Vision", "YOLO11, YOLO-World, ArUco"],
      [L.LuCloudSun, "Context", "Wetter, Kalender"],
      [L.LuBrainCircuit, "Structuring", "Claude tool schema or rules"],
      [L.LuDatabase, "Project state", "Neo4j graph, GAEB, P6"],
      [L.LuLayoutDashboard, "Outputs", "Dashboard, Bericht, Anzeige"],
    ];
    const n = st.length, gap = 0.22, bw = (W - 2 * M - gap * (n - 1)) / n, y = 2.2;
    for (let i = 0; i < n; i++) {
      const x = M + i * (bw + gap);
      const hot = i === 4;
      card(s, x, y, bw, 2.4, { fill: hot ? H.blueTint : H.white, line: hot ? H.blue : H.border });
      await iconCircle(s, st[i][0], x + bw / 2 - 0.35, y + 0.3, 0.7, hot ? H.blue : H.surface, hot ? H.white : H.ink);
      txt(s, st[i][1], { x: x + 0.08, y: y + 1.15, w: bw - 0.16, h: 0.4, fontSize: 15, bold: true, align: "center" });
      txt(s, st[i][2], { x: x + 0.1, y: y + 1.55, w: bw - 0.2, h: 0.7, fontSize: 12, color: H.muted, align: "center", valign: "top" });
      if (i < n - 1) arrow(s, x + bw + 0.02, y + 0.65, x + bw + gap - 0.02, y + 0.65, H.grey4);
    }
    const facts = [
      [L.LuCpu, "One laptop GPU", "Runs on a GTX 1060. No cloud needed."],
      [L.LuWifiOff, "Works offline", "German keyword rules when no LLM is available."],
      [L.LuRotateCcw, "Replayable", "Every stage cached; any capture replays exactly."],
    ];
    for (let i = 0; i < 3; i++) {
      const x = M + i * 4.0;
      s.addImage({ data: await icon(facts[i][0], H.blue), x, y: 5.15, w: 0.42, h: 0.42 });
      txt(s, facts[i][1], { x: x + 0.6, y: 5.08, w: 3.2, h: 0.35, fontSize: 16, bold: true });
      txt(s, facts[i][2], { x: x + 0.6, y: 5.45, w: 3.2, h: 0.6, fontSize: 13, color: H.muted, valign: "top" });
    }
    s.addNotes("Pipeline from phone to graph. Stress: Claude is optional, the rule fallback works offline, and every capture can be replayed without GPU or network.");
  }

  // ================= 7. Trust =================
  {
    const s = content("How it works", "Human in the loop", "Beweis statt Behauptung");
    const rules = [
      [L.LuMic, "Voice confirms, vision only proposes", "A camera detection becomes a dashed proposal. Only the site manager's words or a tap change a state.", H.blue, H.blueTint],
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
    // mini graph
    card(s, 7.45, 1.95, 5.13, 4.65, { fill: "FAFAFA" });
    const N = {
      cap: [10.0, 2.75, "Aufnahme 07:15", H.blue, H.blueTint, H.blue],
      el: [8.6, 4.0, "Stuhlreihe A", H.green, H.greenTint, H.green],
      act: [10.0, 5.25, "A1080 Bestuhlung", H.ink, H.white, H.ink],
      boq: [11.5, 4.0, "GAEB 02.05.0010", H.ink, H.white, H.ink],
      ev: [11.75, 2.75, "2× krank", H.red, H.redTint, H.red],
      prop: [8.25, 2.75, "Vorschlag", H.violet, H.violetTint, H.violet],
    };
    const E = [["cap", "el"], ["el", "act"], ["el", "boq"], ["boq", "act"], ["cap", "ev"], ["ev", "act"], ["prop", "el"]];
    E.forEach(([a, b]) => line(s, N[a][0], N[a][1], N[b][0], N[b][1], b === "el" && a === "prop" ? H.violet : "C4C4C4",
      a === "prop" ? "dash" : undefined));
    Object.entries(N).forEach(([k, n]) => {
      const w = 1.45, h = 0.5;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: n[0] - w / 2, y: n[1] - h / 2, w, h, rectRadius: 0.25,
        fill: { color: n[4] }, line: { color: n[5], width: 1.25, dashType: k === "prop" ? "dash" : undefined } });
      txt(s, n[2], { x: n[0] - w / 2, y: n[1] - h / 2, w, h, fontSize: 11, bold: true, color: n[3], align: "center", valign: "middle" });
    });
    txt(s, "Dashed = seen by camera only, waiting for confirmation", { x: 7.7, y: 6.1, w: 4.7, h: 0.3, fontSize: 10, color: H.muted });
    s.addNotes("This answers the hallucination worry. The LLM cannot claim voice evidence without a matching quote (enforce_evidence). Vision is weak on large surfaces, which is exactly why it only proposes.");
  }

  // ================= 8. Deviation =================
  pres.addSection({ title: "Impact" });
  {
    const s = content("Impact", "Deviation detection", "Abweichung erkannt, bevor sie teuer wird");
    // Gantt: days 23.11 - 02.12 (10 days)
    const gx = M + 2.4, gw = 5.55, gy = 2.25, days = ["23", "24", "25", "26", "27", "28", "29", "30", "01", "02"];
    const dw = gw / days.length;
    days.forEach((d, i) => {
      const we = i === 5 || i === 6;
      if (we) s.addShape(pres.shapes.RECTANGLE, { x: gx + i * dw, y: gy + 0.4, w: dw, h: 3.2, fill: { color: "FAFAFA" }, line: { type: "none" } });
      txt(s, d + ".", { x: gx + i * dw, y: gy, w: dw, h: 0.3, fontSize: 11, color: H.muted, align: "center" });
    });
    const rows = [
      ["A1060", "AV-Technik", 0, 3, null, null, H.green],
      ["A1065", "Bühne", 0, 0, null, null, H.green],
      ["A1080", "Bestuhlung neu", 0, 3, 3, 8, H.amber],
      ["A1090", "Abnahme", 3, 4, 8, 9, H.ink],
    ];
    rows.forEach((r, i) => {
      const y = gy + 0.55 + i * 0.75;
      txt(s, r[0], { x: M, y, w: 0.8, h: 0.45, fontSize: 12, bold: true, color: H.muted, valign: "middle" });
      txt(s, r[1], { x: M + 0.8, y, w: 1.55, h: 0.45, fontSize: 13, bold: true, valign: "middle" });
      if (r[3] > r[2]) s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: gx + r[2] * dw + 0.03, y: y + 0.08, w: (r[3] - r[2]) * dw - 0.06, h: 0.3,
        rectRadius: 0.06, fill: { color: i < 2 ? H.greenTint : H.surface }, line: { color: i < 2 ? H.green : "C4C4C4", width: 1 } });
      else txt(s, "fertig", { x: gx + 0.05, y, w: 1, h: 0.45, fontSize: 11, color: H.green, valign: "middle" });
      if (r[4] !== null) s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: gx + r[4] * dw + 0.03, y: y + 0.08, w: (r[5] - r[4]) * dw - 0.06, h: 0.3,
        rectRadius: 0.06, fill: { color: H.redTint }, line: { color: H.red, width: 1.25 } });
    });
    // today line (26.11 = index 3)
    line(s, gx + 3 * dw, gy + 0.35, gx + 3 * dw, gy + 3.65, H.blue, undefined, 2);
    txt(s, "heute 26.11.", { x: gx + 3 * dw - 0.6, y: gy + 3.7, w: 1.2, h: 0.3, fontSize: 11, bold: true, color: H.blue, align: "center" });
    // annotation
    card(s, M, 6.0, 7.85, 0.6, { fill: H.redTint, line: H.redTint });
    s.addImage({ data: await icon(L.LuUsers, H.red), x: M + 0.2, y: 6.13, w: 0.34, h: 0.34 });
    txt(s, "„Zwei Mann vom Trockenbau sind krank“  →  crew 3 → 1 for 3 working days, Abnahme moves with it",
      { x: M + 0.7, y: 6.0, w: 7.05, h: 0.6, fontSize: 13, bold: true, color: H.red, valign: "middle" });
    // KPIs
    const k = [
      ["01.12.", "Prognose-Ende", "was 30.11.", H.red],
      ["+1 AT", "Verzug Abnahme", "projection from today's evidence", H.red],
      ["34,4 %", "Ist A1080", "up from 28,9 % after the walk", H.ink],
      ["12,6 s", "Reaktionszeit", "voice note to new forecast, incl. cold start", H.ink],
    ];
    k.forEach((kk, i) => {
      const x = 9.1 + (i % 2) * 1.8, y = 2.25 + Math.floor(i / 2) * 1.95;
      card(s, x, y, 1.68, 1.8);
      txt(s, kk[0], { x: x + 0.15, y: y + 0.15, w: 1.45, h: 0.6, fontSize: 26, bold: true, color: kk[3] });
      txt(s, kk[1], { x: x + 0.15, y: y + 0.8, w: 1.45, h: 0.35, fontSize: 12, bold: true });
      txt(s, kk[2], { x: x + 0.15, y: y + 1.13, w: 1.45, h: 0.55, fontSize: 10, color: H.muted, valign: "top" });
    });
    s.addNotes("Forecast: remaining work simulated day by day with planned crew minus that day's absences; finish-to-start successors shift. Numbers are from the rehearsed end-to-end run; confirm on a fresh reset before the pitch.");
  }

  // ================= 9. Notice =================
  {
    const s = content("Impact", "Correspondence", "Vom Verzug zur Anzeige");
    // left: report section
    card(s, M, 1.9, 5.1, 4.25, { fill: H.surface, line: H.surface });
    txt(s, "TAGESBERICHT 26.11.2026", { x: M + 0.3, y: 2.1, w: 4.5, h: 0.3, fontSize: 11, bold: true, color: H.muted, charSpacing: 1 });
    txt(s, "5. Behinderungen / Verzug", { x: M + 0.3, y: 2.45, w: 4.5, h: 0.4, fontSize: 17, bold: true });
    const f = [["Vorgang", "A1080 Bestuhlung neu"], ["Ursache", "2 AK Trockenbau krank"], ["Seit", "26.11.2026, 10:30"],
      ["Auswirkung", "+1 AT, Abnahme 01.12."], ["Beleg", "„Zwei Mann vom Trockenbau sind krank.“"]];
    f.forEach((r, i) => {
      const y = 3.05 + i * 0.58;
      txt(s, r[0], { x: M + 0.3, y, w: 1.3, h: 0.45, fontSize: 12, color: H.muted, valign: "middle" });
      txt(s, r[1], { x: M + 1.6, y, w: 3.3, h: 0.45, fontSize: 13, bold: true, valign: "middle", color: r[0] === "Auswirkung" ? H.red : H.ink });
    });
    // arrow
    await iconCircle(s, L.LuArrowRight, 6.15, 3.7, 0.6, H.ink, H.white);
    // right: letter
    card(s, 7.05, 1.9, 5.53, 4.25, { lw: 1.25 });
    txt(s, "Behinderungsanzeige", { x: 7.35, y: 2.05, w: 3.6, h: 0.35, fontSize: 16, bold: true });
    txt(s, "gem. § 6 (1) VOB/B", { x: 7.35, y: 2.4, w: 3.6, h: 0.25, fontSize: 11, color: H.muted });
    chip(s, "ENTWURF", 11.25, 2.1, 1.1, "92400E", H.amberTint);
    const lines = ["Bauvorhaben: Hörsaal-Sanierung", "Behindernder Umstand: Personalausfall Trockenbau",
      "Betroffene Leistung: Bestuhlung neu (A1080)", "Voraussichtliche Auswirkung: +1 Arbeitstag"];
    lines.forEach((l, i) => txt(s, l, { x: 7.35, y: 2.7 + i * 0.42, w: 5, h: 0.38, fontSize: 13 }));
    for (let i = 0; i < 2; i++) s.addShape(pres.shapes.RECTANGLE, { x: 7.35, y: 4.5 + i * 0.25, w: i ? 3.2 : 4.8, h: 0.1, fill: { color: H.border }, line: { type: "none" } });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.35, y: 5.3, w: 1.7, h: 0.5, rectRadius: 0.08, fill: { color: H.white }, line: { color: H.border } });
    txt(s, "Bearbeiten", { x: 7.35, y: 5.3, w: 1.7, h: 0.5, fontSize: 13, bold: true, align: "center", valign: "middle" });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 9.2, y: 5.3, w: 2.4, h: 0.5, rectRadius: 0.08, fill: { color: H.ink }, line: { type: "none" } });
    txt(s, "Freigeben & PDF", { x: 9.2, y: 5.3, w: 2.4, h: 0.5, fontSize: 13, bold: true, color: H.white, align: "center", valign: "middle" });
    txt(s, "Entwurfsunterstützung, keine Rechtsberatung. Prüfung und Versand durch die Bauleitung.",
      { x: M, y: 6.35, w: 11.8, h: 0.35, fontSize: 11, italic: true, color: H.muted });
    s.addNotes("The fields a §6 notice needs are exactly what Tagwerk already stores: circumstance, since when, affected works, expected schedule effect, plus the original quote as evidence. The site manager edits and approves; we draft, we do not give legal advice.");
  }

  // ================= 10. Challenge fit =================
  {
    const s = content("Impact", "Challenge B", "Challenge B: abgedeckt");
    const items = [
      ["Voice / text capture on mobile", "Phone browser upload, Whisper DE/NL/EN"],
      ["Daily report analysis vs plan", "Ist/Soll, SPI, forecast with absences"],
      ["Notice drafts from keywords", "Behinderungs-, Mehrkosten-, Bedenkenanzeige"],
      ["Structured summaries", "Events: absence, delay, defect, delivery"],
      ["Correspondence on deviation", "Delay detected → draft proposed"],
      ["Human in the loop", "Vision proposes, voice confirms, manager signs"],
      ["PDF export", "A4 Tagesbericht and notice drafts"],
      ["“A day in the life” demo", "Rehearsed 3-minute run with replay fallback"],
    ];
    for (let i = 0; i < items.length; i++) {
      const col = i % 2, row = Math.floor(i / 2);
      const x = M + col * 6.0, y = 1.95 + row * 1.15;
      card(s, x, y, 5.8, 0.98);
      await iconCircle(s, L.LuCheck, x + 0.2, y + 0.2, 0.58, H.greenTint, H.green);
      txt(s, items[i][0], { x: x + 0.98, y: y + 0.14, w: 4.7, h: 0.38, fontSize: 15, bold: true });
      txt(s, items[i][1], { x: x + 0.98, y: y + 0.52, w: 4.7, h: 0.32, fontSize: 12, color: H.muted });
    }
    s.addNotes("Walk the checklist quickly; the demo already showed most of it.");
  }

  // ================= 11. Positioning =================
  pres.addSection({ title: "Market" });
  {
    const s = content("Market", "Positioning", "Sprache, verknüpft mit Vertrag und Terminplan");
    const px = M + 0.5, py = 1.95, pw = 6.6, ph = 4.4;
    card(s, px, py, pw, ph, { fill: "FAFAFA", line: H.border });
    line(s, px + pw / 2, py, px + pw / 2, py + ph, H.border);
    line(s, px, py + ph / 2, px + pw, py + ph / 2, H.border);
    txt(s, "Capture effort  →  passive (talk & film)", { x: px, y: py + ph + 0.08, w: pw, h: 0.3, fontSize: 11, color: H.muted, align: "right" });
    txt(s, "Link to contract & schedule  →", { x: px - 0.3 - 2.2, y: py + ph / 2 - 0.15, w: 4.4, h: 0.3, fontSize: 11, color: H.muted, rotate: 270,
      align: "center" });
    const dots = [
      ["Fieldwire", 0.18, 0.2], ["Procore Daily Log", 0.25, 0.32], ["Primavera P6", 0.18, 0.8],
      ["Capmo KI", 0.72, 0.28], ["PlanRadar", 0.62, 0.18], ["Buildots / Doxel*", 0.78, 0.64],
    ];
    dots.forEach(([n, fx, fy]) => {
      const cx = px + fx * pw, cy = py + (1 - fy) * ph;
      s.addShape(pres.shapes.OVAL, { x: cx - 0.09, y: cy - 0.09, w: 0.18, h: 0.18, fill: { color: H.grey4 }, line: { type: "none" } });
      txt(s, n, { x: cx + 0.15, y: cy - 0.17, w: 2, h: 0.34, fontSize: 12, color: H.muted, valign: "middle" });
    });
    const tx = px + 0.86 * pw, ty = py + (1 - 0.88) * ph;
    s.addShape(pres.shapes.OVAL, { x: tx - 0.17, y: ty - 0.17, w: 0.34, h: 0.34, fill: { color: H.blue }, line: { color: H.white, width: 2 } });
    txt(s, "Tagwerk", { x: tx - 1.6, y: ty - 0.18, w: 1.35, h: 0.36, fontSize: 15, bold: true, color: H.blue, align: "right", valign: "middle" });
    txt(s, "* needs BIM model + camera hardware", { x: px, y: py + ph + 0.4, w: 4, h: 0.3, fontSize: 10, color: H.muted });
    // proof strip
    const proof = [
      ["2.082", "BIM elements in a real open dataset (Schependomlaan), 100 tasks"],
      ["4", "export formats: P6 XML, GAEB X83/X84, Outlook .ics, PDF"],
      ["0", "BIM or extra hardware required: a phone and a laptop"],
    ];
    proof.forEach((p, i) => {
      const y = 1.95 + i * 1.5;
      txt(s, p[0], { x: 8.35, y, w: 4.2, h: 0.7, fontSize: 40, bold: true, color: i === 0 ? H.blue : H.ink });
      txt(s, p[1], { x: 8.35, y: y + 0.72, w: 4.2, h: 0.6, fontSize: 13, color: H.muted, valign: "top" });
    });
    txt(s, "Positions based on public vendor information, Nov 2026. Schependomlaan: CC BY 4.0, academic use.",
      { x: 8.35, y: 6.45, w: 4.3, h: 0.4, fontSize: 9, color: H.muted });
    s.addNotes("Capmo and PlanRadar turn voice into diary entries and tickets, but free text. Buildots and Doxel link to the model but need BIM and cameras and capture progress, not causes. Tagwerk ties spoken causes to BoQ positions and the schedule.");
  }

  // ================= 12. Close =================
  pres.addSection({ title: "Close" });
  {
    const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Close" });
    logo(s, M, 0.75, 0.7, true);
    txt(s, "Tagwerk: the day's work, documented.", { x: M, y: 1.85, w: 11.5, h: 1.0, fontSize: 44, bold: true, color: H.white });
    txt(s, "The site manager talks while walking the site. By evening the evidence is filed against contract and schedule, the Tagesbericht is written, and the notice the delay needs is drafted for review.",
      { x: M, y: 2.95, w: 10.5, h: 1.1, fontSize: 18, color: "D4D4D4", valign: "top" });
    const nx = [
      [L.LuHardHat, "Pilot", "One Bauleiter, one live site, four weeks"],
      [L.LuHistory, "Audit trail", "Corrections with full history"],
      [L.LuPlug, "Integrations", "P6 import, mail client, Capmo / PlanRadar"],
    ];
    for (let i = 0; i < 3; i++) {
      const x = M + i * 3.95;
      card(s, x, 4.45, 3.7, 1.3, { fill: H.dark2, line: "2E2E33" });
      s.addImage({ data: await icon(nx[i][0], "60A5FA"), x: x + 0.25, y: 4.7, w: 0.38, h: 0.38 });
      txt(s, nx[i][1], { x: x + 0.8, y: 4.66, w: 2.7, h: 0.4, fontSize: 16, bold: true, color: H.white });
      txt(s, nx[i][2], { x: x + 0.8, y: 5.06, w: 2.75, h: 0.55, fontSize: 12, color: H.grey4, valign: "top" });
    }
    txt(s, "Team Tagwerk  ·  github.com/Current-cmd/Tagwerk", { x: M, y: 6.3, w: 7, h: 0.3, fontSize: 13, color: H.grey4 });
    txt(s, "Entwurfsunterstützung, keine Rechtsberatung.", { x: 7.8, y: 6.3, w: 4.8, h: 0.3, fontSize: 11, italic: true, color: "71717A", align: "right" });
    s.addNotes("End on the core sentence. Ask: a pilot site manager. Have the disclaimer visible.");
  }

  const out = require("path").resolve(__dirname, "../../docs/design-brief/Tagwerk-Pitch.pptx");
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log("wrote", out);
})().catch((e) => { console.error(e); process.exit(1); });
