const API = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const emoji: any = { crypto: "🔐", web: "🌐", bin: "💻", misc: "🧩", pwn: "💥", ai: "🤖" };
const statusColor: any = { pending: "text-gray-400", running: "text-amber-500", solved: "text-emerald-600", failed: "text-red-500" };
const statusLabel: any = { pending: "pending", running: "running", solved: "solved", failed: "failed" };

export default function ChallengeList({ challenges, onReplayLog }: { challenges: any[]; onReplayLog?: (cid: string) => void }) {
  const solved = challenges.filter((c: any) => c.status === "solved").length;

  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-50">
        <h2 className="text-sm font-semibold text-gray-700">Challenges</h2>
        <span className="text-xs text-gray-400 font-medium">{solved}/{challenges.length} solved</span>
      </div>

      {challenges.length === 0 ? (
        <p className="text-sm text-gray-400 py-10 text-center">no challenges yet</p>
      ) : (
        <div className="divide-y divide-gray-50">
          {challenges.map((c: any) => (
            <div key={c.id} className="px-5 py-3 flex items-center justify-between hover:bg-gray-50/50 transition">
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-300 font-mono">{c.id}</span>
                <span className="text-sm text-gray-700">{c.title}</span>
                <span className="text-xs text-gray-400">{emoji[c.type] || "❓"}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-300">{"★".repeat(Math.min(c.difficulty || 1, 5))}</span>
                <span className={`text-xs font-semibold ${statusColor[c.status] || "text-gray-400"}`}>{statusLabel[c.status] || c.status}</span>
                {c.error && c.status === "failed" && (
                  <span className="text-xs text-red-400/70 max-w-[120px] truncate" title={c.error}>{c.error}</span>
                )}
                {c.flag && c.status === "solved" && (
                  <>
                    <code className="text-xs bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-md font-mono">{c.flag}</code>
                    <button onClick={() => onReplayLog?.(c.id)} className="text-xs px-2 py-1 rounded-md bg-gray-50 hover:bg-gray-100 text-gray-500 font-medium transition">
                      replay
                    </button>
                    <a href={`${API}/api/writeup/${c.id}`} target="_blank" className="text-xs px-2 py-1 rounded-md bg-gray-50 hover:bg-gray-100 text-gray-500 font-medium transition">
                      writeup
                    </a>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
