# Narrative: "Das Einzige war das Wasser" (real site footage)

Two real phone clips from a deep excavation (Baugrube), filmed 21.11.2026. Both are vertical, 478×850.

| Clip | Length | What is in it | Audio (Whisper, German) |
| --- | --- | --- | --- |
| `VID-20261121-WA0000.mp4` | 13 s | Pile wall and pit, snow patches, MEWP, site container; tower crane lifting a scaffold section; walk along the wall crest with a hi-vis colleague, standing water beside the walkway, piling rigs behind | "Ich weiß nicht, wie tief das ist." (0–2 s) |
| `VID-20261121-WA0003.mp4` | 22 s | Excavation under steel pipe struts, two excavators digging, a tractor with dump trailer hauling spoil, dust/water spray | Mostly unclear; clearly audible: "… das Einzige, was … war das Wasser." |

Stills are in `site-frames/` (`walk-wall`, `crane-lift`, `struts-excavator`, `struts-haul`, plus `-sq` thumbnails).

## The story in one line

Thirty-five seconds of phone video on a real site become a Bautagebuch entry. Every observation is tied to a schedule
activity and a contract position, and one throwaway sentence about water turns into a delay with a notice draft.

## Story beats (for the pitch and the video)

1. **07:40, Kontrollgang Pfahlwand** (`walk-wall`). The site manager walks the wall crest. Water stands along the
   wall. He says it out loud. *Engine:* voice note → event "Wasser an Bohrpfahlwand Nord" on activity
   *Wasserhaltung*. The camera sees a hi-vis vest (person), nothing more.
2. **08:15, Gerüst umsetzen** (`crane-lift`). The crane moves a scaffold section. *Engine:* vision detects `crane`;
   with no spoken confirmation this stays a **proposal** (dashed violet) on *Gerüst umsetzen*. This is the
   human-in-the-loop moment: the camera suggests, the site manager decides.
3. **09:30, Aushub unter Steifen** (`struts-excavator`). Two excavators under the struts. Dictation: "Aushub dritte
   Lage halb fertig." *Engine:* `excavator ×2`, `pipe` (struts) plus the sentence → progress 50 % on activity
   *Aushub Lage 3*, BoQ-weighted against the GAEB excavation position (m³).
4. **09:45, Abfuhr** (`struts-haul`). Tractor and dump trailer. *Engine:* loads counted as evidence for the
   *Boden laden und abfahren* position, which feeds the Aufmaß.
5. **The turn.** Back to the real audio: "Das Einzige … war das Wasser." Dewatering is behind, so the slab
   (*Sohle*), which finishes-to-start after it, moves. Forecast shifts, the Gantt turns red.
6. **17:00.** Tagesbericht written, the delay section filled with the quote, time and affected activity, and a
   Behinderungsanzeige draft waiting for approval. Disclaimer: drafting support, no legal advice.

## Deck (added)

- **Slide 5** "35 Sekunden Video. Ein ganzer Bautagebuch-Eintrag." Four real frames with detection chips (dashed
  violet = camera proposal) and voice chips (blue = confirms).
- **Slide 6** "Vom Video zu Terminplan und LV". One row per piece of evidence: signal → element/zone → P6
  activity → GAEB position → effect (Ist 50 %, Fuhren fürs Aufmaß, Vorschlag, Verzug + Anzeige).

## Demo video segment (about 45 s, insert after the hook)

| # | Time | Visual | Audio / VO | On-screen |
| --- | --- | --- | --- | --- |
| 1 | 0:00–0:05 | `WA0000` 0–3 s, pit pan | Site ambience | "Baugrube, 21.11. Echtes Handyvideo." |
| 2 | 0:05–0:12 | `WA0000` 6–9 s, crane lift | Ambience | Violet dashed chip "crane → Vorschlag" pops on |
| 3 | 0:12–0:20 | `WA0003` 0–8 s, excavators under struts | Dictation: "Aushub dritte Lage halb fertig." | Chips `excavator ×2`, `pipe → Steife`; blue voice chip |
| 4 | 0:20–0:27 | `WA0000` 10–13 s, wall crest with water | Real audio: "… das Einzige war das Wasser." | Blue voice chip with the quote, English caption |
| 5 | 0:27–0:37 | Screen capture: graph links clip → element → activity → GAEB position | VO: "Every sentence lands on an element, an activity and a contract position." | Slide 6 row animation as fallback |
| 6 | 0:37–0:45 | Screen capture: Gantt slip and Behinderungsanzeige draft | VO: "The water becomes a delay, and the delay becomes a draft notice. The site manager signs." | "Entwurf, keine Rechtsberatung" |

Edit notes: keep the clips vertical in a phone frame next to the screen capture (picture-in-picture), and blur the
colleague's face in `walk-wall` unless you have his consent. Add English captions to all German audio.

## What has to be true before you show this as live

1. **The engine needs this site as a project.** The seeded projects are the Hörsaal and Schependomlaan; neither has
   excavation, struts or dewatering. To show it live, create a small seed (zones, elements, activities B2030–B2060,
   GAEB positions) or run `scripts/scan_video.py <clip> --make-project baugrube` and add the activities and BoQ
   by hand. Until then, the activity ids and LV positions on slide 6 are examples. The slide footnote says so.
2. **The rule fallback does not know excavation words.** `structure.py` and `seed/glossary.txt` cover the
   auditorium vocabulary. "Aushub", "Steife", "Wasserhaltung" will only be understood via the Claude path or after
   adding aliases. Test the exact dictation line before recording.
3. **The original audio is weak.** Only the water sentence is usable. Record the progress dictation ("Aushub
   dritte Lage halb fertig") separately and lay it over the footage, or re-film on site.
4. **Vision vocabulary.** `crane`, `excavator`, `pipe`, `safety vest`, `hard hat` are in the YOLO-World class list
   (`tagwerk/pipeline/vision.py`); "dump trailer" and "scaffold" are not, so check what the worker actually returns
   on these clips and use those labels in the overlays.
5. **Two projects in one pitch.** The live demo runs on the Hörsaal; this footage is a different site. Either frame
   the Baugrube as "the real-world test" before switching to the rehearsed demo, or seed the Baugrube and make it
   the demo.
