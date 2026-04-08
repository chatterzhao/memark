# Acceptance Checklist

本文件定义当前版本 `MemArk` 的验收标准。

验收对象不是“未来完整产品”，而是当前这版 CLI-first 最小实现。

## A. 仓库与入口

- [x] 仓库内存在真实的 Python 包，而不是只剩文档
- [x] 存在 `python3 -m memark` 入口
- [x] 存在 console script 定义 `memark`
- [x] 不再引用仓库里不存在的 `memark.py`

## B. 工作区初始化

- [x] `memark init` 可创建工作区
- [x] 初始化时会创建 `.memark/config.json`
- [x] 初始化时会创建 `inbox/`
- [x] 初始化时会创建 `corpus/<project>/promoted`
- [x] 初始化时会创建 `corpus/<project>/documents`
- [x] 初始化时会创建 `corpus/<project>/imports`

## C. 输入契约与治理

- [x] `memark validate` 可以校验 room package JSON
- [x] 默认只允许 `wing_kind=project` 的 package 晋升
- [x] 不把“闲聊/general wing”默认送进 `Graphify`
- [x] room package 缺少关键字段时会失败而不是静默继续

## D. 晋升逻辑

- [x] `memark promote` 能把 room package 落成 Markdown
- [x] Markdown 保留 frontmatter 边界信息
- [x] Markdown 包含 `room summary`、`closets`、`evidence`
- [x] 输出路径稳定且可重复覆盖
- [x] 同一 room 重复导入时具备幂等行为
- [x] 可选把已消费 JSON 归档到 `.memark/archive`

## E. 文档纳入

- [x] `memark add-documents` 能把已落盘文档复制进 corpus
- [x] 文档和晋升 room 会落在同一项目 corpus 边界内

## F. Graphify 集成

- [x] `memark build` 会调用真实 `graphify` CLI
- [x] `memark build` 支持 `--update`
- [x] `memark build` 支持 `--wiki`
- [x] `memark build` 支持 `--obsidian`
- [x] `memark build` 支持 `--mcp`
- [x] 当 `graphify` 不存在时会明确报错
- [x] `memark run` 能串联 promote + build

## G. 不做伪实现

- [x] 不声明已实现 `MemPalace` 的增量拉取
- [x] 不声明已实现后台监控服务
- [x] 不声明已实现守护进程式同步
- [x] 不声明已实现 `MemPalace` 数据库稳定直连契约

## H. 自动化验证

- [x] 存在自动化测试
- [x] 覆盖初始化、校验、晋升、幂等、归档、文档复制、Graphify 调用、状态输出
- [x] `memark status --json` 可输出机器可读状态
- [x] `.venv-dev/bin/python -m pytest -q` 通过
- [x] `python3 -m unittest discover -s tests -v` 通过
- [x] `python3 -m compileall memark tests` 通过

## 当前结论

当前版本已经达到“可运行的最小桥接器”验收线。

它还不是“完全自动从 MemPalace 抽取增量的成品”，但已经是：

- 一个真实可安装的 Python CLI
- 一个稳定的 room package -> corpus 编排层
- 一个可测试、可扩展、可继续往上接 extractor 的实现基线
