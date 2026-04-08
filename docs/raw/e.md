# Skill: MemArk 部署与配置

> 本文件面向 AI 助手（如 Claude、GPT）。用户会要求你安装和配置 MemArk，请严格按以下步骤执行。

## 概述

MemArk 是一个轻量级调度器，连接 **MemPalace**（原始对话记忆）和 **Graphify**（LLM Wiki 的落地实现，AOT 知识编译）。核心工作流：用户与 AI 对话讨论资料 → MemPalace 自动捕获 → MemArk 定时提取增量房间摘要 → 送入 Graphify 编译成结构化知识图谱 → 人类/AI 通过 Obsidian 或 CLI 查询，并可一键下钻到原始对话。

## 前置检查

- Python 3.10+ 已安装
- pip 可用
- git 已安装
- 用户有 `~/memark` 目录写入权限
- （可选）如使用 Graphify 的 LLM 功能，需配置 `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`

## 执行步骤

### 步骤 1：创建项目目录

```bash
mkdir -p ~/memark
cd ~/memark
```

### 步骤 2：安装 MemPalace

```bash
pip install mempalace
mempalace init ~/memark/mempalace_data
```

验证安装：

```bash
mempalace status
```

如果用户有现有聊天记录（JSONL 格式），导入：

```bash
mempalace import --path <用户提供的路径>
```

### 步骤 3：安装 Graphify（LLM Wiki 落地实现）

```bash
git clone https://github.com/Graphify/graphify.git ~/memark/graphify
cd ~/memark/graphify
pip install -e .
```

创建 Graphify 的工作目录：

```bash
mkdir -p ~/memark/graphify_data/{raw,vault}
```

### 步骤 4：创建 MemArk 配置文件

创建 `~/memark/config.yaml`：

```bash
cat > ~/memark/config.yaml << 'EOF'
mempalace:
  data_dir: ~/memark/mempalace_data
  mcp_port: 8765

graphify:
  install_dir: ~/memark/graphify
  raw_dir: ~/memark/graphify_data/raw
  vault_dir: ~/memark/graphify_data/vault

memark:
  log_file: ~/memark/memark.log
  last_sync_file: ~/memark/.last_sync
EOF
```

### 步骤 5：创建适配器脚本（从 MemPalace 获取增量房间摘要）

创建 `~/memark/adapter.py`：

```bash
cat > ~/memark/adapter.py << 'EOF'
#!/usr/bin/env python3
"""
MemArk Adapter
从 MemPalace MCP 获取增量房间摘要，转换为 Graphify 接受的 Markdown 格式。
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

CONFIG_PATH = Path.home() / "memark/config.yaml"

def load_config():
    import yaml
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

def get_last_sync() -> str:
    config = load_config()
    last_file = Path(config["memark"]["last_sync_file"]).expanduser()
    if last_file.exists():
        return last_file.read_text().strip()
    return "1970-01-01T00:00:00Z"

def update_last_sync(timestamp: str):
    config = load_config()
    last_file = Path(config["memark"]["last_sync_file"]).expanduser()
    last_file.write_text(timestamp)

def fetch_incremental_rooms(last_ts: str) -> List[Dict[str, Any]]:
    """
    调用 MemPalace MCP 工具获取 timestamp > last_ts 的房间摘要。
    实际需通过 mempalace mcp call 或直接使用 mempalace 命令行。
    这里假设有一个命令 `mempalace list-rooms --since <timestamp>`。
    """
    try:
        result = subprocess.run(
            ["mempalace", "list-rooms", "--since", last_ts, "--format", "json"],
            capture_output=True,
            text=True,
            check=True
        )
        rooms = json.loads(result.stdout)
        return rooms
    except subprocess.CalledProcessError as e:
        print(f"Failed to fetch rooms: {e.stderr}", file=sys.stderr)
        return []
    except json.JSONDecodeError:
        print("Invalid JSON from mempalace", file=sys.stderr)
        return []

def convert_room_to_markdown(room: Dict[str, Any]) -> str:
    """
    将房间摘要转换为 Graphify 可接受的 Markdown 格式。
    Graphify 通常期望每个文档有标题、正文和元数据。
    这里保留下钻 ID 以便后续 drill 命令使用。
    """
    room_id = room.get("room_id") or room.get("id")
    title = room.get("title", f"Room {room_id}")
    summary = room.get("summary", "")
    timestamp = room.get("timestamp", datetime.now(timezone.utc).isoformat())
    
    md = f"# {title}\n\n"
    md += f"**Room ID:** `{room_id}`\n"
    md += f"**Last updated:** {timestamp}\n\n"
    md += f"{summary}\n\n"
    md += f"[^ref_{room_id}]: 原始对话 ID: {room_id}\n"
    return md

def sync():
    config = load_config()
    raw_dir = Path(config["graphify"]["raw_dir"]).expanduser()
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    last_ts = get_last_sync()
    print(f"Syncing rooms since {last_ts}")
    
    rooms = fetch_incremental_rooms(last_ts)
    if not rooms:
        print("No new rooms to sync.")
        return
    
    max_ts = last_ts
    for room in rooms:
        md_content = convert_room_to_markdown(room)
        safe_id = room.get("room_id", room.get("id", "unknown")).replace("/", "_").replace("\\", "_")
        out_file = raw_dir / f"{safe_id}.md"
        out_file.write_text(md_content)
        room_ts = room.get("timestamp", "")
        if room_ts > max_ts:
            max_ts = room_ts
        print(f"  Wrote {out_file}")
    
    update_last_sync(max_ts)
    print(f"Sync completed. Updated last_sync to {max_ts}")

if __name__ == "__main__":
    sync()
EOF

chmod +x ~/memark/adapter.py
```

### 步骤 6：创建 MemArk CLI

创建 `~/memark/memark.py`：

```bash
cat > ~/memark/memark.py << 'EOF'
#!/usr/bin/env python3
"""
MemArk CLI - 统一入口
"""

import subprocess
import sys
import argparse
import yaml
from pathlib import Path

HOME = Path.home()
MEMARK_DIR = HOME / "memark"
CONFIG_PATH = MEMARK_DIR / "config.yaml"

def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

def cmd_sync():
    """同步：从 MemPalace 获取增量房间摘要 → 转换 → 触发 Graphify 编译"""
    print("🔄 MemArk sync started")
    # 1. 运行适配器
    adapter = MEMARK_DIR / "adapter.py"
    result = subprocess.run([sys.executable, str(adapter)], capture_output=False)
    if result.returncode != 0:
        print("❌ Adapter failed", file=sys.stderr)
        return False
    
    # 2. 触发 Graphify 编译（假设 graphify 提供了 build 命令）
    config = load_config()
    graphify_bin = Path(config["graphify"]["install_dir"]) / "graphify"
    raw_dir = Path(config["graphify"]["raw_dir"]).expanduser()
    vault_dir = Path(config["graphify"]["vault_dir"]).expanduser()
    
    try:
        subprocess.run(
            [str(graphify_bin), "build", "--input", str(raw_dir), "--output", str(vault_dir)],
            check=True,
            capture_output=False
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Graphify build failed: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        # 如果 graphify 没有独立二进制，尝试用 python 模块
        subprocess.run(
            [sys.executable, "-m", "graphify", "build", "--input", str(raw_dir), "--output", str(vault_dir)],
            check=True
        )
    
    print("✅ Sync completed")
    return True

def cmd_query(query_str: str):
    """查询：优先从 Graphify vault 检索，必要时提示下钻"""
    config = load_config()
    vault_dir = Path(config["graphify"]["vault_dir"]).expanduser()
    if not vault_dir.exists():
        print("Vault not built yet. Run 'memark sync' first.")
        return
    
    # 简单实现：使用 grep 或 ripgrep 搜索
    try:
        result = subprocess.run(
            ["grep", "-r", "-i", "--color=never", query_str, str(vault_dir)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            print("📖 Found in knowledge vault:\n")
            print(result.stdout[:2000])
            print("\n💡 To see original conversation, use: memark drill <room_id>")
            return
    except FileNotFoundError:
        pass
    
    print("No results in vault. Try: memark drill <room_id> to search memory directly.")

def cmd_drill(room_id: str):
    """下钻：调用 MemPalace MCP 获取原始对话"""
    print(f"🔍 Fetching original conversation for room: {room_id}")
    # 假设 mempalace 提供 get-room 命令
    try:
        subprocess.run(
            ["mempalace", "get-room", "--id", room_id, "--include-drawers"],
            check=False
        )
    except FileNotFoundError:
        print("Please ensure mempalace is installed and MCP server is running.")
        print("You can start MCP server with: memark serve")

def cmd_serve():
    """启动 MemPalace MCP 服务器"""
    config = load_config()
    port = config["mempalace"]["mcp_port"]
    print(f"Starting MemPalace MCP server on port {port}...")
    subprocess.run(["mempalace", "mcp", "serve", "--port", str(port)])

def cmd_upgrade():
    """升级组件"""
    subprocess.run(["pip", "install", "--upgrade", "mempalace"])
    subprocess.run(["pip", "install", "--upgrade", "-e", str(MEMARK_DIR / "graphify")])
    print("Upgraded MemPalace and Graphify.")

def main():
    parser = argparse.ArgumentParser(description="MemArk - AI Second Brain")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    subparsers.add_parser("sync", help="Sync incremental rooms and build knowledge graph")
    subparsers.add_parser("serve", help="Start MemPalace MCP server")
    subparsers.add_parser("upgrade", help="Upgrade components")
    
    query_parser = subparsers.add_parser("query", help="Query knowledge vault")
    query_parser.add_argument("query", type=str)
    
    drill_parser = subparsers.add_parser("drill", help="Drill down to original conversation")
    drill_parser.add_argument("room_id", type=str)
    
    args = parser.parse_args()
    
    if args.command == "sync":
        cmd_sync()
    elif args.command == "query":
        cmd_query(args.query)
    elif args.command == "drill":
        cmd_drill(args.room_id)
    elif args.command == "serve":
        cmd_serve()
    elif args.command == "upgrade":
        cmd_upgrade()

if __name__ == "__main__":
    main()
EOF

chmod +x ~/memark/memark.py
```

### 步骤 7：安装 Python 依赖

```bash
pip install pyyaml
```

### 步骤 8：设置全局命令别名

```bash
echo 'alias memark="python3 ~/memark/memark.py"' >> ~/.bashrc
echo 'alias memark="python3 ~/memark/memark.py"' >> ~/.zshrc 2>/dev/null
source ~/.bashrc 2>/dev/null || source ~/.zshrc 2>/dev/null

# 也可创建软链接
sudo ln -sf ~/memark/memark.py /usr/local/bin/memark
```

### 步骤 9：首次同步与验证

```bash
cd ~/memark
memark sync
```

预期输出类似：
```
🔄 MemArk sync started
Syncing rooms since 1970-01-01T00:00:00Z
  Wrote /home/user/memark/graphify_data/raw/room_xxx.md
Sync completed. Updated last_sync to 2025-03-15T10:30:00Z
✅ Sync completed
```

检查生成的文件：

```bash
ls ~/memark/graphify_data/raw/
ls ~/memark/graphify_data/vault/
```

### 步骤 10：测试查询和下钻

```bash
memark query "测试关键词"
memark drill room_xxx
```

### 步骤 11：设置自动定时同步（可选）

```bash
(crontab -l 2>/dev/null; echo "0 * * * * /usr/local/bin/memark sync >> /home/$USER/memark/memark.log 2>&1") | crontab -
```

## 完成标志

执行完所有步骤后，向用户报告：

```
✅ MemArk 安装完成！

三层架构已就绪：
- MemPalace 数据目录: ~/memark/mempalace_data
- Graphify 工作目录: ~/memark/graphify_data
- MemArk CLI: memark {sync|query|drill|serve|upgrade}

📁 知识图谱 Vault 位置: ~/memark/graphify_data/vault
   可用 Obsidian 打开此文件夹浏览结构化知识。

🔧 命令示例：
   memark sync            # 增量同步并编译知识图谱
   memark query "问题"    # 搜索知识图谱
   memark drill <room_id> # 下钻到原始对话
   memark serve           # 启动 MCP 服务器（供外部 AI 调用）

📝 推荐工作流：
   1. 与 AI 对话讨论资料（论文、文章等），MemPalace 自动记录
   2. 每小时自动同步（或手动运行 memark sync），知识自动编译
   3. 在 Obsidian 中浏览不断生长的知识网络
   4. 需要溯源时，点击引用链接或使用 memark drill

🚀 享受 MemArk 带来的“对话即知识”自动化飞轮！
```

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| `mempalace: command not found` | 重新安装：`pip install --force-reinstall mempalace` |
| `mempalace list-rooms --since` 命令不存在 | MemPalace 可能使用不同接口，请参考其文档；可临时修改 `adapter.py` 中的 `fetch_incremental_rooms` 实现（如直接读取 SQLite） |
| Graphify `build` 命令未找到 | 确认 Graphify 安装成功，尝试 `python -m graphify build --help` |
| 增量同步无新房间 | 检查 MemPalace 中是否有新对话，且对话已生成房间摘要（可能需要运行 `mempalace process`） |
| 下钻 drill 无响应 | 确保 MemPalace MCP 服务器已启动：`memark serve` |
| 端口 8765 冲突 | 修改 `config.yaml` 中的 `mcp_port` |

## 备注

- 本 Skill 设计为一次性执行。用户后续可手动运行 `memark sync` 或依赖定时任务。
- Graphify 的编译可能需要 LLM API 密钥（如 OpenAI），请确保环境变量已设置。
- 如果用户没有现成的 MemPalace 房间摘要，适配器可能返回空；可先用 `mempalace import` 导入聊天记录，再等待 MemPalace 自动生成摘要（或运行其处理命令）。