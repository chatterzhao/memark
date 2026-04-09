# Maintainer Skill Notes

这份文件保存旧的文档维护型 Skill 说明，供仓库维护时参考。

它不是给最终用户安装 `MemPalace` / `Graphify` 用的 Skill。

## 旧定位

旧版 `SKILL.md` 的职责是：

- 解释 MemArk 文档口径
- 整理 `docs/raw`
- 生成实现计划和验收文档

由于当前方向已经收紧为“根目录 `SKILL.md` 只负责安装两者”，这些维护说明不再放在根目录主 Skill 中。

## 当前维护原则

- 根目录 [`SKILL.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/SKILL.md) 是默认生产入口
- [`skill-dev.md`](/Users/zhaoyu/Downloads/code/my-memark/memark/skill-dev.md) 是开发期安装测试入口
- 开发者可见的 runtime skill 副本位于 [`skills/memark`](/Users/zhaoyu/Downloads/code/my-memark/memark/skills/memark)
- 打包进 Python 包的 runtime skill 模板位于 [`memark/skill_bundle`](/Users/zhaoyu/Downloads/code/my-memark/memark/memark/skill_bundle)
- 文档维护与口径收敛说明放在 `docs/` 下
- 不把安装 Skill 和维护 Skill 混成一份
