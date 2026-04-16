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

这里还必须补一条硬约束：

- 自动喂数据、自动加工、自动消费，都必须比单用 `MemPalace` / `Graphify` 更好，或者至少不能打折扣
- 自动化不是目的；如果自动化后的质量、可信度或可消费性下降，这条路径就是失败的

## 一条更严格的产品链路

`MemArk` 不应该只被定义为桥接层，还应被定义为一条自动知识供应链：

1. Intake: 自动从项目活动里持续收集原始数据
2. Process: 自动把原始数据整理成可消费的项目知识单元
3. Consume: 自动把项目知识送到 AI 和管理动作里
4. Improve: 自动根据消费结果更新后续 ingest 和 promotion 优先级

如果只有前两步，没有第三步，这个产品仍然偏向“知识归档工具”，而不是“项目治理系统”。

如果这三步虽然自动了，但任一步的效果低于直接单用上游工具，那么它仍然不是合格产品。

## 当前仓库的真实状态

基于当前仓库代码和文档，现状可收敛为：

### 已经具备

- 能自动扫描 `Codex` sessions 并按项目路径筛选到 staging
- 能自动触发 `MemPalace mine --mode convos`
- 能把 palace drawers 按 `room` 或逻辑 `session` 自动打包
- 能把 package 自动晋升为 `corpus/<project>/promoted/*.md`
- 能直接从注册项目的 `project-root` 纳入正式项目文档
- 文档同步会排除研究归档、构建产物、缓存和其他派生产物，避免自动消费被噪音稀释
- 能对 promoted corpus 做本地固定字符串查询
- 能在需要时生成给上游 `Graphify` skill 的 handoff
- 能自动构建当前 corpus 的 mixed-corpus graph
- 已实现 `memark automation-run`，能把 intake、文档同步、promotion、消费产物生成串成一个单次自动 cycle
- 已实现 `service-install` 默认调度 `automation-run`，而不是只调度 `projects-run`
- 已能自动生成项目级消费产物：
  - `latest-summary.md`
  - `decisions-digest.md`
  - `risks-digest.md`
  - `ai-context.md`
  - `graphify-status.md`
- 已实现 `memark context`，把这些自动消费产物收成一个统一消费入口

### 仍然缺失

- 还没有被真实狗粮稳定证明的“持续后台 intake + process + consume”闭环
- 自动生成的消费产物目前主要是启发式摘要，还不是高质量结构化管理对象抽取
- AI runtime 侧还没有做到“启动任务时自动注入这些上下文”，当前仍需上游 skill/runtime 接手
- 没有自动把消费结果反馈回下一轮 ingest / promotion / 优先级策略
- 没有针对“AI 应该何时主动读什么”的运行时编排

## 好的消费，应该长什么样

“好消费”不是用户知道某个文件被写出来了，而是项目参与方直接受益。

同时，“好自动化”也不是系统自己跑完了，而是每一层都不弱于直接单用上游：

- 自动喂数据不能比手工直连 `MemPalace` 更容易漏上下文或引入污染
- 自动加工不能比直接读原始 session / 项目文档更失真
- 自动消费不能比直接用 `MemPalace search/wake-up` 或 `Graphify report/query` 更绕

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

- 项目内正式文档、ADR、计划文档、复盘文档应由注册项目根目录直接提供
- 同步应受忽略规则治理，不能把派生产物重新喂回系统
- 当前至少应排除 `.experiments/`、`build/`、`dist/`、`.pytest_cache/`、`*.egg-info/`、`docs/raw/`

验收标准：

- 新增或更新文档后，无需手工同步

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
- 系统默认应能自己完成 mixed-corpus graph 更新
- 若上游 skill 可用，系统可以额外支持互操作或半自动触发
- 若 graph 尚未生成，也应明确维护 pending graph updates 状态

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

1. 把 `automation-run` 在真实后台调度里跑稳，而不是只在前台和测试里可用
2. 把自动生成的 summary / decisions / risks 从启发式摘要升级到更可靠的结构化对象
3. 给 AI runtime 接上自动装配的项目上下文，而不是要求用户记得先查 `wake-up`、再查 graph、再查 promoted
4. 把消费反馈回流到后续 ranking、promotion 和优先级策略

更短地说：

- 现在的 `MemArk` 比较像自动整理系统
- 目标中的 `MemArk` 应该变成自动项目治理系统
- 并且这条自动治理主路径必须明确优于单用上游，或者至少不降低上游已有价值

这才符合“喂数据、加工数据、消费数据都不要手工”的标准。
