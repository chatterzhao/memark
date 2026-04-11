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

## 一、真实狗粮已验证

### A1. 用户级安装闭环

证据来源：

- [`docs/INSTALL_VERIFICATION.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/INSTALL_VERIFICATION.md)

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

- [`docs/INSTALL_VERIFICATION.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/INSTALL_VERIFICATION.md)

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

- [`docs/INSTALL_VERIFICATION.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/INSTALL_VERIFICATION.md)
- [`docs/AI_CONSUMPTION_MODEL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/AI_CONSUMPTION_MODEL.md)

已真实验证：

- 当前仓库 palace 状态为 `403 drawers`
- `mempalace search "worktree"` 能命中当前项目真实会话内容
- `mempalace wake-up` 能输出当前项目的压缩历史脉络

结论：

- `MemPalace` 作为“历史找回层”的真实消费已经吃到

### A4. 当前仓库会话晋升

证据来源：

- [`docs/AI_CONSUMPTION_MODEL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/AI_CONSUMPTION_MODEL.md)
- [`docs/ACCEPTANCE_CHECKLIST.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/ACCEPTANCE_CHECKLIST.md)

已真实验证：

- `memark palace-package --group-by session` 在当前仓库 palace 中，能把 `802` 个 drawer 重新整理成 `14` 个会话级 package
- 当前仓库已经产出实际 `promoted/*.md`

结论：

- 从原始项目会话到项目级候选知识，这条加工链已经吃到

### A5. worktree 接入链路

证据来源：

- [`docs/INSTALL_VERIFICATION.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/INSTALL_VERIFICATION.md)

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

同一次验证里，也明确看到一个尚未解决的真实问题：

- 对该 job 执行 `launchctl kickstart -k` 后，`runs` 计数会增长
- 但本次观察窗口里，`.memark/state/projects-run.json` 没有跟着更新
- 对应 stdout/stderr 日志文件仍是 `0 bytes`
- 当时的后台 Python 进程一度持续存活，没有形成可直接引用的 cycle 完成证据

对照验证：

- 用接近 `launchd` 的最小环境前台执行
- `env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin ~/.memark/venv/bin/memark projects-run --workspace ... --json`
- 这条命令在同一台机器上是可完成的，并且能更新 `projects-run.json`

结论：

- 可以说“`launchd` 的安装 / 状态查询 / 卸载已在真实机器上验证”
- 可以说“默认调度目标已经从 intake 半链路升级到 `automation-run`”
- 也可以说“前台最小环境下的单次 cycle 没问题”
- 但还不能说“当前仓库已经稳定靠后台 `launchd` 持续喂数”
- 目前更准确的表述是：真实狗粮已经把后台调度问题暴露出来，但持续 intake 闭环仍未验证完

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

## 四、尚未闭环验证

### D1. `promoted markdown -> Graphify graph`

证据来源：

- [`docs/AI_CONSUMPTION_MODEL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/AI_CONSUMPTION_MODEL.md)
- [`docs/FEATURE_LIST.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/FEATURE_LIST.md)
- [`docs/ACCEPTANCE_CHECKLIST.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/ACCEPTANCE_CHECKLIST.md)

当前已知事实：

- `graphify.detect()` 能看到 `promoted/*.md`
- 但 `graphify.extract()` 公开入口只处理代码
- 当前 `graphify-out/graph.json` 里 `document_nodes = 0`
- 当前 `graphify-out/graph.json` 里 `promoted_nodes = 0`

结论：

- 还不能声称 `Graphify` 已稳定消费 `MemArk` 晋升文档

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
