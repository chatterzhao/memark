# Install Verification

本文件只记录已经真实执行过的安装与验证结果。

它不描述未来设想，只记录已经核对到的事实。

## 验证时间

- 日期：2026-04-08
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

随后改用仓库内虚拟环境 `.venv-skill-check`：

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

- 优先写 `python3 -m pip` / `py -m pip`
- 系统 Python 受限时优先建议虚拟环境
- 不要默认全局安装一定成功
- 不要把 `graphify install --help` 当成安全验证
- 不要伪造 `MemPalace` 已存在的增量接口
