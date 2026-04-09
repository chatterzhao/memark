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
- `mempalace mine`
- `graphify codex install`
- `graphify claude install`
- 手写项目级配置
- 假设安装后已经完成项目接入

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

生产安装依赖一个“临时 bootstrap Python 环境”，因为首次执行时用户机器上还没有 `memark` 命令。

执行原则：

1. 在仓库根目录创建一个临时 bootstrap venv
2. 在 bootstrap venv 中安装当前仓库
3. 用 bootstrap venv 执行 `python -m memark install`
4. 验证安装后真实 runtime 的 `memark doctor`
5. 可选清理 bootstrap venv

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

## 何时切到开发版

如果需要开发期的重置式安装测试与隔离验收，改读 [`skill-dev.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/skill-dev.md) 再继续。
