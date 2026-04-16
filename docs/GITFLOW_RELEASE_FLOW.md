# Gitflow Release Flow

本文件定义当前仓库唯一正式的 Gitflow 发布流程真源。

它回答四个问题：

1. 什么时候可以从 `develop` 发版
2. `develop`、`main`、`tag` 各自承担什么职责
3. 版本号从哪里读取，tag 应该怎么命名
4. 具体应该按什么顺序执行 `push`、`merge`、`tag`

## 角色分工

- `develop`
  - 功能主线
  - 所有 feature branch 最终先合并到这里
  - 日常 dogfood、修复、文档收敛先在这里完成
- `main`
  - 发布主线
  - 只接收已经准备对外说明或内部稳定分发的 `develop`
  - 不承接日常 feature 开发
- annotated tag
  - 发布锚点
  - 只打在 `main` 的发布提交上
  - 不打在 feature branch，也不打在未发布的 `develop` 提交上

## 版本与 Tag 规则

当前仓库版本真源是：

- [`pyproject.toml`](<repo-root>/pyproject.toml) 中的 `project.version`

当前 tag 规则是：

- 使用 `v<version>` 形式
- 例如 `pyproject.toml` 是 `0.1.0`，则发布 tag 是 `v0.1.0`

要求：

- 发布前先确认 `pyproject.toml` 中的版本号已经是这次准备发布的版本
- 不要打与 `pyproject.toml` 不一致的 tag
- 不要在同一版本号上重复打多个不同提交的 tag

## 发布前置条件

在走 Gitflow 发布动作前，必须先满足：

1. [`docs/RELEASE_CHECKLIST.md`](<repo-root>/docs/RELEASE_CHECKLIST.md) 的发布检查已经通过
2. `develop` 工作树是干净的
3. 所有要进入这次发布的 feature branch 都已经被 `develop` 吸收
4. 不把 `dogfood/runtime` 或 research worktree 的本地运行产物带进发布提交

## 正式发布顺序

当前仓库正式发布时，按下面顺序执行：

1. 在 `develop` 完成最终验证
2. `git push origin develop`
3. 切到 `main`
4. `git merge --no-ff develop`
5. 在合并后的 `main` 提交上创建 annotated tag
6. `git push origin main`
7. `git push origin <tag>`

推荐命令模板：

```bash
cd <repo-root>
git checkout develop
git status --short

# 确认发布前检查已通过后
git push origin develop

git checkout main
git merge --no-ff develop

VERSION="$(python3 - <<'PY'
import tomllib
from pathlib import Path
data = tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))
print(data['project']['version'])
PY
)"

git tag -a "v${VERSION}" -m "Release v${VERSION}"
git push origin main
git push origin "v${VERSION}"

git checkout develop
```

## 首次对齐 `main` 的特例

如果当前仓库的 `main` 仍是初始化壳提交，而 `develop` 已经承载了实际工作历史，可能会出现：

- `git merge-base main develop` 为空
- 普通 `git merge develop` 报 `refusing to merge unrelated histories`

这种情况下，允许在首次把 `develop` 正式提升到 `main` 时执行一次：

```bash
git merge --no-ff --allow-unrelated-histories develop
```

约束：

- 这只是把历史壳 `main` 与真实主线 `develop` 对齐的一次性动作
- 完成后，后续发布恢复为普通 `git merge --no-ff develop`
- 不要把 `--allow-unrelated-histories` 当成日常发布默认参数

## 什么时候需要改版本号

如果这次发布代表新的对外版本，就应先更新：

- [`pyproject.toml`](<repo-root>/pyproject.toml)
- 如有需要，再同步更新 README 或发布说明中的显式版本文本

如果只是把当前未发布主线第一次整理到 `main`，且 `pyproject.toml` 当前版本尚未被正式打 tag，则可以直接按当前版本发出第一枚 tag。

## 文档分工

为了避免重复，其他文档只承担各自职责：

- [`docs/RELEASE_CHECKLIST.md`](<repo-root>/docs/RELEASE_CHECKLIST.md)
  - 只定义“能不能发布”的检查项
  - 不重复写完整 Gitflow 命令顺序
- [`docs/DOGFOOD_RUNBOOK.md`](<repo-root>/docs/DOGFOOD_RUNBOOK.md)
  - 只定义持续 dogfood 的运行与排障
  - 不承担正式发版流程真源
- [`README.md`](<repo-root>/README.md)
  - 可以提示维护者去哪里看发布流程
  - 不展开完整 Gitflow 细节
- [`AGENTS.md`](<repo-root>/AGENTS.md)
  - 继续只定义 worktree / branch 基本规则
  - 不复制发布细则

## 当前仓库的发布定义

对当前仓库来说，“发布成功”的最小判定是：

1. `develop` 已包含这次准备发布的内容并已 push
2. `main` 已 merge `develop` 并已 push
3. 对应版本 annotated tag 已创建并 push

只有这三条同时满足，才应把一次 Gitflow 发布动作视为完成。
