"""
LLM 适配层 — 统一接口，支持 DeepSeek / Qwen / Claude / OpenAI / Ollama。
运行时可通过 API 切换 provider + model，前端有下拉框选择。
"""

import os, json, time

# ==== 预置提供商列表（前端选项）====
PROVIDERS = {
    "ollama": {
        "name": "Ollama (本地)",
        "models": ["qwen2.5:3b", "qwen2.5:7b", "qwen2.5:14b", "deepseek-r1:8b", "llama3.1:8b", "codellama:7b"],
        "base_url": "http://localhost:11434/api/generate",
        "api_style": "ollama",
    },
    "deepseek": {
        "name": "DeepSeek",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "base_url": "https://api.deepseek.com/v1/chat/completions",
        "api_style": "openai",
    },
    "qwen": {
        "name": "通义千问 (阿里云)",
        "models": ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-max-longcontext"],
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "api_style": "openai",
    },
    "claude": {
        "name": "Claude (Anthropic)",
        "models": ["claude-opus-4-8", "claude-sonnet-5", "claude-haiku-4-5"],
        "base_url": "https://api.anthropic.com/v1/messages",
        "api_style": "anthropic",
    },
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4o", "gpt-4o-mini", "o3-mini"],
        "base_url": "https://api.openai.com/v1/chat/completions",
        "api_style": "openai",
    },
    "custom": {
        "name": "自定义 (OpenAI 兼容)",
        "models": [],
        "base_url": "",
        "api_style": "openai",
    },
}

# ==== 运行时配置（API 可改，前端控制）====
_config: dict = {
    "provider": "",       # 空=自动检测, 或 "ollama/deepseek/qwen/claude/openai/custom"
    "model": "",          # 空=用默认, 或具体模型名
    "api_key": "",        # 空=读环境变量
    "base_url": "",       # 空=用预置
    "extra_headers": {},  # 额外 HTTP 头
}
_loaded_file = False

# ==== 缓存 ====
_LAST_CHECK = 0
_CHECK_TTL = 30
_CACHED_OK = None
_CACHED_PROVIDER = ""


def _env(name, default=""):
    return os.environ.get(name, default).strip()


def _load_config_file():
    """从 .env 文件读敏感 key，避免硬编码"""
    global _loaded_file
    if _loaded_file:
        return
    _loaded_file = True
    env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.exists(env_file):
        return
    for line in open(env_file, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip("\"'")
        if k not in os.environ:
            os.environ[k] = v


def get_config():
    """返回当前配置（前端用）"""
    return {
        "provider": _config.get("provider") or _detect(),
        "model": _config.get("model") or _default_model(_config.get("provider") or _detect()),
        "available": llm_available(),
        "providers": {k: {"name": v["name"], "models": v["models"]} for k, v in PROVIDERS.items()},
    }


def set_config(provider="", model="", api_key="", base_url=""):
    """运行时切换 provider/model（前端调 POST /api/llm/config）"""
    global _config, _CACHED_OK, _CACHED_PROVIDER, _LAST_CHECK
    if provider and provider in PROVIDERS:
        _config["provider"] = provider
        if not base_url:
            base_url = PROVIDERS[provider]["base_url"]
    if model:
        _config["model"] = model
    if api_key:
        _config["api_key"] = api_key
    if base_url:
        _config["base_url"] = base_url
    # 清缓存，强制重检测
    _CACHED_OK = None
    _CACHED_PROVIDER = ""
    _LAST_CHECK = 0
    return get_config()


def llm_available():
    _load_config_file()
    global _LAST_CHECK, _CACHED_OK, _CACHED_PROVIDER
    now = time.time()
    if now - _LAST_CHECK < _CHECK_TTL and _CACHED_OK is not None:
        return _CACHED_OK

    provider = _resolve_provider()
    ok = False
    try:
        import requests as req
        key = _resolve_key(provider)
        if provider == "ollama":
            r = req.get("http://localhost:11434/api/tags", timeout=3)
            ok = r.status_code == 200
        elif provider in ("deepseek", "qwen"):
            ok = bool(key)
        elif provider == "claude":
            ok = bool(key)
        elif provider == "openai":
            ok = bool(key)
        elif provider == "custom":
            ok = bool(_resolve_url(provider))
    except:
        ok = False

    _CACHED_OK = ok
    _CACHED_PROVIDER = provider
    _LAST_CHECK = now
    return ok


def llm_provider():
    llm_available()
    return _CACHED_PROVIDER


def llm_call(prompt, system="", timeout=20, max_tokens=512):
    _load_config_file()
    provider = _resolve_provider()

    if provider == "ollama":
        return _call_ollama(prompt, system, timeout, max_tokens)
    elif provider in ("deepseek", "qwen", "openai"):
        return _call_openai_style(prompt, system, timeout, max_tokens, provider)
    elif provider == "claude":
        return _call_claude(prompt, system, timeout, max_tokens)
    elif provider == "custom":
        return _call_openai_style(prompt, system, timeout, max_tokens, "custom")
    return None


# ---- 内部解析 ----

def _resolve_provider():
    if _config["provider"] and _config["provider"] in PROVIDERS:
        return _config["provider"]
    explicit = _env("LLM_PROVIDER")
    if explicit:
        return explicit
    # 自动检测
    try:
        import requests as req
        r = req.get("http://localhost:11434/api/tags", timeout=2)
        if r.status_code == 200:
            return "ollama"
    except: pass
    if _env("ANTHROPIC_API_KEY"): return "claude"
    if _env("DEEPSEEK_API_KEY"): return "deepseek"
    if _env("DASHSCOPE_API_KEY"): return "qwen"
    if _env("OPENAI_API_KEY"): return "openai"
    return "ollama"


def _resolve_model(provider):
    m = _config.get("model") or _env(f"{provider.upper()}_MODEL") or _env("LLM_MODEL")
    return m or _default_model(provider)


def _default_model(provider):
    defaults = {"ollama": "qwen2.5:3b", "deepseek": "deepseek-chat", "qwen": "qwen-turbo",
                "claude": "claude-opus-4-8", "openai": "gpt-4o-mini", "custom": "default"}
    return defaults.get(provider, "default")


def _resolve_key(provider):
    key_map = {"claude": "ANTHROPIC_API_KEY", "deepseek": "DEEPSEEK_API_KEY",
               "qwen": "DASHSCOPE_API_KEY", "openai": "OPENAI_API_KEY", "custom": "CUSTOM_API_KEY"}
    env_key = key_map.get(provider, "")
    return _config.get("api_key") or _env(env_key)


def _resolve_url(provider):
    return _config.get("base_url") or PROVIDERS.get(provider, {}).get("base_url", "")


# ---- 后端调用 ----

def _call_ollama(prompt, system, timeout, max_tokens):
    try:
        import requests as req
        model = _resolve_model("ollama")
        body = {"model": model, "prompt": prompt, "stream": False,
                "options": {"temperature": 0.1, "num_predict": max_tokens}}
        if system:
            body["system"] = system
        r = req.post("http://localhost:11434/api/generate", json=body, timeout=timeout)
        if r.status_code == 200:
            return r.json().get("response", "").strip()
        return None
    except: return None


def _call_openai_style(prompt, system, timeout, max_tokens, provider):
    try:
        import requests as req
        url = _resolve_url(provider)
        key = _resolve_key(provider)
        model = _resolve_model(provider)

        messages = []
        if system: messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        if provider == "qwen":
            headers["Authorization"] = f"Bearer {key}"

        r = req.post(url, headers=headers,
                     json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.1},
                     timeout=timeout)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        if r.status_code == 401:
            print(f"[LLM] {provider} API key 无效: {r.text[:100]}")
        return None
    except: return None


def _call_claude(prompt, system, timeout, max_tokens):
    try:
        import requests as req
        key = _resolve_key("claude")
        model = _resolve_model("claude")
        body = {"model": model, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]}
        if system:
            body["system"] = [{"type": "text", "text": system}]
        r = req.post("https://api.anthropic.com/v1/messages",
                     headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                              "Content-Type": "application/json"},
                     json=body, timeout=timeout)
        if r.status_code == 200:
            for b in r.json().get("content", []):
                if b.get("type") == "text":
                    return b["text"].strip()
        return None
    except: return None
