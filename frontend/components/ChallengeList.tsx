interface Challenge {
  id: string;
  title: string;
  type: string;
  difficulty: number;
  status: string;
  flag?: string;
}

const typeLabels: Record<string, string> = {
  crypto: "🔐 密码",
  web: "🌐 Web",
  bin: "💻 逆向",
  misc: "🧩 杂项",
  ai: "🤖 AI",
};

const statusColors: Record<string, string> = {
  pending: "text-gray-500",
  running: "text-yellow-400 animate-pulse",
  solved: "text-green-400",
  failed: "text-red-500",
};

const statusLabels: Record<string, string> = {
  pending: "等待中",
  running: "解题中",
  solved: "已解出",
  failed: "未解出",
};

export default function ChallengeList({
  challenges,
}: {
  challenges: Challenge[];
}) {
  const solved = challenges.filter((c) => c.status === "solved").length;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-bold text-gray-200">📋 题目列表</h2>
        <span className="text-xs text-gray-500">
          {solved}/{challenges.length} 已解出
        </span>
      </div>

      {challenges.length === 0 ? (
        <p className="text-gray-600 text-sm py-8 text-center">
          暂无题目，点击「开始解题」扫描
        </p>
      ) : (
        <div className="space-y-2">
          {challenges.map((c) => (
            <div
              key={c.id}
              className="bg-gray-800/50 border border-gray-700/50 rounded p-3 flex items-center justify-between hover:bg-gray-800 transition"
            >
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500 font-mono">
                  {c.id}
                </span>
                <div>
                  <span className="text-sm text-gray-200">{c.title}</span>
                  <span className="ml-2 text-xs text-gray-500">
                    {typeLabels[c.type] || c.type}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-600">
                  {"⭐".repeat(Math.min(c.difficulty, 5))}
                </span>
                <span
                  className={`text-xs font-bold ${statusColors[c.status] || "text-gray-500"}`}
                >
                  {statusLabels[c.status] || c.status}
                </span>
                {c.flag && c.status === "solved" && (
                  <code className="text-xs bg-green-900/50 text-green-300 px-2 py-0.5 rounded font-mono">
                    {c.flag}
                  </code>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
