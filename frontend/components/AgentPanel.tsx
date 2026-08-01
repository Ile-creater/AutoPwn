const stateIcon: any = { idle: "○", running: "◉", done: "●" };
const stateColor: any = { idle: "text-gray-300", running: "text-amber-500 animate-pulse", done: "text-emerald-500" };

export default function AgentPanel({ agents }: { agents: any[] }) {
  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-sm overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-50">
        <h2 className="text-sm font-semibold text-gray-700">
          Agents
          {agents.length > 0 && <span className="text-gray-400 font-normal ml-1.5">· {agents.filter((a: any) => a.status === "running").length} active</span>}
        </h2>
      </div>
      {agents.length === 0 ? (
        <p className="text-sm text-gray-400 py-8 text-center">idle</p>
      ) : (
        <div className="divide-y divide-gray-50">
          {agents.map((a: any) => (
            <div key={a.id} className="px-5 py-3 hover:bg-gray-50/50 transition">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-700 font-medium">{a.name}</span>
                <span className={`text-lg ${stateColor[a.status] || "text-gray-300"}`}>{stateIcon[a.status] || "○"}</span>
              </div>
              {a.current_challenge && <p className="text-xs text-gray-400 mt-1 truncate">{a.current_challenge}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
