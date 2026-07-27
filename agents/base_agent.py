import os, base64, re, json
from pathlib import Path

# --- SWE-agent 风格：工具注册表 ---
TOOL_REGISTRY: dict[str, dict] = {}

def register_tool(name, desc, category, run_fn):
    TOOL_REGISTRY[name] = {"desc": desc, "category": category, "run": run_fn}
    return run_fn


class BaseAgent:
    def __init__(self, workspace="."):
        self.ws = Path(workspace)
        self.ws.mkdir(parents=True, exist_ok=True)
        self.phase = "init"
        self.history: list[str] = []
        self._kb_hits: list[dict] = []

    @staticmethod
    def llm_ok():
        """LLM 是否可用。缓存 30s，省掉每个 agent 各 ping 一次。"""
        try:
            from backend.llm import llm_available
            return llm_available()
        except:
            return False

    def read_chal(self):
        f = os.environ.get("CHALLENGE_FILE", "")
        return Path(f).read_text(encoding="utf-8", errors="replace") if f else ""

    def fetch(self, url, timeout=10):
        try:
            import requests
            r = requests.get(url, timeout=timeout, allow_redirects=True,
                             headers={"User-Agent": "AutoPwn/0.3"})
            return r.status_code, dict(r.headers), r.text
        except Exception as e:
            return None, None, str(e)

    # ====== 知识库查询 ======

    def kb_lookup(self, chal_id=""):
        try:
            from backend.knowledge import kb_lookup as _lookup
            cid = chal_id or os.environ.get("CHALLENGE_ID", "")
            chal = {"folder": str(Path(os.environ.get("CHALLENGE_FILE", "")).parent)}
            agent_type = os.environ.get("AGENT_TYPE", "crypto")
            hits = _lookup(chal, agent_type)
            self._kb_hits = hits
            return hits
        except:
            return []

    # ====== 统一 LLM 调用 ======

    def _llm(self, prompt, system="", timeout=15):
        """调 LLM。自动检测 provider，支持 Ollama/OpenAI/Anthropic/自定义。"""
        try:
            from backend.llm import llm_call, llm_available
            if not llm_available():
                return None
            return llm_call(prompt, system=system, timeout=timeout)
        except:
            return None

    # ====== SWE-agent 风格：长输出摘要 ======

    def _summarize(self, text, max_chars=2000):
        if len(text) <= max_chars:
            return text
        head = int(max_chars * 0.6)
        tail = int(max_chars * 0.3)
        return (text[:head] + f"\n\n... [省略 {len(text) - head - tail} 字符] ...\n\n" + text[-tail:])

    # ====== AI 推理循环（真正解题的东西）======

    def ai_solve(self, challenge_text, agent_type="general", tools_info=""):
        """让 LLM 接管解题。返回 (flag, reasoning_log)。
        这个方法才是 AutoPwn 的核心——前面的正则匹配只是快捷路径，
        LLM 推理能覆盖正则完全看不懂的题目。"""
        from backend.llm import llm_call, llm_provider, llm_available

        if not llm_available():
            return None, "LLM offline"

        provider = llm_provider()

        context = f"""You are solving a CTF challenge.

Type: {agent_type}
Challenge content:
{challenge_text[:3000]}

{tools_info}

Think step by step. What is the likely vulnerability or encoding? What tools should you use?
Provide a concrete step-by-step plan to find the flag.

最后一行必须是: FLAG: <flag> (如果找到了) 或者 NEXT: <下一步应该尝试什么>"""

        for turn in range(5):
            system = "你是 CTF 解题专家。先分析题目，再制定攻击方案，最后执行。短而精准。"
            if provider == "anthropic":
                system = "You are an expert CTF solver. Analyze the challenge, plan the attack, execute. Be concise and specific."

            resp = llm_call(context, system=system, timeout=60, max_tokens=1024)
            if not resp:
                return None, f"LLM no response (turn {turn})"

            print(f"  [{turn+1}/5] AI: {resp[:300]}...")

            # 检测 flag
            flag = self.grep_flag(resp)
            if flag:
                return flag, resp

            # 检测下一步指令
            if "NEXT:" in resp:
                next_step = resp.split("NEXT:")[-1].strip()[:500]
                context += f"\n\nYour plan: {resp}\n\nExecute this step: {next_step}\nWhat did you find? What now?"
                continue

            # 检测 CODE: 代码块（让 LLM 直接写 Python 执行）
            import re
            code_match = re.search(r"```(?:python)?\n(.*?)```", resp, re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
                print(f"  [执行代码] {code[:100]}...")
                try:
                    exec_globals = {"__builtins__": __builtins__, "base64": __import__("base64"),
                                    "re": __import__("re"), "requests": __import__("requests"),
                                    "os": __import__("os"), "json": __import__("json")}
                    import io, sys
                    old_stdout = sys.stdout
                    sys.stdout = buf = io.StringIO()
                    exec(code, exec_globals)
                    sys.stdout = old_stdout
                    exec_output = buf.getvalue().strip() or "(无输出)"
                    flag = self.grep_flag(exec_output)
                    if flag:
                        return flag, code
                except Exception as e:
                    exec_output = f"ERROR: {e}"
                context += f"\n\nCode executed. Output:\n{exec_output}\n\nAnalyze the output. What next?"
                continue

            # 兜底：让 LLM 继续
            context += f"\n\nYour response: {resp}\n\nContinue analyzing. What did you find? What should we try next?"

        return None, context[-2000:]

    # ====== ctfSolver 风格：多阶段管道 ======

    def run_pipeline(self, phases: list[dict]):
        for p in phases:
            name = p.get("name", "?")
            fn = p.get("fn")
            self.phase = name
            try:
                result = fn()
                self.history.append(f"[{name}] {result[:200] if result else 'done'}")
                print(f"  [{name}] ok")
                if result and "FLAG:" in str(result):
                    return {"phase": name, "ok": True, "output": str(result), "flag": True}
            except Exception as e:
                self.history.append(f"[{name}] FAIL: {e}")
                print(f"  [{name}] 挂了: {e}")
                return {"phase": name, "ok": False, "output": str(e), "flag": False}
        return {"phase": "done", "ok": True, "output": "all phases complete", "flag": False}

    # ====== HexStrike 风格：工具自动发现 ======

    def list_tools(self, category=None):
        if category:
            return [(n, d) for n, d in TOOL_REGISTRY.items() if d["category"] == category]
        return list(TOOL_REGISTRY.items())

    def use_tool(self, name, *args, **kwargs):
        t = TOOL_REGISTRY.get(name)
        if t:
            return t["run"](*args, **kwargs)
        return None

    # ====== AI 推理层 ======

    def ai_think(self, context, agent_type="general"):
        tools = self.list_tools()
        tool_list = "\n".join(f"  - {n}: {d['desc']}" for n, d in tools[:15])
        return self._llm(
            f"CTF {agent_type} challenge.\nAvailable tools:\n{tool_list}\n\n"
            f"Current state:\n{self._summarize(context)}\n\n"
            f"Think step by step. Choose ONE action:\n"
            f"1. What tool to call (or 'none')\n2. What you expect to find\n"
            f"3. If found something interesting, what next?\n\nReply in 2-4 short lines.",
            system="You are a CTF solver agent. Think like a security researcher.", timeout=20,
        )

    def ai_sniff(self, s):
        llm_out = self._llm(
            f"Analyze this text, what encoding? Consider: base64, hex, base32, base85, "
            f"rot13, reverse, base58, base62, uuencode, quoted-printable, url-encode, "
            f"morse, binary, ascii85, z85.\n\nText:\n{s[:800]}\n\n"
            f"Return JSON array: [{{\"method\":\"...\",\"confidence\":0.0-1.0}}, ...]. Only JSON.",
            system="Cryptography expert. Reply with JSON arrays only.", timeout=20,
        )
        if llm_out:
            try:
                parsed = json.loads(llm_out)
                if isinstance(parsed, list):
                    return [(p.get("method", "base64"), p.get("confidence", 0.5)) for p in parsed[:8]]
            except: pass
        return [(e, 0.7) for e in self._fallback_sniff(s)]

    def _fallback_sniff(self, s):
        s = s.strip()
        out = []
        if re.match(r"^[A-Za-z0-9+/=]+$", s) and len(s) % 4 == 0: out.append("base64")
        if re.match(r"^[0-9a-fA-F]+$", s) and len(s) % 2 == 0: out.append("hex")
        if re.match(r"^[A-Z2-7=]+$", s) and len(s) % 8 == 0: out.append("base32")
        if re.match(r"^[A-Za-z0-9!#$%&()*+,\-./:;<=>?@[\]^_`{|}~]+$", s): out.append("base85")
        out.append("reverse")
        if re.match(r"^[a-zA-Z\s{}_\-]+$", s): out.append("rot13")
        return out

    def sniff(self, s):
        return [m for m, _ in self.ai_sniff(s)]

    def ai_plan_web(self, url, status_code, html_preview, hints=""):
        llm_out = self._llm(
            f"Web challenge. URL={url}, HTTP={status_code}, hints={hints}\n"
            f"HTML ({len(html_preview)}B):\n{self._summarize(html_preview, 1200)}\n\n"
            f"Vulnerability type? Choose: SQLi, XSS, SSTI, LFI, command-injection, "
            f"IDOR, file-upload, SSRF, XXE, or 'scan more'.\n"
            f"Reply: VULN_TYPE: <type> REASON: <short reason>.",
            system="Web security expert. Be concise.", timeout=20,
        )
        return llm_out or "VULN_TYPE: scan more REASON: (offline)"

    def ai_analyze_binary(self, strings_sample, file_info):
        return self._llm(
            f"Binary analysis. File: {file_info}\n"
            f"Strings (first 1500 chars):\n{self._summarize(strings_sample, 1500)}\n\n"
            f"Look for: passwords, keys, URLs, flag patterns, suspicious functions. 1-3 bullet points.",
            system="Reverse engineering expert. Be concise.", timeout=20,
        )

    def ai_plan_attack(self, agent_type, context):
        return self._llm(
            f"CTF {agent_type}. Context:\n{self._summarize(context, 1500)}\n\n"
            f"Next 1-3 steps? Each on its own line, start with '- '.",
            system="CTF solver. Practical, specific, short.", timeout=20,
        )

    # ====== 解码 ======

    def decode(self, s, method):
        s = s.strip()
        try:
            if method == "base64": return base64.b64decode(s).decode("utf-8", errors="replace")
            if method == "base32": return base64.b32decode(s).decode("utf-8", errors="replace")
            if method == "base85": return base64.a85decode(s).decode("utf-8", errors="replace")
            if method == "hex": return bytes.fromhex(s).decode("utf-8", errors="replace")
            if method == "reverse": return s[::-1]
            if method == "rot13":
                r = []
                for ch in s:
                    if 'a' <= ch <= 'z': r.append(chr((ord(ch) - 97 + 13) % 26 + 97))
                    elif 'A' <= ch <= 'Z': r.append(chr((ord(ch) - 65 + 13) % 26 + 65))
                    else: r.append(ch)
                return "".join(r)
            if method == "morse":
                morse = {"·-": "A","-···": "B","-·-·": "C","-··": "D","·": "E",
                         "··-·": "F","--·": "G","····": "H","··": "I","·---": "J",
                         "-·-": "K","·-··": "L","--": "M","-·": "N","---": "O",
                         "·--·": "P","--·-": "Q","·-·": "R","···": "S","-": "T",
                         "··-": "U","···-": "V","·--": "W","-··-": "X","-·--": "Y",
                         "--··": "Z","-----": "0","·----": "1","··---": "2","···--": "3",
                         "····-": "4","·····": "5","-····": "6","--···": "7","---··": "8",
                         "----·": "9","/": " "}
                words = s.strip().split("  ")
                return " ".join("".join(morse.get(c, c) for c in w.split()) for w in words)
        except: pass
        return None

    def grep_flag(self, s):
        for pat in (r"flag\{[^}]+\}", r"FLAG\{[^}]+\}", r"ctf\{[^}]+\}", r"CTF\{[^}]+\}"):
            m = re.search(pat, s)
            if m: return m.group(0)
        return None

    def grep_all_flags(self, s):
        found = set()
        for pat in (r"flag\{[^}]+\}", r"FLAG\{[^}]+\}", r"ctf\{[^}]+\}", r"CTF\{[^}]+\}"):
            for m in re.finditer(pat, s):
                found.add(m.group(0))
        return list(found)
