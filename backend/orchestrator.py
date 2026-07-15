import asyncio, json
from pathlib import Path


TYPE_LABEL = {"crypto": "CryptoAgent", "web": "WebAgent", "bin": "BinAgent", "misc": "MiscAgent", "ai": "AIAgent"}


class Orchestrator:
    def __init__(self, challenges_dir, push_log, push_agent, push_chal, broadcast):
        self.dir = challenges_dir
        self.log = push_log
        self.push_agent = push_agent
        self.push_chal = push_chal
        self.bcast = broadcast
        self.chals = []
        self._saved = []   # 动态提交池，从外面注入
        self._running = False

    async def _merge(self):
        """合并提交池到挑战列表，去重"""
        from backend.agent_runner import AGENT_MAP
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
                if not folder.is_dir():
                    continue
                meta = folder / "challenge.json"
                if not meta.exists():
                    continue
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
                })

        # 合并提交的题
        await self._merge()

        await self.bcast({
            "type": "scan_result",
            "challenges": [{k: c[k] for k in ("id", "title", "type", "difficulty", "status")} for c in self.chals],
        })

    async def solve_all(self, use_docker=False):
        if self._running:
            await self.log("Orch", "已经在跑了，别急")
            return
        self._running = True

        from backend.agent_runner import run_agent

        async def solve_one(c):
            agent_type = c.get("type", "crypto")
            label = TYPE_LABEL.get(agent_type, "Agent")
            name = f"{label}-{c['id']}"

            await self.push_agent({"id": c["id"], "name": name, "status": "running", "current_challenge": c["title"]})
            c["status"] = "running"
            await self.push_chal(c)

            ok, flag, _ = await run_agent(c, self.log, use_docker=use_docker)

            c["status"] = "solved" if ok and flag else "failed"
            c["flag"] = flag
            await self.push_chal(c)

            await self.push_agent({"id": c["id"], "name": name, "status": "done", "current_challenge": None})

        tasks = [solve_one(c) for c in self.chals if c["status"] != "solved"]
        if tasks:
            await asyncio.gather(*tasks)

        self._running = False
        await self.bcast({"type": "all_done"})
