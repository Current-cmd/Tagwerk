// Dev-only: lets the Expo web build call the laptop API (which sends no CORS headers). Not used by the phone.
import http from "node:http";
import net from "node:net";
const target = process.argv[2] || "http://100.118.181.69:8082";
http.createServer((req, res) => {
  const cors = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*", "Access-Control-Allow-Methods": "GET,POST,OPTIONS" };
  if (req.method === "OPTIONS") { res.writeHead(204, cors); return res.end(); }
  const u = new URL(req.url, target);
  const p = http.request(u, { method: req.method, headers: { ...req.headers, host: u.host } }, (r) => {
    res.writeHead(r.statusCode, { ...r.headers, ...cors }); r.pipe(res);
  });
  p.on("error", (e) => { res.writeHead(502, cors); res.end(JSON.stringify({ detail: String(e) })); });
  req.pipe(p);
}).on("upgrade", (req, socket, head) => {
  // the app's live channel (websocket /events: pipeline steps, refresh on update) goes through the same address
  const u = new URL(target);
  const up = net.connect(Number(u.port) || 80, u.hostname, () => {
    const h = Object.entries({ ...req.headers, host: u.host }).map(([k, v]) => `${k}: ${v}`).join("\r\n");
    up.write(`${req.method} ${req.url} HTTP/1.1\r\n${h}\r\n\r\n`); up.write(head);
    up.pipe(socket); socket.pipe(up);
  });
  up.on("error", () => socket.destroy()); socket.on("error", () => up.destroy());
}).listen(8099, () => console.log("proxy :8099 ->", target));
