import asyncio, json, os, shutil, sys, uuid, base64
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
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
    title: str = ""
    type: str = "web"        # web / misc / bin / pwn
    url: str = ""             # web 专用
    hints: str = ""           # 提示
    difficulty: int = 2
    content: str = ""         # 题目内容 (文本/base64 附件)

class SolveReq(BaseModel):
    use_docker: bool = False
    challenge_ids: list[str] = []


# ---- 工具检测 ----

TOOL_LINKS = {
    "rizin":       "https://github.com/rizinorg/rizin/releases",
    "ollama":      "https://ollama.com/download",
    "docker":      "https://www.docker.com/products/docker-desktop",
    "pwntools":    "pip install pwntools",
    "binwalk":     "pip install binwalk",
    "exiftool":    "winget install exiftool",
    "steghide":    "winget install steghide",
}

def _check_tool(name):
    if name == "rizin":
        for loc in (r"C:\Program Files\rizin\bin\rizin.exe",
                    r"C:\Program Files (x86)\rizin\bin\rizin.exe",
                    "/usr/bin/rizin", "/usr/local/bin/rizin"):
            if os.path.exists(loc): return True
        return bool(shutil.which("rizin") or shutil.which("r2") or shutil.which("radare2"))
    if name == "ollama":
        return bool(shutil.which("ollama")) or \
               os.path.exists(r"C:\Users\PC\AppData\Local\Programs\Ollama\ollama.exe") or \
               os.path.exists("/usr/local/bin/ollama")
    if name == "docker":
        return bool(shutil.which("docker"))
    if name == "pwntools":
        try: import pwn; return True
        except: return False
    if name == "binwalk":
        return bool(shutil.which("binwalk"))
    if name == "exiftool":
        return bool(shutil.which("exiftool")) or bool(shutil.which("exif"))
    if name == "steghide":
        return bool(shutil.which("steghide"))
    return None


@app.get("/api/tools")
async def tools_status():
    return [{"name": n, "ok": _check_tool(n), "install": TOOL_LINKS.get(n, "")}
            for n in ("rizin", "ollama", "docker", "pwntools", "binwalk", "exiftool")]

TYPE_PREFIX = {"web": "web", "misc": "misc", "bin": "bin", "pwn": "pwn", "ai": "ai"}

@app.post("/api/submit")
async def submit_challenge(req: SubmitReq):
    ctype = req.type if req.type in TYPE_PREFIX else "misc"
    prefix = TYPE_PREFIX[ctype]
    cid = f"{prefix}-{uuid.uuid4().hex[:6]}"
    title = req.title.strip() or f"{ctype.upper()} Challenge"

    folder = _submit_dir / cid
    folder.mkdir(exist_ok=True)

    # 题目内容
    chal_text = req.content.strip() if req.content.strip() else ""
    if ctype == "web" and req.url.strip():
        chal_text = f"{req.url.strip()}\n---\n{req.hints.strip()}" if req.hints.strip() else req.url.strip()

    # 保存
    meta = {"id": cid, "title": title, "type": ctype, "difficulty": req.difficulty,
            "url": req.url.strip(), "hints": req.hints.strip()}
    (folder / "challenge.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    (folder / "challenge.txt").write_text(chal_text, encoding="utf-8")

    chall = {**meta, "status": "pending", "folder": str(folder)}
    # 去重(URL) / 追加(附件题)
    if ctype == "web" and req.url.strip():
        for i, c in enumerate(_saved_chals):
            if c.get("url") == req.url.strip():
                _saved_chals[i] = chall; break
        else:
            _saved_chals.append(chall)
    else:
        _saved_chals.append(chall)

    await push_log("sys", f"收到新题: {title} ({cid}) [{ctype}]")
    await _broadcast({"type": "new_challenge", "challenge": {
        "id": cid, "title": title, "type": ctype,
        "difficulty": req.difficulty, "status": "pending",
    }})
    return {"ok": True, "id": cid, "type": ctype}


@app.post("/api/submit/file")
async def submit_file(
    title: str = Form(default=""),
    type: str = Form(default="misc"),
    hints: str = Form(default=""),
    difficulty: int = Form(default=2),
    file: UploadFile | None = File(default=None),
):
    ctype = type if type in TYPE_PREFIX else "misc"
    prefix = TYPE_PREFIX[ctype]
    cid = f"{prefix}-{uuid.uuid4().hex[:6]}"
    ftitle = title.strip() or f"{ctype.upper()} Challenge"

    folder = _submit_dir / cid
    folder.mkdir(exist_ok=True)

    # 文件存到题目目录
    if file and file.filename:
        fname = file.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]  # 防路径穿越
        raw = await file.read()
        (folder / fname).write_bytes(raw)
        # 也存一份 base64 到 challenge.txt，方便 agent 直接解码
        b64 = base64.b64encode(raw).decode()
        (folder / "challenge.txt").write_text(b64, encoding="utf-8")
    elif hints.strip():
        (folder / "challenge.txt").write_text(hints.strip(), encoding="utf-8")
    else:
        (folder / "challenge.txt").write_text("", encoding="utf-8")

    meta = {"id": cid, "title": ftitle, "type": ctype, "difficulty": difficulty,
            "hints": hints.strip(), "has_file": bool(file and file.filename)}
    (folder / "challenge.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    chall = {**meta, "status": "pending", "folder": str(folder)}
    _saved_chals.append(chall)

    await push_log("sys", f"收到新题: {ftitle} ({cid}) [{ctype}] +文件")
    await _broadcast({"type": "new_challenge", "challenge": {
        "id": cid, "title": ftitle, "type": ctype,
        "difficulty": difficulty, "status": "pending",
    }})
    return {"ok": True, "id": cid, "type": ctype}


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

    # 建连时推送工具状态
    tools = [{"name": n, "ok": _check_tool(n), "install": TOOL_LINKS.get(n, "")}
             for n in ("rizin", "ollama", "docker", "pwntools", "binwalk", "exiftool")]
    await ws.send_text(json.dumps({"type": "tools_status", "tools": tools}, ensure_ascii=False))

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
