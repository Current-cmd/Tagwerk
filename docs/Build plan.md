# Build plan

Nov 20, 2026

## Summary

You and Abdullah build, in about 36 hours, a pipeline that turns a pre-filmed walk through the presentation auditorium into a live-growing Neo4j graph, element by element. The graph is tied to a GAEB bill of quantities and a Primavera P6 XML schedule, and it feeds a daily dashboard for the Bauleiter, an updated P6 XML file and an Outlook .ics file. The plan merges five planners' work; where they conflicted, the choice made is stated.

**Fixed constraints**

- **One laptop does everything:** ASUS ROG GL704GM, GTX 1060 Mobile 6 GB (Pascal), i7-8750H, 32 GB RAM, Ubuntu 22.04. torch 2.14.1 + CUDA 12.6 already works. Bring it to the venue, keep it plugged in (battery at 61% health), and close the thesis notebook that holds 1.4 GB of GPU memory. No home server and no tunnel needed.
- **No custom phone app.** Film with the phone's normal camera, then upload the video and photos through a simple web upload page in Chrome (on the phone or the laptop). A plain file upload needs no HTTPS or camera permissions.
- **Scenario:** a fictitious renovation of the auditorium ("Hörsaal Sanierung"), so element-level progress makes sense in a room that already exists. Tell the judges this.
- **Roles in the product:** the site manager uses the tool and owns the tasks; labour is the trades doing the tasks; the Bauleiter gets the daily dashboard.

## Day-by-day plan to Fri 27 Nov, 09:00

The deadline is read as Friday 27 November at 09:00, about six days; confirm, because if it means tomorrow the whole plan changes. The critical path stays: environment → contracts → seed graph → Claude structuring → progress loop → filming and caching.

| Day | You | Abdullah | Checkpoint by evening |
| --- | --- | --- | --- |
| Fri 20 (tonight) | Export both doc tabs to Markdown into the repo as `docs/PLAN.md`; start Claude Code on the environment check | — | `torch.cuda.is_available()` true, Neo4j running in Docker, Whisper int8 check passes |
| Sat 21 | Measure and photograph the auditorium; write `elements.csv` and the ontology YAML | Repo skeleton, contracts and fixtures; FastAPI ingest, upload page, FFmpeg step | A file uploaded in Chrome appears as a Capture node |
| Sun 22 | IFC generator, P6 XML (MPXJ), GAEB (pyGAEB), mapping file, loader | Neo4j writer, websocket, vis-network graph view | Seed chain visible in the graph view; a capture lands on it |
| Mon 23 | Whisper benchmark and glossary; ArUco markers; YOLO11s + YOLO-World | Claude structuring with the enum schema, plus validation | **Checkpoint 1:** one test video goes all the way into the graph |
| Tue 24 | RelateAnything install and vocabulary (geometric fallback ready); state tables | Roll-ups, earned value, forecast, Bauleiter dashboard | **Checkpoint 2:** a voice note moves an activity from 40 to 60%; dashboard renders |
| Wed 25 | Decide the filming route and marker spots from how the app performs; stick up markers; film the real walk; synthetic past days | .ics and P6 XML export, replay button, cached Claude responses | The filmed walk processes and replay reproduces it |
| Thu 26 | **Feature freeze at 12:00** (tag `demo-v1`); deck; rehearse | Bug fixes only; backup screen recording; submission form | Five timed runs under 3:00, one with the API cut off |
| Fri 27 | Venue setup from 07:30 | Submit by 08:00 | Done by 09:00 |

**If time runs short, drop in this order:** (1) the Schependomlaan BIM slice (Wednesday only, if ahead), (2) the P6 XML re-export, (3) RelateAnything on new footage (show cached results), (4) live weather. Never drop the seed chain, voice-confirmed progress, the dashboard or the graph view.

The split by area stays: you take environment, ontology, seed data, vision, progress rules and filming; Abdullah takes the server, upload page, graph view, dashboard, exports and replay. Adjust once his skills are known.

## Workstream A: ontology (about 5 hours, you)

Build on BOT for the spatial backbone, borrow DiCon terms for activities and actors, and use GAEB field names and DIN 276 cost groups for the contract side. Write it once in the Neo4j Ontology Graph Spec (YAML) and enforce it with plain Cypher constraints; don't depend on the spec's young SDK at runtime.

| Standard | Use it for | Verdict |
| --- | --- | --- |
| [BOT](https://w3id.org/bot) (W3C LBD) | Site, Building, Storey, Space/Zone, Element and their containment | Reuse as the backbone |
| LBD PRODUCT | Element type names (wall, slab, door) | Borrow terms |
| [DiCon](https://w3id.org/digitalconstruction) | Activity, Agent/Role, planned vs actual values | Borrow terms |
| ISO 21597 ICDD (basis of DIN SPEC 91350 / DIN 18290-2) | Linksets between IFC, GAEB and schedule | Borrow the idea as relationships; mention ICDD export as future work |
| GAEB DA XML | BoQ position fields (OZ, short text, qty, unit, unit price) | Reuse field names |
| DIN 276 | Cost groups on elements and BoQ positions, for cost roll-ups on the dashboard | Reuse codes |
| buildingSMART Data Dictionary | URIs on element types | Optional |
| ifcOWL, STLB-Bau, DIN SPEC 91400, Brick | — | Skip: too heavy, licensed, or not construction-phase |

**Node labels:** Project, Site, Building, Storey, Zone, Element {globalId, name\_de, name\_en, type, din276, qty, unit, state, aliases}, Marker, BoQPosition {oz, shortText, qty, unit, unitPrice, din276}, Activity {p6Id, name, plannedStart, plannedFinish, pct, forecastFinish}, WBS, Trade, Actor {role: SiteManager | Labour | Bauleiter}, Capture, Observation, Proposal, Note, WeatherReading, Event, DailyReport.

**Relationships** (one agreed set; the planners used different names):

- Space: `HAS_SITE → HAS_BUILDING → HAS_STOREY → HAS_SPACE → CONTAINS_ELEMENT`, plus `ADJACENT_ELEMENT`
- Contract and schedule: `(BoQPosition)-[:SCHEDULED_AS {share}]->(Activity)`, `(Activity)-[:BUILDS]->(Element)`, `(BoQPosition)-[:QUANTIFIES]->(Element)`, `(Activity)-[:IN_WBS]->(WBS)`, `(Activity)-[:PRECEDES {type, lag}]->(Activity)`
- Actors: `(SiteManager)-[:RESPONSIBLE_FOR]->(Activity)`, `(Labour)-[:MEMBER_OF]->(Trade)`, `(Labour)-[:ASSIGNED_TO]->(Activity)`, `(Event {type: absence, trade, count, date})-[:AFFECTS]->(Activity)`, `(Bauleiter)-[:RECEIVES]->(DailyReport)`
- Evidence: `(Actor)-[:CAPTURED]->(Capture)-[:IN_ZONE]->(Zone)`, `(Capture)-[:HAS_NOTE]->(Note)`, `(Capture)-[:UNDER]->(WeatherReading)`, `(Capture)-[:DETECTED]->(Observation)-[:REL {predicate, score}]->(Observation)`, `(Observation)-[:LIKELY_IS {conf}]->(Element)`, `(Marker)-[:TAGS]->(Element)`, `(Capture)-[:PROPOSES]->(Proposal)-[:FOR]->(Element)`, `(Capture)-[:CONFIRMED {fromState, toState, quote}]->(Element)`, `(Capture)-[:RAISED]->(Event)`, `(DailyReport)-[:SUMMARISES]->(Capture)`

**Constraints:** unique `Element.globalId`, `BoQPosition.oz`, `Activity.p6Id`, `Capture.id` (makes retries harmless), `Marker.code`, `Zone.id`; indexes on `Element.aliases` and `Activity.name`.

**DIN 276 codes:** the two planners suggested different codes for the same elements (e.g. walls 340 vs 335, screen 450 vs 456). Check each against the DIN 276:2018 table before seeding.

## Workstream B: seed data (about 8–9 hours, mostly you)

Keep one CSV of auditorium elements as the master and generate everything else from it: a simple IFC (box geometry via IfcOpenShell, real GlobalIds), the P6 XML schedule via MPXJ, and the GAEB files via pyGAEB. One idempotent loader script puts it all into Neo4j.

| # | Step | Tool | Output | Time |
| --- | --- | --- | --- | --- |
| 1 | Measure and photograph the auditorium; sketch a floor plan; plan the filming route | Tape measure, phone | Dimensions, 20–30 photos from the filming positions | 45 min |
| 2 | Element list: 25–35 elements (4 walls, ceiling/acoustic panels, floor, stage, stage stairs, lectern, screen, projector, lighting truss, 2–3 doors, one element per seat row, emergency lights, cable tray, curtain) | Spreadsheet | `elements.csv`: element\_id, global\_id, ifc\_class, name\_de, name\_en, zone, x/y/z/dx/dy/dz, qty, unit, din276, marker\_id, aliases | 1 h |
| 3 | Generate the IFC from the CSV | IfcOpenShell script | `auditorium.ifc` (opens in Bonsai or any viewer) | 1.5–2 h |
| 4 | Schedule "Hörsaal Sanierung": about 10 activities in 3 WBS levels (Rückbau Bestuhlung, Bodenbelag, Akustikpaneele, Elektro/Licht-Traverse, AV-Technik, Bühne, Malerarbeiten, Bestuhlung neu, Abnahme), finish-to-start links, a 3-week baseline ending on demo day, costs; user-defined fields carry GAEB\_OZ and ELEMENT\_IDS | [MPXJ](https://libraries.io/pypi/mpxj) (Python wrapper, needs Java) | `schedule.xml` (P6 XML) | 1.5 h |
| 5 | Bill of quantities: 12–15 positions in 3 lots (Ausbau, TGA, AV) with OZ like 01.02.0030 | [pyGAEB](https://pypi.org/project/pyGAEB/1.7.1/) | `boq.x83` (tender) and `boq.x84` (priced bid) | 1 h |
| 6 | Mapping table | Spreadsheet | `mapping.csv`: oz, activity\_id, element\_id, share (shares sum to 1 per OZ) | 30 min |
| 7 | Loader: constraints → project and zones → elements → BoQ → WBS and activities → links → actors and trades → history → planned value per day; `MERGE` on keys throughout | Python + neo4j driver | Seeded graph | 1.5 h |
| 8 | Three past days of captures (notes, photos, weather from the Open-Meteo archive, labour present, state changes), written through the real pipeline functions, not raw Cypher | Python | History, so the forecast isn't built on one point | 1 h |
| 9 | Optional: Schependomlaan slice for BIM mode — one storey, at most 40 elements; MPXJ auto-detects its schedule format; Dutch names stored as aliases | IfcOpenShell, MPXJ | Second project in the graph | 2 h |

**Check early:** MPXJ-written P6 XML may need small fixes to import into a real Primavera (user-defined field types must exist first). Read it back with MPXJ, and if the site manager can, try an import into her P6.

## Workstream C: capture and AI pipeline (about 13 hours, split)

A video goes in through an upload page; one GPU worker processes it step by step, loading one model at a time to stay inside 6 GB; every step pushes an event so the graph fills in while it runs. Because the main footage is pre-filmed, speed matters less than reliability.

**Upload page (Chrome, phone or laptop):** file picker for video and photos, zone dropdown (remembers the last one), language toggle DE / EN / auto, optional typed note, upload progress bar, retry that reuses the same capture ID.

**Detection for an auditorium:**

| Layer | Model | Finds |
| --- | --- | --- |
| Identity | OpenCV ArUco markers (`DICT_4X4_50`, one A5 print per filmed element) | Exactly which element is in the frame |
| Everyday objects | YOLO11s, pretrained on COCO | person, chair, tv/monitor, laptop, bottle, backpack |
| Room objects | [YOLO-World](https://docs.ultralytics.com/models/yolo-world) with a fixed class list | stage, lectern, projection screen, projector, speaker, lighting truss, cable, door, stairs |
| Relations | RelateAnything with 12 fixed phrases | on, standing on, in front of, behind, next to, above, below, mounted on, attached to, holding, using, blocking |

**Processing steps on the GTX 1060** (one 15 s clip; timings estimated from the planners' 1080 Ti numbers, which roughly doubled):

| # | Step | Est. time | GPU memory |
| --- | --- | --- | --- |
| 1 | Save upload, push capture node | <1 s | – |
| 2 | FFmpeg: 16 kHz mono WAV, 1 frame/s at 960 px, HEIC → JPEG | 1–2 s | – |
| 3 | Whisper (benchmark large-v3-turbo int8 against small; never float16 on Pascal), German/English glossary in the prompt; then unload | 5–15 s | \~1.5–2.5 GB |
| 4 | ArUco markers | <0.5 s | CPU |
| 5 | YOLO11s + YOLO-World on \~15 frames, merged | 3–5 s | \~1.5 GB |
| 6 | RelateAnything ViT-S+ (fp32, no TensorRT) | 3–6 s | \~2 GB |
| 7 | Weather (Open-Meteo) + candidate list from the graph | <1 s | – |
| 8 | Claude Sonnet, structured output | 3–8 s | – |
| 9 | Write to Neo4j, push events | <1 s | – |
|  | **Total** | **\~20–40 s** | \~3.5–4 GB with the three vision models kept loaded; Whisper on the CPU or as the only extra GPU model |

**Claude step:** the system prompt sets the role, the rules (only the given IDs, null when unsure, quote the evidence) and the glossary. The user message holds the zone, weather, active activities, elements in the zone with aliases, marker hits, detections and triplets, with the transcript marked as data. Candidate IDs (at most 80, fixed for the demo so the schema compiles once) are enums in the output schema: people by role and trade, material, work done (element, activity, proposed state, evidence voice/vision/both, quote, timestamp), events (delay, defect, safety, weather), unmatched items. **A rule in code, not the prompt:** a state only changes when the evidence includes voice; vision alone creates a Proposal.

**Environment:** Python 3.12 via uv; `torch==2.14.* --index-url https://download.pytorch.org/whl/cu126`; ultralytics, opencv-contrib-python, faster-whisper, fastapi, uvicorn, neo4j, anthropic, httpx, ifcopenshell, mpxj, pyGAEB; RelateAnything from its repo; ffmpeg; Java; Neo4j in Docker. Check `ctranslate2.get_supported_compute_types("cuda")` shows int8. Download all weights in advance, then set `HF_HUB_OFFLINE=1`. Keys (`ANTHROPIC_API_KEY`, `HF_TOKEN`) live in `.env`, never in the repo. Skip torch.compile (needs a newer GPU).

| If this fails | Do this |
| --- | --- |
| RelateAnything won't install or the weights are gated | Geometric relations from box positions (on, next to, above), marked `source=geometry` |
| YOLO-World misbehaves on Pascal | COCO classes + markers only |
| Whisper turbo too slow or out of memory | Whisper small |
| Claude API down | Cached responses for the filmed clips; keyword rules for anything new |
| Marker not seen | Zone + Claude match; element link marked inferred |

## Workstream D: loop, dashboard, live graph, exports (about 11 hours, mostly Abdullah)

Progress is tracked as fixed states per element that only ever go up, rolled up to activities by quantity, compared against the P6 baseline, and shown three ways: the live graph for the judges, the Bauleiter's daily dashboard, and files back into Primavera and Outlook.

**Element states** (weight in %; an element's % = its highest state reached):

| Element type | States |
| --- | --- |
| Seat row | removed 20 → substructure 50 → installed 85 → checked 100 |
| Wall section | prepared 30 → primed 60 → painted 90 → done 100 |
| Stage | framed 35 → boarded 70 → finished 100 |
| Lighting truss / fixture | mounted 50 → wired 80 → tested 100 |
| Screen / projector | mounted 60 → connected 85 → commissioned 100 |
| Floor area | stripped 25 → levelled 50 → covered 90 → done 100 |

**Numbers:**

- Activity % = quantity-weighted average of its elements' %.
- Budget at completion per activity = sum of linked BoQ positions (qty × unit price × share).
- Planned value = budget × planned % from the P6 baseline dates; earned value = budget × actual %.
- Actual cost = labour hours (crew from voice, "drei Elektriker", × 8 h) × trade rate from a seed table. These rates are invented, so say so, or show earned value only.
- Expected finish = today + remaining work ÷ (productivity × available crew). "Zwei Mann krank" (two sick) lowers available crew, the finish moves, the delay passes on to successor activities, and the activity turns red. Label it "projection from today's evidence".

**Bauleiter dashboard:** a FastAPI-served page with Apache ECharts (NeoDash rejected: the free edition is unsupported and hard to style). Widgets, top to bottom: KPI strip (actual vs planned %, SPI, earned value, forecast vs baseline finish, open defects) · today's captures with photos and quotes · progress per activity vs plan, worst first · red items with cause · defects and events · labour per trade vs plan · weather · planned/earned/actual curve · zone grid coloured by state.

**Site manager view:** today's activities with element chips and their states, tap to confirm a state; daily report page with a sign-off button that releases it to the dashboard.

**Live graph for judges:** vis-network (MIT, runs from a CDN, animates added nodes). Three levels only: activity → element/zone → today's captures, with detections folded into their capture and proposals drawn dashed. Elements change colour grey → amber → green as their state rises. Updates arrive over a websocket.

**Exports:**

- **.ics** for Outlook: one event per capture and one all-day event per daily report; stable UID `capture-<id>@<host>`; all times in UTC (Outlook shifts Europe/Berlin times by an hour without a timezone block).
- **P6 XML back to Primavera:** same ObjectIds as the import, with PhysicalPercentComplete, ActualStartDate, ActualFinishDate, RemainingDuration, Status and the project DataDate updated. Check the exact field names against a real export from the site manager's P6.
- **Daily report:** HTML, PDF via the browser.

| Step | Hours | Done when |
| --- | --- | --- |
| State table + idempotent confirm function | 1.5 | Confirming twice changes nothing |
| Activity roll-up and earned-value query | 2 | Matches a hand calculation on the seed |
| Absence → crew → finish date + forward pass | 1.5 | "2 sick" moves the finish as expected |
| Websocket + vis-network graph | 2 | A fake capture animates in under 1 s |
| Bauleiter dashboard | 2.5 | Renders the seed plus 3 past days |
| .ics + P6 XML export | 1 | Correct time in Outlook; XML reads back cleanly |
| Rehearsal with replay | 0.5 | Two full 3-minute runs |

## Repo, contracts and the Claude Code workflow

Freeze six JSON contracts in hour one, each with a sample fixture, so you and Abdullah can build in parallel and Claude Code can test every module against them.

| Contract | Fields |
| --- | --- |
| `capture.json` | capture\_id, ts\_device (absolute), ts\_server, gps {lat, lon, acc} (optional), zone\_id (required), lang, media \[{type, path}\], note |
| `transcript.json` | capture\_id, lang, segments \[{start, end, text}\] (seconds from the start of the media file) |
| `vision.json` | capture\_id, frames \[{t, objects \[{obj\_id, label, bbox, conf, marker\_id}\], triplets \[{s, rel, o, score, source: model or geometry}\]}\] (t in seconds from file start; null for photos, time from EXIF) |
| `context.json` | capture\_id, zone\_id, weather {tempC, precipMm, windKmh, source}, candidates \[element and activity IDs with aliases\] |
| `structured.json` | capture\_id, labour\_present \[{trade, count}\], absences \[{trade, count, reason}\], material\_delivered, work\_done \[{element\_ids, activity\_id, state\_proposed, evidence: voice, vision or both, quote, t}\], special\_events, unmatched |
| `graph_event.json` (websocket) | type (node, edge, update), label, id, props |
| `dashboard.json` | date, activities \[{id, name, pct, baseline\_finish, forecast\_finish, delay\_d, ev\_eur}\], events |

**Repo layout:** `contracts/` · `fixtures/` (audio, photos, sample JSON) · `seed/` (ontology.yaml, elements.csv, auditorium.ifc, schedule.xml, boq.x83/x84, mapping.csv, loader) · `server/` with `ingest`, `speech`, `vision`, `structure`, `graph`, `loop`, `export` · `web/` with `upload`, `graph`, `dashboard` · `scripts/replay.py` · `docker-compose.yml` (Neo4j).

**CLAUDE.md, in this order:**

1. The goal in three lines.
2. Hardware limits: GTX 1060 6 GB, Pascal, torch cu126 only, fp32, no torch.compile, load models one at a time.
3. Contracts are the law; fixtures must pass.
4. Ontology labels and relationship names (from Workstream A).
5. Run and test commands.
6. Keys come from `.env`; never commit them.
7. One module per branch.

**Working with Claude Code:** one session per module, with a prompt like "Implement `server/vision`: turn `fixtures/photo_*.jpg` into `vision.json` that validates against `contracts/vision.schema.json`; add a pytest." Use subagents for research and for writing tests, and a separate review subagent before each merge. `main` stays demo-ready; work on `feat/<module>` branches, merge at the two checkpoints, tag `demo-v1` at the freeze.

### Fixes from the final checks

- **Protect torch.** ultralytics, faster-whisper or RelateAnything can silently pull a CUDA 12.8 torch the GPU can't use. Make a fresh uv Python 3.12 env (separate from the thesis venv), pin `torch==2.14.1` from the cu126 index in a constraints file, install RelateAnything with `--no-deps` and add its missing packages by hand, and re-check the torch build after every install.
- **Keep models loaded.** Ubuntu sits on the 5400 rpm disk, so reloading a model costs 5–15 s. Keep YOLO11s, YOLO-World and RelateAnything loaded (\~3.5–4 GB); run Whisper int8 on the CPU or as the only extra GPU model.
- **YOLO-World downloads CLIP the first time** you set classes. Do it once online, save the model with the classes baked in, then work offline.
- **Absences:** "zwei Mann krank" names no person, so store it as `Event {type: absence, trade, count, date}` linked to the affected activity (replaces `Labour-[:ABSENT]->Project`).
- **Weather** lives in `context.json` and becomes the WeatherReading node. Chrome often strips GPS from uploads, so GPS is optional; use the venue's coordinates.
- **Replay:** cache `cache/<capture_id>/{transcript, vision, context, structured}.json`; in `REPLAY_MODE` skip GPU and Claude and re-send the websocket events with realistic delays.
- **Default states** for doors, ceiling, curtain, cable tray and emergency lights: started 30 → installed 70 → checked 100.
- **Test on day one:** MPXJ writing user-defined fields to P6 XML (fallback: keep links in `mapping.csv` and write the P6 XML from an lxml template), and pyGAEB writing X83 (fallback: hand-written XML). Run `java -version` for MPXJ.

### Decisions written down for Claude Code

- Graph labels and keys in English; German in `name_de` and `aliases`.
- The site manager uses the tool; labour appears only as data (trades, crew counts, absences); the Bauleiter only reads the dashboard.
- A state changes only when `evidence` is voice or both, or on a manual tap.
- DIN 276: three-digit codes marked `verify` until checked.
- Demo dates: the 3-week baseline ends Thu 26 Nov; history covers Mon–Wed of demo week; "today" for the forecast is a configurable `DATA_DATE`.
- Upload: video plus photos in one capture, at most 60 s, zone required.
- P6 XML covers activities, WBS, relationships and user-defined fields only; costs live in GAEB.
- Claude Code inspects the existing Tagwerk repo before scaffolding anything.

### First message to paste into Claude Code

After exporting both doc tabs to Markdown and saving them in the repo as `docs/PLAN.md`:

```
Read docs/PLAN.md fully, especially the Build plan. Hackathon project, deadline Fri 27 Nov 09:00.
Hardware: this laptop, GTX 1060 6 GB (Pascal), Ubuntu 22.04, torch 2.14.1+cu126 (never cu128+),
fp32 only, no torch.compile. Docker and Java are installed.
First inspect the existing repo and tell me what's there before changing anything. Then:
(1) Create CLAUDE.md from the plan's CLAUDE.md outline and the "Decisions written down" list.
(2) Create contracts/ with JSON Schemas for capture, transcript, vision, context, structured,
    graph_event and dashboard, plus one valid fixture each in fixtures/.
(3) Create a Python 3.12 uv env with torch pinned to cu126 via a constraints file, a docker-compose.yml
    for Neo4j, and scripts/env_check.py that confirms CUDA, CTranslate2 int8, YOLO11s on a test image,
    OpenCV ArUco and the Neo4j connection. Report the results.
Don't build pipeline modules yet. Keys come from .env, which is gitignored.
```

## The 3-minute demo, fallbacks and risks

The pre-filmed auditorium walk is replayed through the real pipeline, so the judges watch the graph grow; one short live upload proves it isn't a video.

| Time | On screen | Who | What happens |
| --- | --- | --- | --- |
| 0:00–0:20 | Site manager's notebook and Outlook | You | "Site managers lose hours every day on reports nobody connects to the schedule or the contract." |
| 0:20–0:45 | Graph: GAEB position → P6 activity → auditorium elements | You | "We loaded this room's contract and Primavera schedule, element by element." |
| 0:45–1:30 | Replay of the filmed walk: capture node pops in, transcript highlights, boxes and relations appear, the seat row turns green | You narrate, Abdullah drives | "I said 'Stuhlreihe A montiert, zwei Mann krank' (seat row A installed, two workers sick). Watch the graph." |
| 1:30–1:55 | Live: a photo and a short voice note uploaded from Chrome; the node appears | You | "This one is live, from this room, right now." |
| 1:55–2:25 | Bauleiter dashboard: % complete, forecast delay from the sick workers, earned value; the .ics in Outlook; the updated P6 XML | Abdullah | "The Bauleiter sees this every morning, and it's already back in Primavera and Outlook." |
| 2:25–2:50 | Spatial and temporal graph; the robotics path | You | "Element-level, time-stamped tasks are exactly what robots need on site." |
| 2:50–3:00 | Team slide and one-line ask | Both |  |

**Rehearsal:** five full runs between H26 and H32 on the venue network, including one with the API cut off to practise switching to cached responses. Show a green/red health dot for the server on the graph screen.

**Fallback order on stage:** (1) skip the live upload and stay on replay, (2) switch to cached Claude responses, (3) play the backup screen recording.

**Risks:**

1. **Laptop memory and stability.** 6 GB of GPU memory, a weak battery, and the thesis work on the same machine. Close the thesis notebook, stay plugged in, and freeze package versions once it works.
2. **Seed data that doesn't match the footage.** Seed exactly the elements on the filming route, and stick a marker on each.
3. **P6 XML field names vary by version.** Validate against a real export from the site manager's Primavera as early as possible.
4. **A forecast built on little data looks fake.** Pre-seed three past days and label it as a projection.
5. **Licences:** RelateAnything is AGPL and its weights fall under the DINOv3 licence; Schependomlaan is academic-use only. Fine for a hackathon; say so on the last slide.

**Deck (6 slides):** problem with the site manager's quote · solution: capture → graph → schedule · architecture and the contract chain · demo · the edge: spatial + temporal + robotics · team and next steps. **Submission:** repo with README and a demo GIF, backup video under 3 minutes, deck as PDF, licence note, every form field filled an hour before the deadline.

## Still needed from you

The repo is [Current-cmd/Tagwerk](https://github.com/Current-cmd/Tagwerk). I couldn't open it from here because no GitHub account is linked to Claude, so the layout above is a proposal; Claude Code on your laptop can map it onto what's already there.

**Needed to start**

- [ ] Deadline Fri 27 Nov 09:00 (confirm the date); still needed: what you submit and any judging criteria or theme.
- [ ] Abdullah's main skills, to confirm the split above.
- [ ] Auditorium: length × width × height, stage size and height, number of seat rows and seats per row, door positions, and 20–30 photos from the spots you'll film from.
- [ ] The filming route, and whether you're allowed to stick A5 markers on the stage, screen, truss and row 1.
- [ ] Docker and Java: already installed (done).

**Needed in the first hours**

- [ ] Can the site manager export one real P6 XML file from her Primavera? It's the only way to confirm the field names before the demo.
- [ ] Realistic unit prices for the bill of quantities, or are plausible ones enough?
- [ ] A Hugging Face account that has accepted the DINOv3 licence (for the RelateAnything weights).
- [ ] Your Claude API key in `.env` on the laptop when you start building.
- [ ] You mentioned looking at what "Mochi" uses. Who or what is that?

**Decisions you can make later**

- [ ] German or English as the primary language for graph labels?
- [ ] Should the dashboard show cost by DIN 276 cost group, or progress only?
- [ ] Keep the Schependomlaan BIM-mode slice, or drop it to save 2 hours?
- [ ] Real ICDD container export, or just a mention in the pitch?

## Sources

- [BOT ontology](https://w3id.org/bot) · [DiCon ontologies](https://w3id.org/digitalconstruction) · [Neo4j Ontology Graph Spec docs](https://neo4j.com/docs/ontology-graph-spec/)
- [MPXJ](https://libraries.io/pypi/mpxj) · [pyGAEB](https://pypi.org/project/pyGAEB/1.7.1/) · [Oracle P6 XML import/export](https://docs.oracle.com/cd/F51303_01/English/admin/p6_pro_importing_exporting/primaveraprojectmanagementxml.htm) · [Oracle: physical % complete](https://docs.oracle.com/cd/F37125_01/p6help/en/47228.htm)
- [YOLO-World](https://docs.ultralytics.com/models/yolo-world) · [OpenCV ArUco detection](https://docs.opencv.org/4.13.0/d5/dae/tutorial_aruco_detection.html) · [RelateAnything](https://github.com/Maelic/RelateAnything) · [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [PyTorch: Pascal dropped from newer CUDA builds](https://dev-discuss.pytorch.org/t/cuda-toolkit-version-and-architecture-support-update-maxwell-and-pascal-architecture-support-removed-in-cuda-12-8-and-12-9-builds/3128) · [Claude structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) · [Outlook +1 h issue with TZID=Europe/Berlin](https://meta.discourse.org/t/calendar-event-ics-export-wrong-time-1-h-when-importing-into-outlook-with-tzid-europe-berlin/409797?tl=en)
- [Schependomlaan dataset](https://github.com/PlumpMath/DataSetSchependomlaan)
