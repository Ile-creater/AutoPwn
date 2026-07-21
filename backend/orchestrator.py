import asyncio, json
from pathlib import Path

# ctfSolver 风格：五阶段管道
PHASES = ["explore", "scan", "solve", "exec", "verify"]
PHASE_EMOJI = {"explore": "🔎", "scan": "📡", "solve": "🧠", "exec": "⚡", "verify": "✅"}

TYPE_LABEL = {
    "crypto": "CryptoAgent", "web": "WebAgent", "bin": "BinAgent",
    "misc": "MiscAgent", "ai": "AIAgent", "pwn": "BinAgent",
}


class Orchestrator:
    def __init__(self, challenges_dir, push_log, push_agent, push_chal, broadcast):
        self.dir = challenges_dir
        self.log = push_log
        self.push_agent = push_agent
        self.push_chal = push_chal
        self.bcast = broadcast
        self.chals = []
        self._saved = []
        self._running = False

    async def _merge(self):
        existing = {c["id"] for c in self.chals}
        for c in self._saved:
            if c["id"] not in existing:
                self.chals.append(c)
                existing.add(c["id"])
        self.chals.sort(key=lambda c: c["difficulty"])

    async def scan(self):
        self.chals = []
        if self.dir.exists():
            for folder in sorted(self.dir.iterdir()):
                if not folder.is_dir(): continue
                meta = folder / "challenge.json"
                if not meta.exists(): continue
                try:
                    d = json.loads(meta.read_text(encoding="utf-8"))
                except:
                    await self.log("Orch", f"读取 {folder.name}/challenge.json 崩了")
                    continue
                self.chals.append({
                    "id": d.get("id", folder.name),
                    "title": d.get("title", folder.name),
                    "type": d.get("type", "misc"),
                    "difficulty": d.get("difficulty", 3),
                    "status": "pending",
                    "folder": str(folder),
                    "url": d.get("url", ""),
                    "hints": d.get("hints", ""),
                    "phase": "explore",
                })
        await self._merge()
        await self.bcast({"type": "scan_result", "challenges": [
            {k: c[k] for k in ("id", "title", "type", "difficulty", "status", "phase")}
            for c in self.chals
        ]})

    async def solve_all(self, use_docker=False):
        if self._running:
            await self.log("Orch", "已经在跑了")
            return
        self._running = True

        from backend.agent_runner import run_agent

        async def solve_one(c):
            agent_type = c.get("type", "crypto")
            label = TYPE_LABEL.get(agent_type, "Agent")
            name = f"{label}-{c['id']}"

            # 五阶段管道推送
            for phase in PHASES:
                c["phase"] = phase
                emoji = PHASE_EMOJI.get(phase, "")

                await self.push_agent({
                    "id": c["id"], "name": name, "status": "running",
                    "current_challenge": f"{emoji} {phase}: {c['title']}",
                })

                if phase == "explore":
                    c["status"] = "running"
                    await self.push_chal(c)

                elif phase == "solve":
                    # 真正的解题发生在 solve 阶段
                    ok, flag, _ = await run_agent(c, self.log, use_docker=use_docker)
                    c["status"] = "solved" if ok and flag else "failed"
                    c["flag"] = flag
                    await self.push_chal(c)
                    # 如果解出来了，跳过后面两阶段
                    if ok and flag:
                        break

                elif phase == "verify":
                    # 验证阶段：对解出来的 flag 做一次最终检查
                    if c.get("flag") and agent_type in ("crypto", "misc"):
                        # 非网络题重新跑一次确认
                        ok2, flag2, _ = await run_agent(c, self.log, use_docker=use_docker)
                        if ok2 and flag2 == c["flag"]:
                            await self.log(c["id"], "[verify] flag 确认一致 ✓")
                        else:
                            await self.log(c["id"], "[verify] flag 不一致，以第一次为准")
                    elif c.get("flag"):
                        await self.log(c["id"], "[verify] skip (网络题不重跑)")

            # 完成
            await self.push_agent({
                "id": c["id"], "name": name, "status": "done",
                "current_challenge": None,
            })

        tasks = [solve_one(c) for c in self.chals if c["status"] != "solved"]
        if tasks:
            await asyncio.gather(*tasks)

        self._running = False
        await self.bcast({"type": "all_done"})
