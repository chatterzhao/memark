# Project Scope

本文件回答三个问题：

1. `MemArk` 要解决什么问题
2. `MemArk` 与 `MemPalace`、`LLM Wiki`、`Graphify` 是什么关系
3. 闲聊、项目对话、产出文档应该如何隔离与治理
4. 当前仓库已经提供什么，还没有提供什么

## 问题定义

MemArk 要解决的问题很具体：

`MemPalace` 很擅长记录和记忆，也能高精度找回内容；但这些内容天然更适合保存、检索和溯源，不够适合人直接阅读和理解。

因此需要一个知识编译工具，把 `MemPalace` 中保存得很好的内容，进一步转成更适合人浏览、理解和导航的知识形态。

MemArk 关心的正是这条链路：

1. 用户与 AI 进行长期对话
2. `MemPalace` 负责记录、记忆和找回
3. `MemArk` 提取需要处理的内容
4. `MemArk` 将内容输入 `Graphify`
5. `Graphify` 将其编译为图谱、报告、Wiki 或 Obsidian Vault

所以，MemArk 的重点不是“再造一个记忆系统”，而是把“记忆内容”晋升成“项目知识输入”，再交给 `Graphify` 编译成知识视图。

## 组件关系

### MemPalace

`MemPalace` 代表记忆层。它负责：

- 保存原始对话
- 也支持 ingest 项目文件
- 提供记忆检索能力
- 提供 wake-up context
- 支持通过 hooks / 自动 mine 持续采集
- 支持溯源到原始记录
- 通过 `wing -> hall -> room -> closet -> drawer` 组织内容

其中：

- `wing` 是人或项目边界
- `hall` 是记忆类型
- `room` 是具体主题
- `closet` 是指向原始内容的摘要
- `drawer` 是原始逐字内容

### LLM Wiki

`LLM Wiki` 代表一类“把材料整理为知识 Wiki”的思路。它强调：

- 原始材料先经过整理
- 再编译为结构化知识库
- 形成适合长期浏览与复用的知识层

### Graphify

在当前正式口径中，`Graphify` 不应只被描述为“wiki 工具”。

更准确地说，它是一个把目录语料编译成知识图谱、报告、Wiki 和 Obsidian Vault 的知识编译层，也是 `LLM Wiki` 这类思路的一种具体工具形态。

它还提供围绕 `graph.json` 的查询、MCP 和平台集成能力，因此不只是静态导出器。

它更适合处理：

- 项目代码
- 项目文档
- 已沉淀的研究资料
- 经整理后的项目对话增量

### MemArk

`MemArk` 自己不应该承担以下职责：

- 直接替代记忆系统
- 直接替代知识编译系统
- 伪装成已经具备完整实现的安装包

`MemArk` 的合理职责是：

- 从 `MemPalace` 获取待处理内容
- 把内容整理为 `Graphify` 最适合处理的项目语料
- 定义这条处理管线的入口、格式和工作流

## 治理原则

面对“闲聊、项目助手对话、对话产出文档”这三类材料时，推荐采用如下原则：

- 闲聊默认留在 `MemPalace`，不默认进入 `Graphify`
- 项目助手对话进入对应 `project wing`
- 只有具备项目知识价值的增量内容，才由 `MemArk` 晋升给 `Graphify`
- 已落盘的项目文档是 `Graphify` 的一等输入

在当前推荐的默认组合里，还应进一步明确：

- `Graphify` 直接扫描项目目录
- `MemPalace` 默认优先 ingest AI 会话导出，而不是重复全量扫描同一项目目录
- 对 `Codex` 来说，默认应优先读取 `~/.codex/sessions/**/*.jsonl`，因为 session 文件首行 `session_meta` 带 `cwd`
- `~/.codex/history.jsonl` 只适合作为全局索引，不适合作为项目级主入口
- 只有当用户确实需要在 palace 中统一搜索项目文件与会话时，才额外让 `MemPalace` 也 ingest 项目路径

这样做不是否认 `MemPalace` 的项目能力，而是为了减少与 `Graphify` 的默认重叠。

在 `MemPalace` 的宫殿结构中，`MemArk` 当前选择的默认抽取边界不是整个 `wing`，也不是去碰底层 ANN 文件，而是：

- 以 `project wing` 为边界
- 以 `room` 为主题单位
- 以 Chroma 中的 `drawer metadata + chroma:document` 为主抽取面
- 必要时再在桥接层上做主题级整理与晋升

也就是当前桥接层的推荐默认策略：

`project wing -> room -> drawer metadata + text -> promoted markdown`

更完整的隔离与晋升规则见 [`docs/GOVERNANCE_MODEL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/GOVERNANCE_MODEL.md)。

## 当前仓库状态

当前仓库是“文档 + 最小可运行 CLI 实现”的仓库。它已经提供：

- 正式 README
- 项目治理模型
- 安装 `MemPalace` 与 `Graphify` 的 AI Skill
- 真实安装验证记录
- 一个 Python CLI-first 的最小实现
- 文档分层说明
- 原始研究稿与最终评审记录

当前仓库尚未提供：

- 稳定的 `MemPalace -> MemArk` 增量抽取实现
- 后台监控或守护进程

因此，任何面向用户的正式表述都不应把本仓库描述为“已经完成所有自动抽取能力的产品仓库”。

## 文档策略

为了避免再次出现口径混杂，当前采用如下分工：

- `README.md`：只负责项目入口与仓库导航
- `PROJECT_SCOPE.md`：负责定义项目边界与组件关系
- `GOVERNANCE_MODEL.md`：负责定义三类材料的隔离、晋升与输入治理
- `INTERFACE_CONTRACT.md`：负责定义 `MemPalace -> MemArk -> Graphify` 的数据与目录契约
- `CODEX_SESSION_INGEST_DESIGN.md`：负责定义 `Codex sessions -> project staging -> MemPalace` 的 intake 设计
- `SKILL.md`：负责指导 AI 助手安装与验证 `MemPalace`、`Graphify`
- `INSTALL_VERIFICATION.md`：负责记录已经真实执行过的安装与验证结果
- `IMPLEMENTATION_PLAN.md`：负责定义当前 CLI 的实现边界与下一阶段路线
- `ACCEPTANCE_CHECKLIST.md`：负责定义当前版本的验收标准
- `PRODUCT_REQUIREMENTS.md`：负责定义基于上游能力面收敛出的具体产品需求
- `FEATURE_LIST.md`：负责定义应实现与暂不应声称实现的功能列表
- `DOCUMENT_STATUS.md`：负责定义正式文档与研究归档的关系

## 后续应补的文档

当前已经补充：

- `docs/CODEX_SESSION_INGEST_DESIGN.md`

如果后续继续推进，建议再新增以下文档，而不是继续把内容堆进 README：

- `docs/DEPENDENCY_CONTRACT.md`
- `docs/OPERATIONS.md`
