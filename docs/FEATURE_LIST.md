# Feature List

本文件基于 2026-04-09 的实际使用结果，重新整理 `MemArk` 的功能列表。

依据文件：

- [`docs/RESEARCH_MEMPALACE_USAGE.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/RESEARCH_MEMPALACE_USAGE.md)
- [`docs/RESEARCH_GRAPHIFY_USAGE.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/RESEARCH_GRAPHIFY_USAGE.md)
- [`docs/CODEX_SESSION_INGEST_DESIGN.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/CODEX_SESSION_INGEST_DESIGN.md)

## 产品定位

`MemArk` 是一个 `CLI-first` 的桥接与治理工具。

它负责：

- 以用户级 AI skill bundle 的方式安装并配置 `MemArk`
- 通过 `MemArk` 再安装、验证并编排 `MemPalace`、`Graphify`
- 定义项目级输入边界
- 把 `Codex` 会话整理成可安全挖掘的项目级输入
- 编排 `MemPalace` 的项目级 ingest
- 把值得保留的项目过程知识晋升为 `Graphify-ready` 语料
- 触发兼容的 `Graphify` 编译入口

它不负责：

- 自己做长期记忆数据库
- 自己做知识图谱引擎
- 假装上游已经提供稳定的自动增量 API
- 假装任何版本的 `Graphify` 都有同一条稳定 build CLI

## 一、当前必须实现

### F1. 上游安装 skill

说明：

- 根目录 [`SKILL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/SKILL.md) 不再只是“当前项目临时安装说明”
- 它应是用户提供给 AI 工具的生产安装入口
- 它的目标是把一整组 `MemArk` skills 和运行脚本安装到用户 AI 工具的 skill 目录
- 安装后，AI 工具应能在用户任意项目对话中自动使用 `MemArk`
- `MemArk` 再负责检查、安装并调度 `MemPalace`、`Graphify`

当前状态：

- 已实现安装目标目录识别：
  - `~/.claude/skills/memark/`
  - `~/.agents/skills/memark/`
  - 以及其他后续支持的平台目录
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
  - [`skill-dev.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/skill-dev.md)

当前文档中应删除的旧假设：

- “生产 skill 默认只在当前项目创建 `.venv-skill-check/`”
- “生产 skill 默认停在当前项目内 CLI 已可用”

### F2. 项目级会话发现

说明：

- 扫描 `~/.codex/sessions/**/*.jsonl`
- 读取每个 session 文件首行 `session_meta`
- 从 `session_meta.payload.cwd` 判断项目归属
- 支持把多个 worktree、子目录映射回同一个项目根

为什么必须有：

- 实测证明 `~/.codex/history.jsonl` 不带 `cwd`
- 实测证明 `MemPalace convo mine` 不会自动把混合项目输入再拆开

### F3. 项目级 staging

说明：

- 每个项目需要独立的 staging 目录
- 只把属于该项目的 session 文件写入该项目的 staging
- 当 session 内容变化时，写成新的不可变 snapshot 路径
- `MemPalace` 只对这个 staging 目录执行 `mine --mode convos`

当前状态：

- 已实现为 `memark codex-sync`

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

### F5. 项目边界治理

说明：

- 明确哪些目录和文件允许进入 `MemPalace`
- 明确哪些目录和文件允许进入 `Graphify`
- 明确 cross-tool ignore，防止产物回灌

当前至少应治理：

- `graphify-out/`
- `memark-work/`
- `.mempalace/`
- `.experiments/`
- `docs/raw/`
- `entities.json`
- `.graphify_detect.json`
- `.graphify_python`

### F6. MemPalace ingest 编排

说明：

- 以项目为单位执行 `mempalace mine <staging> --mode convos`
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

- 从 `MemPalace` 已 ingest 的项目会话中抽取有价值内容
- 生成 `Graphify-ready` Markdown
- 默认保留来源、会话、文件、时间等 provenance

前置状态：

- 已实现 `memark palace-export` 作为只读 adapter
- 已实现 `memark palace-package`
- 当前能按 `(wing, room)` 生成确定性候选 package
- 当前仍未实现“自动判定哪些内容值得晋升”的策略层

### F8. 语料分层落盘

说明：

- 落成统一的项目 corpus 目录
- 至少保留：
  - `promoted/`
  - `documents/`
  - `imports/`

### F9. Graphify 兼容编排

说明：

- 触发兼容的 `Graphify` 构建入口
- 区分：
  - code-only fallback
  - 真正 mixed-corpus build

### F10. 可观测结果

说明：

- 每次运行都应报告：
  - 扫描了多少 session
  - 命中了多少项目 session
  - 新增或更新了多少 staging 文件
  - 执行了哪条 `MemPalace` 命令
  - 晋升了哪些语料
  - 当前走的是哪条 `Graphify` 路径

当前状态：

- `codex-sync` 与 `mempalace-mine` 已能输出对应统计和命令
- 晋升与 `Graphify` 路径也已有 CLI 输出

## 二、下一阶段应实现

### F11. 项目配置文件

说明：

- 支持一个 `MemArk` 项目配置文件
- 每个项目对象至少包含：
  - `name`
  - `root`
  - `codex_session_glob`
  - `cwd_prefixes`
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

还需要扩展：

- 区分用户级配置与项目级配置
- 用户级配置至少应记录：
  - `memark` 安装根
  - 默认 palace / workspace 根
  - AI 平台类型
  - 已安装的 skill bundle 版本
- 项目级配置继续记录：
  - 项目根
  - sessions 根
  - mine 间隔
  - corpus 目录

### F12. 定时扫描

说明：

- 轮询 `Codex sessions`
- 按项目更新 staging
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

### F13. MemPalace 读取适配器

说明：

- 从 `chroma.sqlite3` 读取 metadata 与 `chroma:document`
- 作为 best-effort adapter，而不是官方稳定 API

当前状态：

- 已实现 `palace-export`
- 已实现 `palace-package`
- 已实现 `palace-run`
- 当前主要面向 `convos` palace 读取

### F14. 更细的治理规则

说明：

- 按以下字段做筛选：
  - `wing`
  - `room`
  - `source_file`
  - `filed_at`
  - `ingest_mode`
  - `extract_mode`

### F15. 人工审核流

说明：

- 在“自动晋升”之外保留“候选 -> 审核 -> 发布”路径
- 对高价值决策、ADR、复盘允许人工确认后再喂给 `Graphify`

## 三、当前不应声称已经实现

- `MemPalace` 提供稳定的 `since timestamp` 接口
- `MemPalace` 会自动按项目拆分混合 `Codex` 会话
- `Graphify` 已稳定支持消费所有晋升后的 Markdown 语料
- `MemArk` 已经具备后台常驻守护服务
- `MemArk` 已经具备跨 AI 工具通用的插件形态
