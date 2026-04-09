# Acceptance Checklist

本文件定义当前版本 `MemArk` 的验收标准。

验收对象不是“未来完整产品”，而是当前这版 `CLI-first` 实现，以及已经接上的 `Codex session intake + MemPalace convo mine` 能力。

## A. 仓库与入口

- [x] 仓库内存在真实的 Python 包，而不是只剩文档
- [x] 存在 `python3 -m memark` 入口
- [x] 存在 console script 定义 `memark`
- [x] 不再引用仓库里不存在的 `memark.py`

## B. 工作区初始化

- [x] `memark init` 可创建工作区
- [x] 初始化时会创建 `.memark/config.json`
- [x] 初始化时会创建 `inbox/`
- [x] 初始化时会创建 `inbox/promoted/`
- [x] 初始化时会创建 `inbox/documents/`
- [x] 初始化时会创建 `corpus/<project>/promoted`
- [x] 初始化时会创建 `corpus/<project>/documents`
- [x] 初始化时会创建 `corpus/<project>/imports`

## C. 输入契约与治理

- [x] `memark validate` 可以校验 room package JSON
- [x] 默认只允许 `wing_kind=project` 的 package 晋升
- [x] 不把“闲聊/general wing”默认送进 `Graphify`
- [x] room package 缺少关键字段时会失败而不是静默继续

## D. 已实现晋升逻辑

- [x] `memark promote` 能把 room package 落成 Markdown
- [x] Markdown 保留 frontmatter 边界信息
- [x] Markdown 包含 `room summary`、`closets`、`evidence`
- [x] 输出路径稳定且可重复覆盖
- [x] 同一 room 重复导入时具备幂等行为
- [x] 可选把已消费 JSON 归档到 `.memark/archive`

## E. 已实现文档纳入

- [x] `memark add-documents` 能把已落盘文档复制进 corpus
- [x] 文档和晋升 room 会落在同一项目 corpus 边界内

## F. 已实现 Graphify 集成

- [x] `memark build` 会调用外部配置的 Graphify 构建入口
- [x] 当顶层 `graphify <folder>` 不可用时，`memark build` 会退回已验证的 code-only fallback
- [x] `memark build` 支持 `--update`
- [x] `memark build` 支持 `--wiki`
- [x] `memark build` 支持 `--obsidian`
- [x] `memark build` 支持 `--mcp`
- [x] 当 `graphify` 不存在时会明确报错
- [x] 当遇到 helper/query 型 `graphify` CLI 且 fallback 不可用时会明确报错
- [x] `memark run` 能串联 promote + build
- [x] `memark run` 会先消费 `inbox/promoted` 与 `inbox/documents`
- [x] `memark mempalace-mine` 能调用 `mempalace mine --mode convos`
- [x] `memark mempalace-mine` 支持 `--dry-run`
- [x] `memark mempalace-mine` 在 `mempalace` 不存在时会明确报错
- [x] `memark palace-export` 能只读导出项目 palace 中的 drawer

## G. 不做伪实现

- [x] 不声明已实现 `MemPalace` 的增量拉取
- [x] 不声明已实现后台监控服务
- [x] 不声明已实现守护进程式同步
- [x] 不声明已实现 `MemPalace` 数据库稳定直连契约
- [x] 不把 `~/.codex/history.jsonl` 写成项目级默认输入
- [x] 不声称 `MemPalace` 会自动按项目拆分混合 `Codex` 会话

## H. 自动化验证

- [x] 存在自动化测试
- [x] 覆盖初始化、校验、晋升、幂等、归档、文档复制、Graphify 调用、状态输出
- [x] `memark status --json` 可输出机器可读状态
- [x] `.venv-dev/bin/python -m pytest -q` 通过
- [x] `python3 -m unittest discover -s tests -v` 通过
- [x] `python3 -m compileall memark tests` 通过

## I. 已实现的 Codex / MemPalace 编排验收项

- [x] 能扫描 `~/.codex/sessions/**/*.jsonl`
- [x] 能从 `session_meta.payload.cwd` 判断项目归属
- [x] 能把一个项目的 session 文件同步到独立 staging 目录
- [x] 能识别同一路径 session 文件增长后的新增内容
- [ ] 还能避免“同内容异路径”导致的重复 ingest
- [x] 能以项目 staging 为输入执行 `mempalace mine --mode convos`
- [x] 能对混合项目 session 做正确隔离，不再让它们落成同一个 ingest 输入目录
- [x] 能在失败时报告具体是 session 解析失败、staging 失败，还是 `MemPalace` mine 失败
- [x] 能从项目 palace 读出 `document + metadata`
- [ ] 还能提供项目级 rebuild 操作
- [x] 文档明确说明当前 Graphify fallback 只保证 code graph 重建，不保证 mixed-corpus 完整编译

## 当前结论

当前版本已经达到“可运行的最小桥接器”验收线。

它还不是“完全自动从 MemPalace 抽取增量的成品”，但已经是：

- 一个真实可安装的 Python CLI
- 一个稳定的 room package -> corpus 编排层
- 一个可测试、可扩展、已具备 code-only Graphify fallback 的实现基线

下一阶段的核心验收重点，不再是继续补主链命令，而是处理两类剩余问题：

- `session` 去重目前仍是“同路径文件增量”，还不是跨路径内容归并
- 还没有项目级 `clean / rebuild / retry` 管理命令
