# REL-X.Y.Z：发布 Manifest

```yaml
status: planning|rc|approved|rolling_out|paused|rolled_back|released|withdrawn
version: X.Y.Z[-pre]+build
channel: internal|alpha|beta|stable
release_owner: <person>
source_tag: <annotated tag>
git_commit: <sha>
build_id: <id>
artifact_sha256: <digest>
created_at: <RFC3339>
```

## 版本矩阵

| Component | Version |
|---|---|
| Desktop/Web/Sidecar | |
| DB schema | |
| API/OpenAPI | |
| GraphPatch/Anchor | |
| Parser/OCR | |
| Prompt/Model policy | |

## 内容与兼容性

- Included WORK/BUG/CHG/ADR：
- 用户可见变化/CHANGELOG：
- 已知问题和绕过：
- 支持 OS/架构：
- 新装/升级来源版本/不支持的降级：
- Migration/config/flags：

## 构建与供应链

- Builder/workflow：
- Dependency lock hashes：
- SBOM：
- Provenance/attestation：
- Signature verification：
- 第三方许可证：

## 验证

- Test reports：
- 安装/升级/migration：
- 备份恢复：
- 故障注入/回滚：
- 安全/隐私：
- 未验证项/风险接受：

## 灰度

| Cohort | Start | Observer | Entry criteria | Stop criteria | Result |
|---|---|---|---|---|---|

## 回滚

- 目标 artifact/digest：
- 数据兼容与恢复点：
- in-flight jobs 处置：
- Runbook：
- 回滚后 smoke/完整性：

## 签字

- 技术：
- QA：GO|CONDITIONAL GO|NO-GO
- 运维：
- 安全/隐私：
- 发布负责人最终决定与时间：
- 发布后观察关闭：
