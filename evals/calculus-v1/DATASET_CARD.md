# Dataset Card: calculus-v1

```yaml
dataset_id: calculus-continuity-differentiability-v1
version: 1.0.0-draft.1
status: author_reviewed_independent_review_pending
language: zh-CN labels and summaries; en source
license: CC-BY-NC-SA-4.0
commercial_use: prohibited
related_work: WORK-2026-004
```

## Purpose

为 parser/Anchor、概念抽取、先修关系和后续 DeepSeek 离线/真实评测提供一个小型、可追溯的固定输入。它只覆盖“连续性与可导性”周边概念，不代表完整微积分课程，也不能证明模型在其他教材或语言上有效。

## Source and selection

用户于 2026-08-13 指定 MIT OCW RES.18-001。教材页面列出 Chapter 2 的 2.1 Derivative、2.3 Slope and Tangent Line、2.6 Limits、2.7 Continuous Functions。本数据集下载官方 Chapter 2 PDF，不镜像整站或完整教材。

PDF 为 52 页、736149 bytes，SHA-256 `c6a89688e956bc83c75c073068e9be3e7e8317377bd34e2a9d905fcb1af119fb`。2026-08-13 作者复核时重新下载官方直链，远端字节数和 SHA-256 与仓库 fixture 一致。PDF 元数据作者为 Gilbert Strang、标题为 `RES.18-001 Calculus (f17), Chapter 02: Derivatives`，无加密或 JavaScript。

## Annotation method

- 概念：人工规范化；中文定义均为项目作者的简短转述，不复制教材长段原文。
- 关系：只标 `prerequisite_of`，方向为“学习前置概念 -> 目标概念”；每条需人工理由和至少一个页级证据。
- 锚点：只承诺 PDF 1-based page。`heading_path` 和 `topic_zh` 用于人工审查，不声明 text quote 或 bbox 精度。
- 计数：30 concepts、40 relations、50 anchors 是冻结验收值；任何改变必须发布新 dataset version。
- 许可：所有 anchor 解析到同一 hash-pinned PDF；数据和说明继承 CC BY-NC-SA 4.0，禁止商业用途。

## Quality controls

- JSON Schema 与 unknown-field rejection；
- ID 唯一、引用完整、无自环/重复边；
- prerequisite DAG 拓扑检查；
- PDF bytes/hash/pages/metadata 检查；
- 许可、署名、非商业与 ShareAlike 字段检查；
- 代表页面视觉抽检：PDF 页 1、16、37、41、45、48、51，覆盖章节开头、2.3、2.6、2.7、可导推出连续与署名页；
- 作者逐项复核已完成；独立学科复核未签字前不得标为 approved baseline。

## Known limitations

- 单一英文教材、单一作者和单一章节，存在表达与编排偏差；
- 金标定义/关系理由为中文转述，尚无跨语言一致性指标；
- 页级锚点不能证明区域级定位，不能用来宣称 Proposal 的 bbox 目标已通过；
- 先修关系具有教学判断性，40 条边尚待第二位学科复核者给出同意/分歧；
- 未包含负样本、概念同义词全量、习题难度、答案或完整课程结构；
- 许可为 NonCommercial + ShareAlike，会阻断未经单独授权的商业发布与商用训练。

## Permitted and prohibited use

允许：本项目的非商业研究、解析/锚点评测、模型 fixture/eval、教学实验，以及遵守同许可的再分发/改编。

禁止：把该 PDF 或衍生金标用于商业产品、收费训练或营利服务；暗示 MIT/作者认可；移除署名；对 ShareAlike 衍生物施加更严格限制。
