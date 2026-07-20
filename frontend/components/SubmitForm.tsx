"use client";

import { useState, useRef } from "react";

interface SubEntry {
  id: string;
  type: string;
  title: string;
  difficulty: number;
  status: string;
}

type ChalType = "web" | "misc" | "bin" | "pwn";

const TABS: { key: ChalType; label: string; icon: string }[] = [
  { key: "web",  label: "Web",     icon: "🌐" },
  { key: "misc", label: "Misc",    icon: "🧩" },
  { key: "bin",  label: "Reverse", icon: "💻" },
  { key: "pwn",  label: "Pwn",     icon: "💥" },
];

const WEB_HINTS = [
  { label: "SQL 注入", value: "试 SQL 注入，用户名 admin，flag 可能在数据库里" },
  { label: "XSS", value: "找 XSS 反射点，提交 <script> 标签试试" },
  { label: "命令注入", value: "可能有命令注入，试 ;id 或 |ls" },
  { label: "SSTI", value: "可能是模板注入，试 {{7*7}} 或 ${7*7}" },
  { label: "LFI", value: "可能有文件包含漏洞，试 ../../../etc/passwd" },
  { label: "IDOR", value: "试试改 URL 里的 id 参数，遍历 1-20" },
  { label: "SSRF", value: "可能有 SSRF，试传内网地址" },
  { label: "文件上传", value: "试试上传 PHP shell 或图片马" },
];

const BIN_HINTS = [
  { label: "查壳", value: "用 file 看下是什么文件，查下有没有壳" },
  { label: "符号表", value: "看看 nm/objdump 符号表里有没有 win/flag 函数" },
  { label: "字符串", value: "strings 全扫一遍，搜索 flag/ctf/password" },
  { label: "反编译", value: "用 rizin 反编译 main 函数，看逻辑" },
  { label: "调试", value: "gdb 动态跟一下输入到比较的路径" },
  { label: "patch", value: "试 NOP 掉关键跳转，或 patch 二进制" },
];

const PWN_HINTS = [
  { label: "checksec", value: "先 checksec 看保护：NX/PIE/Canary/RELRO" },
  { label: "溢出", value: "cyclic 200 测缓冲区大小，找 rip 偏移" },
  { label: "ROP", value: "找 gadget：pop rdi; ret，构造 ROP 链" },
  { label: "fmtstr", value: "格式化字符串漏洞，试 %x.%x.%x.%x 泄露栈" },
  { label: "shellcode", value: "NX 关了就直接写 shellcode 跳过去" },
  { label: "one_gadget", value: "libc 泄露后用 one_gadget 一把梭" },
];

const HINT_MAP: Record<ChalType, { label: string; value: string }[]> = {
  web: WEB_HINTS, misc: [], bin: BIN_HINTS, pwn: PWN_HINTS,
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
  const [history, setHistory] = useState<SubEntry[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const submit = async () => {
    setSending(true); setMsg("");

    try {
      let r: Response;
      // 有文件 → multipart
      if (file && tab !== "web") {
        const fd = new FormData();
        fd.append("title", `[${tab.toUpperCase()}] ${file.name}`);
        fd.append("type", tab);
        fd.append("hints", hints.trim());
        fd.append("difficulty", String(diff));
        fd.append("file", file);
        r = await fetch("http://localhost:8000/api/submit/file", { method: "POST", body: fd });
      } else {
        r = await fetch("http://localhost:8000/api/submit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            type: tab, url: url.trim(), hints: hints.trim(),
            difficulty: diff, title: tab === "web" ? `Web: ${url.trim().slice(0, 30)}` : "",
          }),
        });
      }

      if (r.ok) {
        const d = await r.json();
        setMsg(`✓ 已提交 ${d.id}`);
        setHistory((prev) => [
          { id: d.id, type: tab, title: d.id, difficulty: diff, status: "pending" },
          ...prev.slice(0, 9),
        ]);
        setUrl(""); setHints(""); setFile(null);
        if (fileRef.current) fileRef.current.value = "";
      } else {
        setMsg("提交失败");
      }
    } catch { setMsg("后端没连上"); }
    setSending(false);
  };

  const presets = HINT_MAP[tab] || [];

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-4 py-2 text-left text-sm font-bold text-gray-300 hover:text-gray-100 flex items-center justify-between transition"
      >
        <span className="flex items-center gap-2">
          <span className="text-base">📤</span> 提交题目
          {history.length > 0 && (
            <span className="text-xs bg-blue-900/50 text-blue-300 px-1.5 py-0.5 rounded">{history.length}</span>
          )}
        </span>
        <span className={`text-xs transition ${open ? "rotate-180" : ""}`}>▼</span>
      </button>

      {open && (
        <div className="px-4 pb-4 border-t border-gray-800 pt-3">
          {/* Tabs */}
          <div className="flex gap-1 mb-3 bg-gray-800/50 rounded-lg p-1">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => { setTab(t.key); setUrl(""); setHints(""); }}
                className={`flex-1 text-xs font-bold py-1.5 rounded-md transition ${
                  tab === t.key ? "bg-blue-700 text-white shadow" : "text-gray-500 hover:text-gray-300"
                }`}
              >
                {t.icon} {t.label}
              </button>
            ))}
          </div>

          {/* Web: URL 输入 */}
          {tab === "web" && (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500 mb-1.5 block">容器地址</label>
                <input
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-green-300 font-mono placeholder-gray-600 focus:border-blue-500/50 focus:outline-none"
                  placeholder="http://10.0.0.1:23333/login"
                  value={url} onChange={(e) => setUrl(e.target.value)} autoFocus
                  onKeyDown={(e) => { if (e.key === "Enter" && url.trim()) { e.preventDefault(); submit(); } }}
                />
              </div>
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs text-gray-500">解题提示</label>
                  <span className="text-xs text-gray-600">{hints.length}/500</span>
                </div>
                <textarea
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-600 resize-none focus:border-blue-500/50 focus:outline-none"
                  rows={3} maxLength={500} placeholder="SQL 注入，flag 在 users 表..."
                  value={hints} onChange={(e) => setHints(e.target.value.slice(0, 500))}
                />
                <div className="flex flex-wrap gap-1 mt-1.5">
                  {WEB_HINTS.map((p) => (
                    <button key={p.label} onClick={() => setHints((prev) => (prev ? prev + "; " + p.value : p.value))}
                      className="text-xs px-2 py-0.5 rounded bg-gray-800 border border-gray-700 text-gray-400 hover:text-gray-200 transition">{p.label}</button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Misc / Reverse / Pwn: 文件上传 + 提示 */}
          {tab !== "web" && (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500 mb-1.5 block">附件文件</label>
                <div
                  className="border-2 border-dashed border-gray-700 rounded-lg p-4 text-center cursor-pointer hover:border-blue-500/50 transition"
                  onClick={() => fileRef.current?.click()}
                >
                  {file ? (
                    <div className="flex items-center justify-center gap-2 text-sm">
                      <span className="text-green-400">📎</span>
                      <span className="text-gray-200">{file.name}</span>
                      <span className="text-gray-600">({(file.size / 1024).toFixed(1)} KB)</span>
                      <button
                        onClick={(e) => { e.stopPropagation(); setFile(null); if (fileRef.current) fileRef.current.value = ""; }}
                        className="text-red-400 hover:text-red-300 text-xs ml-2"
                      >移除</button>
                    </div>
                  ) : (
                    <div>
                      <p className="text-gray-500 text-sm">点击选择文件或拖拽到此处</p>
                      <p className="text-gray-600 text-xs mt-1">支持 ZIP / ELF / PNG / TXT 等任意格式</p>
                    </div>
                  )}
                  <input
                    ref={fileRef} type="file" className="hidden"
                    onChange={(e) => { const f = e.target.files?.[0]; if (f) setFile(f); }}
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1.5 block">解题提示</label>
                <textarea
                  className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-600 resize-none focus:border-blue-500/50 focus:outline-none"
                  rows={3} maxLength={500} placeholder="比如：Base64 嵌套 ZIP，strings 找 flag..."
                  value={hints} onChange={(e) => setHints(e.target.value.slice(0, 500))}
                />
                {presets.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {presets.map((p) => (
                      <button key={p.label} onClick={() => setHints((prev) => (prev ? prev + "; " + p.value : p.value))}
                        className="text-xs px-2 py-0.5 rounded bg-gray-800 border border-gray-700 text-gray-400 hover:text-gray-200 transition">{p.label}</button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 难度 + 提交 */}
          <div className="flex items-center gap-3 mt-3">
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-500">难度</span>
              <select className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200"
                value={diff} onChange={(e) => setDiff(Number(e.target.value))}>
                {[1, 2, 3, 4, 5].map((n) => (<option key={n} value={n}>{"★".repeat(n)}</option>))}
              </select>
            </div>
            <span className="text-xs text-gray-600 flex-1">
              {tab === "web" ? "带 URL" : file ? `附件 ${file.name}` : "无附件"}
            </span>
            <button
              onClick={submit} disabled={sending}
              className="px-4 py-2 rounded text-sm font-bold bg-blue-700 hover:bg-blue-600 active:bg-blue-800 text-white disabled:bg-gray-700 disabled:text-gray-500 transition"
            >
              {sending ? "提交中..." : "提交到解题池"}
            </button>
          </div>

          {msg && (
            <p className={`text-xs px-3 py-1.5 mt-2 rounded ${msg.startsWith("✓") ? "bg-green-900/30 text-green-400" : "bg-red-900/30 text-red-400"}`}>{msg}</p>
          )}

          {/* 提交历史 */}
          {history.length > 0 && (
            <div className="border-t border-gray-800 pt-2 mt-2">
              <p className="text-xs text-gray-500 mb-2">提交记录</p>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {history.map((h) => (
                  <div key={h.id} className="flex items-center gap-2 text-xs bg-gray-800/50 rounded px-2 py-1.5">
                    <span className="text-gray-600 font-mono w-14 truncate">{h.id}</span>
                    <span className={`text-xs px-1 rounded ${h.type === "web" ? "bg-blue-900/50 text-blue-300" : h.type === "bin" ? "bg-purple-900/50 text-purple-300" : h.type === "pwn" ? "bg-red-900/50 text-red-300" : "bg-green-900/50 text-green-300"}`}>{h.type}</span>
                    <span className="text-gray-600">{h.difficulty}★</span>
                    <span className={`${h.status === "solved" ? "text-green-400" : "text-gray-500"}`}>{h.status}</span>
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
