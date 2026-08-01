"use client";

import { useState, useEffect } from "react";

interface ProviderInfo {
  name: string;
  models: string[];
}

interface LLMConfig {
  provider: string;
  model: string;
  available: boolean;
  providers: Record<string, ProviderInfo>;
}

export default function ModelPicker() {
  const api = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  const [cfg, setCfg] = useState<LLMConfig | null>(null);
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [msg, setMsg] = useState("");

  const load = async () => {
    try {
      const r = await fetch(`${api}/api/llm/status`);
      if (r.ok) {
        const d = await r.json();
        setCfg(d);
        setModel(d.model || "");
      }
    } catch {}
  };

  useEffect(() => { load(); }, []);

  const changeProvider = async (p: string) => {
    if (!cfg) return;
    setMsg("");
    try {
      const firstModel = cfg.providers[p]?.models?.[0] || "";
      const r = await fetch(`${api}/api/llm/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider: p, model: firstModel, api_key: apiKey }),
      });
      if (r.ok) {
        const d = await r.json();
        setCfg(d);
        setModel(d.model || "");
        setMsg("已切换");
        setTimeout(() => setMsg(""), 2000);
      }
    } catch { setMsg("后端没连上"); }
  };

  const changeModel = async (m: string) => {
    if (!cfg) return;
    setModel(m);
    setMsg("");
    try {
      const r = await fetch(`${api}/api/llm/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider: cfg.provider, model: m, api_key: apiKey }),
      });
      if (r.ok) {
        const d = await r.json();
        setCfg(d);
      }
    } catch {}
  };

  if (!cfg) return null;

  const providerLabel = cfg.providers[cfg.provider]?.name || cfg.provider;
  const models = cfg.providers[cfg.provider]?.models || [];

  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs text-gray-600">🧠</span>

      {/* Provider dropdown */}
      <select
        value={cfg.provider}
        onChange={(e) => changeProvider(e.target.value)}
        className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-200"
      >
        {Object.entries(cfg.providers).map(([k, v]) => (
          <option key={k} value={k}>{v.name}</option>
        ))}
      </select>

      {/* Model dropdown */}
      {models.length > 0 && (
        <select
          value={model}
          onChange={(e) => changeModel(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-200 max-w-[120px]"
        >
          {models.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      )}

      {/* Custom model input (for providers without preset models like custom) */}
      {models.length === 0 && (
        <input
          value={model}
          onChange={(e) => setModel(e.target.value)}
          onBlur={() => model && changeModel(model)}
          onKeyDown={(e) => { if (e.key === "Enter" && model) changeModel(model); }}
          className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-200 w-28"
          placeholder="模型名"
        />
      )}

      {/* API key toggle */}
      <button
        onClick={() => setShowKey(!showKey)}
        className="text-xs text-gray-600 hover:text-gray-400 transition"
        title="设置 API Key"
      >🔑</button>

      {showKey && (
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="API Key..."
          className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-200 w-24"
        />
      )}

      {/* Status dot */}
      <span className={`inline-block w-1.5 h-1.5 rounded-full ${cfg.available ? "bg-green-400" : "bg-red-500"}`} title={cfg.available ? "connected" : "disconnected"} />

      {msg && <span className="text-xs text-green-400">{msg}</span>}
    </div>
  );
}
