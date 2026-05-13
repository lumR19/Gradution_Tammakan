"""
fastapi_app.py
--------------
FastAPI backend for Tamakkan Overspeed Detection.

Endpoints
---------
WebSocket  /ws/speed          — Phone app sends GPS speed every second.
POST       /api/speed/manual  — Demo override: set ego speed manually.
GET        /api/status        — Current limit, ego speed, last event.
POST       /api/ocr           — Simulate an OCR frame read (for testing).

Run
---
    pip install fastapi uvicorn
    uvicorn fastapi_app:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from event_engine import EventEngine

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="Tamakkan Overspeed API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single shared engine instance (replace with per-session if multi-user)
engine = EventEngine()

# Active WebSocket connections (for broadcasting events)
_connections: list[WebSocket] = []


# ── WebSocket: phone GPS ───────────────────────────────────────────────────────

@app.websocket("/ws/speed")
async def websocket_speed(ws: WebSocket):
    """
    Phone app connects here and sends JSON messages every ~1 second:

        {"speed_kmh": 95.3}

    The server replies with any fired event (or {"status": "ok"}).
    """
    await ws.accept()
    _connections.append(ws)
    print(f"[WS] Client connected. Total connections: {len(_connections)}")

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
                speed = float(data.get("speed_kmh", 0))
            except (ValueError, KeyError):
                await ws.send_json({"error": "Invalid payload. Expected {speed_kmh: float}"})
                continue

            engine.update_ego_speed(speed)

            # Check overspeed without new OCR reads this tick
            event = engine._check_overspeed()

            if event:
                response = {"status": "OVERSPEED", "event": event}
                # Broadcast to all connected dashboards
                await _broadcast(response)
            else:
                response = {
                    "status": "ok",
                    "ego_speed_kmh": engine.ego_speed_kmh,
                    "current_limit": engine.current_limit,
                }

            await ws.send_json(response)

    except WebSocketDisconnect:
        _connections.remove(ws)
        print(f"[WS] Client disconnected. Remaining: {len(_connections)}")


async def _broadcast(payload: dict):
    dead = []
    for ws in _connections:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.remove(ws)


# ── REST: manual speed override (demo mode) ────────────────────────────────────

class ManualSpeedRequest(BaseModel):
    speed_kmh: float

class ManualSpeedResponse(BaseModel):
    ego_speed_kmh: float
    current_limit: Optional[int]
    event: Optional[dict]


@app.post("/api/speed/manual", response_model=ManualSpeedResponse)
async def set_manual_speed(req: ManualSpeedRequest):
    """
    Demo endpoint — set ego speed without a phone.

    Example:
        curl -X POST http://localhost:8000/api/speed/manual \\
             -H "Content-Type: application/json" \\
             -d '{"speed_kmh": 105}'
    """
    engine.update_ego_speed(req.speed_kmh)
    event = engine._check_overspeed()

    if event:
        asyncio.create_task(_broadcast({"status": "OVERSPEED", "event": event}))

    return ManualSpeedResponse(
        ego_speed_kmh=engine.ego_speed_kmh,
        current_limit=engine.current_limit,
        event=event,
    )


# ── REST: OCR simulation (for testing without video) ──────────────────────────

class OcrFrameRequest(BaseModel):
    ocr_reads: list[str]          # e.g. ["80"]
    ego_speed_kmh: Optional[float] = None

@app.post("/api/ocr")
async def post_ocr_frame(req: OcrFrameRequest):
    """
    Simulate pushing an OCR result from the video pipeline.

    Example:
        curl -X POST http://localhost:8000/api/ocr \\
             -H "Content-Type: application/json" \\
             -d '{"ocr_reads": ["80"], "ego_speed_kmh": 95}'
    """
    event = engine.process_frame(req.ocr_reads, req.ego_speed_kmh)

    if event:
        asyncio.create_task(_broadcast({"status": "OVERSPEED", "event": event}))

    return {
        "current_limit": engine.current_limit,
        "ego_speed_kmh": engine.ego_speed_kmh,
        "event": event,
    }


# ── REST: status ──────────────────────────────────────────────────────────────

@app.get("/api/status")
async def get_status():
    """Current engine state — useful for dashboard polling."""
    return {
        "current_limit": engine.current_limit,
        "ego_speed_kmh": engine.ego_speed_kmh,
        "last_event": engine.last_event,
        "timestamp": time.time(),
    }