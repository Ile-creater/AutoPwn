export default function LiveTerminal({ lines, logEndRef }: { lines: string[]; logEndRef: any }) {
  return (
    <div className="bg-[#0a0a0a] border border-gray-800 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 bg-gray-900 border-b border-gray-800">
        <span className="w-3 h-3 rounded-full bg-red-500/70" />
        <span className="w-3 h-3 rounded-full bg-yellow-500/70" />
        <span className="w-3 h-3 rounded-full bg-green-500/70" />
        <span className="text-xs text-gray-500 ml-2">terminal</span>
      </div>
      <div className="p-4 h-64 overflow-y-auto font-mono text-xs leading-relaxed" style={{ backgroundColor: "#0a0a0a" }}>
        {lines.length === 0 ? (
          <p className="text-gray-600">waiting...</p>
        ) : (
          lines.map((l, i) => (
            <div key={i} className="text-green-400/80 whitespace-pre-wrap break-all">{l}</div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}
