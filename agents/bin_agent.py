"""
Bin Agent — 二进制/逆向类 CTF。
拿到 ELF 文件 → file → strings → checksec → r2反编译 → objdump → 试运行
"""

import os, sys, re, subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.base_agent import BaseAgent


def run_cmd(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, timeout=timeout,
                           cwd=os.environ.get("WORKSPACE", "."))
        return r.stdout.decode("utf-8", errors="replace"), r.stderr.decode("utf-8", errors="replace"), r.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", -1
    except Exception as e:
        return "", str(e), -1


def find_binary(chal_dir):
    d = Path(chal_dir)
    ignore = {".json", ".txt", ".md", ".py", ".c", ".cpp", ".sh", ".bat", ".js"}
    for f in sorted(d.iterdir()):
        if f.is_file() and f.suffix not in ignore:
            return str(f)
    return None


def _r2_binary():
    """找 radare2 / rizin 的 CLI 路径。返回可执行名或 None"""
    for name in ("rizin", "r2", "radare2"):
        p = subprocess.run(f"where {name}", shell=True, capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            return name
    return None


# ---- r2 分析模块 ----

def r2_cmd(binary, cmds, timeout=30):
    """用 r2/rizin -q 静默模式跑一串命令，返回 stdout"""
    tool = _r2_binary()
    if not tool:
        return ""
    full = ";".join(cmds)
    out, _, _ = run_cmd(f'{tool} -q -e scr.color=false -c "{full}" "{binary}"', timeout=timeout)
    return out


def r2_info(binary):
    """输出文件头 + 段信息 + 导入导出"""
    cmds = ["iI", "iS", "is", "ii", "iz~flag", "iz~ctf"]
    return r2_cmd(binary, cmds, timeout=20)


def r2_functions(binary):
    """列出所有函数 + 大小"""
    return r2_cmd(binary, ["aaa", "afl"], timeout=30)


def r2_decompile_main(binary):
    """反编译 main 函数（需要 r2dec 插件，跑不了就算了）"""
    return r2_cmd(binary, ["aaa", "s main", "pdg"], timeout=30)


def r2_disasm_interest(binary):
    """反汇编 main + 附近 5 个自定义函数、搜 flag/cmp 分支"""
    cmds = [
        "aaa",
        "s main", "pdi 60",
        "s entry0", "pdi 20",
        "/ flag{",  # 搜汇编里的 flag 字符串引用
    ]
    return r2_cmd(binary, cmds, timeout=30)


def r2_rodata(binary):
    """只读数据段里找可疑常量"""
    cmds = [
        "s .rodata", "p8 128",
        "/c flag", "/c ctf", "/c correct", "/c wrong",
    ]
    return r2_cmd(binary, cmds, timeout=20)


def r2_xrefs(binary):
    """看看哪些指令引用了 flag-related 字符串"""
    cmds = [
        "aaa",
        "axt @@ str.*flag*",
        "axt @@ str.*ctf*",
        "axt @@ str.*correct*",
        "axt @@ str.*password*",
    ]
    return r2_cmd(binary, cmds, timeout=20)


def main():
    workspace = os.environ.get("WORKSPACE", ".")
    chal_dir = os.environ.get("CHALLENGE_DIR", "")
    a = BaseAgent(workspace)

    llm_ok = a._llm("ok", timeout=2)
    mode = "AI" if llm_ok else "basic"
    r2 = _r2_binary()
    print(f"BinAgent @ {workspace} [{mode}] r2={'yes' if r2 else 'no'}")

    raw = a.read_chal()
    desc = raw.strip() if raw else "(无描述)"
    print(f"题目: {desc[:200]}")

    binary = find_binary(chal_dir)
    if not binary:
        if raw.strip():
            print("没找到二进制文件，试 base64...")
            try:
                import base64
                data = base64.b64decode(raw.strip())
                binary = str(Path(workspace) / "target.bin")
                Path(binary).write_bytes(data)
                Path(binary).chmod(0o755)
                print(f"从 base64 还原 → {binary} ({len(data)} bytes)")
            except:
                print("base64 也不行，白给")
                sys.exit(1)
        else:
            print("没二进制也没 base64，跑路")
            sys.exit(1)

    bin_name = os.path.basename(binary)
    print(f"二进制: {bin_name}")

    # ====== Phase 1: file ======
    print("\n--- file ---")
    out, _, _ = run_cmd(f'file "{binary}"')
    print(f"  {out.strip()}")
    is_elf = "ELF" in out
    is_pe = "PE" in out

    # ====== Phase 2: strings ======
    print("\n--- strings ---")
    out, _, _ = run_cmd(f'strings "{binary}"')
    interesting = []
    for line in out.split("\n"):
        line = line.strip()
        if not line:
            continue
        f = a.grep_flag(line)
        if f:
            print(f"  FLAG! {line}")
            print(f"FLAG: {f}")
            return
        if any(kw in line.lower() for kw in
               ("flag", "ctf", "password", "passwd", "secret", "key",
                "correct", "wrong", "congrat", "success", "fail",
                "/bin/sh", "shell", "admin", "debug", "backdoor")):
            interesting.append(line)

    if interesting:
        print(f"  可疑字符串 ({len(interesting)} 条):")
        for s in interesting[:20]:
            print(f"    {s[:120]}")
        if llm_ok:
            insight = a.ai_analyze_binary("\n".join(interesting[:50]), out[:300] if out else "unknown")
            if insight:
                print(f"AI: {insight[:300]}")

    # ====== Phase 3: hexdump ======
    print("\n--- hexdump 搜 flag ---")
    raw_bytes = Path(binary).read_bytes()
    for pat in (b"flag{", b"FLAG{", b"ctf{", b"CTF{"):
        idx = 0
        while True:
            idx = raw_bytes.find(pat, idx)
            if idx == -1:
                break
            chunk = raw_bytes[idx:idx + 60]
            try:
                text = chunk.decode("ascii", errors="replace")
                f = a.grep_flag(text)
                if f:
                    print(f"  hex: {text}")
                    print(f"FLAG: {f}")
                    return
            except: pass
            idx += 1

    # ====== Phase 4: checksec ======
    if is_elf:
        print("\n--- checksec ---")
        try:
            from pwn import ELF
            e = ELF(binary)
            print(f"  Arch: {e.arch}  Bits: {e.bits}  Endian: {e.endian}")
            print(f"  RELRO: {e.relro}  Canary: {e.canary}  NX: {e.nx}  PIE: {e.pie}  Stripped: {'yes' if e.stripped else 'no'}")
            if e.entry:
                print(f"  Entry: 0x{e.entry:x}")
        except ImportError:
            print("  pwntools 没装")
        except Exception as ex:
            print(f"  checksec 挂了: {ex}")

    # ====== Phase 5: r2 深度分析 ======
    if r2:
        print("\n--- r2 info ---")
        out = r2_info(binary)
        if out:
            for line in out.split("\n")[:30]:
                line = line.strip()
                if line:
                    f = a.grep_flag(line)
                    if f:
                        print(f"  → FLAG! {f}")
                        print(f"FLAG: {f}")
                        return
                    print(f"  {line[:130]}")

        print("\n--- r2 functions ---")
        out = r2_functions(binary)
        if out:
            lines = out.strip().split("\n")
            print(f"  函数数: {len(lines)}")
            # 只看非系统函数（地址开头 0x4/0x0 的，通常是你自己的代码）
            user_funcs = [l for l in lines if l.strip() and "sym.imp." not in l and "entry" in l.lower() or ("main" in l.lower() and "libc" not in l.lower())]
            for line in lines[:25]:
                line = line.strip()
                if line:
                    print(f"  {line[:130]}")

        print("\n--- r2 disasm ---")
        out = r2_disasm_interest(binary)
        if out:
            for line in out.split("\n"):
                line = line.strip()
                if not line: continue
                # 高亮 flag 相关
                if any(kw in line.lower() for kw in ("flag", "ctf", "cmp", "jne", "je ", "jz ", "call", "lea", "mov")):
                    if len(line) < 140:
                        print(f"  {line}")
                # 搜汇编注释里的 flag
                f = a.grep_flag(line)
                if f:
                    print(f"  → FLAG! {line}")
                    print(f"FLAG: {f}")
                    return

        print("\n--- r2 xrefs ---")
        out = r2_xrefs(binary)
        if out:
            for line in out.split("\n")[:15]:
                line = line.strip()
                if line:
                    print(f"  {line[:130]}")

        print("\n--- r2 decompile ---")
        out = r2_decompile_main(binary)
        if out and "pdg" not in out[:50]:
            for line in out.split("\n")[:40]:
                line = line.strip()
                if line:
                    print(f"  {line[:130]}")

    # ====== Phase 6: objdump ======
    if is_elf:
        print("\n--- objdump ---")
        out, _, _ = run_cmd(f'objdump -d -M intel "{binary}" 2>&1 | head -80')
        for line in out.split("\n"):
            line = line.strip()
            if re.search(r'(flag|FLAG|ctf|CTF)', line):
                print(f"  >>> {line}")
            if any(tag in line for tag in ("<main>:", "<win>:", "<flag>:", "<check>:", "<validate>:")):
                print(f"  {line}")

    # ====== Phase 7: 试运行 ======
    print("\n--- 试运行 ---")
    tests = [
        ("AAAA", "AAAA"),
        ("%x.%x.%x.%x", "fmtstr?"),
        ("flag", "flag"),
        ("admin", "admin"),
    ]
    for inp, label in tests:
        try:
            r = subprocess.run([binary], input=inp.encode(), capture_output=True, timeout=3)
            stdout = r.stdout.decode("utf-8", errors="replace").strip()[:200]
            stderr = r.stderr.decode("utf-8", errors="replace").strip()[:200]
            if stdout or stderr:
                f = a.grep_flag(stdout + stderr)
                if f:
                    print(f"  input='{label}' → FLAG! {f}")
                    print(f"FLAG: {f}")
                    return
                if stdout:
                    print(f"  input='{label}' → stdout: {stdout[:100]}")
        except Exception as e:
            print(f"  input='{label}' → 挂了: {e}")

    # ====== Phase 8: cyclic ======
    if is_elf:
        print("\n--- pwntools cyclic ---")
        try:
            from pwn import cyclic, process
            payload = cyclic(200)
            try:
                p = process([binary])
                p.sendline(payload)
                try:
                    outs = p.recvall(timeout=3).decode("utf-8", errors="replace")
                    f = a.grep_flag(outs)
                    if f:
                        print(f"  overflow → FLAG! {f}")
                        print(f"FLAG: {f}")
                        return
                    print(f"  正常返回 {len(outs)} bytes")
                except:
                    p.close()
                    print("  segfault! 有缓冲区溢出")
            except: pass
            finally:
                try: p.close()
                except: pass
        except ImportError:
            print("  pwntools 没装")
        except Exception as ex:
            print(f"  cyclic 挂了: {ex}")

    # ====== 最终兜底 ======
    print("\n--- 兜底 strings ---")
    out, _, _ = run_cmd(f'strings "{binary}"')
    for line in out.split("\n"):
        for f in a.grep_all_flags(line):
            print(f"  {line.strip()}")
            print(f"FLAG: {f}")
            return

    print("没搞出来，白给了")


if __name__ == "__main__":
    main()
