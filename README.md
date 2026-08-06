# ⚡ AutoPwn

多 Agent CTF 自动解题平台 — 扫题、派 agent、解 flag，一站式全自动。

[![Python](https://img.shields.io/badge/python-3.13-blue)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/next.js-16-black)](https://nextjs.org/)
[![Ollama](https://img.shields.io/badge/Ollama-qwen2.5:3b-orange)](https://ollama.com)
[![status](https://img.shields.io/badge/status-v2.0-emerald)](https://github.com/Ile-creater/AutoPwn)

---

## 怎么跑

```bash
setup.bat    # 首次：一键装依赖
start.bat    # 每次：双终端自动启动
```

浏览器打开 **http://localhost:3000**，点 **start**。

> 或者手动：`python -m uvicorn backend.main:app --port 8000` + `cd frontend && npm run dev`

---

## 怎么加新题

```
challenges/
└── 002_your_challenge/
    ├── challenge.json  → {"id":"xxx","title":"xxx","type":"crypto|web|bin|misc|pwn|ai","difficulty":1-5}
    └── challenge.txt   → 题目内容 / 附件base64 / URL
```

或者直接在仪表盘点 **📤 Submit Challenge**，选类型填 URL/附件/提示，提交即入池。

---

## 原理

```
仪表盘 ←→ WebSocket ←→ FastAPI (Orchestrator) → asyncio.gather 并行
                         │
         ┌───────────────┼───────────────┐
    CryptoAgent  WebAgent  BinAgent  MiscAgent  AIAgent
    (编解码)   (Web漏洞  (逆向)    (杂项)   (prompt注入)
                +PentAGI侦察+XSS Bot)
                         │
              llm.py → Ollama / Claude / DeepSeek / Qwen / OpenAI
              knowledge.py → Jaccard 相似度匹配攻击链
```

**解题流程：**
1. 硬编码正则扫描（0.1s，覆盖常见编码/漏洞）
2. 知识库匹配（查历史成功攻击链）
3. Ollama 本地推理（qwen2.5:3b，免费）
4. 硬编码全失败 → AI 推理循环接管（LLM 规划→执行→看结果→调整，最多5轮）

---

## 目录结构

```
AutoPwn/
├── agents/                  # 5 个解题 agent
│   ├── base_agent.py        #   基类: 编解码/HTTP/LLM调用/知识库/漏洞搜索/执行监控
│   ├── crypto_agent.py      #   编码类: 链式解码 + kb优先
│   ├── web_agent.py         #   Web类: SQL注入/XSS/SSTI/LFI/RCE + PentAGI侦查 + XSS Bot
│   ├── bin_agent.py         #   逆向类: strings/checksec/r2/objdump
│   ├── misc_agent.py        #   杂项类: binwalk/foremost/stego/zip嵌套
│   └── ai_agent.py          #   AI安全: prompt injection/jailbreak payload
├── backend/                 # FastAPI
│   ├── main.py              #   WebSocket + /api/submit + /api/writeup + /api/kb + /api/llm
│   ├── orchestrator.py      #   扫题→排序→asyncio.gather 并行派发, 2阶段管道
│   ├── agent_runner.py      #   子进程/Docker启动器, 120s超时, 自动writeup+KB记录
│   ├── llm.py               #   多模型适配: Ollama/Claude/DeepSeek/Qwen/OpenAI/自定义
│   └── knowledge.py         #   CTF知识库: Jaccard匹配, 攻击链特征提取
├── frontend/                # Next.js 仪表盘 (白底高级风)
│   └── components/          #   SubmitForm/ChallengeList/AgentPanel/LiveTerminal
│                            #   ToolPanel/KBPanel/StatsPanel/ModelPicker
├── challenges/              # CTF 题目 (4道示例)
├── docker/                  # Docker沙箱: Dockerfile + build.bat
└── workspace/               # agent 临时工作目录
```

---

## 功能清单

| 功能 | 说明 |
|------|------|
| 🕷️ PentAGI 侦查 | CMS指纹(15种)/robots解析/技术栈检测/Sploitus漏洞搜索 |
| ⛓️ 知识库 | Jaccard匹配历史攻击链, 解完自动记录 |
| 🤖 AI 推理循环 | LLM接管: 规划→执行→看结果→调整, 5轮迭代 |
| 🧠 多模型切换 | 前端下拉框选 Ollama/Claude/DeepSeek/Qwen/OpenAI/自定义 |
| 📊 统计面板 | SVG饼图(通过率)+柱状图(按类型分布) |
| ▶️ 解题回放 | solved题点replay重放完整日志 |
| 📄 自动Writeup | 解完自动生成report.md, 含工具链+耗时+完整过程 |
| 🐳 Docker沙箱 | 前端可选, crypto/bin断网/web放行, 512M/1核 |
| 🔧 工具链面板 | 检测 rizin/Ollama/Docker/pwntools/binwalk/exiftool 状态 |
| ⚡ 并行解题 | asyncio.gather 全部题一起跑, 互不阻塞 |
| ⏱️ 超时保护 | 120s超时自动kill, 同类攻击失败3次换策略 |
| 🛡️ 错误恢复 | LLM重试/subprocess异常/脚本缺失, 全部捕获透传 |

---

## AI 推理

内置 LLM 适配层，支持 **6 个 provider 前后端实时切换**：

| Provider | 默认模型 | 费用 |
|----------|---------|------|
| Ollama | qwen2.5:3b | 免费（本地） |
| DeepSeek | deepseek-chat | ¥2/1M tokens |
| 通义千问 | qwen-turbo | 免费额度 |
| Claude | claude-opus-4-8 | $5/1M tokens |
| OpenAI | gpt-4o-mini | $0.15/1M tokens |
| 自定义 | 任意 OpenAI 兼容 | — |

Agent 启动时显示 `[AI]` 或 `[basic]`。LLM 不在时自动降级为硬编码规则。

---

## License

MIT — 随便用，出事别找我。
