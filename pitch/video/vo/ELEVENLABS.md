# Voice-over script for ElevenLabs

One clip per block, saved as `public/vo/<id>.wav` (convert from mp3, see below). `<break time="…" />` works with
Multilingual v2 and Turbo/Flash (v3 ignores it; use punctuation). The seconds are what the scene holds today;
longer is fine, the scene stretches (`src/vo.json`).

Narrator: one calm English voice, stability ~50, similarity ~75, style 0–15.

| id | max | text |
|---|---|---|
| title35 | 3.3 s | Thirty-five seconds of site video. <break time="0.4s" /> What did Tagwerk make of it? |
| boxes | 12.8 s | Every second, Tagwerk looks at a frame. <break time="0.5s" /> Equipment and people. <break time="0.3s" /> The building elements in the contract. <break time="0.5s" /> And one thing that shouldn't be there. |
| water | 4.2 s | Water on the pile wall. <break time="0.4s" /> The camera sees it, but can't judge it. |
| facts | 6.8 s | Each sentence confirms something the camera saw. <break time="0.4s" /> The piling rigs got no sentence, so they stay a proposal. |
| titlebim | 2.7 s | With a BIM model, <break time="0.2s" /> or without one. |
| nobim | 9.8 s | No BIM model? <break time="0.4s" /> Drop in the schedule and the bill of quantities. <break time="0.5s" /> Activities, positions and the baseline. Ready. |
| withbim | 7.8 s | With a BIM model, every element carries its own state. <break time="0.4s" /> Here, a real open dataset: <break time="0.2s" /> two thousand and eighty-two elements. |
| mapping | 10.5 s | Every fact lands on an element, a schedule activity, and a contract position. <break time="0.6s" /> The water lands on dewatering. <break time="0.3s" /> And the slab moves. |
| notice | 7.8 s | The delay that needs a notice gets a draft, with the video attached. <break time="0.5s" /> The site manager decides. |
| titlelive | 2.3 s | This runs today, in the demo project. |
| dash | 5.1 s | Plan versus actual, <break time="0.2s" /> S-P-I, <break time="0.2s" /> and the forecast. From today's evidence. |
| graph | 4.1 s | Every recording, linked to positions, activities and zones. |
| report | 4.6 s | The daily report writes itself. <break time="0.3s" /> Delays included. |
| scan | 4.1 s | And from a walk-through video, a three-D scan. <break time="0.3s" /> What was said, and where. |
| close | 10 s | The only thing was the water. <break time="1.0s" /> Now it's in the site diary, <break time="0.3s" /> the schedule, <break time="0.3s" /> and the notice. |
| end | 5.5 s | Tagwerk. <break time="0.6s" /> The day's work, documented. |

Voice note (separate German voice, a site-manager type, Multilingual v2, stability ~40; the transcript types at its pace):

| id | text |
|---|---|
| voicenote | Baugrube Abschnitt drei. <break time="0.5s" /> Aushub dritte Lage, unter der zweiten Steifenlage, zur Hälfte fertig. <break time="0.3s" /> Zwei Bagger, ein Traktor mit Mulde. <break time="0.6s" /> Gerüst an Achse zwölf umgesetzt. <break time="0.8s" /> An der Bohrpfahlwand Nord steht Wasser. <break time="0.4s" /> Die Wasserhaltung reicht nicht. |

New lines for the app scenes go in `lines.json` and here (see `docs/tasks/HANDOFF-pitch.md`).

Convert and re-time (from `pitch/video/`):

```sh
for f in ~/Downloads/vo/*.mp3; do ffmpeg -y -loglevel error -i "$f" -ar 48000 -ac 1 "public/vo/$(basename "$f" .mp3).wav"; done
node scripts/make-vo.mjs --measure-only
npm run render
```
