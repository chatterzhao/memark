# 评审结论

## Findings

### 1. 快速开始引用了仓库中不存在的关键文件，主流程无法执行

- [docs/c.md:15](<repo-root>/docs/c.md#L15) 和 [docs/f.md:66](<repo-root>/docs/f.md#L66) 都要求用户“把本目录下的 `skill.md` 交给 AI 助手”，但本次提交里并没有根目录 `skill.md`，仓库中只有 `docs/a.md` 到 `docs/f.md`。
- 同时，[docs/c.md:49](<repo-root>/docs/c.md#L49) 和 [docs/f.md:82](<repo-root>/docs/f.md#L82) 要求用户直接下载仓库中的 `memark.py`，而这次提交也没有提供该脚本。
- 结果是 README/快速开始在第一步就会把用户带到不存在的文件或脚本，属于阻断性问题。

### 2. 安装 Skill 中的核心命令仍是“假设存在”的占位接口，AI 按文档执行会失败

- [docs/e.md:120](<repo-root>/docs/e.md#L120) 明确写着“这里假设有一个命令 `mempalace list-rooms --since <timestamp>`”。
- [docs/e.md:227](<repo-root>/docs/e.md#L227) 将 Graphify 编译建立在“假设 graphify 提供了 build 命令”上。
- [docs/e.md:280](<repo-root>/docs/e.md#L280) 又将 drill 建立在“假设 mempalace 提供 get-room 命令”上。
- [docs/b.md:193](<repo-root>/docs/b.md#L193) 到 [docs/b.md:205](<repo-root>/docs/b.md#L193) 也承认 `mempalace export` 只是推测接口，失败时直接生成示例文件兜底。
- 这些文件的定位是“请严格按以下步骤执行”的安装配置文档，但主路径依赖未验证的 CLI。对用户或 AI 助手而言，这不是说明不完善，而是流程本身不可落地。

### 3. 多份文档对产品形态和命令约定互相冲突，无法判断哪份是权威版本

- [docs/c.md:3](<repo-root>/docs/c.md#L3) 将项目定义为 “MemPalace + LLM Wiki”，目录结构也是 `llm_wiki/`；[docs/f.md:3](<repo-root>/docs/f.md#L3) 则改为 “MemPalace + Graphify”，目录结构变为 `graphify_data/`。
- [docs/c.md:131](<repo-root>/docs/c.md#L131) 记录的命令是 `memark serve --mcp`，而 [docs/f.md:166](<repo-root>/docs/f.md#L166) 记录的是 `memark serve`。
- 如果这些文档被一并提交，读者将同时看到两套互斥的架构、目录和命令接口，直接增加误用和支持成本。

### 4. 文档中存在已落地的编码/内容损坏，说明发布前缺少最基本的校验

- [docs/b.md:106](<repo-root>/docs/b.md#L106) 的代码块中出现了明显乱码：“Markdown ���式”。
- 这类损坏已经进入最终文档内容，说明至少缺少一次基本的渲染或编码检查。虽然不一定阻断执行，但会降低文档可信度，也容易暗示还有未被发现的复制/转码问题。
