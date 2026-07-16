# ⚡ AutoPwn

多 Agent CTF 自动解题平台。扫题目 → 派 agent → 解 flag，全自动。🚩

[![Python](https://img.shields.io/badge/python-3.13-blue)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/next.js-16-black)](https://nextjs.org/)
[![status](https://img.shields.io/badge/status-MVP-brightgreen)](https://github.com/Ile-creater/AutoPwn)

---

## 怎么跑

开两个终端：

```bash
# 0. 构建 Docker 沙箱（首次）
cd AutoPwn
docker build -t auto-pwn-agent -f docker\Dockerfile .

# 终端 1 — 后端
cd AutoPwn
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 终端 2 — 前端
cd AutoPwn/frontend
npm install
npm run dev
```

> 没装 Docker 也没事，agent_runner 会自动退回子进程模式。

浏览器打开 **http://localhost:3000**，点 **start**。

---

## 怎么加新题

在 `challenges/` 下建一个文件夹，放两个文件：

```
challenges/
└── 002_your_challenge/
    ├── challenge.json   ← {"id":"002_your_challenge","title":"Hex 套娃","type":"crypto","difficulty":2}
    └── challenge.txt    ← 题目内容（编码后的密文）
```

| 字段 | 说明 |
|------|------|
| `id` | 唯一标识 |
| `title` | 题目名字 |
| `type` | crypto / web / bin / misc / ai |
| `difficulty` | 1~5，数字越小越简单 |

然后点一次 **start**，orchestrator 会自动扫到新题并按难度排。

---

## 原理

```
浏览器 (仪表盘)
  ↕ WebSocket
FastAPI (主控)
  ├─ 扫 challenges/ 目录，按 difficulty 排序
  ├─ asyncio.gather 全部题一起跑
  ├─ 3 个 subprocess → stdout 实时推到终端
  └─ 检测到 FLAG:xxx → 标记 solved

  CryptoAgent         WebAgent            BinAgent
  (base64/hex/rot13)  (HTML/注释/扫描)   (strings/checksec/objdump)
```

## 目录结构

```
AutoPwn/
├── agents/              # 解题 agent
│   ├── base_agent.py    #   嗅探、解码、HTTP 请求公共方法
│   ├── crypto_agent.py  #   密码/编码类
│   ├── web_agent.py     #   Web 类：注释挖掘、目录扫描、隐藏字段
│   ├── bin_agent.py     #   逆向类：pwntools / strings / checksec / ELF分析
│   └── misc_agent.py    #   杂项类：file/stego/zip/元数据/归档分析
├── backend/             # FastAPI
│   ├── main.py          #   WebSocket + 路由
│   ├── orchestrator.py  #   扫题、排序、派发
│   └── agent_runner.py  #   Docker 沙箱启动器（没装则退回 subprocess）
├── docker/              # 沙箱镜像
│   ├── Dockerfile       #   python:slim + binwalk + pwntools + agent
│   └── build.bat        #   一键构建
├── frontend/            # Next.js 仪表盘
│   └── components/      #   ChallengeList / AgentPanel / LiveTerminal
├── challenges/          # CTF 题目
└── workspace/           # agent 临时工作目录
```

## TODO

- [x] Web Agent — requests + HTML 分析，注释/隐藏字段/目录扫描/backup 探测
- [x] Binary Agent — pwntools + strings + checksec + objdump + ELF 分析
- [x] 多 Agent 并行 — asyncio.gather 一起跑，题目互不阻塞
- [x] Docker 沙箱 — 每个 agent 独立容器，crypto/bin 断网，web 放行，512M/1核
- [x] Misc Agent — 文件分离/stego/zip/归档/元数据/binwalk/foremost
- [x] 接 Ollama — AI 推理编码类型/攻击方向/二进制分析，模型不在自动降级

## AI 推理

所有 agent 都支持本地 Ollama 推理，**装了就自动用，不装也不影响**。

```bash
# 安装 Ollama
winget install Ollama.Ollama
# 拉个模型（推荐 qwen2.5:3b，够小够快）
ollama pull qwen2.5:3b
```

Agent 启动时会显示 `[AI]` 或 `[basic]` 告知当前模式。LLM 不在时自动降级为硬编码规则。

## License

MIT — 随便用，出事别找我。
