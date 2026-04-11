# AI Consumption Model

本文件基于 2026-04-09 在当前 `memark` 仓库上的实际运行结果，回答一个更关键的问题：

`MemArk` 把数据喂进去之后，项目里的 AI 到底应该怎么消费这些数据，才比单独用 `MemPalace` 或 `Graphify` 更有价值。

## 真实证据

当前仓库已经验证过的事实：

- `mempalace search "worktree hook"` 能直接找回这次开发过程中关于 `worktree` 治理的历史讨论
- `mempalace wake-up` 能输出当前项目的压缩历史脉络，适合新一轮对话前快速恢复上下文
- `memark palace-package --group-by session` 在当前仓库 palace 中，能把 `802` 个 drawer 重新整理成 `14` 个会话级 package
- `Graphify` 在当前仓库代码图上已经产出 `264 nodes / 509 edges / 12 communities`
- 但当前 `memark build` 走到安装版 `Graphify` 的 code-only fallback 时，会因为 `corpus/<project>` 下没有代码而失败
- 当前 `graphify-out/graph.json` 里 `document_nodes = 0`，`promoted_nodes = 0`

这意味着一件事：

当前已经验证成功的是“会话记忆整理”和“代码图消费”。

当前还没有验证成功的是“`MemArk promoted markdown -> Graphify 图谱`”这条闭环。

但现在已经补出一条更准确的桥接面：

- `memark graphify-handoff` 会把当前项目 `corpus/<project>` 的真实边界、文件规模和推荐命令整理出来
- 它明确告诉 AI 应该把哪个目录交给上游 `Graphify` skill 执行 `/graphify <path> --update`
- 这样 `MemArk` 不需要伪装成已经完成 mixed-corpus semantic build

补充一条现在已经核实的上游事实：

- `graphify.detect()` 能看到 `corpus/<project>/promoted/*.md`
- 但公开 Python 入口 `graphify.extract()` 只提代码 AST，不会直接把这些 Markdown 变成图节点
- `graphify.watch()` 对文档变化只会提示去 AI 平台里执行 `/graphify --update`

所以当前闭环卡点不是 `MemArk` 没把文件落出来，而是 `Graphify` 的 mixed-corpus 语义提取仍由上游 skill / AI 运行时主导。

## 三者怎么分工

### 1. `MemPalace` 负责找回“为什么”

适合问它的问题：

- 我们之前为什么这样定
- 某个争论点以前怎么收敛的
- `worktree`、安装、skill、ignore 这些决策以前讨论过什么
- 进入一个继续开发的 session 前，先把必要背景拉起来

当前最有价值的入口：

- `mempalace wake-up`
- `mempalace search <keyword>`

这层提供的是：

- 历史决策
- 原始讨论
- 被遗忘的上下文

它的边界也很清楚：

- 返回的是记忆和原文片段，不是当前代码结构图
- 返回的是“发生过什么”，不是“代码现在怎么连”

### 2. `Graphify` 负责回答“现在代码怎么连”

适合问它的问题：

- 当前 CLI、workspace、project registry、promotion pipeline 是怎么串起来的
- 哪些模块耦合最强
- 哪些节点是图里的 bridge
- 某个函数或模型影响哪些文件

当前最有价值的入口：

- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/graph.json`
- `graphify query` 或兼容查询入口

这层提供的是：

- 当前代码结构
- 模块关系
- 社区划分
- 可导航的图查询面

它当前的明确边界：

- 现阶段并没有证明会自动消费 `MemArk` 晋升出来的 session markdown
- 所以它现在主要回答“代码和正式项目语料如何组织”，不是“会话历史如何演化”

### 3. `MemArk` 负责把“原始会话”整理成“项目可消费的会话知识”

它当前已经做成的，不是新数据库，也不是新图谱，而是：

- 按目录筛出当前项目相关的 `Codex` 会话
- 生成可增量更新的 staging snapshot
- 驱动 `MemPalace mine --mode convos`
- 从 palace 中按逻辑 session 重新打包
- 把这些会话落成带 provenance 的 promoted markdown

这层的直接价值不是替代上游，而是补上它们之间的断层：

- `MemPalace` 有会话历史，但太原始
- `Graphify` 有结构消费能力，但当前没有稳定吃进这些会话整理物
- `MemArk` 先把会话从“原始记忆”整理成“项目级候选知识”
- `MemArk` 现在还额外提供了 `memark query`，让 AI 可以直接搜索这些项目级候选知识

## 当前推荐的消费顺序

项目 AI 在实际开发中，当前最靠谱的消费顺序是：

1. 先用 `MemPalace wake-up` 恢复项目背景
2. 如果需要追某个历史决策，再用 `MemPalace search`
3. 如果要理解当前实现结构，转去读 `Graphify` 的 report / graph
4. 如果需要把一整段历史会话作为项目材料审阅，先用 `memark query` 定位，再读对应 promoted markdown
5. 如果需要把这些晋升材料继续交给 `Graphify` 做 mixed-corpus 语义编译，先运行 `memark graphify-handoff`，再把生成的 handoff 交给上游 `Graphify` skill

更短地说：

- `MemPalace` 管历史找回
- `Graphify` 管当前结构
- `MemArk` 管会话整理、晋升，以及当前阶段的本地项目语料搜索
- `MemArk` 还负责把已经整理好的项目语料，准确地 hand off 给上游 `Graphify` skill

## 为什么不是单独用一个

### 只用 `MemPalace` 不够

因为它能回答“以前说过什么”，但不擅长给出当前代码结构图。

### 只用 `Graphify` 不够

因为它能回答“代码现在怎么连”，但不会自动理解长期对话历史和决策过程。

### `MemArk` 的 1+1>2 点在哪里

不是“强行把两个上游绑在一起”。

真正的加值点是：

- 把项目相关会话从全局 AI 会话堆里筛出来
- 把这些会话变成可治理、可晋升、可审阅的项目材料
- 让项目 AI 不必每次重新翻整段 session 才知道之前讨论过什么

这已经成立。

并且现在多了一条已落地能力：

- 在 `Graphify` 统一入图还没打通前，项目 AI 已经可以通过 `memark query` 直接消费晋升后的项目语料

但下面这条还没有成立：

- 把这些 promoted session 文档稳定编进 `Graphify` 图里，并让 AI 从同一查询面同时消费代码结构和会话知识

## 当前不能声称已经做到

- 不能声称 `Graphify` 已稳定消费 `corpus/memark/promoted/*.md`
- 不能声称 `memark build` 已对会话语料完成 mixed-corpus 编译
- 不能声称 AI 现在只靠 Graphify 一个入口就能同时消费代码图和项目会话知识

## 下一步真正值得做的能力

如果继续往前推，最有价值的不是再增加 ingest，而是解决消费闭环：

- 给 promoted session package 增加更稳定的标题/摘要治理
- 明确 AI 在什么时机优先读 `wake-up`、什么时机优先读 graph
- 验证或补出一条真正可用的 `promoted markdown -> Graphify 可消费层` 路径
- 如果上游暂时没有这条能力，就在 `MemArk` 层先提供独立的 session-knowledge 消费入口，而不是假装闭环已成
