const icons: any = { idle: "💤", running: "🔄", done: "✅" };
const borderStyle: any = { idle: "border-gray-700", running: "border-yellow-500/50 animate-pulse", done: "border-green-600" };

export default function AgentPanel({ agents }: { agents: any[] }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 h-full">
      <h2 className="text-lg font-bold text-gray-200 mb-3">🤖 Agents</h2>
      {agents.length === 0 ? (
        <p className="text-gray-600 text-sm py-8 text-center">idle...</p>
      ) : (
        <div className="space-y-2">
          {agents.map((a: any) => (
            <div key={a.id} className={`bg-gray-800/50 border ${borderStyle[a.status] || "border-gray-700"} rounded p-3`}>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-200">{icons[a.status] || "❓"} {a.name}</span>
                <span className="text-xs text-gray-500">{a.status}</span>
              </div>
              {a.current_challenge && <p className="text-xs text-gray-500 mt-1 truncate">{a.current_challenge}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
