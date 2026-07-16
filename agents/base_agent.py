import os, base64, re, json
from pathlib import Path


class BaseAgent:
    def __init__(self, workspace="."):
        self.ws = Path(workspace)
        self.ws.mkdir(parents=True, exist_ok=True)
        self._llm_ok = None  # None=没测过, True=通, False=不通

    def read_chal(self):
        f = os.environ.get("CHALLENGE_FILE", "")
        return Path(f).read_text(encoding="utf-8", errors="replace") if f else ""

    def fetch(self, url, timeout=10):
        try:
            import requests
            r = requests.get(url, timeout=timeout, allow_redirects=True,
                             headers={"User-Agent": "AutoPwn/0.2"})
            return r.status_code, dict(r.headers), r.text
        except Exception as e:
            return None, None, str(e)

    # ====== Ollama ======

    def _llm(self, prompt, system="", timeout=15):
        """调用本地 Ollama。不通返回 None，自动回退。"""
        if self._llm_ok is False:
            return None
        try:
            import requests as req
            body = {
                "model": os.environ.get("OLLAMA_MODEL", "qwen2.5:3b"),
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 512},
            }
            if system:
                body["system"] = system
            r = req.post("http://localhost:11434/api/generate", json=body, timeout=timeout)
            if r.status_code == 200:
                self._llm_ok = True
                return r.json().get("response", "").strip()
            self._llm_ok = False
            return None
        except:
            self._llm_ok = False
            return None

    # ====== AI 推理层 (均带硬编码回退) ======

    def ai_sniff(self, s):
        """用 LLM 推理编码类型，不通则降级为正则。返回 [(method, confidence), ...]"""
        llm_out = self._llm(
            f"You are a CTF solver. Analyze this text and determine what encoding(s) it might be."
            f"Consider: base64, hex, base32, base85, rot13, reverse, base58, base62, uuencode,"
            f"quoted-printable, url-encode, morse, binary, ascii85, z85.\n\n"
            f"Text to analyze:\n{s[:800]}\n\n"
            f"Respond with a JSON array: [{{\"method\": \"...\", \"confidence\": 0.0-1.0}}, ...]. "
            f"Reply with ONLY the JSON array, no other text.",
            system="You are a cryptography expert. Only reply with JSON arrays.",
            timeout=20,
        )

        if llm_out:
            try:
                parsed = json.loads(llm_out)
                # 格式处理
                if isinstance(parsed, list):
                    return [(p.get("method", "base64"), p.get("confidence", 0.5)) for p in parsed[:8]]
            except:
                pass

        # fallback: 现有硬编码
        return [(e, 0.7) for e in self._fallback_sniff(s)]

    def _fallback_sniff(self, s):
        s = s.strip()
        out = []
        if re.match(r"^[A-Za-z0-9+/=]+$", s) and len(s) % 4 == 0:
            out.append("base64")
        if re.match(r"^[0-9a-fA-F]+$", s) and len(s) % 2 == 0:
            out.append("hex")
        if re.match(r"^[A-Z2-7=]+$", s) and len(s) % 8 == 0:
            out.append("base32")
        if re.match(r"^[A-Za-z0-9!#$%&()*+,\-./:;<=>?@[\]^_`{|}~]+$", s):
            out.append("base85")
        out.append("reverse")
        if re.match(r"^[a-zA-Z\s{}_\-]+$", s):
            out.append("rot13")
        return out

    def sniff(self, s):
        """兼容旧调用：ai_sniff 的结果去 confidence 保留顺序"""
        return [m for m, _ in self.ai_sniff(s)]

    def ai_plan_web(self, url, status_code, html_preview, hints=""):
        """让 LLM 根据页面内容建议下一步攻击方向。返回字符串建议。"""
        llm_out = self._llm(
            f"CTF Web challenge. URL: {url}\nHTTP status: {status_code}\n"
            f"Hints: {hints}\n\n"
            f"HTML preview (first 1200 chars):\n{html_preview[:1200]}\n\n"
            f"Analyze what you see. What web vulnerability is likely present? "
            f"Choose from: SQL injection, XSS, SSTI, LFI/path traversal, "
            f"command injection, IDOR, file upload, SSRF, XXE, or 'scan more'.\n"
            f"Respond with ONLY one line: VULN_TYPE: <type> REASON: <short reason>.",
            system="You are a web security expert. Be concise.",
            timeout=20,
        )
        if llm_out:
            return llm_out
        return f"VULN_TYPE: scan more REASON: (LLM offline, scanning all)"

    def ai_analyze_binary(self, strings_sample, file_info):
        """让 LLM 看 strings 输出，发现可疑线索。"""
        llm_out = self._llm(
            f"Binary analysis.\nFile info: {file_info}\n\n"
            f"Interesting strings found (first 1500 chars):\n{strings_sample[:1500]}\n\n"
            f"Look for: passwords, keys, URLs, flag patterns, suspicious function names, "
            f"encoded strings. What stands out? Respond with 1-3 bullet points.",
            system="You are a reverse engineering expert. Be concise.",
            timeout=20,
        )
        if llm_out:
            return llm_out
        return None

    def ai_plan_attack(self, agent_type, context):
        """通用攻击规划：给一段描述，让 LLM 建议下几步。"""
        llm_out = self._llm(
            f"CTF challenge type: {agent_type}\n"
            f"Context:\n{context[:1500]}\n\n"
            f"What should we try next? Suggest 1-3 concrete actions. Each on one line, "
            f"starting with '- '.",
            system="You are a CTF competition solver. Be practical and specific. Short answers only.",
            timeout=20,
        )
        if llm_out:
            return llm_out
        return None

    # ====== 解码 ======

    def decode(self, s, method):
        s = s.strip()
        try:
            if method == "base64":
                return base64.b64decode(s).decode("utf-8", errors="replace")
            if method == "base32":
                return base64.b32decode(s).decode("utf-8", errors="replace")
            if method == "base85":
                return base64.a85decode(s).decode("utf-8", errors="replace")
            if method == "hex":
                return bytes.fromhex(s).decode("utf-8", errors="replace")
            if method == "reverse":
                return s[::-1]
            if method == "rot13":
                r = []
                for ch in s:
                    if 'a' <= ch <= 'z':
                        r.append(chr((ord(ch) - 97 + 13) % 26 + 97))
                    elif 'A' <= ch <= 'Z':
                        r.append(chr((ord(ch) - 65 + 13) % 26 + 65))
                    else:
                        r.append(ch)
                return "".join(r)
            if method == "morse":
                # 简单莫尔斯码
                morse = {"·-": "A", "-···": "B", "-·-·": "C", "-··": "D", "·": "E",
                         "··-·": "F", "--·": "G", "····": "H", "··": "I", "·---": "J",
                         "-·-": "K", "·-··": "L", "--": "M", "-·": "N", "---": "O",
                         "·--·": "P", "--·-": "Q", "·-·": "R", "···": "S", "-": "T",
                         "··-": "U", "···-": "V", "·--": "W", "-··-": "X", "-·--": "Y",
                         "--··": "Z", "-----": "0", "·----": "1", "··---": "2", "···--": "3",
                         "····-": "4", "·····": "5", "-····": "6", "--···": "7", "---··": "8",
                         "----·": "9", "/": " "}
                words = s.strip().split("  ")
                return " ".join(
                    "".join(morse.get(c, c) for c in w.split())
                    for w in words
                )
        except:
            pass
        return None

    def grep_flag(self, s):
        for pat in (r"flag\{[^}]+\}", r"FLAG\{[^}]+\}", r"ctf\{[^}]+\}", r"CTF\{[^}]+\}"):
            m = re.search(pat, s)
            if m:
                return m.group(0)
        return None

    def grep_all_flags(self, s):
        found = set()
        for pat in (r"flag\{[^}]+\}", r"FLAG\{[^}]+\}", r"ctf\{[^}]+\}", r"CTF\{[^}]+\}"):
            for m in re.finditer(pat, s):
                found.add(m.group(0))
        return list(found)
