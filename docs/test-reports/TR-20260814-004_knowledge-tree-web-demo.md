# TR-20260814-004：会话内知识树 Web Demo 验证

> 本报告冻结 `fff1ce697cf3524fb7622f36cedfc63136e990f2` 的
> developer demo。它证明浏览器中的示例树可交互，不代表持久化、导入、来源
> 跳转、AI、Windows 安装包或正式发布已经完成。

```yaml
status: passed
test_level: component_interaction_browser
owner: graph_qa_fresh
related_ids: [WORK-2026-012, REQ-2026-001, REQ-2026-006, REQ-2026-008]
build_id: fff1ce697cf3524fb7622f36cedfc63136e990f2
started_at: 2026-08-14T02:00:00+08:00
finished_at: 2026-08-14T03:12:00+08:00
supersedes: null
```

## 目的与边界

- 第一屏提供真实可操作的 8 节点示例知识树，而不是工程状态页。
- 人工编辑、增删、拖动、排布、位置锁、会话撤销/重做和重置可验证。
- 桌面/手机都清楚显示这是示例、仅本会话，且导入、AI、数据库未连接。
- 不读取真实文件、网络、Provider、secret、用户数据或浏览器存储。

## 结果

| Test ID | 场景 | Actual | Result |
|---|---|---|---|
| TC-WEB-001 | 三栏/示例树/状态边界 | 8 节点、课程/画布/详情和免责声明 | PASS |
| TC-WEB-002 | 选择/编辑/新增/叶删除 | 状态一致，非叶删除失败关闭 | PASS |
| TC-WEB-003 | drag/layout/lock | 位置变化；locked 精确保留 | PASS |
| TC-WEB-004 | undo/redo/branch/reset | 栈语义、清 redo、恢复 8 节点 | PASS |
| TC-WEB-005 | roles/labels/disabled | toolbar/region/nav/field 可达 | PASS |
| TC-WEB-006 | 1440×900 / 390×844 | document 横溢 0；console error 0 | PASS |
| TC-REPO-001 | Python/仓库门 | validator/Ruff/mypy/154 tests | PASS |
| TC-REPO-002 | TS/Web/依赖/构建门 | frozen install/peers/generation/6 tests/build | PASS |

QA attempt 001 对 `5aab0e3` 发现 1 个 P1：移动断点同时隐藏所有
能力边界说明。`c8c6bf9` 以 1 failed / 5 passed 的测试复现，`fff1ce6`
增加手机端常驻提示条。attempt 002 对该冻结修复 PASS，0 P0/P1/P2、无新发现。

## 浏览器观察

- 1440×900：document client/scroll 均为 1440×900；canvas 自身承担 1000px
  横向滚动。编辑、undo/redo、drag、lock-preserving layout、add/delete/reset
  均通过。
- 390×844：document client/scroll width 均为 375；无 page-level 横溢。
  `演示能力边界` computed display 为 `flex`、visibility 为 `visible`，矩形
  top 68/bottom 106 完整位于首屏，并与保存控件共存。
- 两个尺寸的浏览器 warning/error 都为 0。截图见 evidence 目录。

## 结论与残余风险

- Decision：GO，仅限 WORK-2026-012 的本地 developer demo；自然语言第 3 步完成。
- 机器 QA 为 `correlated_review`，不是人类签字、发布批准或 owner 风险接受。
- 刷新/关闭必然丢失修改；用户不得录入需要保存的真实内容。
- 第 4 步需以独立 Ready 项、SQLite/schema/migration/restart/backup 测试接入
  本地持久化；不得把本 Demo 的 React 内存历史冒充产品保存。
