// Recordings wait here until the server has processed them. Survives app restarts and dead zones on site:
// a job is resent with the same capture_id, and the server answers "exists" for one it already has.
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Directory, File, Paths } from "expo-file-system";
import { Platform } from "react-native";
import { CaptureResult, MediaFile, getJson, postForm, settings } from "./api";

export type JobStatus = "waiting" | "uploading" | "processing" | "done" | "error";
export type Job = {
  id: string; server: string; zone_id: string; zone_name: string; note?: string; kind: string; files: MediaFile[];
  created: string; status: JobStatus; progress: number; step?: string; error?: string; result?: CaptureResult;
};

const KEY = "tw.jobs";
let jobs: Job[] = [];
let running = false;
const subs = new Set<(j: Job[]) => void>();

const emit = () => { const copy = jobs.map((j) => ({ ...j })); subs.forEach((f) => f(copy)); };
const persist = () => AsyncStorage.setItem(KEY, JSON.stringify(jobs.slice(0, 50)));
const patch = (id: string, p: Partial<Job>) => { jobs = jobs.map((j) => (j.id === id ? { ...j, ...p } : j)); emit(); persist(); };

export function subscribe(f: (j: Job[]) => void): () => void {
  subs.add(f); f(jobs.map((j) => ({ ...j })));
  return () => { subs.delete(f); };
}

export async function initQueue(): Promise<void> {
  const raw = await AsyncStorage.getItem(KEY);
  // a job cut off mid-upload or mid-processing goes back to waiting and is resent (idempotent)
  jobs = raw ? (JSON.parse(raw) as Job[]).map((j) => (j.status === "uploading" || j.status === "processing" ? { ...j, status: "waiting" } : j)) : [];
  emit();
  run();
}

export const newId = () => `cap-m-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

/** Copy the picked files out of the picker's cache (Android may clear it) and queue the job. */
export async function enqueue(j: Omit<Job, "status" | "progress" | "created" | "server">): Promise<void> {
  let files = j.files;
  if (Platform.OS !== "web") {
    const dir = new Directory(Paths.document, "captures", j.id);
    if (!dir.exists) dir.create({ intermediates: true });
    files = await Promise.all(j.files.map(async (f) => {
      const dest = new File(dir, f.name);
      if (!dest.exists) await new File(f.uri).copy(dest);
      return { ...f, uri: dest.uri };
    }));
  }
  jobs = [{ ...j, server: settings().server, files, status: "waiting", progress: 0, created: new Date().toISOString() }, ...jobs];
  emit(); await persist();
  run();
}

export function retry(id: string) { patch(id, { status: "waiting", error: undefined }); run(); }
export function remove(id: string) { jobs = jobs.filter((j) => j.id !== id); emit(); persist(); cleanup(id); }
export function setStep(id: string, step: string) { if (jobs.some((j) => j.id === id && j.status === "processing")) patch(id, { step }); }

function cleanup(id: string) {
  if (Platform.OS === "web") return;
  try { const d = new Directory(Paths.document, "captures", id); if (d.exists) d.delete(); } catch { /* best effort */ }
}

async function run(): Promise<void> {
  if (running) return;
  running = true;
  try {
    for (;;) {
      const job = [...jobs].reverse().find((j) => j.status === "waiting"); // oldest first
      if (!job) break;
      patch(job.id, { status: "uploading", progress: 0, step: undefined });
      try {
        let res = await postForm<CaptureResult>(
          "/captures", { zone_id: job.zone_id, capture_id: job.id, note: job.note, lang: "auto" }, job.files,
          (p) => patch(job.id, { progress: p }), () => patch(job.id, { status: "processing", step: "Hochgeladen" }),
          job.server, // the project it was recorded for, even if the app has switched server since
        );
        if (res.status === "exists") res = summarize(await getJson<any>(`/captures/${job.id}`, 10000, job.server), job.id);
        patch(job.id, { status: "done", result: res, step: undefined });
        cleanup(job.id);
      } catch (e: any) {
        patch(job.id, { status: "error", error: String(e?.message ?? e) });
        // no connection: stop here and let the user (or the next app start) retry
        if (/Verbindung|Network/i.test(String(e?.message))) break;
      }
    }
  } finally {
    running = false;
  }
}

/** GET /captures/{id} returns the raw pipeline result; bring it into the POST /captures shape. */
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
