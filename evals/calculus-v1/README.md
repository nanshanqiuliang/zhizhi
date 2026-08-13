# Calculus Gold Dataset v1

本目录是阶段 0 入口所需的非商业微积分金标 fixture，不是产品内置教材，也不是完整课程镜像。

## 冻结范围

- 来源：Gilbert Strang, *Calculus*, Chapter 2: Derivatives；MIT OpenCourseWare RES.18-001；
- 主题：导数、斜率、割线/切线、极限、连续性和“可导推出连续”；
- 规模：30 concepts / 40 prerequisite relations / 50 page-level anchors；
- 资源：`source/mit-ocw-res-18-001-chapter-02-derivatives.pdf`，52 pages；
- 许可：CC BY-NC-SA 4.0，仅非商业使用。详见 `NOTICE.md` 与 `DATASET_CARD.md`。

## 文件

- `gold.json`：人工编写的金标数据；
- `schema/gold.schema.json`：eval fixture v1 contract；
- `DATASET_CARD.md`：范围、标注方法、已知限制和使用门；
- `NOTICE.md`：署名、许可、修改与商用限制；
- `REVIEW.md`：作者复核和独立学科复核状态；
- `independent-review.json`：绑定数据摘要的 30/40/50 逐条待签复核包；
- `INDEPENDENT_REVIEW_GUIDE.md`：独立学科和 QA 的分离复核步骤；
- `source/`：哈希固定的上游第 2 章 PDF。

## 验证

```powershell
uv run python -m scripts.validate_calculus_dataset
uv run pytest tests/contract/test_calculus_dataset.py
uv run python -m scripts.validate_calculus_review
```

任何 hash、许可、计数、引用、DAG 或复核覆盖校验失败都会阻断后续 parser/AI eval。`--require-complete` 在独立学科和 QA 双签前应稳定失败，因此本数据集当前不能成为批准的质量基线。
