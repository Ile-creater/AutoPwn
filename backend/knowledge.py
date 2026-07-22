"""
知识库 — 记录成功的攻击链，下次查询匹配的历史经验。
存在 knowledge/ctf_kb.json，不会被 git 追踪。
"""

import json, time, re
from pathlib import Path
from collections import Counter

KB_FILE = Path(__file__).resolve().parent.parent / "knowledge" / "ctf_kb.json"


def _load():
    if KB_FILE.exists():
        try:
            return json.loads(KB_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return []


def _save(records):
    KB_FILE.parent.mkdir(exist_ok=True)
    KB_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def kb_stats():
    """返回知识库统计：总数、按类型分布、最近几次成功"""
    records = _load()
    types = Counter(r.get("type", "?") for r in records)
    recent = sorted(records, key=lambda r: r.get("ts", 0), reverse=True)[:5]
    return {
        "total": len(records),
        "by_type": dict(types.most_common()),
        "recent": [{"id": r["id"], "type": r["type"], "chain": r.get("chain", []),
                     "flag": r.get("flag", ""), "ts": r.get("ts", 0)} for r in recent],
    }


def kb_record(chal, flag, agent_type, log_lines):
    """记录一次成功解题。返回记录 ID。"""
    records = _load()

    # 提取特征
    features = _extract_features(chal, log_lines)

    # 去重：同样 type + 同样 chain 不要重复存
    chain = features.get("chain", [])
    for r in records:
        if r.get("type") == agent_type and r.get("chain") == chain:
            r["ts"] = int(time.time())
            r["count"] = r.get("count", 1) + 1
            r["flag"] = flag
            _save(records)
            return r.get("id", "")

    record = {
        "id": f"kb-{agent_type}-{len(records)+1:04d}",
        "type": agent_type,
        "title": chal.get("title", ""),
        "flag": flag,
        "features": features,
        "chain": chain,
        "ts": int(time.time()),
        "count": 1,
        "hints": chal.get("hints", "")[:200],
    }
    records.append(record)
    _save(records)
    return record["id"]


def kb_lookup(chal, agent_type):
    """查知识库：给定一个 challenge，返回最匹配的历史记录。"""
    records = _load()
    if not records:
        return []

    # 只看同类型
    same_type = [r for r in records if r.get("type") == agent_type]
    if not same_type:
        return []

    # 特征匹配
    raw = ""
    chal_file = Path(chal.get("folder", "")) / "challenge.txt"
    if chal_file.exists():
        raw = chal_file.read_text(encoding="utf-8", errors="replace")[:2000]

    current_features = _extract_text_features(raw)
    current_set = set(current_features)

    scored = []
    for r in same_type:
        rfeat = r.get("features", {})
        past_set = set(rfeat.get("text_features", []))
        # Jaccard 相似度
        intersection = len(current_set & past_set)
        union = len(current_set | past_set)
        score = intersection / max(union, 1)
        # chain 长度加分（经验丰富的记录更可信）
        chain_bonus = min(len(r.get("chain", [])) * 0.03, 0.15)
        # 使用次数加分
        count_bonus = min(r.get("count", 1) * 0.02, 0.1)
        scored.append((score + chain_bonus + count_bonus, r))

    scored.sort(key=lambda x: -x[0])
    return [s[1] for s in scored[:3] if s[0] > 0.05]


def _extract_features(chal, log_lines):
    """从 challenge 和 agent 输出中提取特征和攻击链。"""
    raw = ""
    chal_file = Path(chal.get("folder", "")) / "challenge.txt"
    if chal_file.exists():
        raw = chal_file.read_text(encoding="utf-8", errors="replace")[:3000]

    text_features = _extract_text_features(raw)

    # 从日志中提取攻击链
    chain = _extract_chain(log_lines)

    return {"text_features": text_features, "chain": chain, "chal_length": len(raw)}


def _extract_text_features(text):
    """抽文本特征：长度区间、字符集、编码标记"""
    features = []
    t = text.strip()
    ln = len(t)

    # 长度区间
    for lo, hi, label in [(0, 50, "short"), (50, 200, "medium"), (200, 1000, "long"), (1000, 99999, "xlong")]:
        if lo <= ln < hi:
            features.append(label)
            break

    # 字符集
    if re.match(r"^[A-Za-z0-9+/=]+$", t):
        features.append("charset_b64")
    if re.match(r"^[0-9a-fA-F\s]+$", t):
        features.append("charset_hex")
    if re.match(r"^[A-Z2-7=]+$", t):
        features.append("charset_b32")
    if re.search(r"[{}]", t):
        features.append("has_braces")
    if re.search(r"flag|FLAG|ctf|CTF", t):
        features.append("contains_flag_word")
    if t.startswith("http"):
        features.append("starts_with_url")
    if len(t) % 4 == 0 and re.match(r"^[A-Za-z0-9+/=]+$", t):
        features.append("exact_b64_len")
    if "==" in t[-4:]:
        features.append("b64_padding")

    return features


def _extract_chain(log_lines):
    """从 agent 日志中提取成功的方法链。"""
    chain = []
    seen = set()
    for line in log_lines:
        line_stripped = line.strip()
        # crypto 方法
        for method in ("base64", "base32", "base85", "hex", "reverse", "rot13", "morse"):
            if method in line_stripped.lower() and "→" in line_stripped:
                key = f"decode_{method}"
                if key not in seen:
                    chain.append(key)
                    seen.add(key)
        # 关键词
        if "sniff" in line_stripped.lower() and "sniff" not in seen:
            chain.append("sniff")
            seen.add("sniff")
        if "strings" in line_stripped.lower() and "strings" not in seen:
            chain.append("strings")
            seen.add("strings")
        if "binwalk" in line_stripped.lower() and "binwalk" not in seen:
            chain.append("binwalk")
            seen.add("binwalk")
        if "checksec" in line_stripped.lower() and "checksec" not in seen:
            chain.append("checksec")
            seen.add("checksec")
        if "rizin" in line_stripped.lower() and "rizin" not in seen:
            chain.append("rizin")
            seen.add("rizin")
        if "fetch" in line_stripped.lower() and "fetch" not in seen:
            chain.append("fetch")
            seen.add("fetch")
    return chain
