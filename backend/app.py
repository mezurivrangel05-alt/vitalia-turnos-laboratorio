"""HTTP API entrypoint for the Vitalia queue service on Vercel."""
from fastapi import FastAPI, HTTPException

from vercel_queue import create_ticket, state

app = FastAPI(title="Vitalia Turnos API")


@app.get("/api/state")
def get_state():
    try:
        return state()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/tickets", status_code=201)
def post_ticket():
    try:
        return create_ticket()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
