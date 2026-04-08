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
7. `memark status`

## 为什么第一版这样切

当前没有核对到 `MemPalace` 官方公开的“按时间戳取增量”接口。

因此第一版不能把下面这种能力写成已实现：

- 直接查询某个时间戳后的更新
- 直接读取 `MemPalace` 数据库并承诺兼容
- 直接依赖不存在的 `mempalace list-rooms --since`

第一版采用的真实边界是：

1. 外部抽取器、AI 助手或人工步骤先产出 room package JSON
2. `MemArk` 负责校验这些 package
3. `MemArk` 负责把 package 稳定晋升为 corpus Markdown
4. `MemArk` 负责把正式文档一起纳入 corpus
5. `MemArk` 负责触发 `Graphify`

## 当前工作区布局

```text
workspace/
  .memark/
    config.json
    archive/
    state/
      <project>-ledger.json
  inbox/
  corpus/
    <project>/
      promoted/
      documents/
      imports/
```

说明：

- `inbox/`：外部抽取器投递 room package JSON 的位置
- `promoted/`：由 `MemArk` 生成的 Graphify-ready Markdown
- `documents/`：已落盘项目文档
- `imports/`：预留给后续其他输入源
- `ledger.json`：记录每个 room 的内容指纹，避免重复写入

## 当前实现原则

- CLI first
- Python stdlib first
- 不直接耦合 `MemPalace` 内部数据库
- 不伪造未验证的上游命令
- 输出必须直接可给 `Graphify` 消费
- 重复导入应可幂等
- 状态输出应支持脚本化消费

## 下一阶段建议

### Phase 2: 上游抽取器

目标：

- 增加一个单独的 extractor 层，而不是把数据库读取硬塞进当前 CLI

建议形式：

- `memark extract-*` 子命令
- 或单独的 `memark-mempalace-adapter`

前提：

- 必须先核对 `MemPalace` 是否提供稳定可依赖的数据访问面
- 如果没有，就只能把读取数据库定义为“best effort adapter”，不能写成稳定契约

### Phase 3: 自动化编译

目标：

- 在 `promote` 之后按策略触发 `build`
- 增加批量目录消费和更完整的归档策略

注意：

- 仍不建议在主产品路径里直接做“后台守护进程”
- 先把可重入、可脚本化的 CLI 做稳

### Phase 4: 平台集成

目标：

- 为 Claude Code / Codex / Cloud Code 一类环境补充调用说明
- 但不把安装 Skill 和运行期桥接器混成同一层

## 当前不足

- 还没有直接抽取 `MemPalace` room package 的适配器
- 还没有 `imports/` 的实际处理命令
- 还没有对 `Graphify` 输出结果做二次验证
- 还没有 Windows CI
