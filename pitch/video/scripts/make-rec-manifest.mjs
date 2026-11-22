// Lists which screen recordings exist in public/rec/ and writes src/rec-manifest.json, so the Submission
// composition can render a labelled placeholder for anything missing instead of crashing.
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync } from "node:fs";

const IDS = ["phone-capture", "phone-result", "phone-confirm", "dash-flip", "dash-trace", "dash-graph", "dash-forecast", "dash-report", "dash-bim"];
const out = {};
for (const id of IDS) {
  const mp4 = `public/rec/${id}.mp4`, json = `public/rec/${id}.json`;
  const e = { exists: false, seconds: 0, width: 0, height: 0, marks: {} };
  if (existsSync(mp4)) {
    try {
      const p = execFileSync("npx", ["remotion", "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration", "-of", "json", mp4], { stdio: ["ignore", "pipe", "ignore"] }).toString();
      const j = JSON.parse(p.slice(p.indexOf("{")));
      e.width = j.streams[0].width; e.height = j.streams[0].height; e.seconds = Math.round(parseFloat(j.format.duration) * 100) / 100;
      e.exists = e.width > 0 && e.seconds > 0;
    } catch (err) { console.warn(id, "unreadable mp4:", String(err).split("\n")[0]); }
  }
  if (existsSync(json)) {
    try { const j = JSON.parse(readFileSync(json, "utf8")); e.marks = j.marks ?? {}; if (!e.seconds && j.seconds) e.seconds = j.seconds; }
    catch { console.warn(id, "unreadable json"); }
  }
  out[id] = e;
  console.log(id.padEnd(15), e.exists ? `${e.width}x${e.height} ${e.seconds}s marks: ${Object.keys(e.marks).join(", ") || "-"}` : "MISSING -> placeholder");
}
writeFileSync("src/rec-manifest.json", JSON.stringify(out, null, 2) + "\n");
