"""
Orchestrator — scans challenge directories, sorts by difficulty, dispatches to agents.
"""

import json
import asyncio
from pathlib import Path


class Orchestrator:
    def __init__(self, challenges_dir: Path, ws_manager):
        self.challenges_dir = challenges_dir
        self.ws = ws_manager
        self.challenges: list[dict] = []

    async def scan(self):
        """Scan the challenges directory and load all challenges."""
        self.challenges = []

        if not self.challenges_dir.exists():
            await self.ws.send_error("challenges/ 目录不存在")
            return

        for folder in sorted(self.challenges_dir.iterdir()):
            if not folder.is_dir():
                continue
            meta_file = folder / "challenge.json"
            if not meta_file.exists():
                continue

            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                challenge = {
                    "id": meta.get("id", folder.name),
                    "title": meta.get("title", folder.name),
                    "type": meta.get("type", "misc"),
                    "difficulty": meta.get("difficulty", 3),
                    "status": "pending",
                    "folder": str(folder),
                }
                self.challenges.append(challenge)
            except Exception as e:
                await self.ws.send_error(f"读取 {folder.name}/challenge.json 失败: {e}")

        # Sort by difficulty (easy first)
        self.challenges.sort(key=lambda c: c["difficulty"])

        # Send to frontend
        scan_list = [
            {
                "id": c["id"],
                "title": c["title"],
                "type": c["type"],
                "difficulty": c["difficulty"],
                "status": c["status"],
            }
            for c in self.challenges
        ]
        await self.ws.send_scan_result(scan_list)

    async def solve_all(self):
        """Solve all challenges one by one."""
        from backend.agent_runner import AgentRunner

        for idx, challenge in enumerate(self.challenges):
            if challenge["status"] == "solved":
                continue

            agent_id = f"agent-{idx + 1}"
            agent_name = f"CryptoAgent-{idx + 1}"

            await self.ws.send_agent_update({
                "id": agent_id,
                "name": agent_name,
                "status": "running",
                "current_challenge": challenge["title"],
            })

            await self.ws.send_challenge_update({
                "id": challenge["id"],
                "title": challenge["title"],
                "type": challenge["type"],
                "difficulty": challenge["difficulty"],
                "status": "running",
            })

            runner = AgentRunner(challenge, self.ws, agent_name)
            result = await runner.run()

            if result.get("solved"):
                challenge["status"] = "solved"
                challenge["flag"] = result["flag"]
                await self.ws.send_challenge_update({
                    **challenge,
                    "flag": result["flag"],
                })
            else:
                challenge["status"] = "failed"
                await self.ws.send_challenge_update({
                    **challenge,
                })

            await self.ws.send_agent_update({
                "id": agent_id,
                "name": agent_name,
                "status": "done",
                "current_challenge": None,
            })

        await self.ws.send_all_done()
