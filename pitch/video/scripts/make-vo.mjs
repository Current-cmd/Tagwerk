// Generates voice-over clips from vo/lines.json and writes src/vo.json with their lengths.
// Replace any public/vo/<id>.wav with a real recording, then run with --measure-only.
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync } from "node:fs";

const lines = JSON.parse(readFileSync("vo/lines.json", "utf8"));
const measureOnly = process.argv.includes("--measure-only");
const out = {};
for (const l of lines) {
  const wav = `public/vo/${l.id}.wav`;
  if (!measureOnly || !existsSync(wav)) {
    const aiff = `/tmp/vo-${l.id}.aiff`;
    execFileSync("say", ["-v", l.voice, "-r", String(l.rate ?? 180), "-o", aiff, l.text]);
    execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", aiff, "-ar", "48000", "-ac", "1", wav]);
  }
  const sec = parseFloat(execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav]).toString());
  out[l.id] = { file: `vo/${l.id}.wav`, seconds: Math.round(sec * 100) / 100 };
  console.log(l.id.padEnd(10), out[l.id].seconds);
}
writeFileSync("src/vo.json", JSON.stringify(out, null, 2) + "\n");
