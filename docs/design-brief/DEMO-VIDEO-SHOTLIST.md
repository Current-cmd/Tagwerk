# Tagwerk demo video v2: "Das Einzige war das Wasser"

Replaces the shot list in `VIDEO-BRIEF.md` §3. Style (§5), the Hörsaal recording checklist (§4.4) and the risk
notes (§6) in that brief still apply.

**Length:** 3:00. **Format:** 1920×1080, 30 fps. **Language:** German site audio and dictation with burned-in
English captions; English voice-over (VO) for the explanations.
**Story:** the video follows the deck. It opens on 35 s of real excavation footage with no explanation, then takes
that clip apart: what the camera saw, what the site manager said, and how it lands on the schedule and the GAEB
bill of quantities. The water remark turns into a delay and a notice draft. Then the same engine runs live on the
seeded Hörsaal project, and the video closes back on the water.

## Structure

| Act | Time | Purpose | Deck slide |
| --- | --- | --- | --- |
| 1 Cold open | 0:00–0:35 | The real clip, uncut. Make the jury watch a site, not a product | 1 |
| 2 Breakdown | 0:35–1:20 | What Tagwerk saw (boxes) and heard (voice note) | 2, 3 |
| 3 Connection | 1:20–2:00 | Clip → element → P6 activity → GAEB position; water → delay → notice | 6, 8, 9 |
| 4 Live engine | 2:00–2:40 | Real screen capture on the Hörsaal project: dashboard, forecast, Tagesbericht, PDF | 10 |
| 5 Close | 2:40–3:00 | Back to the wall crest; the sentence is now documented | 13 |

## Shot list

Status: **have** = asset exists, **record** = still to film or screen-capture, **build** = motion graphic in the editor.

| # | Time | Visual | Audio | Captions / on-screen | Asset | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0:00–0:02 | Black, small white text fades in | Site ambience fades up | "Baugrube · 21.11.2026 · 07:40" | none | build |
| 2 | 0:02–0:15 | `opening-baugrube.mp4` 0–13 s, vertical clip centred on dark background (as in deck slide 1): pit, crane lifting scaffold, wall-crest walk with water | Original audio | At 0:02 (the line at 0:00–0:02 of WA0000): DE small grey "Ich weiß nicht, wie tief das ist." / EN "I don't know how deep that is." | `site-frames/opening-baugrube.mp4` | have |
| 3 | 0:15–0:35 | Same file 13–35 s: excavation under the steel struts, two excavators, tractor hauling | Original audio | Near the end: DE "… das Einzige … war das Wasser." / EN "… the only thing … was the water." Hold the last frame 1 s | same | have |
| 4 | 0:35–0:40 | Freeze on the last frame; title card slides over: "35 Sekunden. Was hat Tagwerk daraus gemacht?" | Music in (soft) | EN subtitle "35 seconds. What did Tagwerk make of it?" | none | build |
| 5 | 0:40–0:52 | Four freeze frames side by side (deck slide 2 layout). Boxes draw on one after another: violet equipment, green elements, red water last | VO: "Every second, Tagwerk looks at a frame. Equipment and people, the building elements that are in the contract, and one thing that shouldn't be there." | Box labels from `boxes.json`; stats "33 frames · 17 objects · 1 deviation" | `det-*.jpg` or animate from `site-frames/boxes.json` on the raw frames | build |
| 6 | 0:52–0:58 | Zoom into `det-person` frame, red box "stehendes Wasser" pulses | VO: "Water on the pile wall. The camera can see it. It can't decide what it means." | none | `det-person.jpg` | build |
| 7 | 0:58–1:10 | Phone in hand (vertical, picture-in-picture left third): site manager taps record on `/upload` and speaks. Right two thirds: the transcript appearing | Dictation (DE, recorded clean): "Baugrube Abschnitt drei. Aushub dritte Lage unter der zweiten Steifenlage zur Hälfte fertig, zwei Bagger, ein Traktor mit Mulde. Gerüst an Achse zwölf umgesetzt. An der Bohrpfahlwand Nord steht Wasser, die Wasserhaltung reicht nicht." | EN captions, two lines at a time | phone footage + screen capture of `/upload` | record |
| 8 | 1:10–1:20 | Five fact cards stack in (deck slide 3 right column): 3× green, 1× red, 1× violet "Bohrgerät ×2 · offen" | VO: "Each sentence confirms something the camera saw. The piling rigs got no sentence, so they stay a proposal." | Card text as on slide 3 | none | build |
| 9 | 1:20–1:35 | Graph build: from the `struts-excavator` thumbnail, lines draw to "Baugrube BA 3, Lage 3" → "B2030 Aushub Lage 3" → "LV 01.02.0030 Aushub BK 3–5, m³"; chip "Ist 50 %" turns green | VO: "Every fact lands on an element, a schedule activity and a contract position. Progress is weighted by the bill of quantities." | Small footer: "Example LV positions for this site" | deck slide 6 row 1 | build |
| 10 | 1:35–1:45 | Second row draws: water → "Bohrpfahlwand Nord" → "B2040 Wasserhaltung" → "B2060 Sohle" | VO: "The water goes onto the dewatering activity. The slab can only start after the excavation." | none | deck slide 6 row 4 | build |
| 11 | 1:45–1:52 | Gantt (deck slide 8): red slip segment grows on Aushub, then Sohle moves; KPI "+2 AT" flips in | Music swell | "Sohle betonieren +2 AT · projection from today's evidence" | deck slide 8 | build |
| 12 | 1:52–2:00 | Notice draft (deck slide 9) slides in; cursor clicks "Freigeben & PDF" | VO: "And the delay that needs a notice gets a draft, with the video attached. The site manager decides." | "Entwurfsunterstützung, keine Rechtsberatung" | deck slide 9 or app screen | build / record |
| 13 | 2:00–2:05 | Title card: "Läuft heute schon. Live im Projekt Hörsaal." | VO: "This isn't a mock-up. Here's the engine running on our seeded project." | EN "Running today. Live on our demo project." | none | build |
| 14 | 2:05–2:15 | Screen: `/app#/dashboard`, morning state, then the hero walk replay arriving under "Aufnahmen des Tages" with quotes | Hero walk audio (DE) | EN captions of the dictation | Hörsaal hero walk replay | record |
| 15 | 2:15–2:25 | Dictation "Zwei Mann vom Trockenbau sind krank." → forecast moves 30.11. → 01.12., red delay in the Gantt | Dictation + click | Callout red outline on the forecast KPI | screen capture | record |
| 16 | 2:25–2:40 | `/app#/report/2026-11-26`: Tagesbericht scrolls to "5. Behinderungen / Verzug", notice draft generated, print to PDF | VO: "By evening: the daily report, the schedule impact, and the notice draft. Printed, ready to sign." | none | screen capture | record |
| 17 | 2:40–2:52 | Back to `walk-wall` footage (WA0000 10–13 s), slow push-in, darkened | Original ambience | Large: "„Das Einzige war das Wasser.“" then "Jetzt steht es im Bautagebuch, im Terminplan und in der Anzeige." / EN "Now it's in the site diary, the schedule and the notice." | `opening-baugrube.mp4` 10–13 s | have |
| 18 | 2:52–3:00 | End card (deck slide 13 style): logo, "Tagwerk: the day's work, documented.", team, repo | Music out | Disclaimer: "Entwurfsunterstützung, keine Rechtsberatung." | none | build |

Acts 1 and 5 use only real footage. Acts 2–3 are motion graphics built from the deck slides, which can be exported
as PNG layers. Act 4 is the only live screen capture and must show the real app, never mock data.

## Assets

| Asset | Path (under `docs/design-brief/`) | Use |
| --- | --- | --- |
| Opening clip, 35.2 s, 478×850, H.264 + AAC | `site-frames/opening-baugrube.mp4` | #2, #3, #17 |
| Annotated frames (hand-corrected boxes) | `site-frames/det-crane.jpg`, `det-person.jpg`, `det-dig.jpg`, `det-struts.jpg` | #5, #6 |
| Box coordinates for animating boxes in the editor | `site-frames/boxes.json` | #5 |
| Square thumbnails | `site-frames/*-sq.jpg` | #9, #10 |
| Raw GPU worker output (vision + speech JSON) | `site-frames/worker-output/` | Proof if asked; not on screen |
| Deck slides 2, 3, 6, 8, 9, 13 | `Tagwerk-Pitch.pptx` (export slides as PNG) | #5, #8–#12, #18 |

The source clip is only 478 px wide. Show it at its native size or in a phone frame and never stretch it to full
1080p width. A light sharpen pass in the editor helps.

## Still to record

1. **Voice note (#7).** About 15 s, German, quiet place or lavalier mic, phone held as on site. Read the script in
   #7 exactly. Film the phone screen too (another phone or a screen capture via QuickTime + cable).
2. **Hörsaal screen capture (#14–#16).** Follow `VIDEO-BRIEF.md` §4.4: reset, restart, `DATA_DATE=2026-11-26`, no
   "Demo-Daten" badge, 1920×1080 window at 110–125 % zoom.
3. **Notice draft in the app (#12).** If the letter feature is on the demo branch, capture its real screen for #12
   and #16 instead of the deck mock-up.

## Editing rules

- Vertical footage sits in the centre (Act 1) or the left third in a phone frame (Acts 2 and 4); the right two
  thirds show the effect.
- **Box colours:** violet for equipment and people, green for building elements, red for the deviation. These match
  the deck, and red appears only for the water.
- **Captions:** German original in small grey italics above the English line, only for real site audio and
  dictation.
- **VO:** calm and factual, English, about 140 words per minute. Total VO in the script above is about 120 words.
- **Music:** minimal, no vocals, ducked under speech. One swell at #11.

## Before publishing

- Blur the colleague's face in the wall-walk shots (#2, #6, #17) unless he agrees in writing to appear.
- The excavation schedule, activity IDs and LV positions are examples. Keep the "Example" footer visible in #9–#11,
  or seed this site as a project and capture the real screens instead.
- Test the dictation in #7 against the app before recording. Without an LLM key, the keyword rules don't know
  "Aushub", "Steife" or "Wasserhaltung".
- The boxes are hand-corrected labels on the worker's frames. If a judge asks, the raw detections are in
  `site-frames/worker-output/`. Say the labels were refined for construction vocabulary.
