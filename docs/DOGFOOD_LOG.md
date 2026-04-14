# Dogfood Log

本文件按时间记录当前 `memark` 仓库自己吃自己的关键证据。

它不替代 [`docs/DOGFOOD_STATUS.md`](<repo-root>/docs/DOGFOOD_STATUS.md)。

更准确的分工是：

- `DOGFOOD_STATUS.md`：当前阶段判断
- `DOGFOOD_LOG.md`：按时间追加的真实运行证据

## 2026-04-10

- 前台执行 `python3 -m memark automation-run --workspace . --no-build --json`
- 成功产出：
  - `latest-summary.md`
  - `decisions-digest.md`
  - `risks-digest.md`
  - `ai-context.md`
  - `graphify-status.md`
- 安装 `launchd` job：
  - `python3 -m memark service-install --workspace . --scheduler launchd --interval-seconds 300 --json`
- `service-status.last_cycle` 可读
- `launchctl print` 可见：
  - `runs = 3`
  - `last exit code = 0`
- `.memark/state/automation-run.json` 时间戳推进
- `palace_drawers` 从 `1014` 推进到 `1024`
- 当日验证结束后执行了 `service-uninstall`

## 2026-04-11

### 前台 cycle

- 执行 `python3 -m memark automation-run --workspace . --no-build --json`
- `automation-status.status = completed`
- `palace_drawers = 1033`
- `packages = 18`
- `promoted_changed = 1`
- `context` 仍可读取自动整理后的 `summary / decisions / risks / graphify status`

### 后台 cycle

- 重新安装 `launchd` job：
  - `python3 -m memark service-install --workspace . --scheduler launchd --interval-seconds 300 --json`
- 当前 label：
  - `io.memark.projects-run.memark.3897640fdb`
- 执行：
  - `launchctl kickstart -k gui/$(id -u)/io.memark.projects-run.memark.3897640fdb`
- `launchctl print` 可见：
  - `runs = 2`
  - `last exit code = 0`
- 后台执行后 `automation-status` 推进到：
  - `started_at = 2026-04-11T07:15:30.282252+00:00`
  - `finished_at = 2026-04-11T07:15:33.372408+00:00`
  - `status = completed`
  - `palace_drawers = 1043`
  - `documents.unchanged = 30`
  - `graphify_status = pending_update`
- 对应日志文件已有非零内容：
  - `out.log = 3022 bytes`
  - `err.log = 840 bytes`

### 后台健康观测

- 基于持续 dogfood 的真实需要，补强了 `python3 -m memark service-status`
- 新增可直接读取：
  - 实际 `interval_seconds`
  - `stdout_bytes`
  - `stderr_bytes`
  - `health`
  - `observations`
- 当前仓库真实输出已看到：
  - `health = ok`
  - `interval_seconds = 300`
  - `stdout_bytes = 5290`
  - `stderr_bytes = 1470`
  - `observations = ["last completed cycle age: 126s"]`

### 里程碑账本入口

- 为了让“看里程碑就知道当前应用做了什么”不只停在文档层，补了：
  - `python3 -m memark milestones`
  - `python3 -m memark milestones --workspace .`
  - `python3 -m memark status --json` 中的 `milestones` 字段
- 当前真实输出已看到：
  - `achieved = M0`
  - `current = M1`
  - workspace snapshot 中已带：
    - `project = memark`
    - `service.health = ok`
    - 最近 `automation` 状态

### 当前决定

- 这次不执行 `service-uninstall`
- 保持 `launchd` job 继续运行
- 后续连续观察按 [`docs/DOGFOOD_RUNBOOK.md`](<repo-root>/docs/DOGFOOD_RUNBOOK.md) 执行
