# DeepAgents in Action · Task 1

第 1–2 章作业：**我的第一个工具 Agent**（目标档次：Advanced 挑战级）

**打卡记录 → [`deepagents-practice/CHECKIN.md`](deepagents-practice/CHECKIN.md)**

## 目录

```
deepagents-practice/          Lite 部分
  step01_tool.py              用 @tool 定义工具，检查工具对象的 name / description / args
  step02_agent_loop.py        create_agent 跑通 human → ai → tool → ai 四段消息
  step03_virtual_fs.py        第一个 Deep Agent（create_deep_agent），9 个工具
  CHECKIN.md                  打卡记录（五段式）

my_deepagent/                 Basic / Advanced 部分
  由 agentseek create 的 deepagents/default 模板生成
  src/my_deepagent/demo_binding.py    新增自定义工具 count_num，挂进 tools=[]
  .agentseek/lifecycle.toml           声明 AG-UI 网关的启动命令与健康检查
```

## 运行

### Lite：三个实验脚本

不需要 API Key（用的是脚本模型）。

```powershell
cd deepagents-practice
uv sync
.\.venv\Scripts\python.exe step01_tool.py
.\.venv\Scripts\python.exe step02_agent_loop.py
.\.venv\Scripts\python.exe step03_virtual_fs.py
```

### Basic：启动主应用（AG-UI 网关）

需要真实模型和 API Key。

```powershell
cd my_deepagent
cp .env.example .env     # 填入模型、API Key、LangSmith 配置
uv sync
agentseek dev            # 读取 .agentseek/lifecycle.toml，在 18088 端口起网关
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:18088/agent/health
```

**注意**：Windows 上必须在 `.env` 里显式写 `BUB_AG_UI_PATH=/agent`。
不写的话 `POST /agent` 会返回 404 —— 原因见 `.env.example` 里的注释。

### Advanced：发一条真实请求

网关起来之后，向 `http://127.0.0.1:18088/agent` 发 `POST`，请求体是 AG-UI 的 `RunAgentInput`：

```json
{
  "thread_id": "t-1",
  "run_id": "r-1",
  "messages": [
    {"id": "m-1", "role": "user", "content": "用 count_num 统计这句话的字符数：今天天气不错"}
  ]
}
```

响应是 SSE 流。完整调用链、输入对比与 Trace 证据见 [打卡报告](deepagents-practice/CHECKIN.md)。
