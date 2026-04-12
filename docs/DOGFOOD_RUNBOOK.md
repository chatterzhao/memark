# Dogfood Runbook

本文件定义维护者如何让当前 `memark` 仓库持续自己吃自己，并且在出现问题时知道先看哪里。

目标不是一次性 smoke，而是：

- 当前仓库可以反复执行自动 cycle
- 当前仓库可以留下一段连续后台运行证据
- 维护者可以快速判断系统是在 intake、promotion、消费，还是 scheduler 这一层出了问题

## Git 工作方式

当前仓库长期 dogfood 时，优先按下面方式保持版本控制干净：

- 功能开发先开分支，再改代码
- 需要并行推进另一块功能时，优先新开 worktree，而不是把多个主题堆在同一个工作树
- 连续后台 dogfood 最好放在专用 worktree，避免主工作树持续生成运行时产物
- `dogfood/runtime` 要定期消费 `develop`，但不要在这个工作树里承接普通 feature 开发

一个可直接复用的方式是：

```bash
git worktree add ../memark-dogfood feature/dogfood-runtime
cd ../memark-dogfood
python3 -m memark automation-run --workspace . --no-build --json
```

如果只是要保留当前仓库的 dogfood 运行，不想新开 worktree，也至少保持：

- `.memark/`、`.mempalace/`、`graphify-out/` 这类运行时目录不入库
- `corpus/<project>/documents/`、`imports/`、`.codex/`、`AGENTS.md` 这类自动生成产物不入库
- 时间戳型 dogfood rollout 文件默认不入库；如果确实要保留，显式挑选后再提交

当前仓库已经进一步收口为：

- `develop` 负责功能主线
- `dogfood/runtime` 负责持续运行验证
- 时间戳型 `corpus/<project>/promoted/room-*-rollout-*.md` 已从版本控制退出，只作为本地 dogfood 产物存在

## 同步 dogfood/runtime

`dogfood/runtime` 的目标是消费最新主线能力，而不是偏离出自己的功能分叉。

推荐做法：

```bash
cd /Users/zhaoyu/Downloads/code/my-memark/memark-dogfood
git status --short
git merge develop
python3 -m memark service-status --workspace . --scheduler launchd --json
python3 -m memark milestones --workspace . --json
```

同步后重点确认：

- `dogfood/runtime` 与 `develop` 没有提交差距
- `service-status.health` 是 `ok` 或至少不是 `not_installed`
- `milestones.assessment.status` 仍是 `ready` 或至少没有新增回归

如果 dogfood 工作树里存在本地 rollout 文件，不要把它们重新纳入 git；保持它们作为被忽略的本地运行产物即可。

## 日常入口

先确认机器级安装健康：

```bash
python3 -m memark doctor --platform codex --json
```

再确认当前 workspace 最近状态：

```bash
python3 -m memark milestones
python3 -m memark milestones --workspace .
python3 -m memark automation-status --workspace . --json
python3 -m memark context --workspace . --json
python3 -m memark service-status --workspace . --scheduler launchd
```

如果只想手工推进一轮当前仓库 dogfood：

```bash
python3 -m memark automation-run --workspace . --no-build --json
```

如果要补齐 `M1` 证据，而不是只刷新 intake/promotion，可以直接执行：

```bash
python3 -m memark build --workspace .
python3 -m memark automation-run --workspace .
python3 -m memark consumption-proof --workspace . --record-verified \
  --command "python3 -m memark context --workspace . --json"
python3 -m memark milestones --workspace . --json
```

## 持续后台观察

如果要验证后台链路，而不是只做前台 smoke：

```bash
python3 -m memark service-install \
  --workspace . \
  --scheduler launchd \
  --interval-seconds 300 \
  --json

python3 -m memark service-status \
  --workspace . \
  --scheduler launchd \
  --json
```

观察重点不是“安装成功”四个字，而是：

- `installed: true`
- `loaded: true`
- `health: ok`
- `interval_seconds` 与你期望的一致
- `last_cycle` 存在
- `last_cycle.finished_at` 在推进
- `.memark/state/automation-run.json` 在推进

如果需要强制触发一轮后台执行：

```bash
launchctl kickstart -k gui/$(id -u)/io.memark.projects-run.memark.3897640fdb
```

验证结束后，如果不想继续挂后台 job：

```bash
python3 -m memark service-uninstall --workspace . --scheduler launchd --json
```

## 关键观测面

优先检查下面这些位置：

- 状态文件：`.memark/state/automation-run.json`
- staging：`.memark/staging/memark/sessions/`
- palace：`.memark/palaces/memark/`
- promoted：`corpus/memark/promoted/`
- documents：`corpus/memark/documents/`
- automation imports：`corpus/memark/imports/automation/`

当前最重要的五个自动消费产物是：

- `latest-summary.md`
- `decisions-digest.md`
- `risks-digest.md`
- `ai-context.md`
- `graphify-status.md`

当前 `service-status` 还会直接给出：

- `health`
- `observations`
- `stdout_bytes`
- `stderr_bytes`
- 实际 `interval_seconds`

当前 `memark status --json` 还会带：

- `milestones.achieved`
- `milestones.current`

而 `memark milestones --workspace .` 会把里程碑账本和当前项目证据一起展示。

## 出问题时先怎么判断

### 1. `automation-status` 没推进

优先看：

- `python3 -m memark automation-status --workspace . --json`
- `python3 -m memark service-status --workspace . --scheduler launchd --json`

如果 `service-status.health = stale`，优先判断：

- `launchd` job 是否还在跑
- `last_cycle.finished_at` 是否已经超过当前 interval 的两倍以上
- `launchctl print` 的 `runs` 是否继续增长

如果 `service-status` 里没有 `last_cycle`，先判断是：

- job 没装上
- job 没加载
- job 装上了但没真正跑

### 2. intake 没推进

优先看：

- `matched`
- `updated`
- `invalid`
- `intake.mined`

如果 `matched` 长期不变，先检查：

- `project-set` 的 `path`
- `sessions_root`
- 当前 session 的 `cwd` 是否仍落在该项目目录下

### 3. promotion 没推进

优先看：

- `packages`
- `promoted_changed`
- `promoted_unchanged`

如果 session 在变，但 `promoted_changed` 长期是 `0`，先检查：

- palace 是否真的新增了可用 drawers
- 当前 grouping 是否过粗
- 变化是否只落在无价值或被忽略内容上

如果 `promoted_changed` 主要来自时间戳 rollout 文件，先不要把它当成需要提交的代码变更。先确认：

- 这些变化是否只是 dogfood 持续运行导致的内容刷新
- 当前需要保留的正式 promoted 文档是否已经另有稳定文件名版本

### 4. 自动消费产物没更新

优先看：

- `corpus/memark/imports/automation/`
- `memark context --workspace . --json`

如果 `context` 没刷新，但 `automation-run` 成功，先怀疑：

- 产物生成逻辑没有拿到新的 promoted/document 输入
- 输入被过滤规则排掉

### 5. Graphify 仍然是 `not_requested` 或 `pending_update`

这不一定是故障。

当前更准确的理解是：

- `MemArk` 已经能把 `Graphify-ready corpus` 整理出来
- 但 mixed-corpus 的真实上游消费还没有被当前仓库稳定自动化接住

所以这一项当前主要是里程碑缺口，不一定是实现 bug。

### 6. `service-status` 直接提示 `not_loaded` / `failing`

优先看：

- `launchctl print gui/$(id -u)/<label>`
- `.memark/logs/*.out.log`
- `.memark/logs/*.err.log`

如果 `health = failing`，优先回到：

- `automation-status.error`
- `last_cycle.results[*].graphify_status`
- intake 的 `mine_skipped_reason` / `mined`

## 维护规则

- 不要把 `docs/raw/`、缓存、构建产物、实验目录重新喂回系统
- 不要把派生产物误写成“已经进入完整图谱”
- 每次做完真实 smoke，更新 `docs/DOGFOOD_STATUS.md`
- 每次准备对外说明 Beta 状态，先过 `docs/RELEASE_CHECKLIST.md`

## 当前仓库建议节奏

如果要让当前仓库持续自己吃自己，建议按下面节奏维护：

1. 每次较大改动后执行一次前台 `automation-run`
2. 每天至少看一次 `automation-status`
3. 阶段性开启 `launchd` 连续观察 3-7 天
4. 每得到新证据，就写回 `DOGFOOD_STATUS.md`
