---
name: memark-installer
description: Use this skill when the user wants an AI assistant to install and configure MemPalace and Graphify for MemArk, verify that both upstream tools are available, and explain the next manual CLI steps without pretending MemArk runtime code already exists.
---

# MemArk Installer Skill

本 Skill 只负责一件事：

安装并配置 `MemPalace` 与 `Graphify`，让后续的 `MemArk` 桥接工作有可用的上下游。

它不是运行期桥接器，也不是文档整理器。

## 目标

当用户要求安装时，这个 Skill 应该帮助 AI 助手完成：

1. 安装 `MemPalace`
2. 安装 `Graphify`
3. 验证两者 CLI 是否可用
4. 创建后续桥接所需的基本目录
5. 告诉用户下一步该如何手动运行

它不负责：

- 持续同步
- 自动监控
- 假装 `MemArk` 已经有完整 CLI
- 编造不存在的 `MemPalace` 增量接口

## 已确认的上游事实

以下内容来自当前公开仓库：

- `MemPalace` 官方仓库：<https://github.com/milla-jovovich/mempalace>
- `Graphify` 官方仓库：<https://github.com/safishamsi/graphify>

当前可直接依据上游 README 使用的安装路径是：

### MemPalace

```bash
pip install mempalace
```

常见初始化与使用命令：

```bash
mempalace init <dir>
mempalace mine <dir>
mempalace status
```

### Graphify

```bash
pip install graphifyy
graphify install
```

常见使用命令：

```bash
graphify .
graphify ./raw --update
graphify ./raw --wiki
graphify ./raw --mcp
```

## 跨平台安装原则

这个 Skill 必须同时考虑：

- Windows
- macOS
- Linux

安装时不要默认：

- 用户只有 `pip`
- 用户 shell 是 bash
- `python` 一定指向正确版本
- 安装后可执行文件一定立刻在 PATH 中

更稳的主路径是：

- Linux / macOS：优先 `python3 -m pip`
- Windows：优先 `py -m pip`
- 如果这些都不可用，再退回 `python -m pip` 或 `pip`

如果系统 Python 返回 `externally-managed-environment` 之类错误，不要强行往系统环境安装。

此时应改走：

- 项目虚拟环境 `python3 -m venv .venv`
- 或用户自己的虚拟环境

不要默认使用 `--break-system-packages` 破坏系统 Python。

## 推荐平台命令

### Linux / macOS

优先：

```bash
python3 -m pip install mempalace
python3 -m pip install graphifyy
```

如果用户环境里没有 `python3`，再尝试：

```bash
python -m pip install mempalace
python -m pip install graphifyy
```

如果系统环境被保护，使用虚拟环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install mempalace
.venv/bin/python -m pip install graphifyy
```

### Windows

优先：

```powershell
py -m pip install mempalace
py -m pip install graphifyy
```

如果用户环境没有 `py`，再尝试：

```powershell
python -m pip install mempalace
python -m pip install graphifyy
```

如果系统环境受限，也应优先改走虚拟环境，而不是修改系统级 Python。

## 工作边界

与用户沟通时，统一采用以下边界：

- `MemPalace` 负责记忆与找回
- `Graphify` 负责图谱、报告、Wiki、Obsidian 输出
- `MemArk` 未来负责桥接
- 当前这个 Skill 只负责把前两者安装好

不要把这个 Skill 说成：

- `MemArk` 本体
- 运行时服务
- 自动后台同步器
- 宿主插件

## 推荐安装流程

如果用户明确要求实际安装，AI 助手应按以下顺序处理：

1. 判断当前平台是 Windows、macOS 还是 Linux
2. 检查 Python 和 `pip` 调用路径
3. 安装 `MemPalace`
4. 验证 `mempalace` CLI
5. 安装 `Graphify`
6. 验证 `graphify` CLI
7. 如有需要，执行 `graphify install`
8. 创建桥接目录，例如：
   - `memark-work/raw/`
   - `memark-work/out/`
9. 告诉用户后续应如何手动：
   - 初始化 `MemPalace`
   - 准备 `Graphify` raw 目录
   - 运行 `graphify ./raw`

## 平台检查要求

安装前至少确认以下之一可用：

### Linux / macOS

- `python3`
- `python3 -m pip`

### Windows

- `py`
- `py -m pip`

如果这些入口不存在，再尝试：

- `python`
- `python -m pip`
- `pip`

## 验证要求

安装后至少验证：

### MemPalace

- `mempalace --help` 或等价帮助输出可运行
- 如果 `mempalace` 不在 PATH，尝试：

```bash
python -m mempalace --help
```

或在 Linux / macOS 上：

```bash
python3 -m mempalace --help
```

或在 Windows 上：

```powershell
py -m mempalace --help
```

### Graphify

- `graphify --help` 或等价帮助输出可运行
- 如果 `graphify` 不在 PATH，不要立刻宣称失败，先检查安装脚本目录是否未进入 PATH
- 不要把 `graphify install --help` 当成安全验证命令

如果 `graphify` 命令存在，再根据平台确认其安装模式：

- Claude Code (Linux / macOS): `graphify install`
- Claude Code (Windows): `graphify install --platform windows`
- Codex: `graphify install --platform codex`

注意：

- `graphify install` 是有副作用的真实安装动作
- 它会写入用户目录下的 skill 配置
- 不应用它替代纯帮助验证

如果命令不存在或失败：

- 明确告诉用户失败发生在哪一步
- 不要伪造“安装成功”
- 明确区分是“包未安装”还是“CLI 未进入 PATH”
- 如果是系统 Python 被保护，明确建议改用虚拟环境

## 禁止事项

不要在主路径里写成已存在的东西：

- `memark sync`
- `memark build`
- `memark watch`
- `memark mcp`

除非这些命令以后在仓库里真实存在并已经验证。

不要声称 `MemPalace` 当前已经提供：

- 按时间戳取增量的稳定 CLI
- 按时间戳取增量的稳定 MCP 工具

当前已核对到的是：它底层 drawer metadata 有 `filed_at`，但仓库没有公开正式的 `since` 增量接口。

## 安装完成后的正确说明

安装完成后，AI 助手应把下一步说清楚：

- 现在已经有 `MemPalace`
- 现在已经有 `Graphify`
- 还没有 `MemArk` 运行期桥接器
- 因此用户接下来只能先手动：
  - 让 `MemPalace` 记录和保存内容
  - 把准备好的材料放到 `Graphify` 的 `raw/`
  - 运行 `graphify` 消费这些语料

如果用户当前平台是 Windows，还应额外提醒：

- 不要默认用 `.sh` 脚本
- 优先使用 Python 命令和 PowerShell 兼容命令
- 如果后续要接 hook，需要单独处理 Windows 命令形式

如果用户当前平台是 macOS 或 Linux，还应额外提醒：

- 某些系统 Python 禁止直接 `pip install`
- 优先使用虚拟环境中的 CLI
- 不要默认全局命令已经进入 PATH

## 输出风格

- 先说安装是否成功
- 再说验证结果
- 最后说下一步手动操作
- 不要把未来设想写成已完成能力
