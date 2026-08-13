# ADR 索引

当前架构基线列出的 ADR-0001 至 ADR-0012 尚未拆成独立、经批准的 ADR。进入技术尖峰前应优先创建：

1. ADR-0003：本地 SQLite / 云端 PostgreSQL；
2. ADR-0004：GraphPatch 唯一公共写协议；
3. ADR-0006：AI 只产草案；
4. ADR-0009：PDF.js 应用内查看；
5. ADR-0011：loopback sidecar 安全通信；
6. ADR-0012：用户变更优先于 AI 合并。

新增提案：

1. [ADR-0001：底层使用属性图，先修关系投影保持 DAG](ADR-0001-property-graph-prerequisite-dag.md)。
2. [ADR-0004：GraphPatch 是知识图的唯一公共写协议](ADR-0004-graphpatch-only-write-contract.md)。
3. [ADR-0006：AI 只能产生草案，不直接写入知识图](ADR-0006-ai-draft-only.md)。
4. [ADR-0012：人工变更和锁定优先于 AI 草案](ADR-0012-user-change-wins.md)。
7. [ADR-0015：以确定性 Harness 编排 AI 学科复核与 AI QA](ADR-0015-ai-review-harness.md)。产品方向已确认；在 v2 contract 和安全 fixture 形成证据前保持 `proposed`。
8. [ADR-0016：个人 MVP 采用 Windows 本地优先、人工确认优先的边界](ADR-0016-personal-mvp-boundaries.md)。安全默认值用于离线 prototype，精确内容仍待 workspace owner 确认；真实 Provider、预算、Embedding 和发布治理仍由独立 gate 控制。

使用 `docs/templates/ADR_TEMPLATE.md`。只有 `accepted` ADR 才是正式决策；架构总纲中的摘要目前仍是建议基线。
