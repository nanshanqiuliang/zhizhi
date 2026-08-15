# AI QA attempt 001 — Inno Setup 安装器（WORK-2026-035，第 10 步切片 3b）

```yaml
attestation_type: machine_attestation
actor_type: ai_agent
role_id: ai_qa_auditor
decision: pass
reviewed_commit: c0cd6a98c0911b43a57fc399fc6459dfb5203445
correlation_classification: correlated_review
human_signature: false
owner_acceptance: false
workspace_modified: false
network_used: false
```

## Decision

**PASS** — 0 P0 / 0 P1；1 P2 + 3 P3（均非阻塞，由 `cb46909` 修复）。这是对冻结提交
`c0cd6a9`（WORK-2026-035 第 10 步切片 3b：Inno Setup 安装器 + 应用图标 + build_installer）
的职责隔离机器审查。

## Red/green chain

Ready `04029a7` → 红灯 `babf418` → 实现 `c0cd6a9`。红灯真值经分离 worktree 实际重跑
（`pytest tests/unit/test_installer.py` → 3 failed：installer.iss 缺失 ×2 + build_installer
ModuleNotFoundError），与声明一致。

## Gates（本人执行，精确数字）

- 聚焦测试 `test_installer.py`：**3/3**。
- 全仓 pytest：**448 passed + 5 skipped**（live-LLM 门）。
- `ruff check .`：clean；`ruff format --check`：109 文件。
- `mypy scripts`：16 文件；`mypy --strict packages+apps/api+apps/desktop`：39 文件。
- `scripts.validate_repository`：**PASS**（含 secret scan）。
- Web（pnpm check/build）：**42/42**、build exit 0（仅 chunk-size 警告）。

## 安装器构建与冒烟（本人执行）

- `build_installer.py`：ISCC.exe（`%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`）编译成功，
  产出 `dist/zhizhi-0.1.0-setup.exe`（23,675,549 B）。
- **静默安装**（exit 0）：`%LOCALAPPDATA%\Programs\知枝\zhizhi.exe`、`unins000.exe`、开始菜单
  `知枝.lnk` + `卸载 知枝.lnk`、HKCU 卸载键（AppId `{8F2B3C1E-...}_is1`，DisplayName
  「知枝 version 0.1.0」）均正确；HKCU + `%LOCALAPPDATA%` 证明按用户免管理员安装。
- **覆盖安装升级**（exit 0）：`%LOCALAPPDATA%\知枝\data\` 标记文件内容不变（AC-5 ✓）。
- **静默卸载**（exit 0）：安装目录/开始菜单/桌面快捷方式/HKCU 键全部移除，数据目录 + 标记
  **保留**（AC-4 ✓）。清理后零残留。
- **ISCC 缺失路径**：明确报错 + SystemExit exit 1。
- **图标可复现**：`generate_icon.py` 重跑产物与提交的 `icon.png/ico` 字节一致；PNG 256×256
  RGBA，ICO {16,32,48,64,128,256}。

## Findings（非阻塞，已由 `cb46909` 修复）

| Sev | 位置 | Finding | 处置 |
|-----|------|---------|------|
| P2 | repository_validation.py TEXT_SUFFIXES | secret scan 未覆盖 `.iss`（scan 声明仅靠人工 grep） | 增 `.iss` |
| P2 | 工作项 doc | 签名描述为 `SIGNTOOL`/`SIGN_CERT` env 门控，实际为注释 `SignTool` 行 | 文档修正 |
| P3 | installer.iss:2 | 注释称传 `/DSourceDir`，实际只传 `/DAppVersion` | 注释修正 |
| P3 | installer.iss Tasks | 「可选桌面快捷方式」默认勾选 | `Flags: unchecked` |
| P3 | test_installer.py | 仅 token 存在性；注册/数据安全/AppId 靠手工冒烟 | 记录为边界（冒烟覆盖） |

## 执行 vs 静态追踪

- **执行**：全部 7 项 Python 门 + pnpm check/build、安装器在 HEAD 重建、完整静默安装/升级/卸载
  循环（含注册表 + 标记检查）、ISCC 缺失路径、红灯重跑、图标字节可复现、secret grep。未改仓库文件。
- **静态追踪**：AppId/`PrivilegesRequired`/`uninsdelete` 语义（已由行为佐证）、SignTool/
  AppPublisherURL 意图、`[Files]` 仅本地来源、doc-vs-commit 对齐。

## Disclosure

本报告为独立 AI QA 子 Agent（与实现 Agent 角色分离、同模型相关性）进行的机器审查，是证据与
工程发现的证明，**不是**人类签名、非 owner 接受。最终残余风险接受属于 workspace owner。
