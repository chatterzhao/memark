# MemArk

> 把 `MemPalace` 里的项目记忆，整理成 `Graphify` 最适合消费的项目语料。

上游项目：

- `MemPalace` GitHub: <https://github.com/milla-jovovich/mempalace>
- `Graphify` GitHub: <https://github.com/safishamsi/graphify>

## 当前判断

基于上游源码、README 和本仓库里的实际安装验证，当前可以把三者关系收敛为：

- `MemPalace`：记忆层。保留原始内容，按 `wing -> hall -> room -> closet -> drawer` 组织，并通过 CLI / MCP 供 AI 检索。
- `Graphify`：知识编译层。读取目录语料，生成 `graph.json`、`GRAPH_REPORT.md`、`graph.html`，也可输出 `--wiki`、`--obsidian`、`--mcp`。
- `MemArk`：桥接层。把 `MemPalace` 中具备项目知识价值的内容，整理成 `Graphify` 的稳定输入目录。

`MemArk` 不是新的记忆系统，也不是新的图谱引擎。

## 两个上游到底怎么用，才能发挥它们的强项

### `MemPalace`

`MemPalace` 的强项不是“人工天天搜库”，而是：

- 本地保存原始对话和资料
- 让 AI 在后续对话里自动找回上下文
- 在需要时追溯到原始逐字内容

更合适的使用方式是：

1. 安装并执行一次 `mempalace init`、`mempalace mine`
2. 把它作为 MCP 接给 Claude / ChatGPT / Cursor / Gemini 一类 AI
3. 让 AI 在问答时自动调用搜索，而不是把它当成人工知识库 UI

需要特别注意的一点是：

- 当前源码里可以看到 drawer metadata 含 `filed_at`
- 但没有核对到一个稳定公开的“按时间戳取增量” CLI 或 MCP 接口

这意味着 `MemArk` 不能假设上游已经提供现成的 `since` 拉取能力。

### `Graphify`

`Graphify` 的强项也不只是“把内容排成 wiki”。

它更像一个 skill/CLI-first 的知识编译器，适合：

- 对一个持续积累的 corpus 目录运行
- 先形成图谱和报告，再让人或 AI 沿结构下钻原文
- 用 `--update`、`--watch` 处理增量变化

更合适的使用方式是：

1. 给它一个稳定的项目语料目录，而不是每次手工粘贴聊天
2. 先让 AI 读 `GRAPH_REPORT.md` 或 `graph.json` 暴露出的结构
3. 把代码、文档、图像、研究材料和晋升后的项目记忆放在同一个 corpus 边界里

## MemArk 该做什么

`MemArk` 的合理职责是：

1. 从 `MemPalace` 中识别哪些内容已经值得晋升为项目知识
2. 以 `project wing` 为边界，按 `room` 组织这些内容
3. 优先抽取 `closet`，必要时附上 `drawer` 引用
4. 落成 `Graphify` 可直接消费的 Markdown 语料
5. 触发 `Graphify` 对 corpus 做 `--update`、`--wiki` 或其他编译

当前最稳的默认晋升单位不是整个宫殿，也不是裸 `drawer`，而是：

`project wing -> hall -> room -> closet (+ drawer refs)`

原因很直接：

- 直接喂全量 `drawer`，噪音太大
- 只喂顶层 taxonomy，信息又太薄
- `room + closet` 正好保留了主题边界和足够正文

## 当前仓库提供什么

这个仓库当前仍然是文档仓库，不是 `MemArk` 运行时实现仓库。

已经提供：

- 经过收敛的项目定义
- `MemPalace -> MemArk -> Graphify` 的治理和接口说明
- 一个只负责安装上游工具的 [`SKILL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/SKILL.md)
- 基于真实命令执行结果的安装验证记录

还没有提供：

- `MemArk` 自己的 CLI
- 稳定的增量抽取实现
- 后台监控或同步服务

## 文档

- [`README.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/README.md)：项目入口
- [`SKILL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/SKILL.md)：安装 `MemPalace` 与 `Graphify` 的 AI Skill
- [`docs/PROJECT_SCOPE.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/PROJECT_SCOPE.md)：项目边界、组件关系、当前状态
- [`docs/GOVERNANCE_MODEL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/GOVERNANCE_MODEL.md)：闲聊、项目对话、产出文档的隔离与晋升模型
- [`docs/INTERFACE_CONTRACT.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/INTERFACE_CONTRACT.md)：推荐输入契约、输出契约与 Markdown 包格式
- [`docs/INSTALL_VERIFICATION.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/INSTALL_VERIFICATION.md)：真实安装与 CLI 验证结果
- [`docs/DOCUMENT_STATUS.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/DOCUMENT_STATUS.md)：正式文档与研究归档的关系
- [`docs/MAINTAINER_SKILL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/MAINTAINER_SKILL.md)：旧的维护型 Skill 说明

## 开源价值

这个项目值得开源，不是因为它重新发明了记忆或图谱，而是因为它试图把两种已经成立的能力接干净：

- `MemPalace` 的“记住与找回”
- `Graphify` 的“编译与导航”

如果这条桥接契约被定义清楚，用户就不必在记忆层和知识层之间手工搬运语料。
