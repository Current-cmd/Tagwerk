# Tagwerk design brief: pitch deck and demo video

Two detailed briefs, one shared design system:

- [DECK-BRIEF.md](DECK-BRIEF.md): 12-slide pitch (~5 min) with a 2-min live demo in the middle.
- [VIDEO-BRIEF.md](VIDEO-BRIEF.md): 2:45 "A day in the life of a site manager" demo video, 20-shot list.

## Shared core message

The site manager talks while walking the site. By evening Tagwerk has filed the evidence against the contract
(GAEB) and schedule (P6), filled in the Tagesbericht, and flagged the delay that needs a notice. The site manager
stays in control: vision proposes, voice confirms.

Positioning: voice capture alone is not unique (Capmo, PlanRadar). The difference is the element-level link to
contract and schedule plus the forecast that moves with the day's evidence.

## Unified visual system (both deck and video)

Taken from `web-app/src/index.css` and components:

| Role | Value |
| --- | --- |
| Base | neutral shadcn black/white; dark surfaces `#141416` |
| Accent (only one) | blue `#2563EB` |
| Done | green `#16A34A` (app also uses Tailwind emerald-500/600; use `#16A34A` everywhere in deck and video) |
| In progress / warning | amber `#F59E0B` |
| Delay / defect | red `#DC2626` |
| Vision-only proposal | violet `#8B5CF6`, dashed |
| Type | Geist (Variable) |
| Icons | Lucide |
| Corners | 10 px radius |
| Canvas | 1920x1080, 12-column grid |

State colours carry meaning only, never decoration.

## Challenge B fit (agreed by both briefs)

| Status | Items |
| --- | --- |
| Implemented | phone voice/video capture; daily analysis vs plan (SPI, forecast shifted by absences); auto-filled German Tagesbericht; drafts from photos and 3D scan; in-app deviation alerts |
| Partial | PDF via browser print; human in the loop (no correct/reject UI yet); summaries of voice notes only |
| Roadmap | Behinderungs-, Mehrkosten-, Bedenken-/Mängelanzeige drafts; Word export; email and minutes summaries; automatic correspondence; in-app legal disclaimer |

Roadmap items appear once, on a card labelled "ROADMAP", never as live features. Bridge line: the
"Behinderungen / Verzug" section of the Tagesbericht already holds the facts such a notice needs.

## Open items before production

1. Confirm the forecast numbers (A1080 28.9 % to 34.4 %, finish 30.11. to 01.12.) on a freshly reset state before
   putting them on slides or captions.
2. Quote the test count `pytest` shows on demo day (docs disagree: 83 vs 113).
3. Record a new 25-35 s German site walk in a lecture hall; add it to `demo_replays` in `seed/project.json`.
   Existing footage is not usable: the phone video is a finished venue (no construction), the screen recording is a
   copyrighted third-party video, `id.m4a` is an internal English memo.
4. Do not pitch the `.ics` export as correspondence: it holds captures and daily reports.
5. "Drafting support, no legal advice" on the PDF shot, the end card and the closing slide.
6. No sourced German statistic on documentation time found. FMI/PlanGrid 2018 (35 % of time on non-productive
   work) is the fallback; do not present it as documentation time.
7. Licences: RelateAnything AGPL-3.0, Schependomlaan academic use with attribution (credit on slide).
8. Highest-value build to close the gap before the deadline: a Behinderungsanzeige draft generated from the
   Tagesbericht delay section, with PDF/Word export and an edit/approve step. That would move three roadmap
   items to implemented.
