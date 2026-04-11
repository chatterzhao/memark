# Automation Consumption Requirements

本文件从一个更直接的产品标准出发定义 `MemArk` 下一阶段需求：

- 数据必须自动进入系统
- 数据必须自动被加工成项目知识
- 数据必须自动被 AI 或人类管理者消费
- 判断标准不是“成功存档”，而是“后续项目管理和项目执行明显变好”

这里的“消费变好”指的是：

- AI 不再反复问已经讨论过的问题
- AI 能主动带着历史决策、失败尝试和当前结构继续工作
- 人类管理者能低成本看到项目风险、最近变化、待决策事项和知识沉淀
- 整个链路不依赖手工导出、手工筛选、手工再喂给另一个工具

## 一条更严格的产品链路

`MemArk` 不应该只被定义为桥接层，还应被定义为一条自动知识供应链：

1. Intake: 自动从项目活动里持续收集原始数据
2. Process: 自动把原始数据整理成可消费的项目知识单元
3. Consume: 自动把项目知识送到 AI 和管理动作里
4. Improve: 自动根据消费结果更新后续 ingest 和 promotion 优先级

如果只有前两步，没有第三步，这个产品仍然偏向“知识归档工具”，而不是“项目治理系统”。

## 当前仓库的真实状态

基于当前仓库代码和文档，现状可收敛为：

### 已经具备

- 能自动扫描 `Codex` sessions 并按项目路径筛选到 staging
- 能自动触发 `MemPalace mine --mode convos`
- 能把 palace drawers 按 `room` 或逻辑 `session` 自动打包
- 能把 package 自动晋升为 `corpus/<project>/promoted/*.md`
- 能把项目文档纳入 `documents/`
- 能对 promoted corpus 做本地固定字符串查询
- 能生成给上游 `Graphify` skill 的 handoff

### 仍然缺失

- 没有“持续后台 intake”能力，当前仍依赖人工或外部 cron/hook 触发 `projects-run`
- 没有基于增量事件的 promotion 调度，当前 palace package/promote 仍是显式命令
- 没有自动消费闭环，当前主要靠人手动执行 `query`、读 markdown、再调用 Graphify
- 没有自动生成面向管理的产物，例如每日项目摘要、风险列表、决策 backlog、异常回顾
- 没有自动把消费结果反馈回下一轮 ingest / promotion / 优先级策略
- 没有针对“AI 应该何时主动读什么”的运行时编排

## 好的消费，应该长什么样

“好消费”不是用户知道某个文件被写出来了，而是项目参与方直接受益。

### 对 AI

AI 在新一轮工作开始时应该自动拿到：

- 项目 wake-up 摘要
- 最近新增的重要 session knowledge
- 当前代码结构入口
- 未决策事项、已知风险、近期失败尝试

AI 在执行任务时应该自动触发：

- 与当前工作路径最相关的 promoted knowledge 检索
- 与当前模块最相关的代码结构检索
- 与当前问题最相关的历史决策检索

AI 在任务结束时应该自动沉淀：

- 本轮新增决策
- 本轮新增风险
- 本轮值得晋升的 session 片段
- 对已有知识的更新或失效标记

### 对人类管理者

管理者不应该手工翻 palace、graph、session markdown。

管理者应该被自动提供：

- 最近 24 小时/7 天项目变化摘要
- 当前风险和阻塞项
- 新增决策及其证据来源
- 哪些模块变化最频繁、讨论最多、返工最多
- 哪些知识已经晋升，哪些还只是原始对话

## 自动喂数据需求

### F1. 项目自动发现

- 当 `MemArk` 发现新的项目目录、worktree 或新注册项目后，应自动建立 intake 配置
- 不应要求用户每个项目都手工跑完整接入命令

验收标准：

- 新项目注册后，可在无额外手工步骤下进入周期运行

### F2. 会话自动同步

- `Codex` / `Claude Code` / 其他支持的会话源应按项目路径自动增量同步
- 同步必须基于 ledger 或等价增量机制，避免重复处理

验收标准：

- 新 session 出现后，系统能在约定延迟内进入 staging

### F3. 文档自动同步

- 项目内正式文档、ADR、计划文档、复盘文档应自动进入 `documents/`
- 同步应受忽略规则治理，不能把派生产物重新喂回系统

验收标准：

- 新增或更新文档后，无需手工 `add-documents`

### F4. Intake 调度自动化

- `projects-run` 只是底层执行器，不应是最终用户主入口
- 系统需要提供守护进程、定时任务模板或 hook 安装能力

验收标准：

- 在用户安装完成后，系统默认存在持续 intake 方案

## 自动加工需求

### P1. 增量 promotion

- 当 palace 中出现新 drawers 或已有逻辑 session 发生变化时，应自动触发 package + promote
- 不应要求用户手工执行 `palace-package` 或 `palace-run`

验收标准：

- 新会话进入 palace 后，可在约定延迟内生成或更新 promoted markdown

### P2. Promotion 质量治理

- session package 必须自动生成稳定标题、摘要、标签、证据链
- 需要区分高价值知识和低价值噪音，不能所有对话平权晋升

验收标准：

- promoted knowledge 对 AI 可读，而不是仅仅“格式合法”

### P3. 知识单元类型化

- promotion 结果不应只有 room/session markdown
- 还应抽出结构化对象，例如：
  - 决策
  - 风险
  - 待办
  - 假设
  - 失败尝试
  - 关键上下文

验收标准：

- 同一轮对话里，系统能抽出至少一部分结构化管理对象

### P4. 失效与去重

- 新知识进入后，应能识别与旧知识的覆盖、冲突、失效和重复
- 不能让 promoted corpus 只增不减，最终变成噪音堆积

验收标准：

- 知识单元具备状态，例如 active、superseded、duplicate、stale

## 自动消费需求

### C1. AI 启动上下文自动装配

- 当 AI 在某项目内启动新任务时，系统应自动准备项目上下文包
- 这个上下文包应同时包含：
  - wake-up
  - 最近 promoted knowledge
  - relevant graph/report entrypoints
  - 当前项目 open risks / open decisions

验收标准：

- AI 不需要人工提示“先去搜一下历史”

### C2. AI 任务中自动检索

- AI 在读写某目录、某模块、某主题时，应自动查找相关 promoted knowledge 和历史决策
- 检索应由任务上下文驱动，而不是固定全局搜索

验收标准：

- AI 在执行变更时能引用相关历史，而不是只依赖当前对话窗口

### C3. 管理视图自动生成

- 系统应自动产出项目级 summary artifacts
- 至少包括：
  - latest summary
  - decisions digest
  - risks digest
  - recent change narrative

验收标准：

- 管理者不必进入底层 corpus 才能知道项目状态

### C4. Graphify 消费自动衔接

- 只生成 handoff 还不够
- 若上游 skill 可用，系统应能自动触发或半自动触发 mixed-corpus 更新
- 若上游 skill 当前不可自动调用，也应明确维护 pending graph updates 状态

验收标准：

- promoted knowledge 是否已经进入图谱，对系统来说是可观测状态，而不是靠人记忆

### C5. 消费反馈自动回流

- AI 或人类消费过哪些知识、哪些结果有效、哪些结果无用，应反哺后续 ranking 和 promotion

验收标准：

- 系统能逐步提升“哪些内容值得晋升和优先展示”的准确性

## 优先级判断

如果只按“让项目变好”排序，优先级应是：

### P0

- 自动 intake 调度
- 自动增量 promotion
- AI 启动上下文自动装配
- 项目级 summary / risks / decisions 自动生成

这四项缺任意一项，当前都还称不上“自动消费闭环”。

### P1

- 管理对象结构化抽取
- Graphify 消费状态可观测
- 任务中自动检索
- 知识失效与去重

### P2

- 消费反馈学习
- 多会话源统一 intake
- 更细粒度的角色化消费视图

## 对当前仓库最直接的需求结论

基于现状，下一阶段不应继续把重点放在“再加一个 ingest 命令”，而应转向四个核心能力：

1. 把 `projects-run` 变成默认自动运行的 intake service，而不是手工命令
2. 把 `palace-run` 变成增量自动 promotion pipeline，而不是人工整理工具
3. 新增项目级自动消费产物，而不是只提供 `query` 和 `promoted/*.md`
4. 给 AI 提供自动装配的项目上下文，而不是要求用户记得先查 `wake-up`、再查 graph、再查 promoted

更短地说：

- 现在的 `MemArk` 比较像自动整理系统
- 目标中的 `MemArk` 应该变成自动项目治理系统

这才符合“喂数据、加工数据、消费数据都不要手工”的标准。
