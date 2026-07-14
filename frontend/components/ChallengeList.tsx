const typeEmoji: any = { crypto: "🔐", web: "🌐", bin: "💻", misc: "🧩", ai: "🤖" };
const statusClass: any = {
  pending: "text-gray-500",
  running: "text-yellow-400 animate-pulse",
  solved: "text-green-400",
  failed: "text-red-500",
};
const statusText: any = { pending: "pending", running: "running", solved: "solved", failed: "failed" };

export default function ChallengeList({ challenges }: { challenges: any[] }) {
  const n = challenges.filter((c: any) => c.status === "solved").length;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-bold text-gray-200">📋 Challenges</h2>
        <span className="text-xs text-gray-500">{n}/{challenges.length} solved</span>
      </div>

      {challenges.length === 0 ? (
        <p className="text-gray-600 text-sm py-8 text-center">还没扫到题，点 start</p>
      ) : (
        <div className="space-y-2">
          {challenges.map((c: any) => (
            <div key={c.id} className="bg-gray-800/50 border border-gray-700/50 rounded p-3 flex items-center justify-between hover:bg-gray-800 transition">
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500 font-mono">{c.id}</span>
                <span className="text-sm text-gray-200">{c.title}</span>
                <span className="text-xs text-gray-500">{typeEmoji[c.type] || "❓"}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-600">{"★".repeat(Math.min(c.difficulty || 1, 5))}</span>
                <span className={`text-xs font-bold ${statusClass[c.status] || "text-gray-500"}`}>{statusText[c.status] || c.status}</span>
                {c.flag && c.status === "solved" && (
                  <code className="text-xs bg-green-900/50 text-green-300 px-2 py-0.5 rounded font-mono">{c.flag}</code>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
