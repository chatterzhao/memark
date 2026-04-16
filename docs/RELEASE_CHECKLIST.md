# Release Checklist

本文件用于回答一个具体问题：

当前 `MemArk` 是否可以按“当前仓库自己吃自己”的 Beta 口径发布。

Gitflow 的 `develop -> release/* -> develop -> main -> tag -> push` 正式发布顺序不在本文重复定义，统一以
[`docs/GITFLOW_RELEASE_FLOW.md`](<repo-root>/docs/GITFLOW_RELEASE_FLOW.md) 为准。

这里的“发布”不是 GA，也不是全平台正式生产承诺，而是：

- 当前仓库
- 当前维护者
- 少量项目
- macOS 优先
- 可接受受控试运行与持续观察

## 使用方式

每次准备把当前版本作为 Beta 对外说明或内部推广时，按下面顺序检查：

1. 自动化测试是否通过
2. 用户级安装链路是否通过
3. 当前仓库 dogfood 链路是否通过
4. 后台调度证据是否成立
5. 文档口径是否仍然准确
6. 未承诺项是否没有被误写成已完成
7. Gitflow 发布动作是否将按 [`docs/GITFLOW_RELEASE_FLOW.md`](<repo-root>/docs/GITFLOW_RELEASE_FLOW.md) 执行

如果其中任一关键项失败，就不要把当前版本表述为“当前 Beta 可发布”。

## A. 自动化测试

- [ ] `python3 -m unittest discover -s tests -p 'test_*.py' -q` 通过
- [ ] `python3 -m memark --help` 可运行
- [ ] `python3 -m memark automation-status --help` 可运行

## B. 用户级安装

- [ ] `memark install` 仍可完成用户级 runtime 安装
- [ ] `memark doctor` 返回 `ok`
- [ ] 用户级 runtime 中可找到：
  - `memark`
  - `mempalace`
  - `graphify`
- [ ] skill bundle 仍可安装到目标平台目录

## C. 当前仓库 Dogfood

- [ ] 当前仓库已完成 `memark init . --auto` 接入
- [ ] `python3 -m memark automation-run --workspace . --no-build --json` 可完成
- [ ] `automation-run` 后已生成：
  - `latest-summary.md`
  - `decisions-digest.md`
  - `risks-digest.md`
  - `ai-context.md`
  - `graphify-status.md`
- [ ] `python3 -m memark context --workspace . --json` 可读取统一消费入口
- [ ] `python3 -m memark query "<topic>" --workspace . --project memark --json` 可返回项目语料命中

## D. 后台调度

- [ ] `python3 -m memark service-install --workspace . --scheduler launchd --interval-seconds 300 --json` 成功
- [ ] `python3 -m memark service-status --workspace . --scheduler launchd --json` 返回：
  - `installed: true`
  - `loaded: true`
  - `last_cycle` 存在
- [ ] `launchctl print gui/$(id -u)/<label>` 可看到：
  - `runs` 存在
  - `last exit code = 0`
- [ ] 手动 `launchctl kickstart -k ...` 后，`.memark/state/automation-run.json` 的时间戳推进
- [ ] 验证结束后已执行 `service-uninstall`

## E. 文档口径

- [ ] `README.md` 仍明确区分：
  - `install`
  - `init --auto`（一键接入）
  - `init`（交互式）/ `project-set`（逐步控制）
- [ ] `SKILL.md` 仍只承担安装入口职责
- [ ] `docs/MILESTONE_BETA.md` 仍与当前真实能力一致
- [ ] `docs/DOGFOOD_STATUS.md` 与 `docs/INSTALL_VERIFICATION.md` 已更新到最新 smoke 结果

## F. 不承诺项复查

发布前必须再次确认下面这些话没有被误写成已完成：

- [ ] 没有声称 promoted markdown 已稳定进入完整 Graphify 图谱
- [ ] 没有声称长期后台无人值守稳定性已完成验证
- [ ] 没有声称全平台统一 scheduler backend 已完成
- [ ] 没有声称安装后任意项目会自动完成接入
- [ ] 没有把当前 Beta 写成 GA 或正式生产完成

## G. Beta 发布结论

只有在下面两条同时满足时，当前版本才可以按 Beta 口径发布：

- [ ] A-D 的关键验证项都通过
- [ ] E-F 的文档与口径复查都通过

## 当前推荐结论模板

如果本清单通过，建议使用下面这种表述：

`MemArk is currently ready for controlled macOS beta dogfood on this repo and similar small-scale projects.`

如果本清单未通过，建议使用下面这种表述：

`MemArk remains in active dogfood and should not yet be described as beta-ready for controlled release.`
