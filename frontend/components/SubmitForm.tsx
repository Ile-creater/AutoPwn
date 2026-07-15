"use client";

import { useState } from "react";

export default function SubmitForm() {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [hints, setHints] = useState("");
  const [diff, setDiff] = useState(2);
  const [sending, setSending] = useState(false);
  const [ok, setOk] = useState("");

  const submit = async () => {
    if (!url.trim()) return;
    setSending(true);
    setOk("");
    try {
      const r = await fetch("http://localhost:8000/api/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim() || "Web Challenge",
          url: url.trim(),
          hints: hints.trim(),
          difficulty: diff,
        }),
      });
      if (r.ok) {
        const d = await r.json();
        setOk(`已提交: ${d.id}`);
        setUrl(""); setTitle(""); setHints("");
      } else {
        setOk("提交失败");
      }
    } catch {
      setOk("后端没连上");
    }
    setSending(false);
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-4 py-2 text-left text-sm font-bold text-gray-400 hover:text-gray-200 flex items-center justify-between"
      >
        <span>📤 提交 Web 题</span>
        <span className={`text-xs transition ${open ? "rotate-180" : ""}`}>▼</span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-800 pt-3">
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-600"
            placeholder="容器地址 http://193.0.1.1:23333"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-600"
            placeholder="题目名（可选）"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <div className="flex gap-3">
            <select
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200"
              value={diff}
              onChange={(e) => setDiff(Number(e.target.value))}
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}> {"★".repeat(n)}</option>
              ))}
            </select>
            <input
              className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-200 placeholder-gray-600"
              placeholder="提示信息：试 SQL 注入，flag 在 admin 表..."
              value={hints}
              onChange={(e) => setHints(e.target.value)}
            />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">{ok || "填 URL 和提示，点提交"}</span>
            <button
              onClick={submit}
              disabled={sending || !url.trim()}
              className="px-4 py-1.5 rounded text-xs font-bold bg-blue-700 hover:bg-blue-600 text-white disabled:bg-gray-700 disabled:text-gray-500"
            >
              {sending ? "提交中..." : "提交"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
