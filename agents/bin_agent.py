"""
Bin Agent — 二进制/逆向类 CTF。
拿到 ELF 文件 → checksec → strings → 静态分析 → 试运行
"""

import os, sys, re, subprocess, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.base_agent import BaseAgent


def run_cmd(cmd, timeout=10):
    """跑一条 shell 命令，返回 (stdout, stderr, returncode)"""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, timeout=timeout,
                           cwd=os.environ.get("WORKSPACE", "."))
        return r.stdout.decode("utf-8", errors="replace"), r.stderr.decode("utf-8", errors="replace"), r.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", -1
    except Exception as e:
        return "", str(e), -1


def find_binary(chal_dir):
    """在题目目录中找二进制文件。跳过 .json .txt .md"""
    d = Path(chal_dir)
    ignore = {".json", ".txt", ".md", ".py", ".c", ".cpp", ".sh", ".bat", ".js"}
    for f in sorted(d.iterdir()):
        if f.is_file() and f.suffix not in ignore:
            return str(f)
    return None


def main():
    workspace = os.environ.get("WORKSPACE", ".")
    chal_dir = os.environ.get("CHALLENGE_DIR", "")
    a = BaseAgent(workspace)

    llm_ok = a._llm("ok", timeout=2)
    mode = "AI" if llm_ok else "basic"
    print(f"BinAgent @ {workspace} [{mode}]")

    raw = a.read_chal()
    desc = raw.strip() if raw else "(无描述)"
    print(f"题目: {desc[:200]}")

    # 找二进制文件
    binary = find_binary(chal_dir)
    if not binary:
        # 尝试从 challenge.txt 里找 base64 编码的二进制，还原到 workspace
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

    # ====== Phase 1: file 识别 ======
    print("\n--- file ---")
    out, _, _ = run_cmd(f'file "{binary}"')
    print(f"  {out.strip()}")
    is_elf = "ELF" in out
    is_pe = "PE" in out

    # ====== Phase 2: strings 捞字符串 ======
    print("\n--- strings ---")
    out, _, _ = run_cmd(f'strings "{binary}"')
    interesting = []
    for line in out.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 找 flag 或可疑字符串
        f = a.grep_flag(line)
        if f:
            print(f"  FLAG! {line}")
            print(f"FLAG: {f}")
            return

        # 捞有意思的行
        if any(kw in line.lower() for kw in
               ("flag", "ctf", "password", "passwd", "secret", "key",
                "correct", "wrong", "congrat", "success", "fail",
                "/bin/sh", "shell", "admin", "debug", "backdoor")):
            interesting.append(line)

    if interesting:
        print(f"  可疑字符串 ({len(interesting)} 条):")
        for s in interesting[:20]:
            print(f"    {s[:120]}")

        # AI 分析 strings 输出
        if llm_ok:
            insight = a.ai_analyze_binary("\n".join(interesting[:50]), out[:300] if out else "unknown")
            if insight:
                print(f"AI: {insight[:300]}")

    # ====== Phase 3: hexdump 找内嵌 flag ======
    print("\n--- hexdump 搜 flag ---")
    raw_bytes = Path(binary).read_bytes()
    # 直接搜 flag{ 字节
    for pat in (b"flag{", b"FLAG{", b"ctf{", b"CTF{"):
        idx = 0
        while True:
            idx = raw_bytes.find(pat, idx)
            if idx == -1:
                break
            # 往后截 60 字节
            chunk = raw_bytes[idx:idx + 60]
            try:
                text = chunk.decode("ascii", errors="replace")
                f = a.grep_flag(text)
                if f:
                    print(f"  hex 里找到: {text}")
                    print(f"FLAG: {f}")
                    return
            except:
                pass
            idx += 1

    # ====== Phase 4: checksec (ELF 才有) ======
    if is_elf:
        print("\n--- checksec ---")
        try:
            from pwn import ELF
            e = ELF(binary)
            print(f"  Arch: {e.arch}  Bits: {e.bits}  Endian: {e.endian}")
            print(f"  RELRO: {e.relro}")
            print(f"  Stack Canary: {e.canary}")
            print(f"  NX: {e.nx}")
            print(f"  PIE: {e.pie}")
            print(f"  Stripped: {'yes' if e.stripped else 'no'}")

            # 看一下入口点附近的反汇编
            if e.entry:
                print(f"  Entry: 0x{e.entry:x}")

            # 列出符号里的关键函数
            syms = {k: v for k, v in e.symbols.items() if not k.startswith("_")}
            if syms:
                print(f"\n  函数符号 ({len(syms)} 个):")
                for name, addr in sorted(syms.items(), key=lambda x: x[1]):
                    print(f"    0x{addr:x}  {name}")

        except ImportError:
            print("  pwntools 没装，跳过")
            print("  (pip install pwntools)")
        except Exception as ex:
            print(f"  checksec 挂了: {ex}")

    # ====== Phase 5: objdump 反汇编前几个函数 ======
    if is_elf:
        print("\n--- objdump (main / 入口附近) ---")
        out, _, _ = run_cmd(f'objdump -d -M intel "{binary}" 2>&1 | head -80')
        for line in out.split("\n"):
            line = line.strip()
            # 搜 flag 相关的汇编
            f = re.findall(r'(flag|FLAG|ctf|CTF)', line)
            if f:
                print(f"  >>> {line}")
            # 搜可疑的 call / lea
            if "main>:" in line or "<win>" in line or "<flag>" in line:
                print(f"  {line}")

    # ====== Phase 6: 试运行 ======
    # 传几个常用输入看看输出
    print("\n--- 试运行 ---")
    tests = [
        ("AAAA", "AAAA"),
        ("%x.%x.%x.%x", "格式化字符串?"),
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

    # ====== Phase 7: pwntools cyclic pattern 试缓冲区溢出 ======
    if is_elf and not is_pe:
        print("\n--- pwntools cyclic (探测溢出) ---")
        try:
            from pwn import cyclic, process

            # 先用一个长输入试试会不会 segfault
            payload = cyclic(200)
            try:
                p = process([binary])
                p.sendline(payload)
                try:
                    outs = p.recvall(timeout=3).decode("utf-8", errors="replace")
                    f = a.grep_flag(outs)
                    if f:
                        print(f"  FLAG from overflow! {f}")
                        print(f"FLAG: {f}")
                        return
                    print(f"  长输入后正常返回，{len(outs)} bytes 输出")
                except:
                    # 可能 segfault 了——说明有溢出
                    p.close()
                    print("  segfault! 有缓冲区溢出漏洞")
                    print("  (漏洞存在但自动利用还没做，需要人工写 exploit)")
            except:
                pass
            finally:
                try:
                    p.close()
                except:
                    pass

        except ImportError:
            print("  pwntools 没装")
        except Exception as ex:
            print(f"  cyclic 探测挂了: {ex}")

    # ====== 最终：strings 再全扫一遍 ======
    print("\n--- 最终扫描 ---")
    out, _, _ = run_cmd(f'strings "{binary}"')
    for line in out.split("\n"):
        for f in a.grep_all_flags(line):
            print(f"  {line.strip()}")
            print(f"FLAG: {f}")
            return

    print("没搞出来，白给了")


if __name__ == "__main__":
    main()
