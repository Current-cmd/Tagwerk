# Phone recordings (storyboard D1, D2, D7 and the Bericht tab)

Real recordings of the site manager app (Expo web build) against a real Tagwerk API. Nothing is mocked and
`TAGWERK_STUBS` is not used. On this Mac only the typed-note path runs (no Whisper, no vision).

## Re-run from a clean state

Three servers, each in its own terminal (or in the background), from the repo root:

```sh
pitch/rec/reset-phone-api.sh                               # API on :8090, own state in data-phone/ and cache-phone/, seeded
node mobile/scripts/cors-proxy.mjs http://localhost:8090   # :8099, adds CORS headers and forwards the /events websocket
(cd mobile && npm install && CI=1 npx expo start --web --port 19006)
```

Then record (about 50 s):

```sh
node pitch/rec/record-phone.mjs
```

The script refuses to start unless the API is in its seeded state (on plan, no capture today, Stuhlreihe A 50 %,
camera proposal for Stuhlreihe F). One take changes that state, so run `pitch/rec/reset-phone-api.sh` before every take.
With `CI=1` Metro does not watch files: restart Expo after changing anything under `mobile/`.

puppeteer-core and ffmpeg (Remotion's bundled build, `remotion ffmpeg`) are taken from the first folder that has both in
`node_modules`: `$TW_TOOLS`, `pitch/rec`, `pitch/video`, `../demo-video`. Chrome: `$CHROME` or the installed Google Chrome.
`TW_KEEP_TMP=1` keeps the raw PNG frames.

Stop everything afterwards: `lsof -ti tcp:8090,8099,19006 -sTCP:LISTEN | xargs kill`.

## What it writes

- `pitch/video/public/rec/phone-capture.mp4`, `phone-result.mp4`, `phone-confirm.mp4`, `phone-report.mp4`:
  H.264, yuv420p, 30 fps, no audio, 750×1624 (375×812 CSS px at 2×; 3× would give an odd width).
- `<id>.json` next to each: `{"seconds", "fps", "width", "height", "marks": {name: seconds}}`.
  Marks: `tap_zone`, `tap_note`, `type_start`, `type_end`, `tap_senden`, `processed` · `swipe`, `result_visible` ·
  `tap_heute`, `proposal_visible`, `tap_bestaetigen`, `bar_moved` · `tap_bericht`, `report_visible`, `scroll_1`, `scroll_2`.
- `pitch/deck/deck7/img/phone-capture.png`, `phone-result.png`, `phone-confirm.png`: lossless frames of the same take.

`phone-capture` and `phone-result` are one continuous take cut in two; `phone-confirm` and `phone-report` follow in the
same session, so they show the state after the capture (2 AT delay).

## How it records

Chrome headless with touch emulation; taps and swipes are real touch events, the note is typed key by key.
A "show taps" overlay (grey circle, ripple on touch down) is injected into the page; it is the only thing on screen that
is not the app. Frames come from the CDP screencast (PNG, with timestamps), are resampled to constant 30 fps (each
output frame = the latest screen at that time) and encoded with libx264, CRF 14.
