# 发布记录索引

当前无候选或正式发布。

每个版本创建：

```text
docs/releases/<version>/
  manifest.md
  checksums.sha256
  sbom-reference.md
  test-evidence.md
  rollout.md
  rollback-result.md
```

禁止覆盖已发布 artifact；同一版本内容变化必须产生新版本。
