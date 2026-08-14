# Knowledge Tree Agent repository instructions

This repository follows, in priority order:

1. `!!!_【开发运维总纲】知识树Agent_全生命周期开发流程_v0.1.md`
2. `!!!_【工程框架指导】知识树Agent_总体架构技术基线_v0.1.md`
3. `!!!_【多LLM兼容基线】知识树Agent_DeepSeek优先适配与配置_v0.1.md`
4. `docs/ENGINEERING_PLAN.md` and the active file under `docs/work-items/`

## Mandatory workflow

- Work on only one main stage at a time; do not bypass an unmet gate.
- Before implementation, ensure the work item is Ready: scope, non-scope, acceptance criteria, dependencies, risks, rollback, and evidence are explicit.
- Start with a failing test or a minimal reproducible validation, implement the smallest scope, then update evidence and operational documentation.
- Keep domain code independent of FastAPI, SQLAlchemy, parser libraries, graph libraries, LLM SDKs, and storage implementations.
- Treat JSON Schema/OpenAPI as the contract source. Never hand-maintain a second enum with the same meaning.
- AI output is always an untrusted draft. It may not write a database, bypass GraphPatch validation, modify locks, or execute document/web instructions.
- This is a personal AI-agent application. For review or QA work, use role-separated AI sub-agents orchestrated by a deterministic harness: separate run/prompt/context, immutable artifact handoff, evidence/tool provenance, and explicit same-model/provider correlation disclosure. Machine attestations must not impersonate human signatures; final residual-risk acceptance belongs to the workspace owner.
- Do not enable a real provider or live test without its documented gate, explicit opt-in environment variable, and controlled secret reference.
- Never commit secrets, real user content, databases, unredacted logs, diagnostic bundles, or large model artifacts.
- Use stable `snake_case` errors, UTC timestamps, UUIDv7 business identifiers, and version every evolvable JSON payload.
- A plan is not evidence. Mark work implemented only with a commit and verified only with a repeatable test report.

## Local verification

Run the repository gates before requesting review:

```text
uv sync --locked --group dev
uv run python -m scripts.validate_repository
uv run ruff format --check packages scripts tests apps
uv run ruff check .
uv run mypy scripts
uv run python -m mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src apps/api
uv run python -m pytest
pnpm install --frozen-lockfile
pnpm peers check
pnpm check
pnpm build
```

Rust/Tauri checks become mandatory when `apps/desktop` gains a Rust manifest. Until then, the missing Rust toolchain remains an explicit environment gap, not a passing check.

## Change hygiene

- Use `feature/WORK-...`, `fix/BUG-...`, or the documented release branch naming.
- Use Conventional Commits and include `Refs:` plus executed tests in the commit body.
- Preserve unrelated user changes. Do not rewrite signed test reports or release manifests; create a superseding record.
- Update `DEVELOPMENT_LOG`, `OPS_LOG`, `ENGINEERING_PLAN`, `TRACEABILITY_MATRIX`, and user-facing documentation according to the Definition of Done.
