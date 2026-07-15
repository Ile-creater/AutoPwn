"""
Web Agent — 处理 Web 类 CTF。
思路：拿到 URL → 踩点 → 挖信息 → 捞 flag
"""

import os, sys, re
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.base_agent import BaseAgent


# 值得扫的常见路径
COMMON_PATHS = [
    "robots.txt", ".git/HEAD", ".env", ".svn/entries",
    "admin/", "backup/", "debug/", "console/", "phpinfo.php",
    "wp-admin/", ".DS_Store", "sitemap.xml",
    "index.php.bak", "index.html~", ".htaccess",
    "source", "flag", "flag.txt", "secret",
]

# 常见 backup 后缀
BACKUP_EXTS = [".bak", ".swp", ".old", ".php~", ".html~", ".txt~", ".orig"]


def try_decode_chunk(a, text):
    """对文本中的 base64/hex 片段逐个尝试解码"""
    hits = []
    # 捞 base64 片段（至少 12 个字符）
    for m in re.finditer(r"[A-Za-z0-9+/=]{12,}", text):
        chunk = m.group().strip()
        r = a.decode(chunk, "base64")
        if r and len(r) > 2:
            f = a.grep_flag(r)
            hits.append(("base64 片段", chunk[:40], r[:100], f))
    # 捞 hex 片段
    for m in re.finditer(r"[0-9a-fA-F]{16,}", text):
        chunk = m.group().strip()
        if len(chunk) % 2 != 0:
            continue
        r = a.decode(chunk, "hex")
        if r and len(r) > 2:
            f = a.grep_flag(r)
            hits.append(("hex 片段", chunk[:40], r[:100], f))
    return hits


def main():
    workspace = os.environ.get("WORKSPACE", ".")
    a = BaseAgent(workspace)

    print(f"WebAgent @ {workspace}")

    raw = a.read_chal()
    if not raw:
        print("空题？challenge.txt 没东西")
        sys.exit(1)

    print(f"题目 {len(raw)} bytes")

    # 第一行如果是 URL 就去抓，否则当 HTML 分析
    lines = raw.strip().split("\n")
    first = lines[0].strip()
    target = None
    body = raw

    if first.startswith("http://") or first.startswith("https://"):
        target = first
        body = "\n".join(lines[1:]) if len(lines) > 1 else ""

    # ====== Phase 1: 如果有 URL，先踩点 ======
    if target:
        print(f"\n--- 踩点: {target} ---")
        code, headers, html = a.fetch(target)

        if code is None:
            print(f"请求失败: {html}")
        else:
            print(f"HTTP {code}, {len(html)} bytes")

            # 1a. 响应头里有没有 flag？
            for k, v in (headers or {}).items():
                f = a.grep_flag(v)
                if f:
                    print(f"响应头 {k}: {v}")
                    print(f"FLAG: {f}")
                    return
                if any(x in k.lower() for x in ("flag", "hint", "debug", "x-")):
                    print(f"  可疑头 {k}: {v}")

            # 1b. body 里直接搜 flag
            for f in a.grep_all_flags(html):
                print(f"页面直接有 flag: {f}")
                print(f"FLAG: {f}")
                return

            # 1c. HTML 注释
            comments = re.findall(r"<!--(.*?)-->", html, re.DOTALL)
            if comments:
                print(f"找到 {len(comments)} 条注释")
                for c in comments:
                    c = c.strip()
                    f = a.grep_flag(c)
                    if f:
                        print(f"注释里有 flag: {f}")
                        print(f"FLAG: {f}")
                        return
                    if len(c) > 10:
                        print(f"  注释: {c[:120]}...")

            # 1d. 注释和页面里的隐藏信息解码
            for c in comments:
                for tag, src, decoded, f in try_decode_chunk(a, c):
                    print(f"  注释→{tag}: {src} → {decoded}")
                    if f:
                        print(f"FLAG: {f}")
                        return

            for tag, src, decoded, f in try_decode_chunk(a, html):
                print(f"  页面→{tag}: {src} → {decoded}")
                if f:
                    print(f"FLAG: {f}")
                    return

            # 1e. hidden input / script 变量
            for m in re.finditer(r'<input[^>]*type=["\']hidden["\'][^>]*value=["\']([^"\']+)["\']', html):
                val = m.group(1)
                f = a.grep_flag(val)
                print(f"  hidden input: {val[:80]}")
                if f:
                    print(f"FLAG: {f}")
                    return

            # 1f. JS 里的可疑字符串
            js_strings = re.findall(r'["\']([^"\']{20,})["\']', html)
            for s in js_strings:
                f = a.grep_flag(s)
                if f:
                    print(f"JS 字符串有 flag: {f}")
                    print(f"FLAG: {f}")
                    return

            # 1g. 扫常见路径
            parsed = urlparse(target)
            base = f"{parsed.scheme}://{parsed.netloc}"
            print(f"\n--- 扫常见路径 (base={base}) ---")
            for path in COMMON_PATHS[:12]:  # 别全扫，太慢
                url = urljoin(base + "/", path)
                try:
                    code2, _, body2 = a.fetch(url, timeout=5)
                    if code2 and code2 < 400:
                        print(f"  {url} → HTTP {code2} ({len(body2 or '')} bytes)")
                        if body2:
                            for f in a.grep_all_flags(body2):
                                print(f"  → flag! {f}")
                                print(f"FLAG: {f}")
                                return
                except:
                    pass

            # 1h. 如果是 HTML 文件，试 backup 后缀
            path_part = parsed.path or "/index.html"
            for ext in BACKUP_EXTS:
                url = base + path_part + ext
                code2, _, body2 = a.fetch(url, timeout=5)
                if code2 and code2 < 400 and body2:
                    print(f"  backup {url} → HTTP {code2} ({len(body2)} bytes)")
                    for f in a.grep_all_flags(body2):
                        print(f"  → flag! {f}")
                        print(f"FLAG: {f}")
                        return

    # ====== Phase 2: 本地 HTML 分析（无 URL 或者 URL 没找到 flag）======
    print(f"\n--- 本地分析 ---")
    html = body or raw

    # 2a. 注释
    comments = re.findall(r"<!--(.*?)-->", html, re.DOTALL)
    for c in comments:
        c = c.strip()
        f = a.grep_flag(c)
        if f:
            print(f"注释里有 flag: {f}")
            print(f"FLAG: {f}")
            return

    # 2b. 编码片段
    for tag, src, decoded, flag in try_decode_chunk(a, html):
        print(f"  {tag}: {src} → {decoded}")
        if flag:
            print(f"FLAG: {flag}")
            return

    # 2c. 直接搜
    for f in a.grep_all_flags(html):
        print(f"直接搜到: {f}")
        print(f"FLAG: {f}")
        return

    # 2d. 对注释里的编码再试一次
    for c in comments:
        for method in ("base64", "hex", "base32", "rot13"):
            r = a.decode(c, method)
            if r:
                f = a.grep_flag(r)
                if f:
                    print(f"  注释 {method} → {r[:80]}")
                    print(f"FLAG: {f}")
                    return

    print("没搞出来，白给了")


if __name__ == "__main__":
    main()
