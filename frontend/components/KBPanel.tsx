"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export default function KBPanel() {
  const [open, setOpen] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const fetchStats = async () => {
    setLoading(true);
    try { const r = await fetch(`${API}/api/kb/stats`); if (r.ok) setStats(await r.json()); } catch {}
    setLoading(false);
  };

  const handleToggle = () => {
    if (!open && !stats) fetchStats();
    setOpen(!open);
  };

  const labels: Record<string, string> = { crypto: "🔐", web: "🌐", bin: "💻", misc: "🧩", ai: "🤖" };

  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-sm overflow-hidden">
      <button onClick={handleToggle} className="w-full px-5 py-3.5 text-left text-sm font-semibold text-gray-700 hover:bg-gray-50/50 flex items-center justify-between transition">
        <span className="flex items-center gap-2">
          <span className="text-base">🧠</span> Knowledge Base
          {stats && <span className="text-xs bg-purple-50 text-purple-600 px-1.5 py-0.5 rounded-md font-medium">{stats.total} entries</span>}
        </span>
        <span className={`text-xs text-gray-400 transition ${open ? "rotate-180" : ""}`}>▼</span>
      </button>
      {open && (
        <div className="px-5 pb-4 border-t border-gray-50 pt-3 space-y-2">
          {loading ? (
            <p className="text-xs text-gray-400 text-center py-2">loading...</p>
          ) : stats && stats.total > 0 ? (
            <>
              <div className="flex gap-1.5 flex-wrap">
                {Object.entries(stats.by_type as Record<string, number>).map(([t, n]: any) => (
                  <span key={t} className="text-xs bg-gray-50 border border-gray-100 rounded-md px-2 py-0.5 text-gray-600">{labels[t] || "❓"} {t}: {n}</span>
                ))}
              </div>
              {stats.recent?.length > 0 && (
                <div className="space-y-1 max-h-28 overflow-y-auto">
                  {stats.recent.map((r: any) => (
                    <div key={r.id} className="text-xs text-gray-500 bg-gray-50 rounded-md px-2 py-1.5 flex items-center gap-2">
                      <span className="font-mono text-gray-300 w-14 truncate">{r.id}</span>
                      <span className="text-gray-600 truncate flex-1">{r.flag}</span>
                      <span className="text-gray-300">{(r.chain || []).join("→")}</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <p className="text-xs text-gray-400 text-center py-2">no records yet</p>
          )}
        </div>
      )}
    </div>
  );
}
