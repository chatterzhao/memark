---
name: memark-installer
description: Use this skill when the user wants an AI assistant to install and configure MemPalace and Graphify for MemArk, verify that both upstream tools are available, and keep installation work clearly separated from MemArk runtime usage.
---

# MemArk Installer Skill

本 Skill 分两阶段，但默认只执行第一阶段：

1. 安装阶段：安装并验证 `MemPalace` 与 `Graphify`
2. 项目接入阶段：只在用户明确要求时，才为某个具体项目准备 `MemPalace` 配置

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
- 把这个 Skill 本身说成 `MemArk` 运行时
- 编造不存在的 `MemPalace` 增量接口
- 默认替用户对某个具体项目做知识治理决策

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

但要注意：

- `mempalace init <dir>` 的语义是“为项目目录生成 `mempalace.yaml`”，不是写入 palace 数据
- 真正把内容写入 ChromaDB palace 的是 `mempalace mine <dir>`
- `mempalace --palace <path>` 对 `mine`、`search`、`status`、`wake-up` 这类命令有效
- 当前已安装版 `mempalace 3.0.0` 实测存在一个非交互缺陷：`mempalace init <dir> --yes` 仍可能卡在 room 审批输入
- 因此不要把 `init --yes` 作为安装 Skill 的默认自动化路径

### Graphify

```bash
pip install graphifyy
```

常见使用命令：

```bash
graphify --help
graphify query "<question>" --graph graphify-out/graph.json
graphify codex install
graphify claude install
```

不要在安装 Skill 里假设任意已安装版本都稳定支持：

```bash
graphify <folder>
```

如果后续需要真正调用 Graphify 构建目录语料，必须先根据用户安装版本或对应上游源码确认该版本暴露的构建入口。

当前对已安装 `graphifyy 0.3.12` 和已克隆上游源码的实测还说明：

- 可以把 `graphify.watch._rebuild_code(Path(...))` 当作一个已验证过的兼容 fallback
- 但它只重建 code graph，不等价于完整 mixed-corpus semantic build
- 因此不要把“已经把 Markdown 语料写进 corpus”直接表述成“已经完整喂给 Graphify”

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

## 阶段边界

### 第一阶段：安装阶段

默认执行这一阶段。

这一阶段只做：

- 安装 `MemPalace`
- 安装 `Graphify`
- 验证 CLI
- 如有需要执行平台 skill 安装

这一阶段不做：

- 运行 `mempalace init <project>`
- 生成某个项目的 `mempalace.yaml`
- 替用户决定项目 wing / rooms
- 运行任何项目级别的 `mine`

### 第二阶段：项目接入阶段

只有当用户明确要求“把某个项目接入 MemPalace”时，才进入这一阶段。

这一阶段可以做：

- 核对用户已安装版本对应的上游源码
- 判断 `mempalace init` 是否可靠
- 必要时手写 `mempalace.yaml`
- 指导或执行 `mempalace --palace <path> mine <project>`

## 推荐安装流程

如果用户明确要求实际安装，AI 助手应按以下顺序处理：

1. 判断当前平台是 Windows、macOS 还是 Linux
2. 检查 Python 和 `pip` 调用路径
3. 安装 `MemPalace`
4. 验证 `mempalace` CLI
5. 安装 `Graphify`
6. 验证 `graphify` CLI
7. 如有需要，执行 `graphify install`
8. 如有需要，创建一个单独工作目录，例如：
   - `memark-work/`
   - `memark-work/palace/`
9. 告诉用户后续应如何手动：
   - 如果后面要接入具体项目，再决定是否运行 `mempalace init` 或手写 `mempalace.yaml`
   - 准备 `Graphify` 可消费的 corpus / raw 目录
   - 按该版本真实支持的入口运行 `Graphify`

## MemPalace 版本核对与 `mempalace.yaml` 生成规则

当用户希望 AI 助手继续“为某个项目准备 MemPalace 配置”时，必须按下面顺序做，不能跳步猜测。

### 第一步：先确认用户实际安装的是哪个版本

优先执行：

```bash
python3 -m pip show mempalace
```

Windows 优先：

```powershell
py -m pip show mempalace
```

如果用户装在虚拟环境里，就使用那个解释器对应的 `-m pip show`。

至少记录以下信息：

- `Name`
- `Version`
- `Location`
- `Home-page`

如果 `pip show` 不可用，再退一步：

```bash
mempalace --help
python3 -m mempalace --help
```

### 第二步：根据版本去核对对应上游源码

不要只看仓库默认分支。应优先核对：

1. PyPI 安装包暴露出的版本号
2. 该版本在上游仓库对应的 tag / release / 包源码
3. 该版本里 `cli.py`、`room_detector_local.py`、`miner.py`、`config.py` 的真实实现

重点核对：

- `cmd_init()` 是否把 `--yes` 传给 room 审批逻辑
- `detect_rooms_local()` 是否仍然包含 `input()`
- `save_config()` 写出的 `mempalace.yaml` 长什么样
- `mine()` 读取的是不是项目目录内的 `mempalace.yaml`
- `--palace` 是否被 `init` 使用，还是只被 `mine/search/status/wake-up` 使用

如果用户机器上安装的是旧版本，而上游主分支已经修复问题，必须明确告诉用户：

- “你当前安装版的行为”
- “上游源码最新版本的行为”

不要把主分支行为伪装成用户当前版本行为。

### 第三步：判断是否应该调用 `mempalace init`

默认原则：

- 安装 Skill 只负责安装工具，不负责替用户对某个具体项目执行 `mempalace init`
- 如果只是完成安装验证，不要自动跑 `init`
- 如果用户明确要求“为这个项目生成 MemPalace 配置”，再继续下面步骤

### 第四步：优先选择哪种生成方式

#### 方式 A：用户当前版本的 `init` 足够可靠时

如果已经核对到该版本支持非交互且不会卡住，可以使用：

```bash
mempalace init <project_dir> --yes
```

只有在确认这个版本真的这样工作时，才能这样做。

#### 方式 B：当前版本 `init` 不可靠，直接生成 `mempalace.yaml`

如果像当前验证到的 `mempalace 3.0.0` 一样，`init --yes` 仍会卡在交互输入，则不要硬跑。

这时应改为：

1. 从上游该版本源码确认 `mempalace.yaml` 契约
2. 根据项目目录结构生成 YAML
3. 写入 `<project_dir>/mempalace.yaml`

根据当前已核对源码，`mempalace.yaml` 的核心结构是：

```yaml
wing: my_project
rooms:
  - name: documentation
    description: Files from docs/
    keywords:
      - documentation
      - docs
  - name: general
    description: Files that don't fit other rooms
    keywords: []
```

也就是说最少要生成：

- 顶层 `wing`
- 顶层 `rooms`
- 每个 room 的 `name`
- 每个 room 的 `description`
- 每个 room 的 `keywords`

### 第五步：YAML 生成原则

生成 `mempalace.yaml` 时：

- `wing` 默认取项目目录名，小写，空格和 `-` 转成 `_`
- `rooms` 先根据顶层和次级目录推断
- 至少保留一个 `general` room
- 不要编造 closet、drawer、hall 配置字段写进 YAML，除非已在该版本源码中核对到
- 不要把 `palace_path` 写进 `mempalace.yaml`，它属于全局配置或 CLI `--palace` 参数，不是项目 room 配置

### 第六步：生成后如何继续

生成完 `mempalace.yaml` 后，应告诉用户正确下一步是：

```bash
mempalace --palace <palace_dir> mine <project_dir>
```

例如：

```bash
mempalace --palace ./memark-work/palace mine .
```

然后再用：

```bash
mempalace --palace ./memark-work/palace status
```

不要把 `init` 说成“已经初始化了 palace 数据库”。那是不准确的。

### 第七步：接入前先做污染隔离

在对真实项目执行 `mine` 之前，应先检查项目是否会把派生产物重新喂回上游工具。

最低限度要确认：

- `.gitignore` 已排除 `graphify-out/`
- `.gitignore` 已排除实验目录、临时工作目录、palace 数据目录
- 如果项目会直接运行 `Graphify detect`，再额外检查 `.graphifyignore`

对当前 `MemArk` 仓库，已经验证有价值的排除对象包括：

- `.experiments/`
- `graphify-out/`
- `.mempalace/`
- `memark-work/`

原因：

- `MemPalace mine` 默认会尊重 `.gitignore`
- `Graphify detect` 默认不会自动理解这些目录都该排除
- 如果不先隔离，实验产物、图谱产物和临时语料会污染后续结果

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
