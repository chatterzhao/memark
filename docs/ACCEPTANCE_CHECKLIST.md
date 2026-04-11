# Acceptance Checklist

本文件定义当前版本 `MemArk` 的验收标准。

验收对象不是“未来完整产品”，而是当前这版 `CLI-first` 实现，以及已经接上的：

- 用户级安装与 skill bundle
- `Codex session intake + MemPalace convo mine`
- `MemPalace -> package -> promote -> Graphify-compatible build`

## A. 仓库与入口

- [x] 仓库内存在真实的 Python 包，而不是只剩文档
- [x] 存在 `python3 -m memark` 入口
- [x] 存在 console script 定义 `memark`
- [x] 不再引用仓库里不存在的 `memark.py`
- [x] 根目录 [`SKILL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/SKILL.md) 已收敛为生产安装入口
- [x] [`skill-dev.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/skill-dev.md) 已收敛为开发期隔离安装验收入口

## B. 用户级安装与技能包

- [x] `memark install` 可创建用户级 runtime venv
- [x] 默认用户级 runtime 目录为 `~/.memark/venv`
- [x] `memark install` 会自动选择兼容的 Python 运行时版本，而不是盲目使用当前系统 `python3`
- [x] `memark install` 会安装 `MemArk`、`mempalace`、`graphifyy`
- [x] `memark install` 支持 `--platform auto|codex|claude|all`
- [x] `memark install` 可把运行时 skill bundle 安装到用户 AI 工具目录
- [x] Codex 目标目录为 `~/.agents/skills/memark/`
- [x] Claude 目标目录为 `~/.claude/skills/memark/`
- [x] skill bundle 至少包含 `SKILL.md`
- [x] skill bundle 至少包含 `project.md`
- [x] skill bundle 至少包含 `doctor.md`
- [x] skill bundle 至少包含 `bin/memark`
- [x] skill bundle 至少包含 `bin/memark.cmd`
- [x] 安装结果包含 `manifest.json`
- [x] 安装后的 `bin/memark` 已具备可执行位
- [x] `memark doctor` 能检查 runtime 与 skill bundle
- [x] `memark doctor` 在缺失 runtime 时会失败
- [x] `memark doctor` 在 runtime Python 超出支持版本时会失败
- [x] `memark doctor` 在 fake runtime + installed bundle 场景下会成功

## C. 工作区初始化

- [x] `memark init` 可创建工作区
- [x] 初始化时会创建 `.memark/config.json`
- [x] 初始化时会创建 `inbox/`
- [x] 初始化时会创建 `inbox/promoted/`
- [x] 初始化时会创建 `inbox/documents/`
- [x] 初始化时会创建 `corpus/<project>/promoted`
- [x] 初始化时会创建 `corpus/<project>/documents`
- [x] 初始化时会创建 `corpus/<project>/imports`

## D. 输入契约与治理

- [x] `memark validate` 可以校验 room package JSON
- [x] 默认只允许 `wing_kind=project` 的 package 晋升
- [x] 不把“闲聊/general wing”默认送进 `Graphify`
- [x] room package 缺少关键字段时会失败而不是静默继续

## E. 已实现晋升逻辑

- [x] `memark promote` 能把 room package 落成 Markdown
- [x] Markdown 保留 frontmatter 边界信息
- [x] Markdown 包含 `room summary`、`closets`、`evidence`
- [x] 输出路径稳定且可重复覆盖
- [x] 同一 room 重复导入时具备幂等行为
- [x] 可选把已消费 JSON 归档到 `.memark/archive`

## F. 已实现文档纳入

- [x] `memark add-documents` 能把已落盘文档复制进 corpus
- [x] 文档和晋升 room 会落在同一项目 corpus 边界内

## G. 已实现 Graphify 集成

- [x] `memark build` 会调用外部配置的 Graphify 构建入口
- [x] 当顶层 `graphify <folder>` 不可用时，`memark build` 会退回已验证的 code-only fallback
- [x] `memark build` 支持 `--update`
- [x] `memark build` 支持 `--wiki`
- [x] `memark build` 支持 `--obsidian`
- [x] `memark build` 支持 `--mcp`
- [x] 当 `graphify` 不存在时会明确报错
- [x] 当遇到 helper/query 型 `graphify` CLI 且 fallback 不可用时会明确报错
- [x] `memark run` 能串联 promote + build
- [x] `memark run` 会先消费 `inbox/promoted` 与 `inbox/documents`
- [x] `memark mempalace-mine` 能调用 `mempalace mine --mode convos`
- [x] `memark mempalace-mine` 支持 `--dry-run`
- [x] `memark mempalace-mine` 在 `mempalace` 不存在时会明确报错
- [x] `memark mempalace-mine` 会在明确的数据库锁冲突上自动重试
- [x] `memark palace-status` 能输出项目级 palace 文件与 drawer 统计
- [x] `memark palace-clean` 能清空项目 palace 并重建空目录
- [x] `memark palace-rebuild` 能先 clean 再重跑 convo mine
- [x] `memark palace-retry` 能在不 clean 的情况下重试 convo mine
- [x] 当旧 palace / Chroma 兼容错误触发时，`MemPalace` 失败信息会明确提示 `palace-rebuild`
- [x] `memark palace-export` 能只读导出项目 palace 中的 drawer
- [x] `memark palace-package` 能把 palace drawer 按 room 整理成候选 room package
- [x] `memark palace-package --write-inbox` 能把候选 package 写回 `inbox/promoted`
- [x] `memark palace-run` 能把 palace package、promote、可选 build 串起来

## H. 不做伪实现

- [x] 不声明已实现 `MemPalace` 的增量拉取
- [x] 不声明已实现后台监控服务
- [x] 不声明已实现守护进程式同步
- [x] 不声明已实现 `MemPalace` 数据库稳定直连契约
- [x] 不把 `~/.codex/history.jsonl` 写成项目级默认输入
- [x] 不声称 `MemPalace` 会自动按项目拆分混合 `Codex` 会话

## I. 自动化验证

- [x] 存在自动化测试
- [x] 覆盖初始化、校验、晋升、幂等、归档、文档复制、Graphify 调用、状态输出
- [x] 覆盖用户级安装与 `doctor`
- [x] `memark status --json` 可输出机器可读状态
- [x] `.venv-dev/bin/python -m pytest -q` 通过
- [x] `python3 -m unittest discover -s tests -v` 通过
- [x] `python3 -m compileall memark tests` 通过

## J. 已实现的 Codex / MemPalace 编排验收项

- [x] 能扫描 `~/.codex/sessions/**/*.jsonl`
- [x] 能从 `session_meta.payload.cwd` 判断目录归属
- [x] 能把一个目录工作单元的 session 文件同步到独立 staging 目录
- [x] 能把原始 `Codex` JSONL 转成可被 `MemPalace convos` 稳定接收的 transcript Markdown snapshot
- [x] 能把同一路径 session 的新版本写成新的 staging snapshot，避免被 `MemPalace convos` 直接跳过
- [x] 能识别同一路径 session 文件增长后的新增内容
- [x] 能以目录级 staging 为输入执行 `mempalace mine --mode convos`
- [x] 能对混合目录 session 做正确隔离，不再让它们落成同一个 ingest 输入目录
- [x] 能在失败时报告具体是 session 解析失败、staging 失败，还是 `MemPalace` mine 失败
- [x] 能从目录 palace 读出 `document + metadata`
- [x] 能从目录 palace 生成确定性的候选 room package
- [x] 能把候选 room package 直接落盘并立即晋升为 Markdown
- [x] 能提供目录级 clean / rebuild / retry 操作
- [x] 能维护目录级 `projects.toml` 配置
- [x] 能执行单次 `projects-run` cycle，把 `codex-sync` 与 `mempalace mine` 按目录配置串起来
- [x] 能在 `projects-run` 中对 `resume` 后同一路径 session 增长维持正确同步
- [x] 能在 `projects-run` 中对目录级 `mine_interval_seconds` 做最小间隔控制
- [x] 能通过 `memark service-install` 安装用户级 intake 调度，而不是只靠手工执行 `projects-run`
- [x] 能通过 `memark service-status` / `memark service-uninstall` 检查和移除已安装的 intake 调度
- [x] 即使 workspace 里配置的是默认命令名，也能在当前 `PATH` 不完整时回退到 `~/.memark/venv/bin/mempalace` / `graphify`
- [x] 能在 `palace-package` / `palace-run` 中对同一逻辑 session 的旧 snapshot 做下游去重
- [x] `palace-package` / `palace-run` 已支持 `--group-by session`，可把会话型 palace 从粗 room 拆成更细的逻辑 session package
- [x] 文档明确说明当前 Graphify fallback 只保证 code graph 重建，不保证 mixed-corpus 完整编译
- [x] 文档明确说明当前 `graphify.detect()` 与 `graphify.extract()` 的边界差异，避免把“已发现文档”误写成“已完成文档入图”
- [x] 能把 `.memark` / `.mempalace` / `.codex` / `.claude` / `AGENTS.md` 从一个目录复制到新 worktree
- [x] `memark worktree-hook-install` 能把自动 attach hook 装到共享 git hooks 目录
- [x] worktree attach 复制 `.memark` 时只复制 `config.json` 与 `projects.toml`，不复制 `state` / `staging` / `palaces`
- [x] `memark query` 能在 `corpus/<project>/promoted|documents|imports` 上提供不依赖 `Graphify` 的本地搜索入口
- [x] `memark graphify-handoff` 能输出当前项目 corpus 的绝对路径、scope 规模和推荐 `/graphify <path> --update` 命令
- [x] `memark graphify-handoff --json` 能输出可直接喂给 AI 的 prompt 与 machine-readable payload

## K. 产品目标验收项

- [x] 文档已明确区分“前半段 ingest”和“后半段消费”
- [x] 文档已明确 `MemPalace`、`MemArk promoted corpus`、`Graphify` 各自承担的消费面
- [x] 当前项目实测证明：会话 ingest 后可通过 `MemPalace search` 取回真实内容
- [x] 当前 worktree 实测证明：新对话成功后可重新 ingest，并可通过 `MemPalace search` 取回 assistant 回复
- [x] 当前项目实测证明：`palace-package --group-by session` 能把 2 个粗 room 改写为 14 个更细的 promoted package
- [x] 已形成面向项目内 AI 的统一消费工作流说明
- [ ] 已验证 `Graphify` 消费晋升后的 Markdown 语料并对项目 AI 产生可观察改进
- [ ] 已验证相比“不使用 MemArk”，项目 AI 在延续性、找回历史决策、减少重复讨论方面有明确提升

## 当前结论

当前版本已经达到“可运行的最小桥接器 + 用户级安装入口”验收线。

它还不是“完全自动从 MemPalace 抽取增量的成品”，但已经是：

- 一个真实可安装的 Python CLI
- 一个可验证的用户级 runtime + AI skill bundle 安装器
- 一个稳定的 room package -> corpus 编排层
- 一个可测试、可扩展、已具备 code-only Graphify fallback 的实现基线

下一阶段的核心验收重点，不再是继续补主链命令，而是处理两类剩余问题：

- 还没有后台守护进程；当前是 `CLI-first` 的单次 cycle，由外部定时器负责重复触发
- 还没有稳定公开的 `MemPalace` 增量读取契约；当前增量策略仍以 `Codex session file` 变化为主
