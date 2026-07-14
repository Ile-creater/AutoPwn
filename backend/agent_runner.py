import asyncio, os, sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


async def run_agent(chal, log, agent_type="crypto"):
    """把 challenge 丢给子进程跑，把 stdout 一行行推出去。返回 (solved, flag)。"""
    workspace = BASE_DIR / "workspace" / chal["id"]
    workspace.mkdir(parents=True, exist_ok=True)

    # 现在只有 crypto agent，后面再加别的
    script = BASE_DIR / "agents" / f"{agent_type}_agent.py"
    if not script.exists():
        await log("runner", f"没找到 agent 脚本: {script}")
        return False, None

    chal_file = Path(chal["folder"]) / "challenge.txt"
    if not chal_file.exists():
        await log("runner", "没有 challenge.txt")
        return False, None

    env = {**os.environ, "CHALLENGE_FILE": str(chal_file), "WORKSPACE": str(workspace)}

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
        return flag is not None, flag

    except Exception as e:
        await log("runner", f"挂了: {e}")
        return False, None
