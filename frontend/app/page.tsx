"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import ChallengeList from "@/components/ChallengeList";
import AgentPanel from "@/components/AgentPanel";
import LiveTerminal from "@/components/LiveTerminal";

interface Challenge {
  id: string;
  title: string;
  type: string;
  difficulty: number;
  status: "pending" | "running" | "solved" | "failed";
  flag?: string;
}

interface AgentState {
  id: string;
  name: string;
  status: "idle" | "running" | "done";
  current_challenge?: string;
}

export default function Home() {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [agents, setAgents] = useState<AgentState[]>([]);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [solving, setSolving] = useState(false);
  const logEndRef = useRef<HTMLDivElement>(null);

  const addLog = useCallback((msg: string) => {
    setLogLines((prev) => [...prev.slice(-200), msg]);
  }, []);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logLines]);

  const connect = useCallback(() => {
    const socket = new WebSocket("ws://localhost:8000/ws");
    socket.onopen = () => {
      addLog("[系统] WebSocket 已连接");
      setConnected(true);
      socket.send(JSON.stringify({ type: "scan" }));
    };
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleMessage(data);
    };
    socket.onclose = () => {
      addLog("[系统] WebSocket 断开，3 秒后重连...");
      setConnected(false);
      setTimeout(connect, 3000);
    };
    setWs(socket);
  }, []);

  const handleMessage = useCallback((data: any) => {
    switch (data.type) {
      case "scan_result":
        setChallenges(data.challenges || []);
        addLog(`[扫描] 发现 ${data.challenges?.length || 0} 个题目`);
        break;
      case "agent_update":
        setAgents((prev) => {
          const exists = prev.find((a) => a.id === data.agent.id);
          if (exists) {
            return prev.map((a) => (a.id === data.agent.id ? data.agent : a));
          }
          return [...prev, data.agent];
        });
        break;
      case "agent_log":
        addLog(`[${data.agent_name || "Agent"}] ${data.line}`);
        break;
      case "challenge_update":
        setChallenges((prev) =>
          prev.map((c) => (c.id === data.challenge.id ? data.challenge : c))
        );
        if (data.challenge.status === "solved") {
          addLog(`[✓] ${data.challenge.title} 已解出！flag: ${data.challenge.flag}`);
        }
        break;
      case "all_done":
        addLog("[系统] 所有题目处理完毕！");
        setSolving(false);
        break;
      case "error":
        addLog(`[错误] ${data.message}`);
        break;
    }
  }, [addLog]);

  useEffect(() => {
    connect();
    return () => ws?.close();
  }, []);

  const startSolving = () => {
    setSolving(true);
    addLog("[系统] 开始解题...");
    ws?.send(JSON.stringify({ type: "start" }));
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-green-400">
            ⚡ CTF Auto-Solver
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            AI-Powered Challenge Solver
          </p>
        </div>
        <div className="flex items-center gap-4">
          <span
            className={`inline-block w-2 h-2 rounded-full ${
              connected ? "bg-green-400" : "bg-red-500"
            }`}
          />
          <span className="text-sm text-gray-400">
            {connected ? "已连接" : "未连接"}
          </span>
          <button
            onClick={startSolving}
            disabled={!connected || solving}
            className={`px-4 py-2 rounded text-sm font-bold transition ${
              solving || !connected
                ? "bg-gray-700 text-gray-500 cursor-not-allowed"
                : "bg-green-600 hover:bg-green-500 text-white"
            }`}
          >
            {solving ? "解题中..." : "开始解题"}
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <div className="lg:col-span-2">
          <ChallengeList challenges={challenges} />
        </div>
        <div>
          <AgentPanel agents={agents} />
        </div>
      </div>

      {/* Terminal */}
      <LiveTerminal lines={logLines} logEndRef={logEndRef} />
    </div>
  );
}
