# Governance Model

本文件回答一个更具体的问题：

面对三类不同材料时，`MemPalace`、`Graphify`、`MemArk` 分别应该怎么处理，哪些内容该隔离，哪些内容该晋升，哪些内容最适合喂给 `Graphify`。

这三类材料是：

1. 天南海北的长期聊天
2. 面向具体项目的 AI 助手对话
3. 对话后产生的文档、代码、笔记、报告

## 先把 `MemPalace` 看清楚

从这次实际测试看，`MemPalace` 有两层都很重要。

第一层是它对外讲的宫殿结构：

- `wing`
- `hall`
- `room`
- `closet`
- `drawer`

第二层是当前真正容易被 bridge 层消费的落地表面：

- `chroma.sqlite3`
- 其中的 metadata
- `chroma:document`

这两层不能混为一谈。

如果讨论“产品语义结构”，`wing / hall / room / closet / drawer` 当然重要。
但如果讨论“`MemArk` 今天到底从哪里稳定取数据”，当前实测更可靠的切口是：

- `wing`
- `room`
- `source_file`
- `filed_at`
- `ingest_mode`
- `extract_mode`
- `chroma:document`

尤其对 `Codex` 会话场景，更要先加一层现实修正：

- `MemPalace` 不会自动根据 `session_meta.payload.cwd` 帮你拆项目
- 如果把两个项目的 session 文件放进同一个输入目录，它会被挖成同一个 wing

所以，真正的顶层治理边界其实不是 palace 里已经存在的 taxonomy，而是：

1. `MemArk` 先按项目切输入
2. `MemPalace` 再 ingest 项目级输入
3. `MemArk` 再从项目级结果里抽可晋升内容

## 哪一层最适合喂给 `Graphify`

当前必须把“理想结构”和“已验证切口”分开。

理想上，最适合喂给 `Graphify` 的不是整座 palace，也不是裸会话洪水，而是经过主题整理、保留证据的项目知识包。

但按这次已验证结果，`MemArk` 现在最应依赖的默认抽取单位不是“官方稳定 closet 导出”，而是：

- 先用 `session_meta.payload.cwd` 切出项目级 `Codex` 会话
- 再让 `MemPalace` ingest 这个项目级会话目录
- 再从 `metadata + chroma:document` 中整理候选主题内容
- 最后生成 `Graphify-ready` Markdown

也就是：

`project-scoped sessions -> MemPalace convo chunks -> curated promoted markdown`

### 为什么不是直接喂全部 `drawer`

- 噪音太大
- 重复太多
- 会话里大量内容只是推进过程，不是最终知识

### 为什么也不能只喂 taxonomy

- 只有 `wing` 或 `room` 名称太薄
- `Graphify` 需要的是有正文的 corpus

### 当前最稳的默认治理

当前默认不应再写成“`room + closet` 已经是实测稳定桥接面”。

更准确的说法是：

- `room` 仍然适合作为主题边界
- 但当前已实测、最稳的读取面是 `chroma metadata + chroma:document`
- `MemArk` 需要自己把 chunked 会话文本整理成更适合 `Graphify` 的主题包

## 三类材料怎么治理

### 1. 天南海北的长期聊天

这类内容默认应该：

- 进入 `MemPalace`
- 留在 `general` 或 `person` 边界
- 不默认进入 `Graphify`

原因：

- 它适合长期记忆和唤醒
- 但通常不适合直接编译为项目知识

### 2. 项目 AI 助手对话

这类内容默认应该：

- 先在 `MemArk` 侧按项目切分
- 再进入对应项目自己的 `MemPalace` ingest 流
- 先保留原始逐字内容
- 再由 `MemArk` 抽出值得晋升的内容

这里要特别强调：

- 对 `Codex`，默认输入不是 `history.jsonl`
- 而是 `~/.codex/sessions/**/*.jsonl`
- 并且必须先按 `session_meta.payload.cwd` 过滤

这类内容是 `MemArk` 最主要的原料来源，因为里面有：

- 决策
- 设计取舍
- 排障过程
- 里程碑推进
- 可复用方法

### 3. 对话产生的文档

这类内容最适合直接进入 `Graphify` 的项目语料目录。

例如：

- 设计文档
- ADR
- 复盘
- 需求草稿
- API 说明
- 调研笔记

一旦已经落盘，它们就是正式 corpus，不应继续只作为“聊天记忆”存在。

## `MemArk` 应做的不是同步，而是晋升

`MemArk` 最重要的职责不是“全量同步”，而是“项目级晋升”。

它不应该：

- 把 `MemPalace` 全量倒给 `Graphify`

它应该：

- 先治理项目边界
- 再识别哪些项目会话内容值得保留
- 再把这些内容稳定地落成项目语料
- 最后交给 `Graphify`

## 推荐晋升单位

默认推荐以“项目主题包”为单位做晋升。

在当前实现口径里，这个主题包通常应包含：

- 项目标识
- 候选主题标题
- 整理后的正文
- 关键时间
- 涉及的人、模块、文件、文档、决策
- 指向原始 session 文件或 drawer 的证据引用

未来它可以映射成 `room` 级对象，但当前不要把这一层写死成已经验证的官方导出格式。

## 推荐隔离模型

最稳的做法是三层隔离。

### Layer A: Raw Memory

这里接受：

- 闲聊
- 项目对话
- 原始材料导入

但对 `Codex` 项目对话，真正第一道边界不是 palace 内 wing，而是 `MemArk` 的项目级 staging。

### Layer B: Promoted Corpus

只有被 `MemArk` 晋升的项目材料进入这一层。

这一层的单位不是“所有聊天”，而是：

- 晋升后的项目主题包
- 正式文档
- 代码和项目文件

这才是 `Graphify` 应该面对的输入目录。

但这里有一条必须额外补上的治理规则：

- 派生产物不能回流

至少要排除：

- `graphify-out/`
- `.experiments/`
- `.mempalace/`
- `memark-work/`

原因不是洁癖，而是已经实测到：

- `MemPalace mine` 会因为忽略规则不同而产生显著不同结果
- `Graphify detect` 也不会天然替你区分“项目知识”和“上次实验产物”

所以桥接之前，必须先隔离，后晋升。

### Layer C: Compiled Knowledge

由 `Graphify` 输出：

- `GRAPH_REPORT.md`
- `graph.json`
- `graph.html`
- `--wiki` 生成的 Markdown Wiki
- `--obsidian` 生成的 Vault

这层才是给人和 AI 消费的知识表面。

## `Graphify` 在这套模型里的位置

`Graphify` 最适合面对的是“一个持续积累、边界清晰的项目语料目录”。

因此它不应该直接连接到：

- `MemPalace` 全量聊天
- `general` 边界
- 未筛选的原始会话 chunk 批量导出

它最适合连接到：

- 某个项目的晋升语料目录
- 已落盘的项目文档目录
- 代码仓库与设计资料的组合目录

也就是说，`Graphify` 处理的是 corpus，不是 live memory。

## 最终建议

- `MemPalace` 负责保真记忆
- `Graphify` 负责知识编译
- `MemArk` 负责项目隔离、增量治理、晋升和编排

对 `Codex` 场景，当前最重要的治理不是“先谈 palace 里的 room/closet”，而是：

1. 从 `~/.codex/sessions/**/*.jsonl` 读真实 session
2. 按 `session_meta.payload.cwd` 做项目归属
3. 为每个项目维护独立 staging
4. 再执行项目级 `MemPalace convo mine`
5. 再从项目级结果晋升到 `Graphify`
