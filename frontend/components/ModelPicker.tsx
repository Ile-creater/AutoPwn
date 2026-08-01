"use client";

import { useState, useEffect } from "react";

export default function ModelPicker() {
  const api = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
  const [cfg, setCfg] = useState<any>(null);
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [msg, setMsg] = useState("");

  const load = async () => {
    try { const r = await fetch(`${api}/api/llm/status`); if (r.ok) { const d = await r.json(); setCfg(d); setModel(d.model || ""); } } catch {}
  };
  useEffect(() => { load(); }, []);

  const switchProvider = async (p: string) => {
    setMsg("");
    const firstModel = cfg?.providers?.[p]?.models?.[0] || "";
    const r = await fetch(`${api}/api/llm/config`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ provider: p, model: firstModel, api_key: apiKey }) });
    if (r.ok) { const d = await r.json(); setCfg(d); setModel(d.model || ""); setMsg("✓"); setTimeout(() => setMsg(""), 2000); }
  };

  const switchModel = async (m: string) => {
    setModel(m);
    await fetch(`${api}/api/llm/config`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ provider: cfg.provider, model: m, api_key: apiKey }) });
  };

  if (!cfg) return null;

  const models = cfg.providers?.[cfg.provider]?.models || [];

  return (
    <div className="flex items-center gap-1.5 text-xs">
      <select value={cfg.provider} onChange={(e) => switchProvider(e.target.value)}
        className="bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1.5 text-gray-600 font-medium focus:outline-none focus:border-gray-300 transition">
        {Object.entries<any>(cfg.providers).map(([k, v]) => (<option key={k} value={k}>{v.name}</option>))}
      </select>

      {models.length > 0 ? (
        <select value={model} onChange={(e) => switchModel(e.target.value)}
          className="bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1.5 text-gray-600 max-w-[110px] focus:outline-none focus:border-gray-300 transition">
          {models.map((m: string) => (<option key={m} value={m}>{m}</option>))}
        </select>
      ) : (
        <input value={model} onChange={(e) => setModel(e.target.value)} onBlur={() => model && switchModel(model)}
          className="bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1.5 text-gray-600 w-24 focus:outline-none focus:border-gray-300 transition" placeholder="model" />
      )}

      <button onClick={() => setShowKey(!showKey)} className="text-gray-400 hover:text-gray-600 transition" title="API Key">🔑</button>
      {showKey && <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
        className="bg-gray-50 border border-gray-200 rounded-lg px-2.5 py-1.5 text-gray-600 w-20 focus:outline-none" placeholder="key" />}

      <span className={`inline-block w-1.5 h-1.5 rounded-full ${cfg.available ? "bg-emerald-500" : "bg-red-400"}`} />
      {msg && <span className="text-emerald-600 text-xs">{msg}</span>}
    </div>
  );
}
