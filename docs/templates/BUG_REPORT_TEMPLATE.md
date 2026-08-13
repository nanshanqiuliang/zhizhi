# BUG-YYYY-NNN：<可搜索的症状标题>

```yaml
status: new
severity: P0|P1|P2|P3|P4
priority: urgent|high|normal|low
owner: <role/person>
first_seen_version: <version>
affected_versions: []
fixed_in_version: null
regression: yes|no|unknown
created_at: <RFC3339>
```

## 影响与风险

- 用户影响/范围/频率：
- 数据丢失或错误覆盖：yes|no|unknown
- 安全/隐私影响：yes|no|unknown
- 可用绕过：
- 是否升级为 Incident：

## 版本与环境

```text
app_version / build_id / git_commit
desktop_version / sidecar_version
database_schema_version / contract versions
OS / CPU / RAM / free disk
config_fingerprint / feature flags
provider / model / prompt / schema
```

## 关联证据

- 发生时间与时区：
- error_code：
- correlation_id / request_id：
- job_id / stage_run_id / model_run_id：
- course_id / graph_revision_id / resource_id：
- diagnostic_bundle / logs / trace / screenshot：

## 复现

- 前置条件：
- 最小输入/fixture（不得附未授权用户资料）：
- 步骤：
  1. 
- 期望：
- 实际：
- 复现次数/样本：
- 最近已知正常版本/环境：

## Triage 与定位

- first bad boundary：
- first bad version/commit：
- 已排除假设及证据：
- 当前假设及可证伪方法：
- root cause category：
- 根因说明（不得只写“人为错误”）：

## 修复

- 修复策略/为什么不是掩盖症状：
- Fix commit/PR：
- 数据修复或用户处置：
- 风险和回滚：

## 验证与关闭

- 失败回归测试 ID：
- 修复后测试 Run：
- 相邻边界/全量回归：
- 升级/回滚/恢复验证：
- 发布版本：
- 发布后观察期与指标：
- 关闭人/时间/证据：
