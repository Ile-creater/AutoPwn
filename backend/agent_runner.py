"""
agent_runner — 跑 agent，stdout 实时推前端 + 存本地日志，解完自动写 writeup
"""

import asyncio, os, shutil, subprocess, signal
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGE = "auto-pwn-agent"
AGENT_TIMEOUT = 120  # 单个 agent 最多跑 2 分钟

AGENT_MAP = {
    "crypto": "crypto_agent.py", "web": "web_agent.py", "bin": "bin_agent.py",
    "misc": "misc_agent.py", "ai": "ai_agent.py", "pwn": "bin_agent.py",
}
NEEDS_NET = {"web", "ai"}


def _docker_exists():
    return shutil.which("docker") is not None

def _image_exists():
    try:
        r = subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True, timeout=5)
        return r.returncode == 0
    except:
        return False


async def run_agent(chal, log, use_docker=False):
    agent_type = chal.get("type", "crypto")
    script_name = AGENT_MAP.get(agent_type, "crypto_agent.py")

    chal_folder = chal["folder"]
    workspace = BASE_DIR / "workspace" / chal["id"]
    workspace.mkdir(parents=True, exist_ok=True)

    # 日志文件
    log_file = workspace / "output.log"
    log_lines: list[str] = []
    t_start = datetime.now(timezone.utc)

    async def _capture(line):
        text = line.decode("utf-8", errors="replace").strip()
        if not text:
            return
        log_lines.append(text)
        log_file.write_text("\n".join(log_lines), encoding="utf-8")
        await log(chal["id"], text)

    error = None
    if not use_docker:
        ok, flag, error = await _run(chal, log, agent_type, workspace, _capture)
    elif not _docker_exists():
        await log(chal["id"], "docker 没装，退回 subprocess")
        ok, flag, error = await _run(chal, log, agent_type, workspace, _capture)
    elif not _image_exists():
        await log(chal["id"], "镜像没构建，退回 subprocess")
        ok, flag, error = await _run(chal, log, agent_type, workspace, _capture)
    else:
        ok, flag, error = await _run_docker(chal, log, agent_type, workspace, _capture)

    t_end = datetime.now(timezone.utc)
    elapsed = (t_end - t_start).total_seconds()

    # 生成 writeup（含错误信息）
    _write_report(chal, flag, log_lines, elapsed, workspace, error)

    # 记入知识库（成功的才记）
    if flag:
        from backend.knowledge import kb_record as _kb_rec
        _kb_rec(chal, flag, agent_type, log_lines)
    return ok, flag, agent_type, error


async def _run(chal, log, agent_type, workspace, capture):
    import sys
    script_name = AGENT_MAP.get(agent_type, "crypto_agent.py")
    script = BASE_DIR / "agents" / script_name
    chal_file = Path(chal["folder"]) / "challenge.txt"

    env = {
        **os.environ,
        "CHALLENGE_FILE": str(chal_file), "CHALLENGE_DIR": chal["folder"],
        "WORKSPACE": str(workspace),
        "CHALLENGE_URL": chal.get("url", ""), "CHALLENGE_HINTS": chal.get("hints", ""),
    }

    proc = None
    flag = None
    error = None
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(script),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            env=env, cwd=str(workspace),
        )
        try:
            # 用 wait_for 包一个读取协程，而不是包 __aiter__
            async def _read_all():
                f = None
                async for raw_line in proc.stdout:
                    raw_line = raw_line.decode("utf-8", errors="replace").strip() if isinstance(raw_line, bytes) else str(raw_line)
                    if not raw_line: continue
                    await capture(raw_line.encode("utf-8", errors="replace"))
                    if "FLAG:" in raw_line:
                        f = raw_line.split("FLAG:")[-1].strip()
                return f
            flag = await asyncio.wait_for(_read_all(), timeout=AGENT_TIMEOUT)
        except asyncio.TimeoutError:
            error = f"超时 {AGENT_TIMEOUT}s，强制 kill"
            await log(chal["id"], f"[!] {error}")
            if proc.returncode is None:
                proc.kill()
            await capture(f"[!] {error}".encode())
    except FileNotFoundError:
        error = f"agent 脚本找不到: {script}"
        await capture(error.encode())
    except Exception as e:
        error = f"subprocess 挂了: {e}"
        await capture(error.encode())
    finally:
        if proc and proc.returncode is None:
            try:
                proc.kill()
                await proc.wait()
            except: pass

    return (flag is not None, flag, error)


async def _run_docker(chal, log, agent_type, workspace, capture):
    script_name = AGENT_MAP.get(agent_type, "crypto_agent.py")
    container_script = f"/app/agents/{script_name}"
    network = "none" if agent_type not in NEEDS_NET else "bridge"

    cmd = [
        "docker", "run", "--rm", "--network", network, "--memory", "512m", "--cpus", "1",
        "-v", f"{chal['folder']}:/chal:ro", "-v", f"{workspace}:/ws",
        "-e", f"CHALLENGE_FILE=/chal/challenge.txt",
        "-e", f"CHALLENGE_URL={chal.get('url', '')}",
        "-e", f"CHALLENGE_HINTS={chal.get('hints', '')}",
        "-e", "CHALLENGE_DIR=/chal", "-e", "WORKSPACE=/ws",
        IMAGE, "python", container_script,
    ]

    proc = None
    flag = None
    error = None
    await log(chal["id"], f"[sandbox] network={network}")
    try:
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
        try:
            async def _read_all():
                f = None
                async for raw_line in proc.stdout:
                    raw_line = raw_line.decode("utf-8", errors="replace").strip() if isinstance(raw_line, bytes) else str(raw_line)
                    if not raw_line: continue
                    await capture(raw_line.encode("utf-8", errors="replace"))
                    if "FLAG:" in raw_line:
                        f = raw_line.split("FLAG:")[-1].strip()
                return f
            flag = await asyncio.wait_for(_read_all(), timeout=AGENT_TIMEOUT)
        except asyncio.TimeoutError:
            error = f"docker 超时 {AGENT_TIMEOUT}s"
            await log(chal["id"], f"[!] {error}")
            await capture(error.encode())
    except Exception as e:
        error = f"docker 挂了: {e}"
        await capture(error.encode())
    finally:
        if proc and proc.returncode is None:
            try:
                proc.kill()
                await proc.wait()
            except: pass

    return (flag is not None, flag, error)


def _write_report(chal, flag, log_lines, elapsed, workspace, error=None):
    title = chal.get("title", "?")
    cid = chal.get("id", "?")
    ctype = chal.get("type", "?")
    diff = chal.get("difficulty", "?")
    hints = chal.get("hints", "")

    lines = []
    lines.append(f"# Writeup: {title}")
    lines.append("")
    lines.append(f"| 字段 | 值 |")
    lines.append(f"|------|----|")
    lines.append(f"| ID | `{cid}` |")
    lines.append(f"| 类型 | {ctype} |")
    lines.append(f"| 难度 | {'★' * diff} |")
    lines.append(f"| 耗时 | {elapsed:.1f}s |")
    lines.append(f"| 结果 | {'✅ Solved' if flag else ('❌ Failed' + (f' ({error})' if error else ''))} |")
    if flag:
        lines.append(f"| Flag | `{flag}` |")
    if hints:
        lines.append(f"| 提示 | {hints} |")

    # 工具链摘要
    tools_used = set()
    for l in log_lines:
        for t in ("sniff", "decode", "fetch", "run_cmd", "rizin", "checksec", "strings",
                  "binwalk", "exiftool", "steghide", "foremost", "sqlmap", "requests"):
            if t.lower() in l.lower():
                tools_used.add(t)
    if tools_used:
        lines.append(f"| 工具链 | {', '.join(sorted(tools_used))} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 解题过程")
    lines.append("")
    lines.append("```")
    for l in log_lines:
        lines.append(l)
    lines.append("```")

    # AI summary
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*由 AutoPwn 自动生成 · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*")

    (workspace / "writeup.md").write_text("\n".join(lines), encoding="utf-8")
