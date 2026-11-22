import React from "react";
import {
  AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, Series, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Easing,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/Geist";
import boxes from "./boxes.json";
import vo from "./vo.json";

const { fontFamily } = loadFont();

// ---------- design tokens (match the app and the deck) ----------
const C = {
  ink: "#0A0A0A", dark: "#141416", dark2: "#1F1F23", line: "#2E2E33", muted: "#737373", border: "#E5E5E5", surface: "#F5F5F5",
  blue: "#2563EB", blueL: "#60A5FA", blueTint: "#DBEAFE", green: "#16A34A", greenTint: "#DCFCE7", amber: "#F59E0B",
  red: "#DC2626", redL: "#F87171", redTint: "#FEE2E2", violet: "#8B5CF6", violetDk: "#6D28D9", violetTint: "#F5F3FF",
  grey4: "#A3A3A3", grey3: "#D4D4D4", white: "#FFFFFF",
};
const KIND: Record<string, string> = { equipment: C.violet, element: C.green, deviation: C.red };
const FPS = 30;
const s = (sec: number) => Math.round(sec * FPS);

// ---------- helpers ----------
const useIn = (delay = 0, damping = 18) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  return spring({ frame: f - delay, fps, config: { damping } });
};
const fadeOut = (f: number, dur: number, len = 12) => interpolate(f, [dur - len, dur], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

const Caption: React.FC<{ de?: string; en: string; from?: number; to?: number }> = ({ de, en, from = 0, to = 99999 }) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [from, from + 8, to - 8, to], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", bottom: 70, left: 0, right: 0, display: "flex", justifyContent: "center", opacity: o }}>
      <div style={{ background: "rgba(0,0,0,0.72)", borderRadius: 14, padding: "14px 28px", maxWidth: 1300, textAlign: "center" }}>
        {de && <div style={{ color: C.grey4, fontStyle: "italic", fontSize: 26, marginBottom: 4 }}>{de}</div>}
        <div style={{ color: C.white, fontSize: 38, fontWeight: 500, lineHeight: 1.25 }}>{en}</div>
      </div>
    </div>
  );
};

const Kicker: React.FC<{ children: React.ReactNode; color?: string }> = ({ children, color = C.blueL }) => (
  <div style={{ color, fontSize: 22, fontWeight: 700, letterSpacing: 4, textTransform: "uppercase" }}>{children}</div>
);

const Logo: React.FC<{ size?: number; inverted?: boolean }> = ({ size = 64, inverted = true }) => (
  <div style={{ width: size, height: size, borderRadius: size * 0.22, background: inverted ? C.white : "#171717", color: inverted ? "#171717" : C.white,
    display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: size * 0.55 }}>T</div>
);

// Annotated frame: raw worker frame + hand-corrected boxes drawn in one after another.
const Annotated: React.FC<{ img: string; keyName: keyof typeof boxes; height: number; delay: number; step?: number; only?: string }> = ({ img, keyName, height, delay, step = 10, only }) => {
  const f = useCurrentFrame();
  const scale = height / 1708, width = 960 * scale;
  const data = (boxes as any)[keyName].boxes as { label: string; bbox: number[]; kind: string }[];
  return (
    <div style={{ position: "relative", width, height, borderRadius: 14, overflow: "hidden", boxShadow: "0 20px 60px rgba(0,0,0,0.45)" }}>
      <Img src={staticFile(img)} style={{ width, height }} />
      {data.filter((b) => !only || b.kind === only).map((b, i) => {
        const p = interpolate(f, [delay + i * step, delay + i * step + 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
        const [x1, y1, x2, y2] = b.bbox.map((v) => v * scale);
        const col = KIND[b.kind];
        return (
          <div key={i} style={{ position: "absolute", left: x1 + 2, top: y1 + 2, width: (x2 - x1 - 4) * p, height: (y2 - y1 - 4) * p, border: `3px solid ${col}`, borderRadius: 4, opacity: p }}>
            <div style={{ position: "absolute", left: -3, top: y1 < 30 ? 2 : -27, background: col, color: C.white, fontSize: 15, fontWeight: 700,
              padding: "3px 7px", borderRadius: 4, whiteSpace: "nowrap" }}>{b.label}</div>
          </div>
        );
      })}
    </div>
  );
};

const Screen: React.FC<{ src: string; zoom?: [number, number]; origin?: string; dur: number }> = ({ src, zoom = [1, 1.08], origin = "50% 50%", dur }) => {
  const f = useCurrentFrame();
  const z = interpolate(f, [0, dur], zoom, { easing: Easing.inOut(Easing.quad) });
  return (
    <div style={{ position: "absolute", inset: 60, borderRadius: 18, overflow: "hidden", boxShadow: "0 30px 80px rgba(0,0,0,0.5)", border: `1px solid ${C.line}` }}>
      <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${z})`, transformOrigin: origin }} />
    </div>
  );
};

// ---------- scenes ----------
const ColdOpen: React.FC = () => {
  const f = useCurrentFrame();
  const vh = 1030, vw = vh * (478 / 850);
  return (
    <AbsoluteFill style={{ background: C.dark }}>
      <OffthreadVideo src={staticFile("opening-baugrube.mp4")} muted style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover", filter: "blur(40px) brightness(0.3)" }} />
      <div style={{ position: "absolute", left: (1920 - vw) / 2, top: 25, width: vw, height: vh, borderRadius: 18, overflow: "hidden", boxShadow: "0 30px 90px rgba(0,0,0,0.6)" }}>
        <OffthreadVideo src={staticFile("opening-baugrube.mp4")} style={{ width: vw, height: vh }} />
      </div>
      <div style={{ position: "absolute", left: 70, top: 60, opacity: interpolate(f, [0, 15, s(5), s(6)], [0, 1, 1, 0], { extrapolateRight: "clamp" }) }}>
        <div style={{ color: C.white, fontSize: 30, fontWeight: 600 }}>Baugrube</div>
        <div style={{ color: C.grey4, fontSize: 24 }}>21.11.2026 · 07:40</div>
      </div>
      <Caption de="Ich weiß nicht, wie tief das ist." en="I don't know how deep that is." from={0} to={s(2.6)} />
      <Caption de="… das Einzige … war das Wasser." en="… the only thing … was the water." from={s(22.9)} to={s(29.5)} />
    </AbsoluteFill>
  );
};

const TitleCard: React.FC<{ a: string; b: string; en?: string; dur: number }> = ({ a, b, en, dur }) => {
  const f = useCurrentFrame(); const p = useIn(0);
  return (
    <AbsoluteFill style={{ background: C.dark, justifyContent: "center", padding: "0 160px", opacity: fadeOut(f, dur) }}>
      <div style={{ color: C.white, fontSize: 96, fontWeight: 700, transform: `translateY(${(1 - p) * 30}px)`, opacity: p }}>{a}</div>
      <div style={{ color: C.blueL, fontSize: 56, fontWeight: 600, marginTop: 12, opacity: useIn(10) }}>{b}</div>
      {en && <div style={{ color: C.grey4, fontSize: 30, marginTop: 24, opacity: useIn(18) }}>{en}</div>}
    </AbsoluteFill>
  );
};

const BoxesScene: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const frames: [string, keyof typeof boxes, string][] = [
    ["raw-crane.jpg", "WA0000_t5", "Kran, Pfahlwand"], ["raw-person.jpg", "WA0000_t10", "Gerüst, Wasser"],
    ["raw-dig.jpg", "WA0003_t2", "Bagger ×2, Steifen"], ["raw-struts.jpg", "WA0003_t8", "Abfuhr, Aushub"],
  ];
  const n = (to: number, at: number) => Math.round(interpolate(f, [at, at + 45], [0, to], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  return (
    <AbsoluteFill style={{ background: C.dark, padding: "60px 70px", opacity: fadeOut(f, dur) }}>
      <Kicker>What Tagwerk sees</Kicker>
      <div style={{ color: C.white, fontSize: 54, fontWeight: 700, marginTop: 6 }}>Was Tagwerk im Video erkennt</div>
      <div style={{ display: "flex", gap: 34, marginTop: 34 }}>
        <div style={{ width: 270, display: "flex", flexDirection: "column", gap: 26 }}>
          {[[n(33, 10), "frames, 1 per second", C.white], [n(17, 40), "objects tagged", C.white], [f > 200 ? 1 : 0, "deviation: Wasser", C.redL]].map(([v, l, c], i) => (
            <div key={i}><div style={{ color: c as string, fontSize: 64, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>{v}</div>
              <div style={{ color: C.grey4, fontSize: 22 }}>{l}</div></div>
          ))}
          <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 12 }}>
            {[["Geräte & Personen", C.violet], ["Bauteile im LV", C.green], ["Abweichung", C.red]].map(([l, c]) => (
              <div key={l} style={{ display: "flex", alignItems: "center", gap: 12, color: C.grey3, fontSize: 22 }}>
                <div style={{ width: 20, height: 20, border: `3px solid ${c}`, borderRadius: 4 }} />{l}</div>
            ))}
          </div>
        </div>
        {frames.map(([img, k, cap], i) => (
          <div key={k} style={{ opacity: useIn(i * 8), transform: `translateY(${(1 - useIn(i * 8)) * 40}px)` }}>
            <Annotated img={img} keyName={k} height={600} delay={30 + i * 45} />
            <div style={{ color: C.grey3, fontSize: 22, fontWeight: 600, textAlign: "center", marginTop: 12 }}>{cap}</div>
          </div>
        ))}
      </div>
      <Caption en="Every second, Tagwerk looks at a frame: equipment and people, the building elements in the contract, and one thing that shouldn't be there." from={20} to={dur - 10} />
    </AbsoluteFill>
  );
};

const WaterZoom: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const z = interpolate(f, [0, dur], [1, 2.1], { easing: Easing.inOut(Easing.cubic) });
  const pulse = 0.6 + 0.4 * Math.sin(f / 5);
  return (
    <AbsoluteFill style={{ background: C.dark, alignItems: "center", justifyContent: "center", opacity: fadeOut(f, dur) }}>
      <div style={{ transform: `scale(${z})`, transformOrigin: "62% 84%" }}>
        <div style={{ position: "relative" }}>
          <Annotated img="raw-person.jpg" keyName="WA0000_t10" height={1000} delay={-100} only="deviation" />
          <div style={{ position: "absolute", left: 530 * (1000 / 1708) - 10, top: 1335 * (1000 / 1708) - 10, width: 235 * (1000 / 1708) + 20, height: 190 * (1000 / 1708) + 20,
            borderRadius: 10, boxShadow: `0 0 ${30 * pulse}px ${C.red}` }} />
        </div>
      </div>
      <Caption en="Water on the pile wall. The camera sees it, but can't judge it." from={10} to={dur - 6} />
    </AbsoluteFill>
  );
};

const VOICE = "Baugrube Abschnitt drei. Aushub dritte Lage unter der zweiten Steifenlage zur Hälfte fertig, zwei Bagger, ein Traktor mit Mulde. Gerüst an Achse zwölf umgesetzt. An der Bohrpfahlwand Nord steht Wasser, die Wasserhaltung reicht nicht.";
const VoiceNote: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const words = VOICE.split(" ");
  const shown = Math.floor(interpolate(f, [20, dur - 50], [0, words.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  return (
    <AbsoluteFill style={{ background: C.dark, padding: "70px 90px", opacity: fadeOut(f, dur) }}>
      <Kicker>What Tagwerk hears</Kicker>
      <div style={{ color: C.white, fontSize: 54, fontWeight: 700, marginTop: 6 }}>15 Sekunden Sprachnotiz nach dem Rundgang</div>
      <div style={{ display: "flex", gap: 90, marginTop: 50, alignItems: "flex-start" }}>
        <div style={{ width: 360, height: 700, borderRadius: 54, background: "#000", padding: 14, boxShadow: "0 30px 80px rgba(0,0,0,0.6)" }}>
          <div style={{ width: "100%", height: "100%", borderRadius: 42, background: C.dark2, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 40 }}>
            <div style={{ width: 130, height: 130, borderRadius: 65, background: C.blue, display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: `0 0 0 ${10 + 8 * Math.sin(f / 6)}px rgba(37,99,235,0.25)` }}>
              <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round"><rect x="9" y="2" width="6" height="12" rx="3" /><path d="M5 10v2a7 7 0 0 0 14 0v-2" /><path d="M12 19v3" /></svg>
            </div>
            <div style={{ display: "flex", gap: 7, alignItems: "center", height: 90 }}>
              {Array.from({ length: 14 }).map((_, i) => (
                <div key={i} style={{ width: 9, borderRadius: 5, background: C.blueL, height: 18 + 60 * Math.abs(Math.sin(f / 4 + i * 0.9)) * (f < dur - 50 ? 1 : 0.1) }} />
              ))}
            </div>
            <div style={{ color: C.grey3, fontSize: 22, fontVariantNumeric: "tabular-nums" }}>0:{String(Math.min(15, Math.floor(f / FPS))).padStart(2, "0")} · Upload</div>
          </div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ color: C.grey4, fontSize: 22, fontWeight: 700, letterSpacing: 3 }}>TRANSKRIPT (WHISPER, DE)</div>
          <div style={{ color: C.white, fontSize: 40, lineHeight: 1.45, marginTop: 20, fontStyle: "italic" }}>
            „{words.slice(0, shown).join(" ")}{shown < words.length ? "▍" : "“"}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const FACTS: [string, string, string, string, string][] = [
  ["Fortschritt", "Aushub Lage 3 → 50 %", "bestätigt: Bagger ×2, Aushub", C.green, C.greenTint],
  ["Leistung", "Boden laden, abfahren", "bestätigt: Traktor mit Mulde", C.green, C.greenTint],
  ["Fortschritt", "Gerüst Achse 12 umgesetzt", "bestätigt: Kran, Gerüst am Haken", C.green, C.greenTint],
  ["Behinderung", "Wasser an Bohrpfahlwand Nord", "bestätigt: stehendes Wasser", C.red, C.redTint],
  ["Offen", "Bohrgerät ×2", "kein Satz dazu, bleibt Vorschlag", C.violetDk, C.violetTint],
];
const Facts: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.white, padding: "70px 90px", opacity: fadeOut(f, dur) }}>
      <Kicker color={C.blue}>Structured, linked to the clip</Kicker>
      <div style={{ color: C.ink, fontSize: 54, fontWeight: 700, marginTop: 6 }}>Vier Fakten. Ein offener Vorschlag.</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 18, marginTop: 40, width: 1250 }}>
        {FACTS.map(([k, t, c, col, tint], i) => {
          const p = useIn(12 + i * 14);
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 26, border: `${i === 4 ? 2 : 1}px ${i === 4 ? "dashed" : "solid"} ${i === 4 ? C.violet : C.border}`,
              borderRadius: 14, padding: "18px 26px", background: C.white, opacity: p, transform: `translateX(${(1 - p) * 80}px)` }}>
              <div style={{ width: 58, height: 58, borderRadius: 29, background: tint, border: `2px solid ${col}` }} />
              <div style={{ width: 200, color: col, fontSize: 20, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase" }}>{k}</div>
              <div style={{ flex: 1, fontSize: 32, fontWeight: 700, color: C.ink }}>{t}</div>
              <div style={{ fontSize: 22, color: C.muted }}>{c}</div>
            </div>
          );
        })}
      </div>
      <Caption en="Each sentence confirms something the camera saw. The piling rigs got no sentence, so they stay a proposal." from={20} to={dur - 6} />
    </AbsoluteFill>
  );
};

const FileIcon: React.FC<{ name: string; tag: string; color: string }> = ({ name, tag, color }) => (
  <div style={{ width: 230, height: 280, background: C.white, borderRadius: 16, border: `1px solid ${C.border}`, boxShadow: "0 18px 40px rgba(0,0,0,0.18)",
    display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 14 }}>
    <div style={{ background: color, color: C.white, fontWeight: 700, fontSize: 24, padding: "6px 14px", borderRadius: 8 }}>{tag}</div>
    <div style={{ fontSize: 22, fontWeight: 600, color: C.ink, textAlign: "center", padding: "0 10px" }}>{name}</div>
  </div>
);

const NoBim: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const fly = (start: number) => interpolate(f, [start, start + 28], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const a = fly(25), b = fly(55);
  const dropped = f > 85;
  const checks = [["10 Vorgänge mit Abhängigkeiten", "P6 XML"], ["15 LV-Positionen mit Mengen und Preisen", "GAEB X83"], ["8 Gewerke, 4 Zonen, 32 Bauteile", "abgeleitet"], ["Basisplan gesetzt", "bereit"]];
  const ready = interpolate(f, [210, 245], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  return (
    <AbsoluteFill style={{ background: C.surface, padding: "70px 90px", opacity: fadeOut(f, dur) }}>
      <Kicker color={C.blue}>Ohne BIM</Kicker>
      <div style={{ color: C.ink, fontSize: 54, fontWeight: 700, marginTop: 6 }}>Terminplan rein. Fertig.</div>
      <div style={{ position: "absolute", left: 90, top: 260, width: 900, height: 600, borderRadius: 24, border: `3px dashed ${dropped ? C.blue : "#C4C4C4"}`,
        background: dropped ? "#EFF6FF" : C.white, display: "flex", alignItems: "center", justifyContent: "center" }}>
        {!dropped && <div style={{ fontSize: 30, color: C.muted }}>Terminplan und LV hierher ziehen</div>}
        {dropped && <div style={{ display: "flex", gap: 30 }}><FileIcon name="Terminplan.xml" tag="P6" color={C.ink} /><FileIcon name="LV.x83" tag="GAEB" color={C.green} /></div>}
      </div>
      {!dropped && <>
        <div style={{ position: "absolute", left: interpolate(a, [0, 1], [1550, 300]), top: interpolate(a, [0, 1], [700, 420]), transform: `rotate(${(1 - a) * 8}deg)` }}><FileIcon name="Terminplan.xml" tag="P6" color={C.ink} /></div>
        <div style={{ position: "absolute", left: interpolate(b, [0, 1], [1650, 560]), top: interpolate(b, [0, 1], [760, 420]), transform: `rotate(${(1 - b) * -8}deg)` }}><FileIcon name="LV.x83" tag="GAEB" color={C.green} /></div>
      </>}
      <div style={{ position: "absolute", left: 1060, top: 300, width: 770, display: "flex", flexDirection: "column", gap: 22 }}>
        {checks.map(([t, src], i) => {
          const p = useIn(95 + i * 22);
          return (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 20, opacity: p, transform: `translateY(${(1 - p) * 20}px)` }}>
              <div style={{ width: 46, height: 46, borderRadius: 23, background: C.greenTint, color: C.green, fontSize: 28, fontWeight: 700, display: "flex", alignItems: "center", justifyContent: "center" }}>✓</div>
              <div style={{ flex: 1, fontSize: 30, fontWeight: 600, color: C.ink }}>{t}</div>
              <div style={{ fontSize: 20, color: C.muted }}>{src}</div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", inset: 0, transform: `translateY(${(1 - ready) * 1080}px)`, background: C.dark }}>
        <Screen src="dashboard.png" zoom={[1, 1.04]} dur={dur} />
        <div style={{ position: "absolute", left: 90, top: 90, background: C.green, color: C.white, fontSize: 26, fontWeight: 700, padding: "10px 20px", borderRadius: 30, opacity: ready }}>Projekt bereit</div>
      </div>
      <Caption en="No BIM model? Drop in the schedule and the bill of quantities. Activities, positions and the baseline are ready." from={20} to={dur - 6} />
    </AbsoluteFill>
  );
};

const WithBim: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const chips: [string, string][] = [["2.082", "Bauteile, jedes einzeln verfolgt"], ["100", "Vorgänge aus dem 4D-Terminplan"], ["Bauteil", "→ Vorgang → Status, live im Modell"]];
  return (
    <AbsoluteFill style={{ background: C.dark, opacity: fadeOut(f, dur) }}>
      <Screen src="bim-schependomlaan.png" zoom={[1.0, 1.35]} origin="18% 75%" dur={dur} />
      <div style={{ position: "absolute", right: 110, top: 130, display: "flex", flexDirection: "column", gap: 18 }}>
        <div style={{ background: C.dark, padding: "14px 22px", borderRadius: 14, opacity: useIn(0) }}><Kicker>Mit BIM</Kicker>
          <div style={{ color: C.white, fontSize: 44, fontWeight: 700 }}>Granular bis zum Bauteil</div></div>
        {chips.map(([a, b], i) => (
          <div key={i} style={{ background: "rgba(20,20,22,0.92)", border: `1px solid ${C.line}`, borderRadius: 14, padding: "16px 22px", width: 470, opacity: useIn(20 + i * 18) }}>
            <div style={{ color: i === 0 ? C.blueL : C.white, fontSize: 40, fontWeight: 700 }}>{a}</div>
            <div style={{ color: C.grey4, fontSize: 22 }}>{b}</div>
          </div>
        ))}
      </div>
      <Caption en="With a BIM model, every element carries its own state. Here: a real open dataset, 2,082 elements." from={20} to={dur - 6} />
    </AbsoluteFill>
  );
};

const ROWS: [string, string, string, string, string, string, string, string][] = [
  ["struts-excavator-sq.jpg", "„Aushub dritte Lage zur Hälfte“", "Baugrube BA 3 · Lage 3", "B2030 Aushub Lage 3", "01.02.0030 Aushub BK 3–5 · m³", "Ist 50 %", C.green, C.greenTint],
  ["struts-haul-sq.jpg", "„ein Traktor mit Mulde“", "Baugrube BA 3 · Abfuhr", "B2030 Aushub Lage 3", "01.02.0040 Boden laden, abfahren", "Aufmaß", C.ink, C.surface],
  ["crane-lift-sq.jpg", "„Gerüst an Achse zwölf umgesetzt“", "Achse 12 · Gerüst", "B2050 Gerüst umsetzen", "03.01.0020 Arbeitsgerüst umsetzen", "Erledigt", C.green, C.greenTint],
  ["walk-wall-sq.jpg", "„Wasser an der Bohrpfahlwand Nord“", "Bohrpfahlwand Nord", "B2040 Wasserhaltung → B2060 Sohle", "01.04.0010 Wasserhaltung betreiben", "Verzug +2 AT", C.red, C.redTint],
];
const Mapping: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const cols = ["SIGNAL", "BAUTEIL / ZONE", "P6-VORGANG", "GAEB-POSITION", "WIRKUNG"];
  const widths = [500, 300, 360, 400, 200];
  return (
    <AbsoluteFill style={{ background: C.white, padding: "70px 90px", opacity: fadeOut(f, dur) }}>
      <Kicker color={C.blue}>How the engine connects it</Kicker>
      <div style={{ color: C.ink, fontSize: 54, fontWeight: 700, marginTop: 6 }}>Vom Video zu Terminplan und LV</div>
      <div style={{ display: "flex", gap: 16, marginTop: 36, color: C.muted, fontSize: 18, fontWeight: 700, letterSpacing: 2 }}>
        {cols.map((c, i) => <div key={c} style={{ width: widths[i] }}>{c}</div>)}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 14 }}>
        {ROWS.map((r, i) => {
          const base = 15 + i * 55;
          const cell = (j: number) => interpolate(f, [base + j * 9, base + j * 9 + 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          const isRed = i === 3;
          return (
            <div key={i} style={{ display: "flex", gap: 16, alignItems: "center", border: `1px solid ${isRed ? "#FECACA" : C.border}`, background: isRed ? "#FFF7F7" : C.white,
              borderRadius: 14, padding: 14, opacity: cell(0) }}>
              <div style={{ width: widths[0] - 14, display: "flex", gap: 16, alignItems: "center" }}>
                <Img src={staticFile(r[0])} style={{ width: 90, height: 90, borderRadius: 8 }} />
                <div style={{ color: C.blue, fontSize: 22, fontWeight: 700 }}>{r[1]}</div>
              </div>
              {[r[2], r[3], r[4]].map((t, j) => (
                <div key={j} style={{ width: widths[j + 1], fontSize: 22, fontWeight: 600, color: C.ink, opacity: cell(j + 1), transform: `translateX(${(1 - cell(j + 1)) * -20}px)` }}>{t}</div>
              ))}
              <div style={{ width: widths[4], opacity: cell(4) }}>
                <div style={{ background: r[7], border: `1px solid ${r[6]}`, color: r[6], fontWeight: 700, fontSize: 20, borderRadius: 10, padding: "10px 12px", textAlign: "center" }}>{r[5]}</div>
              </div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 90, bottom: 26, color: C.muted, fontSize: 16 }}>Example LV positions and activity ids for this site.</div>
      <Caption en="Every fact lands on an element, a schedule activity and a contract position. The water lands on dewatering, and the slab moves." from={30} to={dur - 6} />
    </AbsoluteFill>
  );
};

const Notice: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const lines = ["Bauvorhaben: Baugrube, Abschnitt 3", "Behindernder Umstand: Wasserandrang an der Bohrpfahlwand Nord, Wasserhaltung unzureichend",
    "Seit: 21.11.2026, 07:40", "Betroffen: Aushub Lage 3, Sohle (B2030, B2060)", "Voraussichtliche Auswirkung: +2 Arbeitstage", "Anlage: Video 21.11., 07:40"];
  const clicked = f > dur - 75;
  const cx = interpolate(f, [dur - 120, dur - 80], [1500, 1170], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  const cy = interpolate(f, [dur - 120, dur - 80], [1000, 866], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) });
  return (
    <AbsoluteFill style={{ background: C.surface, alignItems: "center", opacity: fadeOut(f, dur) }}>
      <div style={{ width: 1150, marginTop: 80, background: C.white, borderRadius: 18, border: `1px solid ${C.border}`, padding: "44px 56px", boxShadow: "0 24px 60px rgba(0,0,0,0.12)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div><div style={{ fontSize: 40, fontWeight: 700, color: C.ink }}>Behinderungsanzeige</div>
            <div style={{ fontSize: 22, color: C.muted }}>gem. § 6 (1) VOB/B</div></div>
          <div style={{ background: clicked ? C.greenTint : "#FEF3C7", color: clicked ? C.green : "#92400E", fontWeight: 700, fontSize: 22, padding: "8px 18px", borderRadius: 20 }}>
            {clicked ? "FREIGEGEBEN · PDF" : "ENTWURF"}</div>
        </div>
        <div style={{ marginTop: 28, display: "flex", flexDirection: "column", gap: 14 }}>
          {lines.map((l, i) => <div key={i} style={{ fontSize: 26, color: C.ink, opacity: useIn(10 + i * 10) }}>{l}</div>)}
        </div>
        <div style={{ display: "flex", gap: 18, marginTop: 34 }}>
          <div style={{ border: `1px solid ${C.border}`, borderRadius: 10, padding: "14px 26px", fontSize: 24, fontWeight: 700 }}>Bearbeiten</div>
          <div style={{ background: clicked ? C.green : C.ink, color: C.white, borderRadius: 10, padding: "14px 26px", fontSize: 24, fontWeight: 700, transform: `scale(${clicked && f < dur - 65 ? 0.95 : 1})` }}>Freigeben & PDF</div>
        </div>
      </div>
      <svg style={{ position: "absolute", left: cx, top: cy }} width="34" height="34" viewBox="0 0 24 24"><path d="M3 2l7 19 2.5-7.5L20 11z" fill={C.ink} stroke="white" strokeWidth="1.5" /></svg>
      <div style={{ position: "absolute", bottom: 160, color: C.muted, fontSize: 22, fontStyle: "italic" }}>Entwurfsunterstützung, keine Rechtsberatung. Prüfung und Versand durch die Bauleitung.</div>
      <Caption en="The delay that needs a notice gets a draft, with the video attached. The site manager decides." from={20} to={dur - 6} />
    </AbsoluteFill>
  );
};

const LiveGrab: React.FC<{ src: string; label: string; en: string; zoom: [number, number]; origin: string; dur: number }> = ({ src, label, en, zoom, origin, dur }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.dark, opacity: interpolate(f, [0, 10, dur - 10, dur], [0, 1, 1, 0], { extrapolateRight: "clamp" }) }}>
      <Screen src={src} zoom={zoom} origin={origin} dur={dur} />
      <div style={{ position: "absolute", left: 90, top: 90, display: "flex", gap: 12, alignItems: "center" }}>
        <div style={{ background: C.green, color: C.white, fontSize: 20, fontWeight: 700, padding: "8px 16px", borderRadius: 20 }}>● LIVE</div>
        <div style={{ background: "rgba(20,20,22,0.9)", color: C.white, fontSize: 24, fontWeight: 600, padding: "8px 18px", borderRadius: 20 }}>{label}</div>
      </div>
      <Caption en={en} from={8} to={dur - 8} />
    </AbsoluteFill>
  );
};

const Close: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  const vh = 1080, vw = vh * (478 / 850);
  return (
    <AbsoluteFill style={{ background: C.dark }}>
      <div style={{ position: "absolute", right: 0, top: 0, width: vw, height: vh, overflow: "hidden" }}>
        <Img src={staticFile("walk-wall.jpg")} style={{ width: vw, height: vh, transform: `scale(${1 + f / 900})`, transformOrigin: "50% 80%", filter: "brightness(0.7)" }} />
      </div>
      <div style={{ position: "absolute", left: 120, top: 240, width: 1150 }}>
        <Logo size={80} />
        <div style={{ color: C.white, fontSize: 76, fontWeight: 700, marginTop: 50, opacity: useIn(10) }}>„Das Einzige war das Wasser.“</div>
        <div style={{ color: C.blueL, fontSize: 40, fontWeight: 500, marginTop: 20, opacity: useIn(45) }}>Jetzt steht es im Bautagebuch, im Terminplan und in der Anzeige.</div>
        <div style={{ color: C.grey4, fontSize: 28, marginTop: 14, opacity: useIn(60) }}>Now it's in the site diary, the schedule and the notice.</div>
      </div>
    </AbsoluteFill>
  );
};

const EndCard: React.FC<{ dur: number }> = ({ dur }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.white, alignItems: "center", justifyContent: "center", opacity: interpolate(f, [0, 12], [0, 1]) }}>
      <Logo size={110} inverted={false} />
      <div style={{ fontSize: 64, fontWeight: 700, color: C.ink, marginTop: 36 }}>Tagwerk: the day's work, documented.</div>
      <div style={{ fontSize: 30, color: C.muted, marginTop: 16 }}>Sprache und Video zu Bautagebuch, Terminplan und Anzeige · mit oder ohne BIM</div>
      <div style={{ fontSize: 26, color: C.ink, marginTop: 40 }}>Team Tagwerk · github.com/Current-cmd/Tagwerk</div>
      <div style={{ position: "absolute", bottom: 50, fontSize: 20, color: C.muted, fontStyle: "italic" }}>Entwurfsunterstützung, keine Rechtsberatung.</div>
    </AbsoluteFill>
  );
};

// ---------- timeline ----------
type VoCue = { id: keyof typeof vo; at: number };
const RAW_SCENES: [number, (dur: number) => React.ReactNode, VoCue?][] = [
  [1056, () => <ColdOpen />],
  [s(4), (d) => <TitleCard a="35 Sekunden." b="Was hat Tagwerk daraus gemacht?" en="35 seconds. What did Tagwerk make of it?" dur={d} />, { id: "title35", at: 10 }],
  [s(14), (d) => <BoxesScene dur={d} />, { id: "boxes", at: 20 }],
  [s(5), (d) => <WaterZoom dur={d} />, { id: "water", at: 10 }],
  [s(11), (d) => <VoiceNote dur={d} />, { id: "voicenote", at: 20 }],
  [s(8), (d) => <Facts dur={d} />, { id: "facts", at: 20 }],
  [s(3.5), (d) => <TitleCard a="Mit BIM oder ohne." b="Beides funktioniert." en="With or without a BIM model." dur={d} />, { id: "titlebim", at: 8 }],
  [s(11), (d) => <NoBim dur={d} />, { id: "nobim", at: 20 }],
  [s(9), (d) => <WithBim dur={d} />, { id: "withbim", at: 20 }],
  [s(12), (d) => <Mapping dur={d} />, { id: "mapping", at: 30 }],
  [s(9), (d) => <Notice dur={d} />, { id: "notice", at: 20 }],
  [s(3), (d) => <TitleCard a="Läuft heute schon." b="Live im Demo-Projekt Hörsaal." dur={d} />, { id: "titlelive", at: 6 }],
  [s(6), (d) => <LiveGrab src="dashboard.png" label="Dashboard · Ist/Soll, SPI, Prognose" en="Plan versus actual, SPI and the forecast, from today's evidence." zoom={[1, 1.25]} origin="40% 20%" dur={d} />, { id: "dash", at: 10 }],
  [s(5), (d) => <LiveGrab src="graph.png" label="Live-Graph · GAEB → Vorgang → Zone" en="Every recording linked to positions, activities and zones." zoom={[1.05, 1.3]} origin="45% 55%" dur={d} />, { id: "graph", at: 10 }],
  [s(5.5), (d) => <LiveGrab src="report-delays.png" label="Tagesbericht · Behinderungen / Verzug" en="The daily report writes itself, delays included." zoom={[1, 1.3]} origin="62% 45%" dur={d} />, { id: "report", at: 10 }],
  [s(5), (d) => <LiveGrab src="scan-hackathon.png" label="3D-Scan · was gesagt wurde, im Raum" en="And from a walk-through video, a 3D scan with what was said, where." zoom={[1, 1.15]} origin="45% 50%" dur={d} />, { id: "scan", at: 10 }],
  [s(11), (d) => <Close dur={d} />, { id: "close", at: 10 }],
  [s(7), (d) => <EndCard dur={d} />, { id: "end", at: 15 }],
];
// Each scene is at least as long as its voice-over cue plus a tail (the voice note needs 50 frames for the typing to finish).
const voFrames = (c: VoCue) => Math.ceil(vo[c.id].seconds * FPS);
const SCENES = RAW_SCENES.map(([d, render, cue]) => {
  const tail = cue?.id === "voicenote" ? 50 : 15;
  return { dur: cue ? Math.max(d, cue.at + voFrames(cue) + tail) : d, render, cue };
});
export const TOTAL_FRAMES = SCENES.reduce((a, { dur }) => a + dur, 0);

export const TagwerkDemo: React.FC = () => (
  <AbsoluteFill style={{ fontFamily, background: C.dark }}>
    <Series>
      {SCENES.map(({ dur, render, cue }, i) => (
        <Series.Sequence key={i} durationInFrames={dur}>
          {render(dur)}
          {cue && (
            <Sequence from={cue.at} layout="none">
              <Audio src={staticFile(vo[cue.id].file)} volume={cue.id === "voicenote" ? 0.9 : 1} />
            </Sequence>
          )}
        </Series.Sequence>
      ))}
    </Series>
  </AbsoluteFill>
);
