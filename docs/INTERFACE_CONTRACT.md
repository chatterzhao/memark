# Interface Contract

本文件只定义一件事：

`MemArk` 作为桥接层，应该从 `MemPalace` 取什么，落成什么，再交给 `Graphify`。

这里不假装外部命令已经验证存在。
本文件只定义推荐的数据契约与目录契约，供后续实现时对照。

## 目标

目标不是把 `MemPalace` 全量导出。

目标是把 `MemPalace` 中已经具备项目知识价值的内容，整理成 `Graphify` 最适合处理的项目语料。

默认主路径：

1. 从 `project wing` 读取增量
2. 以 `room` 为晋升单位
3. 优先抽取 `closet`
4. 附带必要 `drawer` 引用
5. 落成稳定 Markdown 文件
6. 交给 `Graphify` 对项目语料目录做增量编译

## 上游输入契约

`MemArk` 不需要一次拿到整个宫殿。

最小可用输入单位应为一个 `room package`。

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
- 这是默认正文来源

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

只有满足下面任一条件的 `room`，才建议晋升：

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

- `promoted/` 放从 `MemPalace` 晋升来的 `room` 包
- `documents/` 放已落盘的项目文档
- `imports/` 放其他预处理输入

每个项目应有独立 corpus。

不建议把多个项目长期混在同一个根目录里。

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

- 选择哪些 `room` 值得晋升
- 把结构化记忆转成稳定语料文件
- 保留追溯信息

`Graphify` 负责：

- 读取项目 corpus
- 生成知识图谱
- 生成报告、Wiki、Obsidian 输出

因此 `MemArk` 不应该：

- 试图替代 `Graphify` 的图谱构建
- 试图在桥接层做过重的知识编译
- 直接把所有原始聊天灌给 `Graphify`

## 最小实现建议

如果以后开始做代码实现，推荐先实现最小路径：

1. 只处理 `wing_kind=project`
2. 只处理 `room` 级增量
3. 每个 `room` 只取一份主 `closet.summary`
4. 每个 `room` 最多附带少量 `drawer_refs`
5. 输出到单项目 corpus
6. 再由 `Graphify` 做增量更新

这样可以先验证主链路，而不是一开始就做成“全宫殿同步器”。
