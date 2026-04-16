# MemArk 文档评审报告

> 评审员: Qwen
> 评审范围: `docs/a.md` ~ `docs/f.md`（6 个新增文档文件）

---

## Summary

本次评审覆盖了 6 个新增文档文件，内容包含 MemArk 系统的部署指南、Python CLI 脚本示例、YAML 配置和架构说明。文档描述了 MemPalace（记忆存储）和 LLM Wiki / Graphify（知识编译）两个不同后端的集成方案。

**核心问题**：文档存在两套互不兼容的架构（LLM Wiki vs Graphify）、YAML 路径 `~` 不会被自动展开导致所有文件操作失败、多个外部命令接口纯属假设而未验证。这些问题会导致用户按文档操作时无法完成安装。

**统计**：共发现 15 个问题，经逐一代码验证后全部确认。

---

## Critical — 必须修复

### 1. YAML 配置中的 `~` 路径不会被展开

**文件:** `docs/a.md`（memark.py 配置加载段）、`docs/b.md`、`docs/e.md`

**问题:** YAML 文件中写入的 `~/memark/mempalace_data` 等路径，`yaml.safe_load()` 会当作字面字符串处理，不会执行 shell 的 `~` 展开。a.md 中的 `memark.py` **完全没有调用 `.expanduser()`**，b.md 和 e.md 仅部分调用。

**影响:** 所有文件读写操作会失败，因为路径是字面的 `"~/memark/..."` 而非 `~/memark/...`。

**建议修复:**
```python
# 在 load_config() 中统一展开
def load_config():
    config = yaml.safe_load(CONFIG_FILE.read_text())
    # 对所有路径值调用 expanduser
    for section in config:
        if isinstance(config[section], dict):
            for key, val in config[section].items():
                if isinstance(val, str) and val.startswith('~'):
                    config[section][key] = str(Path(val).expanduser())
    return config
```

---

### 2. README 引用了不存在的 `skill.md` 文件

**文件:** `docs/a.md`、`docs/c.md`

**问题:** 多处 README 写明「把本目录下的 `skill.md` 文件交给 AI 助手」，但实际目录中不存在名为 `skill.md` 的文件。Skill 内容分散在 a.md、b.md、e.md 中。

**影响:** 用户按 README 指引找不到 `skill.md`。

**建议修复:** 将规范的 Skill 文件重命名为 `skill.md`，或更新所有 README 中的引用指向正确的文件名。

---

### 3. 两套互不兼容的架构并存

**文件:** `docs/a.md`/`b.md`/`c.md`（LLM Wiki 后端） vs `docs/d.md`/`e.md`/`f.md`（Graphify 后端）

**问题:** 两组文档描述了完全不同的技术栈：
- 目录结构：`llm_wiki/{raw,wiki}` vs `graphify_data/{raw,vault}`
- 配置 key：`llm_wiki` vs `graphify`
- 数据流：全量 JSONL 转换 vs 增量房间摘要
- 编译命令：`compile.py` vs `graphify build`

没有任何版本标识或迁移说明。

**影响:** 用户跟随不同文档会搭建出互不兼容的系统。

**建议修复:** 明确标注版本（如「v1: LLM Wiki」、「v2: Graphify」），或合并为单一权威文档并以后端可配置的方式抽象差异。

---

### 4. 外部命令接口纯属假设，未经验证

**文件:** `docs/a.md`（`mempalace export --format jsonl --days 7`）、`docs/e.md`（`mempalace list-rooms --since`、`graphify build`）

**问题:** 文档中大量调用外部命令，但接口完全是假设的，代码注释自己也承认「这里假设有一个命令」。不同文件对同一命令的假设也不一致（如 `mempalace export` 在 a.md 和 b.md 中参数完全不同）。

**影响:** 整个同步/查询/下钻流程会在第一次外部调用时中断。

**建议修复:** 定义正式的外部工具接口契约（如 Python ABC 或 OpenAPI），或明确标注为「假设接口，尚未实现」并提供 mock/stub 替代方案。

---

### 5. Crontab 覆盖式写入会丢失用户已有定时任务

**文件:** `docs/d.md`、`docs/f.md`

**问题:** `echo "0 * * * * ..." | crontab -` 会**替换整个 crontab**，删除用户所有已有的 cron 任务。

**影响:** 数据丢失——用户的备份、监控等其他定时任务被清除。

**建议修复:** 使用追加模式：
```bash
(crontab -l 2>/dev/null | grep -v "memark sync"; echo "0 * * * * /usr/local/bin/memark sync") | crontab -
```

---

## Suggestion — 建议修复

### 6. 用户查询直接作为 grep 正则表达式，存在 ReDoS 风险

**文件:** `docs/a.md`（`cmd_query`）、`docs/b.md`（`query`）、`docs/e.md`（`cmd_query`）

**问题:** `["grep", "-r", "-i", query, str(wiki_dir)]` 中 `query` 被当作正则表达式解析。用户输入 `.*(.*` 会报错，`a{10000}` 会导致 CPU 耗尽。

**影响:** 安全漏洞 + 潜在的性能拒绝服务。

**建议修复:** 使用 `grep -F` 进行固定字符串匹配：
```python
["grep", "-F", "-r", "-i", query, str(wiki_dir)]
```

---

### 7. JSONL 解析无容错，单行错误导致全量失败

**文件:** `docs/a.md`（`cmd_sync`）

**问题:** `conversations = [json.loads(line) for line in result.stdout.strip().split('\n')]` 没有任何 try/except。一行非法 JSON 就会中断整个同步。

**影响:** 同步操作脆弱——一条坏数据丢失所有有效对话。

**建议修复:** 参考 b.md 的做法，逐行 try/except 跳过错误行：
```python
for line in result.stdout.splitlines():
    if not line.strip():
        continue
    try:
        conv = json.loads(line)
    except json.JSONDecodeError:
        continue
```

---

### 8. Wiki/Graphify 编译步骤未检查返回值，静默失败

**文件:** `docs/a.md`（`cmd_sync`）、`docs/e.md`（`cmd_sync`）

**问题:** `subprocess.run(["python", ..., "compile.py"])` 没有 `check=True`，也没有检查 `returncode`，无论成功失败都打印「✅ 同步完成」。

**影响:** 编译实际失败但用户误以为成功。

**建议修复:**
```python
result = subprocess.run([...], capture_output=True, text=True)
if result.returncode != 0:
    print(f"编译失败: {result.stderr}")
    return False
```

---

### 9. `/usr/local/bin/` 软链接无 `sudo` 会静默失败

**文件:** `docs/a.md`（Step 7）、`docs/e.md`（Step 8）

**问题:** `ln -sf ~/memark/memark.py /usr/local/bin/memark` 在大多数系统上需要 root 权限，非 root 用户执行会失败且无提示。

**影响:** `memark` 命令无法全局使用。

**建议修复:** 使用用户可写路径或加 `sudo` 提示：
```bash
ln -sf ~/memark/memark.py ~/.local/bin/memark
```

---

### 10. Crontab 重复安装产生重复任务

**文件:** `docs/a.md`（Step 8）、`docs/e.md`（Step 11）

**问题:** `(crontab -l 2>/dev/null; echo "...") | crontab -` 每次执行都追加。重复运行安装脚本会创建多个相同的 cron 条目。

**影响:** 同步任务并发执行，可能竞争 `.last_sync` 文件和 raw 目录。

**建议修复:** 先过滤掉已有条目再追加（见 Critical #5 的修复）。

---

### 11. 文档命令与实际实现不一致

**文件:** `docs/a.md`、`docs/b.md`、`docs/c.md` 的命令参考表

**问题:** 文档列出了 `memark status`、`memark init`、`memark upgrade --all` 等命令，但没有任何一个实现文件包含这些命令的代码。

**影响:** 用户执行文档命令会得到「unknown command」错误。

**建议修复:** 对齐文档与实现，或补全缺失命令。

---

### 12. 增量同步时间戳缺失导致无限重同步

**文件:** `docs/e.md`（adapter.py `sync()`）

**问题:** 如果所有房间的 `timestamp` 字段缺失，`max_ts` 保持为 `"1970-01-01T00:00:00Z"`。下次同步会重新拉取全部房间。

**影响:** 重复内容和资源浪费。

**建议修复:** 无有效时间戳时，将 `max_ts` 设为当前时间：
```python
max_ts = last_ts if last_ts != "1970-01-01T00:00:00Z" else datetime.now(timezone.utc).isoformat()
```

---

## Nice to Have

### 13. 安装路径硬编码为 `~/memark`，不可配置

**文件:** 全部

**问题:** 所有路径硬编码为 `~/memark`，无法通过环境变量或参数自定义。

**影响:** 锁定单用户单路径安装，不支持多用户/容器化部署。

**建议修复:** 支持 `MEMARK_HOME` 环境变量或 `--config` 参数。

---

### 14. 文件名清洗不完整

**文件:** `docs/b.md`（adapter.py）、`docs/e.md`（adapter.py）

**问题:** `conv_id.replace('/', '_').replace('\\', '_')` 只处理了 `/` 和 `\`，其他危险字符（null 字节、超长字符串等）未处理。

**影响:** 异常 ID 可能导致文件写入失败或覆盖已有文件。

**建议修复:** 使用正则清洗或哈希命名：
```python
safe_name = re.sub(r'[^\w\-_.]', '_', conv_id)
```

---

### 15. GitHub 仓库 URL 可能不存在

**文件:** `docs/c.md`、`docs/f.md`（相关项目段）

**问题:** `github.com/milla-jovovich/mempalace`、`github.com/Graphify/graphify` 等 URL 可能不存在，clone 会 404。

**影响:** 安装流程在第一步就阻塞。

**建议修复:** 验证 URL 有效性，或标注为占位符。

---

## Verdict

**Request Changes** — 文档存在关键的配置路径展开、架构不一致、外部依赖未验证等问题，按当前文档操作无法完成有效安装。需修复上述 Critical 级问题后再合并。
