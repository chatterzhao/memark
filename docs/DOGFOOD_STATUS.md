# Dogfood Status

本文件只回答一个问题：

当前 `memark` 仓库自己吃自己这套系统，究竟验证到了哪一步。

这里明确区分三类状态：

- `真实狗粮已验证`：已经在当前仓库或真实用户目录里跑通过
- `自动化测试已验证`：CLI / 测试已覆盖，但没有对应的真实 dogfood 证据
- `尚未闭环验证`：当前还不能声称已经吃通

## 总结

当前最准确的判断是：

- `喂数据`：真实狗粮已验证
- `加工数据`：真实狗粮已验证
- `本地消费`：部分真实狗粮已验证
- `自动消费产物生成`：真实狗粮已验证
- `Graphify 统一消费闭环`：尚未闭环验证

更短地说：

- `MemPalace search / wake-up` 这条消费链已经吃到
- `MemArk promoted corpus + memark query` 这条消费链已经吃到
- `promoted markdown -> Graphify graph -> AI 统一消费` 这条链还没有吃到

补充一条 `2026-04-11` 的最新真实状态：

- 当前仓库再次执行 `python3 -m memark automation-run --workspace . --no-build --json`
- 本轮状态为 `completed`
- `palace_drawers` 已推进到 `1033`
- `packages` 为 `18`
- `promoted_changed` 为 `1`
- 自动消费产物继续刷新
- `graphify_status` 仍然是 `not_requested`

这说明当前仓库“持续自己吃自己”的单次前台自动 cycle 仍然是活的，但也再次说明 mixed-corpus `Graphify` 闭环还没有被这条链自动接住

同一天又补到一段新的后台证据：

- 当前仓库重新安装了 `launchd` job
- 手动 `kickstart` 后，`launchctl print` 显示：
  - `runs = 2`
  - `last exit code = 0`
- `automation-status` 推进到新的后台时间戳：
  - `started_at = 2026-04-11T07:15:30.282252+00:00`
  - `finished_at = 2026-04-11T07:15:33.372408+00:00`
- `palace_drawers` 进一步推进到 `1043`
- 当前选择是不卸载该 job，让当前仓库继续进入持续 dogfood 观察

对应时间线已追加到 [`docs/DOGFOOD_LOG.md`](<repo-root>/docs/DOGFOOD_LOG.md)

同一天还补了一个直接从真实 dogfood 中长出来的运维需求：

- 之前的 `service-status` 只能回答“装没装”
- 但对持续 dogfood 来说，更需要回答“后台现在健不健康、有没有 stale”
- 当前已补到：
  - 实际 `interval_seconds`
  - `stdout_bytes`
  - `stderr_bytes`
  - `health`
  - `observations`

当前仓库真实输出已能直接看到：

- `installed = true`
- `loaded = true`
- `interval_seconds = 300`
- `health = ok`
- `observations = ["last completed cycle age: ...s"]`

同一天又把这层观测继续收口成里程碑判断入口：

- 当前执行 `python3 -m memark milestones --workspace .`
- 现可直接返回 `Current milestone assessment: ready`
- 当前真实检查已全部通过：
  - 后台 scheduler 健康
  - automation 最近完成
  - 本地 mixed corpus 已存在
  - 自动消费产物已生成
  - mixed-corpus graph closure 已被自动识别

这让 `M1` 不再只是文档判断，而是 CLI 可直接读出的实时阶段判断。

同一天又补上一层更接近产品闭环的状态面：

- 当前新增 `python3 -m memark graphify-proof --workspace .`
- 它用于在上游 `Graphify` skill 真实 ingest 当前 `corpus/<project>` 后，把证据写回 `.memark/state`
- 现在即使不走上游 slash skill，`python3 -m memark build --workspace .` 也会在 `corpus/<project>/graphify-out/` 生成 mixed-corpus graph
- 同时现在也能通过 `python3 -m memark slash --workspace . /graphify . --update` 走 `MemArk` 自己的 slash-compatible adapter surface
- 只要该 graph 里真实包含来自 `promoted/project/imports` 的节点，系统就会自动识别这条 proof
- 当前仓库已实测进入：
  - `graphify_proof.status = ingested`
  - `M1 = ready`

这样后续一旦补到真实 mixed-corpus ingestion 证据，里程碑判断会直接变成系统状态，而不是再改文档口径。

同一天又把 mixed-corpus `Graphify` 的前置接入做成了真实可执行入口：

- 新增 `python3 -m memark graphify-onboard --workspace .`
- 当前仓库已真实执行成功，目标目录是：
  - `corpus/memark`
- 当前真实落盘结果：
  - `corpus/memark/AGENTS.md`
  - `corpus/memark/.codex/hooks.json`

这说明当前仓库已经不只是“知道应该对 corpus 跑 Graphify”，而是已经把上游 Graphify 的项目级接入真正装到了正确目录。

当前状态已经变成：

- `corpus/memark/graphify-out/graph.json` 已存在
- `corpus/memark/graphify-out/GRAPH_REPORT.md` 已存在
- `graphify_corpus_status = ingested`
- workspace root 仍保留旧的 code-only graph，但 corpus graph 已是 mixed-corpus
- `M1 = ready`

同一天又把这条 blocker 推进到了默认消费面：

- 当前重新执行 `python3 -m memark automation-run --workspace . --no-build --json`
- 随后 `python3 -m memark context --workspace . --no-refresh` 已可直接看到：
  - `graphify_corpus_status: ingested`
  - `graphify_onboarding_status: onboarded`
  - `graphify_proof_diagnostics: mixed_corpus_detected`
- `graphify-status` artifact 也已直接写出：
  - `corpus_status`
  - `onboarding_status`
  - `graph_path`
  - 推荐上游命令 `/graphify <repo-root>/corpus/memark --update`

这意味着当前仓库日常“自己吃自己”时，不用再额外翻 `status` 或 `milestones`，只读 `context` 就能看见 mixed-corpus graph 已经吃通。

## 一、真实狗粮已验证

### A1. 用户级安装闭环

证据来源：

- [`docs/INSTALL_VERIFICATION.md`](<repo-root>/docs/INSTALL_VERIFICATION.md)

已真实验证：

- 在 fake `HOME` 下成功执行 `memark install`
- 成功生成用户级 runtime
- 成功生成 AI skill bundle
- `memark doctor` 返回 `ok`
- runtime 内 `mempalace`、`graphify` 可执行

结论：

- 安装器不只是文档存在，已经有真实安装闭环

### A2. 当前仓库 `Codex sessions -> staging -> palace`

证据来源：

- [`docs/INSTALL_VERIFICATION.md`](<repo-root>/docs/INSTALL_VERIFICATION.md)

已真实验证：

- 在当前仓库执行 `projects-run`
- 实测得到：
  - `scanned: 1053`
  - `matched: 14`
  - `copied: 14`
  - `mined: true`
  - `mine_elapsed_seconds: 47.651`

结论：

- 当前仓库的会话 intake 主链是真跑过的

### A3. 当前仓库 palace 可搜索

证据来源：

- [`docs/INSTALL_VERIFICATION.md`](<repo-root>/docs/INSTALL_VERIFICATION.md)
- [`docs/AI_CONSUMPTION_MODEL.md`](<repo-root>/docs/AI_CONSUMPTION_MODEL.md)

已真实验证：

- 当前仓库 palace 状态为 `403 drawers`
- `mempalace search "worktree"` 能命中当前项目真实会话内容
- `mempalace wake-up` 能输出当前项目的压缩历史脉络

结论：

- `MemPalace` 作为“历史找回层”的真实消费已经吃到

### A4. 当前仓库会话晋升

证据来源：

- [`docs/AI_CONSUMPTION_MODEL.md`](<repo-root>/docs/AI_CONSUMPTION_MODEL.md)
- [`docs/ACCEPTANCE_CHECKLIST.md`](<repo-root>/docs/ACCEPTANCE_CHECKLIST.md)

已真实验证：

- `memark palace-package --group-by session` 在当前仓库 palace 中，能把 `802` 个 drawer 重新整理成 `14` 个会话级 package
- 当前仓库已经产出实际 `promoted/*.md`

结论：

- 从原始项目会话到项目级候选知识，这条加工链已经吃到

### A5. worktree 接入链路

证据来源：

- [`docs/INSTALL_VERIFICATION.md`](<repo-root>/docs/INSTALL_VERIFICATION.md)

已真实验证：

- 无 hook 的 worktree 可手动 attach
- 安装 hook 后，新建 worktree 会自动复制 `.memark/config.json` 与 `.memark/projects.toml`
- 新 worktree 的 `projects-run` 可单独识别该目录 session
- 实测得到：
  - `matched: 1`
  - `copied: 1`
  - `mined: true`
  - palace 状态为 `2 drawers`

结论：

- worktree 接入主链也已经吃到

## 二、自动化测试已验证

### B1. CLI 回归

当前测试状态：

- `python3 -m unittest discover -s tests -p 'test_*.py' -q`
- 最近一次实测结果：
  - `Ran 56 tests in 28.497s`
  - `OK`

覆盖范围主要包括：

- install / doctor
- codex-sync
- project-set / projects-run
- mempalace-mine / palace ops
- palace-package / palace-run
- query / graphify-handoff
- worktree attach / hook install
- launchd service install / status / uninstall

结论：

- CLI 主链回归是稳的
- 但自动化通过不等于真实狗粮已经全部吃通

## 三、部分真实验证，但还不能夸大

### C1. 本地项目语料消费

已真实成立：

- `memark query` 这条本地消费入口已经有实现，也有自动化验证
- 当前 promoted markdown 已经在当前仓库真实落盘

但当前文档里还没有足够强的真实记录去证明：

- 项目 AI 在多个真实任务中，已经稳定依赖 `memark query` 而不是手工读文件

结论：

- 可以说“本地消费入口已可用”
- 还不宜说“项目 AI 已持续依赖该入口并显著变好”

### C2. intake service

在 `2026-04-10` 的当前用户机器上，已经补到一段真实狗粮记录。

已真实成立：

- `memark service-install --workspace . --scheduler launchd --interval-seconds 300 --json` 成功安装用户级 `launchd` job
- `memark service-status --workspace . --scheduler launchd --json` 能正确返回 `installed: true`、`loaded: true`
- `launchctl print gui/501/io.memark.projects-run.memark.3897640fdb` 可看到真实 `ProgramArguments`、`WorkingDirectory`、`StartInterval: 300`
- 当前 `ProgramArguments` 已对齐到 `memark automation-run --workspace ...`
- `memark service-uninstall --workspace . --scheduler launchd --json` 成功返回 `removed: true`、`unloaded: true`
- 卸载后再次执行 `service-status`，已回到 `installed: false`、`loaded: false`

后续又补到一段更强的真实验证：

- 先执行前台 `python3 -m memark automation-run --workspace . --no-build --json`
- 再执行 `memark service-install --workspace . --scheduler launchd --interval-seconds 300 --json`
- `service-status --json` 已能返回 `last_cycle.status = completed`
- `last_cycle.started_at` / `finished_at` 会推进到新的后台运行时间
- `launchctl print gui/501/io.memark.projects-run.memark.3897640fdb` 可见：
  - `runs = 3`
  - `last exit code = 0`
- 手动 `launchctl kickstart -k ...` 后，`.memark/state/automation-run.json` 会更新为新的时间戳
- 同一次后台 cycle 里，`palace_drawers` 从 `1014` 推进到 `1024`
- `intake.mined` 也重新回到 `true`
- 对应 stdout / stderr 日志文件不再是 `0 bytes`

结论：

- 可以说“`launchd` 的安装 / 状态查询 / 卸载已在真实机器上验证”
- 可以说“默认调度目标已经从 intake 半链路升级到 `automation-run`”
- 现在也可以说“当前仓库已经拿到真实后台 `launchd -> automation-run -> automation-run.json` 完成证据”
- 但还不能说“当前仓库已经稳定靠后台 `launchd` 长期持续喂数”
- 目前更准确的表述是：单次后台自动 cycle 已真实打通，长期稳定性仍未验证完

### C2.1. 后台健康观测面已补齐一层

在 `2026-04-11` 的真实后台运行基础上，又补了 `service-status` 的健康观测：

- 读取已安装 plist 的实际 `StartInterval`
- 暴露 stdout / stderr 日志字节数
- 根据 `last_cycle.finished_at` 判断是否 stale
- 把结果收敛成 `health`

当前可用的健康状态至少包括：

- `ok`
- `stale`
- `failing`
- `running`
- `not_loaded`
- `not_installed`

结论：

- 当前后台 dogfood 已不只是“有无安装”
- 维护者已经可以直接看“后台是否健康”
- 这对下一阶段长期稳定性里程碑是实打实的推进

### C3. 自动消费产物

在 `2026-04-10` 的当前仓库真实 smoke 里，已执行：

- `python3 -m memark automation-run --workspace . --no-build --json`

已真实成立：

- 单次自动 cycle 能串起 intake、palace package、promotion、消费产物生成
- 当前仓库真实落出了：
  - `latest-summary.md`
  - `decisions-digest.md`
  - `risks-digest.md`
  - `ai-context.md`
  - `graphify-status.md`
- 同一轮 smoke 也确认了一个重要治理边界：
  - 自动文档同步若不加限制，会把 `.experiments/`、`build/`、`.pytest_cache/`、`*.egg-info/`、`docs/raw/` 这类噪音一起带进消费侧
  - 当前实现已补过滤，自动消费优先基于正式项目文档

结论：

- 可以说“自动消费产物生成已在当前仓库真实跑通”
- 但还不宜说“AI runtime 已自动读取这些产物并因此持续变好”

在 `2026-04-11` 又补了一轮真实前台 dogfood：

- `python3 -m memark automation-run --workspace . --no-build --json`
- `python3 -m memark automation-status --workspace . --json`
- `python3 -m memark context --workspace . --json`

本轮实测结果：

- `automation-status.status = completed`
- `project_count = 1`
- `documents.unchanged = 26`
- `intake.updated = 1`
- `intake.mined = true`
- `palace_drawers = 1033`
- `packages = 18`
- `promoted_changed = 1`
- `context` 仍可一次读到 `latest-summary`、`decisions-digest`、`risks-digest`、`ai-context`、`graphify-status`

结论补充：

- 当前仓库不仅在 `2026-04-10` 跑通过，也在 `2026-04-11` 继续跑通
- 这更接近“持续自己吃自己”的状态
- 但仍然属于单机受控 dogfood，不应夸大成长期无人值守稳定性已完成验证

### C4. 当前后台 dogfood 已重新挂起

在 `2026-04-11` 又执行：

- `python3 -m memark service-install --workspace . --scheduler launchd --interval-seconds 300 --json`
- `launchctl kickstart -k gui/$(id -u)/io.memark.projects-run.memark.3897640fdb`
- `python3 -m memark service-status --workspace . --scheduler launchd --json`

本轮实测结果：

- `installed = true`
- `loaded = true`
- `service-status.last_cycle` 已推进到新的后台 cycle
- `launchctl print` 返回 `last exit code = 0`
- stdout / stderr 日志都已是非零字节
- 当前没有执行 `service-uninstall`

结论：

- 当前仓库现在不是“验证完就拆掉”
- 而是已经重新进入持续后台 dogfood 观察阶段
- 但还需要连续多天证据，才能升级成“长期稳定性已验证”

## 四、尚未闭环验证

### D1. `promoted markdown -> Graphify graph`

证据来源：

- [`docs/AI_CONSUMPTION_MODEL.md`](<repo-root>/docs/AI_CONSUMPTION_MODEL.md)
- [`docs/FEATURE_LIST.md`](<repo-root>/docs/FEATURE_LIST.md)
- [`docs/ACCEPTANCE_CHECKLIST.md`](<repo-root>/docs/ACCEPTANCE_CHECKLIST.md)

当前已知事实：

- `corpus/memark/graphify-out/graph.json` 已被 `MemArk` 本地 mixed-corpus builder 更新
- 当前 dogfood 状态里：
  - `total_nodes = 548`
  - `mixed_corpus_nodes = 474`
- workspace root 旧 `graphify-out/graph.json` 仍是 code-only graph

结论：

- 当前仓库已经真实证明 `MemArk` 可在 corpus 级别完成 mixed-corpus graph 更新

### D2. AI 因此明显变好

当前还没有真实闭环证据证明：

- 相比“不使用 MemArk”，项目 AI 明显减少重复讨论
- 项目 AI 明显更稳定找回历史决策
- 项目 AI 已从同一查询面同时消费代码结构和会话知识

结论：

- 这条产品价值判断目前还是“方向成立，最终闭环未完成”

## 五、当前最准确的话术

当前可以直接说：

- `MemArk` 已经在当前仓库上真实跑通了项目会话 intake、palace ingest、session packaging 和 promoted markdown 落盘
- `MemPalace search / wake-up` 已经能真实消费这些项目历史
- `MemArk` 也已经提供了本地项目语料消费入口

当前不应该说：

- `Graphify` 已稳定把 promoted session markdown 编进图谱
- AI 已只靠一个统一图谱入口同时消费代码和会话知识
- 整个“自动喂数据 -> 自动加工 -> 自动消费”闭环已经完全狗粮验证完毕

## 六、下一步最值得补的真实验证

如果要继续提高狗粮可信度，优先级应是：

1. 真实安装并运行 `memark service-install`，观察一段时间后的持续 intake 效果
2. 对当前仓库记录至少 2-3 个真实任务，证明 `memark query` 被实际用于续接项目工作
3. 验证或补出一条真正可运行的 `promoted markdown -> Graphify` 消费路径
4. 再比较“使用 MemArk / 不使用 MemArk”两种情况下的项目 AI 延续性差异
