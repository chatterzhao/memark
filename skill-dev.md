---
name: memark-installer-dev
description: Development-stage installer skill for isolated fake-HOME reset, repeatable MemArk install verification, and non-interactive end-to-end testing.
---

# MemArk Installer Skill (Dev)

开发阶段入口，用于隔离环境下的反复安装验证。正式用户入口是 [`SKILL.md`](<repo-root>/SKILL.md)。

## 平台支持

当前仅支持 **macOS**。

## Dev 执行目标

1. 清理并重建 `.venv-dev/`
2. 以 `-e .[dev]` 安装当前仓库
3. 准备假 `HOME` 与 `MEMARK_HOME`
4. 运行 `python -m memark install`
5. 运行安装后 launcher 的 `memark doctor`
6. 验证 bundle、launcher、manifest、上游 CLI 都存在

## Dev 推荐命令

```bash
rm -rf .venv-dev /tmp/memark-skill-dev
python3 -m venv .venv-dev
.venv-dev/bin/python -m pip install --upgrade pip
.venv-dev/bin/python -m pip install -e '.[dev]'
mkdir -p /tmp/memark-skill-dev/home
HOME=/tmp/memark-skill-dev/home \
MEMARK_HOME=/tmp/memark-skill-dev/home/.memark \
  .venv-dev/bin/python -m memark install \
  --platform codex \
  --memark-home /tmp/memark-skill-dev/home/.memark \
  --source-spec "$(pwd)"
HOME=/tmp/memark-skill-dev/home \
  /tmp/memark-skill-dev/home/.agents/skills/memark/bin/memark doctor --platform codex
```

## Dev 验收标准

- `.venv-dev/` 存在
- 假 `HOME` 下存在 `.memark/venv/`
- 假 `HOME` 下存在 `.agents/skills/memark/` 或 `.claude/skills/memark/`
- `manifest.json` 存在
- `bin/memark` 可执行
- `doctor` 返回成功
- runtime 内存在：`memark`、`mempalace`、`graphify`

## 防止测试泄漏 launchd 服务

测试中设置 `MEMARK_SKIP_SERVICE=1` 可阻止 `memark init` 安装真实的 launchd 服务。

## 与正式入口的关系

- [`SKILL.md`](<repo-root>/SKILL.md) 面向用户机器上的正式安装
- [`skill-dev.md`](<repo-root>/skill-dev.md) 面向开发期隔离验证
- 两者都只负责安装与验证，项目接入用 `memark init`
