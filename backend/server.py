"""Small, dependency-free HTTP API for the Vitalia clinic queue demo."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

DB_PATH = Path(__file__).with_name("turnos.db")
LOCK = threading.RLock()
DESKS = 4
TICKET_DURATION_SECONDS = max(5, int(os.environ.get("TICKET_DURATION_SECONDS", "30")))


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class QueueService:
    """Owns turn creation, queue ordering, and automatic desk assignment."""

    def __init__(self, path: Path = DB_PATH):
        self.path = path
        self.initialize()

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def initialize(self):
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY, code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL, card TEXT, service TEXT NOT NULL,
                status TEXT NOT NULL, desk INTEGER,
                created_at TEXT NOT NULL, called_at TEXT, completed_at TEXT
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS queue_status_created ON tickets(status, created_at)")

    @staticmethod
    def serialize(row):
        # Do not expose patient names or card numbers on the public queue display.
        result = dict(row)
        result["name"] = result["code"]
        result["card"] = None
        return result

    def advance(self):
        """Expire demo service slots, then fill every free desk in queue order."""
        with LOCK, self.connect() as db:
            cutoff = (datetime.now(timezone.utc) - timedelta(seconds=TICKET_DURATION_SECONDS)).isoformat(timespec="seconds")
            db.execute("UPDATE tickets SET status='completed',completed_at=? WHERE status='called' AND called_at<=?", (now(), cutoff))
            occupied = {r[0] for r in db.execute("SELECT desk FROM tickets WHERE status='called'")}
            for desk in (n for n in range(1, DESKS + 1) if n not in occupied):
                row = db.execute("SELECT id FROM tickets WHERE status='waiting' ORDER BY created_at LIMIT 1").fetchone()
                if row is None:
                    break
                db.execute("UPDATE tickets SET status='called',desk=?,called_at=? WHERE id=?", (desk, now(), row["id"]))

    def state(self):
        self.advance()
        with self.connect() as db:
            rows = db.execute("SELECT * FROM tickets WHERE status != 'completed' ORDER BY created_at").fetchall()
            today = datetime.now().strftime("%Y-%m-%d")
            total = db.execute("SELECT COUNT(*) FROM tickets WHERE substr(created_at,1,10)=?", (today,)).fetchone()[0]
        tickets = [self.serialize(row) for row in rows]
        return {"desks": [{"number": n, "ticket": next((t for t in tickets if t["desk"] == n and t["status"] == "called"), None)} for n in range(1, DESKS + 1)],
                "waiting": [t for t in tickets if t["status"] == "waiting"], "total_today": total,
                "waiting_count": sum(t["status"] == "waiting" for t in tickets), "service_seconds": TICKET_DURATION_SECONDS}

    def create(self):
        with LOCK, self.connect() as db:
            count = db.execute("SELECT COUNT(*) FROM tickets WHERE substr(created_at,1,10)=?", (datetime.now().strftime('%Y-%m-%d'),)).fetchone()[0]
            code = f"A{count + 1:03d}"
            ticket_id = str(uuid4())
            db.execute("INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,?,?)", (ticket_id, code, code, None, "Aclaración en ventanilla", "waiting", None, now(), None, None))
        self.advance()
        with self.connect() as db:
            row = db.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        return self.serialize(row)

    def call_next(self):
        with LOCK, self.connect() as db:
            occupied = {r[0] for r in db.execute("SELECT desk FROM tickets WHERE status='called'")}
            desk = next((n for n in range(1, DESKS + 1) if n not in occupied), None)
            if desk is None:
                raise RuntimeError("Las cuatro mesas están ocupadas.")
            row = db.execute("SELECT * FROM tickets WHERE status='waiting' ORDER BY created_at LIMIT 1").fetchone()
            if row is None:
                raise LookupError("No hay turnos en espera.")
            db.execute("UPDATE tickets SET status='called',desk=?,called_at=? WHERE id=?", (desk, now(), row['id']))
            return self.serialize(db.execute("SELECT * FROM tickets WHERE id=?", (row['id'],)).fetchone())

    def recall(self, ticket_id: str):
        with self.connect() as db:
            row = db.execute("SELECT * FROM tickets WHERE id=? AND status='called'", (ticket_id,)).fetchone()
        if row is None:
            raise LookupError("El turno ya no está en atención.")
        return self.serialize(row)

    def complete(self, ticket_id: str):
        with LOCK, self.connect() as db:
            cur = db.execute("UPDATE tickets SET status='completed',completed_at=? WHERE id=? AND status='called'", (now(), ticket_id))
            if not cur.rowcount:
                raise LookupError("No se encontró un turno activo para finalizar.")
        return {"ok": True}


service = QueueService()


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "http://localhost:4200")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_json(204, {})

    def do_GET(self):
        if urlparse(self.path).path == "/api/state":
            return self.send_json(200, service.state())
        self.send_json(404, {"error": "Ruta no encontrada."})

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/")
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            if path == "/api/tickets":
                return self.send_json(201, service.create())
            if path == "/api/calls/next":
                return self.send_json(200, service.call_next())
            parts = path.split("/")
            if len(parts) == 5 and parts[1:3] == ["api", "calls"]:
                if parts[4] == "recall":
                    return self.send_json(200, service.recall(parts[3]))
                if parts[4] == "complete":
                    return self.send_json(200, service.complete(parts[3]))
            self.send_json(404, {"error": "Ruta no encontrada."})
        except ValueError as exc:
            self.send_json(400, {"error": str(exc)})
        except LookupError as exc:
            self.send_json(404, {"error": str(exc)})
        except RuntimeError as exc:
            self.send_json(409, {"error": str(exc)})
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "El cuerpo debe ser JSON válido."})

    def log_message(self, fmt, *args):
        print(f"{self.log_date_time_string()} {self.address_string()} {fmt % args}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Vitalia API disponible en http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
