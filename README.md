# MemArk

> **自动串联 MemPalace 记忆和 Graphify 图谱——任何想用 MemPalace / mempal / Graphify 的人，只需 `cd <your-project-path>` 再执行 `memark init`，它将自动喂数据、自己加工、自己被您在这个项目工作的 AI 消费。**

上游项目：

- `MemPalace` GitHub: <https://github.com/milla-jovovich/mempalace>
- `Graphify` GitHub: <https://github.com/safishamsi/graphify>

## 快速开始

```bash
# 安装 MemArk
python3 -m venv .memark-bootstrap
.memark-bootstrap/bin/python -m pip install .
.memark-bootstrap/bin/python -m memark install --platform codex --source-spec "$(pwd)"

# 在任何项目目录接入
cd your-project
memark init
```

`memark init` 一条命令完成：创建 workspace → 注册项目 → 安装后台调度 → 运行首轮自动化 cycle。

## 平台支持

当前仅支持 **macOS**。后台调度依赖 `launchd`，后续版本将支持 Linux（systemd/cron）和 Windows（Task Scheduler）。

## 当前判断

基于 2026-04-08 的实际使用结果，而不是只看 README 或源码，当前可以把三者关系收敛为：

- `MemPalace`：原始记忆层。真实强项是逐字保存、搜索、wake-up、MCP 协议化访问，以及项目/对话两种 ingest 策略。
- `Graphify`：知识编译层。真实强项是代码图、报告、查询、导出和 AI 工具集成，但安装版 CLI 暴露面比官方技能描述要窄。
- `MemArk`：桥接与治理层。把原始记忆里值得晋升为项目知识的部分，整理成 `Graphify` 更适合消费的语料边界。

`MemArk` 不是新的记忆系统，也不是新的图谱引擎。

`MemArk` 的成功标准也不是“把两者串起来”。

必须满足：

- 自动喂数据不能比单用 `MemPalace` 更差
- 自动加工不能比直接读原始 session / 项目文档更差
- 自动消费不能比直接用 `MemPalace` / `Graphify` 原生入口更差

如果 `MemArk` 让上游已有价值打折扣，它就不是增强层，而是失败的中间层。

基于真实运行，还需要补一个更保守的判断：

- 只需要记忆找回时，`MemPalace` 单独就已经有价值
- 只需要代码结构图时，`Graphify` 单独也已经有价值
- `MemArk` 的价值只在“原始项目记忆 -> 可编译项目知识”这一段

因此下一阶段真正应该收敛成默认体验的是五层自动化：

1. 自动安装
2. 自动配置
3. 自动喂数据
4. 自动加工
5. 自动消费

这不是保守表述，而是来自真实运行结果：

- 在当前 `memark` 仓库上，`MemPalace` 如果不额外治理，会把 `.graphify_detect.json`、`entities.json`、`docs/raw/` 这类噪音也一起挖进去
- 给仓库补上更严格的忽略规则后，当前仓库的 `MemPalace` dogfood 结果收敛到 `28 files / 200 drawers`
- 同一轮 dogfood 中，`Graphify detect` 从 `35 files / ~18.7k words` 收敛到 `25 files / ~11.6k words`
- `Graphify` 在当前仓库代码图上实际给出了 `101 nodes / 167 edges / 8 communities`
- `Graphify benchmark` 在当前仓库图上给出了约 `10.0x` 的每查询 token reduction

详细实测报告：

- [`docs/RESEARCH_MEMPALACE_USAGE.md`](docs/RESEARCH_MEMPALACE_USAGE.md)
- [`docs/RESEARCH_GRAPHIFY_USAGE.md`](docs/RESEARCH_GRAPHIFY_USAGE.md)
- [`docs/MEMARK_REASSESSMENT.md`](docs/MEMARK_REASSESSMENT.md)
- [`docs/CODEX_SESSION_INGEST_DESIGN.md`](docs/CODEX_SESSION_INGEST_DESIGN.md)
- [`docs/AI_CONSUMPTION_MODEL.md`](docs/AI_CONSUMPTION_MODEL.md)

## 两个上游到底怎么用，才能发挥它们的强项

### `MemPalace`

`MemPalace` 的强项不是“人工天天搜库”，而是：

- 本地保存原始对话和资料
- 让 AI 在后续对话里找回上下文
- 在需要时回到原始逐字内容
- 给 AI 一个短得多的 wake-up context，而不是每次重喂历史
- 通过 hooks / `MEMPAL_DIR` 把长期采集自动化

更合适的使用方式是：

1. 安装并执行一次 `mempalace init`、`mempalace mine`
2. 把它接给支持 MCP 的 AI 客户端，或者直接使用它的 CLI / wake-up
3. 让 AI 在问答时自动调用搜索、wake-up 和记忆工具，而不是把它当成人工知识库 UI
4. 对长期项目或长期聊天，优先用 hooks / 自动 mine 保持记忆持续更新

在组合使用 `MemPalace + Graphify` 时，当前更推荐的默认分工是：

- `Graphify` 直接扫描项目目录，负责代码和正式文档的结构理解
- `MemPalace` 优先 ingest `Claude Code` / `Codex` / `ChatGPT` 这类会话导出
- `MemArk` 再从这些会话记忆里挑出值得晋升到项目语料的部分

原因不是 `MemPalace` 不能扫项目。恰恰相反，官方明确支持：

- `mempalace mine <project_dir>` 处理 `code / docs / notes`
- `mempalace mine <chat_dir> --mode convos` 处理 `txt / md / json / jsonl` 会话导出

但在组合场景里，如果让两个上游都默认全量重扫整个项目目录，会产生更多重复与治理成本。

需要特别注意的一点是：

- 实际 palace 顶层是 `chroma.sqlite3` 和 ANN 段文件，不是现成 Markdown 语料目录
- 最适合桥接层消费的表面，是 Chroma 里的 drawer metadata 加 `chroma:document`
- 对 `Codex` 来说，默认主入口应是 `~/.codex/sessions/**/*.jsonl`，因为 session 文件首行 `session_meta` 带 `cwd`
- 这次按 `cwd=<repo-root>` 筛出 `11` 个 session 文件后，实际 mine 出 `216 drawers`
- `~/.codex/history.jsonl` 只是全局扁平索引，不应被当成目录级主入口
- 虽然 metadata 里存在 `filed_at`
- 但这次没有验证到一个稳定公开的“按时间戳取增量” CLI 或 MCP 接口

这意味着 `MemArk` 不能假设上游已经提供现成的 `since` 拉取能力。

### `Graphify`

`Graphify` 的强项也不只是“把内容排成 wiki”。

它更像一个“编译 + 查询 + 平台接入”的知识图谱层，适合：

- 对一个持续积累的 corpus 目录运行
- 先形成图谱和报告，再让人或 AI 沿结构下钻原文
- 产出 `graph.json` 后继续做 query / MCP / wiki / Obsidian 导航
- 对代码变动做 watch / hook，对文档和研究材料做增量更新

更合适的使用方式是：

1. 给它一个稳定的项目语料目录，而不是每次手工粘贴聊天
2. 先让 AI 读 `GRAPH_REPORT.md` 做全局定向，再按需 query `graph.json`
3. 把代码、文档、图像、研究材料和晋升后的项目记忆放在同一个 corpus 边界里
4. 把 `graph.json` 继续作为 AI 可读的查询面，而不是只看静态 HTML

这次实测还确认了一个重要事实：

- 裸安装 `graphify` CLI 主要暴露的是 query、hook、平台安装等入口
- 代码图重建是可运行的
- 但安装版 CLI 不是一个稳定的 direct folder-build 入口
- 当前进一步核实到：
  - `graphify.detect()` 能发现 `promoted/*.md`
  - 但公开 Python 提取入口 `graphify.extract()` 只处理代码
  - `graphify.watch()` 对文档变化只会写 `needs_update`，要求上游 AI skill 再执行 `/graphify --update`

## MemArk 该做什么

`MemArk` 的合理职责是：

1. 从 `MemPalace` 的 Chroma drawer text + metadata 中识别哪些内容值得晋升为项目知识
2. 默认优先从项目相关会话记忆里筛选内容，并以 `project wing` 为边界按 `room` 组织
3. 保留原文证据与来源，而不是伪造新的记忆层
4. 落成 `Graphify-ready` Markdown 语料
5. 在安装版 `graphify` CLI 不支持 direct folder build 时，自己完成本地 mixed-corpus graph build
6. 在 `Graphify` 统一入图尚未打通前，先提供本地项目 corpus 的直接消费入口

当前更稳妥的设计假设不是整个宫殿，也不是裸数据库，而是：

`project wing -> room -> selected drawers -> promoted markdown (+ provenance)`

这是桥接层的治理选择，不是上游官方强制接口。原因很直接：

- 直接喂全量 raw memory，噪音太大
- 只喂 taxonomy，又太薄
- 只读 ANN 段文件，没有产品意义
- drawer metadata + selected text 才是当前最可操作的切口

另外还有一个已经被实测证明的前置条件：

- 先隔离派生产物，再谈桥接

对当前仓库来说，至少要排除：

- `.experiments/`
- `graphify-out/`
- `.mempalace/`
- `memark-work/`
- `.graphify_detect.json`
- `.graphify_python`
- `entities.json`
- `docs/raw/`

## 当前仓库提供什么

这个仓库现在已经提供一个可运行的、CLI-first 的 `MemArk` 最小实现。

已经提供：

- 经过收敛的项目定义
- `MemPalace -> MemArk -> Graphify` 的治理和接口说明
- 一个用户级生产安装入口 [`SKILL.md`](SKILL.md)
- 一份开发期安装测试入口 [`skill-dev.md`](skill-dev.md)
- 一个真实可执行的用户级安装命令：`memark install`
- 一个真实可执行的健康检查命令：`memark doctor`
- 一套会被安装到用户 AI 工具目录的 `MemArk` skill bundle
- 基于真实命令执行结果的安装验证记录
- 一个真实可运行的 Python CLI：`memark`
- 一个针对安装版 `graphify` CLI 差异的兼容策略：当顶层 `graphify <folder>` 不可用或 `graphify` 缺失时，由 `MemArk` 自己构建 mixed-corpus 图
- 一个不依赖 `Graphify` 入图的项目语料消费入口：`memark query`
- 一个把 `MemArk` 语料边界明确交给上游 `Graphify` skill 的可选桥接入口：`memark graphify-handoff`
- 一个把真实 mixed-corpus `Graphify` ingestion evidence 记回 workspace state 的入口：`memark graphify-proof`
- 一个把 Graphify 项目级接入直接安装到 `corpus/<project>` 的入口：`memark graphify-onboard`
- 一个把 slash-only 命令语义稳定适配到 `MemArk` CLI 的入口：`memark slash`
- 一个把 corpus graph 状态显式呈现为 `graph_missing` / `onboarded_graph_missing` / `ingested` 的状态面：`memark status`、`memark milestones`

当前 CLI 已支持：

- `memark init`
- `memark validate`
- `memark query`
- `memark graphify-handoff`
- `memark graphify-proof`
- `memark graphify-onboard`
- `memark slash`
- `memark promote`
- `memark project-set`
- `memark build`
- `memark slash --workspace <workspace> /graphify <workspace-or-corpus> --update`
- `memark slash --workspace <workspace> /context <workspace> --no-refresh --json`
- `memark slash --workspace <workspace> /milestones <workspace> --json`
- `memark slash --workspace <workspace> /automation-status <workspace> --json`
- `memark slash --workspace <workspace> /status <workspace> --json`
- `memark slash --workspace <workspace> /query <terms...> --json`
- `memark slash --workspace <workspace> /graphify-proof <workspace> --json`
- `memark slash --catalog --json`
- `memark run`
- `memark codex-sync`
- `memark project-set`
- `memark projects-list`
- `memark projects-run`
- `memark service-install`
- `memark service-status`
- `memark service-uninstall`
- `memark automation-run`
- `memark automation-status`
- `memark context`
- `memark mempalace-mine`
- `memark palace-status`
- `memark palace-clean`
- `memark palace-rebuild`
- `memark palace-retry`
- `memark palace-export`
- `memark palace-package`
- `memark palace-run`
- `memark status`

新增一条已经过当前仓库 dogfood 验证的实践：

- 对 `Codex` / `Claude Code` 这类会话型 palace，`palace-package` / `palace-run` 当前更推荐加 `--group-by session`
- 原因是 `MemPalace` 在当前仓库里真实只产出了 `sessions/technical` 与 `sessions/architecture` 两个粗 room
- 不加分组治理时，当前仓库只会得到 2 个很大的 promoted room；加上 `--group-by session` 后，当前仓库实测会得到 14 个更细的 promoted Markdown
- 这一步已经能真实改善“记忆晋升”的可读性与可挑选性，但还不等于 Graphify 已把这些 Markdown 吃进完整图谱

仍然没有提供：

- 直接从 `MemPalace` 数据库或 MCP 自动抽取增量的实现
- 后台监控或同步服务
- “安装后自动发现项目并自动执行项目接入”的完整闭环

另一个重要事实是：

- 早期 CLI 探测时，在 `.venv-skill-check` 中验证到的 `graphifyy 0.3.12` 顶层 `graphify --help` 暴露的是 `install`、`query`、`hook`、`claude/codex install` 等入口
- 它不是一个稳定公开的“任何版本都支持 `graphify <folder>`”接口
- 因此 `MemArk build` 当前应被理解为“优先调用兼容的 Graphify 构建入口；若不可用，则由 MemArk 自己产出 mixed-corpus graph”
- 当前实现里，当顶层 CLI 报 `unknown command` 或 `graphify` 缺失时，会直接在 `corpus/<project>/graphify-out/` 写出本地 mixed-corpus `graph.json`、`manifest.json`、`GRAPH_REPORT.md`
- 这条本地构建路径不依赖 slash-command 客户端，因此更符合 `MemArk` 的自动化职责
- `graphify-handoff` 与 `graphify-onboard` 仍保留，但现在是互操作入口，不再是正常自动化闭环的前置条件
- `memark slash` 提供 slash-compatible adapter surface，把 slash 语义映射到 `MemArk` 的稳定 CLI，而不是假装 shell 原生支持 `/...`
- `memark slash --catalog` 可直接枚举当前已支持的 slash adapter、参数和 `MemArk` 映射，方便 AI 自动发现能力
- `memark slash --catalog --json` 现在还会明确给出路由策略：优先直接调用 `MemArk` CLI；slash 只用于上游是 slash-only，或调用方明确要求 slash 语法
- `MemArk` 自己设计的入口同时支持交互式和免交互式，但当前默认面定义为：`non_interactive_first`、`approval=auto`
- 当前 CLI 不提供并存别名；每项能力只保留一个唯一正式命令名，避免 AI 调用面出现双写法漂移
- 当前除 `/graphify` 外，也已支持把 `/context` 映射到 `memark context`
- 现在也已支持把 `/milestones` 映射到 `memark milestones`
- 现在也已支持把 `/automation-status` 映射到 `memark automation-status`
- 现在也已支持把 `/status` 映射到 `memark status`，用于 slash-only 语义下的状态观测
- 现在也已支持把 `/query` 映射到 `memark query`，用于 slash-only 语义下的本地 corpus 搜索
- 现在也已支持把 `/graphify-proof` 映射到 `memark graphify-proof`

还需要把“安装位置”和“项目产物位置”区分开：

- `graphify codex install` 安装的 skill 在用户目录 `~/.agents/skills/graphify/`
- `graphify claude install` 安装的 skill 在用户目录 `~/.claude/skills/graphify/`
- 这些是全局安装，不在当前 `memark` 仓库里
- 但 `graphify` 上游源码同时表明，Codex 安装还会在当前项目目录写入 `AGENTS.md` 和 `.codex/hooks.json`
- 而真正的图谱产物，例如 `graphify-out/graph.json`、`graphify-out/GRAPH_REPORT.md`，则落在你运行 `graphify` 的那个项目目录里

所以之前如果看到当前仓库里出现 `graphify-out/`，那表示“`memark` 被当成 Graphify 的当前语料目录”，不是“Graphify skill 被安装进了 `memark` 仓库本身”。

## 当前安装闭环

当前已经实测通过的生产安装路径是：

1. 用当前仓库做 bootstrap 安装源
2. 执行 `memark install --platform <platform> --source-spec <repo-root>`
3. 让 `MemArk` 自己创建用户级 runtime：`~/.memark/venv`
4. 让 `MemArk` 把运行时 skill bundle 写入：
   - `~/.agents/skills/memark/`
   - `~/.claude/skills/memark/`
5. 用安装后的 launcher 执行 `memark doctor`

在 2026-04-09 的 fake-`HOME` 实测里，当前闭环确认到了：

- `mempalace 3.1.0`
- `graphifyy 0.3.27`
- 安装后的 `bin/memark` 可直接调用 `doctor`
- skill bundle 已实际落到 Codex skill 目录
- runtime 会自动选择兼容 Python；当前实测使用的是 `Python 3.13.6`
- 当前 workspace 即使 `PATH` 没手工加上 `mempalace` / `graphify`，也会优先回退到 `~/.memark/venv/bin/*`

## 安装和项目接入不是一回事

当前最容易让人误解的点是：`memark install` 不是 `memark init`。

两者职责不同：

- `memark install`：安装用户级 runtime 和 skill bundle
- `memark init`：初始化一个具体 workspace
- `memark project-set`：把一个具体项目目录登记到该 workspace

因此首次安装时：

- 可以在任何目录执行 `memark install`
- 不要求当前目录已经是项目目录
- 不要求当前目录已经存在 `.memark/`

更准确的理解是：

- `install` 面向“这台机器”
- `init` 面向“一个 workspace 目录”
- `project-set` 面向“workspace 里要跟踪的项目”

### 新项目要不要再执行 `memark init`

不一定。关键看你是否已经有一个现成 workspace。

如果你已经有一个长期使用的 workspace，比如 `~/memark-work`：

- 不需要为每个新项目重复 `memark init`
- 直接执行新的 `memark project-set --workspace ~/memark-work ...`

如果你希望某个仓库自己带一份独立状态：

- 就在该仓库根目录执行 `memark init`，一键完成所有设置
- 如果只想创建 workspace，用 `memark init --no-auto`，再逐步执行后续步骤

所以更准确的结论是：

- 一台机器通常只需要做一次 `memark install`
- 一个新的项目用 `memark init` 一键接入
- 如果需要逐步控制，用 `memark init --no-auto`，再分别执行 `memark service-install`、`memark automation-run`

### 常见接法

单仓库就地接入（推荐）：

```bash
~/.memark/venv/bin/memark init
```

逐步控制：

```bash
~/.memark/venv/bin/memark init --no-auto --project myproject
~/.memark/venv/bin/memark project-set \
  --workspace . \
  --project myproject \
  --path "$(pwd)" \
  --sessions-root ~/.codex/sessions
~/.memark/venv/bin/memark service-install --workspace .
~/.memark/venv/bin/memark automation-run --workspace . --no-build
```

共享 workspace 管多个项目：

```bash
~/.memark/venv/bin/memark init ~/memark-work
# 后续新增项目只需：
~/.memark/venv/bin/memark project-set \
  --workspace ~/memark-work \
  --project myproject \
  --path /abs/path/to/project \
  --sessions-root ~/.codex/sessions
```

## 当前 CLI 怎么用

先安装当前仓库里的 CLI：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

如果你要验证用户级正式安装链路，`memark install` 可以在任何目录执行：

```bash
python3 -m memark install --platform codex --source-spec "$(pwd)"
~/.memark/venv/bin/memark doctor --platform codex
```

注意：

- runtime Python 只支持 `3.10` 到 `3.13`
- 不要显式把 `--python-command` 指到不兼容的 `python3`
- 默认让 `memark install` 自动选择兼容解释器即可
- 如果 `doctor` 仅警告缺少 `mempal`，表示默认 `mempalace` 安装可用，但 `mem_tool=mempal` 还未就绪
- `mempal` 首次 ingest 可能需要引导默认 embedder 下载模型；若网络或 TLS 不通，`memark mem-tool-mine` 现在会给出明确提示，要求先处理 `~/.mempal/config.toml` 或在可联网环境预热模型

如果你接下来要让某个目录变成 MemArk workspace，再初始化一个工作区：

```bash
python3 -m memark init ./memark-work --project myproject
```

这会同时创建：

- `./memark-work/.memark/config.json`
- `./memark-work/.memark/projects.toml`

仓库里自带一个可直接试跑的样例：

[`examples/sample_room_package.json`](<repo-root>/examples/sample_room_package.json)

可以先把它放进 `inbox/promoted/`，再执行校验与晋升：

```bash
cp examples/sample_room_package.json ./memark-work/inbox/promoted/room.json
python3 -m memark validate ./memark-work/inbox/promoted/room.json
python3 -m memark promote --workspace ./memark-work
```

如果已经有 room package JSON，也可以直接放进去执行同一条主路径。

如果要把 `Codex` 目录会话同步到目录级 staging，再触发 `MemPalace` 对这些会话做 `convos` ingest，可以直接执行：

```bash
python3 -m memark codex-sync \
  --workspace ./memark-work \
  --path /abs/path/to/directory \
  --sessions-root ~/.codex/sessions

python3 -m memark mempalace-mine \
  --workspace ./memark-work
```

如果要把这条链路变成“配置一次，之后反复执行的单次调度 cycle”，可以先登记目录工作单元：

```bash
python3 -m memark project-set \
  --workspace ./memark-work \
  --project myproject \
  --path /abs/path/to/directory \
  --sessions-root ~/.codex/sessions \
  --mine-interval-seconds 120
```

然后执行一次配置化 cycle：

```bash
python3 -m memark projects-run --workspace ./memark-work
python3 -m memark automation-run --workspace ./memark-work --no-build
```

如果要把这条 cycle 安装成用户级自动调度，而不是手工或自己写定时器，当前可以直接执行：

```bash
python3 -m memark service-install \
  --workspace ./memark-work \
  --interval-seconds 300
```

如果要确认最近一轮自动 cycle 是否真的跑完，可以直接查看：

```bash
python3 -m memark automation-status --workspace ./memark-work --json
python3 -m memark service-status --workspace ./memark-work --json
```

`projects-run` 的行为是：

- 先按 `projects.toml` 执行目录级 `codex-sync`
- `codex-sync` 会把每次检测到的新版本 session 写成不可变 snapshot 路径
- 如果该目录 staging 有新增或更新，会记为 `pending_mine`
- 当达到该目录的 `mine_interval_seconds` 后，自动执行一次 `mempalace mine --mode convos`
- 非 `--json` 模式下会输出目录级阶段提示；JSON 输出也会带 `mine_started_at`、`mine_finished_at`、`mine_elapsed_seconds`

如果用户使用 `git worktree`，当前建议做法不是把 `git` 引入主模型，而是把它只当作一个自动发现触发器。对应目录复制可以直接执行：

```bash
python3 -m memark worktree-attach \
  --source-dir /abs/path/to/repo \
  --target-dir /abs/path/to/worktree
```

这条命令会把当前仓库目录下已有的目录级配置复制到目标 worktree，包括：

- `.memark/config.json`
- `.memark/projects.toml`
- `.mempalace/`
- `.codex/`
- `.claude/`
- `AGENTS.md`

后续如果要接 `git worktree add`，可以直接执行：

```bash
python3 -m memark worktree-hook-install --source-dir /abs/path/to/repo
```

这个 hook 只负责发现新 worktree 并调用 `worktree-attach`。

这样做不是多此一举，而是为了绕开 `mempalace 3.0.0` 当前 `convos` ingest 的一个实测限制：

- 同一路径会话文件第一次 ingest 后
- 如果之后只是对原文件追加内容，再次 `mine --mode convos`
- `MemPalace` 会按 `source_file` 直接跳过，不会重吃更新后的同一路径文件

因此 `MemArk` 当前的真实策略是：

- 用 ledger 识别源 session 是否变化
- 把变化后的版本写成新的 staging snapshot 文件名
- 让 `MemPalace` 把每个版本当作新的 `source_file` 摄取
- 在 `palace-package` / `palace-run` 这层按逻辑 session 只取最新 snapshot，避免旧版本混进下游 room package

这不是自写后台守护进程。

更推荐的用法是：

- 直接用 `memark service-install` 安装用户级 `launchd` 调度
- 或者继续用 `cron`、Windows Task Scheduler、CI 等系统层调度器重复调用 `projects-run`
- `MemArk` 仍然只负责单次可重复执行的 cycle，不自己实现常驻 daemon

默认情况下，第二条命令会执行：

```bash
mempalace --palace ./memark-work/.memark/palaces/<project> \
  mine ./memark-work/.memark/staging/<project>/sessions \
  --mode convos
```

其中 `staging/<project>/sessions/` 里的文件名默认类似：

```text
2026/04/09/rollout-a--1775741877453319499-03f00be8b810.md
```

也就是“原 session 逻辑名 + mtime_ns + 内容 hash 前缀”的 snapshot 形式。

如果要查看、清空或重建项目 palace，可以直接执行：

```bash
python3 -m memark palace-status --workspace ./memark-work --json
python3 -m memark palace-clean --workspace ./memark-work
python3 -m memark palace-rebuild --workspace ./memark-work
```

其中：

- `palace-status` 统计 palace 文件数、drawer 数、wing 数、room 数
- `palace-clean` 删除当前项目 palace 内容后重建空目录
- `palace-rebuild` 先 clean，再对当前 staging 重新执行 `mempalace mine --mode convos`
- `palace-retry` 不清空 palace，只重试一次当前 mine
- `mempalace-mine`、`palace-rebuild`、`palace-retry` 现在会在遇到明确的 SQLite 锁冲突时自动 backoff 重试
- 如果旧 palace 目录触发 Chroma 兼容错误，例如 `KeyError: '_type'`，CLI 会直接提示使用 `palace-rebuild`
- `mempalace-mine` 的 JSON / 文本输出会带开始时间、结束时间和耗时秒数

如果要把项目 palace 里已经 ingest 的 drawer 原样读出来做后续适配，可以执行：

```bash
python3 -m memark palace-export \
  --workspace ./memark-work \
  --json
```

当前返回的是只读 adapter 结果，包含：

- `drawer_id`
- `document`
- `wing`
- `room`
- `source_file`
- `filed_at`
- `ingest_mode`
- `extract_mode`

`palace-export` 返回的是 palace 中的原始 drawer 视图。

这意味着：

- 如果同一条 session 后续又有新的 snapshot 被 ingest
- 这里会同时看到旧 snapshot 和新 snapshot
- 这是故意保留的原始 provenance，不是自动去重后的摘要层

如果要把这些 drawer 按 `(wing, room)` 自动整理成候选 room package，可以直接执行：

```bash
python3 -m memark palace-package \
  --workspace ./memark-work \
  --json
```

如果希望直接把候选 package 写回 `inbox/promoted/`，再交给现有 `promote` / `run` 主链消费：

```bash
python3 -m memark palace-package \
  --workspace ./memark-work \
  --write-inbox
```

当前 `palace-package` 的真实边界是：

- 只读 palace 中已经存在的 drawer
- 按 `(wing, room)` 分组
- 如果同一逻辑 session 存在多个 snapshot，只保留最新 snapshot 进入 package
- 生成确定性的 room package JSON
- 保留 `drawer_id`、`source_file`、`filed_at` 等 provenance
- 不伪装成 AI 摘要器，只做保守整理

如果希望直接串起来执行：

```bash
python3 -m memark palace-run \
  --workspace ./memark-work \
  --no-build
```

这条命令会：

- 从 palace 读取 drawer
- 生成候选 room package JSON
- 写入 `inbox/promoted/`
- 立即执行 `promote`

如果不加 `--no-build`，它还会继续触发 `Graphify`。

`promote` 会把输入写成下面这种 Graphify corpus：

```bash
memark-work/
  corpus/
    myproject/
      promoted/
        room-*.md
      imports/
```

最后由 `MemArk` 触发 `Graphify`：

```bash
python3 -m memark build --workspace ./memark-work --update --wiki
```

如果希望“一次消费 inbox 并立刻触发 Graphify”，可以直接：

```bash
python3 -m memark run --workspace ./memark-work --update --wiki
```

其中当前实现约定：

- `inbox/promoted/` 放 room package JSON
- 注册项目根目录中的正式文档会被直接消费
- `run` 会先消费这两个目录，再触发 `Graphify`

注意：

- 当前版本不会伪造 `MemPalace` 的 `since` 接口
- 当前版本已经能从 palace 读 drawer，并生成候选 room package
- 当前版本已经能把 `palace-package -> promote -> 可选 build` 串成一条 CLI
- 但“哪些 drawer 值得晋升、哪些只该停留在原始记忆层”仍是治理问题，不是上游自动保证
- `MemArk` 当前负责的是稳定消费这些 package，并落成 `Graphify` 能直接吃的 corpus
- 如果当前走的是 `_rebuild_code` fallback，真正进入图谱的主要还是代码树；`promoted/` 与注册项目文档仍更像是已整理好的待编译语料
- `memark status --json` 可作为脚本化验收入口
- 如果要让 `MemPalace` 与 `Graphify` 的实测结果保持干净，项目本身还应维护 `.gitignore` 和 `.graphifyignore`

## 文档

- [`README.md`](<repo-root>/README.md)：项目入口
- [`SKILL.md`](<repo-root>/SKILL.md)：默认生产入口 Skill
- [`skill-dev.md`](<repo-root>/skill-dev.md)：开发期安装测试 Skill
- [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md)：项目边界、组件关系、当前状态
- [`docs/GOVERNANCE_MODEL.md`](docs/GOVERNANCE_MODEL.md)：闲聊、项目对话、产出文档的隔离与晋升模型
- [`docs/INTERFACE_CONTRACT.md`](docs/INTERFACE_CONTRACT.md)：推荐输入契约、输出契约与 Markdown 包格式
- [`docs/INSTALL_VERIFICATION.md`](docs/INSTALL_VERIFICATION.md)：真实安装与 CLI 验证结果
- [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md)：当前 Python CLI 的实现范围与后续分层
- [`docs/ACCEPTANCE_CHECKLIST.md`](docs/ACCEPTANCE_CHECKLIST.md)：当前版本的验收标准与完成状态
- [`docs/PRODUCT_REQUIREMENTS.md`](docs/PRODUCT_REQUIREMENTS.md)：基于 `MemPalace` 与 `Graphify` 能力面收敛出的具体需求
- [`docs/MILESTONE_BETA.md`](docs/MILESTONE_BETA.md)：当前仓库自己吃自己的 Beta 里程碑与出站条件
- [`docs/MILESTONES.md`](docs/MILESTONES.md)：按阶段整理的能力账本，方便直接看当前应用已实现什么、下一步做什么
- [`docs/MILESTONE_NEXT.md`](docs/MILESTONE_NEXT.md)：Beta 之后下一阶段里程碑，优先收口长期稳定性与消费闭环，而不是先扩跨平台
- [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md)：按当前 Beta 口径对外说明或内部推广前的发布检查清单
- [`docs/DOGFOOD_RUNBOOK.md`](docs/DOGFOOD_RUNBOOK.md)：当前仓库持续自己吃自己时的日常操作与排障入口
- [`docs/DOGFOOD_LOG.md`](docs/DOGFOOD_LOG.md)：按时间追加的当前仓库真实 dogfood 证据
- [`docs/AI_CONSUMPTION_MODEL.md`](docs/AI_CONSUMPTION_MODEL.md)：项目 AI 当前应如何实际消费 `MemPalace`、`Graphify` 与 `MemArk` 产物
- [`docs/DOCUMENT_STATUS.md`](docs/DOCUMENT_STATUS.md)：正式文档与研究归档的关系
- [`docs/MAINTAINER_SKILL.md`](docs/MAINTAINER_SKILL.md)：旧的维护型 Skill 说明
- [`examples/sample_room_package.json`](examples/sample_room_package.json)：可直接试跑的 room package 示例

如果你想直接从 CLI 看当前阶段和功能账，而不是先翻文档：

```bash
python3 -m memark milestones
python3 -m memark milestones --workspace .
python3 -m memark status --workspace . --json
```

其中 `memark milestones --workspace .` 现在不只展示阶段和证据，还会直接评估当前里程碑是否已达成、当前阻塞项是什么。
`memark status --workspace . --json` 现在还会直接给出 corpus 级 `graphify_corpus.status`，用来区分：

- 当前 corpus 还没有 graph：`graph_missing`
- 已 onboard，但还没生成 corpus 级 `graphify-out/graph.json`：`onboarded_graph_missing`
- 已有真实 mixed-corpus ingestion proof：`ingested`

`memark context` 生成的自动消费产物现在也会带出这条状态：

- `ai-context.md` 会包含 `graphify_corpus_status`、`graphify_onboarding_status`、`graphify_proof_diagnostics`
- `graphify-status.md` 会直接写出 `corpus_status`、`onboarding_status`、证据图路径与推荐 update 命令

如果上游 `Graphify` skill 已经真实 ingest 了当前 corpus，可以用两种方式让系统认出这条闭环证据：

- 显式记录：`python3 -m memark graphify-proof --workspace . --record-ingested ...`
- 自动识别：让 `corpus/<project>/graphify-out/graph.json` 里真实包含来自 `promoted`、注册项目文档、`imports` 的节点；之后 `memark graphify-proof` / `milestones` 会自动认出它

## 开源价值

这个项目值得开源，不是因为它重新发明了记忆或图谱，而是因为它试图把两种已经成立的能力接干净：

- `MemPalace` 的“记住与找回”
- `Graphify` 的“编译与导航”

如果这条桥接契约被定义清楚，用户就不必在记忆层和知识层之间手工搬运语料。
