# DeepAgents in Action

《Deep Agents 实战》课程作业记录。**每个 Task 一个子目录**，各自带自己的打卡与实验脚本。

| Task | 章节 | 主题 | 打卡 |
| --- | --- | --- | --- |
| Task 1 | 第 1–2 章 | 我的第一个工具 Agent | [打卡记录](deepagents-practice/task01-tool-agent/CHECKIN.md) |
| Task 2 | 第 3 章 | 让成果留在文件里（虚拟文件系统） | [Lite 打卡](deepagents-practice/task02-virtual-file-system/CHECKIN.md) |
| Task 3 | 第 4 章 | 让项目按计划完成（任务规划与 Todo） | [Lite 打卡](deepagents-practice/task03-task-planning/CHECKIN.md) |
| Task 4 | 第 5 章 | 把一项工作交给子 Agent（上下文隔离） | [Lite 打卡](deepagents-practice/task04-subagents/CHECKIN.md) |

## 目录

```
deepagents-practice/                  实验脚本（各 Task 共用同一套环境）
  task01-tool-agent/                  Task 1
    CHECKIN.md                        打卡记录
    step01_tool.py                    用 @tool 定义工具，检查工具对象的 name / description / args
    step02_agent_loop.py              create_agent 跑通 human → ai → tool → ai 四段消息
    step03_virtual_fs.py              第一个 Deep Agent（create_deep_agent），9 个工具
  task02-virtual-file-system/         Task 2（Lite）
    CHECKIN.md                        打卡记录
    step04_vfs.py                     默认后端：文件写进 Agent 状态，磁盘上找不到
    step05_filesystem.py              换成 FilesystemBackend：写入 → 读回 → 修改，产物落磁盘
    agent_workspace/report.md         上述脚本生成的产物（真文件）
  task03-task-planning/               Task 3（Lite）
    CHECKIN.md                        打卡记录
    step06_todo_plan.py               显式启用 TodoListMiddleware，观察计划 pending → completed
  task04-subagents/                   Task 4（Lite）
    CHECKIN.md                        打卡记录
    step07_subagent_delegation.py     声明 researcher 子 Agent，验证消息 / 文件 / 工具集三条边界
  knowledge_notes.md / notes/         跨任务知识点笔记（索引 + 分类正文）
  pyproject.toml / uv.lock            依赖版本已锁死，与课程一致

my_deepagent/                         主应用，由 agentseek create 的 deepagents/default 模板生成
  src/my_deepagent/demo_binding.py    新增自定义工具 count_num，挂进 tools=[]
  .agentseek/lifecycle.toml           声明 AG-UI 网关的启动命令与健康检查
```

## 运行

### Lite：实验脚本

不需要 API Key（用的是脚本模型）。

```powershell
cd deepagents-practice
uv sync
.\.venv\Scripts\python.exe task01-tool-agent\step01_tool.py
.\.venv\Scripts\python.exe task01-tool-agent\step02_agent_loop.py
.\.venv\Scripts\python.exe task01-tool-agent\step03_virtual_fs.py
.\.venv\Scripts\python.exe task02-virtual-file-system\step04_vfs.py
.\.venv\Scripts\python.exe task02-virtual-file-system\step05_filesystem.py
.\.venv\Scripts\python.exe task03-task-planning\step06_todo_plan.py
.\.venv\Scripts\python.exe task04-subagents\step07_subagent_delegation.py
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

响应是 SSE 流。完整调用链、输入对比与 Trace 证据见 [Task 1 打卡报告](deepagents-practice/task01-tool-agent/CHECKIN.md)。
