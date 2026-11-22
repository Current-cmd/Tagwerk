  // ================= 4b. Real site footage =================
  const FR = require("path").resolve(__dirname, "../../docs/design-brief/site-frames") + "/";
  {
    const s = pres.addSlide({ masterName: "DARK", sectionTitle: "Solution" });
    txt(s, "REAL SITE · BAUGRUBE · 21.11.2026", { x: M, y: 0.5, w: 8, h: 0.3, fontSize: 12, bold: true, color: "60A5FA", charSpacing: 2 });
    txt(s, "35 Sekunden Handyvideo. Ein ganzer Bautagebuch-Eintrag.", { x: M, y: 0.82, w: 11.8, h: 0.7, fontSize: 30, bold: true, color: H.white });
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
    const s = content("Solution", "How the engine connects it", "Vom Video zu Terminplan und Leistungsverzeichnis");
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
      s.addImage({ path: FR + r[0], x: colX[0] + 0.12, y: y + 0.12, w: 0.84, h: 0.84,
        sizing: { type: "crop", w: 0.84, h: 0.84, x: 0, y: 0.35 } });
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

