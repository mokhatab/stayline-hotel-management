from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.parse import parse_qs, urlparse

from hotel_management.interfaces.http.controllers import HotelController


HTML = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stayline Hotel Operations</title>
<style>
body{font-family:Inter,system-ui,sans-serif;background:#f4f7fb;color:#172033;margin:0}
main{max-width:1050px;margin:0 auto;padding:48px 24px}.eyebrow{color:#2b6cb0;font-weight:700;letter-spacing:.1em;text-transform:uppercase;font-size:12px}
h1{font-size:42px;margin:8px 0}.sub{color:#667085}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-top:28px}
.card{background:white;border:1px solid #e4e9f1;border-radius:16px;padding:22px;box-shadow:0 8px 25px #192b4410}
.metric{font-size:30px;font-weight:750;margin:10px 0 3px}.muted{color:#667085;font-size:14px}
button{background:#172033;color:#fff;border:0;border-radius:9px;padding:11px 16px;font-weight:650;cursor:pointer}
pre{white-space:pre-wrap;background:#0f172a;color:#dbeafe;padding:16px;border-radius:10px;min-height:90px}
</style></head>
<body><main><div class="eyebrow">Stayline / hotel operations</div>
<h1>Run the front desk from one place.</h1><p class="sub">A Clean Architecture starter for rooms, guests, reservations, and stays.</p>
<div class="grid"><div class="card"><div class="muted">Rooms in inventory</div><div class="metric" id="rooms">—</div><div class="muted">Seeded for the starter environment</div></div>
<div class="card"><div class="muted">Availability search</div><div class="metric">Ready</div><div class="muted">Try the API below</div></div>
<div class="card"><div class="muted">Business core</div><div class="metric">Isolated</div><div class="muted">No database or web framework required</div></div></div>
<div class="card" style="margin-top:16px"><h2>Quick availability check</h2><p class="muted">Search seeded rooms without touching infrastructure from the browser.</p>
<button onclick="checkRooms()">Check rooms for 2026-10-01 → 2026-10-03</button><pre id="output">Press the button to query the HTTP adapter.</pre></div>
<script>
async function checkRooms(){const r=await fetch('/api/rooms?check_in=2026-10-01&check_out=2026-10-03&guests=2');const d=await r.json();document.getElementById('output').textContent=JSON.stringify(d,null,2);document.getElementById('rooms').textContent=d.length}
</script></main></body></html>"""


class RequestHandler(BaseHTTPRequestHandler):
    controller: HotelController

    def _respond(self, status: int, payload, content_type: str = "application/json") -> None:
        body = payload if isinstance(payload, bytes) else self.controller.encode(payload)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._respond(200, HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        try:
            if parsed.path == "/api/rooms":
                query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
                status, body = self.controller.list_rooms(query)
                self._respond(status, body)
                return
            self._respond(404, {"error": "Route not found"})
        except Exception as error:
            status, body = self.controller.error(error)
            self._respond(status, body)

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/guests":
                status, body = self.controller.register_guest(payload)
            elif self.path == "/api/bookings":
                status, body = self.controller.create_booking(payload)
            elif self.path.startswith("/api/bookings/") and self.path.endswith("/check-in"):
                booking_id = self.path.removeprefix("/api/bookings/").removesuffix("/check-in")
                status, body = self.controller.check_in(booking_id.rstrip("/"))
            elif self.path.startswith("/api/bookings/") and self.path.endswith("/check-out"):
                booking_id = self.path.removeprefix("/api/bookings/").removesuffix("/check-out")
                status, body = self.controller.check_out(booking_id.rstrip("/"))
            else:
                self._respond(404, {"error": "Route not found"})
                return
            self._respond(status, body)
        except Exception as error:
            status, body = self.controller.error(error)
            self._respond(status, body)

    def log_message(self, format: str, *args) -> None:
        return


def serve(controller: HotelController, host: str = "127.0.0.1", port: int = 8000) -> None:
    handler = type("ConfiguredRequestHandler", (RequestHandler,), {"controller": controller})
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Hotel system running at http://{host}:{port}")
    server.serve_forever()
