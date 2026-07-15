import asyncio, json, os, sys, uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.orchestrator import Orchestrator

app = FastAPI(title="CTF Solver Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# --- WebSocket ---
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

async def push_log(who, text):
    await _broadcast({"type": "agent_log", "agent_name": who, "line": text.strip()})

async def push_agent(a):
    await _broadcast({"type": "agent_update", "agent": a})

async def push_chal(c):
    await _broadcast({"type": "challenge_update", "challenge": c})


# 全局挑战池：扫到的 + 手动提交的都放这里
_saved_chals: list[dict] = []  # 手动提交的题目
_submit_dir = BASE_DIR / "submitted"
_submit_dir.mkdir(exist_ok=True)


class SubmitReq(BaseModel):
    title: str = "Web Challenge"
    url: str
    hints: str = ""
    difficulty: int = 2

class SolveReq(BaseModel):
    use_docker: bool = False
    challenge_ids: list[str] = []


@app.post("/api/submit")
async def submit_challenge(req: SubmitReq):
    """提交一道 Web 题到池子里"""
    cid = f"web-{uuid.uuid4().hex[:6]}"

    # 把题目落盘
    folder = _submit_dir / cid
    folder.mkdir(exist_ok=True)
    (folder / "challenge.json").write_text(json.dumps({
        "id": cid, "title": req.title, "type": "web",
        "difficulty": req.difficulty, "url": req.url, "hints": req.hints,
    }, ensure_ascii=False), encoding="utf-8")
    (folder / "challenge.txt").write_text(f"{req.url}\n---\n{req.hints}", encoding="utf-8")

    chall = {
        "id": cid, "title": req.title, "type": "web",
        "difficulty": req.difficulty, "status": "pending",
        "folder": str(folder), "url": req.url, "hints": req.hints,
    }
    # 去重
    for i, c in enumerate(_saved_chals):
        if c.get("url") == req.url:
            _saved_chals[i] = chall
            break
    else:
        _saved_chals.append(chall)

    await push_log("sys", f"收到新题: {req.title} ({cid}) -> {req.url}")
    await _broadcast({"type": "new_challenge", "challenge": {
        "id": cid, "title": req.title, "type": "web",
        "difficulty": req.difficulty, "status": "pending",
    }})

    return {"ok": True, "id": cid}


@app.post("/api/solve")
async def solve_challenges(req: SolveReq):
    """直接对指定题目启 agent（不走 scan→start 流程）"""
    orch = Orchestrator(BASE_DIR / "challenges", push_log, push_agent, push_chal, _broadcast)
    orch._saved = _saved_chals
    await orch._merge()
    if req.challenge_ids:
        orch.chals = [c for c in orch.chals if c["id"] in req.challenge_ids]
    asyncio.create_task(orch.solve_all(use_docker=req.use_docker))
    return {"ok": True, "count": len(orch.chals)}


@app.websocket("/ws")
async def ws_handler(ws: WebSocket):
    await ws.accept()
    connections.append(ws)

    challenges_dir = BASE_DIR / "challenges"
    orch = Orchestrator(challenges_dir, push_log, push_agent, push_chal, _broadcast)
    orch._saved = _saved_chals  # 共享提交池

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            t = data.get("type")

            if t == "scan":
                await orch.scan()
            elif t == "start":
                await orch._merge()  # 合并提交的题
                asyncio.create_task(orch.solve_all(use_docker=data.get("use_docker", False)))

    except WebSocketDisconnect:
        connections.remove(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
