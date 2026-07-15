"""
agent_runner — 把挑战丢进独立 Docker 沙箱里跑，stdout 一行行推出去。
每个 challenge type 隔离策略不同：crypto/bin 断网，web 放行。
"""

import asyncio, os, shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGE = "auto-pwn-agent"

AGENT_MAP = {
    "crypto": "crypto_agent.py",
    "web":    "web_agent.py",
    "bin":    "bin_agent.py",
    "misc":   "crypto_agent.py",
    "ai":     "crypto_agent.py",
}

# 哪些类型需要网络
NEEDS_NET = {"web"}


def _docker_exists():
    return shutil.which("docker") is not None


async def run_agent(chal, log):
    """Docker 沙箱里跑 agent。返回 (solved, flag, agent_type)。"""
    agent_type = chal.get("type", "crypto")
    script_name = AGENT_MAP.get(agent_type, "crypto_agent.py")
    container_script = f"/app/agents/{script_name}"

    chal_folder = chal["folder"]
    workspace = BASE_DIR / "workspace" / chal["id"]
    workspace.mkdir(parents=True, exist_ok=True)

    # Docker 不存在就退回子进程模式
    if not _docker_exists():
        await log(chal["id"], "docker 没装，退回 subprocess 模式")
        return await _run_subprocess(chal, log, agent_type)

    # 构建 docker run 命令
    network = "none" if agent_type not in NEEDS_NET else "bridge"
    cmd = [
        "docker", "run", "--rm",
        "--network", network,
        "--memory", "512m",
        "--cpus", "1",
        "-v", f"{chal_folder}:/chal:ro",
        "-v", f"{workspace}:/ws",
        "-e", f"CHALLENGE_FILE=/chal/challenge.txt",
        "-e", "CHALLENGE_DIR=/chal",
        "-e", "WORKSPACE=/ws",
        IMAGE,
        "python", container_script,
    ]

    await log(chal["id"], f"[sandbox] network={network}")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
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
        await log(chal["id"], f"sandbox 挂了: {e}")
        return False, None, agent_type


async def _run_subprocess(chal, log, agent_type):
    """fallback：没有 docker 时直接子进程跑"""
    import sys

    script_name = AGENT_MAP.get(agent_type, "crypto_agent.py")
    script = BASE_DIR / "agents" / script_name
    chal_file = Path(chal["folder"]) / "challenge.txt"
    workspace = BASE_DIR / "workspace" / chal["id"]
    workspace.mkdir(parents=True, exist_ok=True)

    env = {
        **os.environ,
        "CHALLENGE_FILE": str(chal_file),
        "CHALLENGE_DIR": chal["folder"],
        "WORKSPACE": str(workspace),
    }

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
