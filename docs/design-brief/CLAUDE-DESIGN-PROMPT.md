# Prompt for Claude Design: Tagwerk pitch deck

Paste everything below the line into Claude Design. Attach screenshots (dashboard, Gantt, task graph, 3D scan,
Tagesbericht, notice draft, phone upload) if available.

---

Create a 12-slide 16:9 pitch deck (1920x1080) for **Tagwerk**, our entry for hackathon Challenge B, "AI Site
Manager Assistant for Documentation, Daily Reports and Claims". It is a 5-minute pitch with a 2-minute live demo
in the middle. The jury mixes construction practitioners (site managers, contractor reps, possibly a construction
lawyer) and technical/VC judges.

**Core message:** The site manager talks while walking the site. By evening Tagwerk has filed the evidence
against the contract (GAEB bill of quantities) and the schedule (Primavera P6), written the Tagesbericht, and
drafted the notice the delay needs. The site manager reviews and signs.

**German tagline:** "Reden statt tippen: der Tagesbericht schreibt sich beim Rundgang."
**Closing line:** "Tagwerk: the day's work, documented."

## Visual system (match our app exactly)
- Look: shadcn/ui neutral theme. White background `#FFFFFF`, ink `#0A0A0A`, surface `#F5F5F5`, border `#E5E5E5`,
  muted text `#737373`. Dark slides (title, demo, close) on `#141416`.
- One accent only: blue `#2563EB` (voice/recording).
- Semantic colours, used only for meaning: done `#16A34A`, in progress `#F59E0B`, delay/critical `#DC2626`,
  vision-only proposal `#8B5CF6` dashed. At most one semantic colour per slide besides blue. Red only where there
  is a delay or claim risk.
- Font: Geist (fallback Inter). Headings semibold 40-48 pt, body 18-22 pt, KPI numbers 60-96 pt tabular.
  Small uppercase muted labels 12-14 pt with +0.04em tracking.
- 12-column grid, 96 px margins, 24 px gutters. Cards with 10 px radius, 1 px border, no shadows.
- Lucide line icons, 2 px stroke (Mic, Video, FileText, CalendarClock, TriangleAlert, Users, CloudRain, Network,
  Box, Check).
- Logo: black rounded square with a white "T".
- Tone: calm, factual, practitioner-first. German site terms stay German (Tagesbericht, Behinderungsanzeige,
  Verzug +1 AT). No "revolutionary", no "AI lawyer". No pie charts, no 3D charts.

## Slides
1. **Tagwerk** (dark). Logo, tagline, team, "Challenge B: AI Site Manager Assistant". Full-bleed photo of a site
   manager on site holding a phone, darkened.
2. **16:30 im Baucontainer.** Scattered inputs (photos, voice memos, paper diary, emails) collapsing into one
   empty Bautagebuch form. Small stat: "35 % of working time goes to non-productive work such as searching for
   project data and rework" (FMI/PlanGrid 2018, ~600 construction leaders), cited in small type.
3. **Ein vergessener Satz kostet Wochen.** Timeline: 10:00 excavator idle, 10:05 quick phone call, nothing in
   writing, weeks later the claim is rejected. VOB/B §6(1): hindrance must be reported "unverzüglich
   schriftlich", otherwise extension of time and compensation can be lost. Same for Mehrkostenanzeige (§2) and
   Bedenkenanzeige (§4(3)).
4. **Reden statt tippen.** One capture, four outputs: phone (30 s video + voice) fanning out to (1) live evidence
   graph, (2) dashboard with forecast, (3) Tagesbericht PDF, (4) notice draft (Behinderungsanzeige).
5. **Demo: ein Tag auf der Baustelle** (dark). Only "LIVE" and a small URL/QR. Placeholder for switching to the
   browser.
6. **Vom Satz zum Bauteil.** Horizontal pipeline: phone upload, Whisper speech-to-text, YOLO + ArUco vision,
   weather, structuring (Claude or German rule fallback), project state, Neo4j graph, live dashboard. Footer:
   "Runs on one laptop GPU. Works offline."
7. **Beweis statt Behauptung.** Three trust rules: voice confirms, vision only proposes (dashed violet); states
   only go up, every change keeps its quote and timestamp; every element linked to a GAEB position and a P6
   activity. Mini graph: GAEB position, activity, zone, recording, event.
8. **Abweichung erkannt, bevor sie teuer wird.** Gantt-style chart: baseline vs forecast bar with a hatched red
   slip segment, annotation "2x Trockenbau krank, +1 AT". KPI chips: Ist/Soll %, SPI, Prognose-Ende 01.12.,
   Verzug +1 AT, offene Mängel. Caption: "projection from today's evidence".
9. **Vom Verzug zur Anzeige.** Split: left, Tagesbericht section "5. Behinderungen / Verzug" (activity, cause,
   +AT, quote, time); right, the generated Behinderungsanzeige draft (project, contract, hindering circumstance,
   since when, affected works, expected schedule effect) with "Entwurf, Prüfung durch Bauleitung" stamp and an
   approve/edit button. Footer: "Entwurfsunterstützung, keine Rechtsberatung."
10. **Challenge B: abgedeckt.** Checklist grid with green ticks: voice capture on mobile; daily report analysis
    vs plan; notice drafts from keywords; structured summaries; correspondence on deviation; human in the loop;
    PDF export.
11. **Positionierung.** 2x2: x axis capture effort (manual forms to passive talk/film), y axis link to contract
    and schedule (free text to element-level BoQ + schedule). Fieldwire, Procore Daily Log bottom-left; Capmo,
    PlanRadar bottom-right; P6 top-left; Buildots, Doxel top-right but "needs BIM + hardware"; Tagwerk top-right
    in blue, "works without BIM, captures causes". Proof strip: 2,082-element real BIM project, P6 XML / GAEB
    X83/X84 / .ics exports, automated tests. Footnote "Based on public vendor information, Nov 2026."
12. **Tagwerk** (dark, title photo). Core message, "Next: pilot with one Bauleiter", contact/QR, disclaimer
    "Entwurfsunterstützung, keine Rechtsberatung."

Add short speaker notes per slide (2-3 sentences). Keep each slide to one idea.
