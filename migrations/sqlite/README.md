# SQLite migrations

SQLite schema v1→v3（meta、history_records、resource、resource_version、
resource_segment、anchor）目前由
`packages/infrastructure/src/knowledge_tree_infrastructure/workspace.py` 的
`migrate()` 以 `PRAGMA user_version` 版本化实现（WORK-2026-013/016/017，
`TR-20260814-005/008/009`）。

本目录保留用于未来把迁移外部化为独立版本化脚本（当 schema 需要服务端/
多进程共管时）；在外部化之前，migration 的权威来源是
`knowledge_tree_infrastructure.workspace.migrate`，不得在此另建一份不同步
的 schema 定义。
