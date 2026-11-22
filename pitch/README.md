# Pitch and demo video

**Next step:** `../docs/tasks/HANDOFF-pitch.md` (bring the mobile app into the deck and the video).

Everything for the Challenge B pitch: the deck, the demo video, and the material they are built from.
The product side lives in the app (`../mobile/`), the dashboard (`/app` on the laptop API) and
`../docs/USER-JOURNEY.md` (roles, journey, ready checklist).

## Where things are

| What | Path |
|---|---|
| Deck (13 slides, opens with the site video) | `../docs/design-brief/Tagwerk-Pitch.pptx` / `.pdf` |
| Deck generator (pptxgenjs) | `deck/build2.js` (current), `deck/build.js` (v1), `deck/site-slides.js` |
| App screenshots for deck and video | `../docs/design-brief/app-grabs/` (made by `deck/grab.js`, puppeteer against the laptop API) |
| Site footage, frames, hand-corrected boxes | `../docs/design-brief/site-frames/` (`opening-baugrube.mp4`, `det-*.jpg`, `boxes.json`, `worker-output/`) |
| Briefs and story | `../docs/design-brief/DECK-BRIEF.md`, `VIDEO-BRIEF.md`, `SITE-NARRATIVE.md`, `DEMO-VIDEO-SHOTLIST.md`, `README.md` (palette) |
| Demo video project (Remotion 4) | `video/` (scenes in `video/src/Video.tsx`, timeline in `SCENES` at the bottom) |
| Voice-over script and clips | `video/vo/lines.json`, `video/public/vo/*.wav`, `video/scripts/make-vo.mjs` |

The rendered video (`Tagwerk-Demo.mp4`, about 75 MB) is not in git. Render it from `video/`.

## Video

```sh
cd pitch/video
npm install
npm run studio                          # edit and preview
npm run render                          # -> out/tagwerk-demo.mp4 (uses the installed Google Chrome, see remotion.config.ts)
node scripts/make-vo.mjs                # regenerate placeholder voice-over with macOS `say`
node scripts/make-vo.mjs --measure-only # after dropping real recordings (e.g. ElevenLabs) into public/vo/<id>.wav
```

Scene lengths stretch to fit each voice-over clip (`src/vo.json`).

## Deck

```sh
cd pitch/deck
npm install
PPTX_SKILL=<path to the pptx skill> NODE_PATH=$PWD/node_modules node build2.js   # writes ../../docs/design-brief/Tagwerk-Pitch.pptx
```

`PPTX_SKILL` points at the Anthropic pptx skill folder (for `scripts/apply_theme.js`).

## Open points

- Voice-over is a macOS placeholder voice; the ElevenLabs script is `video/vo/ELEVENLABS.md`.
- No music yet.
- The Behinderungsanzeige (notice) scene is a mock; the excavation schedule IDs and BoQ positions are examples.
- The video and deck predate the mobile app: add the app (capture → result on the phone → dashboard) to the demo.
