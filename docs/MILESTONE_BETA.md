# Beta Milestone

本文件定义当前 `MemArk` 仓库下一条明确里程碑：

`MemArk Beta: current repo can dogfood MemArk on itself in a controlled macOS workflow`

它不回答“终极产品是否完成”，只回答：

- 当前版本准备把什么能力收成一个对外可解释的阶段
- 哪些能力已经达到这个阶段
- 哪些能力仍然是 Beta 的出站条件，而不是已完成能力

## 里程碑定义

当前 Beta 的目标不是“所有自动化都做完”，而是：

1. 当前仓库可以把自己注册成 `MemArk` 项目
2. 当前仓库可以真实执行 intake -> process -> consume 单次 cycle
3. 当前仓库可以在 macOS `launchd` 下拿到后台 cycle 完成证据
4. 当前仓库的 AI 与维护者已经有可直接读取的消费入口
5. 文档已经把安装、项目接入、自动调度、消费入口讲清楚

更短地说：

当前 Beta 是“受控 dogfood 可用”，不是“全平台正式生产完成”。

## 当前阶段口径

当前建议对外使用的口径是：

- `MemArk` 已达到 macOS 内部 Beta
- 适合当前仓库和少量项目做受控试运行
- 不应表述为 GA
- 不应表述为“mixed-corpus Graphify semantic ingestion 已完成”
- 不应表述为“长期后台稳定运行已经完成验收”

## Beta 入口能力

达到当前 Beta，至少要具备下面这些入口：

- 用户级安装：`memark install`
- 安装健康检查：`memark doctor`
- workspace 初始化：`memark init`
- 项目注册：`memark project-set`
- 单次自动 cycle：`memark automation-run`
- 后台调度安装：`memark service-install`
- 后台运行状态：`memark service-status`
- 自动 cycle 状态：`memark automation-status`
- 项目统一消费入口：`memark context`
- promoted corpus 搜索入口：`memark query`

## 当前已达到

基于当前仓库的测试、真实 smoke 和文档记录，当前 Beta 已达到：

- 安装链路可真实跑通
- `doctor` 能验证 runtime 与 skill bundle
- 当前仓库能登记为项目并执行 `automation-run`
- 当前仓库能真实生成：
  - `latest-summary.md`
  - `decisions-digest.md`
  - `risks-digest.md`
  - `ai-context.md`
  - `graphify-status.md`
- 当前仓库已有 `automation-status` 作为单次自动 cycle 的持久化观测面
- 当前仓库在 macOS `launchd` 下已拿到：
  - `service-install` 成功
  - `service-status.last_cycle` 可读
  - `launchctl print` 中 `runs` 增长
  - `.memark/state/automation-run.json` 时间戳推进
  - 后台 cycle 完成证据
- 文档已明确：
  - `install` 是机器级安装
  - `init` 是 workspace 级初始化
  - `project-set` 是项目接入

## Beta 已实现功能

为了让里程碑本身也能作为功能索引，当前 Beta 已实现能力按使用路径整理如下。

### 1. 安装与接入

- `memark install`
- `memark doctor`
- `memark init`
- `memark project-set`
- `memark projects-list`

这一层回答：

- 机器怎么安装
- workspace 怎么初始化
- 新项目怎么接入

### 2. Intake 与会话同步

- `memark codex-sync`
- `memark projects-run`
- `memark automation-run`

这一层已实现：

- 按项目目录筛选 `Codex` sessions
- 把命中的 session 写入 staging
- 以单次自动 cycle 串起 intake -> process -> consume

### 3. Palace 运维与知识晋升

- `memark mempalace-mine`
- `memark palace-status`
- `memark palace-clean`
- `memark palace-rebuild`
- `memark palace-retry`
- `memark palace-export`
- `memark palace-package`
- `memark palace-run`
- `memark promote`
- `memark add-documents`

这一层已实现：

- 对项目会话做 `MemPalace` ingest
- 从 drawers 导出只读数据
- 按 `room` 或 `logical session` 打包
- 把 package 晋升为 `Graphify-ready` corpus
- 把正式文档同步进 `documents/`

### 4. 本地消费入口

- `memark query`
- `memark context`

当前已做成：

- 直接搜索本地 `promoted/`、`documents/`、`imports/`
- 一次读取 `latest-summary`、`decisions-digest`、`risks-digest`、`ai-context`、`graphify-status`

### 5. 调度、状态与持续 dogfood

- `memark service-install`
- `memark service-status`
- `memark service-uninstall`
- `memark automation-status`

当前已做成：

- `launchd` 安装、查询、卸载
- 自动 cycle 状态持久化
- 后台 `last_cycle` 观测
- `service-status.health`、`observations`、日志字节数、stale 判断

### 6. Graphify bridge 与 worktree 支持

- `memark graphify-handoff`
- `memark build`
- `memark slash`
- `memark worktree-attach`
- `memark worktree-hook-install`

当前已做成：

- 生成给上游 `Graphify` skill 的准确 handoff
- 在安装版 `graphify` CLI 不支持 direct folder build 时，仍能由 `MemArk` 本地完成 mixed-corpus graph build
- 为新 worktree 复制 `.memark` 等项目本地配置
- 通过 hook 自动接入后创建的 worktree

## Beta 已完成事项时间线

- 用户级安装链路打通
- 当前仓库单次自动 cycle 打通
- 自动消费产物落盘
- `launchd` 后台 cycle 证据打通
- `automation-status` 持久化状态面打通
- `service-status` 健康观测面补齐

## Beta 明确不承诺

当前 Beta 不应承诺下面这些能力：

- promoted markdown 已稳定进入完整 Graphify 图谱
- 全平台统一 scheduler backend 已完成
- Windows 生产级验证已完成
- 长期后台无人值守稳定性已完成验证
- 自动治理已经达到高质量结构化对象抽取
- 安装后任意项目会自动完成接入

## Beta 出站条件

要从当前 Beta 继续往前走，至少还需要满足下面这些条件中的大部分：

### B1. 长期后台稳定性

- 在真实项目上连续运行多天
- `automation-status` 持续推进
- 没有反复卡死、僵住或 silent failure

### B2. Graphify mixed-corpus 闭环

- 至少一次真实证明 `promoted/*.md` 被稳定消费进上游图谱
- 不再只停留在 handoff 和 code-only fallback

### B3. 发布边界收敛

- 明确区分：
  - macOS Beta
  - cross-platform preview
  - GA
- 不再混用“已可用”和“已完全生产就绪”

### B4. 运维面补齐

- 增加更明确的发布前检查清单
- 增加更明确的故障排查文档
- 对自动生成产物和状态文件建立维护规则

## 当前维护建议

如果以“当前仓库先自己吃自己”为优先目标，下一步最值得做的是：

1. 把当前 Beta 作为正式里程碑写进仓库文档入口
2. 以 [`docs/RELEASE_CHECKLIST.md`](<repo-root>/docs/RELEASE_CHECKLIST.md) 作为每次对外说明或内部推广前的执行清单
3. 连续观察一段真实后台调度运行结果
4. 按 [`docs/DOGFOOD_RUNBOOK.md`](<repo-root>/docs/DOGFOOD_RUNBOOK.md) 持续运行当前仓库 dogfood
5. 参考 [`docs/MILESTONE_NEXT.md`](<repo-root>/docs/MILESTONE_NEXT.md) 推进下一阶段里程碑

## 一句话结论

当前 `MemArk` 最准确的里程碑不是“生产完成”，而是：

`MemArk Beta: self-dogfood on this repo is operational on macOS, with verified single-cycle automation and verified background-cycle evidence.`
