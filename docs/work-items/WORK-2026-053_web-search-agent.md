# WORK-2026-053：受控 Web 搜索 agent——「主题 → 搜网 → 思维导图」（第 11 步切片 4）

```yaml
status: ready
type: feature
owner: api + infrastructure + web + QA
reviewers: [project_owner, qa]
related_ids: [WORK-2026-043（全库草案）, WORK-2026-038（AI 设置模式）, WORK-2026-048/050（MCP）, REQ-2026-001]
target_stage: 第 11 步 Beta 加固与扩展
risk: medium
created_at: 2026-08-16T00:00:00Z
updated_at: 2026-08-16T00:00:00Z
```

## 问题与结果

- 用户/工程问题：知识树只能从本地资料生成；「告诉 AI 一个主题 → 搜网络 → 直接出
  思维导图」的路径缺失（第 11 步候选 2，被 provider 决策阻塞；owner 已授权按推荐
  方案实施第三方 API）。
- 期望结果：用户在应用内（或外部 AI 经 MCP）输入主题 → sidecar 调搜索 provider
  （Tavily/Brave，二选一，key 受控）→ 结果组装为文本 → 复用既有 workspace AI 草案
  管线（分块/合并/DAG/40 块上限/fail-soft）→ 返回**不可信草案**（`requires_
  confirmation`，预览确认后写入，与本地资料草案同一确认门）；草案面板展示网页来源
  列表。无 key 时结构化 fail-closed，无任何网络出口。
- 成功如何被观察：① 设置端点可配/查/清 provider+key（key 永不回显）；② 无 key →
  503 `web_search_not_available`；③ 注入 fake searcher+generator 时返回草案且图库
  revision 不变、sources 含网页标题/URL；④ 空 query/空结果 → 稳定 422；⑤ MCP
  `search_draft` 工具（工具集 8）同样只读+提议；⑥ live 双门（`RUN_LIVE_WEB_SEARCH_
  TESTS=1` + provider key）才发真实请求；⑦ 全部门禁 + CI 绿。

## 范围

- In scope：
  - `packages/infrastructure/.../web_search.py`（新）：`WebSearchError`（稳定码
    `web_search_invalid_query`/`web_search_failed`/`web_search_not_available`）、
    `SearchHit`、`search_tavily`/`search_brave`（stdlib urllib，镜像 LLM 传输层：
    仅 HTTPS、超时、可注入 opener 供测试、错误映射稳定 code/rule、key 不落日志）。
  - `apps/api/web_search_config.py`（新，镜像 ai_config）：`web-search.json`
    （provider+api_key），环境变量兜底（`ZHIZHI_WEB_SEARCH_PROVIDER` 默认 tavily；
    `TAVILY_API_KEY`/`BRAVE_API_KEY`）；provider 白名单。
  - `apps/api/main.py`：`GET/PUT/DELETE /api/settings/web-search`（configured/
    enabled/provider，key 不回显）+ `POST /api/workspaces/{id}/web-search-draft`
    （query 校验 → search → texts 组装 → workspace_draft_generator →
    `preview_graph_patch` 防御 → `{draft, patch, sources}`，不写库）；create_app 增
    `web_searcher` 注入口。
  - `apps/api/mcp_server.py`：`search_draft(workspace_id, query)`（同语义；工具集
    7→8，仍无图库写动词）；`build_mcp_server` 增注入。
  - `apps/web`：设置对话框增「Web 搜索」块（provider 选择 + key）；资料区增
    「主题」输入 + 「从网络主题生成思维导图」按钮；草案面板显示网页来源列表；
    `api.ts` 增类型与方法。
  - 测试：unit provider 解析/错误映射、integration 设置+草案端点、MCP 工具集 8、
    Web 交互、e2e live 双门骨架。
- Out of scope：网页正文爬取/快照存储（只用搜索摘要）；搜索结果缓存与配额管理；
  问答（/answer）接搜索；多 provider 聚合；searxng 自建；来源锚点落库（accept 后
  evidence_ids 为确定性 chunk id，跳转原文对 web 来源提示不可用）。
- 受影响模块/接口/数据：新增模块+端点+工具+UI 块；无契约/迁移变化；新配置文件
  `web-search.json`（数据目录，不入库）。
- 依赖和假设：无新第三方依赖（stdlib urllib）；Tavily/Brave 公网 API 可达（仅
  配置 key 后）；AI 草案仍需 DeepSeek key（搜索只提供文本素材）。

## 风险影响

- 安全/隐私（harness 门）：① 网络出口仅搜索 provider 域名、仅 HTTPS、仅配置 key
  后启用（文档化门 + 显式 env opt-in + 受控密钥引用，mirror DeepSeek）；② 搜索
  结果是**外部不可信输入**——只作为草案文本素材，AI 输出仍走不可信草案 + 应用内
  确认 + GraphPatch 提交门，prompt 注入面延续 fail-closed 处理；③ key 仅存本机
  数据目录、任何端点不回显；④ query 长度上限 200 字符。
- 并发/幂等/恢复：无状态搜索；草案不落库；失败 fail-closed 不留半成品。
- 性能/容量/成本：单次 8 条结果、basic depth；请求超时 15s；配额由 provider 侧
  控制（文档提示免费额度）。
- 可观测性：稳定 `web_search_*` code/rule；UI 显示精确错误。
- 用户文档：USER_MANUAL「从网络主题生成」+ 设置说明 + provider 免费额度提示。

## 验收标准

- [ ] AC-1：设置三端点行为正确，key 不回显，非法 provider 拒绝。
- [ ] AC-2：无 key → 503 `web_search_not_available`（API 与 MCP 一致）。
- [ ] AC-3：注入链路返回 requires_confirmation 草案 + sources，图库不变。
- [ ] AC-4：空 query/超长 query/空结果 → 稳定 422；网络/HTTP 错误 → 502
  `web_search_failed`（+rule）。
- [ ] AC-5：MCP 工具集 = 8（含 search_draft），禁写子串断言仍通过。
- [ ] AC-6：Web 设置块可保存/清除；主题按钮触发生成并在草案面板显示来源。
- [ ] AC-7：live 测试默认跳过，双门（env+key）才真实请求。
- [ ] 回滚：回退提交即回到无搜索形态；`web-search.json` 可独立删除。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-WEB-001 | unit | tavily/brave 解析+错误映射 | hits/稳定 code/rule | `test_web_search_provider.py` |
| TC-WEB-002 | integration | 设置端点 | 保存/查询（脱敏）/清除/非法 provider | `test_web_search_api.py` |
| TC-WEB-003 | integration | 草案端点（注入） | requires_confirmation+sources+图库不变 | 同上 |
| TC-WEB-004 | integration | fail-closed | 无 key 503；坏 query/空结果 422 | 同上 |
| TC-WEB-005 | integration | MCP search_draft | 工具集 8、不写库、无 key fail-closed | `test_mcp_bridge.py` |
| TC-WEB-006 | web | 设置块+主题按钮 | 保存/生成/来源显示 | `App.websearch.test.tsx` |
| TC-WEB-007 | e2e | live 双门 | 默认 skip | `test_web_search_live_smoke.py` |
| TC-WEB-008 | 全部门禁+CI | 回归 | 全绿 | 门禁/CI run |

## 交付物与关闭

- Commit/PR：红灯测试 → 实现 → 文档 → 证据封存 + 推送触发 CI。
- Contract/ADR/migration/prompt：无契约变化；新增 harness 文档「Web 搜索 provider 门」一节。
- Test Run：`TR-20260816-004`。
- Release：桌面产物重建 + 冻结冒烟（工具集 8）。
- 未完成项的新 ID：来源锚点落库与跳转；搜索缓存/配额；问答接搜索；searxng。
