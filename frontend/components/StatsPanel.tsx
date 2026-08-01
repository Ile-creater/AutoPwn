"use client";

import { useState } from "react";

const emoji: Record<string, string> = { crypto: "🔐", web: "🌐", bin: "💻", misc: "🧩", pwn: "💥", ai: "🤖" };
const colors: Record<string, string> = { crypto: "#10b981", web: "#3b82f6", bin: "#8b5cf6", misc: "#f59e0b", pwn: "#ef4444", ai: "#ec4899" };

export default function StatsPanel({ chals }: { chals: any[] }) {
  const [open, setOpen] = useState(false);
  if (chals.length === 0) return null;

  const solved = chals.filter((c) => c.status === "solved").length;
  const failed = chals.filter((c) => c.status === "failed").length;
  const pending = chals.length - solved - failed;

  const byType: Record<string, { total: number; solved: number }> = {};
  for (const c of chals) {
    if (!byType[c.type]) byType[c.type] = { total: 0, solved: 0 };
    byType[c.type].total++;
    if (c.status === "solved") byType[c.type].solved++;
  }
  const maxType = Math.max(1, ...Object.values(byType).map((v) => v.total));

  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-sm overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full px-5 py-3.5 text-left text-sm font-semibold text-gray-700 hover:bg-gray-50/50 flex items-center justify-between transition">
        <span className="flex items-center gap-2">
          <span className="text-base">📊</span> Stats
          <span className={`text-xs px-1.5 py-0.5 rounded-md ${solved === chals.length ? "bg-emerald-50 text-emerald-600" : "bg-gray-50 text-gray-500"}`}>
            {solved}/{chals.length}
          </span>
        </span>
        <span className={`text-xs text-gray-400 transition ${open ? "rotate-180" : ""}`}>▼</span>
      </button>
      {open && (
        <div className="px-5 pb-4 border-t border-gray-50 pt-4 space-y-4">
          <div className="flex items-center gap-4">
            <svg viewBox="0 0 64 64" className="w-16 h-16 -rotate-90">
              <circle cx="32" cy="32" r="28" fill="none" stroke="#f1f5f9" strokeWidth="8" />
              {solved > 0 && <circle cx="32" cy="32" r="28" fill="none" stroke="#10b981" strokeWidth="8"
                strokeDasharray={`${(solved / chals.length) * 175.9} 175.9`} strokeLinecap="round" />}
              {failed > 0 && <circle cx="32" cy="32" r="28" fill="none" stroke="#ef4444" strokeWidth="8"
                strokeDasharray={`${(failed / chals.length) * 175.9} 175.9`}
                strokeDashoffset={`${-(solved / chals.length) * 175.9}`} strokeLinecap="round" />}
            </svg>
            <div className="space-y-1.5 text-xs">
              <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-emerald-500" /><span className="text-gray-500">{solved} solved</span></div>
              <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-red-400" /><span className="text-gray-500">{failed} failed</span></div>
              {pending > 0 && <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-gray-200" /><span className="text-gray-500">{pending} pending</span></div>}
            </div>
          </div>
          <div className="space-y-1.5">
            {Object.entries(byType).sort((a, b) => b[1].total - a[1].total).map(([type, { total: t, solved: s }]) => (
              <div key={type} className="flex items-center gap-2 text-xs">
                <span className="w-5 text-center">{emoji[type] || "❓"}</span>
                <span className="w-10 text-gray-400 text-right">{s}/{t}</span>
                <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${(t / maxType) * 100}%`, backgroundColor: colors[type] || "#9ca3af", opacity: s / Math.max(t, 1) * 0.85 + 0.15 }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
