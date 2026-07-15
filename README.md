# ⚡ AutoPwn

多 Agent CTF 自动解题平台。扫题目 → 派 agent → 解 flag，全自动。

[![Python](https://img.shields.io/badge/python-3.13-blue)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/next.js-16-black)](https://nextjs.org/)
[![status](https://img.shields.io/badge/status-MVP-brightgreen)](https://github.com/Ile-creater/AutoPwn)

---

## 怎么跑

开两个终端：

```bash
# 终端 1 — 后端
cd AutoPwn
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 终端 2 — 前端
cd AutoPwn/frontend
npm install
npm run dev
```

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
  ├─ 逐个启动子进程 agent
  ├─ 捕获 stdout → 实时推到前端
  └─ 检测到 FLAG:xxx → 标记 solved → 下一题

agent 子进程
  ├─ 读 challenge.txt
  ├─ 嗅探编码类型 (base64 / hex / base32 / base85 / rot13)
  ├─ 递推解码，最多 5 层
  └─ 打印 FLAG:xxx 到 stdout
```

## 目录结构

```
AutoPwn/
├── agents/              # 解题 agent
│   ├── base_agent.py    #   嗅探、解码、HTTP 请求公共方法
│   ├── crypto_agent.py  #   密码/编码类
│   └── web_agent.py     #   Web 类：注释挖掘、目录扫描、隐藏字段
├── backend/             # FastAPI
│   ├── main.py          #   WebSocket + 路由
│   ├── orchestrator.py  #   扫题、排序、派发
│   └── agent_runner.py  #   启子进程、抓输出
├── frontend/            # Next.js 仪表盘
│   └── components/      #   ChallengeList / AgentPanel / LiveTerminal
├── challenges/          # CTF 题目
└── workspace/           # agent 临时工作目录
```

## TODO

- [x] Web Agent — requests + HTML 分析，注释/隐藏字段/目录扫描/backup 探测
- [ ] Binary Agent — pwntools / gdb 处理逆向
- [ ] 多 Agent 并行 — asyncio.gather 同时解题
- [ ] 接 Ollama — 替换 sniff() 的硬编码模式匹配
- [ ] Docker 沙箱 — agent 不该在宿主机随便跑

## License

MIT — 随便用，出事别找我。
