# Document Status

本文件定义当前仓库中文档的层级关系，避免把研究稿误当成正式说明。

## 最新设计入口

如果要理解当前最新口径，请先读下面三份文档：

- [`docs/PRODUCT_REQUIREMENTS.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/PRODUCT_REQUIREMENTS.md)
- [`docs/AI_CONSUMPTION_MODEL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/AI_CONSUMPTION_MODEL.md)
- [`docs/AUTOMATION_CONSUMPTION_REQUIREMENTS.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/AUTOMATION_CONSUMPTION_REQUIREMENTS.md)
- [`docs/DOGFOOD_STATUS.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/DOGFOOD_STATUS.md)

其中：

- `PRODUCT_REQUIREMENTS.md` 定义产品需求边界
- `AI_CONSUMPTION_MODEL.md` 定义当前 AI 应如何消费这些产物
- `AUTOMATION_CONSUMPTION_REQUIREMENTS.md` 定义下一阶段“自动喂数据、自动加工、自动消费”的目标
- `DOGFOOD_STATUS.md` 定义哪些能力已经在当前仓库上真实吃过狗粮，哪些还只是测试通过

## 正式文档

以下文件是当前仓库的唯一权威入口：

- [`README.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/README.md)
- [`SKILL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/SKILL.md)
- [`skill-dev.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/skill-dev.md)
- [`docs/PROJECT_SCOPE.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/PROJECT_SCOPE.md)
- [`docs/GOVERNANCE_MODEL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/GOVERNANCE_MODEL.md)
- [`docs/INTERFACE_CONTRACT.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/INTERFACE_CONTRACT.md)
- [`docs/PRODUCT_REQUIREMENTS.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/PRODUCT_REQUIREMENTS.md)
- [`docs/FEATURE_LIST.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/FEATURE_LIST.md)
- [`docs/AI_CONSUMPTION_MODEL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/AI_CONSUMPTION_MODEL.md)
- [`docs/AUTOMATION_CONSUMPTION_REQUIREMENTS.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/AUTOMATION_CONSUMPTION_REQUIREMENTS.md)
- [`docs/DOGFOOD_STATUS.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/DOGFOOD_STATUS.md)
- [`docs/CODEX_SESSION_INGEST_DESIGN.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/CODEX_SESSION_INGEST_DESIGN.md)
- [`docs/INSTALL_VERIFICATION.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/INSTALL_VERIFICATION.md)
- [`docs/IMPLEMENTATION_PLAN.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/IMPLEMENTATION_PLAN.md)
- [`docs/ACCEPTANCE_CHECKLIST.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/ACCEPTANCE_CHECKLIST.md)

它们用于回答“MemArk 是什么、当前仓库已经实现到哪里、AI 助手该如何理解这些材料”。

[`docs/MAINTAINER_SKILL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/MAINTAINER_SKILL.md) 是维护说明，不是用户入口。

## 研究归档

[`docs/raw/`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/raw) 保存的是研究过程，不是并列正式版本。

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

## 最终裁定来源

当前最重要的判断依据是 [`docs/raw/最终评审.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/docs/raw/最终评审.md)。

它已经明确了三件事：

- 之前的草稿不能直接作为可执行安装文档合并
- 主路径里不能再引用不存在文件或未验证命令
- 必须把理念层、实现层和正式文档边界讲清楚

## 后续维护规则

- 新的正式文档放在仓库根目录或 `docs/` 下，不放进 `docs/raw/`
- `docs/raw/` 只追加研究档案、评审记录、草案比对
- 如果正式口径更新，应同步修改 `README.md` 与 `SKILL.md`
