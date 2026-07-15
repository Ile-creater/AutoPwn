import asyncio, os, sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

AGENT_MAP = {
    "crypto": "crypto_agent.py",
    "web":    "web_agent.py",
    "bin":    "bin_agent.py",
    "misc":   "crypto_agent.py",
    "ai":     "crypto_agent.py",
}


async def run_agent(chal, log):
    """启子进程跑 agent，stdout 一行行推出去。返回 (solved, flag, agent_name)。"""
    agent_type = chal.get("type", "crypto")
    script_name = AGENT_MAP.get(agent_type, "crypto_agent.py")
    script = BASE_DIR / "agents" / script_name
    if not script.exists():
        await log(chal["id"], f"没找到 agent: {script}")
        return False, None, agent_type

    chal_file = Path(chal["folder"]) / "challenge.txt"
    if not chal_file.exists():
        await log(chal["id"], "没有 challenge.txt")
        return False, None, agent_type

    workspace = BASE_DIR / "workspace" / chal["id"]
    workspace.mkdir(parents=True, exist_ok=True)

    env = {
        **os.environ,
        "CHALLENGE_FILE": str(chal_file),
        "CHALLENGE_DIR": chal["folder"],
        "WORKSPACE": str(workspace),
    }

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(script),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            env=env, cwd=str(workspace),
        )

        flag = None
        async for line in proc.stdout:
            text = line.decode("utf-8", errors="replace").strip()
            if not text:
                continue
            await log(chal["id"], text)
            if "FLAG:" in text:
                flag = text.split("FLAG:")[-1].strip()

        await proc.wait()
        return flag is not None, flag, agent_type

    except Exception as e:
        await log(chal["id"], f"挂了: {e}")
        return False, None, agent_type
