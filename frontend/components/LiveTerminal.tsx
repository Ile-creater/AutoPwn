export default function LiveTerminal({ lines, logEndRef }: { lines: string[]; logEndRef: any }) {
  return (
    <div className="bg-gray-900 rounded-xl shadow-sm overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 bg-gray-800/50 border-b border-gray-800">
        <span className="w-2.5 h-2.5 rounded-full bg-red-400/70"></span>
        <span className="w-2.5 h-2.5 rounded-full bg-amber-400/70"></span>
        <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/70"></span>
        <span className="text-xs text-gray-500 ml-2">terminal</span>
      </div>
      <div className="p-4 h-64 overflow-y-auto font-mono text-xs leading-relaxed">
        {lines.length === 0 ? (
          <p className="text-gray-600">waiting...</p>
        ) : (
          lines.map((l: string, i: number) => (
            <div key={i} className="text-emerald-400/80 whitespace-pre-wrap break-all">{l}</div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}
