// 2-minute hackathon submission: 0:00-0:30 the problem (real site footage), then the platform, navigated.
// Shot ids and times: pitch/STORYBOARD-2min.md and src/submission-timeline.json.
// Screen recordings come from public/rec/<id>.mp4 (+ .json marks); src/rec-manifest.json (scripts/make-rec-manifest.mjs)
// says which exist. A missing recording renders as a labelled placeholder. The UI is never redrawn: recordings are
// only framed, zoomed, and annotated with boxes and captions.
import React from "react";
import { AbsoluteFill, Audio, Easing, Img, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Geist";
import timeline from "./submission-timeline.json";
import voRaw from "./submission-vo.json";
import manifestRaw from "./rec-manifest.json";

const { fontFamily } = loadFont();
const MONO = 'ui-monospace, "SF Mono", Menlo, monospace';

const C = {
  ink: "#0A0A0A", dark: "#141416", dark2: "#1F1F23", line: "#2E2E33", muted: "#8A8A93", grey4: "#A3A3A3", grey3: "#D4D4D4", white: "#FFFFFF",
  blue: "#2563EB", blueL: "#60A5FA", green: "#16A34A", greenL: "#4ADE80", amber: "#F59E0B", red: "#DC2626", redL: "#F87171", violet: "#8B5CF6", violetL: "#A78BFA",
};
const FPS = 30;
const fr = (sec: number) => Math.round(sec * FPS);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const ease = Easing.bezier(0.22, 1, 0.36, 1);
const easeIO = Easing.inOut(Easing.cubic);

type Rec = { exists: boolean; seconds: number; width: number; height: number; marks: Record<string, number> };
const manifest = manifestRaw as unknown as Record<string, Rec>;
const vo = voRaw as Record<string, { file: string; seconds: number }>;
type Shot = { id: string; start: number; end: number; rec: string | null; title: string };
const SHOTS = timeline.shots as Shot[];
export const SUBMISSION_FRAMES = Math.min(3600, fr(SHOTS[SHOTS.length - 1].end));

// ------------------------------------------------------------------ small helpers

const useIn = (delay = 0, dur = 14) => {
  const f = useCurrentFrame();
  return interpolate(f, [delay, delay + dur], [0, 1], { ...clamp, easing: ease });
};

const Rise: React.FC<{ delay?: number; children: React.ReactNode; style?: React.CSSProperties; dy?: number }> = ({ delay = 0, children, style, dy = 22 }) => {
  const t = useIn(delay);
  return <div style={{ opacity: t, transform: `translateY(${(1 - t) * dy}px)`, ...style }}>{children}</div>;
};

const Kicker: React.FC<{ children: React.ReactNode; color?: string; size?: number }> = ({ children, color = C.blueL, size = 22 }) => (
  <div style={{ color, fontSize: size, fontWeight: 700, letterSpacing: 3.5, textTransform: "uppercase" }}>{children}</div>
);

const Logo: React.FC<{ size?: number }> = ({ size = 64 }) => (
  <div style={{ width: size, height: size, borderRadius: size * 0.22, background: C.white, color: "#171717", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: size * 0.55 }}>T</div>
);

/** Soft cut: each shot fades in from the dark background. */
const Scene: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 6], [0, 1], clamp);
  return <AbsoluteFill style={{ background: C.dark, fontFamily, color: C.white, opacity: o }}>{children}</AbsoluteFill>;
};

/** Lower third: label, divider, one sentence. */
const LowerThird: React.FC<{ label: string; children: React.ReactNode; color?: string; delay?: number }> = ({ label, children, color = C.blueL, delay = 8 }) => {
  const t = useIn(delay);
  return (
    <div style={{ position: "absolute", left: 128, right: 128, bottom: 18, height: 64, display: "flex", alignItems: "center", gap: 22, opacity: t, transform: `translateY(${(1 - t) * 12}px)` }}>
      <div style={{ color, fontSize: 20, fontWeight: 700, letterSpacing: 3, textTransform: "uppercase", whiteSpace: "nowrap" }}>{label}</div>
      <div style={{ width: 2, height: 32, background: C.line }} />
      <div style={{ fontSize: 29, fontWeight: 500, lineHeight: 1.2, whiteSpace: "nowrap" }}>{children}</div>
    </div>
  );
};

// ------------------------------------------------------------------ recordings: timing, camera, highlights

/** A time inside a recording: source seconds, or the name of a mark from <id>.json (with a fallback in source seconds). */
type T = number | [mark: string, fallback: number, offset?: number];
type Cut = { a: T; b: T; dur: number };                       // play source a..b over `dur` seconds of the shot
type Cam = { t: T; x: number; y: number; z: number };         // focal centre (fractions of the recording) and zoom
type Hl = { from: T; to?: T; box: [number, number, number, number]; label?: string; color?: string; below?: boolean };
type RecCfg = { cuts?: Cut[]; cam?: Cam[]; hl?: Hl[] };

function usePlan(recId: string, shotSeconds: number, cfg: RecCfg) {
  const rec = manifest[recId];
  const src = (t: T) => (typeof t === "number" ? t : rec?.marks?.[t[0]] !== undefined ? rec.marks[t[0]] + (t[2] ?? 0) : t[1]);
  const total = rec?.seconds || shotSeconds;
  const cuts = (cfg.cuts ?? [{ a: 0, b: total, dur: shotSeconds }]).map((c) => ({ a: src(c.a), b: Math.min(src(c.b), total), dur: c.dur }));
  let acc = 0;
  const segs = cuts.map((c) => { const s = { ...c, from: fr(acc), frames: fr(c.dur), rate: Math.max(0.1, (c.b - c.a) / c.dur) }; acc += c.dur; return s; });
  /** Source time -> frame within the shot. */
  const at = (t: T) => {
    const s = src(t);
    const seg = segs.find((g) => s >= g.a && s <= g.b) ?? (s < segs[0].a ? segs[0] : segs[segs.length - 1]);
    return Math.round(seg.from + interpolate(s, [seg.a, seg.b], [0, seg.frames], clamp));
  };
  return { rec, segs, at };
}

const Placeholder: React.FC<{ recId: string; title: string; w: number; h: number }> = ({ recId, title, w, h }) => (
  <div style={{ width: w, height: h, background: "repeating-linear-gradient(135deg, #1b1b1f 0 28px, #222228 28px 56px)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: Math.min(18, w / 30), textAlign: "center", padding: 24, boxSizing: "border-box" }}>
    <div style={{ color: C.amber, fontSize: Math.min(40, w / 11), fontWeight: 700, letterSpacing: 4 }}>PLACEHOLDER</div>
    <div style={{ color: C.white, fontFamily: MONO, fontSize: Math.min(30, w / 15) }}>rec/{recId}.mp4</div>
    <div style={{ color: C.grey4, fontSize: Math.min(26, w / 17) }}>recording not delivered yet</div>
    <div style={{ color: C.grey4, fontSize: Math.min(24, w / 18), maxWidth: w * 0.8 }}>{title}</div>
  </div>
);

/** The recording itself (or a placeholder), with camera moves and highlight boxes that follow the zoom. */
const RecLayer: React.FC<{ recId: string; title: string; shotSeconds: number; cfg: RecCfg; w: number; h: number }> = ({ recId, title, shotSeconds, cfg, w, h }) => {
  const f = useCurrentFrame();
  const { rec, segs, at } = usePlan(recId, shotSeconds, cfg);
  if (!rec?.exists) return <Placeholder recId={recId} title={title} w={w} h={h} />;

  const keys = (cfg.cam ?? [{ t: 0, x: 0.5, y: 0.5, z: 1 }]).map((k) => ({ ...k, f: at(k.t) })).sort((p, q) => p.f - q.f);
  for (let i = 1; i < keys.length; i++) if (keys[i].f <= keys[i - 1].f) keys[i].f = keys[i - 1].f + 1;
  const pick = (k: "x" | "y" | "z") => (keys.length === 1 ? keys[0][k] : interpolate(f, keys.map((q) => q.f), keys.map((q) => q[k]), { ...clamp, easing: easeIO }));
  const z = pick("z");
  const tx = Math.min(0, Math.max(w - w * z, w / 2 - pick("x") * w * z));
  const ty = Math.min(0, Math.max(h - h * z, h / 2 - pick("y") * h * z));
  const shotFrames = fr(shotSeconds);

  return (
    <div style={{ width: w, height: h, overflow: "hidden", position: "relative", background: "#fff" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: w, height: h, transformOrigin: "0 0", transform: `translate(${tx}px, ${ty}px) scale(${z})` }}>
        {segs.map((g, i) => (
          <Sequence key={i} from={g.from} durationInFrames={i === segs.length - 1 ? Math.max(1, shotFrames - g.from) : g.frames} layout="none">
            <OffthreadVideo src={staticFile(`rec/${recId}.mp4`)} muted trimBefore={Math.round(g.a * FPS)} playbackRate={g.rate} style={{ position: "absolute", left: 0, top: 0, width: w, height: h, objectFit: "fill" }} />
          </Sequence>
        ))}
        {(cfg.hl ?? []).map((b, i) => {
          const a = at(b.from), e = b.to === undefined ? shotFrames + 99 : at(b.to);
          const t = interpolate(f, [a, a + 10, e - 8, e], [0, 1, 1, 0], { ...clamp, easing: ease });
          if (t <= 0) return null;
          const col = b.color ?? C.blue;
          const bw = 4 / z;
          return (
            <div key={i} style={{ position: "absolute", left: b.box[0] * w, top: b.box[1] * h, width: b.box[2] * w, height: b.box[3] * h, border: `${bw}px solid ${col}`, borderRadius: 10 / z, boxShadow: `0 0 0 ${5 / z}px ${col}33`, opacity: t, transform: `scale(${1.06 - 0.06 * t})`, boxSizing: "border-box" }}>
              {b.label && (
                <div style={{ position: "absolute", left: -bw, ...(b.below ? { top: `calc(100% + ${6 / z}px)` } : { bottom: `calc(100% + ${6 / z}px)` }), background: col, color: "#fff", fontFamily, fontSize: 21 / z, fontWeight: 700, padding: `${5 / z}px ${12 / z}px`, borderRadius: 8 / z, whiteSpace: "nowrap" }}>{b.label}</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

/** Dashboard recording in a browser-style window, lower third underneath. */
const BrowserShot: React.FC<{ shot: Shot; cfg: RecCfg; url: string; label: string; caption: React.ReactNode; labelColor?: string; children?: React.ReactNode }> = ({ shot, cfg, url, label, caption, labelColor, children }) => {
  const rec = manifest[shot.rec!];
  const aspect = rec?.exists ? rec.width / rec.height : 16 / 9;
  const BAR = 38, MAXW = 1664, MAXH = 936;
  const w = Math.round(Math.min(MAXW, MAXH * aspect)), h = Math.round(w / aspect);
  return (
    <Scene>
      <div style={{ position: "absolute", left: (1920 - w) / 2, top: 16, width: w, height: h + BAR, borderRadius: 14, overflow: "hidden", border: `1px solid ${C.line}`, boxShadow: "0 24px 70px rgba(0,0,0,.55)", background: C.dark2 }}>
        <div style={{ height: BAR, display: "flex", alignItems: "center", padding: "0 16px", gap: 8, background: "#232327" }}>
          {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 12, height: 12, borderRadius: 6, background: c }} />)}
          <div style={{ marginLeft: 18, background: "#17171A", borderRadius: 7, padding: "4px 16px", fontFamily: MONO, fontSize: 15, color: C.grey4, minWidth: 420 }}>{url}</div>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, fontSize: 14, fontWeight: 700, letterSpacing: 2, color: C.grey4 }}>
            <div style={{ width: 9, height: 9, borderRadius: 5, background: C.red }} />SCREEN RECORDING · WORKING PROTOTYPE
          </div>
        </div>
        <div style={{ position: "relative", width: w, height: h }}>
          <RecLayer recId={shot.rec!} title={shot.title} shotSeconds={shot.end - shot.start} cfg={cfg} w={w} h={h} />
          {children}
        </div>
      </div>
      <LowerThird label={label} color={labelColor}>{caption}</LowerThird>
    </Scene>
  );
};

/** Phone recording in a phone frame, with a caption column next to it. */
const PhoneShot: React.FC<{ shot: Shot; cfg: RecCfg; children: React.ReactNode }> = ({ shot, cfg, children }) => {
  const rec = manifest[shot.rec!];
  const aspect = rec?.exists ? rec.width / rec.height : 375 / 812;
  const h = 980, w = Math.round(h * aspect), B = 12;
  const t = useIn(0, 16);
  return (
    <Scene>
      <div style={{ position: "absolute", left: 210, top: (1080 - h - 2 * B) / 2, width: w, height: h, boxSizing: "content-box", borderRadius: 54, border: `${B}px solid #26262B`, overflow: "hidden", boxShadow: "0 30px 90px rgba(0,0,0,.6)", background: "#000", opacity: t, transform: `translateY(${(1 - t) * 20}px)` }}>
        <RecLayer recId={shot.rec!} title={shot.title} shotSeconds={shot.end - shot.start} cfg={cfg} w={w} h={h} />
      </div>
      <div style={{ position: "absolute", left: 210 + w + 2 * B + 110, right: 110, top: 0, bottom: 0, display: "flex", flexDirection: "column", justifyContent: "center" }}>{children}</div>
      <div style={{ position: "absolute", left: 210, width: w + 2 * B, bottom: 8, textAlign: "center", fontSize: 14, fontWeight: 700, letterSpacing: 2, color: C.muted }}>SCREEN RECORDING · MOBILE APP</div>
    </Scene>
  );
};

const Chip: React.FC<{ delay: number; color: string; title: string; children: React.ReactNode; dashed?: boolean }> = ({ delay, color, title, children, dashed }) => {
  const t = useIn(delay, 14);
  return (
    <div style={{ opacity: t, transform: `translateX(${(1 - t) * 36}px)`, background: C.dark2, border: `1px solid ${C.line}`, borderLeft: `7px ${dashed ? "dashed" : "solid"} ${color}`, borderRadius: 12, padding: "16px 24px", marginBottom: 16 }}>
      <div style={{ fontSize: 19, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase", color }}>{title}</div>
      <div style={{ fontSize: 31, fontWeight: 600, marginTop: 4, lineHeight: 1.25 }}>{children}</div>
    </div>
  );
};

// ------------------------------------------------------------------ problem (0:00-0:30)

/** Portrait site clip, framed (never stretched to full screen), over a blurred still of the same site. */
const SiteClip: React.FC<{ file: string; from: number; h: number; style?: React.CSSProperties; rate?: number }> = ({ file, from, h, style, rate = 1 }) => {
  const w = Math.round((h * 478) / 850);
  return (
    <div style={{ width: w, height: h, borderRadius: 22, overflow: "hidden", border: `1px solid ${C.line}`, boxShadow: "0 30px 90px rgba(0,0,0,.6)", background: "#000", ...style }}>
      <OffthreadVideo src={staticFile(file)} muted trimBefore={fr(from)} playbackRate={rate} style={{ width: w, height: h, objectFit: "cover" }} />
    </div>
  );
};

const Backdrop: React.FC<{ img: string }> = ({ img }) => (
  <Img src={staticFile(img)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover", filter: "blur(46px) brightness(0.22) saturate(0.8)", transform: "scale(1.15)" }} />
);

const FootageTag: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div style={{ position: "absolute", background: "rgba(0,0,0,.66)", borderRadius: 8, padding: "6px 12px", fontSize: 17, fontWeight: 600, letterSpacing: 0.5, color: C.grey3, whiteSpace: "nowrap", ...style }}>{children}</div>
);

function P1() {
  const H = 960, W = Math.round((H * 478) / 850);
  return (
    <Scene>
      <Backdrop img="struts-excavator-sq.jpg" />
      <div style={{ position: "absolute", left: 170, top: 60 }}>
        <SiteClip file="site/pit-excavation.mp4" from={8.5} h={H} />
        <FootageTag style={{ left: 14, top: 14 }}>Real site footage · deep excavation · 21.11.2026</FootageTag>
      </div>
      <div style={{ position: "absolute", left: 170 + W + 110, right: 120, top: 0, bottom: 0, display: "flex", flexDirection: "column", justifyContent: "center" }}>
        <Rise delay={4}><Kicker>The problem</Kicker></Rise>
        <Rise delay={10}><div style={{ fontSize: 82, fontWeight: 700, lineHeight: 1.08, letterSpacing: -1.5, marginTop: 22 }}>A construction site changes every hour.</div></Rise>
        <div style={{ marginTop: 44, display: "flex", flexDirection: "column", gap: 14 }}>
          {[["Rock broken out at the face", 50], ["Spoil loaded and hauled away", 76], ["Crews and machines move on", 102]].map(([txt, d]) => (
            <Rise key={txt as string} delay={d as number} dy={14}>
              <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 34, color: C.grey3 }}>
                <div style={{ width: 10, height: 10, borderRadius: 5, background: C.blueL }} />{txt}
              </div>
            </Rise>
          ))}
        </div>
        <Rise delay={138}>
          <div style={{ marginTop: 48, padding: "22px 28px", borderRadius: 12, background: "rgba(20,20,22,.78)", border: `1px solid ${C.line}`, fontSize: 36, fontWeight: 500, lineHeight: 1.3 }}>
            What happened is written into the <b>site diary</b>:<br />in the evening, from memory.
          </div>
        </Rise>
      </div>
    </Scene>
  );
}

const TOOLS = [
  { name: "Site diary", sys: "Bautagebuch", key: "date + free text" },
  { name: "Schedule", sys: "Primavera P6", key: "activity ID · A1080" },
  { name: "Contract", sys: "GAEB bill of quantities", key: "position no. · 01.06.0010" },
  { name: "Claims", sys: "Notices and letters", key: "letter no. + date" },
];

function P2() {
  const f = useCurrentFrame();
  const H = 720;
  const X0 = 120, Y0 = 96;
  const TX = 820, TW = 980, TH = 150, TG = 22, TY = 96;
  const obsY = Y0 + H + 22, obsH = 104;
  const verdict = useIn(250, 16);
  return (
    <Scene>
      <Backdrop img="crane-lift-sq.jpg" />
      <div style={{ position: "absolute", left: X0, top: 36 }}><Kicker>The problem · technically</Kicker></div>
      <div style={{ position: "absolute", left: X0, top: Y0 }}>
        <SiteClip file="site/crane-lift.mp4" from={3.5} h={H} rate={0.7} />
        <FootageTag style={{ left: 12, top: 12 }}>Real site footage</FootageTag>
      </div>
      <Rise delay={24} style={{ position: "absolute", left: X0, top: obsY, width: 560, height: obsH, boxSizing: "border-box", background: C.dark2, border: `1px solid ${C.line}`, borderLeft: `7px solid ${C.blueL}`, borderRadius: 12, padding: "14px 22px" }}>
        <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: 2, color: C.blueL }}>SITE OBSERVATION</div>
        <div style={{ fontSize: 28, fontWeight: 600, marginTop: 4 }}>“Scaffold tower moved by crane.”</div>
      </Rise>
      {/* connectors from the observation to each tool, each one broken */}
      <svg width={1920} height={1080} style={{ position: "absolute", left: 0, top: 0 }}>
        {TOOLS.map((_, i) => {
          const y = TY + i * (TH + TG) + TH / 2;
          const d0 = 60 + i * 28;
          const p = interpolate(f, [d0, d0 + 16], [0, 1], { ...clamp, easing: ease });
          const x1 = X0 + 560 + 10, y1 = obsY + obsH / 2, x2 = TX - 14;
          const mx = x2 - 22, my = y1 + (y - y1) * ((mx - x1) / (x2 - x1));
          const cut = interpolate(f, [150 + i * 12, 162 + i * 12], [0, 1], clamp);
          return (
            <g key={i} opacity={p}>
              <line x1={x1} y1={y1} x2={x1 + (x2 - x1) * p} y2={y1 + (y - y1) * p} stroke={cut > 0.5 ? C.redL : C.grey4} strokeWidth={3} strokeDasharray="10 10" opacity={0.8} />
              <g opacity={cut} transform={`translate(${mx},${my})`}>
                <circle r={20} fill={C.red} />
                <path d="M-8 -8 L8 8 M8 -8 L-8 8" stroke="#fff" strokeWidth={4} strokeLinecap="round" />
              </g>
            </g>
          );
        })}
      </svg>
      {TOOLS.map((t, i) => (
        <Rise key={t.name} delay={36 + i * 28} style={{ position: "absolute", left: TX, top: TY + i * (TH + TG), width: TW, height: TH, boxSizing: "border-box", background: "rgba(31,31,35,.94)", border: `1px solid ${C.line}`, borderRadius: 12, padding: "0 30px", display: "flex", alignItems: "center" }}>
          <div style={{ width: 400 }}>
            <div style={{ fontSize: 40, fontWeight: 700 }}>{t.name}</div>
            <div style={{ fontSize: 25, color: C.grey4, marginTop: 2 }}>{t.sys}</div>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 17, fontWeight: 700, letterSpacing: 2.5, color: C.muted }}>ITS OWN KEY</div>
            <div style={{ fontFamily: MONO, fontSize: 27, color: C.white, marginTop: 6 }}>{t.key}</div>
          </div>
        </Rise>
      ))}
      <div style={{ position: "absolute", left: TX, top: TY + 4 * (TH + TG) + 6, width: TW, boxSizing: "border-box", opacity: verdict, transform: `translateY(${(1 - verdict) * 14}px)`, background: "rgba(220,38,38,.16)", border: `2px solid ${C.red}`, borderRadius: 12, padding: "20px 30px" }}>
        <div style={{ fontSize: 36, fontWeight: 700, lineHeight: 1.2 }}>Four tools, no shared key.</div>
        <div style={{ fontSize: 28, color: C.grey3, marginTop: 6, lineHeight: 1.25 }}>A site observation never reaches the schedule or the contract.</div>
      </div>
    </Scene>
  );
}

const LinkNode: React.FC<{ top: string; main: string; delay: number; color?: string }> = ({ top, main, delay, color = C.line }) => {
  const t = useIn(delay);
  return (
    <div style={{ opacity: t, transform: `translateY(${(1 - t) * 14}px)`, background: C.dark2, border: `2px solid ${color}`, borderRadius: 12, padding: "14px 26px", textAlign: "center" }}>
      <div style={{ fontSize: 17, fontWeight: 700, letterSpacing: 2.5, color: C.muted }}>{top}</div>
      <div style={{ fontSize: 30, fontWeight: 600, marginTop: 4, whiteSpace: "nowrap" }}>{main}</div>
    </div>
  );
};
const Arrow: React.FC<{ delay: number; size?: number }> = ({ delay, size = 34 }) => {
  const t = useIn(delay);
  return <div style={{ opacity: t, fontSize: size, color: C.blueL, fontWeight: 700 }}>→</div>;
};

function P3() {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: f - 2, fps, config: { damping: 16 } });
  return (
    <Scene>
      <Backdrop img="struts-haul-sq.jpg" />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 30, transform: `scale(${0.86 + 0.14 * s})`, opacity: s }}>
          <Logo size={120} />
          <div style={{ fontSize: 140, fontWeight: 700, letterSpacing: -4 }}>Tagwerk</div>
        </div>
        <Rise delay={24}><div style={{ fontSize: 52, fontWeight: 500, marginTop: 34, color: C.grey3 }}>Capture once on site. Linked to schedule and contract.</div></Rise>
        <div style={{ display: "flex", alignItems: "center", gap: 22, marginTop: 70 }}>
          <LinkNode top="ON SITE" main="Observation" delay={60} color={C.blueL} />
          <Arrow delay={74} />
          <LinkNode top="WHAT" main="Element / place" delay={80} />
          <Arrow delay={94} />
          <LinkNode top="SCHEDULE · P6" main="Activity" delay={100} />
          <Arrow delay={114} />
          <LinkNode top="CONTRACT · GAEB" main="BoQ position" delay={120} />
        </div>
        <Rise delay={140}><div style={{ fontSize: 26, color: C.grey4, marginTop: 30 }}>linked at the moment of capture · no scanner, no BIM required</div></Rise>
      </AbsoluteFill>
    </Scene>
  );
}

// ------------------------------------------------------------------ demo (0:30-2:00). Coordinates are fractions of the recording.
// Marks are read from public/rec/<id>.json; the second value is the fallback in source seconds.

const ROWS: [number, number, number, number] = [0.28, 0.703, 0.455, 0.078];   // Gantt rows A1080 + A1090
const REC: Record<string, RecCfg> = {
  D1: {
    hl: [
      { from: ["tap_zone", 0.9, -0.3], to: ["tap_note", 1.8, 0.4], box: [0.255, 0.137, 0.39, 0.06], label: "Zone", below: true },
      { from: ["tap_senden", 8.58, -0.5], to: ["processed", 9.09, 0.2], box: [0.04, 0.715, 0.92, 0.076], label: "Send" },
    ],
  },
  D2: {
    cuts: [{ a: 1.5, b: 7.37, dur: 7 }],   // starts after the "Wird gesendet" toast
    hl: [{ from: ["result_visible", 1.75, 1.6], box: [0.07, 0.737, 0.86, 0.112], color: C.green }],
  },
  D3: {
    cuts: [{ a: 1.3, b: 6.5, dur: 4.6 }, { a: 7.2, b: 11.8, dur: 3.6 }, { a: 12.0, b: 16.0, dur: 3.8 }],
    cam: [
      { t: ["kpi_red", 3.35, 0.3], x: 0.5, y: 0.5, z: 1 },
      { t: ["cursor_kpi", 5.76, -0.6], x: 0.5, y: 0.2, z: 1.5 },
      { t: 6.4, x: 0.5, y: 0.2, z: 1.5 },
      { t: ["cursor_gantt_bestuhlung", 8.06, 0], x: 0.6, y: 0.66, z: 1.5 },
      { t: 11.7, x: 0.6, y: 0.66, z: 1.5 },
      { t: ["cursor_event_absence", 12.71, 0], x: 0.8, y: 0.5, z: 1.5 },
    ],
    hl: [
      { from: ["kpi_red", 3.35, 0.4], to: 6.5, box: [0.405, 0.142, 0.19, 0.098], color: C.red, label: "Finish 01.12. → 03.12.", below: true },
      { from: ["cursor_gantt_bestuhlung", 8.06, -0.2], to: 11.8, box: ROWS, color: C.red, label: "Delay runs on to the successor" },
      { from: ["cursor_event_absence", 12.71, -0.2], box: [0.757, 0.388, 0.228, 0.188], color: C.amber, label: "New events: defect · absence → A1080" },
    ],
  },
  // Ends on the click: the opened recording card labels the typed note "bestätigt · Sprache", which must not be shown.
  D4: {
    cuts: [{ a: 1.2, b: ["click_recording", 11.03, 0.03], dur: 10 }],
    cam: [
      { t: ["sheet_open", 2.59, -0.3], x: 0.5, y: 0.5, z: 1 },
      { t: ["cursor_delay", 3.7, 0], x: 0.87, y: 0.36, z: 1.5 },
      { t: ["cursor_gaeb", 7.35, -0.4], x: 0.87, y: 0.42, z: 1.5 },
      { t: ["cursor_recording", 10.23, -0.3], x: 0.87, y: 0.6, z: 1.5 },
    ],
    hl: [
      { from: ["cursor_cause", 5.12, -0.3], to: ["cursor_gaeb", 7.35, -0.1], box: [0.737, 0.383, 0.257, 0.042], color: C.red, label: "Cause: 2 of 3 drywall crew absent" },
      { from: ["cursor_gaeb", 7.35, 0], to: ["cursor_recording", 10.23, -0.3], box: [0.737, 0.452, 0.257, 0.062], label: "Contract position (GAEB)", below: true },
      { from: ["cursor_recording", 10.23, -0.2], box: [0.737, 0.61, 0.257, 0.046], color: C.green, label: "Evidence: today's capture" },
    ],
  },
  D5: {
    cuts: [{ a: 0.6, b: 15.6, dur: 12 }],
    cam: [{ t: 0.7, x: 0.5, y: 0.5, z: 1 }, { t: 2.1, x: 0.47, y: 0.595, z: 1.22 }],
    hl: [
      { from: ["hover_recording", 2.63, -0.2], to: ["hover_event_absence", 6.33, -0.2], box: [0.62, 0.566, 0.066, 0.044], label: "Capture" },
      { from: ["hover_event_absence", 6.33, -0.1], to: ["hover_activity", 10.61, -0.2], box: [0.742, 0.546, 0.102, 0.086], color: C.amber, label: "Events: absence, defect" },
      { from: ["hover_activity", 10.61, -0.1], to: ["hover_gaeb", 13.13, -0.2], box: [0.334, 0.68, 0.08, 0.094], color: C.red, label: "Activities, +2 days", below: true },
      { from: ["hover_gaeb", 13.13, -0.1], box: [0.166, 0.727, 0.136, 0.05], label: "GAEB position 01.06.0010" },
    ],
  },
  D6: {
    cuts: [{ a: 1.6, b: 4.6, dur: 1.8 }, { a: 6.0, b: 10.6, dur: 3.2 }, { a: 11.9, b: 13.2, dur: 1.0 }, { a: 15.0, b: 17.5, dur: 2.0 }],
    cam: [{ t: 1.6, x: 0.5, y: 0, z: 1.12 }],
    hl: [
      { from: ["back_1", 2.05, 0], to: 4.6, box: [0.058, 0.068, 0.105, 0.056], label: "Past: as recorded", below: true },
      { from: ["past_today", 7.5, 0], to: ["click_heute", 15.44, 0], box: [0.058, 0.068, 0.105, 0.056], color: C.amber, label: "Future: simulated", below: true },
      { from: ["at_forecast", 9.2, 0], to: ["click_heute", 15.44, 0], box: ROWS, color: C.red, label: "Forecast finish 03.12." },
    ],
  },
  D7: {
    hl: [
      { from: ["proposal_visible", 0.87, 0.3], to: ["tap_bestaetigen", 3.67, 0.1], box: [0.04, 0.235, 0.92, 0.178], color: C.violet, label: "Seen, not said" },
      { from: ["bar_moved", 3.88, 0.9], box: [0.08, 0.662, 0.84, 0.07], color: C.green },
    ],
  },
  D8: {
    cuts: [{ a: 1.4, b: 5.2, dur: 2.4 }, { a: 5.2, b: 11.7, dur: 1.6 }, { a: 11.7, b: 15.4, dur: 2.8 }, { a: 15.4, b: 17.7, dur: 0.6 }, { a: 17.7, b: 20.4, dur: 1.6 }],
    cam: [
      { t: ["report_open", 2.67, -0.2], x: 0.5, y: 0.5, z: 1 },
      { t: ["report_open", 2.67, 0.9], x: 0.5, y: 0.3, z: 1.3 },
      { t: ["scrolled_bottom", 11.71, 0], x: 0.5, y: 0.45, z: 1.3 },
      { t: ["cursor_incidents", 12.53, 0.4], x: 0.6, y: 0.45, z: 1.45 },
      { t: 15.4, x: 0.6, y: 0.45, z: 1.45 },
      { t: ["scrolled_top", 17.68, 0.2], x: 0.55, y: 0.3, z: 1.3 },
    ],
    hl: [
      { from: ["report_open", 2.67, 0.8], to: 5.2, box: [0.655, 0.205, 0.192, 0.068], label: "Generated from the day's captures", below: true },
      { from: ["cursor_incidents", 12.53, 0.3], to: 15.4, box: [0.505, 0.377, 0.347, 0.186], color: C.red, label: "Delays with their cause" },
      { from: ["scrolled_top", 17.68, 0.3], box: [0.64, 0.14, 0.215, 0.04], label: "Print-ready A4", below: true },
    ],
  },
  D9: {
    cuts: [{ a: 1.6, b: 3.2, dur: 0.6 }, { a: 10, b: 80, dur: 4.4 }],
    cam: [{ t: 1.6, x: 0.5, y: 0.5, z: 1 }, { t: 14, x: 0.56, y: 0.58, z: 1.18 }],
    hl: [{ from: 12, box: [0.762, 0.41, 0.218, 0.168], color: C.green, label: "2,082 linked elements, by state", below: true }],
  },
};

const PipeStep: React.FC<{ name: string; what: string; delay: number }> = ({ name, what, delay }) => {
  const t = useIn(delay, 12);
  return (
    <div style={{ opacity: t, transform: `translateY(${(1 - t) * 10}px)`, background: C.dark2, border: `1px solid ${C.line}`, borderRadius: 10, padding: "10px 16px", flex: 1 }}>
      <div style={{ fontSize: 22, fontWeight: 700, whiteSpace: "nowrap" }}>{name}</div>
      <div style={{ fontSize: 18, color: C.grey4, marginTop: 2, whiteSpace: "nowrap" }}>{what}</div>
    </div>
  );
};

function D1({ shot }: { shot: Shot }) {
  return (
    <PhoneShot shot={shot} cfg={REC.D1}>
      <Rise delay={6}><Kicker>Site manager · phone</Kicker></Rise>
      <Rise delay={12}><div style={{ fontSize: 68, fontWeight: 700, lineHeight: 1.1, letterSpacing: -1, marginTop: 16 }}>Pick the zone.<br />Send one note.</div></Rise>
      <Rise delay={40}>
        <div style={{ marginTop: 30, borderLeft: `5px solid ${C.blueL}`, paddingLeft: 22 }}>
          <div style={{ fontSize: 30, fontWeight: 500, lineHeight: 1.3 }}>„Stuhlreihe A ist montiert. Zwei Mann vom Trockenbau sind krank. Kratzer an der Bühne.“</div>
          <div style={{ fontSize: 24, color: C.grey4, marginTop: 8, lineHeight: 1.3 }}>Seat row A is installed. Two drywall workers are off sick. Scratch on the stage.</div>
        </div>
      </Rise>
      <Rise delay={110}>
        <div style={{ marginTop: 40, display: "flex", gap: 10 }}>
          {["Video", "Photo", "Voice", "Typed note"].map((k) => (
            <div key={k} style={{ fontSize: 24, fontWeight: 600, padding: "8px 18px", borderRadius: 10, background: k === "Typed note" ? C.white : C.dark2, color: k === "Typed note" ? C.ink : C.grey3, border: `1px solid ${C.line}` }}>{k}</div>
          ))}
        </div>
      </Rise>
      <Rise delay={150}>
        <div style={{ marginTop: 18, fontSize: 26, color: C.grey3, lineHeight: 1.35 }}>
          In this recording the note is <b style={{ color: C.white }}>typed</b>. A typed note counts like voice.
        </div>
      </Rise>
    </PhoneShot>
  );
}

function D2({ shot }: { shot: Shot }) {
  return (
    <PhoneShot shot={shot} cfg={REC.D2}>
      <Rise delay={6}><Kicker>What Tagwerk understood</Kicker></Rise>
      <Rise delay={12}><div style={{ fontSize: 62, fontWeight: 700, lineHeight: 1.1, letterSpacing: -1, margin: "16px 0 34px" }}>One note, three facts.</div></Rise>
      <Chip delay={34} color={C.greenL} title="Progress · confirmed">Stuhlreihe A → montiert · 85 %</Chip>
      <Chip delay={62} color={C.amber} title="Absence · event on activity A1080">2× Trockenbau fehlt (krank)</Chip>
      <Chip delay={90} color={C.redL} title="Defect · logged">Kratzer an der Bühne</Chip>
    </PhoneShot>
  );
}

function D7({ shot }: { shot: Shot }) {
  return (
    <PhoneShot shot={shot} cfg={REC.D7}>
      <Rise delay={6}><Kicker>Human in the loop</Kicker></Rise>
      <Rise delay={12}><div style={{ fontSize: 62, fontWeight: 700, lineHeight: 1.1, letterSpacing: -1, margin: "16px 0 34px" }}>The camera proposes.<br />A tap confirms.</div></Rise>
      <Chip delay={36} color={C.violetL} dashed title="Proposal · camera only">Stuhlreihe F · Unterkonstruktion</Chip>
      <Chip delay={112} color={C.greenL} title="Confirmed · one tap">Reihe F → 50 % · Bestuhlung neu 58 → 63 %</Chip>
      <Rise delay={160}><div style={{ fontSize: 27, color: C.grey3, marginTop: 14 }}>States only go up. Every percent is traceable.</div></Rise>
    </PhoneShot>
  );
}

const ONTO: { label: string; de: string; rel?: string; color?: string; dashed?: boolean }[] = [
  { label: "BoQPosition", de: "GAEB-Position", rel: "SCHEDULED_AS" },
  { label: "Activity", de: "Vorgang (P6)", rel: "BUILDS" },
  { label: "Element / Zone", de: "Bauteil / Ort", rel: "IN_ZONE" },
  { label: "Capture", de: "Aufnahme", rel: "RAISED" },
  { label: "Event / Proposal", de: "Ereignis / Vorschlag", color: C.redL },
];

/** Names the ontology chain (seed/ontology.yaml) over the live graph recording. */
const OntologyBand: React.FC<{ start: number }> = ({ start }) => {
  const f = useCurrentFrame();
  const t = interpolate(f, [start, start + 14], [0, 1], { ...clamp, easing: ease });
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: 0, padding: "12px 26px 14px", background: "rgba(14,14,16,.95)", borderBottom: `1px solid ${C.line}`, opacity: t, transform: `translateY(${(t - 1) * 30}px)`, display: "flex", alignItems: "center", gap: 20 }}>
      <div style={{ width: 170 }}>
        <div style={{ fontSize: 16, fontWeight: 700, letterSpacing: 2.5, color: C.blueL }}>ONTOLOGY</div>
        <div style={{ fontSize: 15, color: C.grey4, marginTop: 3, fontFamily: MONO }}>Neo4j projection</div>
      </div>
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        {ONTO.map((n, i) => {
          const d = start + 16 + i * 30;
          const p = interpolate(f, [d, d + 12], [0, 1], { ...clamp, easing: ease });
          return (
            <React.Fragment key={n.label}>
              <div style={{ opacity: p, transform: `scale(${0.92 + 0.08 * p})`, background: C.dark2, border: `2px solid ${n.color ?? C.blueL}`, borderRadius: 10, padding: "8px 18px", textAlign: "center" }}>
                <div style={{ fontFamily: MONO, fontSize: 23, fontWeight: 700, whiteSpace: "nowrap" }}>{n.label}</div>
                <div style={{ fontSize: 16, color: C.grey4, marginTop: 2, whiteSpace: "nowrap" }}>{n.de}</div>
              </div>
              {n.rel && (
                <div style={{ opacity: interpolate(f, [d + 12, d + 24], [0, 1], clamp), textAlign: "center", flex: 1, minWidth: 0 }}>
                  <div style={{ fontFamily: MONO, fontSize: 15, color: C.grey4, whiteSpace: "nowrap" }}>{n.rel}</div>
                  <div style={{ height: 2, background: C.blueL, margin: "4px 8px 0", position: "relative" }}>
                    <div style={{ position: "absolute", right: -2, top: -5, width: 0, height: 0, borderLeft: `10px solid ${C.blueL}`, borderTop: "6px solid transparent", borderBottom: "6px solid transparent" }} />
                  </div>
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

function Demo({ shot }: { shot: Shot }) {
  const cfg = REC[shot.id] ?? {};
  switch (shot.id) {
    case "D1": return <D1 shot={shot} />;
    case "D2": return <D2 shot={shot} />;
    case "D7": return <D7 shot={shot} />;
    case "D3": return <BrowserShot shot={shot} cfg={cfg} url="localhost:8080/app · Hörsaal Sanierung" label="Alerts · events · forecast" labelColor={C.redL} caption={<>The capture arrives live: absence on A1080, finish <b>01.12. → 03.12.</b> (+2 working days)</>} />;
    case "D4": return <BrowserShot shot={shot} cfg={cfg} url="localhost:8080/app · Hörsaal Sanierung" label="How we link" caption={<>Delay → cause → GAEB position 01.06.0010 → the recording. Every percent traces to a sentence.</>} />;
    case "D5": return (
      <BrowserShot shot={shot} cfg={cfg} url="localhost:8080/app · Live-Graph" label="The ontology layer" caption={<>One graph: every observation is linked when it is captured, not afterwards</>}>
        <OntologyBand start={36} />
      </BrowserShot>
    );
    case "D6": return <BrowserShot shot={shot} cfg={cfg} url="localhost:8080/app · Hörsaal Sanierung" label="Prediction" caption={<>Remaining work re-simulated day by day: crew minus absences, FS/SS successors</>} />;
    case "D8": return <BrowserShot shot={shot} cfg={cfg} url="localhost:8080/app · Tagesbericht 26.11.2026" label="Report · exports" caption={<>Daily report from the day's captures · exports: P6 XML · GAEB X83/X84 · .ics</>} />;
    case "D9": return <BrowserShot shot={shot} cfg={cfg} url="localhost:8081/app · Schependomlaan (open BIM dataset)" label="With a BIM model" caption={<>Build sequence from the schedule, element by element (time-lapse ×16)</>} />;
    default: return null;
  }
}

// ------------------------------------------------------------------ technical approach + close

const ArchBox: React.FC<{ delay: number; title: string; sub?: string; items?: string[]; color?: string; w: number; h?: number; tag?: string }> = ({ delay, title, sub, items, color = C.line, w, h = 330, tag }) => {
  const t = useIn(delay);
  return (
    <div style={{ width: w, height: h, boxSizing: "border-box", opacity: t, transform: `translateY(${(1 - t) * 18}px)`, background: C.dark2, border: `2px solid ${color}`, borderRadius: 14, padding: "20px 20px", display: "flex", flexDirection: "column" }}>
      {tag && <div style={{ fontSize: 15, fontWeight: 700, letterSpacing: 2.5, color: C.blueL, marginBottom: 8, whiteSpace: "nowrap" }}>{tag}</div>}
      <div style={{ fontSize: 30, fontWeight: 700, lineHeight: 1.15 }}>{title}</div>
      {sub && <div style={{ fontSize: 20, color: C.grey4, marginTop: 6, lineHeight: 1.25 }}>{sub}</div>}
      {items && (
        <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 7 }}>
          {items.map((it) => <div key={it} style={{ fontSize: 21, fontWeight: 500, background: "#17171A", border: `1px solid ${C.line}`, borderRadius: 8, padding: "6px 12px", whiteSpace: "nowrap" }}>{it}</div>)}
        </div>
      )}
    </div>
  );
};

function T1() {
  const f = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const closeAt = durationInFrames - 100;
  const dim = interpolate(f, [closeAt, closeAt + 14], [1, 0.16], clamp);
  const c = interpolate(f, [closeAt + 4, closeAt + 20], [0, 1], { ...clamp, easing: ease });
  return (
    <Scene>
      <div style={{ opacity: dim }}>
        <div style={{ position: "absolute", left: 80, top: 96 }}>
          <Kicker>Technical approach</Kicker>
          <div style={{ fontSize: 54, fontWeight: 700, letterSpacing: -1, marginTop: 10 }}>One project state. One graph. Open exports.</div>
        </div>
        <div style={{ position: "absolute", left: 80, right: 80, top: 310, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <ArchBox delay={8} w={236} tag="CAPTURE" title="Phone" items={["video · photos", "voice", "typed note"]} />
          <Arrow delay={20} />
          <ArchBox delay={26} w={330} color={C.blueL} tag="ONE 6 GB GPU LAPTOP" title="Perception" items={["Whisper · speech", "YOLO11s + YOLO-World", "RelateAnything", "SfM · 3D scan"]} h={370} />
          <Arrow delay={48} />
          <ArchBox delay={54} w={236} tag="UNDERSTAND" title="Structuring" sub="rules, or Claude with an API key" items={["progress", "absence · defect", "delay"]} h={370} />
          <Arrow delay={76} />
          <ArchBox delay={82} w={270} color={C.greenL} tag="AUTHORITATIVE" title="Project state" sub="element → P6 activity → GAEB position" items={["states only go up", "forecast re-simulated"]} h={370} />
          <Arrow delay={104} />
          <ArchBox delay={110} w={236} tag="PROJECTION" title="Neo4j graph" sub="idempotent MERGE per capture" items={["ontology", "live task graph"]} />
          <Arrow delay={132} />
          <ArchBox delay={138} w={250} tag="OUT" title="Stakeholders" items={["Dashboard", "Daily report", "P6 XML", "GAEB X83/X84", ".ics"]} h={370} />
        </div>
        <Rise delay={150} style={{ position: "absolute", left: 80, right: 80, top: 770, display: "flex", gap: 18 }}>
          {["Voice or a tap confirms · the camera alone only proposes", "No scanner, no BIM required", "Every stage output cached per capture_id · replayable"].map((s) => (
            <div key={s} style={{ flex: 1, fontSize: 24, color: C.grey3, background: "rgba(31,31,35,.7)", border: `1px solid ${C.line}`, borderRadius: 10, padding: "14px 20px", lineHeight: 1.25 }}>{s}</div>
          ))}
        </Rise>
      </div>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: c, transform: `scale(${0.96 + 0.04 * c})` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
          <Logo size={110} />
          <div style={{ fontSize: 128, fontWeight: 700, letterSpacing: -4 }}>Tagwerk</div>
        </div>
        <div style={{ fontSize: 50, fontWeight: 500, marginTop: 26, color: C.grey3 }}>Capture once. Linked everywhere.</div>
      </AbsoluteFill>
    </Scene>
  );
}

// ------------------------------------------------------------------ timeline

const render = (shot: Shot) => {
  switch (shot.id) {
    case "P1": return <P1 />;
    case "P2": return <P2 />;
    case "P3": return <P3 />;
    case "T1": return <T1 />;
    default: return <Demo shot={shot} />;
  }
};

export const Submission: React.FC = () => (
  <AbsoluteFill style={{ background: C.dark }}>
    {SHOTS.map((shot) => {
      const from = fr(shot.start);
      const dur = Math.min(fr(shot.end), SUBMISSION_FRAMES) - from;
      const line = vo[shot.id];
      return (
        <Sequence key={shot.id} from={from} durationInFrames={dur} name={`${shot.id} ${shot.title}`}>
          {render(shot)}
          {line && <Sequence from={fr(timeline.voLead)} layout="none"><Audio src={staticFile(line.file)} /></Sequence>}
        </Sequence>
      );
    })}
  </AbsoluteFill>
);
