# Tagwerk: pitch deck design brief (Challenge B)

Status: brief only, no slides built. Every product claim below is checked against the repo as of 2026-11-21
(`README.md`, `docs/DEMO.md`, `docs/RELEASE-NOTES.md`, `docs/UI-V2-CONTRACT.md`, `docs/REVIEW-2026-11-21.md`,
`web-app/`, `web/`, `tagwerk/`). Anything not in the code is labelled **roadmap**. Repo paths are relative to the
repo root.

---

## 1. Audience, judging criteria, core message, narrative arc

### Audience
- **Challenge B jury.** Expect a mix of construction practitioners (site managers, a contractor or client
  representative, maybe a construction lawyer) and technical or VC judges. Practitioners will check whether the
  German terms are right (Bautagebuch, Behinderungsanzeige, VOB/B, AT = Arbeitstage). Technical judges will ask
  how it is built and what is real.
- **What they have already seen:** many "ChatGPT writes your letter" prototypes. Tagwerk stands out by
  grounding every sentence in evidence (who said what, when, on which element and contract position), not by
  producing text.

### Likely judging criteria (typical hackathon rubric)
| Criterion | Typical weight | What the deck must prove |
| --- | --- | --- |
| Problem clarity and relevance | ~15-20 % | Documentation burden plus the legal stakes of late or missing notices |
| Innovation | ~25-30 % | Voice/video becomes an evidence graph tied to GAEB and P6, not free text |
| Technical execution, working MVP | ~25 % | A live or replayed demo inside the first 90 s of the demo slot; tests; real dataset |
| Impact and feasibility | ~25 % | Hours saved, claims protected, runs on one laptop GPU, fits German standards |
| Presentation | ~20 % | One clear story: "a day in the life" |

Weights are indicative ([hackhq.io judging guide](https://hackhq.io/planning-guide/judging)). Judges' advice
is consistent: lead with the problem, scope down to one feature done well, and make the demo the centrepiece,
working within about 90 seconds
([JetBrains, "How to Win a Hackathon: Notes From the Judging Table"](https://blog.jetbrains.com/ai/2026/06/how-to-win-a-hackathon-notes-from-the-judging-table/);
[HackerEarth, 10 tips](https://www.hackerearth.com/blog/10-tips-win-hackathon)). Always have a backup recording.

### Core message (one sentence)
**"The site manager talks while walking the site; by evening Tagwerk has filed the evidence against the contract
and schedule, filled in the Bautagebuch, and flagged the delay that needs a notice."**

German tagline option for the title slide: *"Reden statt tippen: der Tagesbericht schreibt sich beim Rundgang."*

### Narrative arc (problem, then turn, then proof)
1. **Pain:** 16:30, the Bauleiter is back in the container with photos, voice memos and a paper diary, and two
   hours of typing ahead.
2. **Stakes:** if a hindrance is not reported in writing without undue delay, claims for extra time and money
   can be lost (VOB/B §6).
3. **Turn:** what if the walk itself were the documentation?
4. **Demo:** film and talk for 30 s, then show the live graph, dashboard, forecast shift and auto-filled
   Tagesbericht.
5. **Why it is trustworthy:** evidence rules (voice confirms, vision only proposes), contract/schedule linkage,
   human sign-off.
6. **Where it goes:** from a detected deviation to a drafted Behinderungsanzeige or Mehrkostenanzeige
   (roadmap), positioned against Capmo, PlanRadar, Procore and Buildots.
7. **Close:** "Tagwerk: the day's work, documented."

---

## 2. Slide-by-slide outline (12 slides, about 5:00)

Timing budget: 2:10 of slides and narration, 2:00 of demo, about 0:50 spare. If the demo runs live from the
phone, start the upload during slide 2 (processing takes about 8 s for the result and about 60-75 s for the 3D,
per `docs/DEMO.md` "3-Minuten-Demo"). Put up a Wi-Fi-loss fallback: `curl … -F replay_of=uw-video` or the
`/graph` replay picker.

| # | Title | Key message | On-slide content | Visual | Speaker-note gist | Time |
|---|---|---|---|---|---|---|
| 1 | **Tagwerk** | The site walk becomes the documentation | Logo (black rounded square, white "T", from `web/app/favicon.svg`), tagline, team names, "Challenge B: AI Site Manager Assistant" | Full-bleed photo: a site manager on a site holding a phone (own photo or a keyframe from `demo-media/user_walk.mp4`) | One sentence on who you are; "we built this for the person who leaves the site last." Start the phone upload now if demoing live. | 0:15 |
| 2 | **16:30 im Baucontainer** | Documentation eats the site manager's day | Three scattered inputs (photos, voice memos, diary, emails) leading to one empty Bautagebuch form. Stat: "35 % of working time goes to non-productive work such as searching for project data and fixing rework (FMI/PlanGrid, ~600 construction leaders)." | Messy collage turning into a clean form | Tell it as a day-in-the-life moment. Do not claim the 35 % is all documentation (see section 5). | 0:25 |
| 3 | **Ein vergessener Satz kostet Wochen** | Late notices lose claims | VOB/B §6(1): hindrance must be reported "unverzüglich schriftlich". Without it, extension of time and compensation may be lost. Same pattern for Mehrkostenanzeige (§2) and Bedenkenanzeige (§4(3)). | Timeline: 10:00 excavator idle, 10:05 a quick call, nothing in writing; weeks later the claim is rejected | The evidence exists (it was said out loud on site) but never reaches a formal document. That is the gap. | 0:20 |
| 4 | **Reden statt tippen** | One capture, three outputs | Left: phone with a 30 s video plus voice. Right: (1) live evidence graph, (2) dashboard with forecast, (3) Tagesbericht PDF. Small label: "Notice drafts: roadmap". | Simple three-way fan-out diagram | The promise in one breath. Hand over to the demo. | 0:15 |
| 5 | **Demo: ein Tag auf der Baustelle** | It works, live | Clean slide with only a QR/URL and "LIVE", or go straight to the browser | Browser: `/app#/dashboard`, then Live-Graph, then 3D, then Tagesbericht | Follow DEMO.md "3-Minuten-Demo": the recording appears under "Aufnahmen des Tages"; changes with quotes; "zwei Mann vom Elektriker sind krank" moves the forecast; Gantt delay in red; open the Tagesbericht and print it to PDF. Fallback: cached replay `uw-video` or the Hörsaal `cap-e2e-2`. | 2:00 |
| 6 | **Vom Satz zum Bauteil** | How it works | Pipeline strip: Phone upload, ffmpeg, Whisper (int8), YOLO11s + YOLO-World + ArUco (+ RelateAnything), weather (Open-Meteo), structuring (Claude tool schema or German/Dutch/English rules), project state, Neo4j, websocket. "Runs on one GTX 1060 laptop." | Horizontal pipeline using the app's semantic colours | Stress "Claude is optional; rule fallback works offline" and "replay with no GPU or network". | 0:20 |
| 7 | **Beweis statt Behauptung** | Trustworthy by design | Three rules: (1) voice/note confirms, vision only proposes (dashed violet nodes); (2) element states only go up, every change keeps its quote and timestamp; (3) linked to GAEB position and P6 activity. Mini task graph: GAEB, activity, zone, recording, event. | Screenshot of the `/app#/graph` task graph (TaskGraph colours) | This answers the jury's hallucination worry. Claude cannot claim voice evidence without a matching quote (`enforce_evidence`, review fix 3). | 0:20 |
| 8 | **Abweichung erkannt, bevor sie teuer wird** | Plan vs actual, automatically | Forecast chart: baseline vs forecast finish, with the shift caused by the absence. KPI chips: Ist/Soll %, SPI, Prognose-Ende, Verzug in AT, offene Mängel. Callout: "Rehearsed: 'zwei Mann krank' moved the forecast 30.11. to 01.12. (12.6 s incl. cold start)." | Line/Gantt chart (see section 4) | Forecast = remaining work simulated day by day with crew minus absences; successors shift. Labelled "projection from today's evidence". | 0:20 |
| 9 | **Vom Verzug zum Anzeigen-Entwurf** | The next step: drafts, not legal advice | Today (implemented): the Tagesbericht section "5. Behinderungen / Verzug" lists activity, cause, +AT. **Roadmap:** one click turns it into a Behinderungsanzeige draft (project, contract, hindering circumstance, since when, affected works, expected effect on schedule), plus Mehrkosten- and Bedenkenanzeige templates; Word/PDF; the site manager reviews and signs. | Split: real report section screenshot on the left, mocked letter draft on the right clearly stamped "Roadmap / Entwurf" | The fields a valid notice needs are exactly what Tagwerk already stores. Say "drafting support, no legal advice". | 0:20 |
| 10 | **Challenge B: abgedeckt** | Fit with the brief | Compressed version of the mapping table (section 3): green tick = implemented, half = partial, outline = roadmap | Checklist grid | Be honest: letter drafting and minutes/email summaries are roadmap. | 0:15 |
| 11 | **Positionierung** | Only tool linking voice evidence to contract and schedule without BIM | 2x2 (section 5). Proof row: 2,082-element real BIM project (Schependomlaan), 100 tasks; P6 XML, GAEB X83/X84, .ics exports; 83+ automated tests | 2x2 matrix plus a strip of numbers | Capmo/PlanRadar do voice-to-diary; Buildots/Doxel do camera progress against BIM; Tagwerk ties the spoken evidence to the BoQ and schedule. | 0:20 |
| 12 | **Tagwerk** | Close and ask | "Next 4 weeks: notice drafts, corrections with audit trail, pilot with one Bauleiter." Contact/QR. Disclaimer line: "Entwurfsunterstützung, keine Rechtsberatung." | Return to the title photo, darkened | End on the core sentence. | 0:15 |

Total about 5:00 (2:10 slides + 2:00 demo + 0:50 buffer for transitions and questions).

---

## 3. Challenge B mapping: objective/use case to Tagwerk feature

Legend: **Implemented** (in code and tested or rehearsed), **Partial** (some of it is in code), **Roadmap** (not in code).

| Challenge B objective / use case | Tagwerk feature | Status | Repo reference |
|---|---|---|---|
| Voice/text capture via mobile | Phone browser upload of video/photos/audio plus typed note; Whisper int8 transcription (German/Dutch/English) | Implemented | `web/upload/index.html`, `tagwerk/api/app.py` (`POST /captures`), `tagwerk/pipeline/speech.py` |
| Automatic daily report analysis vs plan | BoQ-weighted activity %, SPI, day-by-day forecast with absences, FS/SS successors, delay per activity with cause | Implemented | `tagwerk/project.py`, `tagwerk/pipeline/loop.py`, `tagwerk/v2.py` (`/api/v2/day`), `web-app/src/components/KpiStrip.tsx`, `dashboard/Gantt.tsx` |
| Daily report (Bautagebuch) generation | Auto-filled German Tagesbericht: work done with quotes, crew present/absent, 3D-scan inventory, events, delays, lookahead, photos, weather, signature line | Implemented | `tagwerk/report.py`, `/api/v2/report`, `/export/report.html`, `web-app/src/components/report/ReportView.tsx` |
| PDF / Word export | PDF via browser print (A4 print CSS); Word | Partial (PDF via print only; Word is roadmap) | `web-app/src/index.css` (`@media print`), `tagwerk/report.py` |
| Smart letter drafts from keywords (Behinderungs-, Mehrkosten-, Bedenkenanzeige) | Data for the notice exists (cause, affected activity, +AT, quote, time); no letter generator | Roadmap (data layer ready) | Basis: ReportView section "5. Behinderungen / Verzug"; `tagwerk/v2.py` delays/events |
| Structured summaries of diary, minutes, emails | Voice/notes become structured events (absence, delay, defect, delivery, labour); minutes/email ingestion not built | Partial (voice/notes only) | `tagwerk/pipeline/structure.py`, `contracts/structured.schema.json` |
| Automatic correspondence when deviations are detected | Deviations detected live (delay, absence, weather constraint events, defects) and pushed to the dashboard by websocket; outgoing correspondence not built. `.ics` export of captures and daily reports (not a letter) | Partial (detection yes, correspondence roadmap) | `tagwerk/v2.py` (weather events), `tagwerk/events.py`, `web-app/src/components/dashboard/EventsTile.tsx`, `tagwerk/pipeline/export.py` (`captures_to_ics`) |
| Human in the loop | Vision only proposes, voice/note confirms; proposals shown dashed "nur Bild, zu bestätigen"; manual confirm on `/site`; Claude output validated, rule fallback. Correct/reject with audit trail not built | Partial | `tagwerk/pipeline/structure.py` (`enforce_evidence`), `/api/elements/{id}/confirm`, `web/site/index.html`, `TaskGraph.tsx`; roadmap: `tagwerk-fix-plan.md` B1/B2 |
| Use case: form assistant ("excavator idle since 10 am due to …") | Absences by trade, delays, defects, deliveries recognised from speech; idle equipment and hindrance-notice form not built | Partial | `tagwerk/pipeline/structure.py` (rules), `tests/test_demo_phrases.py` |
| Use case: daily report analysis | See row 2 | Implemented | as above |
| Use case: documentation drafts from photos/notes | Photos/keyframes plus note go into the report; 3D room scan with labelled objects and relations ("neben Wand") | Implemented | `tagwerk/pipeline/sfm.py`, `vision.py`, `/api/v2/scan3d/{cid}`, `web-app/src/components/scan/ScanView.tsx` |
| Use case: minute summaries | Not built | Roadmap | none |
| Use case: deviation alerts | In-app: red delay in Gantt, events tile with severity badges, live websocket refresh. Push/email alerts not built | Partial | `EventsTile.tsx`, `Gantt.tsx`, `/events` websocket |
| Deliverable: prototype with chat/voice and PDF/Word export | Voice and video upload, not chat; PDF via print | Partial | `web/upload/index.html`, `/export/report.html` |
| Deliverable: "A day in the life" demo | 3-minute rehearsed runbook with fallbacks | Implemented | `docs/DEMO.md` ("3-Minuten-Demo") |
| No legal advice | Disclaimer not yet in the UI | Roadmap (add to report footer and deck) | none |
| Beyond the brief: link to contract and schedule | GAEB X83/X84 and P6 XML export, element to BoQ position to activity mapping, Neo4j graph | Implemented (P6 XML not yet imported into a real Primavera) | `tagwerk/pipeline/export.py`, `seed/mapping.csv`, `tagwerk/graph/sync.py` |

---

## 4. Visual identity

The deck should look like the product. The React app (`web-app/`) uses shadcn/ui's neutral theme with Geist, and
colour is used only for meaning (state, severity, evidence type). Keep that discipline: monochrome base, semantic
accents.

### Palette (from `web-app/src/index.css`, `TaskGraph.tsx`, `BimView.tsx`, `SceneView.tsx`)
| Role | Hex | Source / use |
|---|---|---|
| Ink (text, logo) | `#0A0A0A` / `#171717` | shadcn `--foreground` oklch(0.145 0 0); favicon fill `#171717` |
| Background | `#FFFFFF` | `--background` |
| Surface / muted | `#F5F5F5` | `--muted`, not-started nodes |
| Border | `#E5E5E5` | `--border` oklch(0.922 0 0) |
| Muted text | `#737373` | `--muted-foreground` oklch(0.556 0 0) |
| **Brand accent: recording/voice** | `#2563EB` (dark `#1D4ED8`) | Recording nodes in the task graph; BIM selection. Use as the one accent colour across the deck |
| Done / confirmed | `#16A34A` (tint `#DCFCE7`) | Done activities, PROGRESSED edges, BIM "target state reached" |
| In progress / warning | `#F59E0B` / `#D97706` (tint `#FEF3C7`) | Started elements, medium severity, "Demo-Daten" badge |
| Delay / critical | `#DC2626` (tint `#FEE2E2`) | Delay outline, high severity, "+N AT" |
| Proposal (vision only) | `#8B5CF6` (tint `#F5F3FF`) dashed | "Vorschlag (nur Bild, zu bestätigen)" |
| Zone / place | `#7DD3FC` on `#F0F9FF` | Zone nodes |
| 3D dark stage | `#141416` + cyan `#22D3EE` | 3D scan viewer background and camera path |

Rules: at most one semantic colour per slide besides the accent blue. Red appears only where there is a delay
or claim risk. Dark slides (title, demo, close) use `#141416` to echo the 3D viewer.

### Typography
- **Geist** (variable, bundled via `@fontsource-variable/geist`): headings in Semibold/650 at 40-48 pt, body
  Regular at 18-22 pt, KPI numbers in Semibold with tabular figures at 60-96 pt.
- Small caps-style labels (12-14 pt, uppercase, +0.04em tracking, muted grey), as in the old dashboard's
  `.kpi .label`.
- German UI terms stay German in italics or chips (*Tagesbericht*, *Behinderungsanzeige*, *Verzug +1 AT*);
  narration is in English if the jury is international.
- Fallback when Geist is missing in PowerPoint: Inter, then system sans. Embed the font or export to PDF.

### Layout grid
- 16:9, 1920×1080, 12-column grid, 96 px outer margins, 24 px gutters.
- Title band at top-left (y 96-200), content area below; one idea per slide.
- Cards with 10 px radius (`--radius: 0.625rem`), 1 px `#E5E5E5` border, no drop shadows (shadcn look).
- Screenshots in a thin browser frame or a phone frame with 16 px radius; never stretched.

### Iconography
- **Lucide** line icons (the app uses `lucide-react`), 2 px stroke, 24/32 px: `Mic`, `Video`, `FileText`
  (Tagesbericht), `CalendarClock`, `TriangleAlert`, `Users`, `CloudRain`, `Network`, `Box` (3D), `Check`.
- Logo: black rounded square with a white "T" (`web/app/favicon.svg`); usable as a bullet or watermark.

### Imagery and screenshot list (capture at 1920×1080, Hörsaal or `userwalk` project, after `reset_demo.py`)
Do not show the amber "Demo-Daten" badge, which appears when the app falls back to mock data. Capture against a
live API.
1. `/app#/dashboard` (today 26.11.): KPI strip plus the three tiles; one recording expanded with transcript,
   quotes and changes.
2. `/app#/dashboard`: Gantt view with the red delay and today line; activity detail sheet open (GAEB positions,
   cause).
3. `/app#/graph`: task graph (GAEB, activity, zone, recording, event, proposal) with the replay video panel on
   the left, mid-replay, captions highlighted.
4. `/app#/scan/uw-video`: 3D point cloud, camera path, labelled objects, one label clicked to show relations.
5. `/app#/report/2026-11-26` and `/export/report.html`: the A4 Tagesbericht, including section 5
   "Behinderungen / Verzug".
6. `/app` on :8081 (Schependomlaan), BIM-Modell tab: building coloured by state; two frames (08.07. and
   24.07.2015) for a "watch it grow" pair.
7. `/upload` on a phone (portrait, in a phone frame).
8. Legacy pages, only as backup or appendix: `/graph` (vis-network live graph with the ▶ Abspielen picker),
   `/dashboard` (old Bauleiter dashboard), `/site` (tap-to-confirm states), `/scan`.
9. Photo: a real site walk keyframe from `user_walk.mp4` (own footage) for slides 1 and 12.

### Chart ideas
- **Forecast shift (slide 8):** two horizontal bars per affected activity (baseline vs forecast), with a
  hatched slip segment like `Gantt.tsx` (`#g-hatch`) and an annotation "2× Elektriker krank, +1 AT". Real
  rehearsed numbers: forecast 30.11. to 01.12.2026, A1080 28.9 % to 34.4 % (`docs/RELEASE-NOTES.md`).
- **Progress curve:** planned vs actual % over the day slider (Hörsaal plan history 09.-19.11. plus captures).
- **SPI gauge or chip:** Schependomlaan replay 1.09 to 1.10, Ist 83.7 % to 84.6 % (`docs/DEMO.md`). Note on the
  slide that these are planned-state snapshots, not as-built data.
- **Time saved (slide 2 or 12):** a simple bar "today: X h typing" vs "with Tagwerk: review and sign".
  Present it as a target hypothesis, not a measured result.
- Use the semantic palette only; no 3D charts, no pie charts.

### Tone
Calm, factual, practitioner-first. Short German site phrases quoted verbatim ("Stuhlreihe A ist montiert",
"zwei Mann vom Trockenbau sind krank"). Claims carry a source or the label "rehearsed" / "roadmap". No
"revolutionary", no "AI lawyer".

---

## 5. Proof points, stats, competitor positioning

### External stats (with confidence)
| Claim for the deck | Source | Confidence / caveat |
|---|---|---|
| Construction leaders spend 35 % of their time (>14 h/week) on non-productive activities: looking for project data (5.5 h), conflict resolution (4.7 h), mistakes and rework (3.9 h); survey of ~600 leaders, 2018; ~$177 bn US labour cost | FMI / PlanGrid "Construction Disconnected" (2018), [PDF](https://pg.plangrid.com/rs/572-JSV-775/images/Construction_Disconnected.pdf); [Autodesk summary](https://www.autodesk.com/blogs/construction/construction-disconnected-fmi-report/); [Construction Dive](https://www.constructiondive.com/news/industry-could-be-overspending-177b-per-year-study-finds/529450/) | High as a figure. It is not "documentation time"; use the wording "non-productive work such as searching for data and rework". Many vendor blogs misquote it |
| German trades lose on average 1.2 working days per week to documentation duties (survey of 1,097 businesses) | BENZ24 survey via [openPR](https://www.openpr.de/news/1292604/Dokumentationsaufwand-kostet-Handwerker-12-Arbeitstage-Woche-BENZ24-digitalisiert-Baustellen-Buerokratie.html) | Medium-low: vendor survey, Handwerk not Bauleiter. Use only as "industry surveys suggest" |
| Bauleiter spend 3-5 h/week reworking documentation afterwards, ~200 h/year | [digital-magazin.de](https://digital-magazin.de/ki-baustellendokumentation/); similar 5 h/week at [bau-master.com](https://bau-master.com/baublog/digitales-bautagebuch/) | Low: unnamed surveys, vendor blogs. Do not put on a slide as hard data |
| Peer-reviewed German time study of site managers (activity shares in %) | TU Wien diploma thesis, Chriti (2015), [repositum.tuwien.at](https://repositum.tuwien.at/bitstream/20.500.12708/3040/2/Chriti%20Manuela%20-%202015%20-%20Aufnahme%20des%20zeitlichen%20Arbeitsaufwandes%20und%20Ermittlung...pdf) | Not yet read; the team should pull the documentation share from it if a German academic figure is wanted |
| VOB/B §6(1): the contractor must report a hindrance to the client "unverzüglich schriftlich" (without culpable delay, §121 BGB); already when it threatens; addressed to the client, not only the architect; content: circumstance, since when, affected works, expected effect on schedule. Without notice, extension of time (§6(2)) and compensation/damages (§642 BGB, §6(6)) can be lost unless the client obviously knew | [hoai.de](https://www.hoai.de/gesetze-recht/vob/behinderungsanzeige/), [forum-verlag.com](https://www.forum-verlag.com/fachwissen/bau-und-gebaeudemanagement/behinderungsanzeige/), [nevaris.com](https://www.nevaris.com/blog/behinderungsanzeige/) | High on the norm text; practice guides, not commentary. Whether e-mail counts as "schriftlich" is disputed: say "documented delivery" |
| Mehrkosten/Nachträge: VOB/B §2(5)/(6); additional work under §2(6) must be announced before execution. Bedenkenanzeige: §4(3) | Standard VOB/B structure (verify wording on the slide against the VOB/B text) | Medium: from domain knowledge, not re-fetched in this research |

### Internal proof points (repo-grounded)
- Rehearsed 3-minute demo: 70 s walk video done after **8 s**, 3D after **61 s** (30 frames registered, 21
  objects) on a GTX 1060 laptop (`docs/DEMO.md`).
- End-to-end test: E-ROW-A confirmed with evidence `both`; A1080 28.9 % to 34.4 %; forecast 2026-11-30 to
  2026-12-01 from "zwei Mann krank"; **12.6 s including cold model load** (`docs/RELEASE-NOTES.md`).
- Real open BIM data: Schependomlaan import with **2,082 elements, 100 real tasks, 6 storeys**; the Dutch note
  confirms 91 walls (`README.md`, `docs/RELEASE-NOTES.md`). The BIM viewer shows 3,504 elements, 2,081 linked
  (`docs/DEMO.md`).
- Exports: P6 XML (baseline and progress, FS+SS), GAEB DA XML X83/X84, Outlook .ics, A4 Tagesbericht.
- Tests: 83 passed / 1 skipped at the release (`docs/RELEASE-NOTES.md`); the later review baseline reports 113
  passed / 3 skipped (`tagwerk-fix-plan.md`). Quote whichever the current `pytest` run shows on demo day.
- Works offline: rule-based structuring without Claude, bundled fonts and vis-network/three.js, replay with no
  GPU or network.

### Competitor positioning
Competitor features are from vendor pages and third-party comparisons, not verified hands-on.

| Tool | What it does (per sources) | Gap Tagwerk fills |
|---|---|---|
| **Capmo** (DE) | "KI Diktiergerät": speak observations, get a structured Bautagebuch draft; voice to tickets; weather auto-filled ([Capmo support](https://support.capmo.com/sprechen-statt-tippen-im-bautagebuch-mit-der-capmo-ki), [Capmo Bautagebuch](https://www.capmo.com/en/produkt/bautagebuch)) | No element-level link to the GAEB BoQ and P6 schedule, no forecast from spoken absences (not seen in sources) |
| **PlanRadar** (AT) | AI form/report builders, voice-to-ticket, AI agents ([PlanRadar 2026 comparison, vendor](https://www.planradar.com/us/the-15-best-construction-management-software-tools-in-2026-compared-honestly/)) | Ticket/defect-centric; schedule impact not shown |
| **Procore** | Daily Log with ~20 entry types, weather, AI summaries / Daily Log Agent; still largely manual field input ([SmartBarrel](https://smartbarrel.io/blog/best-construction-daily-report-apps/), [constructiondailyreportsoftware.com](https://constructiondailyreportsoftware.com/)) | US-centric, heavy; no VOB/GAEB focus |
| **Fieldwire** | Forms and punch lists, daily report from the Business tier ($64/user/mo); limited AI write-ups ([Fieldwire](https://www.fieldwire.com/blog/best-construction-management-software/), [PunchIQ](https://punchiq.ai/resources/best-construction-site-reporting-software)) | Manual capture |
| **Buildots** | Automated progress tracking from 360° helmet cameras vs BIM ([ONES.com](https://ones.com/blog/10-best-ai-tools-for-construction-project-management-in-2026/)) | Needs BIM and hardware; progress only, no diary/notices, no spoken causes (absences, hindrances) |
| **Doxel** | Robot/lidar scans compared to the design model daily ([ONES.com](https://ones.com/blog/10-best-ai-tools-for-construction-project-management-in-2026/)) | Same as Buildots |

**2x2 for slide 11**
- X axis: *capture effort*, from manual forms (left) to passive talk/film while walking (right).
- Y axis: *link to contract and schedule*, from free text (bottom) to element-level BoQ + schedule (top).
- Bottom-left: Fieldwire, Procore Daily Log. Bottom-right/middle: Capmo KI, PlanRadar voice (easy capture,
  weak linkage). Top-left/middle: P6 itself, Procore scheduling (linked, but manual). Top-right but BIM- and
  hardware-bound: Buildots, Doxel. **Tagwerk:** top-right, with the label "works without BIM, captures causes,
  not only progress".
- Footnote: "Positions based on public vendor information, Nov 2026."

---

## 6. Risks and pitfalls

1. **Overclaiming letter generation.** Behinderungs-, Mehrkosten- and Bedenkenanzeige drafting, minutes/email
   summaries, Word export, push/email alerts and correction/reject with audit trail are **not implemented**.
   Mark them "Roadmap" on slides 9, 10 and 12. If you mock a letter, stamp it "Entwurf / Mock-up".
2. **Legal-advice disclaimer.** The challenge says no legal advice. Put "Entwurfsunterstützung, keine
   Rechtsberatung; Prüfung und Versand durch die Bauleitung" on slides 9 and 12 and later in the report footer
   (not yet in the UI). Do not say a draft is "legally sound"; say "contains the elements a §6 notice needs".
   The e-mail form question is disputed, so do not claim e-mail delivery is sufficient.
3. **Claude path maturity.** The Claude structuring path is tested only with a fake client (no API key on the
   laptop; `docs/RELEASE-NOTES.md`). The demo runs on the German rules. Say "LLM-ready with a validated rule
   fallback", not "Claude understands everything". The rules cannot resolve pronouns.
4. **Vision limits.** Vision recall on large surfaces is weak, with false positives. This is why vision only
   proposes; say so before a judge spots it.
5. **Data realism.** The Hörsaal seed is a placeholder. Schependomlaan snapshots are planned states, so SPI is
   inflated and started tasks read 100 %. The P6 XML was never imported into a real Primavera. Do not present
   KPI values from `UI-V2-CONTRACT.md` or `src/mock/` as real results. Hide the "Demo-Daten" badge by using the
   live API.
6. **Licences.** RelateAnything is **AGPL-3.0** (weights under the DINOv3 licence). The Schependomlaan dataset
   is CC BY 4.0 for **academic use** with attribution (`seed/projects/schependomlaan/ATTRIBUTION.md`). Put a
   credit line on any slide showing Schependomlaan. If asked about commercialisation, say RelateAnything would
   be replaced or isolated, and pilot data would come from partner sites (`README.md` "Licences";
   `tagwerk-fix-plan.md` proposes freezing both).
7. **Stats hygiene.** Do not quote the FMI 35 % as "documentation time". Do not use vendor-blog hour figures as
   facts. Cite on-slide in small type.
8. **Demo risk.** Hardware resume can break CUDA (`cuInit 999`), Wi-Fi may fail, and 3D may not finish in time.
   Pre-warm models, keep the `uw-video` cached scan and `cap-e2e-2` replay ready, and have a screen recording as
   the last fallback (`docs/DEMO.md` "Fallbacks"). Do not demo features added in the last hours.
9. **Privacy.** Filming people on site raises GDPR questions. Persons are detected by YOLO (and show up as
   multiple 3D instances). Have one sentence ready: on-premise processing on the laptop, no cloud required in
   rule mode; blurring is roadmap.
10. **Terminology.** Use Arbeitstage (AT), Bautagebuch/Tagesbericht, Auftraggeber/Auftragnehmer correctly. A
    practitioner judge will notice errors.
