# Document Status

本文件定义当前仓库中文档的层级关系，避免把研究稿误当成正式说明。

## 最新设计入口

如果要理解当前最新口径，请先读下面几份文档：

- [`docs/PRODUCT_REQUIREMENTS.md`](<repo-root>/docs/PRODUCT_REQUIREMENTS.md)
- [`docs/MILESTONE_BETA.md`](<repo-root>/docs/MILESTONE_BETA.md)
- [`docs/MILESTONES.md`](<repo-root>/docs/MILESTONES.md)
- [`docs/MILESTONE_NEXT.md`](<repo-root>/docs/MILESTONE_NEXT.md)
- [`docs/RELEASE_CHECKLIST.md`](<repo-root>/docs/RELEASE_CHECKLIST.md)
- [`docs/DOGFOOD_RUNBOOK.md`](<repo-root>/docs/DOGFOOD_RUNBOOK.md)
- [`docs/DOGFOOD_LOG.md`](<repo-root>/docs/DOGFOOD_LOG.md)
- [`docs/AI_CONSUMPTION_MODEL.md`](<repo-root>/docs/AI_CONSUMPTION_MODEL.md)
- [`docs/AUTOMATION_CONSUMPTION_REQUIREMENTS.md`](<repo-root>/docs/AUTOMATION_CONSUMPTION_REQUIREMENTS.md)
- [`docs/DOGFOOD_STATUS.md`](<repo-root>/docs/DOGFOOD_STATUS.md)

其中：

- `PRODUCT_REQUIREMENTS.md` 定义产品需求边界
- `MILESTONE_BETA.md` 定义当前仓库自己吃自己的 Beta 里程碑与出站条件
- `MILESTONES.md` 作为阶段能力账本，汇总各里程碑已经做成的功能
- `MILESTONE_NEXT.md` 定义 Beta 之后下一条更合理的里程碑
- `RELEASE_CHECKLIST.md` 定义当前 Beta 口径对外说明前必须执行的发布检查
- `DOGFOOD_RUNBOOK.md` 定义当前仓库持续自己吃自己时的运维与排障入口
- `DOGFOOD_LOG.md` 记录按时间推进的真实 dogfood 证据
- `AI_CONSUMPTION_MODEL.md` 定义当前 AI 应如何消费这些产物
- `AUTOMATION_CONSUMPTION_REQUIREMENTS.md` 定义下一阶段“自动喂数据、自动加工、自动消费”的目标
- `DOGFOOD_STATUS.md` 定义哪些能力已经在当前仓库上真实吃过狗粮，哪些还只是测试通过

## 正式文档

以下文件是当前仓库的唯一权威入口：

- [`README.md`](<repo-root>/README.md)
- [`SKILL.md`](<repo-root>/SKILL.md)
- [`skill-dev.md`](<repo-root>/skill-dev.md)
- [`docs/PROJECT_SCOPE.md`](<repo-root>/docs/PROJECT_SCOPE.md)
- [`docs/GOVERNANCE_MODEL.md`](<repo-root>/docs/GOVERNANCE_MODEL.md)
- [`docs/INTERFACE_CONTRACT.md`](<repo-root>/docs/INTERFACE_CONTRACT.md)
- [`docs/PRODUCT_REQUIREMENTS.md`](<repo-root>/docs/PRODUCT_REQUIREMENTS.md)
- [`docs/MILESTONE_BETA.md`](<repo-root>/docs/MILESTONE_BETA.md)
- [`docs/MILESTONES.md`](<repo-root>/docs/MILESTONES.md)
- [`docs/MILESTONE_NEXT.md`](<repo-root>/docs/MILESTONE_NEXT.md)
- [`docs/RELEASE_CHECKLIST.md`](<repo-root>/docs/RELEASE_CHECKLIST.md)
- [`docs/DOGFOOD_RUNBOOK.md`](<repo-root>/docs/DOGFOOD_RUNBOOK.md)
- [`docs/DOGFOOD_LOG.md`](<repo-root>/docs/DOGFOOD_LOG.md)
- [`docs/FEATURE_LIST.md`](<repo-root>/docs/FEATURE_LIST.md)
- [`docs/AI_CONSUMPTION_MODEL.md`](<repo-root>/docs/AI_CONSUMPTION_MODEL.md)
- [`docs/AUTOMATION_CONSUMPTION_REQUIREMENTS.md`](<repo-root>/docs/AUTOMATION_CONSUMPTION_REQUIREMENTS.md)
- [`docs/DOGFOOD_STATUS.md`](<repo-root>/docs/DOGFOOD_STATUS.md)
- [`docs/CODEX_SESSION_INGEST_DESIGN.md`](<repo-root>/docs/CODEX_SESSION_INGEST_DESIGN.md)
- [`docs/INSTALL_VERIFICATION.md`](<repo-root>/docs/INSTALL_VERIFICATION.md)
- [`docs/IMPLEMENTATION_PLAN.md`](<repo-root>/docs/IMPLEMENTATION_PLAN.md)
- [`docs/ACCEPTANCE_CHECKLIST.md`](<repo-root>/docs/ACCEPTANCE_CHECKLIST.md)

它们用于回答“MemArk 是什么、当前仓库已经实现到哪里、AI 助手该如何理解这些材料”。

[`docs/MAINTAINER_SKILL.md`](<repo-root>/docs/MAINTAINER_SKILL.md) 是维护说明，不是用户入口。

## Supporting Research

以下文件是当前正式口径的支撑性研究，不应单独覆盖主线产品定义：

- [`docs/RESEARCH_MEMPALACE_USAGE.md`](<repo-root>/docs/RESEARCH_MEMPALACE_USAGE.md)
- [`docs/RESEARCH_GRAPHIFY_USAGE.md`](<repo-root>/docs/RESEARCH_GRAPHIFY_USAGE.md)
- [`docs/RESEARCH_MEMPAL_EVALUATION.md`](<repo-root>/docs/RESEARCH_MEMPAL_EVALUATION.md)

## 研究归档

[`docs/raw/`](<repo-root>/docs/raw) 保存的是研究过程，不是并列正式版本。

建议按以下方式理解 `a-f`：

- `a.md`：早期 `skill.md` 草稿，偏安装脚本思路
- `b.md`：安装型 Skill 的扩展草稿
- `c.md`：早期 README 草稿，采用 `MemPalace + LLM Wiki` 表述
- `d.md`：中期 README 修订说明，开始收敛为“调度器”视角
- `e.md`：转向 `Graphify` 后的 Skill 草稿
- `f.md`：转向 `Graphify` 后的 README 草稿

这六份材料应被看作一条线性的研究链：

1. 先讨论“要不要做一个安装型 AI Skill”
2. 再讨论“系统到底是整合器还是处理管线”
3. 然后收敛到“MemArk 的主要工作是把 MemPalace 内容输入 Graphify 处理”
4. 最后由最终评审筛掉不可直接执行的内容

另外：

- [`docs/raw/UNIFIED_MEMARK_BOUNDARY_2026-04-12.md`](<repo-root>/docs/raw/UNIFIED_MEMARK_BOUNDARY_2026-04-12.md) 保留了一份未来统一 runtime 边界草案
- 该文件已明确标注为 archived future-boundary sketch，不代表当前仓库的正式产品边界

## 最终裁定来源

当前最重要的判断依据是 [`docs/raw/最终评审.md`](<repo-root>/docs/raw/最终评审.md)。

它已经明确了三件事：

- 之前的草稿不能直接作为可执行安装文档合并
- 主路径里不能再引用不存在文件或未验证命令
- 必须把理念层、实现层和正式文档边界讲清楚

## 后续维护规则

- 新的正式文档放在仓库根目录或 `docs/` 下，不放进 `docs/raw/`
- `docs/raw/` 只追加研究档案、评审记录、草案比对
- 如果正式口径更新，应同步修改 `README.md` 与 `SKILL.md`
