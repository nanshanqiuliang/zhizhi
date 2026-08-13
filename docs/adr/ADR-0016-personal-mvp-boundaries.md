# ADR-0016：个人 MVP 采用 Windows 本地优先、人工确认优先的边界

```yaml
status: proposed
date: 2026-08-14
decision_owner: workspace_owner (explicit confirmation pending)
related_ids: [WORK-2026-002, REQ-2026-001, REQ-2026-006, REQ-2026-007, REQ-2026-008, REQ-2026-009, REQ-2026-010]
supersedes: null
```

## Context

- 约束、问题、事实和未知：用户目标是个人笔记 App，可人工编辑树状知识图并由 AI 从授权资料生成草案。当前只有工程状态页和离线 eval；产品代码尚未开始。若同时承诺多平台、多格式、云端协作和自动 AI 写入，会延迟第一个可用闭环并扩大数据风险。
- 架构/安全/运维/数据影响：必须在 Web UI、Tauri、本地数据、GraphPatch、Anchor 和 Provider 之间保持同一领域语义；用户资料不得成为仓库测试内容；真实付费/联网能力未获预算批准。

## Decision Drivers

- 尽快交付能手工使用和修订的笔记/知识树闭环；
- 用户数据本地优先、人工修改高于 AI；
- AI 错误必须可预览、拒绝、撤销和追溯；
- 不用尚未批准的预算、平台或发布选择阻塞离线领域实现；
- Web 界面和 Windows App 不维护两套产品逻辑。

## Considered Options

### Option A：Windows 本地优先，先手工闭环再接 AI

- 优点：最快形成真实可用 App；数据和写入边界清晰；可逐步验证 Anchor/GraphPatch。
- 缺点/风险：macOS、云端协作、PPTX/OCR 和全自动 AI 较晚出现。

### Option B：一开始同时做跨平台、云端和全格式 AI

- 优点：表面功能覆盖更广。
- 缺点/风险：打包/权限/同步/解析/模型风险同时耦合；在手工修改与恢复未稳定前，AI 很容易破坏用户成果。

## Decision

- 选择：Option A。
- 理由：符合用户已认可的自然语言路线；第一版锁定 Windows 10/11 x64、单用户、本地核心可离线，先交付同源 Web UI，再由 Tauri 封装。首批导入 Markdown/TXT/PDF。所有持久图修改默认通过 GraphPatch 预览并由用户确认；内容、关系、位置和标记分别锁定。概念粒度默认“标准概念”，用户可按课程选择，模型只建议。Markdown 链接只能生成 `related_to` 候选，不自动生成先修边。
- 明确不解决：本地大模型、macOS/Linux 包、多人云端、PPTX/DOCX/OCR、shape 级定位、完整 Obsidian vault 迁移、真实模型金额预算、Embedding 选择和公开发布许可证。

## Consequences

- 正面：WORK-2026-005 可离线推进；第一个可见图编辑网页不依赖真实 AI、数据库或桌面壳。
- 负面/技术债：后续多平台和多格式会新增 adapter/打包矩阵；当前 workspace abstraction 暂时只有单用户实现。
- 对接口、迁移、测试、可观测性、运维的要求：GraphPatch/Anchor 必须版本化；锁和 revision 是领域事实；本地存储需备份/恢复/删除测试；日志不得记录正文；真实 Provider 在金额、secret、网络和 eval 门完成前保持关闭。

## Rollback or Migration

- 回滚/替代触发：用户明确要求首版改平台、格式、自动接受或云端边界，或技术尖峰证明当前方案不可行。
- 路径与成本：创建 superseding ADR/CHG，更新 PRD、工作项和迁移计划；不得直接修改已接受决策来掩盖范围变化。

## Evidence and Review

- Prototype/Test：WORK-2026-004 已证明离线 fixture/审查路径；产品功能仍待 WORK-2026-005 及后续工作项。
- 批准：workspace owner 已认可包含安全默认值的自然语言路线并随后要求继续开发，足以将这些值作为离线 prototype 的可回滚开发假设；尚无绑定本 ADR 精确内容的 owner 批准证明，因此保持 `proposed`，不得解释为正式风险接受或阶段出口批准。
- 复审条件/日期：第一个手工 Alpha 验收、引入真实 Provider、增加非 Windows 平台或云端协作前复审。
