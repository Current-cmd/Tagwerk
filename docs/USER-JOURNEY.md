# Tagwerk user journey

Who does what, from the first day of a project to the daily report, and what must be ready before
someone outside the team can use Tagwerk without us standing next to them.

## People

| Person | Where | Uses | Wants |
|---|---|---|---|
| Site manager (Polier / Bauleiter vor Ort) | On site, gloves, noise, little time | **Mobile app** (`mobile/`) | Record what happened in under a minute; never type a report |
| Bauleiter / project lead | Office or site container | **Dashboard** (`/app`) | Plan vs actual, delays with causes, a report and a notice draft he can sign |
| Office / scheduler | Office | Upload P6 XML + GAEB, P6/ICS exports | Schedule and BoQ stay the source of truth |
| Labour | Not a user | Appears only as data (trades, counts, absences) | – |

## Journey

### 0. Project setup (office, once, ~10 min)

Two paths, the same result: elements, activities, BoQ positions, zones and a baseline.

- **No BIM:** drop the P6 XML schedule and the GAEB file (X83/X84). Tagwerk derives zones and elements
  from the activities and the BoQ positions.
- **With BIM:** add the IFC model. Every element is tracked individually (Schependomlaan: 2,082 elements).
- **Nothing yet:** walk the site with the phone in *Scan* mode; Tagwerk proposes a starter project from
  what it sees (`/api/scan` with `make_project`).

Then connect the site manager: open the dashboard on the laptop, show the server address (Tailscale
`http://100.118.181.69:8080`), and the site manager enters it once in the app (or scans the connect QR code).

### 1. Morning (site manager, 1 min)

Opens the app on the **Heute** tab: today's open activities with their elements, plan vs actual, delay in
days, and any proposals waiting for a decision.

### 2. During the day (site manager, 30–60 s per recording)

**Erfassen** tab. Pick the zone, then one of:

- **Video with commentary** (main path): walk and talk. "Estrich im Saal fertig, zwei Mann vom Trockenbau krank."
- **Photo** (+ optional voice note or typed note)
- **Voice note** only
- **Typed note** (counts like voice)

Upload runs in the background; without signal the recording waits in the queue and resends itself with the
same `capture_id` (the server ignores duplicates). After processing the app shows what Tagwerk understood:

- **Confirmed** (green): the sentence names it, so the element state moves up.
- **Proposed** (amber): only the camera saw it. One tap confirms, otherwise nothing changes.
- **Absences, deliveries, special events** (weather, defects, hindrances).

### 3. Correcting (site manager, seconds)

Tap any element on **Heute**, pick its real state. A manual tap counts like voice evidence.

### 4. Walk-through scan (site manager, occasional)

**Scan** tab: a slow 30–90 s walk. Tagwerk lists the objects and elements it recognised (with the frame where it
saw them) and builds a 3D scan with what was said where. Opens in the browser.

### 5. End of day (site manager → Bauleiter, 2 min)

**Bericht** tab: the daily report is already written from the day's recordings (work done, labour, absences,
weather, delays with causes). Site manager checks it and releases it. The Bauleiter sees it on the dashboard,
together with forecast, SPI and the notice draft for delays that need one (Behinderungsanzeige, VOB/B §6).

### 6. Bauleiter (office, any time)

Dashboard: plan vs actual, forecast finish, delays and their causes, the live graph (recording → element →
activity → BoQ position), BIM view, daily reports, P6 XML and .ics exports back into the planning tools.

## Ready checklist (before outside users)

### Must have (demo, Fri 27 Nov)

- [x] API and GPU worker on the laptop, reachable over Tailscale (`:8080` Hörsaal, `:8081` Schependomlaan, `:8082` scan)
- [x] Dashboard `/app`: dashboard, live graph, BIM, daily report, 3D scan
- [x] Capture pipeline: video/photo/voice/note → transcript → vision → structured → graph → dashboard
- [x] Mobile app `mobile/` (Expo + shadcn/React Native Reusables, Android via Expo Go): connect, today, capture with offline queue, result, scan, report
- [ ] Tailscale installed on the demo phone and signed in to the same tailnet
- [x] Metro for the app running on the laptop (`~/tw-mobile.sh start`, serves `exp://100.118.181.69:8090`)
- [ ] Expo Go installed on the demo phone, app opened via `mobile/expo-go-qr.png`
- [ ] One rehearsal on site: record, see the result on the phone, see it live on the dashboard
- [ ] `tw-doubletest.sh` green on the morning of the demo, demo data reset

### Should have (first pilot)

- [ ] `API_TOKEN` set on the laptop (no dev mode outside the demo) and entered in the app
- [ ] HTTPS (Tailscale `serve` gives a certificate), so tokens are not sent in clear text
- [ ] A standalone Android build (`eas build -p android --profile preview`), so the site manager needs no Expo Go
- [ ] Claude structuring key in `.env` (rules fallback misses words outside the glossary, e.g. excavation)
- [ ] Project setup from the UI (today: seed files or `/api/scan` with `ALLOW_PROJECT_CREATE=1`)
- [ ] Glossary per project (trade words, element nicknames the crew uses)
- [ ] Notice (Behinderungsanzeige) export reviewed by someone who signs them; marked as a draft, not legal advice

### Later

- [ ] Several projects per server and a project picker in the app
- [ ] Users and roles instead of one bearer token
- [ ] Push notification when a proposal waits or a delay needs a notice
- [ ] GPS / zone from the phone's location
- [ ] Hosting off the laptop (GPU box in the office or a cloud GPU)
