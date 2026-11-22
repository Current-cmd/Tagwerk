# Voice-over for the 2-minute submission (ElevenLabs)

Composition `Submission` (`src/Submission.tsx`), timeline in `src/submission-timeline.json`, lines in `vo/submission-lines.json`.
The video is fixed at 2:00. A line that runs longer than its shot is shortened; the shot does not stretch.

## Paste this block

One paragraph per shot, in shot order, no labels (labels would be read aloud). Narrator: one calm English voice,
stability about 50, similarity about 75, style 0 to 15, speed 1.0. Leave the blank lines in: each one gives a pause
that the track is cut at.

```text
A construction site changes every hour. What happens is written into a site diary, from memory.

Diary, P6 schedule, GAEB bill of quantities and claims live in separate tools, with no shared key. An observation never reaches the schedule or the contract.

Tagwerk. Capture once on site, and it is linked to the schedule and the contract.

The site manager picks the zone and sends one note. Speech goes through Whisper; typed, as here, counts the same.

Tagwerk reads three facts: row A installed, two drywall workers sick, one defect.

On the dashboard the capture arrives live. Progress is confirmed, the absence lands on its activity, and the forecast moves the finish two working days.

Why? One click shows the cause, the contract position, and the recording behind it. Every percent traces back to a sentence.

Underneath is one graph. Contract position, activity, place, recording, event. Each observation is linked at the moment it is captured, in Neo4j.

One slider: past, today, forecast. Remaining work is re-simulated with the crews actually present.

The camera alone only proposes. A tap or a sentence confirms. States only go up.

The daily report writes itself, delays and causes included. The office gets exports for Primavera, GAEB and the calendar.

With a BIM model, the same loop runs on over two thousand elements.

Speech, vision and 3D run on one six-gigabyte GPU laptop. One project state, one graph, open exports. Tagwerk.
```

Pronunciation, if the voice gets it wrong: "GAEB" is said as one word, "gah-ebb" (respell it that way in the text);
"P6" is "P six"; "Neo4j" is "neo four jay"; "Tagwerk" is German, "TAHG-vairk".

## Paragraph → shot

| # | id | Time | Shot | Shot length | Line must end within | Words |
|---|---|---|---|---|---|---|
| 1 | P1 | 0:00.0–0:08.5 | Problem: a site changes every hour | 8.5 s | 8.0 s | 16 |
| 2 | P2 | 0:08.5–0:21.5 | Problem: four tools, no shared key | 13.0 s | 12.5 s | 26 |
| 3 | P3 | 0:21.5–0:28.5 | Tagwerk in one line | 7.0 s | 6.5 s | 15 |
| 4 | D1 | 0:28.5–0:38.0 | Phone: capture | 9.5 s | 9.0 s | 20 |
| 5 | D2 | 0:38.0–0:45.0 | Phone: result card | 7.0 s | 6.5 s | 13 |
| 6 | D3 | 0:45.0–0:57.0 | Dashboard: capture arrives, forecast flips | 12.0 s | 11.5 s | 25 |
| 7 | D4 | 0:57.0–1:07.0 | Dashboard: trace the delay | 10.0 s | 9.5 s | 21 |
| 8 | D5 | 1:07.0–1:19.0 | Live graph: ontology | 12.0 s | 11.5 s | 22 |
| 9 | D6 | 1:19.0–1:27.0 | Day slider: forecast | 8.0 s | 7.5 s | 14 |
| 10 | D7 | 1:27.0–1:35.0 | Phone: confirm proposal | 8.0 s | 7.5 s | 15 |
| 11 | D8 | 1:35.0–1:44.0 | Daily report and exports | 9.0 s | 8.5 s | 19 |
| 12 | D9 | 1:44.0–1:49.0 | BIM model | 5.0 s | 4.5 s | 13 |
| 13 | T1 | 1:49.0–2:00.0 | Architecture and close | 11.0 s | 10.5 s | 18 |

Each line starts 0.2 s after its shot begins. Total: 237 words.

## Bring the audio back

Either one file per line or one file for the whole block (it is then cut at the pauses between paragraphs).
Clips go to `public/vo/sub-<id>.wav` (48 kHz mono WAV; `afconvert -f WAVE -d LEI16@48000 -c 1 in.mp3 public/vo/sub-P1.wav`). Then, from `pitch/video/`:

```sh
node scripts/make-submission-vo.mjs --measure-only   # measures each clip against its shot, flags any that are too long
npm run render:submission                            # -> out/tagwerk-submission.mp4
```

`node scripts/make-submission-vo.mjs` without the flag regenerates the macOS placeholder voice (overwrites the clips).
