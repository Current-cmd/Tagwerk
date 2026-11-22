# Handoff: update the pitch deck and the demo video for the mobile app

You take over the pitch and the demo video for Tagwerk (Challenge B, "AI Site Manager Assistant for Documentation,
Daily Reports and Claims"). Both were built before the site manager app existed. Your job: bring the app into the
story, so the pitch shows the full loop **phone on site → Tagwerk engine → dashboard, schedule, GAEB, daily report**.
Deadline: **Fri 27 Nov 2026, 09:00**. Work on the Mac (`/Users/anoushk/Developer/hacka/tagwerk`).

## 1. Read first

1. `CLAUDE.md`: product decisions (vision alone only proposes; a sentence or a tap confirms; states only go up).
2. `docs/USER-JOURNEY.md`: roles, the journey from setup to daily report, and the ready checklist. The pitch should follow this journey.
3. `pitch/README.md`: where the deck, the video project, the screenshots and the footage are, and how to build them.
4. `mobile/README.md`: what the app does, screen by screen, and how it runs (Expo Go on Android, Metro on the laptop).
5. `docs/design-brief/SITE-NARRATIVE.md`, `DEMO-VIDEO-SHOTLIST.md`, `README.md` (palette, typography).

## 2. What exists

| Piece | State |
|---|---|
| Deck `docs/design-brief/Tagwerk-Pitch.pptx` (13 slides, generator `pitch/deck/build2.js`) | Opens with the real site video, then the boxes, the voice note, the facts, video → schedule/GAEB, evidence, delay Gantt, notice, live demo, Challenge B fit, positioning, close. **No app slide.** |
| Video `pitch/video` (Remotion, 1920×1080, 30 fps, about 2:51) | Cold open (35 s site clip) → title → boxes → water zoom → voice note → facts → "with or without BIM" → no-BIM schedule drop → BIM (Schependomlaan) → mapping → notice → 4 live dashboard grabs → close → end card. Voice-over is a macOS placeholder (Daniel/Anna). **No app scene.** |
| App `mobile/` | Merged to `main`. Tabs: **Heute** (KPIs, camera proposals with one-tap confirm, open activities, tap element → state), **Erfassen** (zone; video with commentary, photo, voice note, typed note; offline queue; live pipeline steps; result card with confirmed / proposed / absences / deliveries / events), **Scan** (walk-through → objects with frames → 3D link), **Bericht** (today's Bautagebuch, PDF). Settings: server, token, connect QR. shadcn look (React Native Reusables), German UI. |
| User journey `docs/USER-JOURNEY.md` | Setup (no BIM: P6 + GAEB drop; BIM: IFC; nothing: scan) → morning (Heute) → during the day (Erfassen, 30–60 s) → correcting (tap) → scan → end of day (Bericht) → Bauleiter dashboard. |

## 3. What to change

### Story (both deck and video)

Today the story jumps from "site video" straight to "what Tagwerk extracted". Put the **site manager and the phone** in
between, so the audience sees who records, how little effort it is, and what they get back:

1. Site clip (keep the cold open).
2. **The recording is one tap in the app**: Erfassen, zone, "Video mit Kommentar", Senden. Works without signal (queue).
3. Engine (boxes, voice note, facts, mapping to schedule and GAEB): keep, it is the core.
4. **Back on the phone**: the result card (green "bestätigt" from the sentence, amber "Vorschlag" from the camera only). On Heute one tap confirms the proposal; the activity bar moves.
5. Dashboard updates live (existing grabs), Bericht on the phone at the end of the day, notice draft for the Bauleiter.

Keep the video at about **3:00**. To make room, shorten the BIM block, the four live grabs (merge to two), and the close.

### Video: new scenes (`pitch/video/src/Video.tsx`, add to `SCENES`)

| Scene | Content | Length | VO (add to `vo/lines.json` and `vo/ELEVENLABS.md`) |
|---|---|---|---|
| AppRecord | Phone frame with the Erfassen screen; tap "Video mit Kommentar"; zone chip "Bühne"; "Senden an Bühne"; toast "Gespeichert · wird gesendet, sobald Netz da ist" | 6–8 s | "On site, it's one tap. Pick the zone, film, talk. No signal? It waits and sends later." |
| AppResult | Job card: steps "Sprache erkannt → Bilder ausgewertet → Fakten zugeordnet", then green and amber badges | 6–8 s | "A minute later the phone shows what Tagwerk understood. Green was said. Amber was only seen." |
| AppConfirm | Heute: proposal card, finger taps "Bestätigen", the activity bar moves; cut to the dashboard updating | 5–7 s | "One tap confirms it. The schedule and the dashboard move with it." |
| AppReport (optional) | Bericht tab, "Als PDF öffnen" | 4 s | "At the end of the day, the site diary is already written." |

Reuse the existing `phone mock` from the `VoiceNote` scene for the frame.

### Deck (`pitch/deck/build2.js`)

- New slide after the voice-note slide: **"Die App für die Bauleitung vor Ort"**. Three phone screenshots side by side (Erfassen → result card → Heute confirm), one line each.
- New slide or panel: **user journey** in one row (Setup → Morgens → Tagsüber → Korrigieren → Abends → Bauleitung), from `docs/USER-JOURNEY.md`.
- Live demo slide: add "Handy: Aufnahme → Ergebnis → Dashboard live" as the demo path.
- Challenge B slide: the app answers "documentation with minimal effort on site" directly; say so.

### Phone screenshots and recordings

No phone emulator on the Mac. Two options:

1. **Real phone (best for the video):** Expo Go on the Android phone → `exp://100.118.181.69:8090` (laptop Metro, `~/tw-mobile.sh start`). Screen-record on the phone while doing a real capture against `:8080` (Hörsaal). Ask the user to do this; you cannot drive the phone.
2. **Web build (screenshots now):** in `mobile/`, `npx expo start --web --port 19006`. The API sends no CORS headers, so run the dev proxy that adds them (`node mobile/scripts/cors-proxy.mjs http://100.118.181.69:8080`, listens on :8099) and set the app's server to `http://localhost:8099` (Settings, or `localStorage tw.settings`). Use a 375×812 viewport, light colour scheme. Puppeteer with system Chrome works (`pitch/deck/grab.js` shows the setup).

Do **not** send test captures to `:8080` (the Hörsaal demo state) without the user's OK; use `:8082` (scan project) for test recordings.

### Voice-over

The narration is still the macOS placeholder. The user records it in ElevenLabs from `pitch/video/vo/ELEVENLABS.md`.
Add the new app lines there, then `node scripts/make-vo.mjs --measure-only` after the files land in `public/vo/`.

## 4. Rules

- Commit **as the user**: in the Mac repo `user.name=Anoushk`, `user.email=186037197+Current-cmd@users.noreply.github.com` is set. Never commit as Claude, no co-author lines.
- On the Mac push directly (`git push -u origin <branch>`); the token procedure in CLAUDE.md is only for the laptop.
- One branch per piece (`docs/pitch-app`), PR into `main`, merge when CI is green.
- The rendered MP4 is gitignored (`docs/design-brief/Tagwerk-Demo.mp4`); re-render, don't commit it.
- Laptop: `ssh -o BatchMode=yes anoushk@100.118.181.69`. Tailscale SSH may ask for a re-check: give the user the login URL it prints.
- Palette: shadcn neutral, blue `#2563EB` accent, green `#16A34A` (confirmed), amber `#F59E0B` (proposal), red `#DC2626` (delay). Deck font Arial (QA reliability), video font Geist.

## 5. Done when

- Video ≤ 3:05 with the app scenes, rendered to `docs/design-brief/Tagwerk-Demo.mp4`, stills of every new scene checked.
- Deck rebuilt with the app slide and the journey, PDF exported, every slide rendered and checked for overflow.
- `vo/lines.json` and `vo/ELEVENLABS.md` include the new lines.
- `pitch/README.md` and `DEMO-VIDEO-SHOTLIST.md` match the new order.
- PR merged into `main`.
