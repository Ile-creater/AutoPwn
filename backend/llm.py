"""
LLM 适配层 — 统一接口，支持 Ollama / OpenAI / Anthropic / 自定义 API。
环境变量 LLM_PROVIDER 控制，不设自动检测。
"""

import os, json, time

# ==== 全局状态缓存（省掉每个 agent 各 ping 一次的开销）====
_LAST_CHECK = 0
_CHECK_TTL = 30  # 30s 内复用缓存
_CACHED_OK = None
_CACHED_PROVIDER = ""


def _env(name, default=""):
    return os.environ.get(name, default).strip()


def llm_available():
    """查 LLM 是否可用。带 TTL 缓存，避免每个 agent 各 ping 一次。"""
    global _LAST_CHECK, _CACHED_OK, _CACHED_PROVIDER
    now = time.time()
    if now - _LAST_CHECK < _CHECK_TTL:
        return _CACHED_OK

    provider = _detect()
    ok = False
    try:
        import requests as req
        if provider == "ollama":
            r = req.get("http://localhost:11434/api/tags", timeout=3)
            ok = r.status_code == 200
        elif provider == "openai":
            r = req.get(f"{_env('OPENAI_BASE_URL', 'https://api.openai.com/v1')}/models",
                        headers={"Authorization": f"Bearer {_env('OPENAI_API_KEY')}"}, timeout=5)
            ok = r.status_code == 200
        elif provider == "anthropic":
            ok = bool(_env("ANTHROPIC_API_KEY"))
        elif provider == "custom":
            r = req.get(_env("CUSTOM_API_BASE", "http://localhost:8080/v1/models"),
                        headers=_custom_headers(), timeout=5)
            ok = r.status_code == 200
    except:
        ok = False

    _CACHED_OK = ok
    _CACHED_PROVIDER = provider
    _LAST_CHECK = now
    return ok


def llm_provider():
    """返回当前使用的 provider 名。"""
    llm_available()  # refresh cache
    return _CACHED_PROVIDER


def llm_call(prompt, system="", timeout=20, max_tokens=512):
    """统一 LLM 调用入口。一次超时自动重试，两次失败降级。"""
    provider = _detect()

    call = None
    if provider == "ollama":      call = _call_ollama
    elif provider == "openai":    call = _call_openai
    elif provider == "anthropic": call = _call_anthropic
    elif provider == "custom":    call = _call_custom

    if not call:
        return None

    # 第一次尝试
    for attempt in (1, 2):
        try:
            result = call(prompt, system, timeout, max_tokens)
            if result is not None:
                return result
        except:
            pass
        if attempt == 1:
            time.sleep(0.5)  # 短等一下再重试

    return None


# ---- 自动检测 ----

def _detect():
    """按优先级检测可用 provider。"""
    # 显式设置优先
    explicit = _env("LLM_PROVIDER")
    if explicit:
        return explicit

    # 检测 Ollama
    try:
        import requests as req
        r = req.get("http://localhost:11434/api/tags", timeout=2)
        if r.status_code == 200:
            return "ollama"
    except:
        pass

    # 检测 Anthropic
    if _env("ANTHROPIC_API_KEY"):
        return "anthropic"

    # 检测 OpenAI
    if _env("OPENAI_API_KEY"):
        return "openai"

    # 检测自定义
    if _env("CUSTOM_API_BASE"):
        return "custom"

    return "ollama"  # 默认


# ---- 各后端实现 ----

def _call_ollama(prompt, system, timeout, max_tokens):
    try:
        import requests as req
        body = {
            "model": _env("OLLAMA_MODEL", "qwen2.5:3b"),
            "prompt": prompt, "stream": False,
            "options": {"temperature": 0.1, "num_predict": max_tokens},
        }
        if system:
            body["system"] = system
        r = req.post("http://localhost:11434/api/generate", json=body, timeout=timeout)
        if r.status_code == 200:
            return r.json().get("response", "").strip()
        return None
    except:
        return None


def _call_openai(prompt, system, timeout, max_tokens):
    try:
        import requests as req
        base = _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = _env("OPENAI_API_KEY", "sk-no-key")
        model = _env("OPENAI_MODEL", "gpt-4o-mini")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        r = req.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.1},
            timeout=timeout,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        return None
    except:
        return None


def _call_anthropic(prompt, system, timeout, max_tokens):
    try:
        import requests as req
        api_key = _env("ANTHROPIC_API_KEY")
        model = _env("ANTHROPIC_MODEL", "claude-opus-4-8")

        body = {
            "model": model, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = [{"type": "text", "text": system}]

        r = req.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json=body, timeout=timeout,
        )
        if r.status_code == 200:
            data = r.json()
            for b in data.get("content", []):
                if b.get("type") == "text":
                    return b["text"].strip()
        return None
    except:
        return None


def _custom_headers():
    h = {"Content-Type": "application/json"}
    key = _env("CUSTOM_API_KEY")
    if key:
        h["Authorization"] = f"Bearer {key}"
    for pair in _env("CUSTOM_API_HEADERS", "").split(","):
        pair = pair.strip()
        if ":" in pair:
            k, v = pair.split(":", 1)
            h[k.strip()] = v.strip()
    return h


def _call_custom(prompt, system, timeout, max_tokens):
    """通用 OpenAI 兼容 API（vLLM / LM Studio / text-generation-webui / DeepSeek 等）"""
    try:
        import requests as req
        base = _env("CUSTOM_API_BASE", "http://localhost:8080/v1")
        model = _env("CUSTOM_MODEL", "default")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        r = req.post(
            f"{base}/chat/completions",
            headers=_custom_headers(),
            json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.1},
            timeout=timeout,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        return None
    except:
        return None
