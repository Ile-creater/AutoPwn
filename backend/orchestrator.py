import json
from pathlib import Path


class Orchestrator:
    def __init__(self, challenges_dir, push_log, push_agent, push_chal, broadcast):
        self.dir = challenges_dir
        self.log = push_log
        self.push_agent = push_agent
        self.push_chal = push_chal
        self.bcast = broadcast
        self.chals = []

    async def scan(self):
        self.chals = []

        if not self.dir.exists():
            await self.bcast({"type": "error", "message": "challenges/ 目录不存在"})
            return

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
            })

        # easy first
        self.chals.sort(key=lambda c: c["difficulty"])

        await self.bcast({
            "type": "scan_result",
            "challenges": [{k: c[k] for k in ("id", "title", "type", "difficulty", "status")} for c in self.chals],
        })

    async def solve_all(self):
        from backend.agent_runner import run_agent

        for i, c in enumerate(self.chals):
            if c["status"] == "solved":
                continue

            agent = {"id": f"a-{i+1}", "name": f"CryptoAgent-{i+1}", "status": "running", "current_challenge": c["title"]}
            await self.push_agent(agent)

            c["status"] = "running"
            await self.push_chal(c)

            agent_type = c.get("type", "crypto")
            ok, flag = await run_agent(c, self.log, agent_type)

            if ok and flag:
                c["status"] = "solved"
                c["flag"] = flag
            else:
                c["status"] = "failed"
            await self.push_chal(c)

            agent["status"] = "done"
            agent["current_challenge"] = None
            await self.push_agent(agent)

        await self.bcast({"type": "all_done"})
