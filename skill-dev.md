---
name: memark-installer-dev
description: Development-stage installer skill for isolated fake-HOME reset, repeatable MemArk install verification, and non-interactive end-to-end testing.
---

# MemArk Installer Skill (Dev)

这是开发阶段入口，不是正式用户入口。

它的目标不是“解释概念”，而是让 AI 在开发阶段反复执行真实安装验收，并把副作用隔离在临时目录里。

适用场景：

- 反复销毁并重建隔离安装环境
- 做 `codex exec` 免交互验收
- 验证用户级 runtime + skill bundle 是否真的可用
- 在不污染真实 `HOME` 的前提下做完整安装
- 回归测试 `memark install` 与 `memark doctor`

正式入口仍然是 [`SKILL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/SKILL.md)。

## Dev 默认策略

开发阶段默认使用“假 `HOME` + 独立 `MEMARK_HOME` + 本地源码安装”的方式。

因此默认要求：

- 使用仓库内 `.venv-dev/` 作为 bootstrap Python 环境
- 使用临时目录模拟用户主目录，例如 `/tmp/memark-skill-dev/home`
- 使用 `memark install --source-spec <repo-root>` 做真实用户级安装
- 安装目标落到假 `HOME` 下的：
  - `.memark/`
  - `.agents/skills/memark/`
  - `.claude/skills/memark/`
- 再用安装后的 launcher 执行 `memark doctor`
- 每次执行都显式报告安装路径和平台目录

必要时可以先清理：

- `.venv-dev/`
- `/tmp/memark-skill-dev/`
- 其他本次验收专用临时目录

## Dev 执行目标

一次标准 dev 执行只做下面几件事：

1. 清理并重建 `.venv-dev/`
2. 以 `-e .[dev]` 安装当前仓库
3. 准备假 `HOME` 与 `MEMARK_HOME`
4. 运行 `python -m memark install`
5. 运行安装后 launcher 的 `memark doctor`
6. 验证 bundle 文件、launcher、manifest、上游 CLI 都存在
7. 记录精确路径和结果

不要扩展去做：

- 项目接入
- `project-set`
- `projects-run`
- `mempalace mine`
- `graphify codex install`
- `graphify claude install`

## Dev 推荐命令

### Linux / macOS

```bash
rm -rf .venv-dev /tmp/memark-skill-dev
python3 -m venv .venv-dev
.venv-dev/bin/python -m pip install --upgrade pip
.venv-dev/bin/python -m pip install -e '.[dev]'
mkdir -p /tmp/memark-skill-dev/home
HOME=/tmp/memark-skill-dev/home \
MEMARK_HOME=/tmp/memark-skill-dev/home/.memark \
  .venv-dev/bin/python -m memark install \
  --platform codex \
  --memark-home /tmp/memark-skill-dev/home/.memark \
  --source-spec "$(pwd)"
HOME=/tmp/memark-skill-dev/home \
  /tmp/memark-skill-dev/home/.agents/skills/memark/bin/memark doctor --platform codex
```

### Windows

```powershell
if (Test-Path .venv-dev) { Remove-Item .venv-dev -Recurse -Force }
if (Test-Path $env:TEMP\memark-skill-dev) { Remove-Item $env:TEMP\memark-skill-dev -Recurse -Force }
py -m venv .venv-dev
.venv-dev\Scripts\python -m pip install --upgrade pip
.venv-dev\Scripts\python -m pip install -e ".[dev]"
$env:HOME = "$env:TEMP\\memark-skill-dev\\home"
$env:MEMARK_HOME = "$env:HOME\\.memark"
New-Item -ItemType Directory -Force -Path $env:HOME | Out-Null
.venv-dev\Scripts\python -m memark install --platform codex --memark-home $env:MEMARK_HOME --source-spec "%CD%"
& "$env:HOME\.agents\skills\memark\bin\memark.cmd" doctor --platform codex
```

## Dev 验收标准

- `.venv-dev/` 存在
- 假 `HOME` 下存在 `.memark/venv/`
- 假 `HOME` 下存在 `.agents/skills/memark/` 或 `.claude/skills/memark/`
- `manifest.json` 存在
- `bin/memark` 或 `bin/memark.cmd` 可执行
- `doctor` 返回成功
- runtime 内存在：
  - `memark`
  - `mempalace`
  - `graphify`

## `codex exec` 用法

如果要验证 AI 是否能仅凭 Skill 正确执行，应要求：

- 只读这个 dev skill
- 免交互
- 自动批准
- 允许本地源码安装
- 必须把真实副作用限制在假 `HOME`

典型要求应接近：

- 清理并重建 `.venv-dev/`
- 建立假 `HOME`
- 执行 `memark install`
- 运行安装后 launcher 的 `memark doctor`
- 输出 runtime 与 skill bundle 路径
- 不触碰真实用户目录

## 失败时优先排查

- Python 版本不满足要求
- 系统 Python 被 externally-managed 锁住
- `.venv-dev` 没有安装当前仓库
- `--source-spec` 没传仓库根目录
- 假 `HOME` 与 `MEMARK_HOME` 不一致
- AI 误执行了项目接入命令

## 与正式入口的关系

- [`SKILL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/SKILL.md) 面向用户机器上的正式安装
- [`skill-dev.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/skill-dev.md) 面向开发期隔离验证
- 两者都只负责安装与验证，不负责项目接入
