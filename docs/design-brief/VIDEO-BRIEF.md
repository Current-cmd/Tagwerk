# Tagwerk demo video: design brief and shot list

> **Superseded shot list (2026-11-21):** the story and shot list now open on the real excavation footage. See
> [DEMO-VIDEO-SHOTLIST.md](DEMO-VIDEO-SHOTLIST.md). Sections 4.4 (recording checklist), 5 (visual style) and 6
> (risks) here still apply.


Status: brief only, nothing edited yet. Written 2026-11-21 against the repo state described in `docs/DEMO.md`,
`docs/UI-V2-CONTRACT.md` and `docs/RELEASE-NOTES.md`. Every on-screen action below is something the app does today,
unless it is marked **ROADMAP (do not show as live)**.

---

## 1. Goal, audience, length, message, tone, language

**Goal.** Win Challenge B ("AI Site Manager Assistant for Documentation, Daily Reports and Claims") by showing the
required use case, *"A day in the life of a site manager with an AI assistant"*, end to end on the real prototype,
ending on the PDF daily report (the required export).

**Audience.** Hackathon judges (mix of construction practitioners, investors, engineers). Many watch the first pass
muted, so the story must read from captions and screen alone ([Devpost help](https://help.devpost.com/article/84-video-making-best-practices),
[recorded.app](https://recorded.app/en/blog/hackathon-demo-videos/)).

**Length.** Target **2:45** (hard window 2:30-3:00). Most hackathons cap at 3:00 and judges stop at the limit
([recorded.app](https://recorded.app/en/blog/hackathon-demo-videos/)). Budget about 15 s hook, 15 s problem,
~1:50 product, 20 s outcome/next/end card, in line with AngelHack's "most of the time on the demo" split
([AngelHack](https://angelhack.com/blog/10-tips-to-help-you-rock-your-next-hackathon-demo/)).

**Core message (one sentence).** *The site manager just walks and talks; Tagwerk turns it into the Bautagebuch,
the schedule impact and the paper trail, tied to the contract and the P6 plan, and the human signs off.*

**Tone.** Calm, competent, practical. A real working day, not a sci-fi pitch. No hype words ("revolutionary",
"fully autonomous"). Let the UI changing on screen carry the excitement.

**Language (recommendation).** German site audio (the Bauleiter dictating, exactly as the product expects) with
**burned-in English captions**, plus an English voice-over only for the hook, problem and outro (or no VO at all and
English title cards). Reasons: the UI is German (`Aufnahmen des Tages`, `Tagesbericht`, `Behinderungen / Verzug`),
the dictation must be German for the keyword rules to fire, and German audio signals domain authenticity. English
captions keep it readable for non-German judges and for muted viewing. Put a small English gloss next to German UI
terms the first time they appear (e.g. "Tagesbericht = daily site report").

---

## 2. "Day in the life" story structure

Grounding for the routine: a typical German Bauleiter day runs roughly 06:30 arrival and plan, 07:00 site walk before
work starts, 07:30 morning meeting with foremen and subcontractors, 08:00-11:00 coordination on site, a Baubesprechung,
and an office block for Bautagebuch, minutes, change orders and measurements
([M&S Akademie](https://m-s-akademie.de/wordpress/was-macht-ein-bauleiter/)). The Jour fixe is a weekly fixed-date
site meeting, usually a walk followed by a sit-down, minuted with status, decisions, open points and deadlines
([Deutscher Bauzeiger](https://www.deutscher-bauzeiger.de/bauen/bauleitung/baubesprechung/jour-fixe/)). The Bautagebuch
records weather, attendance per trade, work done, instructions, hindrances (Behinderungen) and extra work; on paper it
costs 20-45 min a day and incidents should be logged immediately, not at the end of the day
([GREENOX](https://greenox-group.de/bautagebuch/), [Baugrid](https://www.baugrid.de/blog/bautagebuch-fuehren-pflicht-vorlage-digital)).
A Behinderungsanzeige under § 6 (1) VOB/B must be given "unverzüglich" and in writing, naming since when, the cause,
the affected work and the effect on time; without it the contractor generally loses extension and compensation claims
([nevaris](https://www.nevaris.com/blog/behinderungsanzeige/), [lb-consult](https://www.lb-consult.com/ratgeber/behinderungsanzeige-vob)).
That last point is the emotional stake of the video: the sick crew at 10:30 is a claim that must not get lost.

Project in the video: **"Hörsaal Sanierung"** (seed project `hoersaal`, API :8080), a lecture-hall refurbishment
with 10 P6 activities (A1010 Baustelleneinrichtung ... A1090 Abnahme), 15 GAEB positions, 32 elements (Stuhlreihe A-H,
Bühne, Licht-Traverse, Lautsprecher, Leinwand ...), zones Bühne / Zuschauerraum / Technik / Eingang.
Project "today" (`DATA_DATE`) = **Thu 26.11.2026**, the planned Abnahme day.

| Clock (story) | Video time | Beat | Challenge B objective | Tagwerk feature / route |
|---|---|---|---|---|
| — | 0:00-0:12 | Hook: Bauleiter speaks one sentence on site, graph lights up | Voice capture via mobile | phone footage + `/graph` replay (synced video, captions, "Erfasst") |
| — | 0:12-0:27 | Problem: paper Bautagebuch, claims lost when not reported "unverzüglich" | (framing) | title cards |
| 06:45 | 0:27-0:45 | Morning briefing: where do we stand vs plan, what runs the next 3 days | Daily report analysis vs plan | `/app#/dashboard`: KPI strip (Ist/Soll, SPI, Prognose-Ende, offene Mängel, Wetter), Gantt, "Vorschau: nächste 3 Arbeitstage"; day slider |
| 07:15 | 0:45-1:05 | Site walk: films and dictates in the Zuschauerraum and on the Bühne | Voice/text capture via mobile | phone footage; `/upload` on the phone (zone, video, note, Hochladen) |
| 07:20 | 1:05-1:25 | The walk becomes structured data, element by element | Structured summaries; automatic analysis | `/graph` replay picker ▶ Abspielen (video left, live captions, graph fills at each spoken second) or `/app` Live-Graph |
| 09:30 / 10:00 | 1:25-1:35 | Delivery logged, defect logged | Documentation; defect capture | `/app` Ereignisse tile (Lieferung, Mangel), KPI "Offene Mängel" |
| 10:30 | 1:35-1:58 | Two drywallers sick: forecast moves, delay shows red with its cause | Detect deviations | Gantt red delay, ActivitySheet ("cause: 2× Trockenbau krank"), KPI Prognose-Ende |
| 11:00 | 1:58-2:10 | Human in the loop: vision only *proposes*, the Bauleiter confirms with a tap | Human in the loop | proposals (dashed, "nur Bild") in the recording accordion / task graph; `/site` tap-to-confirm |
| 14:00 | 2:10-2:20 | Jour fixe: the plan goes back to the tools the office already uses | Automatic correspondence (partial) | `/export/p6.xml`, `/export/day.ics` (Outlook), `/export/boq.x84` |
| 16:45 | 2:20-2:38 | Tagesbericht filled itself; print to PDF, sign | Daily report + PDF export (required) | `/app#/report/2026-11-26` → *Drucken / PDF*; `/export/report.html` A4 with signature lines |
| 17:00 | 2:38-2:45 | Report out, day done; roadmap line; end card | Smart letter drafts (**ROADMAP**) | end card |

Coverage honesty: Challenge B objectives that Tagwerk does **not** implement today and must only appear as roadmap:
**smart letter drafts** (Behinderungsanzeige, Mehrkostenanzeige, Mängelanzeige), **Word (.docx) export**, ingestion
and summarisation of **emails / meeting minutes**, and **automatic sending** of correspondence. What it does have that
feeds these: the delay with its cause, the defect events and the dated quote ("Behinderungen / Verzug" section of the
report), which are exactly the facts a Behinderungsanzeige needs (since when, cause, affected activity, time effect).
Say this out loud in the video as "next step", never as a working feature.

---

## 3. Shot list

Conventions: **PH** = phone footage (vertical, shown in a 9:16 frame or cropped), **SC** = screen capture of the
running app on the laptop API :8080 (Hörsaal), 1920×1080. **VO** = English voice-over (optional, can be replaced by
title cards). **DE** = German site audio from the Bauleiter, captioned in English.

All German dictation lines are taken from or built strictly on the phrases verified by `tests/test_demo_phrases.py`
and the keyword tables in `tagwerk/pipeline/structure.py` (state words: `montiert`, `angeschlossen`, `in Betrieb`,
`unterkonstruktion`, `verkabelt`; absence: count word + trade word + `krank`; delivery: `geliefert`; defect:
`kratzer`). Rules for the speaker: one fact per short sentence, name the element every time (the rules cannot resolve
"das"/"die"), avoid future words (`morgen`, `wird noch`, `nächste Woche`, `später`) in a sentence that should count
as done, and avoid `fehlt` about work. Each element only moves up once per reset, so every take needs a fresh reset
(or use replay).

| # | Time | Scene | Visual | Audio (VO or DE line) | English caption | On-screen text / overlay | Transition |
|---|---|---|---|---|---|---|---|
| 1 | 0:00-0:05 | Cold open on site | PH: Bauleiter in the hall, phone filming the seat rows | DE: "Stuhlreihe A ist montiert." | "Row A of the seating is installed." | — | hard cut in on the word "Stuhlreihe" |
| 2 | 0:05-0:12 | It lands in the plan | SC `/graph`: replay video panel left, node "Stuhlreihe A" turns green, "Erfasst 00:03" appears | DE (continues): "Zwei Mann vom Trockenbau sind krank." | "Two drywall workers are off sick." | Big type: **"He just talked. Tagwerk updated the schedule."** | quick zoom-in on the Erfasst list, cut |
| 3 | 0:12-0:20 | Problem | Black title card, Geist type, then a stock-free illustration: paper Bautagebuch page | VO: "Site managers spend up to 45 minutes a day writing the site diary. And a delay that isn't reported right away can cost the claim." | (same as VO) | "20-45 min/day on paper" · "§ 6 VOB/B: report hindrances without delay" (small source line) | dissolve |
| 4 | 0:20-0:27 | Title | Logo (black rounded square, white "T") + wordmark | VO: "This is Tagwerk. One day on a lecture-hall refurbishment." | — | "Tagwerk · Hörsaal Sanierung · Thursday 26.11." | wipe to screen |
| 5 | 0:27-0:37 | 06:45 Morning briefing | SC `/app#/dashboard` day 26.11: KPI strip, Gantt with today line | VO: "06:45. Before anyone arrives: progress against plan, schedule index, forecast finish, open defects, weather." | "Progress vs plan, SPI, forecast finish" | Lower-third clock "06:45 · Morgenbriefing"; callouts on KPI tiles | cursor-led pan |
| 6 | 0:37-0:45 | Lookahead | SC: scroll to "Vorschau: nächste 3 Arbeitstage"; drag the day slider back a few days and forward to today (graph/Gantt build up) | VO: "And what has to happen in the next three working days." | "3-day lookahead from the P6 schedule" | Gloss: "Vorgänge = P6 activities" | cut on slider release |
| 7 | 0:45-0:55 | 07:15 Site walk, audience area | PH: walking the seat rows, rows visibly in place | DE: "Stuhlreihe A ist montiert. Reihen F bis H Unterkonstruktion." | "Row A installed. Rows F to H: substructure done." | Lower-third "07:15 · Rundgang Zuschauerraum" | match cut on movement |
| 8 | 0:55-1:05 | Stage | PH: stage, speakers, screen | DE: "Lautsprecher links und Lautsprecher rechts angeschlossen. Die Leinwand ist in Betrieb." | "Left and right speakers connected. The screen is commissioned." | — | cut |
| 9 | 1:05-1:10 | Upload | PH or SC phone mirror: `/upload`, zone "Zuschauerraum", video picked, *Hochladen* | ambient | "One upload. No forms." | — | swipe |
| 10 | 1:10-1:25 | Structuring | SC `/graph` (old page) replay: ▶ Abspielen; video left at ~38 %, live captions with recognised phrases highlighted, graph nodes update at each spoken second; toast "fertig: N Änderungen" | VO: "Whisper transcribes, vision checks markers and objects, and every sentence is matched to an element, an activity in P6 and a position in the GAEB contract." | "Speech → element → P6 activity → GAEB position" | Callout arrows: "voice confirms", "vision only proposes" | cut |
| 11 | 1:25-1:30 | 09:30 Delivery | PH: boxes of chairs at the door (or close-up of a delivery note) | DE: "40 Stühle geliefert." | "40 chairs delivered." | Lower-third "09:30 · Lieferung" | cut |
| 12 | 1:30-1:35 | 10:00 Defect | PH close-up of a scratch on the stage edge | DE: "Kratzer an der Bühne." | "Scratch on the stage." | SC inset: Ereignisse tile shows "Mangel", KPI "Offene Mängel" increments | cut |
| 13 | 1:35-1:47 | 10:30 Deviation | PH: Bauleiter on phone call, then speaks | DE: "Zwei Mann vom Trockenbau sind krank." | "Two drywall workers are off sick." | Lower-third "10:30 · Ausfall" | cut to screen on "krank" |
| 14 | 1:47-1:58 | Forecast moves | SC `/app` dashboard: Gantt bar of "Bestuhlung neu" (A1080) extends, delay in red; click opens ActivitySheet with cause "2× Trockenbau krank"; KPI Prognose-Ende shifts by a day | VO: "Tagwerk recomputes the forecast from today's crew. The delay shows up with its cause, the same morning." | "Forecast recalculated from crew absences" | Callout: "Verzug + cause = the facts for a hindrance notice" | push-in on the red bar |
| 15 | 1:58-2:10 | 11:00 Human in the loop | SC: recording accordion "was der Agent daraus erkannt hat" with a dashed proposal "… begonnen? (nur Bild)"; cut to `/site` on the phone, tap a state, toast "✓ … bestätigt" | VO: "What the camera only sees stays a proposal. The site manager confirms with one tap." | "Vision proposes. The human confirms." | Badge overlay "Human in the loop" | cut |
| 16 | 2:10-2:20 | 14:00 Jour fixe | SC: `/app` Live-Graph tab (GAEB → activity → zone → recording → event); then quick cuts of the export downloads: P6 XML, `day.ics` opening in Outlook/Calendar, GAEB X84 | VO: "For the Jour fixe, the updated schedule goes back to Primavera, the day's captures to Outlook, progress to the GAEB bill of quantities." | "Exports: Primavera P6 XML · Outlook .ics · GAEB X84" | File-type chips | cut |
| 17 | 2:20-2:32 | 16:45 Tagesbericht | SC `/app#/report/2026-11-26`: scroll sections 1 Arbeitskräfte, 3 Ausgeführte Arbeiten (one row per spoken sentence with quote), 4 Besondere Vorkommnisse, 5 Behinderungen / Verzug, Vorschau | VO: "At the end of the day the Bautagebuch has written itself: crew, work done in the site manager's own words, incidents, delays and their causes." | "The daily report filled itself from the day's recordings" | Gloss "Tagesbericht = daily site report" | scroll |
| 18 | 2:32-2:38 | PDF + signature | SC: *Drucken / PDF* → browser print dialog A4 → saved PDF; zoom on "Bauleitung (Datum, Unterschrift)" | VO: "The site manager reviews it, signs it, sends it. 17:00, done." | "Reviewed and signed by the site manager" | Lower-third "17:00 · Bericht raus"; disclaimer line (see section 6) | dissolve |
| 19 | 2:38-2:42 | Next | Static roadmap card, clearly styled differently (outline, "Roadmap" label) | VO: "Next: one-click drafts of the hindrance notice and additional-cost notice from those same facts." | "Roadmap: Behinderungsanzeige & Mehrkostenanzeige drafts, Word export" | Label "ROADMAP" top-left | fade |
| 20 | 2:42-2:45 | End card | Logo, tagline, team, repo URL, tech strip | music out | — | "Tagwerk · Walk. Talk. Done." · Whisper · YOLO · ArUco · Claude (with rule fallback) · Neo4j · P6 · GAEB · github.com/Current-cmd/Tagwerk | cut to black |

Notes on specific shots:
- **#2 and #10** use the replay of a cached capture with video (`▶ Abspielen` on `/graph`, `POST /captures` with
  `replay_of` + `sync=1`): the graph changes at the second each phrase is spoken. The existing entry is `cap-e2e-2`
  ("Demo-Video: Stuhlreihe A montiert, 2× Trockenbau krank, Traverse verkabelt", synthetic German voice + row-A
  marker). Its text says "Traverse verkabelt", not the full script. For the video, record the real walk once with the
  script lines, upload it, and add it to `demo_replays` in `seed/project.json` (see `docs/DEMO.md`, "New replay entry
  with video"); then every take replays it deterministically.
- **#14** numbers: the release notes measured A1080 28.9 % → 34.4 % and forecast 30.11. → 01.12. for the row-A +
  sick-crew capture. Re-check them on the reset state before writing any number into a caption; never hard-code an
  unverified number.
- **#12** "Kratzer an der Bühne" creates a defect event only (no state change); that is correct, do not caption it as
  "status updated".
- **#16** the `.ics` contains one 15-minute event per capture plus an all-day daily-report entry. Do not claim it
  sends e-mails or invitations; it is a file the user imports.
- **Optional 8-second insert (if time allows, replace part of #16):** the 3D room scan `/app#/scan/uw-video` (point
  cloud, camera path, labelled objects with relations "neben Wand"). It is real, but it belongs to the scan project on
  :8082, not the Hörsaal; caption it "Room scan from the same phone video (separate project)" or leave it out.

Word count check: the VO above is about 190 English words plus ~45 German words, which fits 2:45 with breathing room
(~150 wpm guidance, [recorded.app](https://recorded.app/en/blog/hackathon-demo-videos/)).

---

## 4. Footage inventory and recording plan

### 4.1 Existing raw footage (in `/Users/anoushk/Developer/hacka/`, originals untouched)

Probed with `ffprobe`; frames extracted to `/tmp/tw-frames/` and inspected.

| File | Tech | Content | Usable for the video? |
|---|---|---|---|
| `20261121_200042.mp4` | 2:01, HEVC 1920×1080 at 30 fps with −90° rotation (plays as **vertical 1080×1920**), AAC, 210 MB | Handheld walk through a finished conference/venue building at night: catering counter with plates (~0:25), hall with high tables and tiled floor (~0:05), exposed-concrete column and parquet hall with chairs (~0:45), people working at desks (~1:05), corridor with dark doors and a door display (~1:25), wall with a red fire-hose cabinet (~1:50). Fast pans and some motion blur. | **Limited.** It is not a construction site and shows no seat rows, stage or AV, so it cannot illustrate the Hörsaal dictation. Usable as atmospheric B-roll only ("walking the building", 2-3 s steady stretches around 0:00-0:10 and 0:40-0:50), or as input for the room-scan feature. People at desks are identifiable: blur faces or get consent before publishing. See 4.3 for audio. |
| `Screen Recording 2026-11-21 at 01.46.34.mov` | 1:10, H.264 3024×1964 at 60 fps (Retina), AAC, 615 MB | Screen capture of a **third-party YouTube video**: "Expertentipp: Nachhaltig renovieren im Hochbau" (project "Die Baustelle in Amstetten"), a site manager in hi-vis and a fischer-branded presenter on a renovation site, scaffolding, insulation and timber-frame close-ups, YouTube player chrome visible. This is the "user's German construction walkthrough" used as test input in the release notes. | **Do not use in the published video.** It is someone else's copyrighted content with visible branding. Fine as internal pipeline test input; showing even a few seconds would need the rights holder's permission. |
| `id.m4a` | 3:40, AAC audio, 3.6 MB | English voice memo: the spoken UI v2 brief (walks through the Hörsaal dashboard, asks to remove costs, keep recordings / activities + Gantt / events tiles, task-based live graph, a day slider "to go left and right and see the work getting done"). This is the source of `docs/UI-V2-CONTRACT.md`. | **No** as audio (internal, informal, off-topic for judges). Useful as a content reference only: it confirms the slider and "recordings of the day" are the views the team cares about. |

### 4.2 What still needs recording

Shoot in a real lecture hall (any university Hörsaal with seat rows and a stage fits the seed project exactly):

1. **PH hero walk, 25-35 s, vertical**, Bauleiter in hi-vis (or at least a jacket and a clipboard) speaking the script
   of shots #1, #7, #8, #13 in one take, slowly, phone held steady at chest height. Clip-on mic into the phone if
   possible; site audio must be clean for Whisper and for the captions. This single clip is uploaded once and becomes
   the replay entry (4.4, step 6).
2. **PH inserts, 3-5 s each:** seat rows close-up, stage edge (for "Kratzer"), speakers left/right, projection screen,
   chair boxes or stacked chairs at the entrance (delivery), Bauleiter on a phone call (sick crew), hand tapping the
   phone on `/site` (shot #15), hand holding the printed/signed report (shot #18, optional).
3. **SC takes** (laptop screen, 1920×1080), each as a separate short clip so a mistake costs one take, not the whole
   video ([recorded.app](https://recorded.app/en/blog/hackathon-demo-videos/)): dashboard briefing + slider, replay on
   `/graph`, dashboard after the capture (Gantt, ActivitySheet, Ereignisse), recording accordion with a proposal,
   Live-Graph tab, exports (+ `.ics` import into a calendar app), Tagesbericht scroll, print-to-PDF dialog.
4. **VO** recorded separately in a quiet room (or skip VO and use title cards).
5. **Logo/end card** assets: black rounded square with white "T" (as in the app header) and the "Tagwerk" wordmark in Geist.

### 4.3 Audio
All three audio tracks were transcribed locally with faster-whisper (small, CPU) for this inventory:
- **Phone walk** (`20261121_200042.mp4`): English, low level (mean −35.6 dB), loose commentary about the venue
  ("the tables over here ... slab has been placed, dustbins here ... storage here"). Not German, not a Hörsaal script,
  so the structuring rules would match little. **Not usable** as site audio; mute it if any B-roll is used.
- **Screen recording**: German dialogue from the third-party YouTube video (thin concrete facade, Mineralschaum
  eingefüllt, Leibungsblech, Holzrahmen-Elemente vorgefertigt). Third-party, **not usable**.
- **id.m4a**: English internal UI brief (see 4.1). **Not usable** in the video.

Conclusion: no existing audio is usable. The German dictation for the video must be newly recorded (4.2, item 1),
and the English VO separately (4.2, item 4).

### 4.4 Recording checklist (laptop, `~/Developer/hacka/Tagwerk`, `export PYTHONPATH=$PWD`)

Environment
- [ ] Power plugged in, suspend disabled (a resume can break CUDA; fix in `docs/DEMO.md`).
- [ ] `.env`: `DATA_DATE=2026-11-26`. Decide token mode: the laptop runs `TAGWERK_DEV=1` (no token). If `API_TOKEN` is
      set instead, open every page once as `?token=<API_TOKEN>` **before** recording, and never record the URL bar
      while the token is in it.
- [ ] `ANTHROPIC_API_KEY` empty for recording, so structuring uses the deterministic German rules that
      `tests/test_demo_phrases.py` verifies (Claude path is real but only tested with a fake client). If the key is set,
      rehearse every phrase again.
- [ ] `docker compose up -d neo4j`.

Clean state before every take that changes data
- [ ] `.venv/bin/python scripts/reset_demo.py` (resets Hörsaal results, keeps `cache/` so replays survive).
- [ ] `~/tw-restart.sh`, then `curl localhost:8080/health` shows `"graph":"Neo4jStore"`.
- [ ] Warm the models once with a throwaway clip, then reset and restart again.
- [ ] `PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests/test_demo_phrases.py` passes.

Replay entry for the hero walk (once)
- [ ] Upload the hero clip on `/upload` (zone Zuschauerraum). The API copies the video (under 300 MB) to
      `cache/<capture_id>/media/`.
- [ ] Add `{"id": "<capture_id>", "label": "Rundgang 26.11.: Reihe A, Lautsprecher, Leinwand, 2× Trockenbau krank"}`
      to `demo_replays` in `seed/project.json`; reset; confirm it appears in the ▶ Abspielen picker on `/graph`
      (`GET /api/replays`).
- [ ] Check which phrases Whisper actually caught in "Erfasst"; if one is missed, re-record that line rather than
      captioning a change that did not happen.

Browser and screen
- [ ] Chrome, clean profile (no extensions, no bookmarks bar), notifications off (macOS Focus mode), dock hidden.
- [ ] Window exactly 1920×1080 content area (record at that size or at 2× and downscale); browser zoom 110-125 % so
      KPI numbers are readable on a phone screen; mouse cursor enlarged; click highlighting on.
- [ ] Header shows the green live dot and **no amber "Demo-Daten" badge** (the badge means `/api/v2` was unreachable
      and the app fell back to mock data; never record that as "live").
- [ ] Open tabs in order: `/app#/dashboard`, `/graph` (replay), `/app#/report/2026-11-26`, `/site` on the phone.
- [ ] Record the dashboard twice: once before the replay (morning state) and once after (forecast moved).

Fallbacks (from `docs/DEMO.md`)
- [ ] Upload or GPU fails: use the replay (no GPU, network or Claude needed).
- [ ] GPU worker down: API runs speech/vision in-process (slower; fine for a recording).
- [ ] Everything down: rebuild, do not fake screens. Mock mode (`?mock=1`) exists for UI development only.

---

## 5. Visual style

Match the app (`web-app/src/index.css`, shadcn/ui neutral theme):

- **Palette.** Mostly neutral: background white `oklch(1 0 0)`, foreground near-black `oklch(0.145 0 0)` (#0A0A0A),
  muted surfaces `oklch(0.97 0 0)` (#F5F5F5), borders `oklch(0.922 0 0)` (#EBEBEB), muted text `oklch(0.556 0 0)`
  (#737373). Semantic accents taken from the UI: emerald (live dot, confirmed / target reached), amber (begun,
  proposals, Demo badge), red `oklch(0.577 0.245 27.3)` (delay, open defects). Use colour only to mean these things;
  everything else stays black/white/grey.
- **Type.** Geist Variable (bundled in the app via `@fontsource-variable/geist`). Titles Geist Semibold, tight
  tracking; captions Geist Medium. Numbers in tabular figures.
- **Shapes.** Cards with 10 px radius (`--radius: 0.625rem`), 1 px #EBEBEB border, no heavy shadows. The logo is the
  app's black 28 px rounded square with a white bold "T" + "Tagwerk" wordmark.
- **Lower-thirds.** Left-bottom white card, 10 px radius: line 1 clock in tabular Geist Semibold ("10:30"), line 2
  German beat name ("Ausfall") with English gloss in muted grey ("crew absence"). 0.3 s slide-in, 3 s hold.
- **Callouts.** Thin 1.5 px black outline boxes with a short label tab, pointing at real UI; red outline only for
  delay, amber dashed outline for proposals (mirrors the dashed proposal nodes in the graph).
- **Captions.** Burned in, bottom centre, Geist Medium ~44 px at 1080p, white on a 70 % black rounded box, max two
  lines, 42 characters per line; German original in small grey italics above the English line only for the dictation
  shots (#1, #7, #8, #11-13) so judges see the exact phrase the system parsed.
- **Phone footage framing.** Vertical clips in a 9:16 phone frame on the left third of a 16:9 canvas, with the matching
  screen state on the right two thirds whenever cause and effect should be visible together (#2, #12, #14, #15).
- **Music.** Light, steady, optimistic minimal electronic or acoustic-electronic, 90-105 BPM, no vocals, ducked to
  -20 dB under speech and VO; one soft swell on the forecast change (#14) and on the PDF (#18). Use a track whose
  licence clearly allows public use (check the specific licence before publishing).
- **End card (3 s).** White, centred logo, tagline "Walk. Talk. Done.", one-line value prop "Voice and video to
  Bautagebuch, schedule impact and exports", team names, repo URL, small tech strip. Disclaimer line at the bottom
  (section 6).

---

## 6. Human in the loop, disclaimer, risks

**Human-in-the-loop moments to make visible (all real):**
1. Vision only proposes; voice or a typed note confirms (structuring rule). Show the dashed "nur Bild" proposal (#15).
2. One-tap confirmation in `/site` (`POST /api/elements/{id}/confirm`, counts like voice evidence) (#15).
3. Every work-done row in the Tagesbericht carries the spoken quote it came from, so the Bauleiter can check it (#17).
4. The report ends with signature lines for Bauleitung and Auftraggeber; nothing is sent automatically (#18).
5. Element states only move up, and every change keeps its source capture, so nothing is silently overwritten.

**Legal disclaimer placement.** The challenge says no legal advice. Show a small, readable line (Geist Regular,
~24 px, muted grey) for at least 3 s in shot #18 and again on the end card:
"Tagwerk documents and drafts. It is not legal advice; the site manager reviews and signs every report and notice."
In the roadmap shot (#19), add "drafts for review, not legal advice" right under the Behinderungsanzeige line, and
do not mention VOB/B deadlines as something the tool enforces.

**Risks and mitigations**

| Risk | Mitigation |
|---|---|
| Live processing fails or is slow during a take | Record from replay of a cached capture; split takes; the video is edited, so a failed take is simply re-shot after `reset_demo.py`. |
| Whisper mishears a dictation line, so a caption claims a change that did not happen | Check "Erfasst" after the hero upload; re-record the line; only caption what the screen shows. |
| Demo-Daten (mock fallback) recorded by accident | Check the header before every take: green dot, no amber badge. |
| Overclaiming letter drafts, Word export, email/minutes ingestion, automatic correspondence | Only in the roadmap card (#19), visually marked "ROADMAP"; VO says "next". |
| Overclaiming Claude | Say "Claude structuring with a rule-based fallback"; the recording uses the rules. Do not say the AI "understands everything"; pronouns are not resolved by the rules. |
| Overclaiming P6 / GAEB integration | Say "exports P6 XML and GAEB X83/X84"; the P6 XML has not been imported into a real Primavera yet (release notes), so do not show a Primavera screen. |
| Overclaiming accuracy of vision | Say vision proposes; release notes list weak recall on walls and false positives. |
| Forecast presented as certainty | Use the app's own framing: "projection from today's evidence". |
| Copyright / privacy | Do not use the YouTube screen recording; blur or get consent for people in the phone walk; licensed music only. |
| Numbers on screen differ between takes | Always reset before data-changing takes; record morning and afternoon dashboard states in one session. |
| Token leaks in the URL bar | Use `TAGWERK_DEV=1` on the recording machine or hide the URL bar; never record `?token=`. |

---

## Sources

- Devpost, video-making best practices: https://help.devpost.com/article/84-video-making-best-practices
- Devpost blog, 6 tips for a hackathon demo video: https://info.devpost.com/blog/6-tips-for-making-a-hackathon-demo-video
- recorded.app, how to record a winning hackathon demo video: https://recorded.app/en/blog/hackathon-demo-videos/
- AngelHack, 10 hackathon demo tips: https://angelhack.com/blog/10-tips-to-help-you-rock-your-next-hackathon-demo/
- hackathon.com, creating the best demo video: https://tips.hackathon.com/article/creating-the-best-demo-video-for-a-hackathon-what-to-know
- M&S Akademie, Was macht ein Bauleiter (typical day): https://m-s-akademie.de/wordpress/was-macht-ein-bauleiter/
- Deutscher Bauzeiger, Jour fixe: https://www.deutscher-bauzeiger.de/bauen/bauleitung/baubesprechung/jour-fixe/
- GREENOX, Bautagebuch Pflicht und Inhalt: https://greenox-group.de/bautagebuch/
- Baugrid, Bautagebuch führen: https://www.baugrid.de/blog/bautagebuch-fuehren-pflicht-vorlage-digital
- nevaris, Behinderungsanzeige nach VOB/B: https://www.nevaris.com/blog/behinderungsanzeige/
- lb-consult, Behinderungsanzeige nach § 6 VOB/B: https://www.lb-consult.com/ratgeber/behinderungsanzeige-vob

(Several Bautagebuch and Behinderungsanzeige sources are software vendors; the facts used here, the content list and
the "unverzüglich, schriftlich" requirement, are consistent across them.)
