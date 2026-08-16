# QA TR-20260815-009: Python-side gate runner (WORK-2026-047)
# ASCII-only paths; run from the repo root so relative paths resolve.
$ErrorActionPreference = "Continue"
$log = "evidence\TR-20260815-009\gates"
$fail = 0

Write-Host "=== GATE: uv-sync ==="
uv sync --locked --group dev 2>&1 | Tee-Object -FilePath (Join-Path $log "uv-sync.log") | Out-Host
if ($LASTEXITCODE -ne 0) { $fail = 1 }

Write-Host "=== GATE: validate_repository ==="
uv run python -m scripts.validate_repository 2>&1 | Tee-Object -FilePath (Join-Path $log "validate_repository.log") | Out-Host
if ($LASTEXITCODE -ne 0) { $fail = 1 }

Write-Host "=== GATE: ruff_format_check ==="
uv run ruff format --check packages scripts tests apps 2>&1 | Tee-Object -FilePath (Join-Path $log "ruff_format_check.log") | Out-Host
if ($LASTEXITCODE -ne 0) { $fail = 1 }

Write-Host "=== GATE: ruff_check ==="
uv run ruff check . 2>&1 | Tee-Object -FilePath (Join-Path $log "ruff_check.log") | Out-Host
if ($LASTEXITCODE -ne 0) { $fail = 1 }

Write-Host "=== GATE: mypy_scripts ==="
uv run mypy scripts 2>&1 | Tee-Object -FilePath (Join-Path $log "mypy_scripts.log") | Out-Host
if ($LASTEXITCODE -ne 0) { $fail = 1 }

Write-Host "=== GATE: mypy_strict ==="
uv run python -m mypy --strict packages/contracts-py/src packages/domain/src packages/infrastructure/src apps/api apps/desktop 2>&1 | Tee-Object -FilePath (Join-Path $log "mypy_strict.log") | Out-Host
if ($LASTEXITCODE -ne 0) { $fail = 1 }

Write-Host "=== GATE: pytest ==="
uv run python -m pytest -q 2>&1 | Tee-Object -FilePath (Join-Path $log "pytest.log") | Out-Host
if ($LASTEXITCODE -ne 0) { $fail = 1 }

Write-Host "PYTHON_GATES_RESULT=$fail"
exit $fail
