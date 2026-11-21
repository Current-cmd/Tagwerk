# Tagwerk mobile (site manager app)

Expo (SDK 58) app for the site manager, built with React Native Reusables (shadcn/ui for React Native, NativeWind).
It talks to the Tagwerk API on the GPU laptop over Tailscale. Journey and roles: `../docs/USER-JOURNEY.md`.

| Tab | What it does | API |
|---|---|---|
| Heute | Plan vs actual, SPI, delay; camera proposals to confirm; open activities, tap an element to set its state | `GET /api/overview`, `POST /api/elements/{id}/confirm` |
| Erfassen | Zone, then video with commentary / photo / voice note / typed note. Offline queue, resend with the same `capture_id`, live pipeline steps, result card | `POST /captures`, `GET /captures/{id}`, websocket `/events` |
| Scan | Walk-through video: recognised objects with the frame, 3D scan link | `POST /api/scan`, `/app/#/scan/{id}` |
| Bericht | Today's Bautagebuch; release; PDF; dashboard link | `GET /api/v2/report`, `/export/report.html` |
| ⚙︎ | Server URL (`:8080` Hörsaal, `:8081` Schependomlaan, `:8082` scan), token, connect QR (`tagwerk://connect?url=…&token=…`) | `GET /health`, `GET /zones` |

## Run on the phone (Android, Expo Go)

1. Phone: install **Tailscale** (same tailnet as the laptop) and **Expo Go** from the Play Store.
2. Laptop (Metro runs there; the Mac firewall blocks incoming connections): `~/tw-mobile.sh start` (`stop`, `log`).
   The app source on the laptop is `~/Developer/hacka/tagwerk-mobile`; after changes on the Mac:
   `rsync -az --delete --exclude node_modules --exclude .expo ./ anoushk@100.118.181.69:Developer/hacka/tagwerk-mobile/`
   then `~/tw-mobile.sh stop && ~/tw-mobile.sh start` (CI mode: no live reload).
3. Expo Go: scan `expo-go-qr.png` or enter `exp://100.118.181.69:8090`.
4. The app connects to `http://100.118.181.69:8080` by default; change it under ⚙︎.

## Develop on the Mac

```sh
npm install
npx tsc --noEmit
npx expo start --web --port 19006   # UI in the browser; the API sends no CORS headers, so use a local proxy for web only
```

Add shadcn components with `npx @react-native-reusables/cli@latest add <name>` (they land in `components/ui/`).

## Not done yet

- Standalone APK (`npx eas-cli@latest build -p android --profile preview`) so no Expo Go is needed.
- HTTPS and `API_TOKEN` for anything beyond the demo.
