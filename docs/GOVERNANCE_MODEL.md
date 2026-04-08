# Governance Model

本文件回答一个更具体的问题：

面对三类不同材料时，`MemPalace`、`Graphify`、`MemArk` 分别应该怎么处理，哪些内容该隔离，哪些内容该晋升，哪些内容最适合喂给 `Graphify`。

这三类材料是：

1. 天南海北的长期聊天
2. 面向具体项目的 AI 助手对话
3. 对话后产生的文档、代码、笔记、报告

## 先把 `MemPalace` 看清楚

按 `MemPalace` 官方当前 README，它的宫殿结构不是“一个大向量库”，而是明确分层的：

- `wing`：人或项目，是第一层边界
- `hall`：记忆类型，如 `hall_facts`、`hall_events`、`hall_discoveries`、`hall_preferences`、`hall_advice`
- `room`：具体主题，如 `auth-migration`、`ci-pipeline`
- `closet`：指向原始内容的摘要
- `drawer`：原始逐字内容，exact words, never summarized

这意味着，`MemPalace` 的“顶层暴露”首先不是原始文档，而是：

1. `wing`
2. `wing` 下面的 `room`
3. `room` 下面按 `hall` 归类的主题记忆

对 `MemArk` 来说，这个层次非常关键，因为它决定了什么适合继续送到 `Graphify`。

## 哪一层最适合喂给 `Graphify`

先说明口径：

下面的“`room + closet (+ drawer refs)`”不是 `MemPalace` 或 `Graphify` 官方强制接口，而是 `MemArk` 当前采用的桥接治理策略。

在这个前提下，结论是：

最适合喂给 `Graphify` 的默认单位，不是整个宫殿，也不是裸 `drawer`，而是：

- 以 `project wing` 为边界
- 以 `room` 为基本主题单元
- 以 `closet` 为优先抽取对象
- 必要时附上对应 `drawer` 的原文引用或节选

也就是：

`project wing -> hall -> room -> closet (+ drawer refs)`

原因如下。

### 为什么不是直接喂 `drawer`

`drawer` 是原始逐字内容，最完整，也最适合溯源。

但如果把全部 `drawer` 原样喂给 `Graphify`：

- 噪音太大
- 闲聊、试探、重复表述会很多
- 同一个主题会出现大量近似内容
- `Graphify` 会被迫替你做第一轮“去混杂”

这会削弱 `MemPalace` 已经做好的结构价值。

### 为什么也不能只喂最顶层 taxonomy

如果只喂 `wing` 列表、`room` 列表或纯 taxonomy：

- 信息太薄
- 缺少足够的主题内容
- 只能做目录，做不出有解释力的知识图谱

`Graphify` 需要的不是只有目录名，而是“带有内容的主题包”。

### 为什么 `room + closet` 最合适

`room` 已经把一堆对话和材料压到一个明确主题上。

`closet` 又是“指向原始内容的摘要”，既比 taxonomy 丰富，又比全量 `drawer` 干净。

因此，最合理的默认输入包是：

- `wing` 作为项目边界
- `hall` 作为语义标签
- `room` 作为一篇知识条目的主题
- `closet` 作为该条目的核心正文
- `drawer` 只作为引用、证据、追溯链接，不默认全量展开

对 `Graphify` 来说，这种输入最接近“已经过一次项目语义整理的原始语料”，而不是毫无边界的聊天洪水。

## 三类材料怎么治理

### 1. 天南海北的长期聊天

这类内容默认应该：

- 进入 `MemPalace`
- 放在 `wing_general` 或对应 `person wing`
- 不默认进入 `Graphify`

原因很简单：

- 它适合记忆，不一定适合编译成项目知识
- 它对长期个性化检索有价值
- 但对项目图谱常常是噪音

只有当其中某段内容后来被确认与某项目强相关，才允许晋升。

### 2. 项目 AI 助手对话

这类内容默认应该：

- 进入对应 `project wing`
- 在 `hall` 中区分是事实、事件、发现还是建议
- 先保留在 `MemPalace`
- 再由 `MemArk` 挑出值得晋升的 `room` 增量

这类内容是 `MemArk` 最主要的原料来源。

因为这里面常常有：

- 决策
- 设计取舍
- 故障排查
- 里程碑推进
- 可复用的经验模式

这些都比泛聊天更适合继续变成项目知识图谱。

### 3. 对话产生的文档

这类内容最适合直接进入 `Graphify` 的项目语料目录。

例如：

- 设计文档
- ADR
- 复盘
- 需求草稿
- API 说明
- 调研笔记

一旦这些内容已经落盘，它们就不该继续只作为“聊天记忆”存在，而应成为 `Graphify` 的一等输入。

## `MemArk` 应做的不是同步，而是晋升

`MemArk` 最重要的职责不是：

- 把 `MemPalace` 全量导出给 `Graphify`

而是：

- 在 `MemPalace` 中识别什么已经值得成为“项目知识输入”
- 把这些内容稳定地落成项目语料
- 再交给 `Graphify` 做图谱、报告、Wiki、Obsidian 输出

所以，`MemArk` 的动作应该叫 `promotion`，而不只是 `sync`。

## 推荐晋升单位

默认推荐以 `room` 为单位做晋升。

每次晋升一个 `room` 时，建议生成一个面向 `Graphify` 的 Markdown 包，包含：

- `project wing`
- `hall`
- `room`
- `closet` 摘要正文
- 关键时间
- 涉及的人、模块、文档、决策
- 指向原始 `drawer` 的引用信息

这比直接倒原始聊天更稳，因为它：

- 已经有项目边界
- 已经有主题边界
- 已经有记忆类型边界
- 仍然保留对原文的追溯能力

## 推荐隔离模型

最稳的做法是三层隔离。

### Layer A: Memory

全部内容先进 `MemPalace`。

这里接受：

- 闲聊
- 项目对话
- 原始材料导入

但必须有 `wing` 边界：

- `wing_general`
- `wing_person_*`
- `wing_project_*`

### Layer B: Promoted Corpus

只有被 `MemArk` 晋升的项目材料进入这一层。

这一层的单位不是“所有聊天”，而是：

- `room` 级主题包
- 正式文档
- 代码和项目文件

这才是 `Graphify` 应该面对的输入目录。

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
- `wing_general`
- 未筛选的原始 `drawer` 批量导出

它最适合连接到：

- 某个项目的晋升语料目录
- 已落盘的项目文档目录
- 代码仓库与设计资料的组合目录

也就是说，`Graphify` 处理的是 corpus，不是 live memory。

## 最终建议

如果要把 `MemPalace` 和 `Graphify` 接得干净，推荐采用下面这条主路径：

1. 所有聊天和原始材料先进入 `MemPalace`
2. 用 `wing` 做人/项目边界
3. 在项目 wing 中，以 `room` 为主题单元组织记忆
4. 默认从 `closet` 抽取内容，必要时附带 `drawer` 引用
5. 由 `MemArk` 把这些主题包写入项目语料目录
6. 由 `Graphify` 对该目录做 `--update`、`--wiki`、`--obsidian` 等编译输出

一句话说：

`MemPalace` 负责保存和找回世界，`Graphify` 负责编译项目知识，`MemArk` 负责把宫殿里真正值得晋升的房间送过去。
