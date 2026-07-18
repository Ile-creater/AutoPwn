"use client";

import { useState, useRef } from "react";

interface SubEntry {
  id: string;
  url: string;
  title: string;
  hints: string;
  difficulty: number;
  status: string;
  flag?: string;
}

const HINT_PRESETS = [
  { label: "SQL 注入", value: "试 SQL 注入，用户名 admin，flag 可能在数据库里" },
  { label: "XSS", value: "找 XSS 反射点，提交 <script> 标签试试" },
  { label: "命令注入", value: "可能有命令注入，试 ;id 或 |ls" },
  { label: "SSTI", value: "可能是模板注入，试 {{7*7}} 或 ${7*7}" },
  { label: "LFI", value: "可能有文件包含漏洞，试 ../../../etc/passwd" },
  { label: "IDOR", value: "试试改 URL 里的 id 参数，遍历 1-20" },
  { label: "SSRF", value: "可能有 SSRF，试传内网地址" },
  { label: "文件上传", value: "试试上传 PHP shell 或图片马" },
];

export default function SubmitForm() {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [hints, setHints] = useState("");
  const [diff, setDiff] = useState(2);
  const [sending, setSending] = useState(false);
  const [msg, setMsg] = useState("");
  const [history, setHistory] = useState<SubEntry[]>([]);
  const urlRef = useRef<HTMLInputElement>(null);

  const submit = async () => {
    if (!url.trim()) return;
    setSending(true);
    setMsg("");
    try {
      const r = await fetch("http://localhost:8000/api/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: `Web: ${url.trim().replace(/https?:\/\//, "").replace(/:\d+/, "").slice(0, 30)}`,
          url: url.trim(),
          hints: hints.trim(),
          difficulty: diff,
        }),
      });
      if (r.ok) {
        const d = await r.json();
        setMsg(`✓ 已提交 ${d.id}`);
        setHistory((prev) => [
          { id: d.id, url: url.trim(), title: url.trim().replace(/https?:\/\//, "").slice(0, 25), hints: hints.trim(), difficulty: diff, status: "pending" },
          ...prev.slice(0, 9),
        ]);
        setUrl("");
        setHints("");
        urlRef.current?.focus();
      } else {
        setMsg("提交失败");
      }
    } catch {
      setMsg("后端没连上，检查 localhost:8000");
    }
    setSending(false);
  };

  const handleUrlKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && url.trim()) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-4 py-2 text-left text-sm font-bold text-gray-300 hover:text-gray-100 flex items-center justify-between transition"
      >
        <span className="flex items-center gap-2">
          <span className="text-base">🌐</span> 提交 Web 题
          {history.length > 0 && (
            <span className="text-xs bg-blue-900/50 text-blue-300 px-1.5 py-0.5 rounded">{history.length}</span>
          )}
        </span>
        <span className={`text-xs transition ${open ? "rotate-180" : ""}`}>▼</span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-800 pt-3">
          {/* URL 输入 */}
          <div>
            <label className="text-xs text-gray-500 mb-1.5 block">容器地址</label>
            <input
              ref={urlRef}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-green-300 font-mono placeholder-gray-600 focus:border-blue-500/50 focus:outline-none transition"
              placeholder="http://10.0.0.1:23333/login"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={handleUrlKey}
              autoFocus
            />
          </div>

          {/* 提示输入 */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs text-gray-500">解题提示</label>
              <span className="text-xs text-gray-600">{hints.length}/500</span>
            </div>
            <textarea
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:border-blue-500/50 focus:outline-none resize-none transition"
              rows={3}
              maxLength={500}
              placeholder="比如：SQL 注入，flag 在 users 表里，试 admin' OR '1'='1"
              value={hints}
              onChange={(e) => setHints(e.target.value.slice(0, 500))}
            />
            {/* 快捷提示词 */}
            <div className="flex flex-wrap gap-1 mt-1.5">
              {HINT_PRESETS.slice(0, 8).map((p) => (
                <button
                  key={p.label}
                  onClick={() => setHints((prev) => (prev ? prev + "; " + p.value : p.value))}
                  className="text-xs px-2 py-0.5 rounded bg-gray-800 border border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-600 transition"
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* 难度 + 提交 */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-500">难度</span>
              <select
                className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200"
                value={diff}
                onChange={(e) => setDiff(Number(e.target.value))}
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>{"★".repeat(n)}</option>
                ))}
              </select>
            </div>

            <button
              onClick={submit}
              disabled={sending || !url.trim()}
              className="flex-1 px-4 py-2 rounded text-sm font-bold bg-blue-700 hover:bg-blue-600 active:bg-blue-800 text-white disabled:bg-gray-700 disabled:text-gray-500 transition"
            >
              {sending ? "提交中..." : "提交到解题池"}
            </button>
          </div>

          {msg && (
            <p className={`text-xs px-3 py-1.5 rounded ${msg.startsWith("✓") ? "bg-green-900/30 text-green-400" : "bg-red-900/30 text-red-400"}`}>
              {msg}
            </p>
          )}

          {/* 提交历史 */}
          {history.length > 0 && (
            <div className="border-t border-gray-800 pt-2">
              <p className="text-xs text-gray-500 mb-2">提交记录</p>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {history.map((h) => (
                  <div key={h.id} className="flex items-center gap-2 text-xs bg-gray-800/50 rounded px-2 py-1.5">
                    <span className="text-gray-600 font-mono w-16 truncate">{h.id}</span>
                    <span className="text-gray-300 truncate flex-1">{h.url}</span>
                    <span className="text-gray-600">{h.difficulty}★</span>
                    <span className={`${h.status === "solved" ? "text-green-400" : h.status === "failed" ? "text-red-400" : "text-gray-500"}`}>
                      {h.status}
                    </span>
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
