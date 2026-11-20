# Site Manager Daily-Log App — Idea & Transcript

Nov 20, 2026 · @Sam

## The idea

An app for construction site managers that turns whatever they capture on site during the day (voice, photos, video, quick notes) into a structured daily log. The app files each entry into the right place on their calendar, tags it with site conditions, links it to the project's tasks, and feeds it back into the schedule so the forecast updates itself.

The two of you came up with it in a brainstorm after interviewing a site manager. She asked for easy multi-format input, autocomplete, Outlook, and a daily report. You framed the closed loop and the spatial edge yourselves.

**One-line pitch:** a site manager walks the site and talks, and the app turns that into a structured daily report, a calendar history and an updated schedule forecast.

## Decisions so far

| Question | Decision | What it means |
| --- | --- | --- |
| Goal | Hackathon / demo | Speed over polish. The academic-only Schependomlaan licence and RelateAnything's AGPL code are fine for a demo; revisit both before any commercial use. |
| First market | Germany / DACH | GAEB bill of quantities, German roles (Bauleiter, Polier), Outlook. |
| MVP scope | Full chain + vision | Demo the whole loop: GAEB position → Primavera activity → IFC element → daily task, plus RelateAnything on site photos. |
| BIM | Support both | With BIM: element-level links. Without BIM: schedule and progress only, with vision filling in components later. |
| Timeline | 24–48 hours | Updated: deadline Fri 27 Nov 09:00, about six days. See the day-by-day plan in the Build plan tab. |
| Platform | Mobile web app | One codebase, phone camera and mic through the browser. |
| Calendar | Export .ics file | Each day's log becomes calendar events the user imports into Outlook; no Microsoft sign-in needed. |
| Language | German and English | German voice input, summaries shown in both. |

**Scope risk:** the full chain plus vision is a lot for 24–48 hours. Do the slow, one-off work before the hackathon: link the GAEB positions, Primavera activities and IFC elements for one slice of Schependomlaan, load them into Neo4j, and set up RelateAnything on a GPU. During the hackathon, build only the live part: capture, structuring, linking to the graph, the .ics export and the forecast update.

## Demo architecture

*Superseded by the Build plan tab: everything now runs on one GTX 1060 laptop at the venue (no 1080 Ti, no tunnel), and footage is uploaded through a Chrome upload page instead of a custom phone app.*

The phone records; your 1080 Ti machine does all the heavy processing. The phone is just a capture client, so nothing runs on its CPU.

1. **Phone (mobile web app):** records video, photos and voice, and stamps each with time and GPS. Uploads to the server.
2. **Connection:** a tunnel from the phone to your machine (Cloudflare Tunnel, Tailscale or ngrok), so the server doesn't need a public IP.
3. **Server on the 1080 Ti** (Python, FastAPI), processing each upload in this order:
   1. Speech to text: Whisper, German and English.
   2. Frames from video: sample about 1 frame per second.
   3. Detection: YOLO boxes on each frame.
   4. Relations: RelateAnything turns boxes into triplets such as "formwork → around → column", using a construction vocabulary.
   5. Weather: query Open-Meteo (free, no key) for the GPS position and time.
   6. Structuring: an LLM turns transcript plus triplets into an environment description (people, material, work done, special events) and matches it to tasks and elements.
   7. Graph: write everything to Neo4j against the pre-loaded GAEB → activity → element chain.
   8. Loop: update progress and the forecast finish dates.
   9. Output: the daily report and an .ics file for Outlook.

**1080 Ti check (do this first):** it is an 11 GB Pascal card. The newest PyTorch and TensorRT builds may no longer support Pascal, so if the latest install fails, use an older CUDA 12.x PyTorch build and skip TensorRT. RelateAnything also runs on CPU (`device="cpu"`), just slower, as a fallback. It needs Python 3.12+.

## Pipeline review

Five reviewers each took one stage (capture, speech + LLM, vision, data model, loop + demo), then critiqued each other. Their verdict: the full chain can run live, but only if voice drives progress, the seed data matches the room you film, and a cached replay is ready for when the venue-to-home link drops.

### Where they argued, and the verdict

| Question | Positions | Verdict |
| --- | --- | --- |
| Video or stills? | Capture + vision: stills plus a voice note; loop: 10–15 s clips | Stills + voice note by default; short clips (≤15 s) optional. |
| Stream chunks while recording? | Capture: yes; speech + loop: no, too complex, and Whisper needs the whole clip | Upload each capture whole. Show the capture node the instant it arrives, then stream enrichments in. |
| Whisper size | Speech: large-v3-turbo int8 (better German jargon); loop: small (latency) | Benchmark on the 1080 Ti in hour one. Use turbo if a 15 s note transcribes in under \~6 s, otherwise small. Never float16 on Pascal. |
| What moves progress? | Loop wanted vision to turn the wall green; vision: too fragile | Voice ("Bewehrung Wand B fertig") or a tap confirms a state change. Vision only proposes it and attaches the evidence frame. |
| How triplets sit in the graph | Data: Element→Element edges; vision: boxes aren't elements | Data model conceded: (Capture)→(Object)–\[REL\]→(Object), with a dashed LIKELY\_IS link from Object to Element. |
| How the system knows which element is filmed | Speech: GPS zone filter; capture + data: GPS fails indoors | A zone picker on the phone (one tap), plus a printed QR/ArUco marker on each filmed element. GPS only identifies the site and the weather location. |
| BIM mode in the live demo | Loop: hand-model the filmed room as IFC; data: not worth it in 48 h | Run the live part in no-BIM mode (activities + zones + markers). Show BIM mode on a pre-seeded Schependomlaan slice with replayed captures. Hand-model the room only if time allows. |
| Fallback when something fails | Capture: laptop running the server on CPU; vision: vision on CPU is too slow | Primary fallback: a replay button that feeds a pre-processed clip through the same UI. Laptop fallback runs only Whisper small and a nano YOLO. |
| Detector | Vision: COCO YOLO can't see construction objects; open-vocabulary models score badly on site objects | YOLO fine-tuned on the SODA construction dataset. A staged room won't contain rebar or formwork, so film a real site or use props from SODA classes (wood, brick, helmet, vest, person). |
| Schedule file | Data: Schependomlaan's schedule is likely MS Project XML, not P6 | Parse MS Project XML for Schependomlaan; prove the P6 path with a small hand-written XER for the filmed room. |

### Top three risks

1. **PyTorch on the 1080 Ti.** The vision reviewer found that recent PyTorch builds have dropped Pascal and named torch 2.14 with CUDA 12.6 as the last prebuilt option. Install it and confirm `torch.cuda.is_available()` before writing anything else; no TensorRT.
2. **The venue-to-home link.** Tunnel, home upload, or the machine sleeping: one drop freezes the live graph. Use a fixed tunnel hostname, a health indicator on screen, sleep and updates off, and the replay button.
3. **Footage that doesn't match the seed data.** If the filmed room isn't in the graph, everything lands as "unmatched" on stage. Seed activities, zones and BoQ positions for exactly what you will film.

### Agreed must-dos

- One capture ID carried end to end, so retries never duplicate nodes; progress states are idempotent (set the max state, never add).
- FFmpeg normalizes everything first (iOS records MP4/AAC, Android WebM/Opus, iPhone photos HEIC).
- Claude structured outputs with element and activity IDs as enums plus null, a quote as evidence for every match, the transcript wrapped as data; warm up the schema before the demo.
- A German/English glossary in Whisper's prompt and as aliases on graph nodes.
- Vision and speech aligned by timestamp ("this wall" at 12 s means the frame at 12 s).
- Forecasts labelled "projection from today's evidence"; pre-load 2–3 past days so they aren't built on one point.
- Graph view shows three levels (activity → element/zone → today's captures) to avoid a hairball.
- .ics times in UTC with a stable UID per capture (Outlook shifts Europe/Berlin times by an hour without a VTIMEZONE block).

## What I still need from you

The first five block the build; the rest can come while I work. Answer inline under each item or in chat. Already settled: goal, market, MVP scope, BIM, platform, calendar, language, Claude API.

**Blocking: needed before I start**

- [ ] **1. The 1080 Ti machine:** Linux or Windows? Paste the top of `nvidia-smi` (driver and CUDA version). Is Docker installed? Is it wired to the router, and can it stay on with sleep and updates off?
- [ ] **2. What you will film live:** a real construction site or a staged room? Indoors or outdoors? Which 5–10 objects or elements must the system recognise and link?
- [ ] **3. Hackathon logistics:** end time, what you submit (live demo, video, repo, slides), length of the demo slot, and any theme or judging criteria.
- [ ] **4. Team:** who is on it, and who takes frontend, backend, vision and data?
- [ ] **5. Claude API key:** put it in an environment variable on the 1080 Ti machine (don't paste it in chat). OK to default to Claude Sonnet 5.5 for speed?

**Seed data: needed in the first hours**

- [ ] **6.** Do you have any real Primavera XER or GAEB files, even anonymised? If not, I write a small XER and bill of quantities for the filmed area.
- [ ] **7.** The activities and zones of the filmed area (e.g. "EG Achse B: Schalung, Bewehrung, Betonage"). Give me a rough description and I'll draft them for you to check.
- [ ] **8.** A site glossary of 20–50 German/English terms. I can draft it; you correct it.
- [ ] **9.** 3–5 test voice notes (German, English, mixed) and 10–20 photos from the filmed area, recorded on the demo phone.

**Infrastructure**

- [ ] **10.** Phone model, OS version and browser you'll demo with.
- [ ] **11.** Venue internet: Wi-Fi quality, whether a phone hotspot is allowed; your home upload speed.
- [ ] **12.** Tunnel: do you have a domain on Cloudflare, or an ngrok or Tailscale account?
- [ ] **13.** A Hugging Face account that has accepted the DINOv3 licence (needed for RelateAnything weights).
- [ ] **14.** OK to run Neo4j locally in Docker on the 1080 Ti machine, so the stage doesn't depend on the internet for the graph?

**Demo**

- [ ] **15.** Screen setup: projector or laptop? Who holds the phone, and who drives the screen?
- [ ] **16.** Can you reach the site manager you interviewed during the hackathon, for feedback or a quote for the pitch?
- [ ] **17.** GitHub account and repo name for the code.

**Accepted for the demo, revisit before going commercial:** RelateAnything is AGPL and its weights fall under the DINOv3 licence; Schependomlaan is licensed for academic use only.

## How it works

The system has six layers. Each one feeds the next, and the last one closes the loop back into the schedule.

1. **Capture (input).** Voice, pictures, video and typed notes. Autocomplete predicts what comes next from a few keywords, which the site manager explicitly asked for.
2. **Calendar and timeline linking.** Every note, photo and video is placed automatically in the calendar (Outlook first) as an event or an attachment, with no manual entry. A site manager who visits several sites a day can go back later and see what happened where and when. This is separate from the professional Gantt chart; it is the manager's own record of the day.
3. **Environment metadata,** mapped to each note.
   - *Extrinsic* (cannot be controlled, queried automatically): weather and similar conditions. Example: a concrete slab can't be poured in wet conditions because it absorbs moisture.
   - *Intrinsic* (controllable): labor, which tasks were worked on and which come next. Tasks are a stream over time.
   - *Environment description* (the day's state): people on site, material delivered, work done, and mistakes or special events, which get their own note type.
4. **Project model.** The planning data the daily log is mapped onto.
   - *Tasks*, each with: components (the materials or building elements in the plan), time, spatial location, ownership (can be several people), progress as past, current and forecast, and cost variance against the original plan.
   - *Cost* (a function of everything else), *project-level progress*, *material utilization*.
   - *Actors and roles*: labor, the site manager, and the Bauleiter above them. The site manager allocates tasks to workers, like a driver and riders in Uber, so if someone is sick the affected task visibly turns red as delayed.
5. **Closing the loop.** Each daily update is fed into the overall schedule, so the forecast (expected finish dates, delays, costs) updates itself.
6. **The edge: spatial plus temporal.** Things are located and related spatially (scans) and captured daily, so the data forms a graph over space and time. With a BIM model you get component-level task descriptions, which makes it easier to bring robots onto the site (the thesis link). Without BIM you still get scheduling and progress tracking, and vision models (e.g. YOLO) could later generate component descriptions.

**Phase two:** the site manager just walks around with a camera and talks. Video and speech are structured and mapped through all the layers above, and everything shows up in their calendar.

**Deliberately parked:** using site cameras to measure labor efficiency or ergonomics. You both agreed not to let scope get out of hand there.

## From the notebook pages

The two pages match the recording. They add Primavera as an explicit integration and a set-up note: work lives in a repo, synced to a shared Drive and to Claude. Items marked (?) were hard to read.

**Page 1 — Planning feature list**

1. Summary: voice, writing, pictures, video, etc.
2. Notes
3. Autocomplete
4. Primavera
5. Outlook
6. Calendar / Gantt chart
7. Environment metadata: live data, extrinsic query
8. Tasks → temporal
9. Environment description: material on site, work done, special events
10. Scheduling, actors

**Page 2 — Project tree**

- **Project**
  - **Tasks:** time, components, progress, spatial location, ownership, cost variability, past / current / future finish
  - **Cost**
  - **Progress**
  - **Material utilization**
  - **Actors:** site manager, labour, Bauleiter
- **Loop closure:** data points from the day update are fed into future planning.
- **Locate** and **video** (the spatial edge and the phase-two walk-through).

## The chain back to the contract

Every daily log entry should trace back to a contract line: contract → schedule activity → BIM element → task. Then a photo of a finished slab updates progress on its element and its activity, and becomes an earned-value figure against the bill-of-quantities position it was tendered under. That is where cost variance and claims come from.

| Layer | What it holds | Standard / format | Key that links it down |
| --- | --- | --- | --- |
| Contract / tender | Bill of quantities positions, unit prices | GAEB DA XML in Germany; [DIN 18290-2](https://www.din.de/de/mitwirken/normenausschuesse/nabau/veroeffentlichungen/wdc-beuth:din21:369464914/toc-3522068/download) defines a container linking BIM models to the BoQ | BoQ position number |
| Schedule | Activities, WBS, relationships, cost accounts | [Primavera P6 XER or P6 XML](https://products.aspose.com/tasks/supported-formats/xer/) | Activity ID ↔ BoQ position |
| Element | Walls, slabs and other components with quantities | IFC (IfcTask, IfcCostItem, IfcWorkSchedule) | IFC GlobalId ↔ activity ID |
| Task (daily) | Notes, photos, video, progress, environment data | Your app, stored in Neo4j | Node links to GlobalId, activity and date |

The GAEB–IFC link already works in practice. A GAEB file can define a catalog that points at the IFC model, and single BoQ positions can reference it ([Dangl IT](https://dangl-it.com/articles/integrating-bim-ifc-references-with-bills-of-quantities-and-gaeb-files)).

## Building blocks

Three existing pieces cover the vision layer, the graph and the schedule input.

| Piece | What it gives you | Watch out for |
| --- | --- | --- |
| [RelateAnything](https://github.com/Maelic/RelateAnything) (Maelic, released Sept 2026) | Turns an image plus object boxes into scored (subject, relation, object) triplets, e.g. "rebar → on → slab". You set the relation phrases at run time, so construction vocabulary needs no retraining. About 34–39 ms per frame including YOLO detection on a laptop GPU. | AGPL-3.0 code: running it as a network service means publishing your source, unless you agree commercial terms with the author. Weights fall under the DINOv3 licence. Video from files isn't documented yet. |
| [Neo4j Ontology Graph Specification](https://neo4j.com/docs/ontology-graph-spec/) (announced 5 Nov 2026) | An open format (Apache 2.0, YAML or JSON) for defining node types, relationships, properties, constraints and indexes, checked against a JSON Schema. One file can drive database constraints, import mappings and agent context. Repo: [neo4j/ontology-graph-spec](https://github.com/neo4j/ontology-graph-spec). | No RDF serialization yet. To reuse ifcOWL or other RDF ontologies, go through Neo4j's neosemantics plugin. |
| Primavera P6 XER / P6 XML | The schedule input. XER is a tab-delimited text export with tables such as PROJWBS (WBS) and TASKPRED (activity relationships); P6 XML is the open, more verbose alternative. Most construction contracts specify XER. | XER schemas differ slightly between P6 versions. Parsers exist (e.g. Aspose.Tasks), or write a small table reader. |

The Neo4j spec is the natural home for the project tree above. Define Project, Task, Element, BoQPosition, Activity, Actor, Note and EnvironmentReading as node types, with relationships such as Task→Element and Activity→BoQPosition. RelateAnything triplets from site photos then become relationships between Element nodes, each timestamped and located.

## 4D/5D BIM test data

Build the demo on the Schependomlaan dataset. It is the only open set found that has a real schedule linked to the IFC model plus as-built site data from the same weeks, which is exactly the loop the app closes.

| Dataset | What's in it | Fit |
| --- | --- | --- |
| [Schependomlaan](https://github.com/openBIMstandards/DataSetSchependomlaan) (house in Nijmegen, NL; DOI 10.17605/OSF.IO/NE2YU) | Design IFC and subcontractor IFCs; schedule as XML and PDF; as-planned IFC models from Synchro for weeks 26–30 and 37; as-built drone point clouds for weeks 26–30; event logs; drone photos and video | Best. Has 4D (schedule ↔ IFC) plus as-built reality to compare against. No cost data, so you add the 5D layer. Licensed for scientific and academic use only. |
| [BIM Spatial Models for Dependency Inference and Scheduling](https://data.mendeley.com/datasets/fm9myphk9g) (Mendeley) | Three IFC models (meeting room, residential building, Revit advanced sample) with CSVs of spatial and semantic data | Good for testing the IFC-to-graph conversion. No schedule or cost. |
| Build your own 5D with [Bonsai / IfcOpenShell](https://wiki.osarch.org/bonsai-costing/) | Free tool to add IfcWorkSchedule, IfcTask and IfcCostSchedule to any IFC model | Use it to add cost items and a small BoQ to Schependomlaan, then export the schedule into P6 format. |

No open dataset found includes a GAEB tender. You will need to write a small bill of quantities for Schependomlaan yourselves to demonstrate the contract link.

## Open questions and next steps

- [ ] Ask the site manager which apps she uses for scheduling today, beyond Outlook and Primavera.
- [ ] Decide how granular the schedule link should be (project, activity or element).
- [ ] Define the actor roles in full (site manager, labor, Bauleiter, others).
- [ ] Write the ontology in Neo4j's Ontology Graph Spec: Project, Activity, BoQPosition, Element, Task, Actor, Note, EnvironmentReading.
- [ ] Download Schependomlaan, load the IFC and schedule XML, and check what the schedule XML format is.
- [ ] Write a small bill of quantities for Schependomlaan and link its positions to activities and elements.
- [ ] Write a P6 XER/XML importer for the schedule layer.
- [ ] Test RelateAnything on Schependomlaan drone frames with a construction relation vocabulary; check AGPL implications before shipping it in a hosted product.
- [ ] Set up the repo and shared Drive; draft the architecture skeleton with Claude, then refine it together.
- [ ] Write two versions of the pitch: with a BIM model and without one.

## Full transcript

Transcribed automatically from the 16:50 recording (English). Speakers aren't labelled, and a few short passages were unclear. Obvious mishearings were corrected (e.g. Gantt charts, Bauleiter, Claude).

**00:00** That was essential. Just in the input, different input strings. That was essential feature. Voice writing pictures, videos. Videos, yeah images, notes, like by texting, writing. She said autocomplete. She literally mentioned keywords and it can predict things. Yeah, autocomplete.

**00:23** And I think this can actually be linked to the future, which is said like, estimate future stuff. Yeah. First it has to first connect to the schedule and then the estimation. So how does it connect to a primer where whatever apps they generally use? Or should we ask her what apps she uses? For scheduling what does she use? But I think it's P.

**00:45** It takes a summary then what you can do right create nodes or to complete it should connect to the schedule and also provide like how granular can we get with the schedule? So I think should we make it like automatic linkage to other different apps like beside the

**01:07** She was the one who mentioned Outlook. I think Outlook is important. Calendar, like what notes lived where automatically without you entering. So I took this notes now, it links or spot of the attachments that is created as an event in your calendar. She didn't mention that.

**01:27** But I think that will make you easier to go back in time on Sunday evening. I went to this. I want to know what did they do there? Yeah. And linking the timeline in the calendar to the artifacts that she created. But I would, they use Gantt charts for that. I was thinking why will you, why will you, I was just like... For her. I was about to say, like, it's a single site manager right there. So, beside the actual professional...

**01:49** Gantt charts, analysis. I'm talking about I took some notes now. Like if you have photos, right? Like when did you take these photos? Connected to what notes? When? In your because you can go to multiple sites at the same day. So basically you're localizing your notes in the timeline, in the calendar and outlook.

**02:13** I think once you do this, automatically open your outlook and see everything there, I think maybe add some more factors. Yeah, actually good if you like multiple sites then it makes so much sense to keep it different. Yeah, exactly. Then comes the, you connected, now comes the feedback part.

**02:33** or we look at no outer factors like weather, and a bunch of stuff. Yeah, all the data bear exactly how many people came today.

**02:51** What works to date? What does she mean? How many people? Site manager. What is the weather today? So what task are okay and what task are not okay? Automatic... yeah, let's call it like environment metadata. So there's information like weather.

**03:14** all this kind of stuff I don't know if it's relevant for when you're building for construction it's very relevant because certain slab like concrete slab you can't lay it on any table it will absorb moisture and it will hold the whole thing in the foam they'll load them already to the metal table but here we do live metal table like pull it from the concrete yeah you have to query it because you don't need to directly

**03:35** But sometimes you might be... So environment as I would say there is extrinsics and there is intrinsic extrinsics something like the weather you cannot control. It's there. And I would say this is extrinsic so this is maybe if you can write methodic extrinsic stuff like you have to query. And we just map it to the note.

**03:56** Yes. And there is also intrinsic stuff that you can control. Like the labor, I would say. Which tasks you do next. Which tasks you worked on or you do next. So tasks as a segment, as a stream and there is different misting and information there. This is a temporal aspect to it. Temporal, yes.

**04:17** But there is also stuff that's static, not static, but static, like how many people is it? She mentioned that. What the influence is like, environment description. You're describing the environment, right? So what other than people? - Environment description. - Yeah, environment description. Yeah, material, how much material came today?

**04:36** material. What came on site? Yes. Yes. I think so. On site, how much work was done today? Work done on site? Yes. On site, any mistakes or any special events? Notes, yeah. We can create a special note for it.

**04:56** So now you describe the environment, you describe the window. Now I think we have to look at project metadata, which is planning data that's already... Does the site manager does anything with the people who work there? Does he assign things or does he matter? Yeah, I think it's his job to plan what...

**05:17** to the people. You need a tree of tasks in this case, like assigned to people in this case. Maybe actually maybe we can make it like the site manager, the application, the site manager, you know like the Uber driver and captain and user. Like an allocation problem.

**05:38** How he decides from the... - Yes, basically there is a driver and there is a user. So the driver is the pilot, sorry, is the site manager. - Yeah. - There is a common place for the tasks of his notes created, basically like you said, to come to the future. - Yeah. - And there is history. So basically there's tasks, I would say scheduling or database that describes what happened.

**05:59** What is happening, what's next? But also there is actors. And these actors are the people who are in the labor. So if there's somebody sick, you would visually see that one task is getting delayed. I think this is something to do with the mission, but I think it makes sense. I think the best, like either different factors, whether it's all the extrinsic stuff, intrinsic, or even... that's what we did.

**06:22** Now you have to relate it to the project data. Yes, exactly. So this is, yeah, project mapping. So the environment description mapping to the project. Project has tasks and costs. Let's now define that project. The project has a lot of definitions. Maybe you have to define the project.

**06:42** So we have to say tasks, maybe a new page maybe in this case because it's a much bigger. So I'll say the project can be described by tasks, by costs, by progress. This is just where I'm throwing in interviews to describe a project.

**07:01** Tasks, cost and progress Material utilization, materialization, just throw in word and then we can map cluster People, people, people, actors, actors, actors because it's one of them is site manager roles there's different roles for actors Do you want to put extrinsic and intrinsic here or it's

**07:25** We will map this to the project. We just need to define the project. I will define the project as an interface for the project. And then components also. Material? Like, specific tasks is what? But I think we can then go deeper into it. Yes, and tasks we need like implementing what?

**07:46** Components and time back. So each task takes what components each task has and how much time it takes. Component like a tool to achieve the task or you mean like what are the material in the plan. Material, like building the ball. So basically each task should be spatially, temporally and quantity wise.

**08:10** So I was thinking you could get a task note which has all the keys. So which task is happening where? Yes, where and when and the progress is information. You can write all of this in the task. For each task there is also information like this. To progress and material. No, no, no. It's new. Because this is actually task level over task.

**08:30** level of a task and there is progress on a level of a project. That's why we just provide information separately. There is progress, there is time, component, progress, spatial location. Spatial location, where is it? Ownership. Ownership. Because it can multiple people.

**08:51** Cost variability because in the primary you already shed you like it's already done before. You assign like this much taste, this much labour allocation, that cost and care the activity. So cost variability because of due to some and you want to have a canon event.

**09:10** Like if some event that was like forecast or it's part of the progress maybe in progress you can say past current future and progress because it's also kind of forecast like expected to finish when right and you will see like a red somebody is red because somebody is sick but he didn't monitor that in the beginning Actors

**09:34** Yeah, I think we defined it well. Yeah, and actors, I think we need to define our actors. We have to define the site manager in different roles. Maybe even after that, we can define or use Claude to help us define the roles. Site manager, labor, then the person on top of the site manager, the Bauleiter.

**09:56** I think now we have to find the project well, now we map it. Yeah, we have to map it to the environment and stuff, but did we finish the project already? Yeah, we have tasks, we have... Cost is the project. Cost. Cost of the project. I think cost is a function in everything else.

**10:18** But we have to keep it. Keepers have to be cost-effective. We can calculate or estimate the cost based on the changes there. Progress is also helpful. Material utilization, actors. What is it? Yeah, I think this is really... I mean, while we are working on my three visits, it's okay. I think it's good. Yeah, good enough.

**10:41** Here, next comes, mapping to the mapping, right? There is something still need to be, might need to be defined again. I think we define the project like, because it's our environment project, what else? Everything she asked for already provide now.

**11:03** Yeah. I think we provided for all the people who are providing now. So you want a daily report of what happens and we have defined everything that can happen on a project and what are the different components interacting with each other. And with this information we dissected, is it enough to provide the implementation for the forecast? You said that to close the loop, right? Yeah. Close the loop, right? Yeah.

**11:25** This information on a daily update is fed into the overall schedule and then the loop is closed. So loop closed. Data points received from day update.

**11:43** fell into the future planning.

**12:03** to the descriptors of the environment, whatever it is in the description. How do you want to do this? Do you want to do this now or should we sit down with drugs with ping pong? Because usually that's the architecture. Because usually it can give you a very good skeleton. And then you start modifying.

**12:23** Go have this discussion and also define the text by text. Yeah, I think we'll have to. And then we just send this to Claude and then we share it and both of us agree deeply. Yeah, just start the chat in this book. So these are all the features. So if we do this, we have an edge.

**12:41** The edge that comes is the spatial part. So we are able to spatially locate it like the scan. Locate things. Locate and relate. And since we are anyway doing it daily, there is a temporal aspect to it. So how would you feed that into some kind of database that we have?

**13:03** Because the data is also very... It's a graph piece, so you have to figure out how you... The more we talk, the more I keep leaning towards efficiency of the... But you can monitor efficiency of the development of the... We're getting to putting cameras and... We're the best, right? You can measure efficiency of the... of labour.

**13:26** Yeah, it is more of that only. Eventually it is... Yeah, just one day. But that's why I don't want to get it out of hand. But okay. Yeah. Cameras everywhere. And the camera is already on site that let's see the people coming and going out. Yeah, but they don't monitor ergonomics. Yeah, they don't. And you don't move much. It means that you don't work. But one added advantage...

**13:48** and this is also what I was working on in my thesis, if you have a component level description of your task or schedule then robotics implementation is easy. Robotics implementation, what do you mean by robotics implementation? Right now to introduce robots on site, they cannot work with tasks. Ah, yeah. Because there's a lot of things that don't work. But now we're anyway breaking it down to like...

**14:11** because you're building off this. So you're like, this is assuming we have a BIM model. - Yeah, yeah, yeah. - The following, like... - Of course. - Yeah. But you have to make two plays, like assuming you have a BIM model and they say if you don't have a BIM model... - Yeah, that's why I'm trying to handle this problem first. - Yeah. You see, if you don't have a BIM model, also you can still do some parts of it. - Yeah. - You can still do the scheduling, you can still do the progress modeling, etc. But you won't have the component level description because

**14:35** You have to understand the component. But that we can say, our patented vision software will be able to create it for you. That's like, really. Yeah, it will actually be cool maybe with any YOLO or any classifier, image classifier that we can actually... So like, if you have them and if you don't have them, we create it for you, component and description. So example, while you're working, you want to introduce robots.

**14:59** I don't think you can define components from the conceptual side, that's you went too far. Now you start to talk in dreams. It's a pitch for you, it's like a fever pitch. You sell, you sell like those. Yeah, there is a lot of cover, there is some sand here. These people don't even use them bro, they're like next to them.

**15:22** But wait, actually there was something we actually just mentioned that actually makes sense. It just... Yeah, the video. So I would think maybe we can actually make it like the idea that you said in the beginning. Maybe just as a site manager, just go around the camera. Go around and talk. We get like both.

**15:41** Yes, and we map from the structure data from the first step actually we talk to structuring the data and stuff Yeah, we Describe the environment we query some stuff and map everything to so basically video and describing and everything is being you you We have a database of course, but everything is visible in your calendar

**16:03** So you're building literally a startup. That's exactly phase two. That's what the pitch is. Yeah. Unfortunately, it was like, it used to be much easier, man. Like five years ago. Hackathons, yeah. Oh my God. Hackathons, if you have a website. You're literally building. Yeah, yeah. I remember the hackathons before the AI era. If you just have a website. Yeah.

**16:23** What we find, just application. Just application, whoever makes it like any Android is the K native or... Now it's like... You need to have this, you need to have a new structure. You built the startup. Now another built two startups in a couple of days.

**16:45** But do you have anything else to be added?
