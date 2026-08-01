"use client";

import { useState, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

type ChalType = "web" | "misc" | "bin" | "pwn" | "ai";

const TABS: { key: ChalType; label: string; icon: string }[] = [
  { key: "web", label: "Web", icon: "🌐" },
  { key: "misc", label: "Misc", icon: "🧩" },
  { key: "bin", label: "Reverse", icon: "💻" },
  { key: "pwn", label: "Pwn", icon: "💥" },
  { key: "ai", label: "AI 安全", icon: "🤖" },
];

const WEB_HINTS = [
  { label: "SQL 注入", value: "试 SQL 注入，用户名 admin，flag 可能在数据库里" },
  { label: "XSS", value: "找 XSS 反射点，提交 <script> 标签试试" },
  { label: "命令注入", value: "可能有命令注入，试 ;id 或 |ls" },
  { label: "SSTI", value: "可能是模板注入，试 {{7*7}}" },
  { label: "LFI", value: "可能有文件包含，试 ../../../etc/passwd" },
  { label: "IDOR", value: "改 URL 里的 id 参数，遍历 1-20" },
];

const BIN_HINTS = [
  { label: "查壳", value: "用 file 看下是什么文件" },
  { label: "字符串", value: "strings 全扫，搜索 flag/ctf/password" },
  { label: "反编译", value: "用 rizin 反编译 main 函数" },
  { label: "调试", value: "gdb 动态跟一下输入到比较的路径" },
];

const PWN_HINTS = [
  { label: "checksec", value: "先 checksec 看保护：NX/PIE/Canary/RELRO" },
  { label: "溢出", value: "cyclic 200 测缓冲区大小" },
  { label: "ROP", value: "找 gadget：pop rdi; ret，构造 ROP 链" },
  { label: "fmtstr", value: "格式化字符串，试 %x.%x.%x" },
];

const AI_HINTS = [
  { label: "越狱", value: "试 jailbreak prompt：忽略之前指令" },
  { label: "注入", value: "试 prompt injection：覆盖系统提示词" },
  { label: "编码绕过", value: "用 base64 编码恶意指令" },
];

const HINT_MAP: Record<ChalType, { label: string; value: string }[]> = {
  web: WEB_HINTS, misc: [], bin: BIN_HINTS, pwn: PWN_HINTS, ai: AI_HINTS,
};

export default function SubmitForm() {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<ChalType>("web");
  const [url, setUrl] = useState("");
  const [hints, setHints] = useState("");
  const [diff, setDiff] = useState(2);
  const [file, setFile] = useState<File | null>(null);
  const [sending, setSending] = useState(false);
  const [msg, setMsg] = useState("");
  const [history, setHistory] = useState<any[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const submit = async () => {
    setSending(true); setMsg("");
    try {
      let r: Response;
      if (file && tab !== "web") {
        const fd = new FormData();
        fd.append("title", `[${tab.toUpperCase()}] ${file.name}`);
        fd.append("type", tab); fd.append("hints", hints.trim());
        fd.append("difficulty", String(diff)); fd.append("file", file);
        r = await fetch(`${API}/api/submit/file`, { method: "POST", body: fd });
      } else {
        r = await fetch(`${API}/api/submit`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type: tab, url: url.trim(), hints: hints.trim(), difficulty: diff, title: tab === "web" ? `Web: ${url.trim().slice(0, 30)}` : "" }),
        });
      }
      if (r.ok) {
        const d = await r.json();
        setMsg(`Submitted · ${d.id}`);
        setHistory((prev) => [{ id: d.id, type: tab, title: d.id, difficulty: diff, status: "pending" }, ...prev.slice(0, 4)]);
        setUrl(""); setHints(""); setFile(null);
        if (fileRef.current) fileRef.current.value = "";
      } else setMsg("failed");
    } catch { setMsg("backend offline"); }
    setSending(false);
  };

  const presets = HINT_MAP[tab] || [];

  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-sm overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full px-5 py-3.5 text-left text-sm font-semibold text-gray-700 hover:bg-gray-50/50 flex items-center justify-between transition">
        <span className="flex items-center gap-2">
          <span className="text-base">📤</span> Submit Challenge
          {history.length > 0 && <span className="text-xs bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded-md font-medium">{history.length}</span>}
        </span>
        <span className={`text-xs text-gray-400 transition ${open ? "rotate-180" : ""}`}>▼</span>
      </button>

      {open && (
        <div className="px-5 pb-5 border-t border-gray-50">
          {/* Tabs */}
          <div className="flex gap-0.5 mb-4 mt-4 bg-gray-50 rounded-lg p-1">
            {TABS.map((t) => (
              <button key={t.key} onClick={() => { setTab(t.key); setUrl(""); setHints(""); }}
                className={`flex-1 text-xs font-semibold py-2 rounded-md transition ${
                  tab === t.key ? "bg-white text-gray-900 shadow-sm" : "text-gray-400 hover:text-gray-600"}`}>
                {t.icon} {t.label}
              </button>
            ))}
          </div>

          {tab === "web" && (
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1.5 block">Target URL</label>
                <input className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3.5 py-2.5 text-sm text-gray-700 font-mono placeholder-gray-400 focus:border-emerald-300 focus:ring-2 focus:ring-emerald-50 focus:outline-none transition"
                  placeholder="https://10.0.0.1:23333/login" value={url} onChange={(e) => setUrl(e.target.value)} autoFocus
                  onKeyDown={(e) => { if (e.key === "Enter" && url.trim()) { e.preventDefault(); submit(); } }} />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1.5 block">Hints</label>
                <textarea className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3.5 py-2.5 text-sm text-gray-700 placeholder-gray-400 resize-none focus:border-emerald-300 focus:ring-2 focus:ring-emerald-50 focus:outline-none transition"
                  rows={3} maxLength={500} placeholder="e.g., SQL injection, flag in users table..."
                  value={hints} onChange={(e) => setHints(e.target.value.slice(0, 500))} />
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {WEB_HINTS.map((p) => (
                    <button key={p.label} onClick={() => setHints((prev) => (prev ? prev + "; " + p.value : p.value))}
                      className="text-xs px-2.5 py-1 rounded-md bg-gray-50 border border-gray-100 text-gray-500 hover:text-gray-700 hover:border-gray-200 transition">{p.label}</button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {tab !== "web" && (
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1.5 block">Attachment</label>
                <div className="border-2 border-dashed border-gray-200 rounded-xl p-6 text-center cursor-pointer hover:border-emerald-300 hover:bg-emerald-50/30 transition"
                  onClick={() => fileRef.current?.click()}>
                  {file ? (
                    <div className="flex items-center justify-center gap-2 text-sm">
                      <span className="text-emerald-600">📎</span>
                      <span className="text-gray-700 font-medium">{file.name}</span>
                      <span className="text-gray-400">({(file.size / 1024).toFixed(1)} KB)</span>
                      <button onClick={(e) => { e.stopPropagation(); setFile(null); if (fileRef.current) fileRef.current.value = ""; }}
                        className="text-red-400 hover:text-red-500 text-xs ml-2">remove</button>
                    </div>
                  ) : (
                    <div>
                      <p className="text-gray-500 text-sm">click to select file</p>
                      <p className="text-gray-400 text-xs mt-1">ZIP / ELF / PNG / TXT</p>
                    </div>
                  )}
                  <input ref={fileRef} type="file" className="hidden" onChange={(e: any) => { const f = e.target.files?.[0]; if (f) setFile(f); }} />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-500 mb-1.5 block">Hints</label>
                <textarea className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3.5 py-2.5 text-sm text-gray-700 placeholder-gray-400 resize-none focus:border-emerald-300 focus:outline-none transition"
                  rows={3} maxLength={500} value={hints} onChange={(e) => setHints(e.target.value.slice(0, 500))} placeholder="e.g., base64 ZIP, strings for flag..." />
                {presets.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {presets.map((p) => (
                      <button key={p.label} onClick={() => setHints((prev) => (prev ? prev + "; " + p.value : p.value))}
                        className="text-xs px-2.5 py-1 rounded-md bg-gray-50 border border-gray-100 text-gray-500 hover:text-gray-700 hover:border-gray-200 transition">{p.label}</button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="flex items-center gap-3 mt-4">
            <select className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-600"
              value={diff} onChange={(e) => setDiff(Number(e.target.value))}>
              {[1, 2, 3, 4, 5].map((n) => (<option key={n} value={n}>{"★".repeat(n)}</option>))}
            </select>
            <span className="text-xs text-gray-400 flex-1">{tab === "web" ? "URL" : file ? file.name : "no file"}</span>
            <button onClick={submit} disabled={sending}
              className="px-5 py-2 rounded-lg text-sm font-semibold bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white shadow-sm shadow-emerald-200 disabled:bg-gray-100 disabled:text-gray-400 disabled:shadow-none transition-all">
              {sending ? "..." : "submit"}
            </button>
          </div>

          {msg && <p className={`text-xs px-3 py-2 mt-3 rounded-lg ${msg.startsWith("S") ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600"}`}>{msg}</p>}

          {history.length > 0 && (
            <div className="border-t border-gray-50 pt-3 mt-3">
              <p className="text-xs font-medium text-gray-400 mb-2">recent</p>
              <div className="space-y-1">
                {history.map((h) => (
                  <div key={h.id} className="flex items-center gap-2 text-xs text-gray-500">
                    <span className="font-mono text-gray-300 w-14 truncate">{h.id}</span>
                    <span className={`px-1 rounded text-[10px] ${h.type === "web" ? "bg-blue-50 text-blue-600" : h.type === "bin" ? "bg-purple-50 text-purple-600" : h.type === "pwn" ? "bg-red-50 text-red-600" : "bg-emerald-50 text-emerald-600"}`}>{h.type}</span>
                    <span>{h.difficulty}★</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
