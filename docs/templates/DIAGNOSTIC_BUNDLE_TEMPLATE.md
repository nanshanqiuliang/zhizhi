# 用户诊断包 Contract

```yaml
schema_version: 1
owner: operations
status: draft|approved
```

## Manifest 必需字段

```text
bundle_id / generated_at / time_range / redaction_version
app_version / build_id / git_commit
desktop_version / sidecar_version / DB schema / contract versions
OS/architecture/locale/timezone / RAM / free_disk
config_fingerprint / non_sensitive_flags
included_file_paths + SHA-256 + size
user_opt_ins / excluded_categories
```

## 默认内容

- 脱敏日志窗口；
- health 和 DB integrity 摘要；
- job/stage 时间线；
- stable error codes 和 stack signature；
- 更新、备份、磁盘和 Provider 状态摘要；
- checksums。

## 默认排除

- key/token/cookie；
- 原始文档、数据库、向量；
- prompt/response 全文；
- 完整路径、用户名、机器序列号；
- 未经确认的截图或 quote。

## Redaction 测试

| Case | Secret/PII pattern | Expected | Test ID |
|---|---|---|---|

## 生成流程

1. 选择时间和可选内容；
2. 预估大小并显示隐私说明；
3. 只读收集；
4. allowlist + redaction；
5. 扫描秘密和敏感模式；
6. 生成 manifest/checksum；
7. 用户预览和选择保存；
8. 清理临时数据；
9. 写审计事件。

## 验收

- [ ] 无诊断包时应用仍可运行；
- [ ] 生成失败不遗留敏感临时文件；
- [ ] 支持人员可用 error/correlation/job/build 还原路径；
- [ ] 用户可看见并控制包内容；
- [ ] schema 向后兼容或有迁移说明。
