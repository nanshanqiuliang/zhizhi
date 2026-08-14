# 风险登记册

> 风险是尚未发生的不确定事件；已发生的用户影响进入 Bug/Incident。

| ID | 风险 | 概率 | 影响 | 等级 | 触发信号 | 预防 | 应急 | Owner | 目标阶段 | 状态 |
|---|---|---:|---:|---:|---|---|---|---|---|---|
| RISK-2026-001 | 锚点无法稳定恢复，产品核心价值不成立 | 中 | 极高 | 高 | 页/区域指标未达标 | `e918fdf`/`232d0cd` 与 TR-20260813-003/004 已建 50 个页级金标及 v1 覆盖门；仍需 v2 AI 机器复核、parser/viewer 对照和区域金标 | 降级格式/暂停产品开发 | workspace_owner | 阶段 0 | open |
| RISK-2026-002 | AI 覆盖用户锁定内容 | 中 | 极高 | 高 | lock regression 非 0 | GraphPatch 确定性校验、属性测试 | 禁用 AI 写入、恢复 revision | 待定 | 阶段 0/2 | open |
| RISK-2026-003 | 本地安装依赖过重影响验证 | 中 | 高 | 高 | 需 Docker/外部 DB | SQLite + sidecar 本地基线 | 缩减功能或提供云模式 | 待定 | 阶段 1 | open |
| RISK-2026-004 | 日志/诊断包泄露课件、路径或密钥 | 中 | 极高 | 高 | 敏感字段进入 evidence | allowlist、redaction、隐私测试 | 停止上传、轮换密钥、事故响应 | 待定 | 阶段 1/3 | open |
| RISK-2026-005 | 模型/Prompt 更新造成静默质量退化 | 高 | 高 | 高 | eval、schema failure、cost 漂移 | calculus-gold v1 已作者复核；v2 将绑定模型/prompt/tool/harness hash、隔离 QA 和 replay eval；实现仍待完成 | 回退 model policy/prompt，机器审查状态失效 | workspace_owner | 阶段 0/2 | open |
| RISK-2026-006 | migration 或更新导致本地数据不可恢复 | 中 | 极高 | 高 | integrity/restore 失败 | expand-migrate-contract、备份恢复 | 停更、恢复备份/前向修复 | 待定 | 阶段 1/3 | open |
| RISK-2026-007 | 把 OpenAI 兼容误认为语义完全相同，导致 DeepSeek tool/thinking/JSON 失败 | 高 | 高 | 高 | 400、空 JSON、断流、schema failure 上升 | protocol/profile 分层、capability preflight、TC-LLM-001..009 | 隔离 deployment、回退批准配置、恢复 mock | 待定 | 阶段 0/2 | open |
| RISK-2026-008 | Provider 回退重复工具副作用或产生不可追溯的混合草案 | 中 | 极高 | 高 | 同一 tool_call 重放、partial output 被复用 | fresh model run、禁止副作用自动回退、幂等键 | 禁用回退/AI 草案、审计并撤销 revision | 待定 | 阶段 2 | open |
| RISK-2026-009 | 模型下线、别名漂移或能力变化造成静默退化 | 高 | 高 | 高 | `/models` 差异、capability mismatch、eval 漂移 | 显式模型 ID、能力快照、启动探测不自动升级 | 关闭 deployment、回退批准 snapshot | 待定 | 阶段 2/运营 | open |
| RISK-2026-010 | AI 学科与 QA 同源错误造成虚假一致 | 高 | 极高 | 极高 | 相同模型/来源一致 PASS、mutation 漏检 | run/prompt/context 隔离；优先跨模型/Provider；同源自动标 `correlated_review`；TR-005 已验证离线披露/隔离 | 返回 inconclusive；认证 owner 边界未实现前拒绝风险接受；关闭自动放行 | workspace_owner | 阶段 0/2 | open |
| RISK-2026-011 | 搜索结果提示注入、SEO/引用洗白或网页漂移污染自动复核 | 高 | 极高 | 极高 | 工具越权、引用不支持 claim、内容 hash 漂移 | SearchProvider allowlist、来源分级、内容视为不可信、引用/hash/获取时间、反证搜索；TR-005 已验证冻结 replay fixture | 隔离来源、使 attestation 失效、回到本地一手证据或 inconclusive | workspace_owner | 阶段 0/2/3 | open |
| RISK-2026-012 | Harness/validator 共同缺陷同时误导学科 Agent 和 QA | 中 | 极高 | 高 | 两角色共同漏检确定性 mutation | 纯领域验证、property/mutation test、content-addressed artifact、全部 attempt 留证；TR-005 已关闭 3 P1/3 P2 | 禁用机器通过状态、修复并重放所有受影响 run | workspace_owner（技术负责人确定前） | 阶段 0/2 | open |
| RISK-2026-013 | Windows 开发路径含空格导致 Vite `@fs`/`?url` 解析失败，PDF.js worker 加载失败使渲染不可用 | 中 | 高 | 高 | 渲染视图无 canvas/一直"正在渲染"、worker 404 | public worker 固定 URL（`/pdf.worker.min.mjs`）规避 `@fs` 空格；TR-010 浏览器验证通过 | 回退到页文本查看器；重建 worker 资源 | 待定 | 阶段 1 | open |
| RISK-2026-014 | headless/无头环境 canvas 渲染受限，自动化可能误报渲染失败 | 低 | 中 | 中 | headless 下 render promise 挂起或像素异常 | 真实浏览器人工验收（用户手册清单）；自动化只断言 canvas 存在与尺寸 | 用真实浏览器验证；不把 headless 限制当产品缺陷 | 待定 | 阶段 1 | open |

## 评分

概率和影响使用 `低/中/高/极高`。高风险必须有 Owner、触发信号、预防与应急；无缓解的高风险阻断对应阶段。
