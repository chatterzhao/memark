# MemArk

> 把 `MemPalace` 里的项目记忆，整理成 `Graphify` 最适合消费的项目语料。

上游项目：

- `MemPalace` GitHub: <https://github.com/milla-jovovich/mempalace>
- `Graphify` GitHub: <https://github.com/safishamsi/graphify>

## 当前判断

基于上游源码、README 和本仓库里的实际验证记录，当前可以把三者关系收敛为：

- `MemPalace`：记忆层。保留原始内容，按 `wing -> hall -> room -> closet -> drawer` 组织；`closet` 是指向原文的摘要，`drawer` 保留逐字内容；既能 CLI 搜索，也能提供 wake-up context、MCP 工具与自动化采集路径。
- `Graphify`：知识编译层。把目录语料编译为 `graph.json`、`GRAPH_REPORT.md`、`graph.html`，并进一步支持 wiki / Obsidian / MCP / query 等消费路径。
- `MemArk`：桥接层。把 `MemPalace` 中具备项目知识价值的内容，整理成 `Graphify` 的稳定输入目录。

`MemArk` 不是新的记忆系统，也不是新的图谱引擎。

## 两个上游到底怎么用，才能发挥它们的强项

### `MemPalace`

`MemPalace` 的强项不是“人工天天搜库”，而是：

- 本地保存原始对话和资料
- 让 AI 在后续对话里找回上下文
- 在需要时回到原始逐字内容
- 给 AI 一个短得多的 wake-up context，而不是每次重喂历史
- 通过 hooks / `MEMPAL_DIR` 把长期采集自动化

更合适的使用方式是：

1. 安装并执行一次 `mempalace init`、`mempalace mine`
2. 把它接给支持 MCP 的 AI 客户端，或者直接使用它的 CLI / wake-up
3. 让 AI 在问答时自动调用搜索、wake-up 和记忆工具，而不是把它当成人工知识库 UI
4. 对长期项目或长期聊天，优先用 hooks / 自动 mine 保持记忆持续更新

需要特别注意的一点是：

- 当前源码里可以看到 drawer metadata 含 `filed_at`
- 但没有核对到一个稳定公开的“按时间戳取增量” CLI 或 MCP 接口

这意味着 `MemArk` 不能假设上游已经提供现成的 `since` 拉取能力。

### `Graphify`

`Graphify` 的强项也不只是“把内容排成 wiki”。

它更像一个“编译 + 查询 + 平台接入”的知识图谱层，适合：

- 对一个持续积累的 corpus 目录运行
- 先形成图谱和报告，再让人或 AI 沿结构下钻原文
- 产出 `graph.json` 后继续做 query / MCP / wiki / Obsidian 导航
- 对代码变动做 watch / hook，对文档和研究材料做增量更新

更合适的使用方式是：

1. 给它一个稳定的项目语料目录，而不是每次手工粘贴聊天
2. 先让 AI 读 `GRAPH_REPORT.md` 做全局定向，再按需 query `graph.json`
3. 把代码、文档、图像、研究材料和晋升后的项目记忆放在同一个 corpus 边界里
4. 把 `graph.json` 继续作为 AI 可读的查询面，而不是只看静态 HTML

## MemArk 该做什么

`MemArk` 的合理职责是：

1. 从 `MemPalace` 中识别哪些内容已经值得晋升为项目知识
2. 以 `project wing` 为边界，按 `room` 组织这些内容
3. 优先抽取 `closet`，必要时附上 `drawer` 引用
4. 落成 `Graphify` 可直接消费的 Markdown 语料
5. 触发 `Graphify` 对 corpus 做 `--update`、`--wiki` 或其他编译

当前 `MemArk` 的默认设计假设不是整个宫殿，也不是裸 `drawer`，而是：

`project wing -> hall -> room -> closet (+ drawer refs)`

这是桥接层的治理选择，不是上游官方强制接口。原因很直接：

- 直接喂全量 `drawer`，噪音太大
- 只喂顶层 taxonomy，信息又太薄
- `room + closet` 正好保留了主题边界和足够正文

## 当前仓库提供什么

这个仓库现在已经提供一个可运行的、CLI-first 的 `MemArk` 最小实现。

已经提供：

- 经过收敛的项目定义
- `MemPalace -> MemArk -> Graphify` 的治理和接口说明
- 一个只负责安装上游工具的 [`SKILL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/SKILL.md)
- 基于真实命令执行结果的安装验证记录
- 一个真实可运行的 Python CLI：`memark`

当前 CLI 已支持：

- `memark init`
- `memark validate`
- `memark promote`
- `memark add-documents`
- `memark build`
- `memark run`
- `memark status`

仍然没有提供：

- 直接从 `MemPalace` 数据库或 MCP 自动抽取增量的实现
- 后台监控或同步服务

另一个重要事实是：

- 当前在 `.venv-skill-check` 中验证到的 `graphifyy 0.3.12` 顶层 `graphify --help` 暴露的是 `install`、`query`、`hook`、`claude/codex install` 等入口
- 它不是一个稳定公开的“任何版本都支持 `graphify <folder>`”接口
- 因此 `MemArk build` 当前应被理解为“调用兼容的 Graphify 构建入口”，而不是保证所有 `graphifyy` 安装都可直接按同一命令消费目录

## 当前 CLI 怎么用

先安装当前仓库里的 CLI：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

先初始化一个工作区：

```bash
python3 -m memark init ./memark-work --project myproject
```

仓库里自带一个可直接试跑的样例：

[`examples/sample_room_package.json`](/Users/zhaoyu/Downloads/code/my-memark/memark/examples/sample_room_package.json)

可以先把它放进 `inbox/promoted/`，再执行校验与晋升：

```bash
cp examples/sample_room_package.json ./memark-work/inbox/promoted/room.json
python3 -m memark validate ./memark-work/inbox/promoted/room.json
python3 -m memark promote --workspace ./memark-work
```

如果已经有 room package JSON，也可以直接放进去执行同一条主路径。

`promote` 会把输入写成下面这种 Graphify corpus：

```bash
memark-work/
  corpus/
    myproject/
      promoted/
        room-*.md
      documents/
      imports/
```

如果还要把已落盘文档一起喂给 `Graphify`：

```bash
python3 -m memark add-documents --workspace ./memark-work ./docs/adr-001.md
```

最后由 `MemArk` 触发 `Graphify`：

```bash
python3 -m memark build --workspace ./memark-work --update --wiki
```

如果希望“一次消费 inbox 并立刻触发 Graphify”，可以直接：

```bash
python3 -m memark run --workspace ./memark-work --update --wiki
```

其中当前实现约定：

- `inbox/promoted/` 放 room package JSON
- `inbox/documents/` 放待并入 corpus 的正式文档
- `run` 会先消费这两个目录，再触发 `Graphify`

注意：

- 当前版本不会伪造 `MemPalace` 的 `since` 接口
- 因此“从宫殿里拿出 room package”这一步，仍需要外部抽取器、AI 助手或后续专门适配器来完成
- `MemArk` 当前负责的是稳定消费这些 package，并落成 `Graphify` 能直接吃的 corpus
- `memark status --json` 可作为脚本化验收入口

## 文档

- [`README.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/README.md)：项目入口
- [`SKILL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/SKILL.md)：安装 `MemPalace` 与 `Graphify` 的 AI Skill
- [`docs/PROJECT_SCOPE.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/PROJECT_SCOPE.md)：项目边界、组件关系、当前状态
- [`docs/GOVERNANCE_MODEL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/GOVERNANCE_MODEL.md)：闲聊、项目对话、产出文档的隔离与晋升模型
- [`docs/INTERFACE_CONTRACT.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/INTERFACE_CONTRACT.md)：推荐输入契约、输出契约与 Markdown 包格式
- [`docs/INSTALL_VERIFICATION.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/INSTALL_VERIFICATION.md)：真实安装与 CLI 验证结果
- [`docs/IMPLEMENTATION_PLAN.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/IMPLEMENTATION_PLAN.md)：当前 Python CLI 的实现范围与后续分层
- [`docs/ACCEPTANCE_CHECKLIST.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/ACCEPTANCE_CHECKLIST.md)：当前版本的验收标准与完成状态
- [`docs/PRODUCT_REQUIREMENTS.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/PRODUCT_REQUIREMENTS.md)：基于 `MemPalace` 与 `Graphify` 能力面收敛出的具体需求
- [`docs/DOCUMENT_STATUS.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/DOCUMENT_STATUS.md)：正式文档与研究归档的关系
- [`docs/MAINTAINER_SKILL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/MAINTAINER_SKILL.md)：旧的维护型 Skill 说明
- [`examples/sample_room_package.json`](/Users/zhaoyu/Downloads/code/my-memark/memark/examples/sample_room_package.json)：可直接试跑的 room package 示例

## 开源价值

这个项目值得开源，不是因为它重新发明了记忆或图谱，而是因为它试图把两种已经成立的能力接干净：

- `MemPalace` 的“记住与找回”
- `Graphify` 的“编译与导航”

如果这条桥接契约被定义清楚，用户就不必在记忆层和知识层之间手工搬运语料。
