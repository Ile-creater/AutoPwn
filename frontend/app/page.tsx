"use client";

import { useState, useEffect, useRef } from "react";
import ChallengeList from "@/components/ChallengeList";
import AgentPanel from "@/components/AgentPanel";
import LiveTerminal from "@/components/LiveTerminal";
import SubmitForm from "@/components/SubmitForm";
import ToolPanel from "@/components/ToolPanel";
import KBPanel from "@/components/KBPanel";
import StatsPanel from "@/components/StatsPanel";
import ModelPicker from "@/components/ModelPicker";

export default function Home() {
  const [sock, setSock] = useState<WebSocket | null>(null);
  const [online, setOnline] = useState(false);
  const [chals, setChals] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [useDocker, setUseDocker] = useState(false);
  const [tools, setTools] = useState<any[]>([]);
  const tailRef = useRef<HTMLDivElement>(null);

  const pushLog = (s: string) => setLogs((p) => [...p.slice(-200), s]);

  useEffect(() => { tailRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  const replayLog = async (cid: string) => {
    const api = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
    pushLog(`[replay] ${cid}`);
    try {
      const r = await fetch(`${api}/api/log/${cid}`);
      if (r.ok) { (await r.text()).split("\n").forEach((l: string) => pushLog(l)); }
      else pushLog(`[replay] 404`);
    } catch { pushLog("[replay] fail"); }
  };

  function hookup() {
    const api = (process.env.NEXT_PUBLIC_API_BASE || "").replace("http", "ws");
    const ws = new WebSocket(`${api}/ws`);
    ws.onopen = () => {
      pushLog("[sys] connected");
      setOnline(true);
      ws.send(JSON.stringify({ type: "scan" }));
    };
    ws.onmessage = (e) => {
      const d = JSON.parse(e.data);
      if (d.type === "scan_result") {
        setChals(d.challenges || []);
      } else if (d.type === "agent_update") {
        setAgents((old) => {
          const hit = old.find((a) => a.id === d.agent.id);
          return hit ? old.map((a) => (a.id === d.agent.id ? d.agent : a)) : [...old, d.agent];
        });
      } else if (d.type === "agent_log") {
        pushLog(`[${d.agent_name || "?"}] ${d.line}`);
      } else if (d.type === "challenge_update") {
        setChals((old) => old.map((c) => (c.id === d.challenge.id ? d.challenge : c)));
        if (d.challenge.status === "solved") pushLog(`✓ ${d.challenge.title} → ${d.challenge.flag}`);
      } else if (d.type === "all_done") {
        pushLog("[sys] done");
        setBusy(false);
      } else if (d.type === "new_challenge") {
        setChals((old) => [...old, d.challenge]);
      } else if (d.type === "tools_status") {
        setTools(d.tools || []);
      }
    };
    ws.onclose = () => { setOnline(false); setTimeout(hookup, 3000); };
    setSock(ws);
  }

  useEffect(() => { hookup(); return () => sock?.close(); }, []);

  const kickoff = () => {
    setBusy(true);
    sock?.send(JSON.stringify({ type: "start", use_docker: useDocker }));
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Top bar */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl">⚡</span>
            <div>
              <h1 className="text-lg font-bold text-gray-900 tracking-tight">AutoPwn</h1>
              <p className="text-xs text-gray-400">multi-agent ctf solver</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <ModelPicker />

            <div className="flex items-center gap-2">
              <span className={`inline-block w-2 h-2 rounded-full ${online ? "bg-emerald-500" : "bg-red-400"}`} />
              <span className="text-xs text-gray-400">{online ? "online" : "offline"}</span>
            </div>

            <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer select-none">
              <input type="checkbox" checked={useDocker} onChange={(e) => setUseDocker(e.target.checked)} className="accent-emerald-600" />
              🐳 sandbox
            </label>

            <button
              onClick={kickoff}
              disabled={!online || busy}
              className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
                busy || !online
                  ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                  : "bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white shadow-sm shadow-emerald-200"
              }`}
            >
              {busy ? "running..." : "start"}
            </button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2 space-y-5">
            <SubmitForm />
            <ChallengeList challenges={chals} onReplayLog={replayLog} />
          </div>
          <div className="space-y-5">
            <AgentPanel agents={agents} />
            <StatsPanel chals={chals} />
            <ToolPanel tools={tools} />
            <KBPanel />
          </div>
        </div>

        <div className="mt-5">
          <LiveTerminal lines={logs} logEndRef={tailRef} />
        </div>
      </main>
    </div>
  );
}
