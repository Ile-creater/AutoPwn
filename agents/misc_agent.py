"""
Misc Agent — 杂项类 CTF。
文件分离 / 隐写 / 元数据 / 编码 / 归档分析
"""

import os, sys, re, base64, subprocess, shutil, zipfile, tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.base_agent import BaseAgent


def run_cmd(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, timeout=timeout,
                           cwd=os.environ.get("WORKSPACE", "."))
        return r.stdout.decode("utf-8", errors="replace"), r.stderr.decode("utf-8", errors="replace"), r.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", -1
    except Exception as e:
        return "", str(e), -1


def find_files(chal_dir):
    """找到题目目录里的非 meta 文件"""
    d = Path(chal_dir)
    skip = {".json", ".txt", ".md", ".pyc"}
    files = []
    for f in sorted(d.iterdir()):
        if f.is_file() and f.suffix not in skip:
            files.append(str(f))
    return files


def try_unarchive(path, dest):
    """尝试解压 zip/tar/gz/bz2，返回提取的文件列表"""
    extracted = []
    try:
        with zipfile.ZipFile(path) as zf:
            zf.extractall(dest, pwd=None)
            extracted = [str(dest / n) for n in zf.namelist()]
            print(f"  ZIP 解压: {len(extracted)} 个文件")
            return extracted
    except:
        pass
    try:
        with tarfile.open(path) as tf:
            tf.extractall(dest)
            extracted = [str(dest / n) for n in tf.getnames()]
            print(f"  TAR 解压: {len(extracted)} 个文件")
            return extracted
    except:
        pass

    # 用 binwalk 自动分离
    out, _, _ = run_cmd(f'binwalk -e --directory="{dest}" "{path}" 2>&1', timeout=20)
    for line in out.split("\n"):
        if "extraction" in line.lower() or "successfully" in line.lower():
            print(f"  binwalk: {line.strip()[:120]}")
    return extracted


def main():
    workspace = os.environ.get("WORKSPACE", ".")
    chal_dir = os.environ.get("CHALLENGE_DIR", "")
    a = BaseAgent(workspace)
    ws = Path(workspace)

    llm_ok = a._llm("ok", timeout=2)
    print(f"MiscAgent @ {workspace} [{'AI' if llm_ok else 'basic'}]")

    raw = a.read_chal()
    desc = raw.strip()[:200] if raw else "(无描述)"
    print(f"题目: {desc}")

    # ====== Phase 0: 找附件 ======
    files = find_files(chal_dir)

    # challenge.txt 如果是纯 base64（够长、无空格），始终当隐藏附件还原
    raw_b64 = raw.strip()
    if len(raw_b64) > 40 and re.match(r'^[A-Za-z0-9+/=]+$', raw_b64) and len(raw_b64) % 4 == 0:
        try:
            data = base64.b64decode(raw_b64)
            if len(data) > 10:
                outpath = ws / "from_b64.bin"
                outpath.write_bytes(data)
                print(f"challenge.txt → base64 解码: {len(data)} bytes → {outpath}")
                files.insert(0, str(outpath))  # 优先处理
        except:
            pass

    # 如果还是没找到，challenge.txt 可能就是纯编码文本
    if not files:
        print("无附件，直接分析文本")
        cur = raw.strip()
        tried = set()
        for rd in range(5):
            todo = [c for c in a.sniff(cur) if (c, len(cur)) not in tried]
            if not todo:
                todo = ["base64"]
            hit = False
            for method in todo:
                tried.add((method, len(cur)))
                r = a.decode(cur, method)
                if r is None:
                    continue
                print(f"  {method} → {r[:120]}")
                f = a.grep_flag(r)
                if f:
                    print(f"FLAG: {f}")
                    return
                # decode 结果里有没有能提取的二进制数据？
                for m in re.finditer(r'[A-Za-z0-9+/=]{12,}', r):
                    chunk = m.group().strip()
                    if len(chunk) % 4 == 0:
                        try:
                            data = base64.b64decode(chunk)
                            if len(data) > 10:
                                p = ws / f"round{rd}.bin"
                                p.write_bytes(data)
                                print(f"  发现内嵌文件: {p} ({len(data)} bytes)")
                                f2 = a.grep_flag(p.read_text(errors="replace"))
                                if f2:
                                    print(f"FLAG: {f2}")
                                    return
                        except:
                            pass

                if a.sniff(r):
                    cur = r; hit = True; break
                cur = r; hit = True; break
            if not hit:
                break

        f = a.grep_flag(cur)
        if f:
            print(f"FLAG: {f}")
        else:
            print("没解出来")
        return

    # ====== Phase 1: 逐文件分析 ======
    print(f"\n找到 {len(files)} 个附件")

    for filepath in files:
        fname = os.path.basename(filepath)
        fsize = os.path.getsize(filepath)
        print(f"\n--- {fname} ({fsize} bytes) ---")

        # 1a. file 识别
        out, _, _ = run_cmd(f'file "{filepath}"')
        ftype = out.strip()
        print(f"  file: {ftype}")

        # 1b. strings 捞 flag
        out, _, _ = run_cmd(f'strings "{filepath}"')
        for line in out.split("\n"):
            line = line.strip()
            flag = a.grep_flag(line)
            if flag:
                print(f"  strings → {flag}")
                print(f"FLAG: {flag}")
                return

        # 1c. hex 搜 flag{
        data = Path(filepath).read_bytes()
        for pat in (b"flag{", b"FLAG{"):
            idx = 0
            while True:
                idx = data.find(pat, idx)
                if idx == -1: break
                chunk = data[idx:idx + 60]
                try:
                    text = chunk.decode("ascii", errors="replace")
                    f = a.grep_flag(text)
                    if f:
                        print(f"  hex → {f}")
                        print(f"FLAG: {f}")
                        return
                except: pass
                idx += 1

        # 1d. exiftool 元数据
        out, _, _ = run_cmd(f'exiftool "{filepath}" 2>&1', timeout=10)
        if out and "exiftool not found" not in out.lower():
            for line in out.split("\n"):
                flag = a.grep_flag(line)
                if flag:
                    print(f"  exiftool → {flag}")
                    print(f"FLAG: {flag}")
                    return
                if any(kw in line.lower() for kw in ("flag", "comment", "description", "warning", "artist", "user")):
                    print(f"  元数据: {line.strip()[:150]}")

        # 1e. 如果是图片，试 steghide
        if any(ext in fname.lower() for ext in (".png", ".jpg", ".jpeg", ".bmp", ".wav")):
            for passwd in ("", "password", "flag", "123456", "admin", "secret"):
                out, _, _ = run_cmd(f'steghide extract -sf "{filepath}" -p "{passwd}" -xf "{ws}/stego_out" 2>&1')
                if "wrote" in out.lower() or "extracted" in out.lower():
                    stego_out = ws / "stego_out"
                    if stego_out.exists():
                        content = stego_out.read_text(errors="replace")
                        print(f"  steghide (pwd={passwd}): {content[:200]}")
                        f = a.grep_flag(content)
                        if f:
                            print(f"FLAG: {f}")
                            return

            # zsteg (PNG/BMP LSB 隐写)
            if fname.lower().endswith((".png", ".bmp")):
                out, _, _ = run_cmd(f'zsteg -a "{filepath}" 2>&1', timeout=15)
                for line in out.split("\n"):
                    flag = a.grep_flag(line)
                    if flag:
                        print(f"  zsteg → {flag}")
                        print(f"FLAG: {flag}")
                        return
                    if any(kw in line.lower() for kw in ("text:", "b1,r", "b1,g", "b1,b")):
                        # 尝试用 base64 解码 zsteg 的输出
                        m = re.search(r'"([^"]+)"', line)
                        if m:
                            val = m.group(1)
                            f = a.grep_flag(val)
                            if f:
                                print(f"  zsteg text → {f}")
                                print(f"FLAG: {f}")
                                return

        # 1f. 如果是压缩包，递归解
        if any(ext in fname.lower() for ext in (".zip", ".tar", ".gz", ".bz2", ".7z", ".rar")) or \
           any(t in ftype.lower() for t in ("zip", "tar", "gzip", "bzip", "7-zip", "rar", "archive", "compressed")):
            extract_dir = ws / f"extracted_{fname}"
            extract_dir.mkdir(exist_ok=True)
            sub_files = try_unarchive(filepath, extract_dir)
            # 递归分析解出的文件
            for sf in sub_files:
                sf_path = Path(sf)
                if sf_path.is_file():
                    try:
                        content = sf_path.read_text(errors="replace")
                        f = a.grep_flag(content)
                        if f:
                            print(f"  解包文件 {sf_path.name} → {f}")
                            print(f"FLAG: {f}")
                            return
                    except:
                        pass
                    # 继续解嵌套压缩包
                    if sf_path.suffix in (".zip", ".tar", ".gz", ".bz2"):
                        sub_extract = ws / f"nested_{sf_path.name}"
                        sub_extract.mkdir(exist_ok=True)
                        sub2 = try_unarchive(str(sf_path), sub_extract)
                        for s2 in sub2:
                            p2 = Path(s2)
                            if p2.is_file():
                                try:
                                    c2 = p2.read_text(errors="replace")
                                    f = a.grep_flag(c2)
                                    if f:
                                        print(f"  嵌套 {p2.name} → {f}")
                                        print(f"FLAG: {f}")
                                        return
                                except: pass

        # 1g. binwalk 文件分离
        out, _, _ = run_cmd(f'binwalk -e --directory="{ws}" "{filepath}" 2>&1', timeout=15)
        if out:
            for line in out.split("\n"):
                flag = a.grep_flag(line)
                if flag:
                    print(f"  binwalk → {flag}")
                    print(f"FLAG: {flag}")
                    return

        # 1h. foremost 文件恢复
        foremost_dir = ws / "foremost"
        out, _, _ = run_cmd(f'foremost -o "{foremost_dir}" "{filepath}" 2>&1', timeout=20)
        if foremost_dir.exists():
            recovered = list(foremost_dir.rglob("*"))
            for rf in recovered:
                if rf.is_file() and rf.stat().st_size > 0:
                    try:
                        fc = rf.read_text(errors="replace")
                        for f in a.grep_all_flags(fc):
                            print(f"  foremost {rf.name} → {f}")
                            print(f"FLAG: {f}")
                            return
                    except: pass

    # ====== Phase 2: 最终兜底 ======
    print(f"\n--- 兜底 ---")
    # 对 workspace 下所有产出的文件做 strings + hex 扫描
    for f in ws.rglob("*"):
        if f.is_file() and f.stat().st_size < 10 * 1024 * 1024:
            try:
                content = f.read_text(errors="replace")
                for fl in a.grep_all_flags(content):
                    print(f"  {f.name} → {fl}")
                    print(f"FLAG: {fl}")
                    return
            except: pass

    print("没搞出来，白给了")


if __name__ == "__main__":
    main()
