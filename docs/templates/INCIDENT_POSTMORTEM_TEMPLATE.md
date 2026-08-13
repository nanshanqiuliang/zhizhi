# INC-YYYY-NNN：<事故标题>

```yaml
status: declared|mitigating|monitoring|resolved|postmortem_complete
severity: SEV-0|SEV-1|SEV-2|SEV-3
incident_commander: <person>
technical_lead: <person>
operations_lead: <person>
scribe: <person>
started_at: <RFC3339>
detected_at: <RFC3339>
mitigated_at: null
resolved_at: null
```

## 摘要与影响

- 发生了什么：
- 用户/数据/安全/隐私影响：
- 受影响版本、环境、cohort 和时间范围：
- 数量与估算方法：
- 当前状态/用户绕过：

## 时间线（统一 UTC，记录事实和决定）

| Time | Actor | Observation/Action/Decision | Evidence/Result |
|---|---|---|---|

## 检测与响应

- 如何发现；本应由什么更早发现：
- 首次响应和升级是否达到目标：
- 止损/feature flag/停更/回滚：
- 证据保全：
- 对内/对外沟通：

## 根因

- 直接技术根因：
- 促成因素：
- 为什么测试没有阻止：
- 为什么监控没有更早发现：
- 哪些保护有效：
- 哪些保护失效：

## 恢复验证

- 服务/功能：
- 数据完整性：
- 备份/恢复点：
- 安全/隐私处置：
- 观察期：

## 行动项

| WORK ID | Action | Type[prevent/detect/mitigate] | Owner | Due | Verification | Status |
|---|---|---|---|---|---|---|

## 批准

- 复盘主持：
- 技术/QA/运维/安全：
- 完成日期：
