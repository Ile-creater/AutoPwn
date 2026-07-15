import os, base64, re
from pathlib import Path


class BaseAgent:
    def __init__(self, workspace="."):
        self.ws = Path(workspace)
        self.ws.mkdir(parents=True, exist_ok=True)

    def read_chal(self):
        f = os.environ.get("CHALLENGE_FILE", "")
        return Path(f).read_text(encoding="utf-8", errors="replace") if f else ""

    def fetch(self, url, timeout=10):
        """HTTP GET，返回 (status, headers_dict, body_text)。挂了返回 None"""
        try:
            import requests
            r = requests.get(url, timeout=timeout, allow_redirects=True, headers={
                "User-Agent": "AutoPwn/0.1"
            })
            return r.status_code, dict(r.headers), r.text
        except Exception as e:
            return None, None, str(e)

    def sniff(self, s):
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
        """捞所有 flag，不重复"""
        found = set()
        for pat in (r"flag\{[^}]+\}", r"FLAG\{[^}]+\}", r"ctf\{[^}]+\}", r"CTF\{[^}]+\}"):
            for m in re.finditer(pat, s):
                found.add(m.group(0))
        return list(found)
