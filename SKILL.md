---
name: memark-installer
description: Install MemArk — the bridge that automates MemPalace memory and Graphify knowledge graph for any project.
---

# MemArk Installer Skill

**MemArk 自动串联 MemPalace（记忆）和 Graphify（图谱），让项目记忆自动变成可消费的项目知识。**

安装完成后，在任何项目目录下执行 `memark init`，即可一键完成：创建 workspace、注册项目、安装后台调度、运行首轮自动化。

如果要做开发期反复重装、隔离验收，改看 [`skill-dev.md`](<repo-root>/skill-dev.md)。

## 平台支持

当前仅支持 **macOS**。后台调度依赖 `launchd`，后续版本将支持 Linux 和 Windows。

## 两步上手

### 第一步：安装 MemArk

在任意目录执行：

```bash
python3 -m venv .memark-bootstrap
.memark-bootstrap/bin/python -m pip install --upgrade pip
.memark-bootstrap/bin/python -m pip install .
.memark-bootstrap/bin/python -m memark install --platform codex --source-spec "$(pwd)"
memark doctor --platform codex
```

- `--platform codex`：安装到 Codex（`~/.agents/skills/memark/`）
- `--platform claude`：安装到 Claude（`~/.claude/skills/memark/`）
- `--platform all`：同时安装到两者
- 安装后 `memark` 会自动 symlink 到 `~/.local/bin/`

### 第二步：接入项目

在项目根目录执行：

```bash
memark init
```

这一条命令会自动完成：

1. 创建 `.memark/` workspace
2. 注册项目
3. 安装 launchd 后台调度
4. 运行首轮自动化 cycle（同步会话 → 记忆挖掘 → 晋升 → 构建图谱）

如果只想创建 workspace，不装调度、不跑 cycle：

```bash
memark init --no-auto
```

## 安装做了什么

- 用户级 runtime 在 `~/.memark/venv/`
- runtime 内包含：`memark`、`mempalace`、`graphify`
- MemArk skill bundle 写入 AI 工具 skill 目录
- `memark doctor` 可验证所有组件

## 安装后常用命令

- `memark status --workspace . --json` — 查看项目状态
- `memark milestones --workspace . --json` — 查看当前阶段与阻塞项
- `memark context --workspace . --project <name>` — 生成 AI 可消费的项目上下文
- `memark query "<topic>" --workspace . --project <name>` — 搜索项目语料
- `memark automation-run --workspace .` — 手动跑一轮 cycle
- `memark service-status --workspace . --json` — 查看后台调度状态

## 重要边界

- `MemPalace` 负责记忆存储与检索
- `Graphify` 负责图谱、报告、wiki 等产物
- `MemArk` 是桥接与治理层，自动串联两者
- 本 Skill 只负责安装，不负责项目接入（项目接入用 `memark init`）

## 跨平台安装原则

- macOS / Linux：优先 `python3`
- Windows：优先 `py`
- 不要使用 `--break-system-packages`
- `MemArk` runtime 只支持 Python 3.10 到 3.13

## 何时切到开发版

如果需要开发期的重置式安装测试与隔离验收，改读 [`skill-dev.md`](<repo-root>/skill-dev.md)。
