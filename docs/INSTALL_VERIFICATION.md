# Install Verification

本文件只记录已经真实执行过的安装与验证结果。

它不描述未来设想，只记录已经核对到的事实。

## 验证时间

- 日期：2026-04-09
- 工作目录：[`/Users/zhaoyu/Downloads/code/my-memark/memark`](/Users/zhaoyu/Downloads/code/my-memark/memark)

## 验证环境

- Python：`Python 3.14.0`
- `pip`：可通过 `python3 -m pip` 调用
- 平台：当前机器为 macOS / Unix 风格环境

## 已执行验证

先验证系统 Python 直接安装：

```bash
python3 -m pip install mempalace
python3 -m pip install graphifyy
```

结果：

- 两者都因 `externally-managed-environment` 失败
- 说明系统 Python 受 PEP 668 保护
- 因此正式安装路径不能默认写成“直接全局 `pip install` 一定成功”

随后改用仓库内虚拟环境 `.venv-skill-check`。

这一步是上游 CLI 探测，不是当前最终安装闭环：

```bash
python3 -m venv .venv-skill-check
.venv-skill-check/bin/python -m pip install mempalace
.venv-skill-check/bin/python -m pip install graphifyy
```

结果：

- `mempalace` 安装成功
- `graphifyy` 安装成功

## CLI 验证结果

### `MemPalace`

已成功执行：

```bash
.venv-skill-check/bin/mempalace --help
.venv-skill-check/bin/python -m mempalace --help
.venv-skill-check/bin/mempalace status
```

结果：

- CLI 可运行
- `python -m mempalace` 入口可运行
- `mempalace status` 在未初始化 palace 时会正常报出需要先 `init` / `mine`

### `Graphify`

已成功执行：

```bash
.venv-skill-check/bin/graphify --help
```

结果：

- CLI 可运行
- 当前验证到的安装版本是 `graphifyy 0.3.12`
- 顶层 `graphify --help` 暴露的是 `install`、`query`、`benchmark`、`hook`、`claude/codex install` 等入口
- 直接执行 `graphify . --update` 会报 `unknown command '.'`

这意味着：

- `Graphify` 的“目录构建入口”不能在 `MemArk` 中被表述成一个对所有安装版本都稳定成立的顶层 CLI 契约
- `MemArk` 当前只能把这一步定义为“调用兼容的 Graphify 构建入口”

另一个重要发现：

- `graphify install --help` 不是纯帮助命令
- 它会实际执行安装动作并写入用户目录

当前已观察到的副作用路径：

- [`/Users/zhaoyu/.claude/skills/graphify`](/Users/zhaoyu/.claude/skills/graphify)
- [`/Users/zhaoyu/.agents/skills/graphify`](/Users/zhaoyu/.agents/skills/graphify)

因此：

- 不能把 `graphify install --help` 当成无副作用验证命令
- 安装 Skill 时必须把 `graphify install` 视为真正的写入动作

另外，根据上游 `graphify` 源码已核对到：

- skill 安装目标是用户家目录下的平台目录，不是当前项目仓库
- 对 Codex 而言，上游还会把 always-on 注册写到当前项目的 `AGENTS.md`
- 对 Codex 而言，上游还会把 PreToolUse hook 写到当前项目的 `.codex/hooks.json`
- `graphify-out/` 则是运行时输出目录，落在你执行 `graphify` 的项目目录中

这几个层次必须分开理解：

- `~/.agents/skills/graphify` / `~/.claude/skills/graphify`：全局 skill 安装
- `AGENTS.md` / `.codex/hooks.json`：当前项目对 AI 工具的接入注册
- `graphify-out/`：当前项目被 graphify 分析后生成的图谱产物

## 已核对到的上游接口事实

### `MemPalace`

已核对到：

- 官方仓库：<https://github.com/milla-jovovich/mempalace>
- 常见 CLI：`init`、`mine`、`search`、`compress`、`wake-up`、`split`、`status`
- 存在 MCP server
- 底层 drawer metadata 含 `filed_at`

尚未核对到：

- 一个稳定公开的“按时间戳取增量” CLI
- 一个稳定公开的“按时间戳取增量” MCP 工具

### `Graphify`

已核对到：

- 官方仓库：<https://github.com/safishamsi/graphify>
- PyPI 包名：`graphifyy`
- CLI 名称：`graphify`
- 支持 `graphify install`
- 上游 README 明确描述了 `--update`、`--watch`、`--wiki`、`--obsidian`、`--mcp`
- 当前安装版顶层 help 还明确暴露了 `query`、`benchmark`、`hook`、`claude/codex install`

## 对 `SKILL.md` 的直接影响

基于以上验证，根目录 [`SKILL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/SKILL.md) 需要坚持以下口径：

- 首次执行必须允许 bootstrap venv
- 系统 Python 受限时优先建议虚拟环境
- 不要把 `graphify install --help` 当成安全验证
- 不要伪造 `MemPalace` 已存在的增量接口

## 当前正式安装闭环验证

以下验证对应当前产品模型：用户级 runtime + AI skill bundle。

### 验证命令

```bash
rm -rf /tmp/memark-prod-e2e
mkdir -p /tmp/memark-prod-e2e/home
HOME=/tmp/memark-prod-e2e/home \
  ./.venv-dev/bin/python -m memark install \
  --platform codex \
  --memark-home /tmp/memark-prod-e2e/home/.memark \
  --source-spec /Users/zhaoyu/Downloads/code/my-memark/memark \
  --json
HOME=/tmp/memark-prod-e2e/home \
  /tmp/memark-prod-e2e/home/.agents/skills/memark/bin/memark doctor --platform codex
/tmp/memark-prod-e2e/home/.memark/venv/bin/mempalace --help
/tmp/memark-prod-e2e/home/.memark/venv/bin/graphify --help
```

### 验证结果

说明：

- 命令中使用的是 `/tmp/...`
- macOS 实际解析后的绝对路径是 `/private/tmp/...`

- `memark install` 成功创建 runtime：[`/private/tmp/memark-prod-e2e/home/.memark/venv`](/private/tmp/memark-prod-e2e/home/.memark/venv)
- `memark install` 成功写入 Codex skill bundle：[`/private/tmp/memark-prod-e2e/home/.agents/skills/memark`](/private/tmp/memark-prod-e2e/home/.agents/skills/memark)
- skill bundle 中已确认存在：
  - [`SKILL.md`](/private/tmp/memark-prod-e2e/home/.agents/skills/memark/SKILL.md)
  - [`project.md`](/private/tmp/memark-prod-e2e/home/.agents/skills/memark/project.md)
  - [`doctor.md`](/private/tmp/memark-prod-e2e/home/.agents/skills/memark/doctor.md)
  - [`bin/memark`](/private/tmp/memark-prod-e2e/home/.agents/skills/memark/bin/memark)
  - [`bin/memark.cmd`](/private/tmp/memark-prod-e2e/home/.agents/skills/memark/bin/memark.cmd)
  - [`manifest.json`](/private/tmp/memark-prod-e2e/home/.agents/skills/memark/manifest.json)
- `bin/memark` 已具备可执行位
- `memark doctor --platform codex` 返回 `Doctor summary: ok`
- runtime 内上游 CLI 可执行：
  - [`mempalace`](/private/tmp/memark-prod-e2e/home/.memark/venv/bin/mempalace)
  - [`graphify`](/private/tmp/memark-prod-e2e/home/.memark/venv/bin/graphify)

### 当前闭环安装到的版本

- `mempalace 3.1.0`
- `graphifyy 0.3.24`

这说明当前仓库已经不只是“文档里写了安装器”，而是已经真实具备：

- 用户级 runtime 安装
- AI skill bundle 下发
- 安装后 launcher 调用
- `doctor` 自检

## 当前仓库上的真实联调结果

以下结果是在当前 `memark` 仓库里直接实测得到的，不是推测。

### 清理治理后的 `MemPalace`

先为当前仓库手写 `mempalace.yaml`，并让仓库级忽略规则排除派生产物后，执行：

```bash
PYTHONPATH=/Users/zhaoyu/Downloads/code/my-memark/mempalace \
  .venv-skill-check/bin/python -m mempalace \
  --palace /tmp/memark-palace-clean mine .
```

结果：

- `Files: 35`
- `Files processed: 34`
- `Drawers filed: 258`
- room 分布：
  - `documentation`: `140`
  - `implementation`: `92`
  - `testing`: `24`
  - `examples`: `2`

同一仓库在未清理治理时，之前实测曾达到 `823` drawers。

这说明：

- `MemPalace` 默认会受项目忽略规则影响
- 如果不先隔离 `graphify-out/`、实验目录和工作目录，结果会明显污染

随后在同一个干净 palace 上执行：

```bash
PYTHONPATH=/Users/zhaoyu/Downloads/code/my-memark/mempalace \
  .venv-skill-check/bin/python -m mempalace \
  --palace /tmp/memark-palace-clean search "graphify cli contract mismatch"
```

结果：

- 能准确命中 [`tests/test_cli.py`](/Users/zhaoyu/Downloads/code/my-memark/memark/tests/test_cli.py)
- 对当前仓库这类中小型项目，`MemPalace` 的“精确找回”已经很有用

### 清理治理后的 `Graphify`

对当前仓库执行 `detect()` 后，结果为：

- `total_files`: `32`
- `total_words`: `15,186`
- `needs_graph`: `False`
- warning：`Corpus is ~15,186 words - fits in a single context window. You may not need a graph.`

这说明：

- 在当前仓库规模下，`Graphify` 不应被写成强制必需层
- 它更适合作为“当 corpus 继续增长后再开启”的知识编译层
- 当前桥接层最先该做好的，是治理与晋升，而不是盲目全量编图

### `MemArk build` 的真实 fallback 联调

在单独工作区里，用当前 `MemArk` CLI：

1. 初始化 workspace
2. 晋升一个 room package
3. 复制当前仓库的 `memark/cli.py`、`memark/graphify.py`、[`tests/test_cli.py`](/Users/zhaoyu/Downloads/code/my-memark/memark/tests/test_cli.py) 等文件进入 corpus
4. 让 `PATH` 指向已安装 `graphify` 的 `.venv-skill-check/bin/graphify`
5. 从 `memark` 自己的 `.venv` 执行 `memark build`

结果：

- 顶层 `graphify <folder>` 仍然不可用
- `MemArk` 成功退回到 `graphify.watch._rebuild_code`
- 退回时使用的是当前执行 `memark` 的 Python 解释器，因此该解释器环境里也必须能导入 `graphify`
- 成功生成：
  - `graphify-out/graph.json`
  - `graphify-out/GRAPH_REPORT.md`
- 本次实测输出为：
  - `82 nodes`
  - `140 edges`
  - `7 communities`
- 继续用 `graphify query` 检查时，命中的是 `memark/` 代码节点和函数关系
- 手写晋升进去的 Markdown room 与 `documents/` 文档没有出现在图输出里

这也再次说明：

- 当前 fallback 是真实可用的
- 但它是 code-only rebuild
- 它不能被写成“任意 corpus 都能完整 semantic build”
- 当前真正成立的是“MemArk 已能整理语料并构建代码图”，还不是“MemPalace 晋升记忆已完整进入 Graphify 图谱”
