// Recordings wait here until the server has processed them. Survives app restarts and dead zones on site:
// a job is resent with the same capture_id, and the server answers "exists" for one it already has.
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Directory, File, Paths } from "expo-file-system";
import { AppState, Platform } from "react-native";
import { CaptureResult, MediaFile, getJson, postForm, settings } from "./api";

export type JobStatus = "waiting" | "uploading" | "processing" | "done" | "error";
export type Job = {
  id: string; server: string; token?: string; zone_id: string; zone_name: string; note?: string; kind: string; files: MediaFile[];
  created: string; status: JobStatus; progress: number; step?: string; error?: string; result?: CaptureResult;
  attempts?: number; recovered?: boolean;
};

const KEY = "tw.jobs";
const KEEP_DONE = 30; // finished jobs kept for the list; unfinished ones are never dropped
const STEPS = ["Hochgeladen", "normalized", "transcribed", "vision", "structured", "done", "sfm"];
let jobs: Job[] = [];
let running = false;
let retryTimer: ReturnType<typeof setTimeout> | null = null;
const subs = new Set<(j: Job[]) => void>();

const isNetwork = (msg: string) => /Verbindung|Network|Tailscale/i.test(msg);
const emit = () => { const copy = jobs.map((j) => ({ ...j })); subs.forEach((f) => f(copy)); };
const persist = () => {
  let done = 0;
  const keep = jobs.filter((j) => j.status !== "done" || ++done <= KEEP_DONE);
  jobs.filter((j) => !keep.includes(j)).forEach((j) => cleanup(j.id));
  jobs = keep;
  return AsyncStorage.setItem(KEY, JSON.stringify(jobs));
};
/** `save: false` for progress ticks: re-render, but do not rewrite storage hundreds of times per upload. */
const patch = (id: string, p: Partial<Job>, save = true) => {
  jobs = jobs.map((j) => (j.id === id ? { ...j, ...p } : j)); emit(); if (save) persist();
};

export function subscribe(f: (j: Job[]) => void): () => void {
  subs.add(f); f(jobs.map((j) => ({ ...j })));
  return () => { subs.delete(f); };
}

export async function initQueue(): Promise<void> {
  const raw = await AsyncStorage.getItem(KEY);
  // a job cut off mid-upload or mid-processing goes back to waiting; before resending, the queue asks the server
  // whether it already has it (re-uploading while the first run is still processing would overwrite its files)
  jobs = raw ? (JSON.parse(raw) as Job[]).map((j) => (j.status === "uploading" || j.status === "processing"
    ? { ...j, status: "waiting", recovered: true } : j)) : [];
  emit();
  // back from the background (signal may be back too): try again
  AppState.addEventListener("change", (s) => { if (s === "active") kick(); });
  kick(); // also resends jobs that failed for lack of connection last time
}

export const newId = () => `cap-m-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

/** Copy the picked files out of the picker's cache (Android may clear it) and queue the job. */
export async function enqueue(j: Omit<Job, "status" | "progress" | "created" | "server" | "token">): Promise<void> {
  let files = j.files;
  if (Platform.OS !== "web") {
    const dir = new Directory(Paths.document, "captures", j.id);
    try {
      if (!dir.exists) dir.create({ intermediates: true });
      files = await Promise.all(j.files.map(async (f) => {
        const dest = new File(dir, f.name);
        if (!dest.exists) await new File(f.uri).copy(dest);
        return { ...f, uri: dest.uri };
      }));
    } catch (e) {
      cleanup(j.id);
      throw e;
    }
  }
  const { server, token } = settings();
  jobs = [{ ...j, server, token, files, status: "waiting", progress: 0, created: new Date().toISOString() }, ...jobs];
  emit(); await persist();
  run();
}

export function retry(id: string) { patch(id, { status: "waiting", error: undefined, attempts: 0 }); run(); }
/** Only waiting or failed jobs can be removed: an upload in flight still reads the files. */
export function remove(id: string) {
  const j = jobs.find((x) => x.id === id);
  if (!j || j.status === "uploading" || j.status === "processing") return;
  jobs = jobs.filter((x) => x.id !== id); emit(); persist(); cleanup(id);
}
/** Live step from the websocket. The server replays old events on reconnect, so a step never moves backwards. */
export function setStep(id: string, step: string) {
  const j = jobs.find((x) => x.id === id && x.status === "processing");
  if (j && STEPS.indexOf(step) > STEPS.indexOf(j.step ?? "")) patch(id, { step }, false);
}
/** Resend jobs that failed for lack of connection (app back in front, or the timer). */
export function kick() {
  jobs.forEach((j) => { if (j.status === "error" && isNetwork(j.error ?? "")) patch(j.id, { status: "waiting" }); });
  run();
}

function cleanup(id: string) {
  if (Platform.OS === "web") return;
  try { const d = new Directory(Paths.document, "captures", id); if (d.exists) d.delete(); } catch { /* best effort */ }
}

async function fetchExisting(job: Job): Promise<CaptureResult | null> {
  try {
    return summarize(await getJson<any>(`/captures/${job.id}`, 10000, job.server, job.token ?? settings().token), job.id);
  } catch (e: any) {
    if (e?.status === 404) return null;
    throw e;
  }
}

async function run(): Promise<void> {
  if (running) return;
  running = true;
  let offline = false;
  try {
    for (;;) {
      const job = [...jobs].reverse().find((j) => j.status === "waiting"); // oldest first
      if (!job) break;
      patch(job.id, { status: "uploading", progress: 0, step: undefined });
      try {
        const token = job.token ?? settings().token;
        let res = job.recovered ? await fetchExisting(job) : null;
        if (!res) {
          res = await postForm<CaptureResult>(
            "/captures", { zone_id: job.zone_id, capture_id: job.id, note: job.note, lang: "auto" }, job.files,
            (p) => patch(job.id, { progress: p }, false), () => patch(job.id, { status: "processing", step: "Hochgeladen" }),
            job.server ?? settings().server, token, // the project it was recorded for, even if the app switched server since
          );
          if (res.status === "exists") res = (await fetchExisting(job)) ?? res;
        }
        patch(job.id, { status: "done", result: res, step: undefined, recovered: false, error: undefined });
        cleanup(job.id);
      } catch (e: any) {
        const msg = String(e?.message ?? e);
        // after a failed attempt the server may hold the capture already: ask first next time
        patch(job.id, { status: "error", error: msg, recovered: true, attempts: (job.attempts ?? 0) + 1 });
        if (isNetwork(msg)) { offline = true; break; } // the other jobs would fail the same way
      }
    }
  } finally {
    running = false;
  }
  if (offline) {
    if (retryTimer) clearTimeout(retryTimer);
    retryTimer = setTimeout(kick, 30000); // keep trying while the app is open
  }
}

/** GET /captures/{id}: the in-memory pipeline result, or after an API restart only the stored capture. */
function summarize(r: any, id: string): CaptureResult {
  if (r?.status === "processed") return r;
  const s = r?.structured ?? {};
  return {
    capture_id: id, status: "processed",
    transcript: (r?.transcript?.segments ?? []).map((g: any) => g.text).join(" ") || r?.quotes?.join(" "),
    changes: (r?.changes ?? []).filter((c: any) => ["confirmed", "proposed", "unchanged"].includes(c.action)),
    absences: s.absences ?? [], events: s.special_events ?? [], material: s.material_delivered ?? [], labour: s.labour_present ?? [],
  };
}
