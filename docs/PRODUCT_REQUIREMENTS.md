# Product Requirements

本文件只回答一个问题：

既然要同时利用 `MemPalace` 和 `Graphify`，`MemArk` 具体应该满足什么需求，才能真的做到 `1 + 1 > 2`。

## 上游能力结论

### `MemPalace` 的能力面

从上游 README、安装版 CLI 和包内源码可以确认：

- 它能把项目资料和对话都挖进同一个 palace
- 它的核心结构是 `wing -> hall -> room -> closet -> drawer`
- `closet` 是摘要层，`drawer` 是逐字原文层
- 它不只是 search，还支持 `wake-up`
- 它有 MCP server
- 它支持 hooks / 自动 mine 这类持续采集路径

结论：

`MemPalace` 最强的是“持续记忆、结构组织、精确找回、短上下文唤醒”。

### `Graphify` 的能力面

从上游 README、安装版 CLI、包内模块和帮助输出可以确认：

- 它能把一个目录里的代码、文档、图片、研究材料转成知识图谱
- 它不只是生成静态输出，还围绕 `graph.json` 提供 query / MCP / 平台集成
- 它适合面对持续累积的 corpus
- 它能产出 `GRAPH_REPORT.md`、`graph.json`、`graph.html`、wiki、Obsidian 等知识表面
- 它有 watch / hook 思路，但不同版本的顶层 CLI 构建入口并不完全稳定

结论：

`Graphify` 最强的是“把边界清晰的项目语料编译成可导航、可查询、可继续喂给 AI 的知识图谱层”。

## 为什么要结合

如果只有 `MemPalace`：

- 能记住
- 能找回
- 能追溯原文
- 但项目知识的可浏览性、可总览性、跨材料结构化导航仍然偏弱

如果只有 `Graphify`：

- 能编译知识图谱
- 能生成报告和 wiki
- 能继续 query / MCP
- 但它不负责替你长期保存对话，也不负责记忆治理

所以两者结合的价值不是重复，而是分工：

- `MemPalace` 负责记忆的保真、分层、检索、唤醒
- `Graphify` 负责知识的编译、查询、导航、再利用
- `MemArk` 负责晋升和编排

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
- 默认以 `closet` 为正文来源
- `drawer` 只保留引用、证据和追溯信息

说明：

这是 `MemArk` 的治理策略，不是上游强制格式。

### R4. 项目会话和正式文档必须分层进入同一 corpus

- 项目对话晋升结果进入 `corpus/<project>/promoted`
- 已落盘文档进入 `corpus/<project>/documents`
- 其他预处理材料进入 `corpus/<project>/imports`

### R5. Graphify 的消费面不应只停在 build

- 编译后要把 `GRAPH_REPORT.md` 当作第一阅读入口
- 要把 `graph.json` 当作 AI 可查询接口
- 要支持 wiki / Obsidian / MCP 作为后续消费面

### R6. Graphify 调用必须适配版本差异

- `MemArk` 不能再假设任何安装版 `graphify` 都支持同一条顶层 build 命令
- 必须允许“兼容的 Graphify 构建入口”作为外部依赖
- 当遇到 helper/query 型 CLI 时，要明确提示接口不匹配

### R7. 运行方式必须 CLI-first

- 可脚本化
- 可放进自动化流程
- 不依赖桌面常驻应用

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
