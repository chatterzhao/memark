# Milestones

本文件把 `MemArk` 的里程碑当成“阶段能力账本”来维护。

目标不是只写阶段口号，而是回答两个更实际的问题：

- 当前应用已经做成了哪些能力
- 下一阶段具体还缺什么

如果以后想快速知道“这个应用现在有什么功能、已经做到哪一步”，优先读这里，再顺着链接下钻到各里程碑明细。

如果想直接从 CLI 看同样的信息：

```bash
python3 -m memark milestones
python3 -m memark milestones --workspace .
```

第二条会把当前 workspace 的实时证据也带上，例如：

- 当前 project
- promoted/project/imports 规模
- 最近 automation 状态
- 当前 scheduler health

现在它还会直接输出：

- 当前里程碑评估结果
- 已通过的检查项
- 还未满足的 blocker
- 下一步最该补什么

## 当前里程碑地图

### M0. Beta

定义文件：

- [`docs/MILESTONE_BETA.md`](<repo-root>/docs/MILESTONE_BETA.md)

当前阶段判断：

- 已达到
- 当前口径是 `macOS controlled beta dogfood`

这一阶段已经做成的核心能力：

- 用户级安装与运行时自检：`memark install`、`memark doctor`
- workspace 初始化与项目接入：`memark init`、`memark project-set`
- 会话 intake 与单次自动闭环：`memark codex-sync`、`memark projects-run`、`memark automation-run`
- `MemPalace` 运维入口：`mempalace-mine`、`palace-status`、`palace-clean`、`palace-rebuild`、`palace-retry`
- 会话晋升与 corpus 落盘：`palace-export`、`palace-package`、`palace-run`、`promote`、`project-set`
- 本地消费入口：`memark query`、`memark context`
- 调度与观测：`service-install`、`service-status`、`service-uninstall`、`automation-status`
- worktree 接入：`worktree-attach`、`worktree-hook-install`
- Graphify bridge：`graphify-handoff`
- autonomous mixed-corpus graph build：`build`、`run`、`automation-run`
- slash-compatible adapter surface：`slash`
- slash-compatible status observation：`slash /status`
- slash-compatible automation and proof observation：`slash /automation-status`、`slash /graphify-proof`
- 唯一正式 CLI 命令面：同一能力不再并存多种命令拼写

### M1. Beta+1

定义文件：

- [`docs/MILESTONE_NEXT.md`](<repo-root>/docs/MILESTONE_NEXT.md)

当前阶段判断：

- 进行中
- 当前重点不是跨平台，而是长期后台可靠性和真实消费闭环

这一阶段主攻的能力：

- 后台长期稳定运行证据
- `service-status` 健康观测与 stale/failing 判断
- mixed-corpus graph 真实闭环
- `graphify-proof` 让 mixed-corpus graph proof 成为可观测状态
- slash-only 能力通过 `MemArk` CLI 稳定适配
- slash-only 状态观测也能走统一 catalog 和执行面
- direct CLI surface 保持唯一正式命令名，避免 AI 自动调用漂移到多种拼写
- AI 自动消费真正减少重复劳动

### M2. Cross-platform Preview

当前还未进入实现主阶段。

预计范围：

- Linux `systemd` 或 `cron`
- Windows Task Scheduler
- 跨平台安装和状态查询体验收敛

## 如何维护

- 每新增一项用户可见能力，优先把它挂到对应里程碑
- 如果能力已经实现，但还没达到“阶段可宣称”，要同时写清：
  - 已做成什么
  - 还不能宣称什么
- 里程碑是阶段视角
- [`docs/FEATURE_LIST.md`](<repo-root>/docs/FEATURE_LIST.md) 是组件/能力视角
- [`docs/DOGFOOD_STATUS.md`](<repo-root>/docs/DOGFOOD_STATUS.md) 是真实验证视角
