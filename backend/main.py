import asyncio, json, os, sys
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.orchestrator import Orchestrator

app = FastAPI(title="CTF Solver Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# 管 WebSocket 连接和群发消息，懒得写类了
connections: list[WebSocket] = []


async def _broadcast(data: dict):
    msg = json.dumps(data, ensure_ascii=False)
    gone = []
    for ws in connections:
        try:
            await ws.send_text(msg)
        except:
            gone.append(ws)
    for ws in gone:
        connections.remove(ws)


# 这几个是快捷方式，省得每次写 type
async def push_log(who, text):
    await _broadcast({"type": "agent_log", "agent_name": who, "line": text.strip()})


async def push_agent(a):
    await _broadcast({"type": "agent_update", "agent": a})


async def push_chal(c):
    await _broadcast({"type": "challenge_update", "challenge": c})


@app.websocket("/ws")
async def ws_handler(ws: WebSocket):
    await ws.accept()
    connections.append(ws)

    challenges_dir = BASE_DIR / "challenges"
    orch = Orchestrator(challenges_dir, push_log, push_agent, push_chal, _broadcast)

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            t = data.get("type")

            if t == "scan":
                await orch.scan()
            elif t == "start":
                asyncio.create_task(orch.solve_all(use_docker=data.get("use_docker", False)))

    except WebSocketDisconnect:
        connections.remove(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
