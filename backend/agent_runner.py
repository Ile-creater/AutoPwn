"""
AgentRunner — launches a subprocess agent, captures stdout, relays via WebSocket.
"""

import asyncio
import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class AgentRunner:
    def __init__(self, challenge: dict, ws_manager, agent_name: str):
        self.challenge = challenge
        self.ws = ws_manager
        self.agent_name = agent_name
        self.workspace = BASE_DIR / "workspace" / challenge["id"]
        self.workspace.mkdir(parents=True, exist_ok=True)

    async def run(self) -> dict:
        """Run the matching agent for this challenge type."""
        agent_type = self.challenge.get("type", "crypto")

        # Map challenge type to agent script
        agent_scripts = {
            "crypto": BASE_DIR / "agents" / "crypto_agent.py",
            "misc": BASE_DIR / "agents" / "crypto_agent.py",
            "ai": BASE_DIR / "agents" / "crypto_agent.py",
        }

        script = agent_scripts.get(agent_type, agent_scripts["crypto"])
        if not script.exists():
            await self.ws.send_log(self.agent_name, f"Agent 脚本不存在: {script}")
            return {"solved": False}

        challenge_file = Path(self.challenge["folder"]) / "challenge.txt"
        if not challenge_file.exists():
            await self.ws.send_log(self.agent_name, "challenge.txt 不存在")
            return {"solved": False}

        env = os.environ.copy()
        env["CHALLENGE_ID"] = self.challenge["id"]
        env["CHALLENGE_FILE"] = str(challenge_file)
        env["WORKSPACE"] = str(self.workspace)

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                str(script),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
                cwd=str(self.workspace),
            )

            result_flag = None
            async for line in proc.stdout:
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                await self.ws.send_log(self.agent_name, text)

                # Check for flag in output
                if "FLAG:" in text:
                    result_flag = text.split("FLAG:")[-1].strip()

            await proc.wait()

            return {
                "solved": result_flag is not None,
                "flag": result_flag,
            }

        except Exception as e:
            await self.ws.send_log(self.agent_name, f"运行异常: {e}")
            return {"solved": False, "error": str(e)}
