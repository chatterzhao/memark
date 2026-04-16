# Codex Session Ingest Design

本文件定义 `MemArk` 对 `Codex` 会话的正确处理方式。

目标不是“猜测上游应该怎么工作”，而是把已经实测的事实固化成产品设计。

## 已验证事实

### 1. `history.jsonl` 不是项目主输入

实测可确认：

- `~/.codex/history.jsonl` 是全局扁平索引
- 它包含 `session_id`、`ts`、`text`
- 它不包含目录级 `cwd`

因此：

- 它可以作为全局检索或审计辅助输入
- 不能作为 `MemArk` 的默认项目记忆来源

### 2. 正确主输入是 `sessions/**/*.jsonl`

实测可确认：

- `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` 才是原始 session 文件
- 每个 session 文件首行存在 `session_meta`
- `session_meta.payload.cwd` 可用于项目匹配

因此：

- `MemArk` 必须扫描 `~/.codex/sessions/**/*.jsonl`
- 必须先读 `session_meta` 再决定归属

### 3. `MemPalace` 不会自动按项目拆分混合输入

实测可确认：

- 把两个不同项目的 session 文件放入同一个输入目录
- 再执行 `mempalace mine <dir> --mode convos`
- 结果会形成一个 wing，而不是自动拆分成两个项目

因此：

- 项目隔离必须发生在 `MemPalace` ingest 之前
- 这层责任属于 `MemArk`

### 4. `resume` 后会继续追加到原 session 文件

实测可确认：

- `Codex resume` 之后，原 `rollout-*.jsonl` 会继续增长
- 同一路径文件的 `mtime` 和内容会继续变化

因此：

- `MemArk` 必须先把“同一路径 session 增长后的增量同步”做对
- 当前主增量入口应围绕 `source_path + size + mtime_ns + sha256`

### 5. `MemPalace 3.0.0` 的 `convos` ingest 不会重吃已存在 `source_file`

实测可确认：

- 同一路径会话第一次 `mine --mode convos` 之后
- 如果只是对原 JSONL 继续追加内容
- 再次执行 `mine --mode convos`
- `MemPalace` 会直接把该文件视为 `already filed`
- 它不会像普通项目 `mine` 那样依据 `mtime` 重新 ingest

因此：

- `MemArk` 不能把“更新后的同一路径 session”继续写回同一个 staging 路径
- 必须把每次变化写成新的 staging snapshot 路径
- 后续 package 层再按逻辑 session 取最新 snapshot

## 设计目标

`MemArk` 对 `Codex` 会话 intake 的设计目标如下：

1. 识别当前机器上的全部 `Codex` session 文件
2. 把 session 稳定地映射到具体项目
3. 为每个项目维护独立 staging
4. 把 staging 目录作为 `MemPalace convo mine` 的唯一输入
5. 让同一路径 resume 增量能稳定进入后续 mine
6. 为后续晋升到 `Graphify` 保留 provenance

## 处理流水线

推荐主路径：

1. 扫描 session 文件
2. 读取 `session_meta`
3. 做项目匹配
4. 更新项目 staging
5. 执行目录级 `mempalace mine --mode convos`
6. 从 palace 中抽取候选内容
7. 晋升到 `Graphify-ready` corpus

## 一、项目匹配

### 输入

默认扫描路径：

- `~/.codex/sessions/**/*.jsonl`

每个 session 文件至少提取：

- `session_file`
- `session_id`
- `cwd`
- `timestamp`

### 匹配规则

目录匹配不应只做简单字符串相等，而应支持：

- 被跟踪目录精确匹配
- 子目录映射回被跟踪目录
- 附加目录路径命中

推荐规则顺序：

1. 先看 `cwd` 是否等于被跟踪目录
2. 再看 `cwd` 是否位于被跟踪目录之下
3. 再看 `cwd` 是否命中目录工作单元定义的 `extra_paths`
4. 未命中则视为未归属

`git` 不是主模型。

- 非 git 目录也必须可以被整理
- `worktree` 当前只作为“创建新目录后复制配置”的自动化触发器
- 如果后续接 `git worktree add`，hook 只需要调用 `memark worktree-attach`

## 二、目录 staging

### 目标

每个目录工作单元都需要一个只包含该目录 session 的 staging 目录。

例如：

```text
.memark/
  staging/
    memark/
      sessions/
        2026/04/08/rollout-a--1775741877453319499-03f00be8b810.jsonl
```

### 更新策略

可选方式：

- 复制文件
- 硬链接
- 符号链接

当前默认更稳妥的是：

- 复制为 transcript Markdown snapshot 到 staging

原因：

- 跨平台最稳定
- 后续做内容指纹最直接
- 不依赖 `MemPalace` 对软链接行为的额外假设
- 可以把每次会话更新落成新的不可变 snapshot
- 可以避免原始 JSONL 过大时直接撞上 `MemPalace convos` 的输入大小限制

当前 staged 文件至少保留：

- `Source Path`
- `Workspace Path`
- `Session ID`
- `Session Timestamp`
- 用户 / assistant transcript

## 三、增量账本

### 为什么需要

因为 `MemPalace` 的 convo 去重不是内容级，所以 `MemArk` 需要自己的 ledger。

### 推荐记录字段

每个 staged session 至少记录：

- `source_path`
- `staged_path`
- `staged_relative_path`
- `size`
- `mtime_ns`
- `sha256`
- `session_id`
- `cwd`
- `last_mined_at`

### 判断逻辑

默认判断：

- `source_path` 不存在记录：新增
- `size` 或 `mtime_ns` 变化：重新计算 hash
- hash 未变化：不生成新的 staging snapshot
- hash 变化：写入新的 staging snapshot，并标记需要重新 mine

当前真实优先级：

- 先保证“同一路径 session 追加”可持续进入项目 staging
- 再保证这类更新不会被 `MemPalace convos` 因同一 `source_file` 而跳过
- 再由单次 cycle 或外部定时器决定何时触发 `mempalace mine`
- “同内容异路径”仍可作为后续 hardening，但不是目前已验证主链需求

## 四、MemPalace ingest

### 输入面

`MemPalace` 看到的只能是项目 staging 目录，而不是用户的全部 `Codex sessions` 根目录。

推荐命令形态：

```bash
mempalace --palace <project-palace> mine <project-staging-dir> --mode convos
```

这里的 `<project-staging-dir>` 应理解为：

- 项目隔离后的输入目录
- 里面放的是 `MemArk` 管理的 session snapshot
- 不是直接把用户原始 `~/.codex/sessions` 原样交给 `MemPalace`

### 项目粒度

推荐一项目一 palace，或一项目一独立 wing 的受控 palace。

当前更稳妥的默认设计是：

- 一项目一 palace

原因：

- 锁争用更容易控制
- 重建和清理更简单
- 避免跨项目污染

## 五、从 palace 到晋升语料

### 当前已验证可读表面

对 bridge 层最实用的表面是：

- Chroma metadata
- `chroma:document`

常见元数据：

- `wing`
- `room`
- `source_file`
- `filed_at`
- `ingest_mode`
- `extract_mode`

### 当前推荐晋升单位

当前不应假装已经验证到稳定的 `closet` 导出 API。

已验证的现实切口是：

- `project-scoped convo chunks`
- `metadata + text`

因此当前推荐晋升单位是：

- 项目边界下的候选主题包
- 由 `MemArk` 在桥接层上整理，而不是完全依赖 `MemPalace` 自带导出

## 六、调度模型

### 当前推荐

`CLI-first + single-cycle polling`

例如：

- 每 2 分钟扫描一次 session 文件
- 每次执行一轮 `projects-run`
- 由系统定时器而不是 `MemArk` 常驻 daemon 负责重复调用
- 更新项目 staging
- 如果检测到新增内容，再执行一次目录级 `mine`

### 为什么不是插件常驻

当前没有验证到：

- `Codex` 提供稳定的会话变更回调
- `MemPalace` 提供稳定的目录级增量查询接口

因此轮询更符合当前事实。

## 七、失败与恢复

### 需要显式支持的运维动作

- 清空项目 staging 后全量重建
- 清空项目 palace 后重新 mine
- 只重跑某个项目
- 只重跑某一批 session

### 需要记录的错误

- session 文件缺少 `session_meta`
- `cwd` 缺失
- 文件截断或 JSONL 损坏
- `MemPalace` 数据库锁冲突
- staging 写入失败

## 八、对 `MemArk` 功能边界的直接影响

这份设计意味着 `MemArk` 应新增或明确以下能力：

- `codex sessions` 扫描器
- 项目匹配器
- staging 管理器
- 内容级 ledger
- 目录级 `mempalace mine` 编排
- palace 提取适配器
- 晋升到 `Graphify-ready` corpus 的治理器

同时也意味着当前不应声称：

- `MemPalace` 已替我们解决项目隔离
- `MemArk` 只要读 `history.jsonl` 就够了
- `MemArk` 已有稳定的时间戳增量接口

## 九、worktree 配置复制

当前 `git` 不属于主模型，只在一个地方参与：

- 发现新建 `worktree`
- 调用 `memark worktree-attach`

当前已实现：

- `memark worktree-attach --source-dir <dir> --target-dir <dir>`
- `memark worktree-hook-install --source-dir <dir>`

当前复制语义是：

- 复制 `.codex`、`.claude`、`.mempalace`、`AGENTS.md` 这类目录局部配置
- 复制 `.memark` 时只复制：
  - `config.json`
  - `projects.toml`
- 不复制 `.memark/state`、`.memark/staging`、`.memark/palaces`

这样做的原因是：

- 新 worktree 需要本地接入点
- 但不应把旧目录的运行状态、已挖掘 palace、staging snapshot 一起污染到新目录
