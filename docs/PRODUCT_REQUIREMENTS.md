# Product Requirements

本文件只回答一个问题：

既然要同时利用 `MemPalace` 和 `Graphify`，`MemArk` 具体应该满足什么需求，才能真的做到 `1 + 1 > 2`。

这里的目标必须拆成前后两段：

1. 先把项目相关对话和材料稳定喂进去
2. 再在项目 AI 真正需要时，把更有用的结果拿出来

如果只有第一段，没有第二段，`MemArk` 只是数据搬运层，还没有形成足够产品价值。

## 上游能力结论

以下结论以 2026-04-08 的实际使用结果为准，不再只基于 README 或源码推断。

### `MemPalace` 的能力面

从实际命令执行、MCP 调用和 palace 数据检查可以确认：

- 它能把项目资料和对话都挖进同一个 palace
- 它的 CLI 主路径是真实可用的：`mine`、`search`、`wake-up`、`status`
- 它不只是 search，还支持 `wake-up`
- 它有 MCP server
- 它的 MCP 面不只是搜索，还包含 drawer、diary、知识图谱和 taxonomy 工具
- 实际顶层存储是 `chroma.sqlite3` 与 ANN 文件
- 对桥接层最有价值的表面，是 drawer text 与 metadata，不是底层索引文件

结论：

`MemPalace` 最强的是“持续记忆、结构组织、精确找回、短上下文唤醒”。

### `Graphify` 的能力面

从安装版 CLI、源码模块、导出结果和实际 watch/query/benchmark 可以确认：

- 它的代码图重建、报告、查询、导出、AI 集成都是真实可用的
- 它能产出 `GRAPH_REPORT.md`、`graph.json`、`graph.html`、GraphML、SVG、Cypher、Obsidian 等输出
- watch 对代码和文档采用不同策略，这点是实测确认的
- 安装版 CLI 的公开表面明显窄于官方 skill 叙事
- 不同环境下还依赖 `watchdog`、`mcp`、`matplotlib` 等额外包

结论：

`Graphify` 最强的是“把边界清晰的项目语料编译成可导航、可查询、可继续喂给 AI 的知识图谱层”。

补充限制：

- `detect()` 能识别文档、论文、图片
- 但当前公开 Python 提取入口 `extract()` 只处理代码 AST
- `watch()` 对非代码变化只会写 `needs_update` 并提示去 AI 平台里执行 `/graphify --update`
- 因此，当前 `Graphify` 的 mixed-corpus 语义提取主路径仍然是上游 skill 驱动，而不是一个可直接由 `MemArk` 本地复用的稳定纯 Python API

## 为什么要结合

如果只有 `MemPalace`：

- 能记住
- 能找回
- 能追溯原文
- 还能用 MCP 协议化地写 diary、facts、drawers
- 但项目知识的可浏览性、可总览性、跨材料结构化导航仍然偏弱

如果只有 `Graphify`：

- 能编译知识图谱
- 能生成报告和导出物
- 能继续 query / serve / AI 集成
- 但它不负责替你长期保存对话，也不负责记忆治理

所以两者结合的价值不是重复，而是分工：

- `MemPalace` 负责记忆的保真、分层、检索、唤醒
- `Graphify` 负责知识的编译、查询、导航、再利用
- `MemArk` 负责晋升和编排

但还要加一个实测后的限制条件：

- 如果 corpus 还很小，`Graphify` 可能不是刚需
- 当前 `memark` 仓库实测约 `15,186` words，`Graphify` 直接提示“可能不需要 graph”
- 因此 `1 + 1 > 2` 不是默认成立，它依赖治理质量和 corpus 规模

## 1 + 1 > 2 的具体场景

### 场景 A: 天南海北聊天

需求：

- 这类内容默认只进 `MemPalace`
- 允许后续按项目相关性再晋升
- 不默认进入 `Graphify`

原因：

- 对个体记忆有用
- 对项目图谱大多是噪音

### 场景 B: 项目 AI 助手对话

需求：

- 默认进入对应 `project wing`
- 保留原始逐字内容
- 同时能抽出值得晋升的主题单元
- 在默认组合里，优先把这类材料作为 `MemPalace` 的主输入面

原因：

- 这是两个系统结合后最有价值的原料
- 这里面包含决策、取舍、排障、里程碑和可复用方法

### 场景 C: 对话后产生的文档

需求：

- 已落盘文档直接进入 `Graphify` 项目 corpus
- 同时保留与 `MemPalace` 里对话记忆的追溯关系

原因：

- 文档已经是高密度项目知识
- 它们应成为知识图谱的一等输入

### 场景 D: 项目内 AI 需要消费结果

需求：

- 当 AI 正在开发项目、排障、继续讨论方案时，不能只知道“数据已经被喂进去”
- AI 需要能在合适时机读到：
  - `MemPalace` 里的历史决策、失败尝试、上下文
  - `Graphify` 里的结构图、报告、query 结果、wiki 导航
  - `MemArk` 晋升后的项目知识 Markdown
- 消费结果必须比“不使用 MemArk，只靠当前会话上下文”更有价值

原因：

- 用户真正要的不是存档本身
- 用户要的是项目内 AI 在后续工作时回答更准、延续性更强、重复劳动更少

## MemArk 必须满足的产品需求

### R1. 明确边界

- `MemArk` 不是新的记忆系统
- `MemArk` 不是新的图谱引擎
- `MemArk` 是桥接和晋升层

### R2. 输入必须稳定

- 第一稳定输入契约是 `room package JSON`
- 不假装已经有稳定的 `MemPalace since timestamp` 接口
- 不直接承诺兼容 `MemPalace` 内部数据库

### R3. 晋升单位必须治理过

- 默认只处理 `project wing`
- 默认以 `room` 为主题单位
- 默认以筛选后的 drawer text 为正文来源
- 必须保留来源、时间、room 等追溯信息
- 如果上游是 `Codex sessions/**/*.jsonl` 这类 conversation ingest，桥接层要准备自己从 `session_meta` 和 `chroma:document` 解析 `cwd`、`session_id`、`ts`

说明：

这是 `MemArk` 的治理策略，不是上游强制格式。

补充：

- 当前不应再把 `closet` 写成已验证的唯一桥接切口
- 这次真正验证到的、最上层且最可消费的表面是 Chroma metadata 加 drawer text
- 对会话型 palace，默认只按 `room` 晋升会过粗；当前仓库实测会收敛成 `technical` / `architecture` 两个大桶
- 因此桥接层必须支持比 `room` 更细的治理单位；当前已验证可行的一档是“按逻辑 session 分组晋升”
- 这一步的目标不是替代 `MemPalace search`，而是把“值得反复读的单次项目对话”整理成更适合继续消费的 corpus 单元

### R4. 项目会话和正式文档必须分层进入同一 corpus

- 项目对话晋升结果进入 `corpus/<project>/promoted`
- 已落盘文档进入 `corpus/<project>/documents`
- 其他预处理材料进入 `corpus/<project>/imports`

### R4.1. 派生产物必须先隔离

- `MemArk` 不能把 `graphify-out/` 再喂回 `MemPalace`
- `MemArk` 不能把实验目录、临时工作目录、palace 数据目录默认送进任一上游工具
- 项目级忽略规则必须先覆盖这些派生产物

说明：

当前仓库最新 dogfood 已实测到：

- 未补充忽略规则时，`MemPalace` 会把 `.graphify_detect.json`、`entities.json`、`docs/raw/` 一并采进 palace
- 补充忽略规则后，当前仓库的 `MemPalace` 结果收敛到 `28 files / 200 drawers`
- 同时 `Graphify detect` 也从 `35 files / ~18.7k words` 收敛到 `25 files / ~11.6k words`

### R5. Graphify 的消费面不应只停在 build

- 编译后要把 `GRAPH_REPORT.md` 当作第一阅读入口
- 要把 `graph.json` 当作 AI 可查询接口
- 要支持 wiki / Obsidian / MCP 作为后续消费面

### R5.1. 必须定义“怎么出数据给 AI 用”

- `MemArk` 的目标不只是 ingest 成功
- 必须明确区分三类可消费结果：
  - 记忆找回：由 `MemPalace search / wake-up / MCP` 消费
  - 项目知识语料：由 `promoted/*.md` 和 `documents/` 消费
  - 结构化导航：由 `Graphify` 的 `GRAPH_REPORT.md`、`graph.json`、query、wiki、MCP 消费

说明：

- `MemPalace` 负责“以前发生过什么”
- `Graphify` 负责“项目现在是什么结构”
- `MemArk` 负责“从原始记忆中挑出值得反复给 AI 看的项目知识”

### R5.2. 消费效果必须优于“不使用 MemArk”

至少应带来下面一种改进：

- AI 能找回以前的项目决策，而不是重复讨论
- AI 能找回以前的失败尝试，而不是重复踩坑
- AI 能读到项目级晋升文档，而不是只依赖当前对话窗口
- AI 能结合 `Graphify` 结构结果更快定位代码位置、影响面和相关模块

如果做不到这些，说明当前只完成了 ingest，没有完成产品目标。

### R6. Graphify 调用必须适配版本差异

- `MemArk` 不能再假设任何安装版 `graphify` 都支持同一条顶层 build 命令
- 必须允许“兼容的 Graphify 构建入口”作为外部依赖
- 当遇到 helper/query 型 CLI 时，要明确提示接口不匹配，或退回已验证的兼容路径
- 同时不能要求用户手工先把 `~/.memark/venv/bin` 永久加进 shell `PATH`；workspace 在使用默认命令名时，应能回退到用户级 runtime 里的 `mempalace` / `graphify`
- 当前仓库里已实现的兼容路径是 `graphify.watch._rebuild_code`
- 但这个兼容路径只适用于 code graph 重建，不应伪装成完整 semantic build

### R6.1. 必须区分“语料已整理”与“语料已进图”

- `promoted/` 和 `documents/` 可以先作为 Graphify-ready corpus 落盘
- 但如果当前实际调用的是 `_rebuild_code` fallback，就不能宣称这些 Markdown 已经进入最终图谱
- 只有在接上真实 mixed-corpus Graphify build 入口后，才能把“记忆晋升 -> 图谱编译”写成完整闭环
- 当前更准确的说法是：
  - `MemArk` 负责把会话整理成 `Graphify` 能消费的目录边界
  - 上游 `Graphify` skill / AI 平台负责真正对这些文档做语义提取并更新图谱

### R7. 运行方式必须 CLI-first

- 可脚本化
- 可放进自动化流程
- 不依赖桌面常驻应用

### R7.1. 安装入口必须是用户级 Skill

- 用户应把 `MemArk` 的安装 Skill 交给自己的 AI 工具
- 安装完成后，`MemArk` 的一组 skills 与脚本应进入用户 AI 工具的 skill 目录
- 之后用户在任意项目里与 AI 对话时，AI 应能自动调用 `MemArk`
- 安装 Skill 本身不是运行时全部能力，而是安装器

### R7.2. Skill bundle 必须与运行脚本分层

- 至少区分：
  - 安装 Skill
  - 运行时 Skill
  - 启动脚本 / CLI 入口
- 不能把所有职责都塞进单一 `SKILL.md`
- 开发期验收 Skill 与生产安装 Skill 也应区分

### R8. 后续可扩展，但当前不能伪实现

- 后续可增加 `MemPalace` extractor / adapter
- 后续可增加自动监控
- 当前不能把这些写成已完成能力

## 当前对本仓库的直接影响

基于以上需求，当前仓库最需要保持准确的地方是：

- 不把 `MemPalace` 写窄成“只是搜索”
- 不把 `Graphify` 写窄成“只是 wiki 导出”
- 不把 `room + closet` 写成上游官方唯一正确答案
- 不把 `graphify <folder>` 写成已经稳定验证的跨版本公共契约
- 不把当前 code-only fallback 写成“晋升后的记忆已经全部被 Graphify 消费”
