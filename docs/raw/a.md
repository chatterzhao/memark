# 文件一：`skill.md`

```markdown
# Skill: MemArk 部署与配置

## 技能描述
本 Skill 用于在用户环境中自动部署和配置 MemArk 系统，包括 MemPalace、LLM Wiki 以及 MemArk 核心管道。

## 触发条件
当用户说以下任意语句时触发本 Skill：
- "帮我安装 MemArk"
- "配置 MemArk 系统"
- "部署 AI 第二大脑"
- "设置记忆宫殿 + Wiki"

## 执行步骤

### 步骤 1：环境检查
```bash
# 检查 Python 版本（需要 >= 3.10）
python --version

# 检查 pip
pip --version

# 检查 git
git --version

# 检查 Node.js（可选，某些依赖需要）
node --version
```

如果缺少依赖，告知用户并自动安装（使用系统包管理器）。

### 步骤 2：创建项目目录
```bash
mkdir -p ~/memark
cd ~/memark
```

### 步骤 3：安装 MemPalace
```bash
# 安装 MemPalace Python 包
pip install mempalace

# 初始化 MemPalace 数据库
mempalace init ~/memark/mempalace_data

# 验证安装
mempalace status
```

### 步骤 4：安装 LLM Wiki
```bash
# 克隆 LLM Wiki 仓库
git clone https://github.com/milla-jovovich/llm-wiki.git ~/memark/llm-wiki

# 安装依赖（如果有 requirements.txt）
cd ~/memark/llm-wiki
pip install -r requirements.txt 2>/dev/null || echo "无 requirements 文件，跳过"

# 创建必要的目录结构
mkdir -p ~/memark/llm-wiki/raw
mkdir -p ~/memark/llm-wiki/wiki
```

### 步骤 5：配置 MemArk 核心
创建配置文件 `~/memark/config.yaml`：

```yaml
# MemArk 配置文件
version: "1.0"

paths:
  mempalace_data: "~/memark/mempalace_data"
  llm_wiki_root: "~/memark/llm-wiki"
  raw_folder: "~/memark/llm-wiki/raw"
  wiki_folder: "~/memark/llm-wiki/wiki"

mempalace:
  database: "sqlite"
  sqlite_path: "~/memark/mempalace_data/memories.db"
  chromadb_path: "~/memark/mempalace_data/chroma"

llm_wiki:
  ai_model: "claude"  # 可选: claude, gpt, local
  compile_interval: 300  # 秒，5分钟

memark:
  log_level: "INFO"
  auto_sync: true
  sync_interval: 3600  # 秒，1小时
```

### 步骤 6：创建 MemArk CLI 入口
创建 `~/memark/memark.py`：

```python
#!/usr/bin/env python3
"""
MemArk CLI - 统一入口
"""

import argparse
import subprocess
import sys
import json
from pathlib import Path

# 加载配置
CONFIG_FILE = Path.home() / "memark" / "config.yaml"
if CONFIG_FILE.exists():
    import yaml
    config = yaml.safe_load(CONFIG_FILE.read_text())
else:
    print("错误: 未找到配置文件，请先运行 memark init")
    sys.exit(1)


def cmd_sync():
    """同步：从 MemPalace 拉取对话 → 转换 → 存入 raw/ → 触发 Wiki 编译"""
    print("🔄 开始同步...")
    
    # 1. 从 MemPalace 导出最近的对话（JSONL 格式）
    print("  📥 从 MemPalace 拉取对话...")
    result = subprocess.run(
        ["mempalace", "export", "--format", "jsonl", "--days", "7"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"  ❌ MemPalace 导出失败: {result.stderr}")
        return False
    
    # 2. 转换 JSONL → Markdown（适配器）
    print("  🔄 转换 JSONL → Markdown...")
    conversations = [json.loads(line) for line in result.stdout.strip().split('\n') if line]
    
    for conv in conversations:
        markdown = convert_to_markdown(conv)
        raw_file = Path(config['paths']['raw_folder']) / f"{conv['id']}.md"
        raw_file.write_text(markdown)
    
    # 3. 触发 LLM Wiki 编译
    print("  📚 触发 LLM Wiki 编译...")
    subprocess.run(
        ["python", str(Path(config['paths']['llm_wiki_root']) / "compile.py")],
        cwd=config['paths']['llm_wiki_root']
    )
    
    print("✅ 同步完成！")
    return True


def convert_to_markdown(conv: dict) -> str:
    """将 JSONL 对话转换为 Markdown 格式"""
    md = f"# 对话: {conv.get('title', conv['id'])}\n\n"
    md += f"> 原始引用: `{conv['id']}`\n"
    md += f"> 时间: {conv.get('timestamp', '未知')}\n\n"
    md += "---\n\n"
    
    for msg in conv.get('messages', []):
        role = "用户" if msg['role'] == 'user' else "AI"
        md += f"**{role}:**\n\n{msg['content']}\n\n"
        md += f"[🔗 查看原始记录](memark://drill?id={conv['id']}&msg={msg.get('index', 0)})\n\n"
        md += "---\n\n"
    
    return md


def cmd_query(query: str):
    """查询：先查 Wiki，必要时下钻到 MemPalace"""
    print(f"🔍 查询: {query}")
    
    # 1. 先在 Wiki 中搜索
    wiki_root = Path(config['paths']['wiki_folder'])
    if wiki_root.exists():
        result = subprocess.run(
            ["grep", "-r", "-i", query, str(wiki_root)],
            capture_output=True,
            text=True
        )
        if result.stdout:
            print("📖 从 Wiki 找到相关条目:\n")
            print(result.stdout[:2000])  # 限制输出长度
            print("\n💡 如需查看原始对话，请使用: memark drill <ref-id>")
            return
    
    # 2. Wiki 没找到，下钻到 MemPalace
    print("📦 Wiki 中未找到，正在搜索原始记忆...")
    result = subprocess.run(
        ["mempalace", "query", query],
        capture_output=True,
        text=True
    )
    print(result.stdout)


def cmd_drill(ref_id: str):
    """下钻：根据引用 ID 获取原始对话"""
    print(f"🔍 获取原始记录: {ref_id}")
    
    result = subprocess.run(
        ["mempalace", "get", "--id", ref_id],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("\n📄 原始对话记录:\n")
        print(result.stdout)
    else:
        print(f"❌ 未找到记录: {result.stderr}")


def cmd_serve():
    """启动 MCP 服务器"""
    print("🚀 启动 MemArk MCP 服务器...")
    subprocess.run(["mempalace", "serve", "--mcp"])


def main():
    parser = argparse.ArgumentParser(description="MemArk - AI 第二大脑")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    subparsers.add_parser("sync", help="同步记忆到 Wiki")
    subparsers.add_parser("serve", help="启动 MCP 服务器")
    
    query_parser = subparsers.add_parser("query", help="查询知识")
    query_parser.add_argument("query", type=str, help="查询内容")
    
    drill_parser = subparsers.add_parser("drill", help="下钻到原始记录")
    drill_parser.add_argument("ref_id", type=str, help="引用 ID")
    
    args = parser.parse_args()
    
    if args.command == "sync":
        cmd_sync()
    elif args.command == "query":
        cmd_query(args.query)
    elif args.command == "drill":
        cmd_drill(args.ref_id)
    elif args.command == "serve":
        cmd_serve()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

### 步骤 7：创建快捷命令
```bash
# 创建全局可执行文件
chmod +x ~/memark/memark.py
ln -sf ~/memark/memark.py /usr/local/bin/memark

# 验证
memark --help
```

### 步骤 8：设置自动同步（可选）
```bash
# 添加 crontab 定时任务
(crontab -l 2>/dev/null; echo "0 */1 * * * /usr/local/bin/memark sync") | crontab -
```

### 步骤 9：验证安装
```bash
# 检查所有组件状态
memark status

# 执行一次手动同步
memark sync

# 测试查询
memark query "测试查询"
```

## 预期输出
成功安装后，用户应看到：
```
✅ MemArk 安装完成！

下一步：
1. 查看 Wiki: cd ~/memark/llm-wiki/wiki && ls
2. 在 Obsidian 中打开 ~/memark/llm-wiki/wiki 作为仓库
3. 手动同步: memark sync
4. 查询知识: memark query "你的问题"
5. 启动 MCP: memark serve
```

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| `mempalace: command not found` | 重新安装: `pip install mempalace --force-reinstall` |
| JSONL 转换失败 | 检查 MemPalace 导出格式，确保包含 `messages` 字段 |
| Wiki 编译无输出 | 确认 `raw/` 文件夹中有 `.md` 文件 |
| MCP 端口冲突 | 修改 `config.yaml` 中的端口配置 |

## 注意事项
1. MemPalace 的 MCP Server 默认在本地运行，数据不会上传
2. LLM Wiki 编译需要调用 AI（Claude/OpenAI），请确保 API Key 已配置
3. 首次同步可能需要几分钟，取决于对话数量
```

---

# 文件二：`README.md`

```markdown
# MemArk

> 融合 MemPalace 与 LLM Wiki 的 AI 第二大脑

MemArk 是一个深度集成项目，将 MemPalace（完美记忆）和 LLM Wiki（智慧整理）合二为一，构建一个能从对话中**自动生长、永不遗忘、分层消费**的 AI 第二大脑系统。

## 核心理念

```
记忆为根，知识为树，按需深潜，永不遗忘。
```

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      消费层：谁在提问                         │
│          👤 人类用户                    🤖 外部 AI Agent       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   MemArk 核心：统一查询入口                   │
│                  memark query / memark serve                 │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────┐
│   第一响应：Wiki 知识层   │     │   深潜：记忆宫殿层           │
│  • LLM Wiki 结构化知识库 │     │  • MemPalace MCP Server     │
│  • Markdown 页面 + 双向链 │ ◄── │  • 19 个查询/读写工具         │
│  • 语义搜索接口          │ 触发 │  • JSONL / ChromaDB / SQLite│
└─────────────────────────┘     └─────────────────────────────┘
```

## 组件职责

| 组件 | 职责 | 输入 | 输出 | 消费者 |
|------|------|------|------|--------|
| **MemPalace** | 无损记忆 | 对话 JSONL | SQLite/ChromaDB | AI Agent、程序 |
| **LLM Wiki** | 结构化整理 | `raw/` 文件夹 | `wiki/` Markdown | 人类（Obsidian） |
| **MemArk** | 管道 + 统一入口 | 两者输出 | 查询结果 + 溯源 | 人类 + AI |

## 快速开始

### 对于 AI（推荐）

直接对任意 AI 助手说：

> "请按照 skill.md 帮我安装 MemArk"

AI 会自动完成所有安装配置。

### 对于人类（手动）

```bash
# 1. 安装 MemArk CLI
pip install memark

# 2. 初始化
memark init

# 3. 同步记忆 → 知识
memark sync

# 4. 查询
memark query "我们讨论过的方案"
```

## 使用场景

### 场景 1：日常查询（Wiki 层）
```bash
memark query "上周的产品需求"
```
返回：结构化的 Wiki 摘要，快速、节约 Token。

### 场景 2：深度溯源（下钻层）
当 Wiki 摘要不够用时，点击引用链接：
```bash
memark drill "conv_20240101_001"
```
返回：完整的原始对话 JSONL。

### 场景 3：AI Agent 集成
启动 MCP 服务器，供外部 AI 调用：
```bash
memark serve
```
然后 AI 可以通过 MCP 协议查询记忆。

### 场景 4：Obsidian 知识库
在 Obsidian 中打开 `~/memark/llm-wiki/wiki` 文件夹：
- 浏览自动生成的 Wiki 页面
- 点击双向链接跳转
- 点击引用链接下钻到原始记录

## 命令参考

| 命令 | 说明 |
|------|------|
| `memark init` | 初始化项目（首次运行） |
| `memark sync` | 同步：记忆 → Wiki |
| `memark query "<问题>"` | 查询（先 Wiki，后下钻） |
| `memark drill <ref-id>` | 根据引用 ID 获取原始记录 |
| `memark serve` | 启动 MCP 服务器 |
| `memark upgrade --all` | 升级所有组件 |
| `memark status` | 查看状态 |

## 目录结构

```
~/memark/
├── mempalace_data/      # MemPalace 数据
│   ├── chromadb/        # 向量数据库
│   └── memories.db      # SQLite 数据库
├── llm-wiki/            # LLM Wiki 项目
│   ├── raw/             # 原始资料（自动填入）
│   ├── wiki/            # 生成的 Wiki（Obsidian 打开这个）
│   └── compile.py       # 编译脚本
├── config.yaml          # MemArk 配置
├── memark.py            # CLI 入口
└── memark.log           # 运行日志
```

## 工作流程

### 正向：记忆 → 知识
```
AI 对话 → MemPalace 存储 → memark sync → 适配器转换 → raw/ → LLM Wiki 编译 → wiki/ → Obsidian 阅读
```

### 反向：知识 → 记忆
```
Obsidian 编辑 Wiki → memark feedback → MemPalace 更新记忆
```

## 设计思想：分层消费，按需深潜

1. **Wiki 层（第一响应）**：日常查询优先，返回结构化摘要，节约 Token
2. **MemPalace 层（深潜）**：需要溯源时下钻，获取完整原始记录
3. **无缝衔接**：Wiki 页面中的每条陈述都带有引用链接

这类似于 **Skill 设计思想**——Wiki 是“目录”，MemPalace 是“全书”。

## 技术依赖

- Python >= 3.10
- MemPalace（pip install mempalace）
- LLM Wiki（git clone）
- Obsidian（可选，用于阅读 Wiki）
- Claude/OpenAI API Key（用于 LLM Wiki 编译）

## 路线图

- [x] Phase 1: 基础集成与管道构建（MVP）
- [ ] Phase 2: 双向增强（Wiki 反哺记忆）
- [ ] Phase 3: 智能引擎（矛盾检测、知识图谱）
- [ ] Phase 4: 产品化与生态（GUI、插件）

## 贡献

欢迎提交 Issue 和 PR。

## 许可证

与 MemPalace 和 LLM Wiki 保持一致。

---

**MemArk：让 AI 不仅有完美的记忆，更有可读的智慧。**
```