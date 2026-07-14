"use client";

import { useState, useEffect, useRef } from "react";
import ChallengeList from "@/components/ChallengeList";
import AgentPanel from "@/components/AgentPanel";
import LiveTerminal from "@/components/LiveTerminal";

export default function Home() {
  const [sock, setSock] = useState<WebSocket | null>(null);
  const [online, setOnline] = useState(false);
  const [chals, setChals] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const tailRef = useRef<HTMLDivElement>(null);

  const pushLog = (s: string) => setLogs((p) => [...p.slice(-200), s]);

  // scroll to bottom on new log
  useEffect(() => { tailRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  // websocket guts
  function hookup() {
    const ws = new WebSocket("ws://localhost:8000/ws");
    ws.onopen = () => {
      pushLog("[sys] ws connected");
      setOnline(true);
      ws.send(JSON.stringify({ type: "scan" }));
    };
    ws.onmessage = (e) => {
      const d = JSON.parse(e.data);

      if (d.type === "scan_result") {
        setChals(d.challenges || []);
        pushLog(`[scan] ${d.challenges?.length || 0} 个题`);
      } else if (d.type === "agent_update") {
        setAgents((old) => {
          const hit = old.find((a) => a.id === d.agent.id);
          return hit ? old.map((a) => (a.id === d.agent.id ? d.agent : a)) : [...old, d.agent];
        });
      } else if (d.type === "agent_log") {
        pushLog(`[${d.agent_name || "?"}] ${d.line}`);
      } else if (d.type === "challenge_update") {
        setChals((old) => old.map((c) => (c.id === d.challenge.id ? d.challenge : c)));
        if (d.challenge.status === "solved") {
          pushLog(`[√] ${d.challenge.title} solved! ${d.challenge.flag}`);
        }
      } else if (d.type === "all_done") {
        pushLog("[sys] 全搞定了");
        setBusy(false);
      } else if (d.type === "error") {
        pushLog(`[!] ${d.message}`);
      }
    };
    ws.onclose = () => {
      pushLog("[sys] ws 断了，3s 重连...");
      setOnline(false);
      setTimeout(hookup, 3000);
    };
    setSock(ws);
  }

  useEffect(() => {
    hookup();
    return () => sock?.close();
  }, []);

  const kickoff = () => {
    setBusy(true);
    pushLog("[sys] go!");
    sock?.send(JSON.stringify({ type: "start" }));
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* top bar */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-green-400">⚡ AutoPwn</h1>
          <span className="text-xs text-gray-600">multi-agent ctf solver</span>
        </div>
        <div className="flex items-center gap-3">
          <span className={`inline-block w-2 h-2 rounded-full ${online ? "bg-green-400" : "bg-red-500"}`} />
          <span className="text-xs text-gray-500">{online ? "online" : "offline"}</span>
          <button
            onClick={kickoff}
            disabled={!online || busy}
            className={`px-4 py-2 rounded text-sm font-bold ${busy || !online ? "bg-gray-700 text-gray-500" : "bg-green-600 hover:bg-green-500 text-white"}`}
          >
            {busy ? "running..." : "start"}
          </button>
        </div>
      </div>

      {/* challenges + agents */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <div className="lg:col-span-2"><ChallengeList challenges={chals} /></div>
        <div><AgentPanel agents={agents} /></div>
      </div>

      {/* terminal */}
      <LiveTerminal lines={logs} logEndRef={tailRef} />
    </div>
  );
}
