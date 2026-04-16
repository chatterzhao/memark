# MemArk

> 自动串联 MemPalace 记忆和 Graphify 图谱，让项目会话逐步变成 AI 可消费的项目知识。

上游项目：

- `MemPalace` GitHub: <https://github.com/milla-jovovich/mempalace>
- `Graphify` GitHub: <https://github.com/safishamsi/graphify>

## Sponsor

Sponsor placeholder.

If you want to sponsor `MemArk`, open an issue or contact the maintainer first.

## 先给 AI 用

如果你是让 AI 帮你安装和接入，优先把下面两个文件之一直接给 AI：

- 正式用户安装入口：[`SKILL.md`](SKILL.md)
- 开发期隔离验收入口：[`skill-dev.md`](skill-dev.md)

可以直接把文件内容贴给 AI，也可以把文档链接发给 AI，再让它按文档执行。

人工手动执行时，也建议先看这两个文件：

- `SKILL.md` 负责正式安装与项目接入
- `skill-dev.md` 负责开发期重装、假 `HOME`、隔离验证

## 它是什么

`MemArk` 不是新的记忆系统，也不是新的图谱引擎。

它的职责是桥接和治理：

- `MemPalace` 负责记忆存储、搜索、wake-up、会话 ingest
- `Graphify` 负责图谱、报告、查询等知识消费面
- `MemArk` 负责把项目相关记忆整理成更适合 AI 消费和图谱编译的项目语料

最核心的目标不是“把两个上游串起来”，而是让下面这条链路尽量自动化：

1. 自动安装
2. 自动配置
3. 自动喂数据
4. 自动加工
5. 自动消费

## 快速开始

```bash
# 先安装 MemArk
python3 -m venv .memark-bootstrap
.memark-bootstrap/bin/python -m pip install --upgrade pip
.memark-bootstrap/bin/python -m pip install .
.memark-bootstrap/bin/python -m memark install --platform codex --source-spec "$(pwd)"
memark doctor --platform codex

# 再在任意项目目录接入
cd your-project
memark init
```

`memark init` 默认会完成：

1. 创建 `.memark/` workspace
2. 注册项目
3. 安装后台调度
4. 执行首轮自动化 cycle

如果只想初始化 workspace，不自动装服务、不自动跑 cycle：

```bash
memark init --no-auto
```

## 安装和项目接入是两回事

- `memark install`
  - 面向这台机器
  - 安装用户级 runtime 和 skill bundle
- `memark init`
  - 面向某个 workspace 或项目目录
  - 初始化本地状态并接入自动化
- `memark project-set`
  - 面向已经存在的 workspace
  - 给一个 workspace 追加或更新项目登记

这也是为什么：

- 机器通常只需要执行一次 `memark install`
- 一个项目通常执行一次 `memark init`
- 多项目共享 workspace 时，后续更多是执行 `memark project-set`

## AI 和人工各自怎么用

### AI 驱动

推荐顺序：

1. 把 [`SKILL.md`](SKILL.md) 或 [`skill-dev.md`](skill-dev.md) 交给 AI
2. 让 AI 完成安装
3. 再让 AI 在目标项目目录执行 `memark init`
4. 后续通过 `memark context`、`memark query`、`memark automation-run` 持续消费

### 手工执行

如果你不打算让 AI 直接读 skill 文件，也可以手工按下面理解：

- `SKILL.md` 是正式用户路径
- `skill-dev.md` 是开发者验证路径
- `README.md` 只保留总览，不再重复完整安装细节

## 常用命令

- `memark doctor --platform codex`
  - 验证安装是否完整
- `memark init`
  - 在当前项目目录完成初始化
- `memark status --workspace . --json`
  - 查看项目状态
- `memark milestones --workspace . --json`
  - 查看当前阶段与阻塞项
- `memark context --workspace . --project <name>`
  - 输出 AI 可消费的项目上下文
- `memark query "<topic>" --workspace . --project <name>`
  - 搜索项目语料
- `memark automation-run --workspace .`
  - 手动跑一轮自动化 cycle
- `memark service-status --workspace . --json`
  - 查看后台调度状态

## 当前边界

当前仓库的公开边界是一个 CLI-first 的最小可用实现，重点在：

- 安装用户级 runtime
- 安装 AI skill bundle
- 初始化项目 workspace
- 同步会话
- 驱动记忆挖掘与晋升
- 提供本地 corpus 查询和上下文消费
- 在需要时构建本地图谱产物

当前仅支持 **macOS**。后台调度依赖 `launchd`。

## 详细文档

如果需要更细的背景、研究和设计，按主题看下面这些文档：

- 发布流程：[`docs/GITFLOW_RELEASE_FLOW.md`](docs/GITFLOW_RELEASE_FLOW.md)
- 发布检查：[`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md)
- Dogfood 运行：[`docs/DOGFOOD_RUNBOOK.md`](docs/DOGFOOD_RUNBOOK.md)
- 能力清单：[`docs/FEATURE_LIST.md`](docs/FEATURE_LIST.md)
- 接口与边界：[`docs/INTERFACE_CONTRACT.md`](docs/INTERFACE_CONTRACT.md)
- AI 消费模型：[`docs/AI_CONSUMPTION_MODEL.md`](docs/AI_CONSUMPTION_MODEL.md)
- 安装验证：[`docs/INSTALL_VERIFICATION.md`](docs/INSTALL_VERIFICATION.md)
- MemPalace 调研：[`docs/RESEARCH_MEMPALACE_USAGE.md`](docs/RESEARCH_MEMPALACE_USAGE.md)
- Graphify 调研：[`docs/RESEARCH_GRAPHIFY_USAGE.md`](docs/RESEARCH_GRAPHIFY_USAGE.md)
- `mempal` 调研：[`docs/RESEARCH_MEMPAL_EVALUATION.md`](docs/RESEARCH_MEMPAL_EVALUATION.md)
- 重新评估：[`docs/MEMARK_REASSESSMENT.md`](docs/MEMARK_REASSESSMENT.md)

## 维护者说明

维护者做正式 Gitflow 发布时，统一参考 [`docs/GITFLOW_RELEASE_FLOW.md`](docs/GITFLOW_RELEASE_FLOW.md)。
