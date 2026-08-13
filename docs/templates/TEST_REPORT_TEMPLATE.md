# TR-YYYYMMDD-NNN：<测试报告标题>

> 签字后不可原位改写；更正创建新报告并通过 `supersedes` 关联。

```yaml
status: planned|running|passed|failed|blocked
test_level: unit|property|contract|integration|e2e|ai_eval|security|performance|recovery|release
owner: <QA>
related_ids: []
build_id: <build>
started_at: <RFC3339>
finished_at: <RFC3339>
supersedes: null
```

## 目的、范围和门槛

- 对应需求/风险/缺陷：
- In scope / Out of scope：
- 通过/失败/阻断定义：
- 工程初值与其依据：

## 冻结环境

```text
OS / CPU / RAM / disk / locale / timezone
app/build/commit / dependency lock hash
DB schema / API / GraphPatch / Anchor versions
config fingerprint / flags
test data and dataset card version
provider/model/prompt/schema/sampling/seed
network and cache state
```

## 方法

- 命令/脚本版本：
- 样本量与重复次数：
- 对照/基线：
- 统计方法：
- 已知限制：

## 结果

| Test ID | 场景 | Expected | Actual | Result | Bug | Evidence |
|---|---|---|---|---|---|---|

性能/概率指标必须报告适用的 p50/p95/p99、最大值、IQR/置信区间、样本量和失败率，不能只报平均值。

## 证据完整性

- Evidence manifest：
- checksums：
- 原始日志/trace/截图/数据：
- 脱敏检查：
- 复跑命令：

## 结论

- Decision：GO | CONDITIONAL GO | NO-GO
- 阻断缺陷：
- 接受风险及批准人：
- 未验证项：
- 下一步/Owner/期限：
- QA 签字：
