"""
Base Agent — shared utilities for all agent types.
"""

import os
import base64
import re
from pathlib import Path


class BaseAgent:
    """Provides common decoding / detection utilities for CTF agents."""

    def __init__(self, workspace: str):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

    def read_challenge(self) -> str:
        """Read the challenge description file."""
        challenge_file = os.environ.get("CHALLENGE_FILE", "")
        if challenge_file:
            return Path(challenge_file).read_text(encoding="utf-8", errors="replace")
        return ""

    def detect_encoding(self, text: str) -> list[str]:
        """Try to detect common encoding types in the given text.
        Returns a list of encoding names in the order they should be tried.
        """
        text = text.strip()
        candidates = []

        # Base64: only A-Za-z0-9+/=, length multiple of 4
        if re.match(r"^[A-Za-z0-9+/=]+$", text) and len(text) % 4 == 0:
            candidates.append("base64")

        # Hex: only 0-9a-fA-F, even length
        if re.match(r"^[0-9a-fA-F]+$", text) and len(text) % 2 == 0:
            candidates.append("hex")

        # Base32: A-Z2-7 and =
        if re.match(r"^[A-Z2-7=]+$", text) and len(text) % 8 == 0:
            candidates.append("base32")

        # Base85: contains ~, {, }, etc.
        if re.match(r"^[A-Za-z0-9!#$%&()*+,\-./:;<=>?@[\]^_`{|}~]+$", text):
            candidates.append("base85")

        # Reverse string
        candidates.append("reverse")

        # ROT13 / Caesar
        if re.match(r"^[a-zA-Z\s{}_\-]+$", text):
            candidates.append("rot13")

        return candidates

    def try_decode(self, text: str, encoding: str) -> str | None:
        """Try to decode text with a specific encoding. Returns decoded text or None."""
        text = text.strip()
        try:
            if encoding == "base64":
                decoded = base64.b64decode(text)
                return decoded.decode("utf-8", errors="replace")

            elif encoding == "hex":
                decoded = bytes.fromhex(text)
                return decoded.decode("utf-8", errors="replace")

            elif encoding == "base32":
                decoded = base64.b32decode(text)
                return decoded.decode("utf-8", errors="replace")

            elif encoding == "base85":
                decoded = base64.a85decode(text)
                return decoded.decode("utf-8", errors="replace")

            elif encoding == "reverse":
                return text[::-1]

            elif encoding == "rot13":
                result = []
                for ch in text:
                    if "a" <= ch <= "z":
                        result.append(chr((ord(ch) - ord("a") + 13) % 26 + ord("a")))
                    elif "A" <= ch <= "Z":
                        result.append(chr((ord(ch) - ord("A") + 13) % 26 + ord("A")))
                    else:
                        result.append(ch)
                return "".join(result)

        except Exception:
            return None

        return None

    def extract_flag(self, text: str) -> str | None:
        """Try to extract a flag pattern from text."""
        patterns = [
            r"flag\{[^}]+\}",
            r"FLAG\{[^}]+\}",
            r"ctf\{[^}]+\}",
            r"CTF\{[^}]+\}",
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                return m.group(0)
        return None
