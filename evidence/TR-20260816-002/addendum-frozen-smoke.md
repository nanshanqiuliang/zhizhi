# TR-20260816-002 Addendum：冻结产物重建 + 冻结 exe MCP 冒烟（WORK-2026-050）

- addendum_to: `TR-20260816-002`（原报告 P-3-001 覆盖边界：冻结 exe 冒烟待产物重建）
- 性质: superseding record（不改写已封存报告；本文件为其补充证据）
- 时间: 2026-08-16 15:39–15:43 local
- 判定: **PASS**（P-3-001 覆盖边界关闭）

## 产物重建（真实运行）

| 步骤 | 命令 | 结果 |
|---|---|---|
| Web 构建 | `pnpm build` | OK |
| 冻结 | `uv run --group dev --group build python scripts/build_desktop.py` | Build complete，`dist/zhizhi/` |
| 安装器 | `uv run --group dev --group build python scripts/build_installer.py` | `dist/zhizhi-0.1.0-setup.exe`（24,916,030 字节） |
| 便携包 | `uv run --group dev --group build python scripts/package_desktop.py` | `dist/zhizhi-0.1.0-portable.zip`（29,297,933 字节） |

构建时无 zhizhi.exe 进程占用（tasklist 验证）。

## 冻结 exe MCP 冒烟（真实运行，探针 `probes/frozen_mcp_smoke.py`，输出 `logs/frozen-smoke.log`）

以 `dist/zhizhi/zhizhi.exe --mcp-stdio --data-root <临时目录>` 启动冻结产物：

| 检查 | 结果 |
|---|---|
| P1 工具集 = 6（含 propose_patch/proposal_status） | PASS |
| P2 propose_patch → pending 提议 + proposal_id + confirmed=false | PASS |
| P3 proposal_status → pending、change_id=null | PASS |
| P4 未知 proposal_id → proposal_missing fail-closed | PASS |
| P5 图库 revision=0、concepts 空（未写库） | PASS |
| P6 proposals/ 目录落盘一个提议文件 | PASS |

RESULT: PASS（6/6）。

## 结论

WORK-2026-050 的冻结产物链路（stdio 6 工具 + 提议入队 + 只读观察 + fail-closed）
在 PyInstaller 冻结环境下验证通过；P-3-001 关闭。剩余观察仅 P-3-002（自动确认
开关为后续独立评审项，有意默认逐条确认）。

correlation 披露同原报告：correlated_review、human_signature=false、
owner_acceptance=false。
