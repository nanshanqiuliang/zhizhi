# 用户手册

> status: engineering_preview
> 当前没有可安装产品。仅有开发者可运行的工程状态页，不得视为 MVP 功能。

> 已批准的产品方向：个人使用、本地优先的 AI Agent App。仓库已有不联网的开发者 mock/replay 审查原型，但产品端自动复核、真实模型和受控 Web Search 尚未实现，不得据此推断用户功能可用。

## 当前可用内容

- 无安装包；
- 无用户数据目录；
- 无诊断包导出；
- 无更新和恢复功能。
- 开发者在完成根 README 的锁定安装后，可运行 `pnpm --filter @knowledge-tree/web dev` 查看状态页；页面只显示工程门，不导入资料、不保存数据、不调用 LLM。
- 开发者可运行 `uv run python -m scripts.validate_ai_review_harness` 复放 v2 mock 审查门；输出 `machine_reviewed`/`correlated_review` 只表示确定性 fixture 通过，不是真人签字、真实模型质量证明或数据集批准。

## 未来每个用户可见功能必须说明

1. 前置条件与支持平台；
2. 操作步骤和成功结果；
3. 常见失败、稳定错误码和恢复建议；
4. 数据存储、联网、模型 Provider 和隐私影响；
5. 撤销、备份、导出和删除方式；
6. 版本差异、迁移和已知限制；
7. 如何复制 correlation/job ID 和导出脱敏诊断包。

用户可见行为变化若未同步本文件，不满足 Definition of Done。
