# Interface Contract

本文件只定义一件事：

`MemArk` 作为桥接层，应该从哪里取输入，怎样落成项目 corpus，再交给 `Graphify`。

这里要明确区分两层契约：

- 当前已经实现的最小契约：`room package JSON -> corpus`
- 当前已经验证、但尚未完整实现的上游现实契约：`Codex session files -> project staging -> MemPalace convos ingest -> metadata + text`

本文件定义的是这两层之间的关系，而不是假装 `MemPalace` 已经提供稳定的自动增量导出 API。

还要明确一点：

- 前半段契约是“怎么吃数据”
- 后半段契约是“项目 AI 怎么把结果读出来”

## 目标

目标不是把 `MemPalace` 全量导出。

目标是把 `MemPalace` 中已经具备项目知识价值的内容，整理成 `Graphify` 最适合处理的项目语料。

默认主路径：

1. 扫描 `~/.codex/sessions/**/*.jsonl`
2. 按 `session_meta.payload.cwd` 匹配项目
3. 写入项目级 staging snapshot
4. 对 staging 执行 `MemPalace` 的 `mine --mode convos`
5. 从 `metadata + chroma:document` 整理候选内容
6. 落成稳定 Markdown 文件
7. 交给 `Graphify` 对项目语料目录做编译

默认消费路径：

1. 需要历史上下文时，优先读 `MemPalace`
2. 需要项目级沉淀知识时，优先读 `promoted/*.md`
3. 需要结构化导航和代码影响面时，优先读 `Graphify` 结果

## 已实现输入契约

当前实现中的默认入口是：

- `workspace/inbox/promoted/*.json`
- `memark validate <file>`
- `memark promote --workspace <workspace>`
- `memark run --workspace <workspace>`

这层契约的作用是：

- 先让 `MemArk` 具备一个稳定可测的最小闭环
- 不依赖尚未固化的 `MemPalace` 读取接口

推荐字段如下：

- `wing_id`
- `wing_kind`
- `hall_id`
- `room_id`
- `room_title`
- `room_summary`
- `closets`
- `drawer_refs`
- `participants`
- `related_entities`
- `source_timestamps`
- `updated_at`

### 字段说明

`wing_id`

- 项目边界标识
- 推荐形如 `project/memark`

`wing_kind`

- 推荐值：`project`、`person`、`general`
- 只有 `project` 默认允许晋升到 `Graphify`

`hall_id`

- 记忆类型
- 例如：`facts`、`events`、`discoveries`、`preferences`、`advice`

`room_id`

- 主题唯一标识
- 应稳定，可重复同步

`room_title`

- 主题标题

`room_summary`

- 对 `room` 的简短概览
- 如果上游没有，可为空

`closets`

- 一个或多个摘要对象
- 这是当前最小实现的默认正文来源

`drawer_refs`

- 指向原始逐字内容的引用
- 不要求全量内联原文

`participants`

- 人、agent、角色

`related_entities`

- 模块、文件、文档、服务、仓库、外部系统

`source_timestamps`

- 原始对话时间范围

`updated_at`

- 本 `room` 最后更新时间

## 已验证上游现实契约

对于 `Codex`，当前实测成立的上游现实契约不是 `room package JSON`，而是：

- 输入源：`~/.codex/sessions/**/*.jsonl`
- 项目识别字段：`session_meta.payload.cwd`
- `MemPalace` ingest 命令：`mine <staging-dir> --mode convos`
- 可读 bridge 表面：`chroma metadata + chroma:document`

当前已知的重要限制：

- `~/.codex/history.jsonl` 不能作为项目主输入
- `MemPalace` 不会自动按项目拆分混合 session 目录
- `MemPalace` convo 去重主要按 `source_file` 路径，而不是内容
- `MemPalace 3.0.0` 对同一路径追加后的 session 不会重新 ingest

因此，`MemArk` 必须自己拥有：

- 项目匹配
- staging
- ledger
- staging snapshot 策略
- package 层逻辑去重

更完整设计见 [`docs/CODEX_SESSION_INGEST_DESIGN.md`](<repo-root>/docs/CODEX_SESSION_INGEST_DESIGN.md)。

## `closet` 推荐最小字段

每个 `closet` 推荐包含：

- `closet_id`
- `summary`
- `key_points`
- `tags`
- `evidence_refs`

说明：

- `summary` 是最适合进入 `Graphify` 正文的内容
- `key_points` 用于稳定输出 bullet points
- `tags` 用于后续 Graphify 关系提取
- `evidence_refs` 指向 `drawer_refs`

## `drawer_refs` 推荐最小字段

每个 `drawer_ref` 推荐包含：

- `drawer_id`
- `timestamp`
- `speaker`
- `excerpt`
- `source_uri`

说明：

- `excerpt` 只保留必要片段
- 不建议默认内联整段原始对话
- `source_uri` 可以是未来实现里的 MCP 地址、内部路径或 stable id

## 晋升准入规则

只有满足下面任一条件的内容，才建议晋升：

- 包含明确决策
- 包含设计取舍
- 包含故障与修复过程
- 包含里程碑进展
- 包含稳定可复用的方法
- 已经生成或正在生成正式文档

默认不晋升：

- 纯闲聊
- 情绪宣泄
- 无结论发散
- 与项目无关的话题
- 高重复、低信息增量的聊天

## 输出目录契约

推荐目录布局如下：

```text
corpus/
  memark/
    promoted/
      room-auth-migration.md
      room-ci-pipeline.md
    documents/
      adr-001.md
      architecture-overview.md
    imports/
      repo-index.md
```

说明：

- `promoted/` 放从 `MemPalace` 晋升来的项目主题包
- `documents/` 放已落盘的项目文档
- `imports/` 放其他预处理输入

每个项目应有独立 corpus。

不建议把多个项目长期混在同一个根目录里。

## 消费契约

当前应把可消费结果明确成三层：

### C1. 记忆层消费

入口：

- `MemPalace search`
- `MemPalace wake-up`
- `MemPalace MCP`

适用问题：

- “我们之前讨论过什么”
- “为什么这样设计”
- “之前试过哪些方案失败了”

### C2. 项目知识层消费

入口：

- `corpus/<project>/promoted/*.md`
- `corpus/<project>/documents/*`

适用问题：

- “这个项目有哪些已经沉淀下来的决策和主题”
- “当前项目有哪些值得优先读的文档”

### C3. 结构层消费

入口：

- `GRAPH_REPORT.md`
- `graph.json`
- `graphify query`
- wiki / Obsidian / MCP

适用问题：

- “当前代码结构是什么”
- “哪些模块相关”
- “改动影响面在哪里”

### C4. 默认消费顺序

推荐顺序：

1. 先看当前问题需要的是历史、沉淀知识，还是结构导航
2. 历史问题先走 `MemPalace`
3. 项目主题问题先走 `promoted/*.md`
4. 结构与影响面问题先走 `Graphify`

这正是 `MemArk` 相比“只靠当前对话上下文”应提供的额外价值。

## 推荐 Markdown 契约

每个晋升文件建议使用如下结构：

```md
---
source: mempalace
source_kind: promoted_room
project: memark
wing_id: project/memark
hall_id: discoveries
room_id: auth-migration
room_title: Authentication Migration
participants:
  - user
  - assistant
tags:
  - auth
  - migration
updated_at: 2026-04-08T00:00:00Z
source_time_start: 2026-04-01T10:00:00Z
source_time_end: 2026-04-07T18:00:00Z
drawer_refs:
  - drawer_001
  - drawer_009
---

# Authentication Migration

## Room Summary

这里放 `room_summary`。

## Closets

### Closet 1

这里放 `closet.summary`。

- Key point A
- Key point B

## Entities

- Module: auth-service
- File: src/auth.ts
- Doc: adr-001.md

## Evidence

- `drawer_001`: 某次关键讨论摘录
- `drawer_009`: 某次修复确认摘录
```

## 为什么要用这种格式

这样做有四个好处：

- 人能直接读
- `Graphify` 能直接吃目录语料
- frontmatter 保留了结构边界
- 仍然可以回到 `MemPalace` 原始内容

## 与 `Graphify` 的边界

`MemArk` 负责：

- 选择哪些项目会话内容值得晋升
- 把它们整理为稳定 corpus
- 保留 provenance

`Graphify` 负责：

- 对这些 corpus 做图谱、报告、查询和导出

当前还不应声称：

- 任何当前生成的 `promoted/*.md` 都已经通过完整 semantic Graphify pipeline 进入最终图谱

因为当前仓库里已经验证的 fallback 仍是 code-only 路径。
