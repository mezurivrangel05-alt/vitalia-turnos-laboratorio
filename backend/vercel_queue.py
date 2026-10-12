"""PostgreSQL-backed queue service for Vercel Functions."""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

DESKS = 4
TICKET_DURATION_SECONDS = max(5, int(os.environ.get("TICKET_DURATION_SECONDS", "30")))


def connect():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Falta configurar DATABASE_URL en Vercel.")
    return psycopg.connect(url, row_factory=dict_row, connect_timeout=10)


def now():
    return datetime.now(timezone.utc)


def initialize(db):
    db.execute("""
        CREATE TABLE IF NOT EXISTS vitalia_tickets (
            id TEXT PRIMARY KEY, code TEXT NOT NULL UNIQUE,
            service TEXT NOT NULL, status TEXT NOT NULL,
            desk INTEGER, created_at TIMESTAMPTZ NOT NULL,
            called_at TIMESTAMPTZ, completed_at TIMESTAMPTZ
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS vitalia_queue_status_created ON vitalia_tickets(status, created_at)")
    db.execute("CREATE SEQUENCE IF NOT EXISTS vitalia_ticket_number START 1")


def serialize(row):
    return {
        "id": row["id"], "code": row["code"], "name": row["code"],
        "card": None, "service": row["service"], "status": row["status"],
        "desk": row["desk"],
    }


def advance(db):
    db.execute("SELECT pg_advisory_xact_lock(731204)")
    cutoff = now() - timedelta(seconds=TICKET_DURATION_SECONDS)
    db.execute("UPDATE vitalia_tickets SET status='completed', completed_at=%s WHERE status='called' AND called_at<=%s", (now(), cutoff))
    occupied = {r["desk"] for r in db.execute("SELECT desk FROM vitalia_tickets WHERE status='called'").fetchall()}
    for desk in (n for n in range(1, DESKS + 1) if n not in occupied):
        row = db.execute("SELECT id FROM vitalia_tickets WHERE status='waiting' ORDER BY created_at LIMIT 1 FOR UPDATE").fetchone()
        if row is None:
            break
        db.execute("UPDATE vitalia_tickets SET status='called',desk=%s,called_at=%s WHERE id=%s", (desk, now(), row["id"]))


def state():
    with connect() as db:
        initialize(db)
        advance(db)
        rows = db.execute("SELECT * FROM vitalia_tickets WHERE status != 'completed' ORDER BY created_at").fetchall()
        total = db.execute("SELECT COUNT(*) AS count FROM vitalia_tickets WHERE created_at::date=CURRENT_DATE").fetchone()["count"]
    tickets = [serialize(row) for row in rows]
    return {
        "desks": [{"number": n, "ticket": next((t for t in tickets if t["desk"] == n and t["status"] == "called"), None)} for n in range(1, DESKS + 1)],
        "waiting": [t for t in tickets if t["status"] == "waiting"],
        "total_today": total,
        "waiting_count": sum(t["status"] == "waiting" for t in tickets),
        "service_seconds": TICKET_DURATION_SECONDS,
    }


def create_ticket():
    with connect() as db:
        initialize(db)
        db.execute("SELECT pg_advisory_xact_lock(731204)")
        number = db.execute("SELECT nextval('vitalia_ticket_number') AS number").fetchone()["number"]
        ticket_id, created = str(uuid4()), now()
        code = f"A{number:03d}"
        db.execute("INSERT INTO vitalia_tickets (id,code,service,status,desk,created_at,called_at,completed_at) VALUES (%s,%s,%s,'waiting',NULL,%s,NULL,NULL)", (ticket_id, code, "Aclaración en ventanilla", created))
        advance(db)
        row = db.execute("SELECT * FROM vitalia_tickets WHERE id=%s", (ticket_id,)).fetchone()
    return serialize(row)
