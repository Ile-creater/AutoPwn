"use client";

import { useState } from "react";

interface Chal {
  type: string;
  status: string;
  difficulty: number;
}

const typeEmoji: Record<string, string> = {
  crypto: "🔐", web: "🌐", bin: "💻", misc: "🧩", pwn: "💥", ai: "🤖",
};
const typeColor: Record<string, string> = {
  crypto: "#10b981", web: "#3b82f6", bin: "#8b5cf6", misc: "#f59e0b", pwn: "#ef4444", ai: "#ec4899",
};

export default function StatsPanel({ chals }: { chals: Chal[] }) {
  const [open, setOpen] = useState(false);

  if (chals.length === 0) return null;

  const solved = chals.filter(c => c.status === "solved").length;
  const failed = chals.filter(c => c.status === "failed").length;
  const running = chals.filter(c => c.status === "running").length;
  const pending = chals.length - solved - failed - running;

  // By type
  const byType: Record<string, { total: number; solved: number }> = {};
  for (const c of chals) {
    if (!byType[c.type]) byType[c.type] = { total: 0, solved: 0 };
    byType[c.type].total++;
    if (c.status === "solved") byType[c.type].solved++;
  }

  const maxTypeCount = Math.max(1, ...Object.values(byType).map(v => v.total));

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-4 py-2 text-left text-sm font-bold text-gray-400 hover:text-gray-200 flex items-center justify-between transition"
      >
        <span className="flex items-center gap-2">
          <span className="text-base">📊</span> 统计
          <span className={`text-xs px-1.5 py-0.5 rounded ${solved === chals.length ? "bg-green-900/50 text-green-400" : "bg-gray-800 text-gray-400"}`}>
            {solved}/{chals.length}
          </span>
        </span>
        <span className={`text-xs transition ${open ? "rotate-180" : ""}`}>▼</span>
      </button>

      {open && (
        <div className="px-4 pb-4 border-t border-gray-800 pt-3 space-y-4">
          {/* Pie chart row */}
          <div>
            <p className="text-xs text-gray-500 mb-2">通过率</p>
            <div className="flex items-center gap-3">
              <div className="relative w-16 h-16">
                <svg viewBox="0 0 64 64" className="w-16 h-16 -rotate-90">
                  {/* Background circle */}
                  <circle cx="32" cy="32" r="28" fill="none" stroke="#1f2937" strokeWidth="8" />
                  {/* Solved arc */}
                  {solved > 0 && (
                    <circle cx="32" cy="32" r="28" fill="none" stroke="#10b981" strokeWidth="8"
                      strokeDasharray={`${(solved / chals.length * 100) / 100 * 175.9} 175.9`}
                      strokeLinecap="round" />
                  )}
                  {/* Failed arc */}
                  {failed > 0 && (
                    <circle cx="32" cy="32" r="28" fill="none" stroke="#ef4444" strokeWidth="8"
                      strokeDasharray={`${(failed / chals.length * 100) / 100 * 175.9} 175.9`}
                      strokeDashoffset={`${-(solved / chals.length * 100) / 100 * 175.9}`}
                      strokeLinecap="round" />
                  )}
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-xs font-bold text-gray-200">{Math.round(solved/chals.length*100)}%</span>
                </div>
              </div>
              <div className="flex-1 space-y-1 text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
                  <span className="text-gray-400">{solved} solved</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                  <span className="text-gray-400">{failed} failed</span>
                </div>
                {pending > 0 && (
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-gray-500" />
                    <span className="text-gray-400">{pending} pending</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Bar chart by type */}
          <div>
            <p className="text-xs text-gray-500 mb-2">按类型</p>
            <div className="space-y-1.5">
              {Object.entries(byType).sort((a, b) => b[1].total - a[1].total).map(([type, { total: t, solved: s }]) => (
                <div key={type} className="flex items-center gap-2 text-xs">
                  <span className="w-5 text-center">{typeEmoji[type] || "❓"}</span>
                  <span className="w-12 text-gray-400 text-right">{s}/{t}</span>
                  <div className="flex-1 h-3 bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-500" style={{
                      width: `${(t / maxTypeCount) * 100}%`,
                      backgroundColor: typeColor[type] || "#6b7280",
                      opacity: s / Math.max(t, 1) * 0.8 + 0.2,
                    }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
