# Submission storyboard: 2-minute demo video and 7-slide deck

Hard rules of the submission:
- **Deck:** PDF, max. 7 slides. Problem (short, precise, technical) · Solution (what we built, how it solves it) · Tech stack and architecture.
- **Video:** max. 2:00. Screen recording with voice-over. Must include a live demo of the working prototype and explain the technical approach. Slides allowed, a real demo is required.

Budget: 0:00–0:30 problem, 0:30–2:00 the platform, navigated and clicked. English voice-over and captions; the UI stays German.

## What must come across
1. **How we link:** every site observation is tied to an element, a P6 activity and a GAEB contract position, at the moment it is captured.
2. **The ontology layer:** one graph, GAEB position → activity → element/place → recording → event/proposal (`seed/ontology.yaml`, Neo4j projection).
3. **Why we are different:** voice (or a tap) confirms, the camera alone only proposes; states only go up; every percent is traceable to a sentence. No scanner, no BIM required, runs on one 6 GB GPU laptop.
4. **Alerts and events:** absences, defects, delays are captured as events and attached to the affected activity.
5. **Prediction:** the forecast re-simulates the remaining work (crew minus absences, FS/SS successors) and moves the finish date.
6. **Stakeholders and pipelines:** site manager (phone), Bauleiter (dashboard, daily report, notice draft), office (P6 XML, GAEB, .ics exports).

## The one story (Hörsaal Sanierung, data date Thu 26.11.2026)
Seeded state: on plan. 81.7 % done / 80 % planned, SPI 1.02, finish 01.12., one camera proposal waiting (Stuhlreihe F, Unterkonstruktion).
The site manager sends, zone **Zuschauerraum**:

> Stuhlreihe A ist montiert. Zwei Mann vom Trockenbau sind krank. Kratzer an der Bühne.

Result: Stuhlreihe A 50 → 85 % (bestätigt), 2× Trockenbau krank (absence on A1080), defect logged. Bestuhlung neu 30.11. → 02.12.,
Abnahme 01.12. → 03.12. (+2 AT), cause "2 of 3 Trockenbau absent today". Then one tap on the phone confirms the camera proposal for Reihe F.

On this Mac there is no GPU, Whisper or YOLO, so the note is **typed** (a typed note counts like voice). Never show or say that
speech or vision ran in this recording. The pipeline (Whisper, YOLO11s + YOLO-World, RelateAnything, SfM) is described as the
architecture; real detection output on the host's site footage exists in `docs/design-brief/site-frames/` (`det-*.jpg`, `boxes.json`).

## Shots (file names are the contract between the agents)
Recordings go to `pitch/video/public/rec/<id>.mp4` (H.264, 30 fps, no audio), each with `<id>.json`
(`{"seconds": n, "marks": {"name": seconds, ...}}` for moments the editor needs, e.g. the click or the flip).

| # | Time | id | Source | What is seen | Point made |
|---|---|---|---|---|---|
| P1 | 0:00–0:12 | (clip) `opening-baugrube.mp4` / pit clip | site footage | Real excavation: struts, excavator on rock, dump trailer | A site changes every hour |
| P2 | 0:12–0:22 | (clip) crane clip + four "tool" tiles | site footage + graphics | Diary, schedule (P6), contract (GAEB), claims: four tools, nothing linked | The technical problem: no shared key between observation, schedule and contract |
| P3 | 0:22–0:30 | title | graphics | Tagwerk: capture once, linked everywhere | Solution in one line |
| D1 | 0:30–0:39 | `phone-capture` | phone (app web build, 375×812) | Erfassen: zone Zuschauerraum, typed note, Senden, pipeline steps | One tap on site |
| D2 | 0:39–0:46 | `phone-result` | phone | Result card: green bestätigt, absence, defect | What Tagwerk understood |
| D3 | 0:46–0:58 | `dash-flip` | dashboard :8080 | Dashboard open and green; the capture arrives live; KPI turns red, Gantt bars shift, event cards appear | Alerts, events, prediction |
| D4 | 0:58–1:08 | `dash-trace` | dashboard | Click "Bestuhlung neu": sheet with cause, GAEB position 01.06.0010, recordings; open the recording | How we link |
| D5 | 1:08–1:20 | `dash-graph` | dashboard, Live-Graph tab | The graph: GAEB → Vorgang → Ort → Aufnahme → Ereignis; hover/click the new recording node and the red activity | The ontology layer |
| D6 | 1:20–1:28 | `dash-forecast` | dashboard | Day slider: step back a few days and forward past today (forecast), back to Heute | Past, present, predicted future in one model |
| D7 | 1:28–1:36 | `phone-confirm` | phone, Heute tab | Proposal card (amber) → tap Bestätigen → activity bar moves | Camera proposes, a tap confirms |
| D8 | 1:36–1:45 | `dash-report` | dashboard | Tagesbericht for 26.11.: work done, absence, delays with cause; scroll; Druckversion | Daily report writes itself; office exports |
| D9 | 1:45–1:52 | `dash-bim` | dashboard :8081 | BIM-Modell tab, "Bauablauf abspielen" | With BIM: 2,082 elements |
| T1 | 1:52–2:00 | architecture + close | graphics | Phone → pipeline on one GPU laptop → project state → Neo4j graph → dashboard / P6 / GAEB / .ics; closing line | Technical approach |

The editor may shift a second here or there to fit the voice-over, but the total stays ≤ 2:00 and the demo part stays ≥ 85 s.

## Voice-over (draft; the editor owns the final wording, one line per shot, ids = shot ids)
The user records it in ElevenLabs afterwards; scene lengths follow the clips.
