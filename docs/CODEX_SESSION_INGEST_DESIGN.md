# Codex Session Ingest Design

本文件定义 `MemArk` 对 `Codex` 会话的正确处理方式。

目标不是“猜测上游应该怎么工作”，而是把已经实测的事实固化成产品设计。

## 已验证事实

### 1. `history.jsonl` 不是项目主输入

实测可确认：

- `~/.codex/history.jsonl` 是全局扁平索引
- 它包含 `session_id`、`ts`、`text`
- 它不包含项目级 `cwd`

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

### 4. `MemPalace` convo 去重不是内容级去重

实测可确认：

- 同一路径重跑会被跳过
- 同内容换路径重喂会再次 ingest

因此：

- `MemArk` 必须自己拥有内容级增量治理能力

## 设计目标

`MemArk` 对 `Codex` 会话 intake 的设计目标如下：

1. 识别当前机器上的全部 `Codex` session 文件
2. 把 session 稳定地映射到具体项目
3. 为每个项目维护独立 staging
4. 把 staging 目录作为 `MemPalace convo mine` 的唯一输入
5. 避免重复 ingest
6. 为后续晋升到 `Graphify` 保留 provenance

## 处理流水线

推荐主路径：

1. 扫描 session 文件
2. 读取 `session_meta`
3. 做项目匹配
4. 更新项目 staging
5. 执行项目级 `mempalace mine --mode convos`
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

项目匹配不应只做简单字符串相等，而应支持：

- 项目根目录精确匹配
- worktree 路径映射回主项目
- 子目录映射回项目根

推荐规则顺序：

1. 先看 `cwd` 是否等于项目根
2. 再看 `cwd` 是否位于项目根之下
3. 再看 `cwd` 是否命中项目定义的 `cwd_prefixes`
4. 未命中则视为未归属

## 二、项目 staging

### 目标

每个项目都需要一个只包含本项目 session 的 staging 目录。

例如：

```text
.memark/
  staging/
    memark/
      sessions/
        rollout-2026-04-08T02-44-36-....jsonl
```

### 更新策略

可选方式：

- 复制文件
- 硬链接
- 符号链接

当前默认更稳妥的是：

- 复制到 staging

原因：

- 跨平台最稳定
- 后续做内容指纹最直接
- 不依赖 `MemPalace` 对软链接行为的额外假设

## 三、增量账本

### 为什么需要

因为 `MemPalace` 的 convo 去重不是内容级，所以 `MemArk` 需要自己的 ledger。

### 推荐记录字段

每个 staged session 至少记录：

- `source_path`
- `staged_path`
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
- hash 未变化：不重写 staging
- hash 变化：更新 staging，并标记需要重新 mine

## 四、MemPalace ingest

### 输入面

`MemPalace` 看到的只能是项目 staging 目录，而不是用户的全部 `Codex sessions` 根目录。

推荐命令形态：

```bash
mempalace --palace <project-palace> mine <project-staging-dir> --mode convos
```

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

`CLI-first + polling`

例如：

- 每 2 分钟扫描一次 session 文件
- 更新项目 staging
- 如果检测到新增内容，再执行一次项目级 `mine`

### 为什么不是插件常驻

当前没有验证到：

- `Codex` 提供稳定的会话变更回调
- `MemPalace` 提供稳定的项目级增量查询接口

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
- 项目级 `mempalace mine` 编排
- palace 提取适配器
- 晋升到 `Graphify-ready` corpus 的治理器

同时也意味着当前不应声称：

- `MemPalace` 已替我们解决项目隔离
- `MemArk` 只要读 `history.jsonl` 就够了
- `MemArk` 已有稳定的时间戳增量接口
