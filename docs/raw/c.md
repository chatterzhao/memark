# MemArk

> 融合 MemPalace 与 LLM Wiki 的 AI 第二大脑

MemArk 是一个**自动化的知识管理管道**，它将 MemPalace（完美记忆）收集的原始对话，自动转换为 LLM Wiki 的结构化维基知识库，实现 **“分层消费、按需深潜”**。

- **记忆为根**：MemPalace 无损存储所有原始对话（JSONL），保证可回溯、高召回（96.6%）
- **知识为树**：LLM Wiki 将原始资料编译为人类可读的 Markdown 维基，支持双向链接
- **按需深潜**：日常查询使用 Wiki 层（节约 Token），需要溯源时一键下钻到原始记录

---

## 快速开始（给 AI 助手）

**直接把本目录下的 [`skill.md`](./skill.md) 文件交给 AI 助手（如 Claude、GPT）**，它会自动完成所有安装和配置。

如果你想手动安装，请参考下方“手动安装”章节。

---

## 架构概览

```
消费层：人类（Obsidian）←→ 外部 AI Agent
                │
                ▼
MemArk 统一入口（CLI / MCP）
        │               │
        ▼               ▼
   Wiki 层         记忆宫殿层
（结构化知识）    （原始 JSONL）
```

---

## 手动安装（不推荐，仅备查）

```bash
# 1. 创建目录
mkdir -p ~/memark && cd ~/memark

# 2. 安装 MemPalace
pip install mempalace
mempalace init ~/memark/mempalace_data

# 3. 创建 LLM Wiki 目录结构
mkdir -p ~/memark/llm_wiki/{raw,wiki}

# 4. 下载 MemArk 脚本（从本仓库获取）
curl -O https://raw.githubusercontent.com/memark/memark/main/memark.py
chmod +x memark.py

# 5. 同步数据
./memark.py sync
```

详细的脚本内容请参考 [`skill.md`](./skill.md) 中的适配器、CLI 和配置文件。

---

## 使用指南

### 1. 导入聊天记录

将你的 AI 对话导出为 JSONL 格式，然后：

```bash
mempalace import --path /path/to/chat.jsonl
```

### 2. 同步生成原始资料

```bash
memark sync
```

这会将 MemPalace 中的对话导出、转换为 Markdown 并存放到 `llm_wiki/raw/`。

### 3. 编译为 Wiki

让 AI 读取 `llm_wiki/raw/` 中的所有文件，并按照 LLM Wiki 的方法生成 `llm_wiki/wiki/` 目录。

推荐使用 **Obsidian** 打开 `wiki/` 文件夹，享受双向链接的知识网络。

### 4. 查询知识

```bash
memark query "去年讨论过的某个方案"
```

- 优先从 Wiki 层返回结构化摘要
- 如果信息不足，自动调用 MemPalace 检索原始对话

### 5. 下钻到原始记录（计划中）

在 Obsidian 中阅读 Wiki 时，点击引用链接（如 `[^ref_xxx]`），可以触发：

```bash
memark drill ref_xxx
```

这会显示该引用对应的完整原始对话。

---

## 目录结构

```
~/memark/
├── mempalace_data/       # MemPalace 数据库（SQLite + ChromaDB）
├── llm_wiki/
│   ├── raw/              # 转换后的原始 Markdown（由适配器生成）
│   ├── wiki/             # 编译后的结构化维基（AI 生成）
│   └── CLAUDE.md         # LLM Wiki 配置文件
├── memark.py             # MemArk CLI 主脚本
├── adapter.py            # JSONL → Markdown 转换器
├── config.yaml           # 配置文件
└── memark.log            # 日志
```

---

## 命令参考

| 命令 | 说明 |
|------|------|
| `memark init` | 初始化目录结构（已由安装完成） |
| `memark sync` | 从 MemPalace 导出最新对话，转换并放入 `raw/` |
| `memark query "<问题>"` | 查询知识（先 Wiki 后 MemPalace） |
| `memark upgrade` | 升级 MemPalace 组件 |
| `memark serve --mcp` | 启动 MCP 服务器供外部 AI 调用 |

---

## 设计思想

### 分层消费，节约 Token

- **Wiki 层**：精炼、结构化，适合 80% 的日常查询
- **记忆层**：完整、原始，只在需要溯源或细节时调用

### Skill 式安装

用户不再需要手动配置依赖、环境变量等。只需将 `skill.md` 提供给 AI，AI 会自动执行安装脚本。这符合 AI 时代“以 AI 为中心”的交互模式。

### 双向增强

- 记忆 → 知识：自动管道，新对话持续流入 Wiki
- 知识 → 记忆：用户在 Wiki 中的修正可以回流到 MemPalace（计划中）

---

## 未来路线

- [ ] 官方 Python 包：`pip install memark`
- [ ] 完整的 MCP 服务器实现
- [ ] Obsidian 插件：一键下钻、高亮溯源
- [ ] 增量编译：仅处理新增对话
- [ ] 知识图谱可视化

---

## 许可证

MIT

---

## 相关项目

- [MemPalace](https://github.com/milla-jovovich/mempalace) – 完美记忆宫殿
- [LLM Wiki](https://github.com/andrepk/llm-wiki) – 概念性项目（Andrej Karpathy 引爆）
- [Obsidian](https://obsidian.md) – 强大的知识管理工具

---

**MemArk：让 AI 的记忆成为你的知识。**