// Check a recording: print codec/size/fps/duration and extract stills.
//   node pitch/rec/frames.mjs dash-flip 1 3.5 8        -> /tmp/tw-frames/dash-flip-1.jpg ...
import fs from 'node:fs'
import path from 'node:path'
import { OUT, ffrun } from './lib.mjs'
const [id, ...times] = process.argv.slice(2)
const file = path.join(OUT, `${id}.mp4`)
console.log((await ffrun(['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name,width,height,r_frame_rate,pix_fmt,nb_frames,duration', '-of', 'default=nw=1', file], 'probe')).trim().replace(/\n/g, ' '))
console.log('audio streams:', (await ffrun(['-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'csv=p=0', file], 'probe')).trim() || 'none')
const dir = process.env.FRAMES_DIR || '/tmp/tw-frames'
fs.mkdirSync(dir, { recursive: true })
for (const t of times) {
  const out = path.join(dir, `${id}-${t}.jpg`)
  await ffrun(['-y', '-v', 'error', '-ss', t, '-i', file, '-frames:v', '1', '-q:v', '2', out])
  console.log(out)
}
