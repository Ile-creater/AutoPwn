"use client";

import { useState } from "react";

interface KBStats {
  total: number;
  by_type: Record<string, number>;
  recent: { id: string; type: string; chain: string[]; flag: string }[];
}

export default function KBPanel() {
  const [open, setOpen] = useState(false);
  const [stats, setStats] = useState<KBStats | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const r = await fetch("http://localhost:8000/api/kb/stats");
      if (r.ok) setStats(await r.json());
    } catch {}
    setLoading(false);
  };

  const handleToggle = () => {
    if (!open && !stats) fetchStats();
    setOpen(!open);
  };

  const typeLabels: Record<string, string> = {
    crypto: "🔐", web: "🌐", bin: "💻", misc: "🧩", ai: "🤖",
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
      <button
        onClick={handleToggle}
        className="w-full px-4 py-2 text-left text-sm font-bold text-gray-400 hover:text-gray-200 flex items-center justify-between transition"
      >
        <span className="flex items-center gap-2">
          <span className="text-base">🧠</span> 知识库
          {stats && (
            <span className="text-xs bg-purple-900/50 text-purple-300 px-1.5 py-0.5 rounded">
              {stats.total} 条
            </span>
          )}
        </span>
        <span className={`text-xs transition ${open ? "rotate-180" : ""}`}>▼</span>
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-2 border-t border-gray-800 pt-3">
          {loading ? (
            <p className="text-xs text-gray-500 text-center py-2">加载中...</p>
          ) : stats && stats.total > 0 ? (
            <>
              <div className="flex gap-2 flex-wrap">
                {Object.entries(stats.by_type).map(([t, n]) => (
                  <span key={t} className="text-xs bg-gray-800 border border-gray-700 rounded px-2 py-0.5 text-gray-300">
                    {typeLabels[t] || "❓"} {t}: {n}
                  </span>
                ))}
              </div>
              {stats.recent.length > 0 && (
                <div className="space-y-1 mt-1 max-h-28 overflow-y-auto">
                  {stats.recent.map((r) => (
                    <div key={r.id} className="text-xs bg-gray-800/50 rounded px-2 py-1 flex items-center gap-2">
                      <span className="text-gray-500 font-mono w-14 truncate">{r.id}</span>
                      <span className="text-gray-300 truncate flex-1">{r.flag}</span>
                      <span className="text-gray-600">{r.chain?.join("→") || "?"}</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <p className="text-xs text-gray-500 text-center py-2">暂无记录，解出 flag 后自动积累</p>
          )}
        </div>
      )}
    </div>
  );
}
