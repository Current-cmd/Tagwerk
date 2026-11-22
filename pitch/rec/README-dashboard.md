# Dashboard screen recordings

Real recordings of the running web dashboard for the 2-minute video (`pitch/STORYBOARD-2min.md`, shots D3, D4, D5, D6,
D8, D9). Output: `pitch/video/public/rec/dash-*.mp4` (H.264, 1920×1080, 30 fps, no audio) and `dash-*.json`
(`seconds`, `marks`, `capture` statistics).

| File | Shot | What happens |
|---|---|---|
| `dash-flip` | D3 | Dashboard on plan; the script POSTs the site manager's capture; the page updates over its websocket; cursor: KPI, red Gantt rows, new events, new recording |
| `dash-trace` | D4 | Click "Bestuhlung neu", activity sheet (Verzug, Ursache, GAEB position, Aufnahmen), click `walk-2611`, the recording opens |
| `dash-graph` | D5 | Live-Graph: recording node (hover, click), its two events, the red activity, its GAEB position, click on the activity opens the sheet |
| `dash-forecast` | D6 | Three days back with the arrow, drag the slider past Heute to 01.12., one day further, press Heute |
| `dash-report` | D8 | Tagesbericht 26.11.: sections 1 to 5, scroll, back up to "Druckversion (HTML)" (not clicked: it opens a new tab) |
| `dash-bim` | D9 | Schependomlaan, BIM-Modell, "Bauablauf abspielen" from the first day of the schedule to the data date (real time, about 0.8 s per working day; speed it up in the edit) |

## Re-run from a clean state

```sh
cd <repo>
pitch/rec/servers.sh reset      # stops :8080, scripts/reset_demo.py, rm -rf cache/walk-2611, starts :8080 (Hörsaal, seeded)
pitch/rec/servers.sh start      # starts :8081 (Schependomlaan) if it is not running
node pitch/rec/record-dashboard.mjs            # all six, in order (about 4 minutes, most of it the BIM playback)
node pitch/rec/record-dashboard.mjs trace graph   # single shots; they need the state after `flip`
node pitch/rec/frames.mjs dash-flip 1 3.6 10   # ffprobe line + stills in /tmp/tw-frames to check by eye
pitch/rec/servers.sh reset && pitch/rec/servers.sh stop   # leave Hörsaal clean, stop both servers
```

`flip` changes the project state (it is the capture), so it runs first and refuses to start unless the KPI is on plan
(forecast 01.12., 0 days late). `trace`, `graph`, `forecast` and `report` are recorded on the state after `flip`.
The servers run with `TAGWERK_DEV=1 NEO4J_URI=` (no token, in-memory graph), without `TAGWERK_STUBS`; the note is typed.

Options (environment): `DSF` device scale factor (default 1.35, i.e. a 1422×800 CSS viewport rendered at 1920×1080;
1.2 shows more, 1.5 clips the Gantt), `BIM_UNTIL=2015-04-30` stops the BIM playback earlier, `CAPTURE_TS` sends a `ts`
with the capture (the API's time override; without it the recording carries the wall-clock time of the run),
`TW_TOOLS` a folder whose `node_modules` has `puppeteer-core` and `@remotion/compositor-*`, `CHROME` the browser binary.

## How it records

- `lib.mjs`: headless Google Chrome through `puppeteer-core`; CDP `Page.startScreencast` (JPEG, quality 93). The
  screencast only delivers device pixels when the scale factor is forced at browser level
  (`--force-device-scale-factor`) in addition to the viewport's, otherwise the frames are CSS-sized.
- The screencast sends a frame whenever the picture changes (up to 60 per second here). The frames are resampled to a
  constant 30 fps by their timestamps (each output frame = the last captured frame at or before its time) and piped as
  MJPEG into Remotion's bundled ffmpeg (`libx264 -crf 16 -pix_fmt yuv420p`). No system ffmpeg is needed; the tools are
  taken from `pitch/video/node_modules` or `../demo-video/node_modules`.
- Marks are seconds from the first frame, taken from the same clock as the frame timestamps.
- Cursor: headless Chrome draws none. The only thing added to the page is an overlay (`#tw-rec-cursor`,
  `pointer-events: none`) that follows the real pointer events sent through CDP, plus a ripple on pointerdown.
  Everything else is the app as served: all clicks, hovers, drags and wheel scrolls are real input events.
- `dash-graph` hides the replay panel with the page's own toggle before the recording starts, and reads the node
  positions from the vis-network instance (read-only) to know where to move the mouse.
- WebGL for the BIM view runs on SwiftShader (`--enable-unsafe-swiftshader`); this Mac has no GPU.
