# TR-20260813-003：微积分金标数据集验证

> 本报告冻结 WORK-2026-004 在实现提交 `e918fdf915d635760a86842ba1ccee933f962ed1` 上的作者复核结果。它不替代独立学科复核或独立 QA 签字，也不证明区域级 Anchor、parser 或任何 LLM 质量。

```yaml
status: passed
test_level: contract
owner: Codex (dataset author / separate verification pass; independent review pending)
related_ids: [WORK-2026-004, NFR-2026-002, NFR-2026-008, RISK-2026-001, RISK-2026-005]
build_id: e918fdf915d635760a86842ba1ccee933f962ed1
started_at: 2026-08-13T18:25:00+08:00
finished_at: 2026-08-13T19:48:00+08:00
supersedes: null
```

## 目的、范围和门槛

- 对应需求/风险：为页级 Anchor、概念/关系抽取和后续 AI eval 建立合法、冻结、可复跑的微积分输入；降低来源漂移、无证据边、成环和许可误用风险。
- In scope：MIT OCW RES.18-001 第 2 章 PDF、dataset card、NOTICE、30 个概念、40 条 `prerequisite_of` 关系、50 个页级锚点、JSON Schema、语义/来源/许可校验、失败变异及代表页视觉抽检。
- Out of scope：区域/bbox 金标、产品 Anchor/GraphPatch contract、parser 准确率、LLM/DeepSeek 调用、商业用途、独立学科或 QA 签字。
- 通过定义：固定计数和 schema 合法；ID/引用完整；关系端点存在、无重复/自环/环且证据覆盖两端；官方 PDF 字节/hash/页数/元数据一致，无加密、活动文档动作或嵌入文件；许可字段和 NOTICE 完整；代表页清晰可辨。
- 失败定义：任一自动门非零，官方资源重下摘要不同，页面/署名不可辨，或数据集错误标为 `approved`。
- 阻断定义：来源不可获取、PDF 工具不可用或独立复核未安排。前两项未发生；独立复核仍阻断工作项关闭。

## 冻结环境

```text
OS: Microsoft Windows 11 Home China 10.0.26200 / x64 / Asia/Shanghai
CPU: AMD Ryzen 9 7940HX with Radeon Graphics
RAM: 16,334,233,600 bytes
locale: zh-CN
Python: 3.12.6 / uv 0.12.3 / pypdf 6.15.0
Node: 24.14.1 / pnpm 11.19.0
commit: e918fdf915d635760a86842ba1ccee933f962ed1
uv.lock sha256: b0655498ba30cf987d8059291e1bbdada717185ab68871af369fb67d3b13f7cf
pnpm-lock.yaml sha256: 457e5378ea60e6451ec4e352e2ba3db35dec4d4f051efb3e8e6cf3ad966261ba
dataset: calculus-continuity-differentiability-v1 / 1.0.0-draft.1 / author_reviewed
dataset schema: calculus-gold.v1
gold.json sha256: 53268e3b7b54a9596ac73fc0e6096c5e8aa1941a534be0635591d42510d0e299
source PDF: 52 pages / 736149 bytes / sha256 c6a89688e956bc83c75c073068e9be3e7e8317377bd34e2a9d905fcb1af119fb
GraphPatch/API/DB: not created; page-level eval fixture only
Provider/model/prompt/sampling/seed: none/not applicable
network: official PDF re-download and official license/source verification only; no LLM calls
```

## 方法

- 命令：执行根 `AGENTS.md` 的完整本地 Python/Web 门，并额外运行 `uv run python -m scripts.validate_calculus_dataset` 与 `git diff --check`。
- 样本：30 concepts、40 relations、50 anchors、52-page PDF；14 个金标合同/失败变异测试；仓库总计 Python 24 tests、Web 1 component test。
- 变异：计数超限、未知端点、自环、重复边、环、证据端点缺失、PDF hash、许可商用字段、越界/非 PDF 路径、作者复核状态和伪批准状态。
- 来源对照：重新下载 MIT OCW 官方 PDF，确认 736149 bytes 和 SHA-256 与仓库 fixture 完全一致；资源页和 MIT OCW Terms 再核验作者、课程与 CC BY-NC-SA 4.0。
- 视觉抽检：用 Poppler `pdftoppm` 以 144 DPI 渲染 PDF 页 1、16、37、41、45、48、51，人工检查章节开头、切线、极限、ε-δ、连续、可导推出连续及署名页。
- 已知限制：关系属于教学判断；视觉样本不是 52 页全量复核；页级锚点不能用于声明 bbox 指标；作者与验证者为同一主体的分时复核。

## 结果

| Test ID | 场景 | Expected | Actual | Result | Bug | Evidence |
|---|---|---|---|---|---|---|
| TC-DATA-001 | schema、固定计数与 ID/引用 | 30/40/50，字段及引用合法 | 30/40/50；schema/引用通过 | PASS | — | validator、14/14 contract tests |
| TC-DATA-002 | 端点、自环、重复、证据与 DAG | 有效图通过；6 类关系变异失败 | 有效图通过；相关变异均拒绝 | PASS | — | `test_calculus_dataset.py` |
| TC-DATA-003 | PDF 来源、hash、页数、边界与安全属性 | 官方字节一致；52 页；anchor 1..52；无活动内容 | 重下 736149 bytes/hash 一致；52 页；边界通过；无加密/动作/嵌入文件 | PASS | — | validator、source re-download |
| TC-DATA-004 | 署名、许可、非商业、ShareAlike 与审批门 | NOTICE/字段完整；缺失/伪批准失败 | Gilbert Strang/MIT OCW/CC BY-NC-SA 4.0 完整；变异被拒绝 | PASS | — | schema、NOTICE、official terms |
| TC-DATA-005 | 代表页视觉渲染 | 标题、正文、公式、图和署名清晰 | 7/7 清晰；无裁切、黑块或观察到的缺字 | PASS | — | `evidence/TR-20260813-003/screenshots/` |
| TC-BUILD-001 | 仓库完整本地门 | 全部返回 0 | Python 24/24、Web 1/1；format/lint/type/peer/build 全绿 | PASS | — | evidence gate summary |

Poppler 输出包含旧 PDF 字体替代和 Type 3 glyph bounding-box 警告；7 张最终渲染图未观察到对应的可见缺陷，因此记录为非阻断工具告警，不推断全 PDF 无字体问题。

## 证据完整性

- Evidence manifest：`evidence/TR-20260813-003/manifest.json`。
- checksums：`evidence/TR-20260813-003/checksums.sha256`；fixture/schema/locks 摘要见冻结环境。
- 原始截图：7 张 PNG 位于 `evidence/TR-20260813-003/screenshots/`；命令、环境与门禁摘要同目录。
- 脱敏检查：仅公开教材、公开 URL、工具版本和摘要；无用户内容、API Key、Provider 请求/响应或本机秘密。
- 复跑命令：`evidence/TR-20260813-003/commands.txt`。

## 结论

- Decision：CONDITIONAL GO——金标 fixture 的自动验证和作者复核通过，可提交独立学科/QA 复核；不得标为 `approved`，不得据此进入下一主阶段或启用真实 DeepSeek。
- 阻断缺陷：范围内自动门无；工作项关闭门仍缺独立学科复核和独立 QA 签字。
- 接受风险及批准人：尚无；作者分时复核不替代项目负责人、独立学科或 QA 风险接受。
- 未验证项：40 条关系的第二人教学判断、50 个锚点的第二人页面确认、区域/bbox 精度、parser/LLM 质量与商业授权。
- 下一步/Owner/期限：项目负责人指派 independent_subject_reviewer 和 QA；复核者逐条记录接受/分歧，之后创建后续签字记录或 superseding report。
- QA 签字：`pending`（作者只完成 separate verification pass）。
