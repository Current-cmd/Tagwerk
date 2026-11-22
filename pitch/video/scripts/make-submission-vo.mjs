// Placeholder voice-over for the 2-minute submission (composition "Submission").
// Reads vo/submission-lines.json ({id: text}), writes public/vo/sub-<id>.wav and src/submission-vo.json.
// Real recordings: drop public/vo/sub-<id>.wav (48 kHz mono WAV), then run with --measure-only.
// The total length is fixed at 2:00: a line that is longer than its shot must be shortened, the shot does not stretch.
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";

const lines = JSON.parse(readFileSync("vo/submission-lines.json", "utf8"));
const tl = JSON.parse(readFileSync("src/submission-timeline.json", "utf8"));
const measureOnly = process.argv.includes("--measure-only");
const VOICE = process.env.VO_VOICE ?? "Daniel";
const RATE = process.env.VO_RATE ?? "165";
// `say` reads these better when spelled out; the script text for ElevenLabs stays as written.
const forSay = (t) => t.replace(/\bGAEB\b/g, "gah-ebb").replace(/\bP6\b/g, "P six").replace(/\b3D\b/g, "three D").replace(/Neo4j/g, "Neo four J").replace(/Tagwerk/g, "Tahg-verk");
mkdirSync("public/vo", { recursive: true });
const out = {};
let bad = 0, words = 0;
for (const shot of tl.shots) {
  const text = lines[shot.id];
  if (!text) { console.log(shot.id, "NO LINE"); bad++; continue; }
  const wav = `public/vo/sub-${shot.id}.wav`;
  if (!measureOnly || !existsSync(wav)) {
    const aiff = `/tmp/sub-vo-${shot.id}.aiff`;
    execFileSync("say", ["-v", VOICE, "-r", RATE, "-o", aiff, forSay(text)]);
    execFileSync("afconvert", ["-f", "WAVE", "-d", "LEI16@48000", "-c", "1", aiff, wav]);
  }
  const info = execFileSync("afinfo", [wav]).toString();
  const sec = parseFloat(/estimated duration: ([\d.]+)/.exec(info)[1]);
  const slot = shot.end - shot.start;
  const room = slot - tl.voLead - sec;
  const n = text.trim().split(/\s+/).length; words += n;
  out[shot.id] = { file: `vo/sub-${shot.id}.wav`, seconds: Math.round(sec * 100) / 100, words: n };
  const flag = room < 0 ? "  << TOO LONG, shorten the line" : room < 0.3 ? "  (tight)" : "";
  if (room < 0) bad++;
  console.log(shot.id.padEnd(4), `${String(n).padStart(3)} words`, `${sec.toFixed(2).padStart(6)} s`, `slot ${slot.toFixed(1).padStart(5)} s`, `air ${room.toFixed(2).padStart(6)} s${flag}`);
}
console.log("total words", words);
writeFileSync("src/submission-vo.json", JSON.stringify(out, null, 2) + "\n");
if (bad) { console.error(`${bad} line(s) do not fit`); process.exitCode = 1; }
