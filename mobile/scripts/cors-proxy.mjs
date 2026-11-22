// Dev-only: lets the Expo web build call the laptop API (which sends no CORS headers). Not used by the phone.
import http from "node:http";
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
}).listen(8099, () => console.log("proxy :8099 ->", target));
