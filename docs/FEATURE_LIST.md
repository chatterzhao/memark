# Feature List

本文件基于 2026-04-09 的实际使用结果，重新整理 `MemArk` 的功能列表。

依据文件：

- [`docs/RESEARCH_MEMPALACE_USAGE.md`](<repo-root>/docs/RESEARCH_MEMPALACE_USAGE.md)
- [`docs/RESEARCH_GRAPHIFY_USAGE.md`](<repo-root>/docs/RESEARCH_GRAPHIFY_USAGE.md)
- [`docs/CODEX_SESSION_INGEST_DESIGN.md`](<repo-root>/docs/CODEX_SESSION_INGEST_DESIGN.md)

## 产品定位

`MemArk` 是一个 `CLI-first` 的桥接与治理工具。

它的成功标准不是“包了一层自动化”，而是：

- 自动喂数据不能比单用 `MemPalace` 更差
- 自动加工不能比直接读原始 session / 项目文档更差
- 自动消费不能比直接用 `MemPalace` / `Graphify` 原生入口更差
- 如果任一自动化主路径降低了上游已有价值，这条路径就不该被当成正式能力宣传

它负责：

- 以用户级 AI skill bundle 的方式安装并配置 `MemArk`
- 通过 `MemArk` 再安装、验证并编排 `MemPalace`、`Graphify`
- 定义目录级输入边界
- 把 `Codex` 会话整理成可安全挖掘的目录级输入
- 编排 `MemPalace` 的目录级 ingest
- 把值得保留的目录过程知识晋升为 `Graphify-ready` 语料
- 触发兼容的 `Graphify` 编译入口
- 在上游 mixed-corpus 编译仍由 skill 主导时，生成准确的 Graphify handoff
- 维持唯一正式 CLI 命令面，避免同一能力出现多种拼写导致自动化漂移

它不负责：

- 自己做长期记忆数据库
- 自己做知识图谱引擎
- 假装上游已经提供稳定的自动增量 API
- 假装任何版本的 `Graphify` 都有同一条稳定 build CLI

当前命名策略：

- 每个能力只保留一个唯一正式命令名
- 如果未来需要更短命令，应在新增能力时直接把短名定为唯一正式名
- slash 不是默认入口；只有 direct CLI 不可用或任务明确要求 slash 语法时才走 slash adapter

## 一、当前必须实现

### F1. 上游安装 skill

说明：

- 根目录 [`SKILL.md`](<repo-root>/SKILL.md) 不再只是“当前项目临时安装说明”
- 它应是用户提供给 AI 工具的生产安装入口
- 它的目标是把一整组 `MemArk` skills 和运行脚本安装到用户 AI 工具的 skill 目录
- 安装后，AI 工具应能在用户任意项目对话中自动使用 `MemArk`
- `MemArk` 再负责检查、安装并调度 `MemPalace`、`Graphify`

当前状态：

- 已实现安装目标目录识别：
  - `~/.claude/skills/memark/`
  - `~/.agents/skills/memark/`
  - 以及其他后续支持的平台目录
- 已实现兼容 Python 运行时自动选择：
  - 当前会优先选择 `3.13/3.12/3.11/3.10`
  - 当前会明确拒绝不兼容的 `3.14+` runtime
- 已实现 skill bundle 复制：
  - `SKILL.md`
  - `project.md`
  - `doctor.md`
  - `bin/memark`
  - `bin/memark.cmd`
  - `manifest.json`
- 已实现用户级运行入口：
  - `memark install`
  - `memark doctor`
  - 安装后 launcher `~/.agents/skills/memark/bin/memark`
- 已实现开发期隔离验收入口：
  - [`skill-dev.md`](<repo-root>/skill-dev.md)

当前文档中应删除的旧假设：

- “生产 skill 默认只在当前项目创建 `.venv-skill-check/`”
- “生产 skill 默认停在当前项目内 CLI 已可用”

### F2. 目录级会话发现

说明：

- 扫描 `~/.codex/sessions/**/*.jsonl`
- 读取每个 session 文件首行 `session_meta`
- 从 `session_meta.payload.cwd` 判断目录归属
- 以目录路径为主模型，不要求目录必须处于 git 仓库中
- 支持把附加目录路径映射到同一个目录工作单元

为什么必须有：

- 实测证明 `~/.codex/history.jsonl` 不带 `cwd`
- 实测证明 `MemPalace convo mine` 不会自动把混合项目输入再拆开

### F3. 目录级 staging

说明：

- 每个目录工作单元需要独立的 staging 目录
- 只把属于该目录工作单元的 session 文件写入对应 staging
- 默认写入的是 transcript Markdown snapshot，而不是原始 JSONL 原样复制
- 当 session 内容变化时，写成新的不可变 snapshot 路径
- `MemPalace` 只对这个 staging 目录执行 `mine --mode convos`

当前状态：

- 已实现为 `memark codex-sync`
- 当前 staged snapshot 会保留：
  - `Source Path`
  - `Workspace Path`
  - `Session ID`
  - `Session Timestamp`
  - 用户 / assistant transcript

### F4. 增量同步与去重

说明：

- 记录已处理 session 文件
- 至少跟踪 `path`、`mtime`、`size`
- 需要准备扩展到 `content hash` 或 `offset`

为什么必须有：

- 实测确认 `resume` 后会继续往原 JSONL 追加内容
- 实测确认 `MemPalace 3.0.0` 对同一路径追加后的 `convos` 输入会直接跳过
- 当前真实刚需是“同一路径 session 增长后，staging 和后续 mine 继续正确更新”

当前状态：

- 已实现“同路径增量检测 + staging snapshot 写入”
- 已实现 `projects-run` 对“新增/更新 -> pending_mine -> 自动 mine”的单次 cycle
- 已实现 package 层对同一逻辑 session 的最新 snapshot 选择
- “跨路径同内容归并”目前仍是防御性增强项，不是已验证主需求

### F5. 目录边界治理

说明：

- 明确哪些目录和文件允许进入 `MemPalace`
- 明确哪些目录和文件允许进入 `Graphify`
- 明确 cross-tool ignore，防止产物回灌

当前至少应治理：

- `graphify-out/`
- `memark-work/`
- `.mempalace/`
- `.experiments/`
- `build/`
- `dist/`
- `.pytest_cache/`
- `*.egg-info/`
- `docs/raw/`
- `entities.json`
- `.graphify_detect.json`
- `.graphify_python`

### F6. MemPalace ingest 编排

说明：

- 以目录工作单元为单位执行 `mempalace mine <staging> --mode convos`
- 明确 palace 路径
- 明确清理、重建、重跑的运维入口

当前状态：

- 已实现 `memark mempalace-mine`
- 已实现 `memark palace-status`
- 已实现 `memark palace-clean`
- 已实现 `memark palace-rebuild`
- 已实现 `memark palace-retry`

### F7. 项目知识晋升

说明：

- 从 `MemPalace` 已 ingest 的目录会话中抽取有价值内容
- 生成 `Graphify-ready` Markdown
- 默认保留来源、会话、文件、时间等 provenance

前置状态：

- 已实现 `memark palace-export` 作为只读 adapter
- 已实现 `memark palace-package`
- 已实现 `palace-package --group-by session`
- 已实现按逻辑 session 只取最新 snapshot，避免同一会话旧版本继续流入下游
- 已实现优先从 staging snapshot 的首个有效会话开场语句提取 `room_title`，避免完全退化成时间戳标题
- 当前能按 `(wing, room)` 或 `logical session` 生成确定性候选 package
- 当前仍未实现“自动判定哪些内容值得晋升”的策略层
- 当前 `room_title` 仍然只是启发式标题，不是稳定的会话摘要

### F8. 语料分层落盘

说明：

- 落成统一的目录 corpus 目录
- 至少保留：
  - `promoted/`
  - `documents/`
  - `imports/`

### F9. Graphify 兼容编排

说明：

- 触发兼容的 `Graphify` 构建入口
- 区分：
  - 上游 CLI 直连 build
  - `MemArk` autonomous mixed-corpus build

当前状态：

- 已实现安装版 `graphify` CLI 不暴露直接 folder build 时的兼容回退
- 当顶层 `graphify <folder>` 不可用，或 `graphify` 缺失时，`MemArk` 会直接在 `corpus/<project>/graphify-out/` 构建本地 mixed-corpus graph
- 当前本地构建产物包括：
  - `graph.json`
  - `manifest.json`
  - `GRAPH_REPORT.md`
- 当前已通过 Graphify 源码与本仓库实测再次确认：
  - `detect()` 能发现 `promoted/*.md`
  - 但 `extract()` 公开入口只处理代码文件
  - `watch()` 对文档变化只会写 `graphify-out/needs_update`，要求上游 AI skill 再执行 `/graphify --update`
- 当前更准确的能力定义是：
  - `MemArk` 能稳定落出 `Graphify-ready corpus`
  - `MemArk` 能独立完成一个可检测、可消费的 mixed-corpus graph build
  - `MemArk` 能把 slash-only `Graphify` 请求映射到自己的 CLI 适配层
  - `MemArk` 能枚举当前支持的 slash adapter 与参数映射，供 AI 自动发现
  - `MemArk` 能在 catalog 中声明路由原则：CLI 优先、免交互优先、自动批准
  - `MemArk` 也能把统一上下文消费入口映射成 `/context`
  - `MemArk` 也能把阶段状态入口映射成 `/milestones`
  - `MemArk` 也能把本地 corpus 搜索入口映射成 `/query`
  - 上游 `Graphify` skill 互操作仍然可选保留，但不再是正常自动化闭环前置条件

### F10. 可观测结果

说明：

- 每次运行都应报告：
  - 扫描了多少 session
  - 命中了多少目录 session
  - 新增或更新了多少 staging 文件
  - 执行了哪条 `MemPalace` 命令
  - 晋升了哪些语料
  - 当前走的是哪条 `Graphify` 路径

当前状态：

- `codex-sync` 与 `mempalace-mine` 已能输出对应统计和命令
- 晋升与 `Graphify` 路径也已有 CLI 输出

### F10.2. Intake 调度安装入口

说明：

- `projects-run` 不应只停留在手工命令
- 需要有正式的系统调度器安装入口
- 同时仍然保持 `MemArk` 自身是单次 cycle，而不是自写常驻 daemon

当前状态：

- 已实现 `memark service-install`
- 已实现 `memark service-status`
- 已实现 `memark service-uninstall`
- 已实现 `memark automation-run` 作为默认自动闭环 cycle
- 当前 `service-install` 默认调度的是 `automation-run`，而不是只调度 `projects-run`
- 当前首个正式支持的调度后端是 macOS `launchd`
- 当前自动文档同步已排除研究归档、构建产物和缓存，避免把噪音重新喂进消费侧
- 当前仍未实现跨平台统一 scheduler backend

### F10.1. 本地项目语料消费入口

说明：

- 当 `Graphify` 尚未稳定把 promoted markdown 编进图时，`MemArk` 仍需要一个独立消费入口
- 这个入口至少应支持对 `corpus/<project>/promoted`、`documents`、`imports` 做固定字符串搜索
- 输出应包含标题、路径、命中行、片段

当前状态：

- 已实现 `memark query`
- 已支持：
  - `--scope promoted|documents|imports|all`
  - `--limit`
  - `--json`
- 该命令不依赖 `Graphify`，是当前阶段项目 AI 直接读取晋升知识的最小可用入口

### F10.3. 自动消费产物

说明：

- 安装完成后，系统不应只把知识写到 `promoted/*.md`
- 还应自动产出 AI / 管理者可直接读取的项目级消费文件

当前状态：

- 已实现 `memark automation-run`
- 每轮自动 cycle 现在会自动生成：
  - `corpus/<project>/imports/automation/latest-summary.md`
  - `corpus/<project>/imports/automation/decisions-digest.md`
  - `corpus/<project>/imports/automation/risks-digest.md`
  - `corpus/<project>/imports/automation/ai-context.md`
  - `corpus/<project>/imports/automation/graphify-status.md`
- 这些文件当前主要基于 promoted/documents 语料做启发式整理
- 因此它们已经构成自动消费基线，但还不能等同于“高质量项目治理智能体”

### F10.4. 自动消费统一入口

说明：

- 自动消费不能停在“文件已经写出来了”
- AI 和人类管理者需要一个统一入口，把当前项目最该读的自动产物一次性拿到

当前状态：

- 已实现 `memark context`
- 默认会先刷新一轮 `automation-run`
- 然后统一输出：
  - `ai-context`
  - `latest-summary`
  - `decisions-digest`
  - `risks-digest`
  - `graphify-status`
- 运行时 skill bundle 现在也已把 `memark context` 提升为默认项目消费入口
- 但当前还不能声称它已经稳定优于直接使用 `MemPalace wake-up/search` 与 `Graphify report/query`

### F10.2. Graphify skill handoff

说明：

- 当任务明确要求上游 `Graphify` skill / AGENTS/hooks 互操作时，`MemArk` 仍需要给 AI 一个准确 handoff
- 这个 handoff 至少应明确：
  - 当前项目 `corpus/<project>` 的绝对路径
  - `promoted/documents/imports` 的文件规模
  - 推荐命令 `/graphify <corpus> --update`
  - 这是可选互操作路径，而不是默认构建路径

当前状态：

- 已实现 `memark graphify-handoff`
- 已输出：
  - corpus 目标路径
  - 推荐命令
  - scope 文件数与词数
  - 可直接复制给 AI 的 prompt

### F10.3. Graphify ingestion proof

说明：

- mixed-corpus graph 是否真的覆盖过当前 corpus，必须是系统可见状态
- 否则 `M1` 是否达成仍然只能靠人类记忆或文档补记

当前状态：

- 已实现 `memark graphify-proof`
- 可持久记录：
  - `recorded_at`
  - `recommended_command`
  - 实际执行命令
  - 证据文件路径
  - 备注
- 也可自动识别：
  - `corpus/<project>/graphify-out/graph.json`
  - 其中存在来自 `promoted/`、`documents/` 或 `imports/` 的节点
- `memark milestones --workspace ...` 已会把这条 proof 作为 mixed-corpus 闭环判断依据

### F10.4. Graphify corpus onboarding

说明：

- mixed-corpus `Graphify` 真正要跑的目录不是 workspace root，而是 `corpus/<project>`
- 因此仍需要一个明确入口，把上游 `Graphify` 的项目级 AGENTS / hooks 安装到这个 corpus 目录
- 但这条路径现在只服务于上游 interop，不再是本地自动构图的前置条件

当前状态：

- 已实现 `memark graphify-onboard`
- 当前会在 `corpus/<project>` 内执行上游 `graphify <platform> install`
- 已实现 corpus 级 Graphify onboarding state 暴露：
  - `graph_missing`
  - `onboarded_graph_missing`
  - `ingested`
- `memark status --json` 与 `memark milestones --workspace ...` 现在都会显示这条状态
- 当前仓库已真实验证：
  - `corpus/memark/AGENTS.md`
  - `corpus/memark/.codex/hooks.json`

### F10.5. Graphify blocker surfaced in default context

说明：

- 日常消费入口不能只说 `graphify_status=not_requested`，还要能回答当前到底是 graph 还没生成，还是只差上游 interop
- 否则 AI 在 `context` 面前仍要额外翻 `status` 或 `milestones`

当前状态：

- 已实现自动消费产物携带 corpus 级 Graphify 状态
- `ai-context.md` 现包含：
  - `graphify_corpus_status`
  - `graphify_onboarding_status`
  - `graphify_proof_diagnostics`
- `graphify-status.md` 现包含：
  - `corpus_status`
  - `onboarding_status`
  - `graph_path`
  - `recommended_command`

## 二、下一阶段应实现

### F11. 目录配置文件

说明：

- 支持一个 `MemArk` 目录配置文件
- 每个目录对象至少包含：
  - `name`
  - `path`
  - `sessions_root`
  - `extra_paths`
  - `staging_dir`
  - `palace_dir`
  - `mine_interval_seconds`
  - `graphify_corpus_dir`

建议格式：

- 优先 `TOML`

当前状态：

- 已实现 `.memark/projects.toml`
- 已实现 `memark project-set`
- 已实现 `memark projects-list`
- 已实现 `memark init --auto`，一键完成 workspace 初始化 + 项目注册 + 调度安装 + 首轮 cycle

还需要扩展：

- 区分用户级配置与目录级配置
- 用户级配置至少应记录：
  - `memark` 安装根
  - 默认 palace / workspace 根
  - AI 平台类型
  - 已安装的 skill bundle 版本
- 目录级配置继续记录：
  - 目录路径
  - sessions 根
  - mine 间隔
  - corpus 目录

### F12. 定时扫描

说明：

- 轮询 `Codex sessions`
- 按目录更新 staging
- 必要时触发 `mempalace mine`

限制：

- 这是轮询，不是假装文件系统事件流
- 不应默认同时自动触发晋升和编图

当前状态：

- 已实现 `memark projects-run` 作为单次 cycle
- 推荐由 `cron`、`launchd`、Windows Task Scheduler 或 CI 重复调用
- 尚未实现常驻 daemon

### F13. 用户级自动工作入口

说明：

- 安装完成后，`MemArk` 不能只停留在“用户以后手工输入命令”
- 用户在 AI 工具中使用任意项目时，AI 应能无感调用 `MemArk`
- 这要求 skill bundle 中存在稳定入口，而不只是安装说明

至少需要：

- 一个主 Skill，告诉 AI 何时调用 `MemArk`
- 一个或多个辅助 Skill，负责：
  - 安装后验证
  - 项目接入
  - 运行时工作流
- 一个稳定脚本入口，供 Skill 调用

### F14. 安装后自动配置

说明：

- 安装过程应能把 `MemArk` 所需的 skill bundle 放入用户 AI 工具目录
- 必要时写入 AI 工具要求的说明文件、入口文件或 hook 配置
- 安装完成后应让 `MemArk` 处于“AI 可直接使用”的状态

注意：

- 这里的“自动”是指安装阶段配置好，不代表后台守护进程已经实现
- 当前仍不能伪装成“已经有完整后台自动同步系统”

### F15. MemPalace 读取适配器

说明：

- 从 `chroma.sqlite3` 读取 metadata 与 `chroma:document`
- 作为 best-effort adapter，而不是官方稳定 API

当前状态：

- 已实现 `palace-export`
- 已实现 `palace-package`
- 已实现 `palace-run`
- 当前主要面向 `convos` palace 读取

### F16. 更细的治理规则

说明：

- 按以下字段做筛选：
  - `wing`
  - `room`
  - `source_file`
  - `filed_at`
  - `ingest_mode`
  - `extract_mode`

### F17. 人工审核流

说明：

- 在“自动晋升”之外保留“候选 -> 审核 -> 发布”路径
- 对高价值决策、ADR、复盘允许人工确认后再喂给 `Graphify`

## 三、当前不应声称已经实现

- `MemPalace` 提供稳定的 `since timestamp` 接口
- `MemPalace` 会自动按项目拆分混合 `Codex` 会话
- `Graphify` 已稳定支持消费所有晋升后的 Markdown 语料
- `MemArk` 已经具备后台常驻守护服务
- `MemArk` 已经具备跨 AI 工具通用的插件形态

### F18. worktree 配置复制

说明：

- `git` 当前只用于发现 `worktree` 创建事件
- 真正的复制动作由 `memark worktree-attach` 执行
- 复制对象是目录级配置，而不是把 `git` 逻辑项目引入主模型
- 默认复制：
  - `.memark/`
  - `.mempalace/`
  - `.codex/`
  - `.claude/`
  - `AGENTS.md`

当前状态：

- 已实现为 `memark worktree-attach`
- 已实现为 `memark worktree-hook-install`
- 当前 `.memark` 只复制：
  - `config.json`
  - `projects.toml`
- 当前不会复制：
  - `.memark/state/`
  - `.memark/staging/`
  - `.memark/palaces/`
- 后续可由 `git worktree add` 包装脚本或 hook 调用
