以下是完整的 `skill.md` 文件，AI 可据此自动安装和配置 MemArk、MemPalace 和 LLM Wiki。

```markdown
# MemArk 安装配置 Skill

> 本文件面向 AI 助手（如 Claude、GPT）。用户会要求你安装和配置 MemArk，请严格按以下步骤执行。

## 概述

MemArk 是融合 MemPalace 和 LLM Wiki 的统一项目。你的任务是：**自动完成 MemArk、MemPalace、LLM Wiki 三个组件的安装、配置和初始同步**。

## 前置检查

在执行任何操作前，先确认：
- Python 3.10+ 已安装
- pip 可用
- git 已安装（如果需要克隆仓库）
- 用户有 `~/memark` 目录的写入权限

## 执行步骤

### 步骤 1：创建项目目录

```bash
mkdir -p ~/memark
cd ~/memark
```

### 步骤 2：安装 MemPalace

MemPalace 负责收集和存储原始对话（JSONL）。

```bash
# 安装 mempalace Python 包
pip install mempalace

# 初始化 MemPalace 数据库（使用默认配置）
mempalace init ~/memark/mempalace_data

# 验证安装
mempalace status
```

如果用户有现成的聊天记录导出文件（JSONL 格式），询问路径后导入：

```bash
mempalace import --path <用户提供的路径>
```

### 步骤 3：安装 LLM Wiki

LLM Wiki 负责将原始资料编译成 Markdown 维基。由于目前没有官方 Python 包，我们创建标准目录结构。

```bash
# 创建 LLM Wiki 目录结构
mkdir -p ~/memark/llm_wiki/{raw,wiki}

# 创建基础配置文件 CLAUDE.md
cat > ~/memark/llm_wiki/CLAUDE.md << 'EOF'
# LLM Wiki 配置

## 职责
将 `raw/` 文件夹中的 Markdown 文件编译成结构化的维基知识库，输出到 `wiki/` 文件夹。

## 编译规则
1. 读取 `raw/` 下的所有 .md 文件
2. 提取核心概念、实体和关系
3. 为每个重要概念生成独立的 wiki 页面
4. 添加双向链接 `[[概念]]`
5. 保留原始引用标记 `[^ref_xxx]` 用于下钻

## 输出格式
- 文件：`wiki/<概念名>.md`
- 内容：概念定义、相关对话摘要、反向链接、原始引用
EOF
```

### 步骤 4：配置 MemArk 核心

创建 `~/memark/config.yaml`：

```bash
cat > ~/memark/config.yaml << 'EOF'
# MemArk 配置文件
mempalace:
  data_dir: ~/memark/mempalace_data
  mcp_port: 8765

llm_wiki:
  root_dir: ~/memark/llm_wiki
  raw_dir: ~/memark/llm_wiki/raw
  wiki_dir: ~/memark/llm_wiki/wiki

memark:
  log_file: ~/memark/memark.log
EOF
```

### 步骤 5：创建适配器脚本（JSONL → Markdown）

创建 `~/memark/adapter.py`：

```bash
cat > ~/memark/adapter.py << 'EOF'
#!/usr/bin/env python3
"""将 MemPalace 导出的 JSONL 转换为 LLM Wiki 需要的 Markdown 格式"""

import json
import sys
from pathlib import Path

def convert_jsonl_to_markdown(jsonl_path: Path, output_dir: Path):
    """读取 JSONL 文件，每个对话生成一个 Markdown 文件"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                conv = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Warning: line {line_num} is not valid JSON: {e}", file=sys.stderr)
                continue
            
            # 提取对话 ID 和消息
            conv_id = conv.get('conversation_id') or conv.get('id') or f"conv_{line_num}"
            messages = conv.get('messages') or conv.get('conversation') or []
            
            # 构建 Markdown 内容
            md_lines = [
                f"# Conversation {conv_id}\n",
                f"**Original ID:** {conv_id}\n",
                f"[^ref_{conv_id}]: 原始记录 ID: {conv_id}\n\n"
            ]
            
            for msg in messages:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                # 处理可能的嵌套内容
                if isinstance(content, list):
                    content = ' '.join(str(c) for c in content)
                md_lines.append(f"**{role}:** {content}\n\n")
            
            # 保存 Markdown 文件
            safe_name = conv_id.replace('/', '_').replace('\\', '_')
            md_path = output_dir / f"{safe_name}.md"
            md_path.write_text(''.join(md_lines), encoding='utf-8')
            print(f"Converted {conv_id} -> {md_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: adapter.py <input.jsonl> <output_raw_dir>")
        sys.exit(1)
    convert_jsonl_to_markdown(Path(sys.argv[1]), Path(sys.argv[2]))
EOF

chmod +x ~/memark/adapter.py
```

### 步骤 6：创建 MemArk CLI

创建 `~/memark/memark.py`：

```bash
cat > ~/memark/memark.py << 'EOF'
#!/usr/bin/env python3
"""MemArk 统一命令行工具"""

import subprocess
import sys
import os
from pathlib import Path

# 配置路径
HOME = Path.home()
MEMARK_DIR = HOME / "memark"
CONFIG_PATH = MEMARK_DIR / "config.yaml"
ADAPTER = MEMARK_DIR / "adapter.py"

def load_config():
    import yaml
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

def sync():
    """从 MemPalace 导出对话 → 转换 → 放入 raw/"""
    config = load_config()
    raw_dir = Path(config["llm_wiki"]["raw_dir"]).expanduser()
    export_file = MEMARK_DIR / "temp_export.jsonl"
    
    # 1. 尝试从 MemPalace 导出
    # 注意：mempalace export 命令可能因版本不同而不同，这里使用通用方式
    # 假设 mempalace 提供了导出功能
    try:
        subprocess.run(["mempalace", "export", "--output", str(export_file)], 
                       check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("Warning: mempalace export failed. Please ensure mempalace is installed and has data.", file=sys.stderr)
        # 如果没有导出命令，尝试从数据库直接读取？这里先创建示例文件
        print("Creating example raw file for testing...")
        example_md = raw_dir / "example.md"
        example_md.write_text("# Example Conversation\n\nThis is a placeholder. Please import real chat data using `mempalace import`.")
        print(f"Created {example_md}")
        return
    
    # 2. 运行适配器
    if export_file.exists():
        subprocess.run([sys.executable, str(ADAPTER), str(export_file), str(raw_dir)], check=True)
        export_file.unlink()
    else:
        print("No export file generated.")
    
    print(f"Sync completed. Raw files are in {raw_dir}")
    print("Next step: Ask an AI to compile the raw files into wiki/ using LLM Wiki methodology.")

def query(question: str):
    """查询知识：先查 wiki 目录，若无结果则提示使用 mempalace mcp"""
    config = load_config()
    wiki_dir = Path(config["llm_wiki"]["wiki_dir"]).expanduser()
    
    if wiki_dir.exists():
        # 使用 grep 或 ripgrep 搜索
        try:
            result = subprocess.run(["grep", "-r", "-i", question, str(wiki_dir)], 
                                    capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                print("=== Wiki Results ===")
                print(result.stdout)
                return
        except FileNotFoundError:
            pass
    
    # 如果 wiki 没有结果或不存在，提示使用 MCP
    print("No results found in Wiki knowledge base.")
    print("You can start MemPalace MCP server with: memark serve --mcp")
    print("Then connect your AI to query historical memory directly.")

def serve_mcp():
    """启动 MemPalace 的 MCP 服务器"""
    config = load_config()
    port = config["mempalace"]["mcp_port"]
    print(f"Starting MemPalace MCP server on port {port}...")
    # 假设 mempalace 提供了 mcp serve 命令
    subprocess.run(["mempalace", "mcp", "serve", "--port", str(port)])

def upgrade():
    """升级组件"""
    subprocess.run(["pip", "install", "--upgrade", "mempalace"])
    print("MemPalace upgraded.")
    print("LLM Wiki is a concept; no automated upgrade. Please check for updates manually.")

def main():
    if len(sys.argv) < 2:
        print("Usage: memark {init|sync|query|serve|upgrade}")
        print("  init      - Initialize directories (already done during install)")
        print("  sync      - Export MemPalace data, convert, and populate raw/")
        print("  query     - Search wiki for answer")
        print("  serve     - Start MCP server for MemPalace")
        print("  upgrade   - Upgrade MemPalace")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "init":
        print("MemArk already initialized. Run 'memark sync' to start.")
    elif cmd == "sync":
        sync()
    elif cmd == "query":
        if len(sys.argv) < 3:
            print("Please provide a query string.")
            sys.exit(1)
        query(" ".join(sys.argv[2:]))
    elif cmd == "serve":
        serve_mcp()
    elif cmd == "upgrade":
        upgrade()
    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()
EOF

chmod +x ~/memark/memark.py
```

### 步骤 7：安装 Python 依赖（yaml）

```bash
pip install pyyaml
```

### 步骤 8：设置 PATH 别名（可选）

为了在任何目录下都能使用 `memark` 命令：

```bash
echo 'alias memark="python3 ~/memark/memark.py"' >> ~/.bashrc
# 如果使用 zsh
echo 'alias memark="python3 ~/memark/memark.py"' >> ~/.zshrc
source ~/.bashrc 2>/dev/null || source ~/.zshrc 2>/dev/null
```

### 步骤 9：首次同步

```bash
cd ~/memark
python3 memark.py sync
```

### 步骤 10：验证安装

```bash
# 检查 MemPalace 状态
mempalace status

# 检查 raw 目录是否有文件生成
ls -la ~/memark/llm_wiki/raw/

# 测试查询命令
memark query "test"
```

## 常见问题及处理

| 问题 | 解决方法 |
|------|----------|
| `mempalace: command not found` | 确保 pip 安装的包在 PATH 中，或使用 `python -m mempalace` |
| MemPalace 没有 `export` 命令 | 当前版本可能不支持导出。可以指导用户手动将数据库内容导出为 JSONL，或使用 `mempalace dump` 等替代命令。如果不行，创建示例文件让用户理解流程 |
| `adapter.py` 转换失败 | 检查 JSONL 的实际结构，修改 adapter 中的字段映射（`conversation_id`, `messages` 等） |
| LLM Wiki 没有自动编译 | 这是预期行为。LLM Wiki 需要 AI 手动编译。告诉用户：请 AI 读取 `~/memark/llm_wiki/raw/` 并按照 `CLAUDE.md` 的规则生成 `wiki/` 目录 |
| 端口 8765 被占用 | 修改 `config.yaml` 中的 `mcp_port` 为其他端口 |

## 完成标志

执行完所有步骤后，向用户报告以下信息：

```
✅ MemArk 安装完成！

📁 目录结构：
   - MemPalace 数据: ~/memark/mempalace_data
   - LLM Wiki raw:   ~/memark/llm_wiki/raw
   - LLM Wiki wiki:  ~/memark/llm_wiki/wiki

🔧 可用命令：
   memark sync          # 同步 MemPalace 数据到 raw/
   memark query "问题"  # 搜索 wiki 知识库
   memark serve         # 启动 MCP 服务器（供 AI 查询历史记忆）

📝 下一步：
   1. 导入你的聊天记录: mempalace import --path <file.jsonl>
   2. 运行 memark sync 生成原始 Markdown
   3. 让 AI 读取 raw/ 并编译为 wiki/（参考 CLAUDE.md）
   4. 用 Obsidian 打开 wiki/ 浏览知识网络

🚀 享受 MemArk 带来的 AI 第二大脑！
```

## 备注

- 本 skill 设计为**一次性执行**。如果用户后续需要更新配置，可以重新运行相关步骤。
- LLM Wiki 的编译依赖 AI（如 Claude、GPT）。如果用户希望自动化编译，可以后续集成 LangChain 或其他编排工具。
- MemPalace 的 MCP 服务器是独立进程，可以常驻后台供外部 AI Agent 调用。
```

以上就是完整的 `skill.md`，AI 可以逐条执行命令完成安装配置。