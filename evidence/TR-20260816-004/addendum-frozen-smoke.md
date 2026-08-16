# TR-20260816-004 Addendum：冻结产物重建 + 冻结 exe 搜索冒烟（WORK-2026-053）

- addendum_to: `TR-20260816-004`（原报告 P-3-001 覆盖边界之一为产物级验证）
- 性质: superseding record（不改写已封存报告）
- 时间: 2026-08-16 17:1x local
- 判定: **PASS**

## 产物重建（真实运行）

| 步骤 | 结果 |
|---|---|
| `pnpm build` | OK |
| `scripts/build_desktop.py` | Build complete（无进程占用，tasklist 验证） |
| `scripts/build_installer.py` | `dist/zhizhi-0.1.0-setup.exe`（28,931,045 字节） |
| `scripts/package_desktop.py` | `dist/zhizhi-0.1.0-portable.zip`（36,489,305 字节） |

无新增第三方依赖（搜索为 stdlib urllib），体积与上版基本一致。

## 冻结 exe 冒烟（`probes/frozen_search_smoke.py`，输出 `logs/frozen-smoke.log`）

以冻结产物 `--mcp-stdio` 启动、无 key 环境：

| 检查 | 结果 |
|---|---|
| S1 工具集 = 8（含 search_draft） | PASS |
| S2 search_draft 无 key → 结构化 `web_search_not_available`（key_required），零网络出口 | PASS |

RESULT: PASS（2/2）。

## 结论

WORK-2026-053 冻结链路验证通过；P-3-001 的产物级部分关闭，真实 provider 全链路
（owner 配 key）仍待复测。correlation 披露同原报告。
