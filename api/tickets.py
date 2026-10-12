import json
from http.server import BaseHTTPRequestHandler

from backend.vercel_queue import create_ticket


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            self.send_response(201)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(create_ticket(), ensure_ascii=False).encode("utf-8"))
        except Exception as exc:
            self.send_response(503)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8"))
