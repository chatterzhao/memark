---
name: memark-installer
description: Production installer skill that bootstraps MemArk into a user-level runtime, installs the MemArk skill bundle into Codex or Claude, and verifies MemPalace plus Graphify are ready.
---

# MemArk Installer Skill

这是正式用户入口，不是开发阶段临时试装说明。

本 Skill 的目标是：

- 把 `MemArk` 安装到用户级运行时目录
- 让 `MemArk` 再安装 `MemPalace` 与 `Graphify`
- 把 `MemArk` 的运行时 skill bundle 安装到 AI 工具的 skill 目录
- 最后用 `memark doctor` 验证运行时与 skill bundle 都可用

如果要做开发期反复重装、隔离验收、假 `HOME` 测试，改看 [`skill-dev.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/skill-dev.md)。

## 重要边界

- `MemPalace` 负责记忆存储与检索
- `Graphify` 负责图谱、报告、wiki、obsidian 等产物
- `MemArk` 当前是桥接与治理层
- 本 Skill 只负责安装 `MemArk` 及其上游依赖，并把运行时 skill bundle 放到用户 AI 工具目录

不要把本 Skill 说成：

- 项目接入器
- 后台监控器
- 自动项目注册器
- 自动晋升与自动编图器

## 默认目标

当用户要求安装时，只完成下面几件事：

1. 确认当前 AI 平台是 `codex`、`claude` 或需要 `all`
2. 用 Python 创建或重建用户级 `MemArk` runtime venv
3. 在该 venv 里安装：
   - 当前 `MemArk` 仓库
   - `mempalace`
   - `graphifyy`
4. 将 `MemArk` 运行时 skill bundle 写入：
   - Codex: `~/.agents/skills/memark/`
   - Claude: `~/.claude/skills/memark/`
5. 用安装后的 `memark doctor` 验证：
   - runtime venv
   - `memark`
   - `mempalace`
   - `graphify`
   - skill bundle
6. 报告真实安装路径

默认不要做：

- `memark project-set`
- `memark projects-run`
- `memark automation-run`
- `mempalace mine`
- `graphify codex install`
- `graphify claude install`
- 手写目录级配置
- 假设安装后已经完成项目接入

要特别明确：

- `memark install` 可以在任何目录执行
- 它不要求当前目录是项目目录
- 它也不会自动替某个项目执行 `memark init`
- 安装完成只代表这台机器有了可用 runtime，不代表任何项目已经接入

如果用户接着问"新项目怎么接"，再切到项目接入说明：

1. 在项目目录下执行 `memark init . --auto`，一键完成：创建 workspace、注册项目、安装调度、跑一轮 cycle
2. 如果需要逐步控制，则分步执行：`memark init` → `memark project-set` → `memark service-install` → `memark automation-run`
3. 交互式 `memark init` 会提示按 `Ctrl+C` 退出后用 `--auto` 完成免交互设置
4. 当前命令面每项能力只保留一个唯一正式命令名，不要自己发明缩写或别名

## 已确认的上游事实

官方仓库：

- `MemPalace`: <https://github.com/milla-jovovich/mempalace>
- `Graphify`: <https://github.com/safishamsi/graphify>

上游 README 可直接确认的基础安装命令：

```bash
pip install mempalace
pip install graphifyy
```

`MemPalace` 常见命令：

```bash
mempalace init <dir>
mempalace mine <dir>
mempalace status
```

`Graphify` 常见命令：

```bash
graphify --help
graphify query "<question>" --graph graphify-out/graph.json
```

额外注意：

- 这版 `MemArk` 安装器不依赖 `graphify codex install` 或 `graphify claude install`
- `MemArk` 自己会安装它自己的 skill bundle
- `Graphify` 仍由 `MemArk` runtime venv 提供 CLI 能力
- `MemPalace` 与 `Graphify` 仍然是 Python 包，因此无论 `MemArk` 将来是否换语言，当前安装闭环都仍然需要 Python

## 跨平台安装原则

必须考虑：

- Windows
- macOS
- Linux

优先级：

- Linux / macOS：优先 `python3`
- Windows：优先 `py`
- 如果不可用，再退回 `python`

不要默认：

- 直接装系统 Python
- 使用 `--break-system-packages`
- 假设 `pip install` 到系统环境一定成功
- 假设用户已经把 `memark` 加入 PATH

## 生产安装流程

生产安装依赖一个"临时 bootstrap Python 环境"，因为首次执行时用户机器上还没有 `memark` 命令。

执行原则：

1. 在仓库根目录创建一个临时 bootstrap venv
2. 在 bootstrap venv 中安装当前仓库
3. 用 bootstrap venv 执行 `python -m memark install`
4. 验证安装后真实 runtime 的 `memark doctor`
5. 可选清理 bootstrap venv

额外约束：

- `MemArk` runtime 只支持 `Python 3.10` 到 `3.13`
- 不要显式传 `--python-command python3`，除非你已经确认那个 `python3` 落在支持范围内
- 正常情况下让 `memark install` 自动挑选兼容 runtime Python 即可
- 如果系统默认 `python3` 是 `3.14+`，bootstrap 仍可用，但 runtime 必须落到 `3.13`、`3.12`、`3.11` 或 `3.10`

### Linux / macOS 示例

```bash
python3 -m venv .memark-bootstrap
.memark-bootstrap/bin/python -m pip install --upgrade pip
.memark-bootstrap/bin/python -m pip install .
.memark-bootstrap/bin/python -m memark install --platform codex --source-spec "$(pwd)"
~/.memark/venv/bin/memark doctor --platform codex
```

如果要同时安装到 `Codex` 和 `Claude`：

```bash
.memark-bootstrap/bin/python -m memark install --platform all --source-spec "$(pwd)"
~/.memark/venv/bin/memark doctor --platform all
```

### Windows 示例

```powershell
py -m venv .memark-bootstrap
.memark-bootstrap\Scripts\python -m pip install --upgrade pip
.memark-bootstrap\Scripts\python -m pip install .
.memark-bootstrap\Scripts\python -m memark install --platform codex --source-spec "%CD%"
%USERPROFILE%\.memark\venv\Scripts\memark doctor --platform codex
```

如果 `doctor` 只报 `missing mempal executable in PATH`，要这样理解：

- 这不阻塞默认 `mempalace` 路径
- 这只说明当前机器还不能使用 `mem_tool=mempal`
- 需要额外安装 `mempal` 后，`mempal` 可插拔路径才算就绪

## 已实现的安装结果

至少确认：

- 用户级 runtime 在 `~/.memark/venv/`
- runtime 内存在：
  - `memark`
  - `mempalace`
  - `graphify`
- 已安装 `MemArk` skill bundle：
  - `~/.agents/skills/memark/`
  - `~/.claude/skills/memark/`
- skill bundle 至少包含：
  - `SKILL.md`
  - `project.md`
  - `doctor.md`
  - `bin/memark`
  - `bin/memark.cmd`
  - `manifest.json`
- `memark doctor` 可通过

## 输出要求

完成后应明确报告：

- `MemArk home` 绝对路径
- runtime venv 绝对路径
- `mempalace` 可执行文件路径
- `graphify` 可执行文件路径
- `memark` 可执行文件路径
- skill bundle 安装到哪个平台目录
- `doctor` 是否通过

## 安装后默认使用方式

安装完成后，运行时 `MemArk` skill bundle 应指导 AI 采用下面的消费顺序：

1. 需要历史讨论与上下文时，优先 `mempalace search` / `mempalace wake-up`
2. 需要读晋升后的项目知识时，优先 `memark query "<topic>" --workspace <workspace> --project <name>`
3. 需要看代码结构和图谱导航时，再使用 `Graphify` 的 report / query
4. 需要刷新当前项目的 mixed-corpus 图时，优先 `memark build --workspace <workspace> --project <name>`
5. `MemArk` 自己的入口默认优先直接走 CLI，而不是 slash；这些 CLI 入口设计目标是免交互、自动批准、适合 AI 自动执行
6. 如果任务本身是 slash-only 语义，或调用方明确要求 slash 语法，再走 `memark slash --workspace <workspace> /graphify <workspace-or-corpus> --update`
7. 只有任务明确要求走上游 `Graphify` skill / AGENTS/hooks 互操作时，才运行 `memark graphify-handoff --workspace <workspace> --project <name>`
8. 如果需要先判断当前 `MemArk` 已支持哪些 slash adapter，先运行 `memark slash --catalog --json`
9. 如果任务语义更接近"读取当前项目统一上下文"，优先 `memark context --workspace <workspace> --project <name>`；只有 slash-only 时才用 `memark slash --workspace <workspace> /context <workspace> --no-refresh --json`
10. 如果任务语义更接近"读取当前阶段、阻塞项、下一步"，优先 `memark milestones --workspace <workspace> --json`；只有 slash-only 时才用 `memark slash --workspace <workspace> /milestones <workspace> --json`
11. 如果任务语义更接近"读取当前项目状态与 graphify corpus 状态"，优先 `memark status --workspace <workspace> --json`；只有 slash-only 时才用 `memark slash --workspace <workspace> /status <workspace> --json`
12. 如果任务语义更接近"在本地 corpus 里直接搜主题"，优先 `memark query "<topic>" --workspace <workspace> --project <name>`；只有 slash-only 时才用 `memark slash --workspace <workspace> /query <terms...> --json`
13. 如果任务语义更接近"读取最近自动化周期状态"，优先 `memark automation-status --workspace <workspace> --json`；只有 slash-only 时才用 `memark slash --workspace <workspace> /automation-status <workspace> --json`
14. 如果任务语义更接近"读取或记录 mixed-corpus graph proof"，优先 `memark graphify-proof --workspace <workspace> --json`；只有 slash-only 时才用 `memark slash --workspace <workspace> /graphify-proof <workspace> --json`
15. 不要对现有正式命令再造缩写；如果未来要新增更短命令，应该在设计时直接定为唯一正式名，而不是并存双入口

当前不要把安装结果表述成：

- promoted markdown 已自动进入 `Graphify` 图
- 安装后任何项目都已自动接入 `MemArk`

## 何时切到开发版

如果需要开发期的重置式安装测试与隔离验收，改读 [`skill-dev.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/skill-dev.md) 再继续。
