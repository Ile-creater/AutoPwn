interface Agent {
  id: string;
  name: string;
  status: string;
  current_challenge?: string;
}

const statusIcons: Record<string, string> = {
  idle: "💤",
  running: "🔄",
  done: "✅",
};

const statusColors: Record<string, string> = {
  idle: "border-gray-700",
  running: "border-yellow-500/50 animate-pulse",
  done: "border-green-600",
};

export default function AgentPanel({ agents }: { agents: Agent[] }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 h-full">
      <h2 className="text-lg font-bold text-gray-200 mb-3">
        🤖 Agent 状态
      </h2>

      {agents.length === 0 ? (
        <p className="text-gray-600 text-sm py-8 text-center">
          等待启动...
        </p>
      ) : (
        <div className="space-y-2">
          {agents.map((a) => (
            <div
              key={a.id}
              className={`bg-gray-800/50 border ${statusColors[a.status] || "border-gray-700"} rounded p-3 transition-colors`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-200">
                  {statusIcons[a.status] || "❓"} {a.name}
                </span>
                <span className="text-xs text-gray-500">{a.status}</span>
              </div>
              {a.current_challenge && (
                <p className="text-xs text-gray-500 mt-1 truncate">
                  当前：{a.current_challenge}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
