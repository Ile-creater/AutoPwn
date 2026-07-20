"use client";

import { useState } from "react";

interface Tool {
  name: string;
  ok: boolean;
  install: string;
}

const toolMeta: Record<string, { icon: string; label: string; desc: string }> = {
  rizin:    { icon: "🔬", label: "Rizin",    desc: "反汇编/反编译" },
  ollama:   { icon: "🧠", label: "Ollama",   desc: "本地 AI 推理" },
  docker:   { icon: "🐳", label: "Docker",   desc: "沙箱隔离" },
  pwntools: { icon: "💥", label: "pwntools", desc: "漏洞利用框架" },
  binwalk:  { icon: "🔍", label: "binwalk",  desc: "文件分离" },
  exiftool: { icon: "📷", label: "exiftool", desc: "元数据提取" },
};

export default function ToolPanel({ tools }: { tools: Tool[] }) {
  const [open, setOpen] = useState(false);

  const ok = tools.filter((t) => t.ok).length;
  const total = tools.length;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-4 py-2 text-left text-sm font-bold text-gray-400 hover:text-gray-200 flex items-center justify-between transition"
      >
        <span className="flex items-center gap-2">
          <span className="text-base">🔧</span> 工具链
          <span className={`text-xs px-1.5 py-0.5 rounded ${ok === total ? "bg-green-900/50 text-green-400" : "bg-yellow-900/50 text-yellow-400"}`}>
            {ok}/{total}
          </span>
        </span>
        <span className={`text-xs transition ${open ? "rotate-180" : ""}`}>▼</span>
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-2 border-t border-gray-800 pt-3">
          {tools.map((t) => {
            const m = toolMeta[t.name] || { icon: "❓", label: t.name, desc: "" };
            return (
              <div key={t.name} className={`flex items-center gap-2 rounded px-2 py-1.5 text-xs ${t.ok ? "bg-green-900/20 border border-green-800/30" : "bg-gray-800/50 border border-gray-700/50"}`}>
                <span className="text-sm">{m.icon}</span>
                <div className="flex-1">
                  <span className="text-gray-200 font-bold">{m.label}</span>
                  <span className="text-gray-600 ml-1.5">{m.desc}</span>
                </div>
                {t.ok ? (
                  <span className="text-green-400 text-xs font-bold">✓</span>
                ) : (
                  <button
                    onClick={() => {
                      if (t.install.startsWith("http")) {
                        window.open(t.install, "_blank");
                      } else {
                        navigator.clipboard?.writeText(t.install);
                        alert(`已复制安装命令：\n${t.install}`);
                      }
                    }}
                    className="text-xs px-2 py-1 rounded bg-blue-700/60 hover:bg-blue-600 text-blue-200 font-bold whitespace-nowrap transition"
                    title={t.install.startsWith("http") ? "打开下载页" : "复制安装命令"}
                  >
                    {t.install.startsWith("http") ? "下载" : "复制"}
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
