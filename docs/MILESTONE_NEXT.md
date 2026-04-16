# Next Milestone

本文件定义 `MemArk` 在当前 Beta 之后的下一条里程碑。

当前不把下一条里程碑定义成“先做跨平台”，原因很直接：

- 目前最大的真实缺口不是平台覆盖率
- 而是后台长期稳定性、mixed-corpus graph 闭环，以及 AI 自动消费闭环

因此下一条里程碑应定义为：

`MemArk Beta+1: unattended dogfood is reliable on macOS, and promoted knowledge has at least one real mixed-corpus graph proof`

更短地说：

先把“能跑”推进到“能持续跑、值得持续用”，再去做 cross-platform preview。

## 为什么不是先跨平台

如果现在先扩 Linux / Windows，最容易发生的事情是：

- 花大量时间在 scheduler 差异、安装细节、路径兼容
- 但核心产品闭环仍然没有被更强地证明

这样会把阶段判断变模糊：

- 看起来支持的平台更多了
- 但 AI 是否真的因 `MemArk` 持续变好，仍然说不清

当前更值得优先收口的是：

1. 后台自动链路能否连续多天稳定推进
2. 晋升后的 `promoted/*.md` 能否至少一次真实进入 corpus 级 mixed-corpus 图谱
3. AI 在新任务开始时，能否默认拿到自动整理后的上下文入口

## 里程碑定义

达到 `Beta+1`，至少要满足下面三类能力中的大部分：

### N1. 长期后台稳定性

- 当前仓库在 macOS `launchd` 下连续运行多天
- `automation-status` 持续推进
- 没有持续性的 silent failure、卡死、重复失败不告警
- 日志、状态文件、自动生成产物有明确维护方式

### N2. Mixed-corpus graph 真实闭环

- 至少一次真实证明 `corpus/<project>/promoted/*.md` 与注册项目文档被 mixed-corpus graph 消费
- 不再只停留在 `graphify-handoff` 或旧的 code-only fallback 口径
- 把 slash-only 能力抽成 `MemArk` 自己的 CLI 适配层，而不是继续散在上游 client skill 里
- 让 slash-only 状态观测也直接走 `MemArk` 的 catalog 与执行面
- 让自动化状态与 graph proof 观测也同时具备 CLI 和 slash 兼容入口
- direct CLI surface 继续保持唯一正式命令名，优先避免 AI 在同一能力上使用多种拼写
- 文档明确区分：
  - `Graphify-ready corpus`
  - `actually ingested into graph`

### N3. AI 自动消费增强

- 项目 AI 在启动任务时有稳定入口读取 `memark context`
- 能默认拿到：
  - `latest-summary`
  - `decisions-digest`
  - `risks-digest`
  - `graphify-status`
- 至少有一轮真实 dogfood 可以证明：
  - AI 没有重复问已经讨论过的问题
  - AI 明确引用了自动整理后的历史知识继续执行

## 当前已完成的前置能力

`Beta+1` 不是从零开始。下面这些能力已经在上一阶段做成，并且是当前阶段继续向前推的基础：

- `memark install` / `doctor`
- `memark init` / `project-set`
- `memark automation-run`
- `memark build`
- `memark slash`
- `memark context`
- `memark query`
- `memark service-install` / `service-status` / `service-uninstall`
- `memark automation-status`
- `memark graphify-handoff`
- `memark graphify-proof`
- `memark worktree-attach` / `worktree-hook-install`
- 唯一正式 CLI 命令面，避免一项能力同时存在多个入口名

当前已经具备的真实运维基础：

- 当前仓库持续自己吃自己
- `launchd` job 已可保持安装状态连续观察
- `service-status` 已能直接看 `health`
- `DOGFOOD_RUNBOOK` 与 `DOGFOOD_LOG` 已形成持续记录面
- mixed-corpus graph proof 已有持久化状态入口

## 当前阶段已推进到的事项

虽然 `Beta+1` 还未完成，但已经开始推进下面这些能力：

### 1. 持续后台可靠性

已做成：

- 后台 job 可以保持不卸载持续观察
- `service-status` 已能给出：
  - `interval_seconds`
  - `stdout_bytes`
  - `stderr_bytes`
  - `health`
  - `observations`
- 已支持区分：
  - `ok`
  - `stale`
  - `failing`
  - `running`
  - `not_loaded`
  - `not_installed`

### 2. 里程碑配套运维文档

已做成：

- [`docs/RELEASE_CHECKLIST.md`](<repo-root>/docs/RELEASE_CHECKLIST.md)
- [`docs/DOGFOOD_RUNBOOK.md`](<repo-root>/docs/DOGFOOD_RUNBOOK.md)
- [`docs/DOGFOOD_LOG.md`](<repo-root>/docs/DOGFOOD_LOG.md)

### 3. 仍在推进中的缺口

还没做完的核心缺口仍然是：

- mixed-corpus graph 真实闭环
- AI 自动消费效果的真实证明
- 多天后台稳定性证据

## 下一里程碑不承诺

即使 `Beta+1` 达成，也不应自动承诺：

- Linux / Windows 已达到同等生产验证
- 任意项目安装后可自动零配置接入
- 高质量结构化对象抽取已经完全成熟
- `MemArk` 已达到 GA

## 之后再做什么

在 `Beta+1` 收口后，再进入下一条更合适：

`Cross-platform Preview: scheduler and install paths are verified on macOS plus at least one non-macOS platform`

这个阶段才适合去解决：

- Linux `systemd` 或 `cron`
- Windows Task Scheduler
- 路径、shell、用户目录差异
- 安装和状态查询的跨平台体验收敛

## 当前建议执行顺序

如果继续按“当前仓库自己吃自己”推进，推荐按这个顺序做：

1. 补持续 dogfood runbook，并按 runbook 连续观察
2. 补故障排查与状态文件维护规则
3. 争取至少一次真实 mixed-corpus graph 闭环证据
4. 再评估 cross-platform preview

## 一句话结论

下一条里程碑不该先定义成“跨平台”，而应定义成：

`MemArk Beta+1: reliable unattended dogfood plus one real mixed-corpus graph proof.`
