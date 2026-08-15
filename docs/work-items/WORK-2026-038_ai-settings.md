# WORK-2026-038：AI 接入设置（DeepSeek key 配置 + 设置对话框，第 10 步后用户反馈）

```yaml
status: ready
type: feature
owner: Codex (api + web role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [WORK-2026-007, WORK-2026-008, WORK-2026-026, REQ-2026-001, NFR-2026-001]
target_stage: "阶段 1 / 第 10 步后使用反馈修复"
risk: medium
created_at: 2026-08-15T23:00:00+08:00
updated_at: 2026-08-15T23:00:00+08:00
```

## 问题与结果

- 用户/工程问题：使用反馈——「AI 接入实际没有完成，并不能向 AI 提问」「没有接入 AI 的窗口
  选项」。根因：桌面版只从环境变量 `DEEPSEEK_API_KEY` 读 key，安装器/开始菜单启动的环境无该
  变量，且无任何设置界面，导致 AI 永远「未连接」。
- 期望结果：应用内提供「AI 设置」入口——粘贴/保存/清除 DeepSeek API key（存到
  `data_root/ai.json`），保存后 AI 功能（草案/问答/指令）即时可用；状态徽标动态显示
  「AI 已连接/未连接」。
- 成功如何被观察：红灯测试（`/api/settings/ai` 缺失 404）→ 实现；GET 返回 configured/enabled；
  PUT 保存 key 后 enabled=true（generator 重建）；DELETE 清除后 enabled=false；Web 设置对话框
  保存/清除并更新状态徽标；全仓门全绿。

## 范围

- In scope：
  - `apps/api/ai_config.py`：`load_api_key(data_root)`（`ai.json` 优先，env 兜底）+
    `save_api_key(data_root, key|None)`。
  - `apps/api/{ai_draft,answer,command}.py`：`build_deepseek_*_generator(api_key=None)` 显式
    key 参数（缺省读 env）。
  - `apps/api/main.py`：`create_app` 用 `load_api_key(root)` 构建未注入的 generator；可变的
    `ai_state` 供路由读取；新增 `GET/PUT/DELETE /api/settings/ai`（保存后重建 generator）。
  - `apps/web/src/api.ts`：`getAiSettings/setAiKey/clearAiKey`（可选方法）。
  - `apps/web/src/App.tsx`：「AI 设置」对话框（输入/保存/清除/关闭）+ 动态状态徽标。
  - 测试：`tests/integration/test_ai_settings.py`；Web 组件测试（可选）。
- Out of scope：多 Provider 选择；用量/账单展示；key 加密存储（`ai.json` 明文，个人本地数据目录，
  记录为边界）；代理/网络诊断。
- 受影响模块：`apps/api/ai_config.py`（新）、`ai_draft/answer/command.py`、`main.py`、web。
- 依赖和假设：DeepSeek provider 已 `enabled: true`（WORK-2026-008）；key 只写 `data_root/ai.json`
  （不在仓库）；保存后 generator 重建即时生效。

## 设计边界

- 领域/契约：无新 canonical contract；新增本地设置端点（GET/PUT/DELETE，仅本机）。
- 生命周期：`ai_state` 为 create_app 内部可变持有者；PUT/DELETE 后重建/清空 generator，路由
  读 `ai_state` 而非闭包参数。
- 兼容性：既有注入式 generator（测试/嵌入）优先；未注入时用 `load_api_key(root)`（配置文件 →
  env）。
- 安全：key 不回显（GET 只返回 configured/enabled）；`ai.json` 明文（个人本地数据目录，边界）；
  key 不进入仓库/日志。

## 风险影响

- 数据/schema/migration：无迁移；新增 `data_root/ai.json`。
- 安全/隐私：key 明文存本地数据目录（边界记录）；网络仅 DeepSeek API（用户已批准 provider）。
- 并发/幂等/恢复：PUT 幂等；生成器重建不崩溃（fail-closed 保持 503）。
- 性能/容量/成本：零额外成本（无 key 不调用）。
- 可观测性/诊断：状态徽标动态；设置保存/清除有状态反馈。
- 用户文档：手册「AI 设置」章节。

## 验收标准

- [ ] AC-1：`load_api_key` 配置文件优先、env 兜底；`save_api_key` 写/删 `ai.json`。
- [ ] AC-2：`GET /api/settings/ai` 返回 `{configured, enabled}`（不回显 key）。
- [ ] AC-3：`PUT` 保存 key → generator 重建、enabled=true；`DELETE` → 清除、enabled=false。
- [ ] AC-4：无 key 时 AI 端点仍 503 `ai_not_available`（fail-closed）。
- [ ] AC-5：Web「AI 设置」对话框保存/清除并更新徽标。
- [ ] AC-6：全仓门（validator/Ruff/mypy/pytest/Web）全绿。
- [ ] 错误和恢复路径：空/非字符串 key 422；配置文件损坏回退 env。
- [ ] 回滚/禁用方法：回退本提交即回「仅 env 读 key」。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-AI-001 | unit | load/save_api_key 优先级与写删 | 配置优先/env 兜底 | 待实现 |
| TC-AI-002 | integration | GET/PUT/DELETE /settings/ai | configured/enabled 正确 | 待实现 |
| TC-AI-003 | integration | 无 key 时 /ai-draft 503 | fail-closed | 待实现 |
| TC-AI-004 | component | 设置对话框保存/清除 + 徽标 | 状态更新 | 待实现 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 待实现 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-038-ai-settings`；Ready → 红灯 → 实现。
- Contract/ADR/migration/prompt：无新 canonical contract；新增本地设置端点。
- Test Run：TC-AI-001..004 + 全仓门。
- Release：随下一个桌面构建。
- 观察结果：应用内可接入 DeepSeek（设置 key 后草案/问答/指令可用）。
- 未完成项的新 ID：key 加密存储、用量展示、多 Provider（第 11 步）。
