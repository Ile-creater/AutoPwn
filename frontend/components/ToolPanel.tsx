"use client";

import { useState } from "react";

interface Tool { name: string; ok: boolean; install: string; }

const meta: Record<string, { icon: string; label: string; desc: string }> = {
  rizin: { icon: "🔬", label: "Rizin", desc: "disassembler" },
  ollama: { icon: "🧠", label: "Ollama", desc: "local AI" },
  docker: { icon: "🐳", label: "Docker", desc: "sandbox" },
  pwntools: { icon: "💥", label: "pwntools", desc: "exploit dev" },
  binwalk: { icon: "🔍", label: "binwalk", desc: "file carving" },
  exiftool: { icon: "📷", label: "exiftool", desc: "metadata" },
};

export default function ToolPanel({ tools }: { tools: Tool[] }) {
  const [open, setOpen] = useState(false);
  const ok = tools.filter((t) => t.ok).length;
  const total = tools.length;

  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-sm overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full px-5 py-3.5 text-left text-sm font-semibold text-gray-700 hover:bg-gray-50/50 flex items-center justify-between transition">
        <span className="flex items-center gap-2">
          <span className="text-base">🔧</span> Toolchain
          <span className={`text-xs px-1.5 py-0.5 rounded-md ${ok === total ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"}`}>{ok}/{total}</span>
        </span>
        <span className={`text-xs text-gray-400 transition ${open ? "rotate-180" : ""}`}>▼</span>
      </button>
      {open && (
        <div className="px-5 pb-4 space-y-2 border-t border-gray-50 pt-3">
          {tools.map((t) => {
            const m = meta[t.name] || { icon: "❓", label: t.name, desc: "" };
            return (
              <div key={t.name} className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-xs ${t.ok ? "bg-emerald-50/50 border border-emerald-100/50" : "bg-gray-50 border border-gray-100"}`}>
                <span className="text-sm">{m.icon}</span>
                <div className="flex-1">
                  <span className="text-gray-700 font-semibold">{m.label}</span>
                  <span className="text-gray-400 ml-1.5">{m.desc}</span>
                </div>
                {t.ok ? (
                  <span className="text-emerald-500 text-xs font-bold">✓</span>
                ) : (
                  <button
                    onClick={() => { if (t.install.startsWith("http")) window.open(t.install, "_blank"); else { navigator.clipboard?.writeText(t.install); alert(`copied: ${t.install}`); } }}
                    className="text-xs px-2 py-1 rounded-md bg-white border border-gray-200 hover:bg-gray-50 text-gray-600 font-medium transition">
                    {t.install.startsWith("http") ? "install" : "copy"}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
