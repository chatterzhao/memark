# Implementation Plan

本文件记录当前已落地的实现边界，以及下一阶段该如何继续推进。

## 当前实现范围

当前仓库已经有一个真实可运行的 Python CLI 包：

- 包名：`memark`
- 入口：`python3 -m memark`
- console script：`memark`

当前命令面：

1. `memark init`
2. `memark validate`
3. `memark promote`
4. `memark add-documents`
5. `memark build`
6. `memark run`
7. `memark codex-sync`
8. `memark mempalace-mine`
9. `memark palace-export`
10. `memark palace-package`
11. `memark palace-run`
12. `memark status`

## 为什么第一版这样切

当前没有核对到 `MemPalace` 官方公开的“按时间戳取增量”接口。

同时，这次又多验证到了三件关键事实：

- `Codex` 的项目主输入应是 `~/.codex/sessions/**/*.jsonl`
- 项目归属要靠 `session_meta.payload.cwd`
- `MemPalace` convo ingest 不会替我们自动拆项目

因此当前实现不能把下面这些能力写成已完成：

- 直接查询某个时间戳后的更新
- 直接读取 live palace 并承诺长期兼容
- 直接依赖不存在的 `mempalace list-rooms --since`
- 直接把 `history.jsonl` 当项目主输入

第一版采用的真实边界是：

1. 外部抽取器、AI 助手或人工步骤先产出 room package JSON
2. `MemArk` 负责校验这些 package
3. `MemArk` 负责把 package 稳定晋升为 corpus Markdown
4. `MemArk` 负责把正式文档一起纳入 corpus
5. `MemArk` 负责触发 `Graphify`

这一段现在已经有了第一版正式能力：

1. `memark codex-sync`
2. `session_meta.payload.cwd` 项目匹配
3. 项目级 staging
4. 项目级 session ledger
5. `memark mempalace-mine`
6. `memark palace-export`
7. `memark palace-package`
8. `memark palace-run`

## 当前工作区布局

```text
workspace/
  .memark/
    config.json
    archive/
    state/
      <project>-ledger.json
      <project>-codex-sessions.json
    staging/
      <project>/sessions/
    palaces/
      <project>/
  inbox/
    promoted/
    documents/
  corpus/
    <project>/
      promoted/
      documents/
      imports/
```

说明：

- `inbox/promoted/`：外部抽取器投递 room package JSON 的位置
- `inbox/documents/`：待纳入 corpus 的正式文档
- `promoted/`：由 `MemArk` 生成的 Graphify-ready Markdown
- `documents/`：已落盘项目文档
- `imports/`：预留给后续其他输入源
- `<project>-ledger.json`：记录每个 room 的内容指纹，避免重复写入
- `<project>-codex-sessions.json`：记录每个同步过的 `Codex` session 文件指纹
- `staging/<project>/sessions/`：项目隔离后的会话输入目录
- `palaces/<project>/`：项目隔离后的 `MemPalace` 宫殿目录

## 当前实现原则

- CLI first
- Python stdlib first
- 不直接耦合 `MemPalace` 内部数据库
- 不伪造未验证的上游命令
- 输出必须直接可给 `Graphify` 消费
- 重复导入应可幂等
- 状态输出应支持脚本化消费

## 下一阶段建议

### Phase 2: Codex session intake

状态：已完成第一版。

建议形式：

- `memark codex-sync`

前提：

- 只能基于 `sessions/**/*.jsonl`
- 不能退回到 `history.jsonl` 作为默认主路径

### Phase 3: 项目级 MemPalace 编排

状态：已完成第一版主链和基础运维命令。

已完成：

- 在项目 staging 上执行 `mempalace mine --mode convos`
- 支持 `--dry-run`
- 支持项目级 `palace_dir` / `staging_dir` / `mempalace_bin` 覆盖
- `memark palace-status`
- `memark palace-clean`
- `memark palace-rebuild`
- `memark palace-retry`
- 对明确的 SQLite 锁冲突执行自动重试和指数 backoff

注意：

- 应把 palace 当并发存储看待
- 要预期数据库锁冲突和重试

### Phase 4: Palace 读取适配器

状态：已完成第一版只读适配器和候选 package 生成。

已完成：

- `memark palace-export`
- 读取 `document + metadata`
- 优先走 Chroma collection 读取
- 无 `chromadb` 时回退 SQLite 只读提取
- `memark palace-package`
- 按 `(wing, room)` 分组生成确定性的 room package JSON
- 可选直接写入 `inbox/promoted/`
- `memark palace-run`
- 可把 package -> promote -> 可选 build 串成一条命令

注意：

- 这是 best-effort adapter，不是官方稳定 API 契约
- 当前生成的是保守候选 package，不等价于“自动完成知识治理”

### Phase 5: 自动化编译

目标：

- 在 `promote` 之后按策略触发 `build`
- 增加批量目录消费和更完整的归档策略

注意：

- 仍不建议在主产品路径里直接做后台守护进程
- 先把可重入、可脚本化的 CLI 做稳

### Phase 6: 平台集成

目标：

- 为 Claude Code / Codex / Cloud Code 一类环境补充调用说明
- 但不把安装 skill 和运行期桥接器混成同一层

## 当前不足

- 还没有 `imports/` 的实际处理命令
- 还没有对 `Graphify` 输出结果做二次验证
- `Graphify` 的直接构建 CLI 契约在不同版本/入口之间并不稳定
- 还没有 Windows CI
- 还没有自写后台守护进程；当前主路径是通过 `memark service-install` 安装用户级 `launchd` 调度，其他平台仍需外部定时器
- 还没有稳定公开的 `MemPalace` 增量读取契约，当前项目级增量仍以 `Codex session` 文件变化和 `pending_mine` 状态为主
