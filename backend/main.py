"""
CTF Auto-Solver Backend — FastAPI + WebSocket
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path for imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.orchestrator import Orchestrator

app = FastAPI(title="CTF Solver Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WSManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, data: dict):
        msg = json.dumps(data, ensure_ascii=False)
        dead = []
        for ws in self.connections:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def send_log(self, agent_name: str, line: str):
        await self.broadcast({
            "type": "agent_log",
            "agent_name": agent_name,
            "line": line.strip(),
        })

    async def send_agent_update(self, agent: dict):
        await self.broadcast({"type": "agent_update", "agent": agent})

    async def send_challenge_update(self, challenge: dict):
        await self.broadcast({"type": "challenge_update", "challenge": challenge})

    async def send_scan_result(self, challenges: list[dict]):
        await self.broadcast({"type": "scan_result", "challenges": challenges})

    async def send_all_done(self):
        await self.broadcast({"type": "all_done"})

    async def send_error(self, message: str):
        await self.broadcast({"type": "error", "message": message})


ws_manager = WSManager()


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)

    challenges_dir = BASE_DIR / "challenges"
    orchestrator = Orchestrator(challenges_dir, ws_manager)

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)

            if data.get("type") == "scan":
                await orchestrator.scan()

            elif data.get("type") == "start":
                asyncio.create_task(orchestrator.solve_all())

    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
