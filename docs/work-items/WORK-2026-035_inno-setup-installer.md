# WORK-2026-035：Windows 安装器（Inno Setup，第 10 步切片 3b）

```yaml
status: ready
type: feature
owner: Codex (installer + packaging role)
reviewers: [ai_qa_auditor, workspace_owner]
related_ids: [WORK-2026-033, WORK-2026-034, REQ-2026-001, NFR-2026-001]
target_stage: "阶段 1 / 自然语言第 10 步（Windows 桌面封装）切片 3b"
risk: medium
created_at: 2026-08-15T21:50:00+08:00
updated_at: 2026-08-15T21:50:00+08:00
```

## 问题与结果

- 用户/工程问题：切片 1/2 已交付便携 zip 与原生窗口，但「安装」仍靠手动解压/复制目录，没有
  开始菜单、卸载入口与「覆盖安装升级」。第 10 步「安装包 + 迁移/升级」还差最后一环。
- 期望结果：Inno Setup 生成单文件安装器 `zhizhi-<version>-setup.exe`——按用户安装（无需管理员）、
  开始菜单/桌面快捷方式、注册卸载器、覆盖安装升级（数据在 `%LOCALAPPDATA%\知枝\data` 不受影响）；
  应用与安装器带图标；代码签名作为可选（证书环境变量门控）能力。
- 成功如何被观察：从失败测试启动；`installer.iss` 与 `scripts/build_installer.py` 存在；安装器
  构建产物可静默安装 → 文件/快捷方式/卸载器注册正确 → 静默卸载干净；覆盖安装后数据仍在；
  全仓门全绿。

## 范围

- In scope（切片 3b）：
  - `apps/desktop/icon.ico`（+ `icon.png`）由 `scripts/generate_icon.py`（Pillow）生成；
    `build.spec` 的 EXE 与 Inno Setup 快捷方式共用该图标。
  - `apps/desktop/installer.iss`：AppId 固定（升级覆盖安装）、按用户安装到
    `{localappdata}\Programs\知枝\`、开始菜单 + 可选桌面快捷方式、卸载器注册、覆盖安装时
    保留用户数据（数据目录在安装目录之外）。
  - `scripts/build_installer.py`：定位 `ISCC.exe`（Inno Setup 6）→ 用版本/路径参数编译 .iss →
    `dist/zhizhi-<version>-setup.exe`；可选签名（`SIGNTOOL` + `SIGN_CERT` env 门控，缺省跳过）。
  - `pyproject.toml` build 组增 `pillow`（图标生成）。
  - 测试：`tests/unit/test_installer.py`（`installer.iss` 存在 + 关键节存在）；`scripts/build_installer.py`
    构建 + 静默安装/卸载冒烟。
- Out of scope（切片 3b）：代码签名证书的实际签发/购买（无证书，保持 env 门控、缺省跳过）；
  自动更新/增量更新（后续）；多用户/机器级安装（按用户优先）；商店发布。
- 受影响模块/接口/数据：新增 `apps/desktop/installer.iss`、`apps/desktop/icon.*`、
  `scripts/generate_icon.py`、`scripts/build_installer.py`；`build.spec` 增 icon；无 canonical
  contract/迁移/存储格式变化。
- 依赖和假设：WORK-2026-033/034 已验证；Inno Setup 6 编译器（`ISCC.exe`，经 winget 安装）；
  Pillow（build 组）；数据目录 `%LOCALAPPDATA%\知枝\data` 与安装目录分离（升级不丢数据）。

## 设计边界

- 领域/契约：无新 canonical contract/迁移。安装器只「放置文件 + 快捷方式 + 卸载器」，不改应用
  语义；数据目录永不写入安装目录。
- 升级：固定 AppId + 覆盖安装（Inno Setup 默认 `overwritealways` 语义）；数据在安装目录外，
  覆盖安装/卸载均不触碰 `%LOCALAPPDATA%\知枝\data`。
- 权限：按用户安装到 `{localappdata}\Programs\知枝\`，无需管理员；`PrivilegesRequired=lowest`。
- 签名：`SIGNTOOL`/`SIGN_CERT` 环境变量存在时才在 `[Setup] SignTool` 生效；缺省跳过且构建不失败。

## 风险影响

- 数据/schema/migration：无迁移；卸载/覆盖安装不删除 `%LOCALAPPDATA%\知枝\data`（不写
  `uninsdelete` 到数据目录）。
- 安全/隐私：安装器仅写安装目录 + 开始菜单/卸载器注册表键；无管理员权限；无网络下载。
- 并发/幂等/恢复：覆盖安装幂等（同 AppId）；卸载干净（快捷方式/卸载器移除）；数据保留。
- 性能/容量/成本：安装器 ~25 MB（含 WebView2 运行时依赖已由系统提供）；零模型成本。
- 可观测性/诊断：`build_installer.py` 打印 ISCC 路径与产物；静默安装日志 `/LOG`。
- 用户文档：`USER_MANUAL` 增「安装器」章节（安装/升级/卸载/数据位置）；路线第 10 步进度更新。

## 验收标准

- [ ] AC-1 (c1)：`scripts/generate_icon.py` 产出 `apps/desktop/icon.ico`；`build.spec` 与安装器引用它。
- [ ] AC-2 (c2)：`installer.iss` 存在且含固定 AppId、按用户安装、开始菜单/桌面快捷方式、卸载器注册。
- [ ] AC-3 (c3)：`scripts/build_installer.py` 产出 `dist/zhizhi-<version>-setup.exe`。
- [ ] AC-4 (c4)：静默安装后：`zhizhi.exe` 在安装目录、开始菜单快捷方式存在、卸载器注册正确；
  静默卸载后：安装目录/快捷方式/卸载器移除，`%LOCALAPPDATA%\知枝\data` 保留。
- [ ] AC-5 (c5)：覆盖安装升级后用户数据仍在。
- [ ] AC-6 (c6)：repository 门：validator、Ruff、scripts + strict package mypy、全仓 pytest、Web 全绿。
- [ ] 错误和恢复路径：ISCC 缺失时明确报错；签名证书缺失时跳过签名并告警（不失败）。
- [ ] 回滚/禁用方法：回退本工作项提交即回到「便携 zip 手动解压」；安装器不影响数据目录。

## 验证计划

| Test ID | 层次 | 场景 | 期望 | 证据 |
|---|---|---|---|---|
| TC-INST-001 | unit | installer.iss 存在 + 关键节 | AppId/目录/快捷方式/卸载器 | 待实现 |
| TC-INST-002 | build | build_installer 产出 setup.exe | 产物存在且可执行 | 待实现 |
| TC-INST-003 | e2e | 静默安装/卸载 + 数据保留 | 文件/快捷方式/卸载器 + 数据在 | 待实现 |
| TC-INST-004 | e2e | 覆盖安装升级数据保留 | 数据仍在 | 待实现 |
| TC-REPO-001 | repository | 全仓门 | validator/Ruff/mypy/pytest/Web | 待实现 |

## 交付物与关闭

- Commit/PR：分支 `feature/WORK-2026-035-inno-setup-installer`；Ready → 红灯 → 实现 → QA。
- Contract/ADR/migration/prompt：无新 canonical contract/ADR/migration/prompt；build 组增 pillow。
- Test Run：TC-INST-001..004 + 全仓门 + 静默安装/卸载冒烟。
- Release：`dist/zhizhi-<version>-setup.exe`（单文件安装器）；便携 zip 仍由 `package_desktop.py` 产出。
- 观察结果：新机器可「双击 setup.exe 安装 → 开始菜单启动 → 覆盖安装升级 → 卸载」，数据始终保留；
  第 10 步完成标志达成。
- 未完成项的新 ID：代码签名证书（owner 未提供，env 门控）；自动更新；向量检索（第 9 步遗留）。
