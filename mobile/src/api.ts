// Talks to the Tagwerk API on the laptop (FastAPI, tagwerk/api/app.py).
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Platform } from "react-native";

export type Settings = { server: string; token: string };
export const DEFAULT_SERVER = "http://100.118.181.69:8080"; // the GPU laptop over Tailscale

const KEY = "tw.settings";
let current: Settings = { server: DEFAULT_SERVER, token: "" };

export async function loadSettings(): Promise<Settings> {
  const raw = await AsyncStorage.getItem(KEY);
  if (raw) current = { ...current, ...JSON.parse(raw) };
  return current;
}
export async function saveSettings(s: Settings): Promise<void> {
  current = { server: s.server.trim().replace(/\/+$/, ""), token: s.token.trim() };
  await AsyncStorage.setItem(KEY, JSON.stringify(current));
}
export const settings = () => current;

/** `tagwerk://connect?url=…&token=…` (the connect QR code) or a bare URL. */
export function parseConnect(text: string): Settings | null {
  const t = text.trim();
  const m = t.match(/^tagwerk:\/\/connect\?(.*)$/);
  if (m) {
    const p = new URLSearchParams(m[1]);
    const url = p.get("url");
    return url ? { server: url, token: p.get("token") ?? "" } : null;
  }
  return /^https?:\/\//.test(t) ? { server: t, token: "" } : null;
}

const headers = (token = current.token): Record<string, string> => (token ? { Authorization: `Bearer ${token}` } : {});

/** A page URL to open in the browser (pages read the token from `?token=`). */
export function pageUrl(path: string): string {
  const u = `${current.server}${path}`;
  return current.token ? `${u}${u.includes("?") ? "&" : "?"}token=${encodeURIComponent(current.token)}` : u;
}

export async function getJson<T>(path: string, timeoutMs = 10000, server = current.server, token = current.token): Promise<T> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const r = await fetch(`${server}${path}`, { headers: headers(token), signal: ctl.signal });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw Object.assign(new Error(body.detail || `HTTP ${r.status}`), { status: r.status });
    return body as T;
  } catch (e: any) {
    if (e?.name === "AbortError") throw new Error("Keine Verbindung: Server antwortet nicht (Tailscale an?)");
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${current.server}${path}`, {
    method: "POST", headers: { ...headers(), "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const out = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(out.detail || `HTTP ${r.status}`);
  return out as T;
}

export type MediaFile = { uri: string; name: string; type: string };

/** Multipart POST with upload progress (fetch has none). `onUploaded` fires when the last byte is sent and the
 * server starts processing; the promise resolves with the server's answer. */
export async function postForm<T>(
  path: string, fields: Record<string, string | undefined>, files: MediaFile[],
  onProgress?: (fraction: number) => void, onUploaded?: () => void, server = current.server, token = current.token,
  timeoutMs = 15 * 60 * 1000, // upload + GPU processing of a long video; a dead connection must not hang the queue
): Promise<T> {
  const form = new FormData();
  for (const [k, v] of Object.entries(fields)) if (v !== undefined && v !== "") form.append(k, v);
  for (const f of files) {
    if (Platform.OS === "web") form.append("files", await (await fetch(f.uri)).blob(), f.name);
    else form.append("files", { uri: f.uri, name: f.name, type: f.type } as any);
  }
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${server}${path}`);
    for (const [k, v] of Object.entries(headers(token))) xhr.setRequestHeader(k, v);
    xhr.timeout = timeoutMs;
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress?.(e.loaded / e.total);
    xhr.upload.onload = () => { onProgress?.(1); onUploaded?.(); };
    xhr.onload = () => {
      let body: any = {};
      try { body = JSON.parse(xhr.responseText); } catch { /* not JSON */ }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as T);
      else reject(new Error(body.detail || `HTTP ${xhr.status}`));
    };
    xhr.onerror = () => reject(new Error("Keine Verbindung zum Server"));
    xhr.ontimeout = () => reject(new Error("Keine Verbindung: Zeitüberschreitung"));
    xhr.onabort = () => reject(new Error("Keine Verbindung: abgebrochen"));
    xhr.send(form);
  });
}

/** Live pipeline steps from the API's websocket (`/events`). Returns a function that closes it. */
export function listen(onMessage: (m: any) => void): () => void {
  let ws: WebSocket | null = null, closed = false, backoff = 1000;
  let timer: ReturnType<typeof setTimeout> | null = null;
  const open = () => {
    if (closed) return;
    const base = current.server.replace(/^http/, "ws");
    ws = new WebSocket(`${base}/events${current.token ? `?token=${encodeURIComponent(current.token)}` : ""}`);
    ws.onmessage = (ev) => { try { onMessage(JSON.parse(String(ev.data))); } catch { /* ignore */ } };
    ws.onopen = () => { backoff = 1000; };
    ws.onclose = () => { if (!closed) timer = setTimeout(open, backoff); backoff = Math.min(backoff * 2, 15000); };
  };
  open();
  return () => { closed = true; if (timer) clearTimeout(timer); ws?.close(); };
}

// ---------- response shapes (only the fields the app reads) ----------
export type Health = { status: string; project: string; elements: number; activities: number; data_date: string; structuring: string };
export type Zone = { id: string; name: string };
export type Element = { id: string; name: string; pct: number; state: string; states: string[] };
export type Activity = {
  id: string; name: string; trade?: string; pct: number; planned_pct: number; planned_start?: string;
  tracked?: boolean; delay_d?: number; elements: string[]; red?: boolean; cause?: string;
};
export type Change = { element_id: string; action: string; state: string; pct?: number; quote?: string; evidence?: string; activity_id?: string };
export type Overview = {
  date: string;
  kpi: { pct_actual: number; pct_planned: number; spi: number | null; delay_d: number; forecast_finish: string | null; open_defects?: number };
  activities: Activity[];
  zones: { zone_id: string; name: string; elements: Element[] }[];
  proposals: { element_id: string; state: string; name?: string; quote?: string; capture_id?: string }[];
  captures: { capture_id: string; zone_id: string; ts: string; note?: string; quotes?: string[]; changes?: Change[] }[];
  today_capture_ids: string[];
};
export type CaptureResult = {
  capture_id: string; status: "processed" | "exists"; transcript?: string; changes?: Change[];
  absences?: { trade: string; count: number; reason?: string }[]; events?: { type: string; text: string; severity?: string }[];
  material?: { name: string; qty?: number; unit?: string }[]; labour?: { trade: string; count: number }[];
};
export type ScanItem = { label: string; name_de: string; category: string; category_de: string; ifc_class?: string | null; instances: number; frames: number; thumb?: string };
export type ScanResult = {
  scan_id: string; items: ScanItem[]; element_count?: number;
  scan3d?: { ok: boolean; reason?: string; frames_registered: number; objects: number; url: string };
};
export type Report = {
  date: string; project: { name: string };
  recordings: unknown[]; work_done: { activity_name: string | null; element_name: string; state_de: string; quote: string | null; capture_id: string }[];
  workforce: { present: { trade: string; count: number }[]; absent: { trade: string; count: number; reason?: string | null }[] };
  events: { type: string; text: string }[];
  delays: { activity_id: string; activity_name: string; delay_d: number; cause: string }[];
  lookahead: { date: string; activities: string[] }[];
};
