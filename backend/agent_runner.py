"""
agent_runner — 把挑战丢进独立 Docker 沙箱里跑，stdout 一行行推出去。
每个 challenge type 隔离策略不同：crypto/bin 断网，web 放行。
"""

import asyncio, os, shutil, subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGE = "auto-pwn-agent"

AGENT_MAP = {
    "crypto": "crypto_agent.py",
    "web":    "web_agent.py",
    "bin":    "bin_agent.py",
    "misc":   "misc_agent.py",
    "ai":     "crypto_agent.py",
}

# 哪些类型需要网络
NEEDS_NET = {"web"}


def _docker_exists():
    return shutil.which("docker") is not None


def _image_exists():
    """检查 auto-pwn-agent 镜像在不在本地。"""
    try:
        r = subprocess.run(
            ["docker", "image", "inspect", IMAGE],
            capture_output=True, timeout=5
        )
        return r.returncode == 0
    except:
        return False


async def run_agent(chal, log, use_docker=False):
    """跑 agent。use_docker=True 时用沙箱，否则子进程。返回 (solved, flag, agent_type)。"""
    agent_type = chal.get("type", "crypto")
    script_name = AGENT_MAP.get(agent_type, "crypto_agent.py")

    chal_folder = chal["folder"]
    workspace = BASE_DIR / "workspace" / chal["id"]
    workspace.mkdir(parents=True, exist_ok=True)

    # 没开 docker 或者没装 docker 都走子进程
    if not use_docker:
        return await _run_subprocess(chal, log, agent_type)

    if not _docker_exists():
        await log(chal["id"], "docker 没装，退回 subprocess")
        return await _run_subprocess(chal, log, agent_type)

    if not _image_exists():
        await log(chal["id"], "镜像没构建，退回 subprocess")
        return await _run_subprocess(chal, log, agent_type)

    container_script = f"/app/agents/{script_name}"

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
        "-e", f"CHALLENGE_URL={chal.get('url', '')}",
        "-e", f"CHALLENGE_HINTS={chal.get('hints', '')}",
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
        "CHALLENGE_URL": chal.get("url", ""),
        "CHALLENGE_HINTS": chal.get("hints", ""),
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
